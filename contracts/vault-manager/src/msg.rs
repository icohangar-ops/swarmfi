//! # SwarmFi Vault Manager — Message Definitions
//!
//! Instantiate, Execute, and Query messages for AI-agent-driven
//! auto-rebalancing DeFi vaults.

use cosmwasm_schema::{cw_serde, QueryResponses};
use cosmwasm_std::{Coin, Timestamp, Uint128};

/// Instantiate the vault-manager contract.
#[cw_serde]
pub struct InstantiateMsg {
    /// Admin address.
    pub admin: String,
    /// Protocol fee in basis-points on profits.
    pub fee_rate_bps: u64,
}

// ── Execute messages ──────────────────────────────────────────────

#[cw_serde]
pub enum ExecuteMsg {
    /// Create a new vault with a given strategy type.
    CreateVault {
        name: String,
        strategy_type: String, // Conservative, Balanced, Aggressive
    },

    /// Deposit tokens into a vault and receive shares.
    Deposit {
        vault_id: u64,
    },

    /// Withdraw tokens by burning shares.
    Withdraw {
        vault_id: u64,
        share_amount: Uint128,
    },

    /// Rebalance a vault's allocations (whitelisted agents only).
    Rebalance {
        vault_id: u64,
        from_asset: String,
        to_asset: String,
        amount: Uint128,
        reason: String,
    },

    /// Update global or vault-specific config.
    UpdateConfig {
        admin: Option<String>,
        fee_rate_bps: Option<u64>,
    },

    /// Whitelist or remove an agent address for rebalancing.
    UpdateWhitelist {
        agent: String,
        add: bool,
    },

    /// Activate / deactivate a vault.
    SetVaultActive {
        vault_id: u64,
        active: bool,
    },
}

// ── Query messages ────────────────────────────────────────────────

#[cw_serde]
#[derive(QueryResponses)]
pub enum QueryMsg {
    #[returns(VaultResponse)]
    GetVault { vault_id: u64 },

    #[returns(VaultsResponse)]
    ListVaults {
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(VaultPositionsResponse)]
    GetVaultPositions { vault_id: u64 },

    #[returns(DepositsResponse)]
    GetUserDeposits {
        owner: String,
        start_after: Option<u64>,
        limit: Option<u32>,
    },

    #[returns(RebalanceHistoryResponse)]
    GetRebalanceHistory {
        vault_id: u64,
        start_after: Option<u64>,
        limit: Option<u32>,
    },
}

// ── Response types ────────────────────────────────────────────────

#[cw_serde]
pub struct VaultResponse {
    pub id: u64,
    pub name: String,
    pub strategy_type: String,
    pub owner: String,
    pub assets: Vec<Coin>,
    pub total_value: Uint128,
    pub total_shares: Uint128,
    pub performance_history: Vec<PerformancePoint>,
    pub risk_score: u8,
    pub agent_count: u32,
    pub is_active: bool,
    pub created_at: Timestamp,
}

#[cw_serde]
pub struct PerformancePoint {
    pub timestamp: Timestamp,
    pub value: Uint128,
}

#[cw_serde]
pub struct VaultsResponse {
    pub vaults: Vec<VaultResponse>,
}

#[cw_serde]
pub struct VaultPositionsResponse {
    pub vault_id: u64,
    pub assets: Vec<Coin>,
}

#[cw_serde]
pub struct DepositResponse {
    pub depositor: String,
    pub vault_id: u64,
    pub amount: Uint128,
    pub deposited_at: Timestamp,
    pub shares: Uint128,
}

#[cw_serde]
pub struct DepositsResponse {
    pub deposits: Vec<DepositResponse>,
}

#[cw_serde]
pub struct RebalanceEventResponse {
    pub vault_id: u64,
    pub from_asset: String,
    pub to_asset: String,
    pub amount: Uint128,
    pub triggered_by: String,
    pub reason: String,
    pub executed_at: Timestamp,
}

#[cw_serde]
pub struct RebalanceHistoryResponse {
    pub events: Vec<RebalanceEventResponse>,
}
