//! # SwarmFi Reputation Registry — State

use cosmwasm_std::{Addr, Timestamp, Uint128};
use cw_storage_plus::{Item, Map};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── Config ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Config {
    pub admin: Addr,
}

pub const CONFIG: Item<Config> = Item::new("config");

// ── Agent Reputation ──────────────────────────────────────────────

/// Reputation tier thresholds:
/// - Bronze:   accuracy_score < 500
/// - Silver:   500 ≤ accuracy_score < 750
/// - Gold:     750 ≤ accuracy_score < 900
/// - Platinum: accuracy_score ≥ 900

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum ReputationTier {
    Bronze,
    Silver,
    Gold,
    Platinum,
}

impl ReputationTier {
    pub fn as_str(&self) -> &'static str {
        match self {
            ReputationTier::Bronze => "Bronze",
            ReputationTier::Silver => "Silver",
            ReputationTier::Gold => "Gold",
            ReputationTier::Platinum => "Platinum",
        }
    }

    /// Determine tier from an accuracy score.
    pub fn from_score(score: u64) -> Self {
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

    /// Parse from a string, falling back to Bronze.
    pub fn from_string(s: &str) -> Self {
        match s {
            "Silver" => ReputationTier::Silver,
            "Gold" => ReputationTier::Gold,
            "Platinum" => ReputationTier::Platinum,
            _ => ReputationTier::Bronze,
        }
    }
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct AgentReputation {
    pub agent_address: Addr,
    pub total_tasks: u32,
    pub successful_tasks: u32,
    pub accuracy_score: u64, // 0–1000
    pub reliability_score: u64, // percentage * 100 (e.g. 8500 = 85.00%)
    pub tier: ReputationTier,
    pub updated_at: Timestamp,
}

/// Key: agent address.
pub const AGENT_REPUTATIONS: Map<&Addr, AgentReputation> = Map::new("agent_reputations");

// ── User Reputation ───────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct UserReputation {
    pub address: Addr,
    pub total_bets: u32,
    pub correct_bets: u32,
    pub volume_contributed: Uint128,
    pub badges: Vec<u64>,
    pub created_at: Timestamp,
}

/// Key: user address.
pub const USER_REPUTATIONS: Map<&Addr, UserReputation> = Map::new("user_reputations");

// ── Badges ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Badge {
    pub id: u64,
    pub name: String,
    pub description: String,
    pub icon: String,
}

pub const BADGE_COUNT: Item<u64> = Item::new("badge_count");
pub const BADGES: Map<u64, Badge> = Map::new("badges");
