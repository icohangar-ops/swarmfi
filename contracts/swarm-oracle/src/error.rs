//! # SwarmFi Oracle — Custom Error Type

use cosmwasm_std::StdError;
use thiserror::Error;

#[derive(Error, Debug, PartialEq, Eq)]
pub enum ContractError {
    #[error("{0}")]
    Std(#[from] StdError),

    #[error("Unauthorized: sender is not {role}")]
    Unauthorized { role: String },

    #[error("Agent already registered: {address}")]
    AgentAlreadyRegistered { address: String },

    #[error("Agent not found: {address}")]
    AgentNotFound { address: String },

    #[error("Agent is inactive")]
    AgentInactive {},

    #[error("Invalid confidence value: must be 1–255")]
    InvalidConfidence {},

    #[error("Price cannot be zero")]
    ZeroPrice {},

    #[error("Signal strength cannot be zero")]
    ZeroSignalStrength {},

    #[error("Reputation score would underflow below zero")]
    ReputationUnderflow {},
}
