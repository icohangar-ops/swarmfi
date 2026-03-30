//! # SwarmFi Bridge Adapter — Contract Business Logic
//!
//! Interface with Initia's Interwoven Bridge for cross-chain asset
//! transfers with fee collection and status tracking.

use crate::error::ContractError;
use crate::msg::{
    ConfigResponse, ExecuteMsg, InstantiateMsg, QueryMsg, TransferResponse, TransfersResponse,
};
use crate::state::{
    BridgeConfig, TransferRecord, TransferStatus, ALLOWED_ASSETS, CONFIG, SENDER_TRANSFERS,
    TRANSFER_COUNT, TRANSFERS,
};
use cosmwasm_std::{
    coin, ensure, to_json_binary, Addr, BankMsg, Binary, Deps, DepsMut, Env, MessageInfo,
    Order, Response, StdResult, Timestamp, Uint128,
};

// ── Instantiate ───────────────────────────────────────────────────

pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    _info: MessageInfo,
    msg: InstantiateMsg,
) -> Result<Response, ContractError> {
    let config = BridgeConfig {
        admin: deps.api.addr_validate(&msg.admin)?,
        fee_rate: msg.fee_rate,
        min_transfer: msg.min_transfer,
    };
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new()
        .add_attribute("action", "instantiate")
        .add_attribute("admin", &config.admin))
}

// ── Execute dispatch ──────────────────────────────────────────────

pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> Result<Response, ContractError> {
    match msg {
        ExecuteMsg::InitiateTransfer {
            recipient,
            asset,
            amount,
            source_chain,
            dest_chain,
        } => execute_initiate_transfer(
            deps,
            env,
            info,
            recipient,
            asset,
            amount,
            source_chain,
            dest_chain,
        ),
        ExecuteMsg::CompleteTransfer { transfer_id } => {
            execute_complete_transfer(deps, env, info, transfer_id)
        }
        ExecuteMsg::FailTransfer { transfer_id } => {
            execute_fail_transfer(deps, env, info, transfer_id)
        }
        ExecuteMsg::UpdateConfig {
            admin,
            fee_rate,
            min_transfer,
        } => execute_update_config(deps, env, info, admin, fee_rate, min_transfer),
        ExecuteMsg::SetAllowedAsset { asset, allowed } => {
            execute_set_allowed_asset(deps, env, info, asset, allowed)
        }
    }
}

// ── Execute implementations ───────────────────────────────────────

/// Initiate a new cross-chain transfer.
fn execute_initiate_transfer(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    recipient: String,
    asset: String,
    amount: Uint128,
    source_chain: String,
    dest_chain: String,
) -> Result<Response, ContractError> {
    // Verify the asset is allowed.
    let is_allowed = ALLOWED_ASSETS
        .may_load(deps.storage, &asset)?
        .unwrap_or(false);
    ensure!(is_allowed, ContractError::AssetNotAllowed { asset: asset.clone() });

    // Verify amount meets minimum.
    let config = CONFIG.load(deps.storage)?;
    ensure!(amount >= config.min_transfer, ContractError::BelowMinimum {});

    // Verify sufficient funds.
    let payment = info
        .funds
        .iter()
        .find(|c| c.denom == asset)
        .map(|c| c.amount)
        .unwrap_or(Uint128::zero());
    ensure!(payment >= amount, ContractError::InsufficientFunds {});

    // Calculate fee.
    let fee = amount.multiply_ratio(config.fee_rate, 10_000u128);

    // Create transfer record.
    let transfer_id = TRANSFER_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    TRANSFER_COUNT.save(deps.storage, &transfer_id)?;

    let record = TransferRecord {
        id: transfer_id,
        sender: info.sender.clone(),
        recipient,
        asset: asset.clone(),
        amount,
        fee,
        source_chain,
        dest_chain,
        status: TransferStatus::Pending,
        created_at: env.block.time,
        completed_at: None,
    };
    TRANSFERS.save(deps.storage, transfer_id, &record)?;

    // Track sender → transfer ids.
    let mut sender_txs = SENDER_TRANSFERS
        .may_load(deps.storage, &info.sender)?
        .unwrap_or_default();
    sender_txs.push(transfer_id);
    SENDER_TRANSFERS.save(deps.storage, &info.sender, &sender_txs)?;

    // In production this would emit an IBC packet or call the bridge
    // module. For now we just record the transfer on-chain.

    Ok(Response::new()
        .add_attribute("action", "initiate_transfer")
        .add_attribute("transfer_id", transfer_id.to_string())
        .add_attribute("asset", &asset)
        .add_attribute("amount", amount.to_string())
        .add_attribute("fee", fee.to_string()))
}

/// Complete a pending transfer (called by relayer / bridge module).
fn execute_complete_transfer(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    transfer_id: u64,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let mut record = TRANSFERS.load(deps.storage, transfer_id)?;
    ensure!(
        record.status == TransferStatus::Pending,
        ContractError::TransferAlreadySettled {}
    );

    record.status = TransferStatus::Completed;
    record.completed_at = Some(env.block.time);
    TRANSFERS.save(deps.storage, transfer_id, &record)?;

    // In production, the bridge module would have already delivered
    // tokens on the destination chain. Here we just mark it complete.

    Ok(Response::new()
        .add_attribute("action", "complete_transfer")
        .add_attribute("transfer_id", transfer_id.to_string())
        .add_attribute("status", "completed"))
}

/// Mark a transfer as failed (refunds sender).
fn execute_fail_transfer(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    transfer_id: u64,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let mut record = TRANSFERS.load(deps.storage, transfer_id)?;
    ensure!(
        record.status == TransferStatus::Pending,
        ContractError::TransferAlreadySettled {}
    );

    record.status = TransferStatus::Failed;
    record.completed_at = Some(env.block.time);
    TRANSFERS.save(deps.storage, transfer_id, &record)?;

    // Refund the sender (amount + fee).
    let refund_amount = record.amount + record.fee;
    let refund_msg = BankMsg::Send {
        to_address: record.sender.to_string(),
        amount: vec![coin(refund_amount.u128(), &record.asset)],
    };

    Ok(Response::new()
        .add_message(refund_msg)
        .add_attribute("action", "fail_transfer")
        .add_attribute("transfer_id", transfer_id.to_string())
        .add_attribute("status", "failed")
        .add_attribute("refund", refund_amount.to_string()))
}

/// Admin updates bridge configuration.
fn execute_update_config(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    admin: Option<String>,
    fee_rate: Option<u64>,
    min_transfer: Option<Uint128>,
) -> Result<Response, ContractError> {
    let mut config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    if let Some(admin_str) = admin {
        config.admin = deps.api.addr_validate(&admin_str)?;
    }
    if let Some(v) = fee_rate {
        config.fee_rate = v;
    }
    if let Some(v) = min_transfer {
        config.min_transfer = v;
    }
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new().add_attribute("action", "update_config"))
}

/// Admin adds or removes an asset from the allowed list.
fn execute_set_allowed_asset(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    asset: String,
    allowed: bool,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    if allowed {
        ALLOWED_ASSETS.save(deps.storage, &asset, &true)?;
    } else {
        ALLOWED_ASSETS.remove(deps.storage, &asset);
    }

    Ok(Response::new()
        .add_attribute("action", "set_allowed_asset")
        .add_attribute("asset", &asset)
        .add_attribute("allowed", allowed.to_string()))
}

// ── Query dispatch ────────────────────────────────────────────────

pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetTransfer { transfer_id } => {
            to_json_binary(&query_transfer(deps, transfer_id)?)
        }
        QueryMsg::ListTransfers {
            sender,
            status,
            start_after,
            limit,
        } => to_json_binary(&query_list_transfers(deps, sender, status, start_after, limit)?),
        QueryMsg::GetConfig => to_json_binary(&query_config(deps)?),
    }
}

fn query_transfer(deps: Deps, transfer_id: u64) -> StdResult<TransferResponse> {
    let r = TRANSFERS.load(deps.storage, transfer_id)?;
    Ok(TransferResponse {
        id: r.id,
        sender: r.sender.to_string(),
        recipient: r.recipient,
        asset: r.asset,
        amount: r.amount,
        fee: r.fee,
        source_chain: r.source_chain,
        dest_chain: r.dest_chain,
        status: r.status.as_str().to_string(),
        created_at: r.created_at,
        completed_at: r.completed_at,
    })
}

fn query_list_transfers(
    deps: Deps,
    sender: Option<String>,
    status_filter: Option<String>,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<TransfersResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after.map(cosmwasm_std::Bound::inclusive_bound);

    let transfers: Vec<TransferResponse> = TRANSFERS
        .range(deps.storage, start, None, Order::Descending)
        .take(limit * 2) // over-fetch for filtering
        .filter_map(|item| item.ok())
        .filter(|(_, r)| {
            // Filter by sender if specified.
            if let Some(ref sender_str) = sender {
                if r.sender.as_str() != sender_str.as_str() {
                    return false;
                }
            }
            // Filter by status if specified.
            if let Some(ref status_str) = status_filter {
                if r.status.as_str() != status_str.as_str() {
                    return false;
                }
            }
            true
        })
        .take(limit)
        .map(|(_, r)| TransferResponse {
            id: r.id,
            sender: r.sender.to_string(),
            recipient: r.recipient,
            asset: r.asset,
            amount: r.amount,
            fee: r.fee,
            source_chain: r.source_chain,
            dest_chain: r.dest_chain,
            status: r.status.as_str().to_string(),
            created_at: r.created_at,
            completed_at: r.completed_at,
        })
        .collect();

    Ok(TransfersResponse { transfers })
}

fn query_config(deps: Deps) -> StdResult<ConfigResponse> {
    let config = CONFIG.load(deps.storage)?;
    let transfer_count = TRANSFER_COUNT.may_load(deps.storage)?.unwrap_or(0);

    // Collect allowed assets.
    let allowed_assets: Vec<String> = ALLOWED_ASSETS
        .range(deps.storage, None, None, Order::Ascending)
        .filter_map(|item| item.ok())
        .filter_map(|(k, v)| if v { Some(k) } else { None })
        .collect();

    Ok(ConfigResponse {
        admin: config.admin.to_string(),
        fee_rate: config.fee_rate,
        min_transfer: config.min_transfer,
        allowed_assets,
        transfer_count,
    })
}
