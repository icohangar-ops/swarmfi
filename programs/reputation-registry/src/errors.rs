//! # Reputation Registry — Error Definitions

use anchor_lang::prelude::*;

#[error_code]
pub enum ReputationError {
    #[msg("Unauthorized: sender is not admin")]
    Unauthorized,

    #[msg("Agent not found")]
    AgentNotFound,

    #[msg("User not found")]
    UserNotFound,

    #[msg("Badge not found")]
    BadgeNotFound,

    #[msg("Invalid tier")]
    InvalidTier,

    #[msg("Accuracy delta would underflow below zero")]
    AccuracyUnderflow,

    #[msg("Badge name too long")]
    BadgeNameTooLong,

    #[msg("Badge description too long")]
    BadgeDescriptionTooLong,

    #[msg("Badge URI too long")]
    BadgeUriTooLong,

    #[msg("Already initialized")]
    AlreadyInitialized,
}
