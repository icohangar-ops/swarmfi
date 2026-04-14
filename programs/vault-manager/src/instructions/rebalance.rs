//! # Rebalance Vault
//!
//! Whitelisted AI agents trigger rebalances based on swarm consensus
//! risk signals. This shifts allocations between assets in the vault.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::VaultError;

#[derive(Accounts)]
pub struct RebalanceVault<'info> {
    #[account(
        seeds = [b"vault_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, VaultConfig>,

    #[account(
        mut,
        seeds = [b"vault", vault.id.to_le_bytes().as_ref()],
        bump = vault.bump,
        constraint = vault.is_active @ VaultError::VaultNotActive,
    )]
    pub vault: Account<'info, Vault>,

    /// Agent must be whitelisted to trigger rebalances
    #[account(
        seeds = [b"whitelisted_agent", agent.key().as_ref()],
        bump = whitelisted.bump,
        constraint = whitelisted.is_active @ VaultError::AgentNotWhitelisted,
    )]
    pub whitelisted: Account<'info, WhitelistedAgent>,

    #[account(
        init,
        payer = agent,
        space = 8 + RebalanceRecord::INIT_SPACE,
        seeds = [b"rebalance_record", config.rebalance_count.to_le_bytes().as_ref()],
        bump
    )]
    pub rebalance_record: Account<'info, RebalanceRecord>,

    /// CHECK: Agent triggering the rebalance (must be whitelisted)
    pub agent: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<RebalanceVault>,
    from_asset: String,
    to_asset: String,
    amount: u64,
    reason: String,
) -> Result<()> {
    require!(from_asset.len() <= MAX_ASSET_LEN, VaultError::AssetTooLong);
    require!(to_asset.len() <= MAX_ASSET_LEN, VaultError::AssetTooLong);
    require!(reason.len() <= MAX_REASON_LEN, VaultError::ReasonTooLong);
    require!(amount > 0, VaultError::InsufficientFunds);

    let config = &mut ctx.accounts.config;
    let vault = &mut ctx.accounts.vault;
    let record = &mut ctx.accounts.rebalance_record;
    let clock = Clock::get()?;

    // Find and deduct from from_asset
    let mut from_found = false;
    for asset in vault.assets.iter_mut() {
        if asset.symbol == from_asset {
            require!(asset.amount >= amount, VaultError::InsufficientAssetBalance);
            asset.amount = asset.amount.saturating_sub(amount);
            from_found = true;
            break;
        }
    }
    require!(from_found, VaultError::AssetNotFound);

    // Add to to_asset (create if not present)
    let mut to_found = false;
    for asset in vault.assets.iter_mut() {
        if asset.symbol == to_asset {
            asset.amount = asset.amount.saturating_add(amount);
            to_found = true;
            break;
        }
    }
    if !to_found {
        vault.assets.push(AssetAllocation {
            symbol: to_asset,
            amount,
        });
    }

    // Remove zero-balance assets
    vault.assets.retain(|a| a.amount > 0);

    // Update vault stats
    vault.agent_rebalance_count += 1;
    vault.last_rebalance_at = clock.unix_timestamp;

    // Record rebalance event
    record.id = config.rebalance_count;
    record.vault_id = vault.id;
    record.from_asset = from_asset;
    record.to_asset = to_asset;
    record.amount = amount;
    record.triggered_by = ctx.accounts.agent.key();
    record.reason = reason;
    record.executed_at = clock.unix_timestamp;
    record.bump = ctx.bumps.rebalance_record;

    config.rebalance_count += 1;

    // Record performance snapshot after rebalance
    vault.performance_history.push(clock.unix_timestamp);
    vault.performance_history.push(vault.total_value as i64);

    Ok(())
}
