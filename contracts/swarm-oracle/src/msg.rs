//! # SwarmFi Oracle — Message Definitions
//!
//! Defines all Instantiate, Execute, and Query messages for the core
//! swarm-intelligence oracle engine.

use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Addr, Timestamp, Uint128};

/// Instantiate the oracle contract with governance parameters.
#[cw_serde]
pub struct InstantiateMsg {
    /// Multisig / DAO address that owns the contract.
    pub owner: String,
    /// Operator allowed to update agent reputations and config.
    pub admin: String,
    /// Minimum number of unique agents whose prices must land within
    /// `acceptable_deviation_bps` before a consensus price is emitted.
    pub min_agents_for_consensus: u32,
    /// Max age (in seconds) of a price submission that still counts
    /// toward the current consensus round.
    pub max_age_seconds: u64,
    /// Acceptable price deviation in basis-points (1 bp = 0.01 %).
    pub acceptable_deviation_bps: u64,
}

// ── Execute messages ──────────────────────────────────────────────

#[cw_serde]
pub enum ExecuteMsg {
    /// Register a new AI agent in the oracle.
    RegisterAgent {
        name: String,
        agent_type: String,
    },

    /// Agent submits a price for an asset pair.
    SubmitPrice {
        asset_pair: String,
        price: Uint128,
        confidence: u8, // 0–255
    },

    /// Agent deposits a stigmergy signal (coordination hint for other agents).
    SubmitStigmergySignal {
        signal_type: String,
        data_hash: String,
        strength: Uint128,
        decay_rate: u64, // per-second decay numerator (basis-point style)
    },

    /// Admin updates an agent's reputation score.
    UpdateAgentReputation {
        agent: String,
        reputation_delta: i64,
        accuracy_delta: i64,
    },

    /// Owner updates global configuration.
    UpdateConfig {
        admin: Option<String>,
        min_agents_for_consensus: Option<u32>,
        max_age_seconds: Option<u64>,
        acceptable_deviation_bps: Option<u64>,
    },
}

// ── Query messages ────────────────────────────────────────────────

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    /// Latest price submitted for an asset pair (may not be consensus).
    #[returns(PriceFeedResponse)]
    GetPrice { asset_pair: String },

    /// Metadata for a registered agent.
    #[returns(AgentResponse)]
    GetAgent { address: String },

    /// Paginated list of all registered agents.
    #[returns(AgentsResponse)]
    ListAgents {
        start_after: Option<String>,
        limit: Option<u32>,
    },

    /// Weighted-median consensus price for an asset pair.
    #[returns(ConsensusPriceResponse)]
    GetConsensusPrice { asset_pair: String },

    /// Active stigmergy signals, optionally filtered by type.
    #[returns(StigmergySignalsResponse)]
    GetStigmergySignals {
        signal_type: Option<String>,
        start_after: Option<u64>,
        limit: Option<u32>,
    },
}

// ── Response types ────────────────────────────────────────────────

#[cw_serde]
pub struct PriceFeedResponse {
    pub asset_pair: String,
    pub price: Uint128,
    pub confidence: u8,
    pub submitted_by: String,
    pub submitted_at: Timestamp,
    pub consensus_weight: Uint128,
    pub agent_signatures: Vec<String>,
}

#[cw_serde]
pub struct AgentResponse {
    pub address: String,
    pub name: String,
    pub agent_type: String,
    pub reputation_score: u64,
    pub total_submissions: u64,
    pub accuracy_score: u64,
    pub is_active: bool,
    pub registered_at: Timestamp,
}

#[cw_serde]
pub struct AgentsResponse {
    pub agents: Vec<AgentResponse>,
}

#[cw_serde]
pub struct ConsensusPriceResponse {
    pub asset_pair: String,
    pub price: Uint128,
    pub agent_count: u32,
    pub computed_at: Timestamp,
    pub confidence: u8,
}

#[cw_serde]
pub struct StigmergySignalsResponse {
    pub signals: Vec<StigmergySignalResponse>,
}

#[cw_serde]
pub struct StigmergySignalResponse {
    pub signal_type: String,
    pub from_agent: String,
    pub data_hash: String,
    pub strength: Uint128,
    pub deposited_at: Timestamp,
    pub decay_rate: u64,
}
