//! # SwarmFi Bridge Adapter — Message Definitions
//!
//! Messages for interfacing with Initia's Interwoven Bridge for
//! cross-chain asset transfers.

use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Timestamp, Uint128};

/// Instantiate the bridge-adapter contract.
#[cw_serde]
pub struct InstantiateMsg {
    /// Admin address.
    pub admin: String,
    /// Protocol fee rate in basis-points.
    pub fee_rate: u64,
    /// Minimum transfer amount.
    pub min_transfer: Uint128,
}

// ── Execute messages ──────────────────────────────────────────────

#[cw_serde]
pub enum ExecuteMsg {
    /// Initiate a cross-chain transfer. Must attach the transfer amount.
    InitiateTransfer {
        recipient: String,
        asset: String,
        amount: Uint128,
        source_chain: String,
        dest_chain: String,
    },

    /// Complete a pending transfer (called by relayer / bridge module).
    CompleteTransfer {
        transfer_id: u64,
    },

    /// Mark a transfer as failed.
    FailTransfer {
        transfer_id: u64,
    },

    /// Admin updates bridge config.
    UpdateConfig {
        admin: Option<String>,
        fee_rate: Option<u64>,
        min_transfer: Option<Uint128>,
    },

    /// Admin adds or removes an asset from the allowed list.
    SetAllowedAsset {
        asset: String,
        allowed: bool,
    },
}

// ── Query messages ────────────────────────────────────────────────

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    #[returns(TransferResponse)]
    GetTransfer { transfer_id: u64 },

    #[returns(TransfersResponse)]
    ListTransfers {
        sender: Option<String>,
        status: Option<String>,
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(ConfigResponse)]
    GetConfig,
}

// ── Response types ────────────────────────────────────────────────

#[cw_serde]
pub struct TransferResponse {
    pub id: u64,
    pub sender: String,
    pub recipient: String,
    pub asset: String,
    pub amount: Uint128,
    pub fee: Uint128,
    pub source_chain: String,
    pub dest_chain: String,
    pub status: String,
    pub created_at: Timestamp,
    pub completed_at: Option<Timestamp>,
}

#[cw_serde]
pub struct TransfersResponse {
    pub transfers: Vec<TransferResponse>,
}

#[cw_serde]
pub struct ConfigResponse {
    pub admin: String,
    pub fee_rate: u64,
    pub min_transfer: Uint128,
    pub allowed_assets: Vec<String>,
    pub transfer_count: u64,
}
