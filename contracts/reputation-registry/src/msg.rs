//! # SwarmFi Reputation Registry — Message Definitions
//!
//! Messages for tracking AI agent quality and user reputation across
//! the SwarmFi ecosystem.

use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Timestamp, Uint128};

/// Instantiate the reputation registry.
#[cw_serde]
pub struct InstantiateMsg {
    /// Admin address.
    pub admin: String,
}

// ── Execute messages ──────────────────────────────────────────────

#[cw_serde]
pub enum ExecuteMsg {
    /// Record a completed task for an agent (success or failure).
    RecordAgentTask {
        agent: String,
        successful: bool,
        accuracy_delta: i64,
    },

    /// Admin manually updates an agent's reputation tier.
    UpdateAgentTier {
        agent: String,
        tier: String, // Bronze, Silver, Gold, Platinum
    },

    /// Award a badge to a user or agent.
    AwardBadge {
        recipient: String,
        badge_id: u64,
    },

    /// Record a user's prediction outcome (for user reputation tracking).
    RecordUserPrediction {
        user: String,
        correct: bool,
        volume: Uint128,
    },

    /// Admin creates a new badge definition.
    CreateBadge {
        name: String,
        description: String,
        icon: String,
    },
}

// ── Query messages ────────────────────────────────────────────────

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    #[returns(AgentReputationResponse)]
    GetAgentReputation { agent: String },

    #[returns(UserReputationResponse)]
    GetUserReputation { address: String },

    #[returns(TopAgentsResponse)]
    ListTopAgents {
        start_after: Option<u32>,
        limit: Option<u32>,
    },

    #[returns(BadgesResponse)]
    ListBadges {
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(UserBadgesResponse)]
    GetUserBadges { address: String },
}

// ── Response types ────────────────────────────────────────────────

#[cw_serde]
pub struct AgentReputationResponse {
    pub agent_address: String,
    pub total_tasks: u32,
    pub successful_tasks: u32,
    pub accuracy_score: u64,
    pub reliability_score: u64,
    pub tier: String,
    pub updated_at: Timestamp,
}

#[cw_serde]
pub struct UserReputationResponse {
    pub address: String,
    pub total_bets: u32,
    pub correct_bets: u32,
    pub volume_contributed: Uint128,
    pub badges: Vec<u64>,
    pub created_at: Timestamp,
}

#[cw_serde]
pub struct TopAgentsResponse {
    pub agents: Vec<AgentReputationResponse>,
}

#[cw_serde]
pub struct BadgeResponse {
    pub id: u64,
    pub name: String,
    pub description: String,
    pub icon: String,
}

#[cw_serde]
pub struct BadgesResponse {
    pub badges: Vec<BadgeResponse>,
}

#[cw_serde]
pub struct UserBadgesResponse {
    pub address: String,
    pub badge_ids: Vec<u64>,
}
