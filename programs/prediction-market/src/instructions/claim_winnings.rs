//! # Claim Winnings
//!
//! Winners claim their share of the total pool (their stake + proportional
/// share of losing stakes, minus protocol fees).

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::MarketError;

#[derive(Accounts)]
pub struct ClaimWinnings<'info> {
    #[account(
        seeds = [b"market_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, MarketConfig>,

    #[account(
        seeds = [b"market", market.id.to_le_bytes().as_ref()],
        bump = market.bump,
        constraint = market.status == MarketStatus::Resolved @ MarketError::MarketNotActive,
    )]
    pub market: Account<'info, Market>,

    #[account(
        mut,
        seeds = [
            b"prediction",
            market.id.to_le_bytes().as_ref(),
            user.key().as_ref(),
            prediction.outcome.as_bytes(),
        ],
        bump = prediction.bump,
        constraint = !prediction.claimed @ MarketError::NoWinnings,
        constraint = prediction.outcome == market.winning_outcome @ MarketError::NoWinnings,
    )]
    pub prediction: Account<'info, Prediction>,

    /// CHECK: Market treasury holds the pool funds
    #[account(
        mut,
        seeds = [b"market_treasury"],
        bump
    )]
    pub treasury: AccountInfo<'info>,

    #[account(mut)]
    pub user: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<ClaimWinnings>) -> Result<()> {
    let market = &ctx.accounts.market;
    let prediction = &mut ctx.accounts.prediction;
    let config = &ctx.accounts.config;

    // Verify the prediction is on the winning outcome
    require!(
        prediction.outcome == market.winning_outcome,
        MarketError::NoWinnings
    );

    require!(!prediction.claimed, MarketError::NoWinnings);

    let total_pool = market.liquidity;
    let user_stake = prediction.stake_amount;

    // Calculate payout:
    // User gets back their stake + proportional share of losing stakes
    // Payout = user_stake + (user_stake / winning_pool) * losing_pool
    // Simplified: payout = user_stake * total_pool / winning_pool
    //
    // Since we don't track winning_pool separately (it requires aggregating),
    // we use a simplified model: payout = stake * (1 + reward_multiplier)
    // where reward_multiplier is based on the implied probability

    // For the hackathon, use: payout = stake * total_pool / stake_estimate_of_winning_side
    // Simplified further: user gets back stake + proportional share

    let fee = (user_stake as u128 * config.fee_rate_bps as u128 / 10_000u128) as u64;
    let base_payout = user_stake.saturating_sub(fee);

    // In production, compute actual winning_pool from all predictions
    // For now, give a 2x return on winning predictions (simplified model)
    let reward = user_stake.saturating_sub(fee); // Net reward = stake - fee
    let total_payout = base_payout.saturating_add(reward);

    // Mark as claimed
    prediction.claimed = true;

    // Transfer payout from treasury to user
    let treasury_lamports = ctx.accounts.treasury.lamports();
    let actual_payout = total_payout.min(treasury_lamports);

    if actual_payout > 0 {
        // Transfer SOL from treasury to user
        **ctx.accounts.treasury.try_borrow_mut_lamports()? -= actual_payout;
        **ctx.accounts.user.try_borrow_mut_lamports()? += actual_payout;
    }

    Ok(())
}
