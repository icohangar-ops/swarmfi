//! # SwarmFi Vault Manager — Solana Program
//!
//! Auto-rebalancing vault management with AI swarm-driven risk signals.
//! Agents trigger rebalances based on swarm consensus risk assessments.

use anchor_lang::prelude::*;

pub mod errors;
pub mod instructions;
pub mod state;

use errors::*;
use state::*;

declare_id!("VltMgcHHAfKXkRBRyfzXhCZrN3NaE8kTGYhfPaCmjPQy");

#[program]
pub mod vault_manager {
    use super::*;

    /// Initialize the vault manager protocol.
    pub fn initialize(ctx: Context<InitializeVaultManager>, fee_rate_bps: u64) -> Result<()> {
        instructions::initialize::handler(ctx, fee_rate_bps)
    }

    /// Create a new vault with a strategy type.
    pub fn create_vault(
        ctx: Context<CreateVault>,
        name: String,
        strategy_type: VaultStrategy,
    ) -> Result<()> {
        instructions::create_vault::handler(ctx, name, strategy_type)
    }

    /// Deposit SOL into a vault and receive vault shares.
    pub fn deposit(ctx: Context<DepositVault>, amount: u64) -> Result<()> {
        instructions::deposit::handler(ctx, amount)
    }

    /// Withdraw from a vault by burning shares.
    pub fn withdraw(ctx: Context<WithdrawVault>, share_amount: u64) -> Result<()> {
        instructions::withdraw::handler(ctx, share_amount)
    }

    /// Auto-rebalance a vault based on swarm risk signals.
    pub fn rebalance(
        ctx: Context<RebalanceVault>,
        from_asset: String,
        to_asset: String,
        amount: u64,
        reason: String,
    ) -> Result<()> {
        instructions::rebalance::handler(ctx, from_asset, to_asset, amount, reason)
    }
}
