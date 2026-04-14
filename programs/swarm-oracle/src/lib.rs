//! # SwarmFi Oracle — Solana Program
//!
//! Core AI swarm intelligence oracle for Solana.
//! Agents register, stake SOL, submit prices, and participate in
//! weighted-median consensus rounds with stigmergic coordination.

use anchor_lang::prelude::*;
use anchor_lang::solana_program::sysvar;
use instructions::*;

pub mod errors;
pub mod instructions;
pub mod state;

use errors::*;
use state::*;

declare_id!("FsWBMoA5x5bSaZGJGYeCsSWaaBGJ4eCqGMPbQnMBnKNp");

#[program]
pub mod swarm_oracle {
    use super::*;

    /// Initialize the global oracle configuration.
    pub fn initialize(ctx: Context<Initialize>, params: OracleInitParams) -> Result<()> {
        instructions::initialize::handler(ctx, params)
    }

    /// Register a new AI agent node.
    /// Mints an agent identity token (SPL Token) and stakes SOL.
    pub fn register_agent(
        ctx: Context<RegisterAgent>,
        name: String,
        agent_type: AgentType,
        stake_amount: u64,
    ) -> Result<()> {
        instructions::register_agent::handler(ctx, name, agent_type, stake_amount)
    }

    /// Agent submits a price for an asset pair.
    pub fn submit_price(
        ctx: Context<SubmitPrice>,
        asset_pair: String,
        price: u64,
        confidence: u8,
    ) -> Result<()> {
        instructions::submit_price::handler(ctx, asset_pair, price, confidence)
    }

    /// Run a weighted consensus round and compute the median price.
    pub fn run_consensus(ctx: Context<RunConsensus>, asset_pair: String) -> Result<()> {
        instructions::consensus::handler(ctx, asset_pair)
    }

    /// Submit a stigmergy coordination signal.
    pub fn submit_stigmergy_signal(
        ctx: Context<SubmitStigmergySignal>,
        signal_type: SignalType,
        data_hash: [u8; 32],
        strength: u64,
        decay_rate: u64,
    ) -> Result<()> {
        instructions::consensus::submit_stigmergy_signal(
            ctx,
            signal_type,
            data_hash,
            strength,
            decay_rate,
        )
    }

    /// Slash an agent's stake for excessive deviation from consensus.
    pub fn slash_agent(
        ctx: Context<SlashAgent>,
        deviation_bps: u64,
        reason: String,
    ) -> Result<()> {
        instructions::slash_agent::handler(ctx, deviation_bps, reason)
    }

    /// Update an agent's reputation score (admin only).
    pub fn update_agent_reputation(
        ctx: Context<UpdateAgentReputation>,
        reputation_delta: i64,
        accuracy_delta: i64,
    ) -> Result<()> {
        instructions::update_agent_reputation::handler(ctx, reputation_delta, accuracy_delta)
    }
}
