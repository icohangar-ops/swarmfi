//! # SwarmFi Prediction Market — Solana Program
//!
//! Binary/scalar prediction markets with Constant Product AMM,
//! fee-collecting trades, liquidity provision, and oracle-based resolution.

use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use errors::*;
use state::*;

declare_id!("PMkt1SxPMKp3f5xLKNJghKBBm9JvHZQCEMJKWGPn7x4D");

#[program]
pub mod prediction_market {
    use super::*;

    /// Initialize the prediction market protocol.
    pub fn initialize(ctx: Context<InitializeMarket>, fee_rate_bps: u64, max_markets: u32) -> Result<()> {
        instructions::initialize::handler(ctx, fee_rate_bps, max_markets)
    }

    /// Create a new binary prediction market with initial liquidity.
    pub fn create_market(
        ctx: Context<CreateMarket>,
        question: String,
        description: String,
        outcomes: Vec<String>,
        end_time: i64,
    ) -> Result<()> {
        instructions::create_market::handler(ctx, question, description, outcomes, end_time)
    }

    /// Submit a prediction (stake on an outcome).
    pub fn submit_prediction(
        ctx: Context<SubmitPrediction>,
        outcome: String,
        amount: u64,
    ) -> Result<()> {
        instructions::submit_prediction::handler(ctx, outcome, amount)
    }

    /// Resolve a market using oracle data.
    pub fn resolve_market(
        ctx: Context<ResolveMarket>,
        winning_outcome: String,
    ) -> Result<()> {
        instructions::resolve_market::handler(ctx, winning_outcome)
    }

    /// Claim winnings from a resolved market.
    pub fn claim_winnings(ctx: Context<ClaimWinnings>) -> Result<()> {
        instructions::claim_winnings::handler(ctx)
    }
}
