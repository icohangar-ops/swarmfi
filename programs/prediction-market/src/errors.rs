//! # Prediction Market — Error Definitions

use anchor_lang::prelude::*;

#[error_code]
pub enum MarketError {
    #[msg("Unauthorized: sender is not admin")]
    Unauthorized,

    #[msg("Market not found")]
    MarketNotFound,

    #[msg("Market is not active")]
    MarketNotActive,

    #[msg("Market has already ended")]
    MarketEnded,

    #[msg("Market already resolved")]
    MarketAlreadyResolved,

    #[msg("Market already cancelled")]
    MarketAlreadyCancelled,

    #[msg("Invalid outcome")]
    InvalidOutcome,

    #[msg("Amount cannot be zero")]
    ZeroAmount,

    #[msg("Insufficient funds sent")]
    InsufficientFunds,

    #[msg("Insufficient position balance")]
    InsufficientPosition,

    #[msg("Slippage tolerance exceeded")]
    SlippageExceeded,

    #[msg("Maximum number of active markets reached")]
    MaxMarketsReached,

    #[msg("Market must have at least 2 outcomes")]
    TooFewOutcomes,

    #[msg("End time must be in the future")]
    InvalidEndTime,

    #[msg("Question string too long (max 256 bytes)")]
    QuestionTooLong,

    #[msg("Description string too long (max 512 bytes)")]
    DescriptionTooLong,

    #[msg("Outcome string too long (max 64 bytes)")]
    OutcomeTooLong,

    #[msg("Market already initialized")]
    AlreadyInitialized,

    #[msg("No winnings to claim")]
    NoWinnings,

    #[msg("Math overflow")]
    MathOverflow,
}
