//! # SwarmFi Reputation Registry — Custom Error Type

use cosmwasm_std::StdError;
use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum ContractError {
    #[error("{0}")]
    Std(#[from] StdError),

    #[error("Unauthorized: sender is not {role}")]
    Unauthorized { role: String },

    #[error("Badge not found: {id}")]
    BadgeNotFound { id: u64 },

    #[error("Agent not found: {address}")]
    AgentNotFound { address: String },

    #[error("User not found: {address}")]
    UserNotFound { address: String },

    #[error("Invalid tier: {tier}")]
    InvalidTier { tier: String },

    #[error("Accuracy delta would underflow below zero")]
    AccuracyUnderflow {},
}
