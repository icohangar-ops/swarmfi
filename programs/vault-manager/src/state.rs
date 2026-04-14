//! # Vault Manager — State Definitions

use anchor_lang::prelude::*;
use anchor_lang::solana_program::pubkey::Pubkey;

pub const MAX_VAULT_NAME_LEN: usize = 64;
pub const MAX_REASON_LEN: usize = 128;
pub const MAX_ASSET_LEN: usize = 32;
pub const MAX_ASSETS: usize = 10;
pub const MAX_PERFORMANCE_POINTS: usize = 50;

/// Vault strategy types with different risk profiles.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq, InitSpace)]
pub enum VaultStrategy {
    /// Low risk, stable returns
    Conservative,
    /// Medium risk, balanced allocation
    Balanced,
    /// High risk, aggressive growth
    Aggressive,
}

impl VaultStrategy {
    pub fn risk_score(&self) -> u8 {
        match self {
            VaultStrategy::Conservative => 1,
            VaultStrategy::Balanced => 5,
            VaultStrategy::Aggressive => 9,
        }
    }
}

/// An individual asset allocation within a vault.
#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct AssetAllocation {
    /// Asset identifier (e.g. "SOL", "USDC", "BTC")
    #[max_len(MAX_ASSET_LEN)]
    pub symbol: String,
    /// Amount held (in lamports or smallest unit)
    pub amount: u64,
}

/// Global vault manager configuration.
#[account]
#[derive(InitSpace)]
pub struct VaultConfig {
    /// Protocol admin
    pub admin: Pubkey,
    /// Protocol fee in basis points
    pub fee_rate_bps: u64,
    /// Vault counter
    pub vault_count: u64,
    /// Rebalance counter
    pub rebalance_count: u64,
    /// Bump seed
    pub bump: u8,
}

/// A vault that holds assets and is rebalanced by AI agents.
#[account]
#[derive(InitSpace)]
pub struct Vault {
    /// Vault ID (auto-incrementing)
    pub id: u64,
    /// Human-readable name
    #[max_len(MAX_VAULT_NAME_LEN)]
    pub name: String,
    /// Investment strategy
    pub strategy_type: VaultStrategy,
    /// Vault owner/creator
    pub owner: Pubkey,
    /// Asset allocations
    #[max_len(MAX_ASSETS)]
    pub assets: Vec<AssetAllocation>,
    /// Total value in lamports
    pub total_value: u64,
    /// Total outstanding shares
    pub total_shares: u64,
    /// Risk score (1-10)
    pub risk_score: u8,
    /// Number of rebalance events triggered by agents
    pub agent_rebalance_count: u32,
    /// Whether the vault is active
    pub is_active: bool,
    /// Creation timestamp
    pub created_at: i64,
    /// Last rebalance timestamp
    pub last_rebalance_at: i64,
    /// Performance history (timestamp, value pairs)
    // Stored as a flat array: [ts0, val0, ts1, val1, ...]
    #[max_len(MAX_PERFORMANCE_POINTS * 2)]
    pub performance_history: Vec<i64>,
    /// Bump seed
    pub bump: u8,
}

/// A user's deposit record in a vault.
#[account]
#[derive(InitSpace)]
pub struct VaultDeposit {
    /// Depositor's wallet
    pub depositor: Pubkey,
    /// Vault ID
    pub vault_id: u64,
    /// Amount deposited (in lamports)
    pub amount: u64,
    /// Number of vault shares held
    pub shares: u64,
    /// Deposit timestamp
    pub deposited_at: i64,
    /// Bump seed
    pub bump: u8,
}

/// A record of a vault rebalance event.
#[account]
#[derive(InitSpace)]
pub struct RebalanceRecord {
    /// Record ID (auto-incrementing)
    pub id: u64,
    /// Vault ID
    pub vault_id: u64,
    /// Asset being decreased
    #[max_len(MAX_ASSET_LEN)]
    pub from_asset: String,
    /// Asset being increased
    #[max_len(MAX_ASSET_LEN)]
    pub to_asset: String,
    /// Amount rebalanced (in lamports)
    pub amount: u64,
    /// Agent that triggered the rebalance
    pub triggered_by: Pubkey,
    /// Human-readable reason
    #[max_len(MAX_REASON_LEN)]
    pub reason: String,
    /// Execution timestamp
    pub executed_at: i64,
    /// Bump seed
    pub bump: u8,
}

/// Whitelisted agent for rebalancing.
#[account]
#[derive(InitSpace)]
pub struct WhitelistedAgent {
    /// Agent's public key
    pub agent: Pubkey,
    /// Whether the agent is active
    pub is_active: bool,
    /// Bump seed
    pub bump: u8,
}
