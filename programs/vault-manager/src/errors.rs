//! # Vault Manager — Error Definitions

use anchor_lang::prelude::*;

#[error_code]
pub enum VaultError {
    #[msg("Unauthorized: sender is not admin")]
    Unauthorized,

    #[msg("Vault not found")]
    VaultNotFound,

    #[msg("Vault is not active")]
    VaultNotActive,

    #[msg("Insufficient funds sent")]
    InsufficientFunds,

    #[msg("Insufficient share balance")]
    InsufficientShares,

    #[msg("Invalid strategy type")]
    InvalidStrategy,

    #[msg("Agent not whitelisted for rebalancing")]
    AgentNotWhitelisted,

    #[msg("Asset not found in vault")]
    AssetNotFound,

    #[msg("Insufficient asset balance for rebalance")]
    InsufficientAssetBalance,

    #[msg("Vault name too long")]
    VaultNameTooLong,

    #[msg("Reason string too long")]
    ReasonTooLong,

    #[msg("Asset string too long")]
    AssetTooLong,

    #[msg("Already initialized")]
    AlreadyInitialized,

    #[msg("Math overflow in vault calculation")]
    MathOverflow,
}
