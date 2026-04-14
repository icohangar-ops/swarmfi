//! # Create Market
//!
//! Create a new prediction market with initial liquidity deposit.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::MarketError;

#[derive(Accounts)]
#[instruction(question: String, description: String, outcomes: Vec<String>, end_time: i64)]
pub struct CreateMarket<'info> {
    #[account(
        mut,
        seeds = [b"market_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, MarketConfig>,

    #[account(
        init,
        payer = creator,
        space = 8 + Market::INIT_SPACE,
        seeds = [b"market", config.market_count.to_le_bytes().as_ref()],
        bump
    )]
    pub market: Account<'info, Market>,

    /// CHECK: Treasury PDA for protocol fees
    #[account(
        mut,
        seeds = [b"market_treasury"],
        bump
    )]
    pub treasury: AccountInfo<'info>,

    #[account(mut)]
    pub creator: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<CreateMarket>,
    question: String,
    description: String,
    outcomes: Vec<String>,
    end_time: i64,
) -> Result<()> {
    require!(outcomes.len() >= 2, MarketError::TooFewOutcomes);
    require!(outcomes.len() <= MAX_OUTCOMES, MarketError::TooManyMarkets);
    require!(question.len() <= MAX_QUESTION_LEN, MarketError::QuestionTooLong);
    require!(description.len() <= MAX_DESCRIPTION_LEN, MarketError::DescriptionTooLong);

    for outcome in &outcomes {
        require!(outcome.len() <= MAX_OUTCOME_LEN, MarketError::OutcomeTooLong);
    }

    let clock = Clock::get()?;
    require!(end_time > clock.unix_timestamp, MarketError::InvalidEndTime);

    let config = &mut ctx.accounts.config;
    let market = &mut ctx.accounts.market;

    let market_id = config.market_count;

    market.id = market_id;
    market.creator = ctx.accounts.creator.key();
    market.question = question;
    market.description = description;
    market.outcomes = outcomes;
    market.end_time = end_time;
    market.total_volume = 0;
    market.liquidity = 0;
    market.status = MarketStatus::Active;
    market.winning_outcome = String::new();
    market.resolved_at = 0;
    market.oracle_program = Pubkey::default();
    market.bump = ctx.bumps.market;

    config.market_count += 1;

    Ok(())
}
