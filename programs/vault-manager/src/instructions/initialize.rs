//! # Initialize Vault Manager

use anchor_lang::prelude::*;
use crate::state::*;

#[derive(Accounts)]
pub struct InitializeVaultManager<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + VaultConfig::INIT_SPACE,
        seeds = [b"vault_config"],
        bump
    )]
    pub config: Account<'info, VaultConfig>,

    #[account(mut)]
    pub admin: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<InitializeVaultManager>, fee_rate_bps: u64) -> Result<()> {
    let config = &mut ctx.accounts.config;
    config.admin = ctx.accounts.admin.key();
    config.fee_rate_bps = fee_rate_bps;
    config.vault_count = 0;
    config.rebalance_count = 0;
    config.bump = ctx.bumps.config;

    Ok(())
}
