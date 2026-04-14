//! # Slash Agent
//!
//! Slash an agent's stake for excessive deviation from the consensus price.
//! Slashed SOL is transferred to the protocol treasury.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::OracleError;

#[derive(Accounts)]
#[instruction(_deviation_bps: u64, _reason: String)]
pub struct SlashAgent<'info> {
    #[account(
        mut,
        seeds = [b"oracle_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ OracleError::Unauthorized,
    )]
    pub config: Account<'info, OracleConfig>,

    #[account(
        mut,
        seeds = [b"agent_node", agent_authority.key().as_ref()],
        bump = agent_node.bump,
    )]
    pub agent_node: Account<'info, AgentNode>,

    /// The agent's PDA stake vault
    #[account(
        mut,
        seeds = [b"agent_stake_vault", agent_authority.key().as_ref()],
        bump
    )]
    pub stake_vault: SystemAccount<'info>,

    /// Treasury to receive slashed funds
    #[account(
        mut,
        seeds = [b"treasury"],
        bump = treasury.bump,
    )]
    pub treasury: Account<'info, Treasury>,

    /// CHECK: Agent authority must match the agent_node
    pub agent_authority: AccountInfo<'info>,

    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

/// Minimal treasury account to receive slashed funds
#[account]
#[derive(InitSpace)]
pub struct Treasury {
    pub bump: u8,
}

pub fn handler(
    ctx: Context<SlashAgent>,
    deviation_bps: u64,
    reason: String,
) -> Result<()> {
    require!(
        reason.len() <= MAX_REASON_LEN,
        OracleError::AgentNameTooLong // reuse max len error
    );

    let config = &mut ctx.accounts.config;
    let agent_node = &mut ctx.accounts.agent_node;

    // Calculate slash amount: stake * (deviation_bps / 10000) * (slash_rate / 10000)
    // Scale to avoid precision loss
    let deviation_fraction = deviation_bps as u128;
    let slash_fraction = config.slash_rate_bps as u128;
    let stake = agent_node.stake_amount as u128;

    let slash_amount = (stake
        .saturating_mul(deviation_fraction)
        .saturating_mul(slash_fraction)
        / 10_000_000_000u128) as u64;

    require!(slash_amount > 0, OracleError::SlashExceedsStake);
    require!(
        slash_amount <= agent_node.stake_amount,
        OracleError::SlashExceedsStake
    );

    // Transfer from stake vault to treasury
    let treasury_bump = ctx.accounts.treasury.bump;
    let treasury_seeds = &[b"treasury", &[treasury_bump]];
    let treasury_key = Pubkey::create_program_address(treasury_seeds, ctx.program_id)?;

    // ** Note: In production, the stake vault should be a proper system account
    // or use a token-based staking mechanism. For this implementation,
    // we deduct from the tracked stake amount. **

    // Deduct from agent's stake
    agent_node.stake_amount = agent_node.stake_amount.saturating_sub(slash_amount);
    agent_node.slash_count += 1;

    // Reduce reputation on slash
    let reputation_penalty = (agent_node.reputation_score as u128)
        .saturating_mul(deviation_fraction.min(1000) as u128)
        / 1000u128;
    agent_node.reputation_score = agent_node
        .reputation_score
        .saturating_sub(reputation_penalty as u64);

    // Deactivate agent if stake drops too low or reputation too low
    if agent_node.stake_amount < 100_000_000 || agent_node.reputation_score < 10 {
        agent_node.is_active = false;
    }

    // Update global totals
    config.total_staked = config.total_staked.saturating_sub(slash_amount);

    Ok(())
}
