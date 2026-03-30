//! # SwarmFi Prediction Market — Contract Business Logic
//!
//! Constant Product AMM (x·y = k) based prediction market with
//! fee-collecting trades, liquidity provision, and resolution.

use crate::error::ContractError;
use crate::msg::{
    ExecuteMsg, InstantiateMsg, MarketResponse, MarketsResponse, OrderResponse, OrdersResponse,
    PositionResponse, PositionsResponse, QueryMsg,
};
use crate::state::{
    Config, Market, MarketStatus, Order, OrderSide, OutcomePool, Position, ORDERS, CONFIG, LP_SHARES,
    MARKET_COUNT, MARKETS, ORDER_COUNT, OUTCOME_POOLS, POSITIONS,
};
use cosmwasm_std::{
    coin, ensure, entry_point, to_json_binary, Addr, BankMsg, Binary, Coin, Deps, DepsMut, Env,
    MessageInfo, Order as StdOrder, Response, StdResult, Timestamp, Uint128,
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
        min_liquidity: msg.min_liquidity,
        max_markets: msg.max_markets,
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
        ExecuteMsg::CreateMarket {
            question,
            description,
            outcomes,
            end_time,
            resolution_source,
        } => execute_create_market(
            deps,
            env,
            info,
            question,
            description,
            outcomes,
            end_time,
            resolution_source,
        ),
        ExecuteMsg::BuyOutcome {
            market_id,
            outcome,
            amount,
            max_price,
        } => execute_buy_outcome(deps, env, info, market_id, outcome, amount, max_price),
        ExecuteMsg::SellOutcome {
            market_id,
            outcome,
            amount,
            min_price,
        } => execute_sell_outcome(deps, env, info, market_id, outcome, amount, min_price),
        ExecuteMsg::ResolveMarket {
            market_id,
            winning_outcome,
        } => execute_resolve_market(deps, env, info, market_id, winning_outcome),
        ExecuteMsg::CancelMarket { market_id } => {
            execute_cancel_market(deps, env, info, market_id)
        }
        ExecuteMsg::AddLiquidity { market_id, amount } => {
            execute_add_liquidity(deps, env, info, market_id, amount)
        }
        ExecuteMsg::RemoveLiquidity {
            market_id,
            share_bps,
        } => execute_remove_liquidity(deps, env, info, market_id, share_bps),
        ExecuteMsg::UpdateConfig {
            admin,
            fee_rate_bps,
            min_liquidity,
            max_markets,
        } => execute_update_config(
            deps, env, info, admin, fee_rate_bps, min_liquidity, max_markets,
        ),
    }
}

// ── Execute implementations ───────────────────────────────────────

/// Create a new market. Requires initial liquidity deposit.
fn execute_create_market(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    question: String,
    description: String,
    outcomes: Vec<String>,
    end_time: Timestamp,
    resolution_source: Option<String>,
) -> Result<Response, ContractError> {
    ensure!(outcomes.len() >= 2, ContractError::TooFewOutcomes {});
    ensure!(end_time > env.block.time, ContractError::InvalidEndTime {});

    let config = CONFIG.load(deps.storage)?;
    let current_count = MARKET_COUNT.may_load(deps.storage)?.unwrap_or(0);
    ensure!(current_count < config.max_markets, ContractError::MaxMarketsReached {});

    // Require initial liquidity deposit.
    let payment = info
        .funds
        .iter()
        .find(|c| c.denom == "uinit")
        .cloned()
        .unwrap_or(Coin::new(0, "uinit"));
    ensure!(payment.amount >= config.min_liquidity, ContractError::InsufficientFunds {});

    let market_id = current_count + 1;
    MARKET_COUNT.save(deps.storage, &market_id)?;

    let market = Market {
        id: market_id,
        creator: info.sender.clone(),
        question,
        description,
        outcomes: outcomes.clone(),
        end_time,
        resolution_source,
        total_volume: Uint128::zero(),
        liquidity: payment.amount,
        status: MarketStatus::Active,
        winning_outcome: None,
        resolved_at: None,
    };
    MARKETS.save(deps.storage, market_id, &market)?;

    // Initialise AMM pools for each outcome with equal liquidity split.
    let per_outcome = payment.amount / Uint128::from(outcomes.len() as u128);
    for outcome in &outcomes {
        let pool = OutcomePool {
            token_reserve: per_outcome,
            native_reserve: per_outcome,
        };
        OUTCOME_POOLS.save(deps.storage, (market_id, outcome), &pool)?;
    }

    // Record LP shares for the creator.
    LP_SHARES.save(
        deps.storage,
        (market_id, &info.sender),
        &payment.amount,
    )?;

    Ok(Response::new()
        .add_attribute("action", "create_market")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("outcomes", &outcomes.join(",")))
}

/// Buy outcome tokens via the Constant Product AMM.
///
/// Price formula (per-token cost):
///   `price_a = native_reserve_b / (token_reserve_a + buy_amount)`
///
/// Total cost = `buy_amount * price_a + fee`
fn execute_buy_outcome(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    market_id: u64,
    outcome: String,
    amount: Uint128,
    max_price: Option<Uint128>,
) -> Result<Response, ContractError> {
    ensure!(!amount.is_zero(), ContractError::ZeroAmount {});

    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(market.status == MarketStatus::Active, ContractError::MarketNotActive {});

    market
        .outcomes
        .iter()
        .find(|o| **o == outcome)
        .ok_or_else(|| ContractError::InvalidOutcome {
            outcome: outcome.clone(),
        })?;

    let config = CONFIG.load(deps.storage)?;
    let mut pool = OUTCOME_POOLS.load(deps.storage, (market_id, &outcome))?;

    // Compute cost: constant-product AMM.
    // new_token_reserve = token_reserve + amount
    // cost = native_reserve - (k / new_token_reserve)
    // where k = token_reserve * native_reserve
    let k = pool.token_reserve.multiply_ratio(pool.native_reserve, Uint128::one());
    let new_token_reserve = pool.token_reserve + amount;
    let new_native_reserve = k / new_token_reserve;
    let raw_cost = pool.native_reserve.saturating_sub(new_native_reserve);

    // Apply fee.
    let fee = raw_cost.multiply_ratio(config.fee_rate_bps, 10_000u128);
    let total_cost = raw_cost + fee;

    // Slippage check.
    let price_per_token = if amount.is_zero() {
        Uint128::zero()
    } else {
        total_cost.multiply_ratio(Uint128::one(), amount)
    };
    if let Some(max) = max_price {
        ensure!(price_per_token <= max, ContractError::SlippageExceeded {
            actual: price_per_token.to_string(),
        });
    }

    // Verify payment.
    let payment = info.funds.iter().find(|c| c.denom == "uinit").map(|c| c.amount).unwrap_or(Uint128::zero());
    ensure!(payment >= total_cost, ContractError::InsufficientFunds {});

    // Update pool.
    pool.token_reserve = new_token_reserve;
    pool.native_reserve = new_native_reserve;
    OUTCOME_POOLS.save(deps.storage, (market_id, &outcome), &pool)?;

    // Update user position.
    let pos_key = (market_id, &info.sender, outcome.as_str());
    let mut position = POSITIONS
        .may_load(deps.storage, pos_key)?
        .unwrap_or(Position {
            owner: info.sender.clone(),
            market_id,
            outcome: outcome.clone(),
            amount: Uint128::zero(),
            avg_price: Uint128::zero(),
        });

    // Weighted average price.
    let total_value = position.amount.multiply_ratio(position.avg_price, Uint128::one())
        + amount.multiply_ratio(price_per_token, Uint128::one());
    let new_amount = position.amount + amount;
    position.avg_price = if new_amount.is_zero() {
        Uint128::zero()
    } else {
        total_value / new_amount
    };
    position.amount = new_amount;
    POSITIONS.save(deps.storage, pos_key, &position)?;

    // Update market volume.
    market.total_volume += total_cost;
    MARKETS.save(deps.storage, market_id, &market)?;

    // Record order.
    let order_id = ORDER_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    ORDER_COUNT.save(deps.storage, &order_id)?;
    ORDERS.save(
        deps.storage,
        (market_id, order_id),
        &Order {
            id: order_id,
            market_id,
            owner: info.sender.clone(),
            outcome: outcome.clone(),
            side: OrderSide::Buy,
            amount,
            price: price_per_token,
            filled: amount,
            created_at: env.block.time,
        },
    )?;

    Ok(Response::new()
        .add_attribute("action", "buy_outcome")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("outcome", &outcome)
        .add_attribute("amount", amount.to_string())
        .add_attribute("price", price_per_token.to_string())
        .add_attribute("fee", fee.to_string()))
}

/// Sell outcome tokens back to the AMM.
fn execute_sell_outcome(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    market_id: u64,
    outcome: String,
    amount: Uint128,
    min_price: Option<Uint128>,
) -> Result<Response, ContractError> {
    ensure!(!amount.is_zero(), ContractError::ZeroAmount {});

    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(market.status == MarketStatus::Active, ContractError::MarketNotActive {});

    let config = CONFIG.load(deps.storage)?;
    let mut pool = OUTCOME_POOLS.load(deps.storage, (market_id, &outcome))?;

    // Check user has enough tokens.
    let pos_key = (market_id, &info.sender, outcome.as_str());
    let mut position = POSITIONS
        .load(deps.storage, pos_key)
        .map_err(|_| ContractError::InsufficientPosition {})?;
    ensure!(position.amount >= amount, ContractError::InsufficientPosition {});

    // Compute payout via AMM.
    let k = pool.token_reserve.multiply_ratio(pool.native_reserve, Uint128::one());
    let new_token_reserve = pool.token_reserve + amount; // tokens returned to pool
    let new_native_reserve = k / new_token_reserve;
    let raw_payout = pool.native_reserve.saturating_sub(new_native_reserve);

    let fee = raw_payout.multiply_ratio(config.fee_rate_bps, 10_000u128);
    let net_payout = raw_payout.saturating_sub(fee);

    let price_per_token = if amount.is_zero() {
        Uint128::zero()
    } else {
        net_payout.multiply_ratio(Uint128::one(), amount)
    };

    if let Some(min) = min_price {
        ensure!(price_per_token >= min, ContractError::SlippageExceeded {
            actual: price_per_token.to_string(),
        });
    }

    // Update pool.
    pool.token_reserve = new_token_reserve;
    pool.native_reserve = new_native_reserve;
    OUTCOME_POOLS.save(deps.storage, (market_id, &outcome), &pool)?;

    // Update position.
    position.amount = position.amount.saturating_sub(amount);
    POSITIONS.save(deps.storage, pos_key, &position)?;

    // Update market volume.
    market.total_volume += raw_payout;
    MARKETS.save(deps.storage, market_id, &market)?;

    // Record order.
    let order_id = ORDER_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    ORDER_COUNT.save(deps.storage, &order_id)?;
    ORDERS.save(
        deps.storage,
        (market_id, order_id),
        &Order {
            id: order_id,
            market_id,
            owner: info.sender.clone(),
            outcome: outcome.clone(),
            side: OrderSide::Sell,
            amount,
            price: price_per_token,
            filled: amount,
            created_at: env.block.time,
        },
    )?;

    // Transfer payout to seller.
    let transfer_msg = BankMsg::Send {
        to_address: info.sender.to_string(),
        amount: vec![coin(net_payout.u128(), "uinit")],
    };

    Ok(Response::new()
        .add_message(transfer_msg)
        .add_attribute("action", "sell_outcome")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("outcome", &outcome)
        .add_attribute("amount", amount.to_string())
        .add_attribute("price", price_per_token.to_string())
        .add_attribute("payout", net_payout.to_string())
        .add_attribute("fee", fee.to_string()))
}

/// Resolve a market after end_time. Admin or oracle only.
fn execute_resolve_market(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    market_id: u64,
    winning_outcome: String,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(market.status == MarketStatus::Active, ContractError::MarketAlreadyResolved {});
    ensure!(env.block.time >= market.end_time, ContractError::MarketEnded {});

    market
        .outcomes
        .iter()
        .find(|o| **o == winning_outcome)
        .ok_or_else(|| ContractError::InvalidOutcome {
            outcome: winning_outcome.clone(),
        })?;

    market.status = MarketStatus::Resolved;
    market.winning_outcome = Some(winning_outcome.clone());
    market.resolved_at = Some(env.block.time);
    MARKETS.save(deps.storage, market_id, &market)?;

    Ok(Response::new()
        .add_attribute("action", "resolve_market")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("winning_outcome", &winning_outcome))
}

/// Cancel a market. Creator or admin only.
fn execute_cancel_market(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    market_id: u64,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(
        market.status == MarketStatus::Active,
        ContractError::MarketAlreadyCancelled {}
    );
    ensure!(
        info.sender == market.creator || info.sender == config.admin,
        ContractError::Unauthorized {
            role: "creator/admin".to_string(),
        }
    );

    market.status = MarketStatus::Cancelled;
    MARKETS.save(deps.storage, market_id, &market)?;

    // Refund LP shares to creator.
    let lp_balance = LP_SHARES
        .may_load(deps.storage, (market_id, &market.creator))?
        .unwrap_or(Uint128::zero());

    let refund_msg = if !lp_balance.is_zero() {
        Some(BankMsg::Send {
            to_address: market.creator.to_string(),
            amount: vec![coin(lp_balance.u128(), "uinit")],
        })
    } else {
        None
    };

    let mut resp = Response::new()
        .add_attribute("action", "cancel_market")
        .add_attribute("market_id", market_id.to_string());
    if let Some(msg) = refund_msg {
        resp = resp.add_message(msg);
    }
    Ok(resp)
}

/// Add liquidity to an existing active market.
fn execute_add_liquidity(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    market_id: u64,
    amount: Coin,
) -> Result<Response, ContractError> {
    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(market.status == MarketStatus::Active, ContractError::MarketNotActive {});
    ensure!(amount.denom == "uinit", ContractError::InsufficientFunds {});
    ensure!(!amount.amount.is_zero(), ContractError::ZeroAmount {});

    let payment = info
        .funds
        .iter()
        .find(|c| c.denom == "uinit" && c.amount >= amount.amount)
        .cloned();
    ensure!(payment.is_some(), ContractError::InsufficientFunds {});

    let add_amount = payment.unwrap().amount;

    // Split liquidity equally across all outcomes.
    let per_outcome = add_amount / Uint128::from(market.outcomes.len() as u128);
    for outcome in &market.outcomes {
        let mut pool = OUTCOME_POOLS.load(deps.storage, (market_id, outcome))?;
        pool.token_reserve += per_outcome;
        pool.native_reserve += per_outcome;
        OUTCOME_POOLS.save(deps.storage, (market_id, outcome), &pool)?;
    }

    // Credit LP shares.
    let current_shares = LP_SHARES
        .may_load(deps.storage, (market_id, &info.sender))?
        .unwrap_or(Uint128::zero());
    LP_SHARES.save(
        deps.storage,
        (market_id, &info.sender),
        &(current_shares + add_amount),
    )?;

    market.liquidity += add_amount;
    MARKETS.save(deps.storage, market_id, &market)?;

    Ok(Response::new()
        .add_attribute("action", "add_liquidity")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("amount", add_amount.to_string()))
}

/// Remove liquidity proportionally from a market.
fn execute_remove_liquidity(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    market_id: u64,
    share_bps: u64,
) -> Result<Response, ContractError> {
    let mut market = MARKETS.load(deps.storage, market_id)?;
    ensure!(market.status == MarketStatus::Active, ContractError::MarketNotActive {});
    ensure!(share_bps > 0 && share_bps <= 10_000u64, ContractError::ZeroAmount {});

    let shares = LP_SHARES
        .may_load(deps.storage, (market_id, &info.sender))?
        .unwrap_or(Uint128::zero());
    ensure!(!shares.is_zero(), ContractError::InsufficientPosition {});

    let withdraw_amount = shares.multiply_ratio(share_bps, 10_000u128);
    let remaining_shares = shares.saturating_sub(withdraw_amount);
    LP_SHARES.save(deps.storage, (market_id, &info.sender), &remaining_shares)?;

    // Reduce pools proportionally.
    let per_outcome = withdraw_amount / Uint128::from(market.outcomes.len() as u128);
    for outcome in &market.outcomes {
        let mut pool = OUTCOME_POOLS.load(deps.storage, (market_id, outcome))?;
        pool.token_reserve = pool.token_reserve.saturating_sub(per_outcome);
        pool.native_reserve = pool.native_reserve.saturating_sub(per_outcome);
        OUTCOME_POOLS.save(deps.storage, (market_id, outcome), &pool)?;
    }

    market.liquidity = market.liquidity.saturating_sub(withdraw_amount);
    MARKETS.save(deps.storage, market_id, &market)?;

    let transfer_msg = BankMsg::Send {
        to_address: info.sender.to_string(),
        amount: vec![coin(withdraw_amount.u128(), "uinit")],
    };

    Ok(Response::new()
        .add_message(transfer_msg)
        .add_attribute("action", "remove_liquidity")
        .add_attribute("market_id", market_id.to_string())
        .add_attribute("withdrawn", withdraw_amount.to_string()))
}

/// Admin updates protocol config.
fn execute_update_config(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    admin: Option<String>,
    fee_rate_bps: Option<u64>,
    min_liquidity: Option<Uint128>,
    max_markets: Option<u32>,
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
    if let Some(v) = min_liquidity {
        config.min_liquidity = v;
    }
    if let Some(v) = max_markets {
        config.max_markets = v;
    }
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new().add_attribute("action", "update_config"))
}

// ── Query dispatch ────────────────────────────────────────────────

pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetMarket { market_id } => to_json_binary(&query_market(deps, market_id)?),
        QueryMsg::ListMarkets { start_after, limit } => {
            to_json_binary(&query_list_markets(deps, start_after, limit)?)
        }
        QueryMsg::GetPosition {
            owner,
            market_id,
            outcome,
        } => to_json_binary(&query_position(deps, owner, market_id, outcome)?),
        QueryMsg::GetUserPositions {
            owner,
            start_after,
            limit,
        } => to_json_binary(&query_user_positions(deps, owner, start_after, limit)?),
        QueryMsg::GetMarketOrders { market_id } => {
            to_json_binary(&query_market_orders(deps, market_id)?)
        }
    }
}

fn query_market(deps: Deps, market_id: u64) -> StdResult<MarketResponse> {
    let m = MARKETS.load(deps.storage, market_id)?;
    Ok(MarketResponse {
        id: m.id,
        creator: m.creator.to_string(),
        question: m.question,
        description: m.description,
        outcomes: m.outcomes,
        end_time: m.end_time,
        resolution_source: m.resolution_source,
        total_volume: m.total_volume,
        liquidity: m.liquidity,
        status: format!("{:?}", m.status).to_lowercase(),
        winning_outcome: m.winning_outcome,
        resolved_at: m.resolved_at,
    })
}

fn query_list_markets(
    deps: Deps,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<MarketsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after.map(Bound::inclusive_bound);

    let markets: Vec<MarketResponse> = MARKETS
        .range(deps.storage, start, None, StdOrder::Ascending)
        .take(limit)
        .filter_map(|item| item.ok())
        .map(|(_, m)| MarketResponse {
            id: m.id,
            creator: m.creator.to_string(),
            question: m.question,
            description: m.description,
            outcomes: m.outcomes,
            end_time: m.end_time,
            resolution_source: m.resolution_source,
            total_volume: m.total_volume,
            liquidity: m.liquidity,
            status: format!("{:?}", m.status).to_lowercase(),
            winning_outcome: m.winning_outcome,
            resolved_at: m.resolved_at,
        })
        .collect();

    Ok(MarketsResponse { markets })
}

fn query_position(
    deps: Deps,
    owner: String,
    market_id: u64,
    outcome: String,
) -> StdResult<PositionResponse> {
    let addr = deps.api.addr_validate(&owner)?;
    let pos = POSITIONS.load(deps.storage, (&market_id, &addr, &outcome))?;
    Ok(PositionResponse {
        owner: pos.owner.to_string(),
        market_id: pos.market_id,
        outcome: pos.outcome,
        amount: pos.amount,
        avg_price: pos.avg_price,
    })
}

fn query_user_positions(
    deps: Deps,
    owner: String,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<PositionsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let addr = deps.api.addr_validate(&owner)?;

    // Prefix by (market_id, owner). We iterate markets in order.
    let market_count = MARKET_COUNT.may_load(deps.storage)?.unwrap_or(0);
    let start_market = start_after.unwrap_or(1);

    let mut positions = Vec::new();
    for mid in start_market..=market_count {
        if positions.len() >= limit {
            break;
        }
        // We need the outcomes to build keys. Load market.
        if let Ok(market) = MARKETS.load(deps.storage, mid) {
            for outcome in &market.outcomes {
                if let Ok(pos) = POSITIONS.may_load(deps.storage, (&mid, &addr, outcome.as_str())) {
                    if let Some(p) = pos {
                        if !p.amount.is_zero() {
                            positions.push(PositionResponse {
                                owner: p.owner.to_string(),
                                market_id: p.market_id,
                                outcome: p.outcome,
                                amount: p.amount,
                                avg_price: p.avg_price,
                            });
                        }
                    }
                }
            }
        }
    }

    Ok(PositionsResponse { positions })
}

fn query_market_orders(deps: Deps, market_id: u64) -> StdResult<OrdersResponse> {
    let orders: Vec<OrderResponse> = ORDERS
        .prefix(market_id)
        .range(deps.storage, None, None, StdOrder::Descending)
        .take(100)
        .filter_map(|item| item.ok())
        .map(|(_, o)| OrderResponse {
            id: o.id,
            market_id: o.market_id,
            owner: o.owner.to_string(),
            outcome: o.outcome,
            side: format!("{:?}", o.side).to_lowercase(),
            amount: o.amount,
            price: o.price,
            filled: o.filled,
            created_at: o.created_at,
        })
        .collect();

    Ok(OrdersResponse { orders })
}

use cosmwasm_std::{Bound, Order as StdOrder};
