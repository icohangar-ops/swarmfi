//! # SwarmFi Prediction Market — State

use cosmwasm_std::{Addr, Timestamp, Uint128};
use cw_storage_plus::{Item, Map};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── Config ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Config {
    pub admin: Addr,
    pub fee_rate_bps: u64,
    pub min_liquidity: Uint128,
    pub max_markets: u32,
}

pub const CONFIG: Item<Config> = Item::new("config");

// ── Market ────────────────────────────────────────────────────────

/// Market status lifecycle.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum MarketStatus {
    Active,
    Resolved,
    Cancelled,
}

/// A prediction market.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Market {
    pub id: u64,
    pub creator: Addr,
    pub question: String,
    pub description: String,
    pub outcomes: Vec<String>,
    pub end_time: Timestamp,
    pub resolution_source: Option<String>,
    pub total_volume: Uint128,
    pub liquidity: Uint128,
    pub status: MarketStatus,
    pub winning_outcome: Option<String>,
    pub resolved_at: Option<Timestamp>,
}

pub const MARKET_COUNT: Item<u64> = Item::new("market_count");
pub const MARKETS: Map<u64, Market> = Map::new("markets");

// ── Position ──────────────────────────────────────────────────────

/// A user's position in a specific outcome of a market.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Position {
    pub owner: Addr,
    pub market_id: u64,
    pub outcome: String,
    pub amount: Uint128,
    pub avg_price: Uint128,
}

/// Primary key: `(market_id, owner, outcome)`.
pub const POSITIONS: Map<(&u64, &Addr, &str), Position> = Map::new("positions");

// ── AMM Pool ──────────────────────────────────────────────────────

/// Tracks the liquidity pool for each outcome in each market.
/// `outcome_liquidity` holds the token reserves for each outcome.
///
/// AMM invariant: for any two outcomes A and B in the same market,
/// `pool_A * pool_B = k` (constant product).
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct OutcomePool {
    /// Number of outcome tokens in the pool.
    pub token_reserve: Uint128,
    /// Native-token (e.g. uinit) reserve backing this outcome.
    pub native_reserve: Uint128,
}

/// Key: `(market_id, outcome)`.
pub const OUTCOME_POOLS: Map<(&u64, &str), OutcomePool> = Map::new("outcome_pools");

// ── LP Shares ─────────────────────────────────────────────────────

/// LP share balance per (market, provider).
/// Key: `(market_id, provider)`.
pub const LP_SHARES: Map<(&u64, &Addr), Uint128> = Map::new("lp_shares");

// ── Orders ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Order {
    pub id: u64,
    pub market_id: u64,
    pub owner: Addr,
    pub outcome: String,
    pub side: OrderSide,
    pub amount: Uint128,
    pub price: Uint128,
    pub filled: Uint128,
    pub created_at: Timestamp,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum OrderSide {
    Buy,
    Sell,
}

pub const ORDER_COUNT: Item<u64> = Item::new("order_count");
/// Key: `(market_id, order_id)`.
pub const ORDERS: Map<(&u64, u64), Order> = Map::new("orders");
