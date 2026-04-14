//! # Withdraw from Vault

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::VaultError;

#[derive(Accounts)]
pub struct WithdrawVault<'info> {
    #[account(
        seeds = [b"vault_config"],
        bump = config.bump,
    )]
    pub config: Account<'info, VaultConfig>,

    #[account(
        mut,
        seeds = [b"vault", vault.id.to_le_bytes().as_ref()],
        bump = vault.bump,
    )]
    pub vault: Account<'info, Vault>,

    #[account(
        mut,
        seeds = [
            b"vault_deposit",
            vault.id.to_le_bytes().as_ref(),
            depositor.key().as_ref(),
        ],
        bump = deposit.bump,
        constraint = deposit.shares >= share_amount @ VaultError::InsufficientShares,
    )]
    pub deposit: Account<'info, VaultDeposit>,

    /// CHECK: PDA holding vault funds
    #[account(
        mut,
        seeds = [b"vault_funds", vault.id.to_le_bytes().as_ref()],
        bump
    )]
    pub vault_funds: SystemAccount<'info>,

    #[account(mut)]
    pub depositor: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<WithdrawVault>, share_amount: u64) -> Result<()> {
    require!(share_amount > 0, VaultError::InsufficientShares);

    let vault = &mut ctx.accounts.vault;
    let deposit_record = &mut ctx.accounts.deposit;
    let clock = Clock::get()?;

    // Calculate withdrawal value: proportional to share fraction
    let withdraw_value = if vault.total_shares == 0 {
        0
    } else {
        ((share_amount as u128)
            .saturating_mul(vault.total_value as u128)
            / vault.total_shares as u128) as u64
    };

    require!(withdraw_value > 0, VaultError::InsufficientFunds);

    // Apply protocol fee
    let fee = ((withdraw_value as u128) * ctx.accounts.config.fee_rate_bps as u128 / 10_000u128) as u64;
    let net_withdraw = withdraw_value.saturating_sub(fee);

    // Deduct from vault
    vault.total_shares = vault.total_shares.saturating_sub(share_amount);
    vault.total_value = vault.total_value.saturating_sub(withdraw_value);

    // Deduct SOL from asset allocations
    for asset in vault.assets.iter_mut() {
        if asset.symbol == "SOL" {
            let asset_withdraw = if vault.total_value == 0 {
                asset.amount
            } else {
                ((share_amount as u128)
                    .saturating_mul(asset.amount as u128)
                    / (vault.total_shares + share_amount) as u128) as u64
            };
            asset.amount = asset.amount.saturating_sub(asset_withdraw);
            break;
        }
    }

    // Remove zero-balance assets
    vault.assets.retain(|a| a.amount > 0);

    // Update deposit record
    deposit_record.shares = deposit_record.shares.saturating_sub(share_amount);
    deposit_record.amount = deposit_record.amount.saturating_sub(withdraw_value);

    // Record performance
    vault.performance_history.push(clock.unix_timestamp);
    vault.performance_history.push(vault.total_value as i64);

    // Transfer SOL from vault funds to depositor
    let vault_lamports = ctx.accounts.vault_funds.lamports();
    let actual_withdraw = net_withdraw.min(vault_lamports);

    if actual_withdraw > 0 {
        **ctx.accounts.vault_funds.try_borrow_mut_lamports()? -= actual_withdraw;
        **ctx.accounts.depositor.try_borrow_mut_lamports()? += actual_withdraw;
    }

    Ok(())
}
