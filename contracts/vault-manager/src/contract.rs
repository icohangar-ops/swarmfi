//! # SwarmFi Vault Manager — Contract Business Logic

use crate::error::ContractError;
use crate::msg::{
    DepositsResponse, DepositResponse, ExecuteMsg, InstantiateMsg, PerformancePoint,
    QueryMsg, RebalanceEventResponse, RebalanceHistoryResponse, VaultPositionsResponse,
    VaultResponse, VaultsResponse,
};
use crate::state::{
    Config, RebalanceEvent, Vault, VaultDeposit, DEPOSITS, CONFIG, REBALANCE_COUNT,
    REBALANCE_EVENTS, USER_VAULTS, VAULTS, VAULT_COUNT, WHITELISTED_AGENTS,
};
use cosmwasm_std::{
    coin, to_json_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut, Env, MessageInfo, Order,
    Response, StdResult, Timestamp, Uint128,
};

// ── Instantiate ───────────────────────────────────────────────────

pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    _info: MessageInfo,
    msg: InstantiateMsg,
) -> Result<Response, ContractError> {
    let config = Config {
        admin: deps.api.addr_validate(&msg.admin)?,
        fee_rate_bps: msg.fee_rate_bps,
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
        ExecuteMsg::CreateVault {
            name,
            strategy_type,
        } => execute_create_vault(deps, env, info, name, strategy_type),
        ExecuteMsg::Deposit { vault_id } => execute_deposit(deps, env, info, vault_id),
        ExecuteMsg::Withdraw {
            vault_id,
            share_amount,
        } => execute_withdraw(deps, env, info, vault_id, share_amount),
        ExecuteMsg::Rebalance {
            vault_id,
            from_asset,
            to_asset,
            amount,
            reason,
        } => execute_rebalance(deps, env, info, vault_id, from_asset, to_asset, amount, reason),
        ExecuteMsg::UpdateConfig {
            admin,
            fee_rate_bps,
        } => execute_update_config(deps, env, info, admin, fee_rate_bps),
        ExecuteMsg::UpdateWhitelist { agent, add } => {
            execute_update_whitelist(deps, env, info, agent, add)
        }
        ExecuteMsg::SetVaultActive { vault_id, active } => {
            execute_set_vault_active(deps, env, info, vault_id, active)
        }
    }
}

// ── Execute implementations ───────────────────────────────────────

fn execute_create_vault(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    name: String,
    strategy_type: String,
) -> Result<Response, ContractError> {
    // Validate strategy type.
    match strategy_type.as_str() {
        "Conservative" | "Balanced" | "Aggressive" => {}
        _ => return Err(ContractError::InvalidStrategy {
            strategy: strategy_type,
        }),
    }

    let vault_id = VAULT_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    VAULT_COUNT.save(deps.storage, &vault_id)?;

    let vault = Vault {
        id: vault_id,
        name,
        strategy_type,
        owner: info.sender.clone(),
        assets: vec![],
        total_value: Uint128::zero(),
        total_shares: Uint128::zero(),
        performance_history: vec![],
        risk_score: match strategy_type.as_str() {
            "Conservative" => 1,
            "Balanced" => 5,
            _ => 9,
        },
        agent_count: 0,
        is_active: true,
        created_at: env.block.time,
    };
    VAULTS.save(deps.storage, vault_id, &vault)?;

    Ok(Response::new()
        .add_attribute("action", "create_vault")
        .add_attribute("vault_id", vault_id.to_string()))
}

fn execute_deposit(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    vault_id: u64,
) -> Result<Response, ContractError> {
    let mut vault = VAULTS.load(deps.storage, vault_id)?;
    if !vault.is_active {
        return Err(ContractError::VaultNotActive {});
    }

    // Accept any tokens sent with the message.
    let total_deposited: Uint128 = info
        .funds
        .iter()
        .map(|c| c.amount)
        .fold(Uint128::zero(), |acc, a| acc + a);

    if total_deposited.is_zero() {
        return Err(ContractError::InsufficientFunds {});
    }

    // Calculate shares: if TVL is 0, shares = deposited amount.
    // Otherwise shares = deposited * total_shares / total_value.
    let shares = if vault.total_shares.is_zero() {
        total_deposited
    } else {
        total_deposited.multiply_ratio(vault.total_shares, vault.total_value)
    };

    // Update vault assets.
    for coin in &info.funds {
        if let Some(existing) = vault.assets.iter_mut().find(|c| c.denom == coin.denom) {
            existing.amount += coin.amount;
        } else {
            vault.assets.push(coin.clone());
        }
    }
    vault.total_value += total_deposited;
    vault.total_shares += shares;

    // Record performance snapshot.
    vault.performance_history.push(PerformancePoint {
        timestamp: env.block.time,
        value: vault.total_value,
    });
    // Keep only last 100 data-points.
    if vault.performance_history.len() > 100 {
        vault.performance_history = vault.performance_history.split_off(vault.performance_history.len() - 100);
    }

    VAULTS.save(deps.storage, vault_id, &vault)?;

    // Record deposit.
    DEPOSITS.save(
        deps.storage,
        (vault_id, &info.sender),
        &VaultDeposit {
            depositor: info.sender.clone(),
            vault_id,
            amount: total_deposited,
            deposited_at: env.block.time,
            shares,
        },
    )?;

    // Track user → vaults.
    let mut user_vaults = USER_VAULTS
        .may_load(deps.storage, &info.sender)?
        .unwrap_or_default();
    if !user_vaults.contains(&vault_id) {
        user_vaults.push(vault_id);
        USER_VAULTS.save(deps.storage, &info.sender, &user_vaults)?;
    }

    Ok(Response::new()
        .add_attribute("action", "deposit")
        .add_attribute("vault_id", vault_id.to_string())
        .add_attribute("amount", total_deposited.to_string())
        .add_attribute("shares", shares.to_string()))
}

fn execute_withdraw(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    vault_id: u64,
    share_amount: Uint128,
) -> Result<Response, ContractError> {
    if share_amount.is_zero() {
        return Err(ContractError::InsufficientShares {});
    }

    let mut vault = VAULTS.load(deps.storage, vault_id)?;

    let deposit = DEPOSITS.load(deps.storage, (vault_id, &info.sender))?;
    ensure!(deposit.shares >= share_amount, ContractError::InsufficientShares {});

    // Calculate withdrawal amount: proportional to share fraction.
    let withdraw_value = if vault.total_shares.is_zero() {
        Uint128::zero()
    } else {
        share_amount.multiply_ratio(vault.total_value, vault.total_shares)
    };

    // Deduct from vault.
    vault.total_shares = vault.total_shares.saturating_sub(share_amount);
    vault.total_value = vault.total_value.saturating_sub(withdraw_value);

    // Deduct assets proportionally from each allocation.
    let mut return_coins: Vec<Coin> = vec![];
    for asset in &mut vault.assets {
        let asset_withdraw = if vault.total_value.is_zero() {
            asset.amount
        } else {
            share_amount.multiply_ratio(asset.amount, vault.total_shares + share_amount)
        };
        asset.amount = asset.amount.saturating_sub(asset_withdraw);
        if !asset_withdraw.is_zero() {
            return_coins.push(Coin {
                denom: asset.denom.clone(),
                amount: asset_withdraw,
            });
        }
    }

    // Remove zero-balance assets.
    vault.assets.retain(|c| !c.amount.is_zero());

    // Update deposit record.
    let mut updated_deposit = deposit;
    updated_deposit.shares = updated_deposit.shares.saturating_sub(share_amount);
    updated_deposit.amount = updated_deposit.amount.saturating_sub(withdraw_value);
    DEPOSITS.save(deps.storage, (vault_id, &info.sender), &updated_deposit)?;

    // Performance snapshot.
    vault.performance_history.push(PerformancePoint {
        timestamp: env.block.time,
        value: vault.total_value,
    });
    if vault.performance_history.len() > 100 {
        vault.performance_history = vault.performance_history.split_off(vault.performance_history.len() - 100);
    }

    VAULTS.save(deps.storage, vault_id, &vault)?;

    // Transfer tokens back.
    let transfer_msg = BankMsg::Send {
        to_address: info.sender.to_string(),
        amount: return_coins,
    };

    Ok(Response::new()
        .add_message(transfer_msg)
        .add_attribute("action", "withdraw")
        .add_attribute("vault_id", vault_id.to_string())
        .add_attribute("shares", share_amount.to_string())
        .add_attribute("value", withdraw_value.to_string()))
}

fn execute_rebalance(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    vault_id: u64,
    from_asset: String,
    to_asset: String,
    amount: Uint128,
    reason: String,
) -> Result<Response, ContractError> {
    // Only whitelisted agents can trigger rebalances.
    let is_whitelisted = WHITELISTED_AGENTS
        .may_load(deps.storage, &info.sender)?
        .unwrap_or(false);
    if !is_whitelisted {
        return Err(ContractError::AgentNotWhitelisted {});
    }

    let mut vault = VAULTS.load(deps.storage, vault_id)?;
    if !vault.is_active {
        return Err(ContractError::VaultNotActive {});
    }

    // Deduct from from_asset.
    let from_entry = vault
        .assets
        .iter_mut()
        .find(|c| c.denom == from_asset)
        .ok_or_else(|| ContractError::AssetNotFound {
            asset: from_asset.clone(),
        })?;
    ensure!(from_entry.amount >= amount, ContractError::InsufficientAssetBalance {});
    from_entry.amount = from_entry.amount.saturating_sub(amount);

    // Add to to_asset (create if not present).
    if let Some(to_entry) = vault.assets.iter_mut().find(|c| c.denom == to_asset) {
        to_entry.amount += amount;
    } else {
        vault.assets.push(Coin {
            denom: to_asset.clone(),
            amount,
        });
    }

    // Remove zero-balance assets.
    vault.assets.retain(|c| !c.amount.is_zero());

    vault.agent_count += 1;

    // Record rebalance event.
    let event_id = REBALANCE_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    REBALANCE_COUNT.save(deps.storage, &event_id)?;

    REBALANCE_EVENTS.save(
        deps.storage,
        event_id,
        &RebalanceEvent {
            id: event_id,
            vault_id,
            from_asset: from_asset.clone(),
            to_asset: to_asset.clone(),
            amount,
            triggered_by: info.sender.clone(),
            reason,
            executed_at: env.block.time,
        },
    )?;

    VAULTS.save(deps.storage, vault_id, &vault)?;

    Ok(Response::new()
        .add_attribute("action", "rebalance")
        .add_attribute("vault_id", vault_id.to_string())
        .add_attribute("from_asset", &from_asset)
        .add_attribute("to_asset", &to_asset)
        .add_attribute("amount", amount.to_string())
        .add_attribute("triggered_by", &info.sender))
}

fn execute_update_config(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    admin: Option<String>,
    fee_rate_bps: Option<u64>,
) -> Result<Response, ContractError> {
    let mut config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    if let Some(admin_str) = admin {
        config.admin = deps.api.addr_validate(&admin_str)?;
    }
    if let Some(v) = fee_rate_bps {
        config.fee_rate_bps = v;
    }
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new().add_attribute("action", "update_config"))
}

fn execute_update_whitelist(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    agent: String,
    add: bool,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let agent_addr = deps.api.addr_validate(&agent)?;
    if add {
        WHITELISTED_AGENTS.save(deps.storage, &agent_addr, &true)?;
    } else {
        WHITELISTED_AGENTS.remove(deps.storage, &agent_addr);
    }

    Ok(Response::new()
        .add_attribute("action", "update_whitelist")
        .add_attribute("agent", &agent_addr)
        .add_attribute("add", add.to_string()))
}

fn execute_set_vault_active(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    vault_id: u64,
    active: bool,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let mut vault = VAULTS.load(deps.storage, vault_id)?;
    vault.is_active = active;
    VAULTS.save(deps.storage, vault_id, &vault)?;

    Ok(Response::new()
        .add_attribute("action", "set_vault_active")
        .add_attribute("vault_id", vault_id.to_string())
        .add_attribute("active", active.to_string()))
}

// ── Query dispatch ────────────────────────────────────────────────

pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetVault { vault_id } => to_json_binary(&query_vault(deps, vault_id)?),
        QueryMsg::ListVaults { start_after, limit } => {
            to_json_binary(&query_list_vaults(deps, start_after, limit)?)
        }
        QueryMsg::GetVaultPositions { vault_id } => {
            to_json_binary(&query_vault_positions(deps, vault_id)?)
        }
        QueryMsg::GetUserPositions {
            owner,
            start_after,
            limit,
        } => to_json_binary(&query_user_deposits(deps, owner, start_after, limit)?),
        QueryMsg::GetRebalanceHistory {
            vault_id,
            start_after,
            limit,
        } => to_json_binary(&query_rebalance_history(
            deps,
            vault_id,
            start_after,
            limit,
        )?),
    }
}

fn query_vault(deps: Deps, vault_id: u64) -> StdResult<VaultResponse> {
    let v = VAULTS.load(deps.storage, vault_id)?;
    Ok(VaultResponse {
        id: v.id,
        name: v.name,
        strategy_type: v.strategy_type,
        owner: v.owner.to_string(),
        assets: v.assets,
        total_value: v.total_value,
        total_shares: v.total_shares,
        performance_history: v.performance_history,
        risk_score: v.risk_score,
        agent_count: v.agent_count,
        is_active: v.is_active,
        created_at: v.created_at,
    })
}

fn query_list_vaults(
    deps: Deps,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<VaultsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after.map(cosmwasm_std::Bound::inclusive_bound);

    let vaults: Vec<VaultResponse> = VAULTS
        .range(deps.storage, start, None, Order::Ascending)
        .take(limit)
        .filter_map(|item| item.ok())
        .map(|(_, v)| VaultResponse {
            id: v.id,
            name: v.name,
            strategy_type: v.strategy_type,
            owner: v.owner.to_string(),
            assets: v.assets,
            total_value: v.total_value,
            total_shares: v.total_shares,
            performance_history: v.performance_history,
            risk_score: v.risk_score,
            agent_count: v.agent_count,
            is_active: v.is_active,
            created_at: v.created_at,
        })
        .collect();

    Ok(VaultsResponse { vaults })
}

fn query_vault_positions(deps: Deps, vault_id: u64) -> StdResult<VaultPositionsResponse> {
    let vault = VAULTS.load(deps.storage, vault_id)?;
    Ok(VaultPositionsResponse {
        vault_id,
        assets: vault.assets,
    })
}

fn query_user_deposits(
    deps: Deps,
    owner: String,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<DepositsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let addr = deps.api.addr_validate(&owner)?;
    let user_vaults = USER_VAULTS.may_load(deps.storage, &addr)?.unwrap_or_default();

    let start = start_after.unwrap_or(0) as usize;
    let deposits: Vec<DepositResponse> = user_vaults
        .iter()
        .skip_while(|vid| **vid <= start as u64)
        .filter_map(|vid| DEPOSITS.may_load(deps.storage, (*vid, &addr)).ok().flatten())
        .take(limit)
        .map(|d| DepositResponse {
            depositor: d.depositor.to_string(),
            vault_id: d.vault_id,
            amount: d.amount,
            deposited_at: d.deposited_at,
            shares: d.shares,
        })
        .collect();

    Ok(DepositsResponse { deposits })
}

fn query_rebalance_history(
    deps: Deps,
    vault_id: u64,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<RebalanceHistoryResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after.map(cosmwasm_std::Bound::inclusive_bound);

    let events: Vec<RebalanceEventResponse> = REBALANCE_EVENTS
        .range(deps.storage, start, None, Order::Descending)
        .take(limit * 2) // over-fetch then filter
        .filter_map(|item| item.ok())
        .filter(|(_, e)| e.vault_id == vault_id)
        .take(limit)
        .map(|(_, e)| RebalanceEventResponse {
            vault_id: e.vault_id,
            from_asset: e.from_asset,
            to_asset: e.to_asset,
            amount: e.amount,
            triggered_by: e.triggered_by.to_string(),
            reason: e.reason,
            executed_at: e.executed_at,
        })
        .collect();

    Ok(RebalanceHistoryResponse { events })
}

use cosmwasm_std::ensure;
