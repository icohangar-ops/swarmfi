//! # SwarmFi Oracle — Error Definitions

use anchor_lang::prelude::*;

#[error_code]
pub enum OracleError {
    #[msg("Unauthorized: sender does not have the required role")]
    Unauthorized,

    #[msg("Agent is already registered")]
    AgentAlreadyRegistered,

    #[msg("Agent not found")]
    AgentNotFound,

    #[msg("Agent is inactive")]
    AgentInactive,

    #[msg("Price cannot be zero")]
    ZeroPrice,

    #[msg("Invalid confidence value: must be between 1-255")]
    InvalidConfidence,

    #[msg("Signal strength cannot be zero")]
    ZeroSignalStrength,

    #[msg("Not enough agents for consensus")]
    InsufficientAgents,

    #[msg("Consensus round already exists for this epoch")]
    ConsensusAlreadyExists,

    #[msg("Invalid deviation basis points")]
    InvalidDeviationBps,

    #[msg("Agent stake is insufficient")]
    InsufficientStake,

    #[msg("Oracle is already initialized")]
    AlreadyInitialized,

    #[msg("Invalid agent type")]
    InvalidAgentType,

    #[msg("Math overflow in consensus calculation")]
    MathOverflow,

    #[msg("Reputation score would underflow below zero")]
    ReputationUnderflow,

    #[msg("Asset pair string is too long (max 32 bytes)")]
    AssetPairTooLong,

    #[msg("Agent name string is too long (max 32 bytes)")]
    AgentNameTooLong,

    #[msg("Slash amount exceeds stake")]
    SlashExceedsStake,
}
