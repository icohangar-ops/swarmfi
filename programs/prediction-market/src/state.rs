//! # Prediction Market — State Definitions

use anchor_lang::prelude::*;
use anchor_lang::solana_program::pubkey::Pubkey;

pub const MAX_QUESTION_LEN: usize = 256;
pub const MAX_DESCRIPTION_LEN: usize = 512;
pub const MAX_OUTCOME_LEN: usize = 64;
pub const MAX_OUTCOMES: usize = 10;

/// Market status lifecycle.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq, InitSpace)]
pub enum MarketStatus {
    Active,
    Resolved,
    Cancelled,
}

/// Global market configuration.
#[account]
#[derive(InitSpace)]
pub struct MarketConfig {
    /// Protocol admin
    pub admin: Pubkey,
    /// Fee in basis points charged on every trade
    pub fee_rate_bps: u64,
    /// Maximum number of simultaneous active markets
    pub max_markets: u32,
    /// Auto-incrementing market counter
    pub market_count: u64,
    /// Auto-incrementing prediction counter
    pub prediction_count: u64,
    /// Bump seed
    pub bump: u8,
}

/// A prediction market.
#[account]
#[derive(InitSpace)]
pub struct Market {
    /// Market ID (auto-incrementing)
    pub id: u64,
    /// Creator of the market
    pub creator: Pubkey,
    /// Market question
    #[max_len(MAX_QUESTION_LEN)]
    pub question: String,
    /// Market description
    #[max_len(MAX_DESCRIPTION_LEN)]
    pub description: String,
    /// Possible outcomes (at least 2)
    #[max_len(MAX_OUTCOMES)]
    pub outcomes: Vec<String>,
    /// Unix timestamp when the market ends
    pub end_time: i64,
    /// Total volume traded (in lamports)
    pub total_volume: u64,
    /// Total liquidity (in lamports)
    pub liquidity: u64,
    /// Current status
    pub status: MarketStatus,
    /// Winning outcome (set on resolution)
    #[max_len(MAX_OUTCOME_LEN)]
    pub winning_outcome: String,
    /// Resolution timestamp
    pub resolved_at: i64,
    /// Oracle program ID used for resolution
    pub oracle_program: Pubkey,
    /// Bump seed
    pub bump: u8,
}

/// A user's position in a market outcome.
#[account]
#[derive(InitSpace)]
pub struct Prediction {
    /// Prediction ID (auto-incrementing)
    pub id: u64,
    /// Market this prediction belongs to
    pub market_id: u64,
    /// The outcome the user bet on
    #[max_len(MAX_OUTCOME_LEN)]
    pub outcome: String,
    /// The user who made the prediction
    pub user: Pubkey,
    /// Amount staked (in lamports)
    pub stake_amount: u64,
    /// Average price per token
    pub avg_price: u64,
    /// Timestamp of the prediction
    pub created_at: i64,
    /// Whether winnings have been claimed
    pub claimed: bool,
    /// Bump seed
    pub bump: u8,
}

/// Resolution record for a market.
#[account]
#[derive(InitSpace)]
pub struct Resolution {
    /// Market ID
    pub market_id: u64,
    /// Winning outcome
    #[max_len(MAX_OUTCOME_LEN)]
    pub winning_outcome: String,
    /// Oracle consensus price used for resolution
    pub oracle_price: u64,
    /// Total pool size at resolution
    pub total_pool: u64,
    /// Winning pool size
    pub winning_pool: u64,
    /// Unix timestamp of resolution
    pub resolved_at: i64,
    /// Admin who resolved
    pub resolver: Pubkey,
    /// Bump seed
    pub bump: u8,
}

/// AMM pool for each outcome in a market.
/// Key: (market_id, outcome) -> OutcomePool
#[account]
#[derive(InitSpace)]
pub struct OutcomePool {
    /// Market ID
    pub market_id: u64,
    /// Outcome this pool covers
    #[max_len(MAX_OUTCOME_LEN)]
    pub outcome: String,
    /// Token reserve (outcome tokens)
    pub token_reserve: u64,
    /// Native reserve (SOL/lamports)
    pub native_reserve: u64,
    /// Bump seed
    pub bump: u8,
}
