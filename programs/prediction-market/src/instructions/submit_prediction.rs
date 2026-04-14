//! # Submit Prediction
//!
//! A user stakes on an outcome in a prediction market.
//! Uses a simplified AMM model for pricing.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::MarketError;

#[derive(Accounts)]
#[instruction(outcome: String, amount: u64)]
pub struct SubmitPrediction<'info> {
    #[account(
        seeds = [b"market_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, MarketConfig>,

    #[account(
        mut,
        seeds = [b"market", market.id.to_le_bytes().as_ref()],
        bump = market.bump,
        constraint = market.status == MarketStatus::Active @ MarketError::MarketNotActive,
    )]
    pub market: Account<'info, Market>,

    #[account(
        init,
        payer = user,
        space = 8 + Prediction::INIT_SPACE,
        seeds = [
            b"prediction",
            market.id.to_le_bytes().as_ref(),
            user.key().as_ref(),
            outcome.as_bytes(),
        ],
        bump
    )]
    pub prediction: Account<'info, Prediction>,

    #[account(mut)]
    pub user: Signer<'info>,

    /// CHECK: Market treasury receives SOL from losing bets
    #[account(
        mut,
        seeds = [b"market_treasury"],
        bump
    )]
    pub treasury: AccountInfo<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<SubmitPrediction>,
    outcome: String,
    amount: u64,
) -> Result<()> {
    require!(amount > 0, MarketError::ZeroAmount);
    require!(outcome.len() <= MAX_OUTCOME_LEN, MarketError::OutcomeTooLong);

    let market = &mut ctx.accounts.market;
    let prediction = &mut ctx.accounts.prediction;
    let clock = Clock::get()?;

    // Validate outcome exists in market
    require!(
        market.outcomes.contains(&outcome),
        MarketError::InvalidOutcome
    );

    // Transfer stake from user to market treasury
    anchor_lang::system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.user.to_account_info(),
                to: ctx.accounts.treasury.clone(),
            },
        ),
        amount,
    )?;

    // Calculate implied probability and price
    // Price = total_pool / (total_pool + new_stake)
    // This gives us a simple bonding curve pricing model
    let total_pool = market.liquidity;
    let price = if total_pool == 0 {
        50_000_000 // 0.5 in 8-decimal precision (50% probability)
    } else {
        // Simplified AMM price calculation
        // Each 1 lamport of stake increases outcome probability
        // price = total_pool * 1e8 / (total_pool + amount)
        (total_pool as u128 * 100_000_000u128 / (total_pool as u128 + amount as u128)) as u64
    };

    // Store the prediction
    prediction.id = config.prediction_count;
    prediction.market_id = market.id;
    prediction.outcome = outcome;
    prediction.user = ctx.accounts.user.key();
    prediction.stake_amount = amount;
    prediction.avg_price = price;
    prediction.created_at = clock.unix_timestamp;
    prediction.claimed = false;
    prediction.bump = ctx.bumps.prediction;

    // Update market stats
    market.liquidity = market.liquidity.saturating_add(amount);
    market.total_volume = market.total_volume.saturating_add(amount);

    Ok(())
}
