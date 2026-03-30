//! # SwarmFi Bridge Adapter — Custom Error Type

use cosmwasm_std::StdError;
use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum ContractError {
    #[error("{0}")]
    Std(#[from] StdError),

    #[error("Unauthorized: sender is not {role}")]
    Unauthorized { role: String },

    #[error("Transfer not found: {id}")]
    TransferNotFound { id: u64 },

    #[error("Transfer already completed or failed")]
    TransferAlreadySettled {},

    #[error("Asset not allowed: {asset}")]
    AssetNotAllowed { asset: String },

    #[error("Amount below minimum transfer")]
    BelowMinimum {},

    #[error("Insufficient funds sent")]
    InsufficientFunds {},
}
