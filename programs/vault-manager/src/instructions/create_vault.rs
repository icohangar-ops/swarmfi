//! # Create Vault

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::VaultError;

#[derive(Accounts)]
#[instruction(name: String, strategy_type: VaultStrategy)]
pub struct CreateVault<'info> {
    #[account(
        mut,
        seeds = [b"vault_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, VaultConfig>,

    #[account(
        init,
        payer = owner,
        space = 8 + Vault::INIT_SPACE,
        seeds = [b"vault", config.vault_count.to_le_bytes().as_ref()],
        bump
    )]
    pub vault: Account<'info, Vault>,

    /// CHECK: Vault PDA to hold deposited funds
    #[account(
        mut,
        seeds = [b"vault_funds", config.vault_count.to_le_bytes().as_ref()],
        bump
    )]
    pub vault_funds: SystemAccount<'info>,

    #[account(mut)]
    pub owner: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<CreateVault>,
    name: String,
    strategy_type: VaultStrategy,
) -> Result<()> {
    require!(name.len() <= MAX_VAULT_NAME_LEN, VaultError::VaultNameTooLong);

    let config = &mut ctx.accounts.config;
    let vault = &mut ctx.accounts.vault;
    let clock = Clock::get()?;

    let vault_id = config.vault_count;

    vault.id = vault_id;
    vault.name = name;
    vault.strategy_type = strategy_type;
    vault.owner = ctx.accounts.owner.key();
    vault.assets = Vec::new();
    vault.total_value = 0;
    vault.total_shares = 0;
    vault.risk_score = strategy_type.risk_score();
    vault.agent_rebalance_count = 0;
    vault.is_active = true;
    vault.created_at = clock.unix_timestamp;
    vault.last_rebalance_at = 0;
    vault.performance_history = Vec::new();
    vault.bump = ctx.bumps.vault;

    config.vault_count += 1;

    Ok(())
}
