//! # Initialize Oracle Config

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::OracleError;

#[derive(Accounts)]
#[instruction(params: OracleInitParams)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + OracleConfig::INIT_SPACE,
        seeds = [b"oracle_config"],
        bump
    )]
    pub config: Account<'info, OracleConfig>,

    #[account(
        init,
        payer = authority,
        mint::decimals = 0,
        mint::authority = config,
        seeds = [b"agent_token_mint"],
        bump
    )]
    pub agent_token_mint: Account<'info, anchor_spl::token::Mint>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub token_program: Program<'info, anchor_spl::token::Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn handler(ctx: Context<Initialize>, params: OracleInitParams) -> Result<()> {
    let config = &mut ctx.accounts.config;

    config.authority = ctx.accounts.authority.key();
    config.admin = ctx.accounts.authority.key();
    config.agent_token_mint = ctx.accounts.agent_token_mint.key();
    config.min_agents_for_consensus = params.min_agents_for_consensus;
    config.max_age_seconds = params.max_age_seconds;
    config.acceptable_deviation_bps = params.acceptable_deviation_bps;
    config.slash_rate_bps = params.slash_rate_bps;
    config.agent_count = 0;
    config.total_staked = 0;
    config.consensus_round_count = 0;
    config.signal_count = 0;
    config.bump = ctx.bumps.config;

    Ok(())
}
