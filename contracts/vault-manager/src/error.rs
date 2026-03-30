//! # SwarmFi Vault Manager — Custom Error Type

use cosmwasm_std::StdError;
use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum ContractError {
    #[error("{0}")]
    Std(#[from] StdError),

    #[error("Unauthorized: sender is not {role}")]
    Unauthorized { role: String },

    #[error("Vault not found: {id}")]
    VaultNotFound { id: u64 },

    #[error("Vault is not active")]
    VaultNotActive {},

    #[error("Insufficient funds sent")]
    InsufficientFunds {},

    #[error("Insufficient share balance")]
    InsufficientShares {},

    #[error("Asset not found in vault: {asset}")]
    AssetNotFound { asset: String },

    #[error("Invalid strategy type: {strategy}")]
    InvalidStrategy { strategy: String },

    #[error("Agent not whitelisted")]
    AgentNotWhitelisted {},

    #[error("Rebalance amount exceeds from_asset balance")]
    InsufficientAssetBalance {},
}
