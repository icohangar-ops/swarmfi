//! # Reputation Registry — State Definitions

use anchor_lang::prelude::*;
use anchor_lang::solana_program::pubkey::Pubkey;

pub const MAX_BADGE_NAME_LEN: usize = 64;
pub const MAX_BADGE_DESC_LEN: usize = 256;
pub const MAX_BADGE_URI_LEN: usize = 256;
pub const MAX_BADGES: usize = 20;

/// Reputation tier thresholds:
/// - Bronze:   accuracy_score < 500
/// - Silver:   500 ≤ accuracy_score < 750
/// - Gold:     750 ≤ accuracy_score < 900
/// - Platinum: accuracy_score ≥ 900
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Eq, InitSpace)]
pub enum ReputationTier {
    Bronze,
    Silver,
    Gold,
    Platinum,
}

impl ReputationTier {
    pub fn from_score(score: u64) -> ReputationTier {
        if score >= 900 {
            ReputationTier::Platinum
        } else if score >= 750 {
            ReputationTier::Gold
        } else if score >= 500 {
            ReputationTier::Silver
        } else {
            ReputationTier::Bronze
        }
    }

    pub fn weight_multiplier(&self) -> u64 {
        match self {
            ReputationTier::Bronze => 100,
            ReputationTier::Silver => 200,
            ReputationTier::Gold => 400,
            ReputationTier::Platinum => 800,
        }
    }
}

/// Global registry configuration.
#[account]
#[derive(InitSpace)]
pub struct RegistryConfig {
    /// Protocol admin
    pub admin: Pubkey,
    /// Total agents tracked
    pub agent_count: u32,
    /// Total users tracked
    pub user_count: u32,
    /// Badge counter
    pub badge_count: u64,
    /// Bump seed
    pub bump: u8,
}

/// An AI agent's reputation record.
#[account]
#[derive(InitSpace)]
pub struct AgentReputation {
    /// Agent's wallet/public key
    pub agent: Pubkey,
    /// Total tasks completed (oracle submissions, predictions)
    pub total_tasks: u32,
    /// Successful tasks count
    pub successful_tasks: u32,
    /// Accuracy score (0–1000)
    pub accuracy_score: u64,
    /// Reliability score (percentage * 100, e.g. 8500 = 85.00%)
    pub reliability_score: u64,
    /// Current tier based on accuracy
    pub tier: ReputationTier,
    /// Last update timestamp
    pub updated_at: i64,
    /// Bump seed
    pub bump: u8,
}

/// A user's reputation record (for prediction market participation).
#[account]
#[derive(InitSpace)]
pub struct UserReputation {
    /// User's wallet/public key
    pub user: Pubkey,
    /// Total predictions made
    pub total_bets: u32,
    /// Correct predictions count
    pub correct_bets: u32,
    /// Total volume wagered (in lamports)
    pub volume_contributed: u64,
    /// Earned badge IDs
    #[max_len(MAX_BADGES)]
    pub badges: Vec<u64>,
    /// Registration timestamp
    pub created_at: i64,
    /// Bump seed
    pub bump: u8,
}

/// A badge definition.
#[account]
#[derive(InitSpace)]
pub struct Badge {
    /// Badge ID (auto-incrementing)
    pub id: u64,
    /// Badge name
    #[max_len(MAX_BADGE_NAME_LEN)]
    pub name: String,
    /// Badge description
    #[max_len(MAX_BADGE_DESC_LEN)]
    pub description: String,
    /// URI for badge icon/metadata (on-chain or IPFS)
    #[max_len(MAX_BADGE_URI_LEN)]
    pub badge_uri: String,
    /// Bump seed
    pub bump: u8,
}
