//! # Deposit into Vault

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::VaultError;

#[derive(Accounts)]
pub struct DepositVault<'info> {
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

    #[account(
        init,
        payer = depositor,
        space = 8 + VaultDeposit::INIT_SPACE,
        seeds = [
            b"vault_deposit",
            vault.id.to_le_bytes().as_ref(),
            depositor.key().as_ref(),
        ],
        bump
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

pub fn handler(ctx: Context<DepositVault>, amount: u64) -> Result<()> {
    require!(amount > 0, VaultError::InsufficientFunds);

    let vault = &mut ctx.accounts.vault;
    let deposit_record = &mut ctx.accounts.deposit;
    let clock = Clock::get()?;

    // Calculate shares: if TVL is 0, shares = amount; else proportional
    let shares = if vault.total_shares == 0 {
        amount
    } else {
        // shares = amount * total_shares / total_value
        ((amount as u128)
            .saturating_mul(vault.total_shares as u128)
            / vault.total_value as u128) as u64
    };

    // Transfer SOL from depositor to vault funds PDA
    anchor_lang::system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.depositor.to_account_info(),
                to: ctx.accounts.vault_funds.to_account_info(),
            },
        ),
        amount,
    )?;

    // Update vault totals
    vault.total_value = vault.total_value.saturating_add(amount);
    vault.total_shares = vault.total_shares.saturating_add(shares);

    // Update or create SOL asset allocation
    let mut found = false;
    for asset in vault.assets.iter_mut() {
        if asset.symbol == "SOL" {
            asset.amount = asset.amount.saturating_add(amount);
            found = true;
            break;
        }
    }
    if !found {
        vault.assets.push(AssetAllocation {
            symbol: "SOL".to_string(),
            amount,
        });
    }

    // Record performance snapshot
    vault.performance_history.push(clock.unix_timestamp);
    vault.performance_history.push(vault.total_value as i64);
    // Keep only last MAX_PERFORMANCE_POINTS entries
    let max_entries = MAX_PERFORMANCE_POINTS * 2;
    while vault.performance_history.len() > max_entries {
        vault.performance_history.remove(0);
        vault.performance_history.remove(0);
    }

    // Store deposit record
    deposit_record.depositor = ctx.accounts.depositor.key();
    deposit_record.vault_id = vault.id;
    deposit_record.amount = amount;
    deposit_record.shares = shares;
    deposit_record.deposited_at = clock.unix_timestamp;
    deposit_record.bump = ctx.bumps.deposit;

    Ok(())
}
