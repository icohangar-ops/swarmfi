//! # SwarmFi Prediction Market — Message Definitions
//!
//! Instantiate, Execute, and Query messages for creating, trading on,
//! and resolving prediction markets with a Constant Product AMM.

use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Coin, Timestamp, Uint128};

/// Instantiate the prediction-market contract.
#[cw_serde]
pub struct InstantiateMsg {
    /// Admin address (can resolve markets, update config).
    pub admin: String,
    /// Protocol fee in basis-points charged on every trade.
    pub fee_rate_bps: u64,
    /// Minimum native-token liquidity required to create a market.
    pub min_liquidity: Uint128,
    /// Maximum number of simultaneously active markets.
    pub max_markets: u32,
}

// ── Execute messages ──────────────────────────────────────────────

#[cw_serde]
pub enum ExecuteMsg {
    /// Create a new prediction market. Must attach `min_liquidity` as initial funding.
    CreateMarket {
        question: String,
        description: String,
        outcomes: Vec<String>,
        end_time: Timestamp,
        resolution_source: Option<String>,
    },

    /// Buy outcome tokens via the Constant Product AMM.
    BuyOutcome {
        market_id: u64,
        outcome: String,
        amount: Uint128,
        /// Maximum price per token the buyer is willing to pay (slippage guard).
        max_price: Option<Uint128>,
    },

    /// Sell outcome tokens back to the AMM.
    SellOutcome {
        market_id: u64,
        outcome: String,
        amount: Uint128,
        /// Minimum price per token the seller is willing to receive.
        min_price: Option<Uint128>,
    },

    /// Resolve a market after `end_time`. Admin or authorised oracle only.
    ResolveMarket {
        market_id: u64,
        winning_outcome: String,
    },

    /// Cancel a market (creator or admin). Refunds liquidity.
    CancelMarket { market_id: u64 },

    /// Provide additional liquidity to an active market.
    AddLiquidity {
        market_id: u64,
        amount: Coin,
    },

    /// Withdraw proportional liquidity from a market.
    RemoveLiquidity {
        market_id: u64,
        /// Fraction of LP shares to withdraw in basis-points (0–10000).
        share_bps: u64,
    },

    /// Admin updates protocol config.
    UpdateConfig {
        admin: Option<String>,
        fee_rate_bps: Option<u64>,
        min_liquidity: Option<Uint128>,
        max_markets: Option<u32>,
    },
}

// ── Query messages ────────────────────────────────────────────────

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    #[returns(MarketResponse)]
    GetMarket { market_id: u64 },

    #[returns(MarketsResponse)]
    ListMarkets {
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(PositionResponse)]
    GetPosition {
        owner: String,
        market_id: u64,
        outcome: String,
    },

    #[returns(PositionsResponse)]
    GetUserPositions {
        owner: String,
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(OrdersResponse)]
    GetMarketOrders { market_id: u64 },
}

// ── Response types ────────────────────────────────────────────────

#[cw_serde]
pub struct MarketResponse {
    pub id: u64,
    pub creator: String,
    pub question: String,
    pub description: String,
    pub outcomes: Vec<String>,
    pub end_time: Timestamp,
    pub resolution_source: Option<String>,
    pub total_volume: Uint128,
    pub liquidity: Uint128,
    pub status: String,
    pub winning_outcome: Option<String>,
    pub resolved_at: Option<Timestamp>,
}

#[cw_serde]
pub struct MarketsResponse {
    pub markets: Vec<MarketResponse>,
}

#[cw_serde]
pub struct PositionResponse {
    pub owner: String,
    pub market_id: u64,
    pub outcome: String,
    pub amount: Uint128,
    pub avg_price: Uint128,
}

#[cw_serde]
pub struct PositionsResponse {
    pub positions: Vec<PositionResponse>,
}

#[cw_serde]
pub struct OrdersResponse {
    pub orders: Vec<OrderResponse>,
}

#[cw_serde]
pub struct OrderResponse {
    pub id: u64,
    pub market_id: u64,
    pub owner: String,
    pub outcome: String,
    pub side: String,
    pub amount: Uint128,
    pub price: Uint128,
    pub filled: Uint128,
    pub created_at: Timestamp,
}
