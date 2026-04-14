//! # Submit Price
//!
//! Agent submits a price for an asset pair. The price feed is stored on-chain
//! with a consensus weight derived from the agent's reputation and stake.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::OracleError;

#[derive(Accounts)]
#[instruction(asset_pair: String, _price: u64, _confidence: u8)]
pub struct SubmitPrice<'info> {
    #[account(
        seeds = [b"oracle_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, OracleConfig>,

    #[account(
        mut,
        seeds = [b"agent_node", agent_authority.key().as_ref()],
        bump = agent_node.bump,
        constraint = agent_node.is_active @ OracleError::AgentInactive,
    )]
    pub agent_node: Account<'info, AgentNode>,

    #[account(
        init,
        payer = agent_authority,
        space = 8 + PriceFeed::INIT_SPACE,
        seeds = [b"price_feed", asset_pair.as_bytes(), agent_authority.key().as_ref()],
        bump
    )]
    pub price_feed: Account<'info, PriceFeed>,

    #[account(mut)]
    pub agent_authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<SubmitPrice>,
    asset_pair: String,
    price: u64,
    confidence: u8,
) -> Result<()> {
    require!(!price == false, OracleError::ZeroPrice); // price must not be 0
    require!(price > 0, OracleError::ZeroPrice);
    require!(confidence > 0, OracleError::InvalidConfidence);
    require!(asset_pair.len() <= MAX_ASSET_PAIR_LEN, OracleError::AssetPairTooLong);

    let agent_node = &mut ctx.accounts.agent_node;
    let price_feed = &mut ctx.accounts.price_feed;
    let clock = Clock::get()?;

    // Compute consensus weight: reputation * (stake in SOL)
    // Scale: reputation is 0-1000, stake is in lamports
    let stake_sol = agent_node.stake_amount / 1_000_000_000; // Convert lamports to SOL
    let consensus_weight = agent_node.reputation_score.saturating_mul(stake_sol.max(1));

    // Store the price feed
    price_feed.asset_pair = asset_pair;
    price_feed.price = price;
    price_feed.confidence = confidence;
    price_feed.agent = ctx.accounts.agent_authority.key();
    price_feed.consensus_weight = consensus_weight;
    price_feed.submitted_at = clock.unix_timestamp;
    price_feed.included_in_consensus = false;
    price_feed.bump = ctx.bumps.price_feed;

    // Update agent stats
    agent_node.total_submissions += 1;
    agent_node.last_submission_at = clock.unix_timestamp;

    Ok(())
}
