//! # Resolve Market
//!
//! Resolve a prediction market after end_time using oracle data.
//! The admin (or oracle via CPI) sets the winning outcome.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::MarketError;

#[derive(Accounts)]
#[instruction(winning_outcome: String)]
pub struct ResolveMarket<'info> {
    #[account(
        seeds = [b"market_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ MarketError::Unauthorized,
    )]
    pub config: Account<'info, MarketConfig>,

    #[account(
        mut,
        seeds = [b"market", market.id.to_le_bytes().as_ref()],
        bump = market.bump,
        constraint = market.status == MarketStatus::Active @ MarketError::MarketAlreadyResolved,
    )]
    pub market: Account<'info, Market>,

    #[account(
        init,
        payer = authority,
        space = 8 + Resolution::INIT_SPACE,
        seeds = [b"resolution", market.id.to_le_bytes().as_ref()],
        bump
    )]
    pub resolution: Account<'info, Resolution>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<ResolveMarket>,
    winning_outcome: String,
) -> Result<()> {
    require!(winning_outcome.len() <= MAX_OUTCOME_LEN, MarketError::OutcomeTooLong);

    let market = &mut ctx.accounts.market;
    let resolution = &mut ctx.accounts.resolution;
    let clock = Clock::get()?;

    // Verify market has ended
    require!(clock.unix_timestamp >= market.end_time, MarketError::MarketEnded);

    // Verify winning outcome is valid
    require!(
        market.outcomes.contains(&winning_outcome),
        MarketError::InvalidOutcome
    );

    // Update market status
    market.status = MarketStatus::Resolved;
    market.winning_outcome = winning_outcome.clone();
    market.resolved_at = clock.unix_timestamp;

    // Create resolution record
    resolution.market_id = market.id;
    resolution.winning_outcome = winning_outcome;
    resolution.oracle_price = 0; // Set via CPI from oracle in production
    resolution.total_pool = market.liquidity;
    resolution.winning_pool = 0; // Computed during claim
    resolution.resolved_at = clock.unix_timestamp;
    resolution.resolver = ctx.accounts.authority.key();
    resolution.bump = ctx.bumps.resolution;

    Ok(())
}
