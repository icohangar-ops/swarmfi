//! # SwarmFi Prediction Market — Custom Error Type

use cosmwasm_std::StdError;
use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum ContractError {
    #[error("{0}")]
    Std(#[from] StdError),

    #[error("Unauthorized: sender is not {role}")]
    Unauthorized { role: String },

    #[error("Market not found: {id}")]
    MarketNotFound { id: u64 },

    #[error("Market is not active")]
    MarketNotActive {},

    #[error("Market has already ended")]
    MarketEnded {},

    #[error("Market already resolved")]
    MarketAlreadyResolved {},

    #[error("Market already cancelled")]
    MarketAlreadyCancelled {},

    #[error("Invalid outcome: {outcome}")]
    InvalidOutcome { outcome: String },

    #[error("Amount cannot be zero")]
    ZeroAmount {},

    #[error("Insufficient funds sent")]
    InsufficientFunds {},

    #[error("Insufficient position balance")]
    InsufficientPosition {},

    #[error("Slippage tolerance exceeded: price would be {actual}")]
    SlippageExceeded { actual: String },

    #[error("Maximum number of active markets reached")]
    MaxMarketsReached {},

    #[error("Market must have at least 2 outcomes")]
    TooFewOutcomes {},

    #[error("End time must be in the future")]
    InvalidEndTime {},
}
