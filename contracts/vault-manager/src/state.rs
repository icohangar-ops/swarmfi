//! # SwarmFi Vault Manager — State

use cosmwasm_std::{Addr, Coin, Timestamp, Uint128};
use cw_storage_plus::{Item, Map};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── Config ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Config {
    pub admin: Addr,
    pub fee_rate_bps: u64,
}

pub const CONFIG: Item<Config> = Item::new("config");

// ── Whitelisted agents ────────────────────────────────────────────

pub const WHITELISTED_AGENTS: Map<&Addr, bool> = Map::new("whitelisted_agents");

// ── Vault ─────────────────────────────────────────────────────────

/// A single performance history data-point.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct PerformancePoint {
    pub timestamp: Timestamp,
    pub value: Uint128,
}

/// A vault that holds assets and is rebalanced by AI agents.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct Vault {
    pub id: u64,
    pub name: String,
    pub strategy_type: String,
    pub owner: Addr,
    /// Asset allocations stored as denom → amount.
    pub assets: Vec<Coin>,
    /// Total notional value of all assets.
    pub total_value: Uint128,
    /// Total outstanding vault shares.
    pub total_shares: Uint128,
    pub performance_history: Vec<PerformancePoint>,
    pub risk_score: u8,
    pub agent_count: u32,
    pub is_active: bool,
    pub created_at: Timestamp,
}

pub const VAULT_COUNT: Item<u64> = Item::new("vault_count");
pub const VAULTS: Map<u64, Vault> = Map::new("vaults");

// ── Vault Deposits ────────────────────────────────────────────────

/// Record of a single deposit into a vault.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct VaultDeposit {
    pub depositor: Addr,
    pub vault_id: u64,
    pub amount: Uint128,
    pub deposited_at: Timestamp,
    pub shares: Uint128,
}

/// Primary key: `(vault_id, depositor)`.
pub const DEPOSITS: Map<(&u64, &Addr), VaultDeposit> = Map::new("deposits");

// ── User → list of vault ids they've deposited into ──────────────

/// Tracks which vaults a user has deposits in (for enumeration).
/// Key: `depositor`, value: `Vec<vault_id>`.
pub const USER_VAULTS: Map<&Addr, Vec<u64>> = Map::new("user_vaults");

// ── Rebalance events ──────────────────────────────────────────────

/// A historical record of a vault rebalance event.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct RebalanceEvent {
    pub id: u64,
    pub vault_id: u64,
    pub from_asset: String,
    pub to_asset: String,
    pub amount: Uint128,
    pub triggered_by: Addr,
    pub reason: String,
    pub executed_at: Timestamp,
}

pub const REBALANCE_COUNT: Item<u64> = Item::new("rebalance_count");
pub const REBALANCE_EVENTS: Map<u64, RebalanceEvent> = Map::new("rebalance_events");
