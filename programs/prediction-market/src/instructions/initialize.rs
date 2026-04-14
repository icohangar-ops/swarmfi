//! # Initialize Market Config

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::MarketError;

#[derive(Accounts)]
pub struct InitializeMarket<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + MarketConfig::INIT_SPACE,
        seeds = [b"market_config"],
        bump
    )]
    pub config: Account<'info, MarketConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<InitializeMarket>,
    fee_rate_bps: u64,
    max_markets: u32,
) -> Result<()> {
    let config = &mut ctx.accounts.config;
    config.admin = ctx.accounts.admin.key();
    config.fee_rate_bps = fee_rate_bps;
    config.max_markets = max_markets;
    config.market_count = 0;
    config.prediction_count = 0;
    config.bump = ctx.bumps.config;

    Ok(())
}
