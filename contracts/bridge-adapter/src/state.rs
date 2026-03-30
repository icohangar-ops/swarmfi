//! # SwarmFi Bridge Adapter — State

use cosmwasm_std::{Addr, Timestamp, Uint128};
use cw_storage_plus::{Item, Map};
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

// ── Config ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct BridgeConfig {
    pub admin: Addr,
    pub fee_rate: u64,
    pub min_transfer: Uint128,
}

pub const CONFIG: Item<BridgeConfig> = Item::new("bridge_config");

// ── Allowed assets ────────────────────────────────────────────────

pub const ALLOWED_ASSETS: Map<&str, bool> = Map::new("allowed_assets");

// ── Transfer records ──────────────────────────────────────────────

/// Transfer status lifecycle.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
#[serde(rename_all = "snake_case")]
pub enum TransferStatus {
    Pending,
    Completed,
    Failed,
}

impl TransferStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            TransferStatus::Pending => "pending",
            TransferStatus::Completed => "completed",
            TransferStatus::Failed => "failed",
        }
    }

    pub fn from_string(s: &str) -> Self {
        match s {
            "completed" => TransferStatus::Completed,
            "failed" => TransferStatus::Failed,
            _ => TransferStatus::Pending,
        }
    }
}

/// A single cross-chain transfer record.
#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq, JsonSchema)]
pub struct TransferRecord {
    pub id: u64,
    pub sender: Addr,
    pub recipient: String,
    pub asset: String,
    pub amount: Uint128,
    pub fee: Uint128,
    pub source_chain: String,
    pub dest_chain: String,
    pub status: TransferStatus,
    pub created_at: Timestamp,
    pub completed_at: Option<Timestamp>,
}

pub const TRANSFER_COUNT: Item<u64> = Item::new("transfer_count");
pub const TRANSFERS: Map<u64, TransferRecord> = Map::new("transfers");

// ── Sender → transfer ids (for enumeration) ───────────────────────

pub const SENDER_TRANSFERS: Map<&Addr, Vec<u64>> = Map::new("sender_transfers");
