//! # SwarmFi Reputation Registry — Solana Program
//!
//! Tracks agent and user reputation scores, accuracy, reliability tiers,
//! and badge awards. Reputation feeds into oracle consensus weighting
//! and prediction market credibility scoring.

use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use errors::*;
use state::*;

declare_id!("RepRGhYwcxEhMaSnZ3dKLCg3xNPEBcbNBjGEoTBDFZv");

#[program]
pub mod reputation_registry {
    use super::*;

    /// Initialize the reputation registry.
    pub fn initialize(ctx: Context<InitializeRegistry>) -> Result<()> {
        instructions::initialize::handler(ctx)
    }

    /// Update an agent's reputation after an oracle/prediction round.
    pub fn update_reputation(
        ctx: Context<UpdateReputation>,
        successful: bool,
        accuracy_delta: i64,
    ) -> Result<()> {
        instructions::update_reputation::handler(ctx, successful, accuracy_delta)
    }

    /// Get an agent's reputation (view function via account deserialization).
    pub fn get_reputation(ctx: Context<GetReputation>) -> Result<()> {
        instructions::get_reputation::handler(ctx)
    }

    /// Update a user's prediction record.
    pub fn record_prediction(
        ctx: Context<RecordPrediction>,
        correct: bool,
        volume: u64,
    ) -> Result<()> {
        instructions::update_reputation::record_prediction(ctx, correct, volume)
    }

    /// Create a new badge definition.
    pub fn create_badge(
        ctx: Context<CreateBadge>,
        name: String,
        description: String,
        badge_uri: String,
    ) -> Result<()> {
        instructions::update_reputation::create_badge(ctx, name, description, badge_uri)
    }

    /// Award a badge to a user or agent.
    pub fn award_badge(ctx: Context<AwardBadge>, badge_id: u64) -> Result<()> {
        instructions::update_reputation::award_badge(ctx, badge_id)
    }
}
