//! # SwarmFi Oracle — State
//!
//! On-chain state structures and storage layout.

use cosmwasm_std::{Addr, Timestamp, Uint128};
use cw_storage_plus::{Index, IndexList, IndexedMap, Item, Map};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── Top-level config ──────────────────────────────────────────────

/// Global configuration stored at a fixed key.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Config {
    pub owner: Addr,
    pub admin: Addr,
    pub min_agents_for_consensus: u32,
    pub max_age_seconds: u64,
    pub acceptable_deviation_bps: u64,
}

pub const CONFIG: Item<Config> = Item::new("config");

// ── Agents ────────────────────────────────────────────────────────

/// A registered AI oracle agent.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Agent {
    pub address: Addr,
    pub name: String,
    pub agent_type: String,
    pub reputation_score: u64,
    pub total_submissions: u64,
    pub accuracy_score: u64,
    pub is_active: bool,
    pub registered_at: Timestamp,
}

// Secondary index helpers so we can iterate by name.
pub struct AgentIndexes<'a> {
    pub name: Index<'a, Agent, String>,
}

impl<'a> IndexList<Agent> for AgentIndexes<'a> {
    fn get_indexes(&self) -> Box<dyn Iterator<Item = &'a dyn Index<Agent>> + '_> {
        Box::new(vec![&self.name as &dyn Index<Agent>].into_iter())
    }
}

pub fn agents<'a>() -> IndexedMap<'a, &'a Addr, Agent, AgentIndexes<'a>> {
    let indexes = AgentIndexes {
        name: Index::new(|a| a.name.clone(), "agents__name"),
    };
    IndexedMap::new("agents", indexes)
}

// ── Price feeds ───────────────────────────────────────────────────

/// A single price submission from an agent.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct PriceFeed {
    pub asset_pair: String,
    pub price: Uint128,
    pub confidence: u8,
    pub submitted_by: Addr,
    pub submitted_at: Timestamp,
    pub consensus_weight: Uint128,
    pub agent_signatures: Vec<String>,
}

/// Primary key: `(asset_pair, agent_address)`.
/// This lets us look up the latest submission for any agent on any pair.
pub const PRICE_FEEDS: Map<(&str, &Addr), PriceFeed> = Map::new("price_feeds");

// ── Consensus prices ──────────────────────────────────────────────

/// The latest consensus price for each asset pair.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct ConsensusPrice {
    pub asset_pair: String,
    pub price: Uint128,
    pub agent_count: u32,
    pub computed_at: Timestamp,
    pub confidence: u8,
}

pub const CONSENSUS_PRICES: Map<&str, ConsensusPrice> = Map::new("consensus_prices");

// ── Stigmergy signals ─────────────────────────────────────────────

/// A coordination signal deposited by an agent (ant-colony inspired).
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct StigmergySignal {
    pub signal_type: String,
    pub from_agent: Addr,
    pub data_hash: String,
    pub strength: Uint128,
    pub deposited_at: Timestamp,
    pub decay_rate: u64,
}

/// Auto-incrementing ID counter for stigmergy signals.
pub const SIGNAL_COUNTER: Item<u64> = Item::new("signal_counter");

/// Primary key: signal id (u64).
pub const STIGMERGY_SIGNALS: Map<u64, StigmergySignal> = Map::new("stigmergy_signals");
