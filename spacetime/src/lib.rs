use spacetimedb::{ReducerContext, ScheduleAt, Timestamp, Table, Identity, TimeDuration};

// ─── Agent tier enum ───────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum AgentTier {
    Bronze,
    Silver,
    Gold,
    Platinum,
}

// ─── Stigmergy signal type ─────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum SignalType {
    Coordinate,
    Alert,
    Withdraw,
}

// ─── Consensus round status ────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum RoundStatus {
    Pending,
    Computing,
    Resolved,
    Failed,
}

// ─── Bridge source ─────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum BridgeSource {
    Solana,
    Spacetime,
}

// ─── Bridge tx status ──────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum BridgeTxStatus {
    Pending,
    Confirmed,
    Failed,
}

// ─── Vault strategy ────────────────────────────────────────────────────────────

#[derive(Clone, Copy, PartialEq, Eq, spacetimedb::SpacetimeType)]
pub enum VaultStrategy {
    Conservative,
    Balanced,
    Aggressive,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 1: Agent
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = agent, public)]
pub struct Agent {
    #[primary_key]
    pub id: Identity,
    pub name: String,
    pub pubkey: String,
    pub stake_amount: u64,
    pub reputation_score: f64,
    pub tier: AgentTier,
    pub is_active: bool,
    pub registered_at: Timestamp,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 2: PriceSubmission
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = price_submission, public)]
pub struct PriceSubmission {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub agent_id: Identity,
    pub asset_pair: String,
    pub price: f64,
    pub timestamp: Timestamp,
    pub stigmergy_signal: f64,
    pub weight: f64,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 3: StigmergySignal
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = stigmergy_signal, public)]
pub struct StigmergySignal {
    #[primary_key]
    #[auto_inc]
    pub signal_id: u64,
    pub agent_id: Identity,
    pub signal_type: SignalType,
    pub intensity: f64,
    pub decay_factor: f64,
    pub created_at: Timestamp,
    pub expires_at: Timestamp,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 4: ConsensusRound
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = consensus_round, public)]
pub struct ConsensusRound {
    #[primary_key]
    #[auto_inc]
    pub round_id: u64,
    pub asset_pair: String,
    pub start_time: Timestamp,
    pub end_time: Timestamp,
    pub price_submissions: Vec<u64>,
    pub weighted_median_price: f64,
    pub status: RoundStatus,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 5: MarketState
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = market_state, public)]
pub struct MarketState {
    #[primary_key]
    #[auto_inc]
    pub market_id: u64,
    pub question: String,
    pub outcomes: Vec<String>,
    pub deadline: u64,
    pub resolved: bool,
    pub winning_outcome: Option<String>,
    pub total_stake: u64,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 6: VaultState
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = vault_state, public)]
pub struct VaultState {
    #[primary_key]
    #[auto_inc]
    pub vault_id: u64,
    pub strategy: VaultStrategy,
    pub total_deposits: u64,
    pub share_price: f64,
    pub last_rebalance: u64,
}

// ═══════════════════════════════════════════════════════════════════════════════
// TABLE 7: BridgeTx
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::table(accessor = bridge_tx, public)]
pub struct BridgeTx {
    #[primary_key]
    #[auto_inc]
    pub tx_id: u64,
    pub source: BridgeSource,
    pub data_hash: String,
    pub status: BridgeTxStatus,
    pub created_at: Timestamp,
}

// ─── Helper: determine tier from stake ─────────────────────────────────────────

fn tier_from_stake(stake: u64) -> AgentTier {
    if stake >= 1_000_000_000 {
        AgentTier::Platinum
    } else if stake >= 100_000_000 {
        AgentTier::Gold
    } else if stake >= 10_000_000 {
        AgentTier::Silver
    } else {
        AgentTier::Bronze
    }
}

// ─── Helper: compute weighted median ───────────────────────────────────────────

fn compute_weighted_median(prices: &[(f64, f64)]) -> f64 {
    if prices.is_empty() {
        return 0.0;
    }
    let mut entries: Vec<(f64, f64)> = prices.to_vec();
    entries.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap_or(std::cmp::Ordering::Equal));
    let total_weight: f64 = entries.iter().map(|(_, w)| w).sum();
    let half = total_weight / 2.0;
    let mut cumulative = 0.0;
    for (price, weight) in &entries {
        cumulative += weight;
        if cumulative >= half {
            return *price;
        }
    }
    entries.last().map(|(p, _)| *p).unwrap_or(0.0)
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 1: register_agent
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn register_agent(ctx: &ReducerContext, name: String, pubkey: String, stake: u64) -> Result<(), String> {
    let id = ctx.sender();
    let now = ctx.timestamp;

    let agent = Agent {
        id,
        name,
        pubkey,
        stake_amount: stake,
        reputation_score: 0.0,
        tier: tier_from_stake(stake),
        is_active: true,
        registered_at: now,
    };
    ctx.db.agent().insert(agent);
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 2: submit_price
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn submit_price(ctx: &ReducerContext, agent_id: Identity, asset_pair: String, price: f64, signal: f64) -> Result<(), String> {
    // Verify agent exists and is active
    let agent = ctx.db.agent().id().find(agent_id).ok_or_else(|| "Agent not found".to_string())?;
    if !agent.is_active {
        return Err("Agent is not active".to_string());
    }

    let now = ctx.timestamp;

    // Weight based on reputation + stake
    let weight = 1.0 + (agent.reputation_score * 0.5) + ((agent.stake_amount as f64) / 1_000_000_000.0);

    let submission = PriceSubmission {
        id: 0, // auto_inc
        agent_id,
        asset_pair: asset_pair.clone(),
        price,
        timestamp: now,
        stigmergy_signal: signal,
        weight,
    };
    ctx.db.price_submission().insert(submission);

    // Emit stigmergy signal for coordination
    let signal_type = if signal > 0.5 {
        SignalType::Coordinate
    } else if signal < -0.5 {
        SignalType::Withdraw
    } else {
        SignalType::Alert
    };

    let expires_at = Timestamp::from_micros_since_unix_epoch(now.to_micros_since_unix_epoch() + 3_600_000_000); // +1 hour in µs

    let stig_signal = StigmergySignal {
        signal_id: 0, // auto_inc
        agent_id,
        signal_type,
        intensity: signal.abs(),
        decay_factor: 0.95,
        created_at: now,
        expires_at,
    };
    ctx.db.stigmergy_signal().insert(stig_signal);

    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 3: compute_consensus
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn compute_consensus(ctx: &ReducerContext, asset_pair: String) -> Result<(), String> {
    let now = ctx.timestamp;

    // Collect recent submissions (last 5 minutes = 300_000_000 µs)
    let window_start = Timestamp::from_micros_since_unix_epoch(now.to_micros_since_unix_epoch().saturating_sub(300_000_000));

    let mut submissions: Vec<(f64, f64)> = Vec::new();
    let mut submission_ids: Vec<u64> = Vec::new();

    for sub in ctx.db.price_submission().iter() {
        if sub.asset_pair == asset_pair && sub.timestamp >= window_start {
            submissions.push((sub.price, sub.weight));
            submission_ids.push(sub.id);
        }
    }

    let weighted_median = compute_weighted_median(&submissions);

    let round = ConsensusRound {
        round_id: 0, // auto_inc
        asset_pair: asset_pair.clone(),
        start_time: window_start,
        end_time: now,
        price_submissions: submission_ids,
        weighted_median_price: weighted_median,
        status: RoundStatus::Resolved,
    };
    ctx.db.consensus_round().insert(round);

    // Decay stigmergy signals for this asset pair (apply decay factor)
    let mut to_remove: Vec<u64> = Vec::new();
    for signal in ctx.db.stigmergy_signal().iter() {
        if now >= signal.expires_at {
            to_remove.push(signal.signal_id);
        }
    }
    for sid in to_remove {
        ctx.db.stigmergy_signal().signal_id().delete(sid);
    }

    // Update submitting agents' reputation
    for sub in ctx.db.price_submission().iter() {
        if sub.asset_pair == asset_pair && sub.timestamp >= window_start {
            let accuracy = 1.0 - ((sub.price - weighted_median).abs() / weighted_median.max(1e-12)).min(1.0);
            if let Some(mut agent) = ctx.db.agent().id().find(sub.agent_id) {
                agent.reputation_score = (agent.reputation_score * 0.9) + (accuracy * 0.1);
                ctx.db.agent().id().update(agent);
            }
        }
    }

    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 4: create_market
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn create_market(ctx: &ReducerContext, question: String, outcomes: Vec<String>, deadline: u64) -> Result<(), String> {
    if outcomes.len() < 2 {
        return Err("Need at least 2 outcomes".to_string());
    }

    let market = MarketState {
        market_id: 0, // auto_inc
        question,
        outcomes,
        deadline,
        resolved: false,
        winning_outcome: None,
        total_stake: 0,
    };
    ctx.db.market_state().insert(market);
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 5: place_prediction
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn place_prediction(ctx: &ReducerContext, market_id: u64, agent_id: Identity, outcome_index: u64, amount: u64) -> Result<(), String> {
    let mut market = ctx.db.market_state().market_id().find(market_id).ok_or_else(|| "Market not found".to_string())?;
    if market.resolved {
        return Err("Market already resolved".to_string());
    }
    if (outcome_index as usize) >= market.outcomes.len() {
        return Err("Invalid outcome index".to_string());
    }
    let mut agent = ctx.db.agent().id().find(agent_id).ok_or_else(|| "Agent not found".to_string())?;
    if agent.stake_amount < amount {
        return Err("Insufficient stake".to_string());
    }

    agent.stake_amount -= amount;
    ctx.db.agent().id().update(agent);

    market.total_stake += amount;
    ctx.db.market_state().market_id().update(market);

    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 6: resolve_market
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer]
pub fn resolve_market(ctx: &ReducerContext, market_id: u64) -> Result<(), String> {
    let mut market = ctx.db.market_state().market_id().find(market_id).ok_or_else(|| "Market not found".to_string())?;
    if market.resolved {
        return Err("Market already resolved".to_string());
    }

    // Look up the most recent consensus round — use as oracle price feed
    let mut best_round: Option<ConsensusRound> = None;
    for round in ctx.db.consensus_round().iter() {
        if round.status == RoundStatus::Resolved {
            match &best_round {
                Some(br) if round.round_id > br.round_id => best_round = Some(round),
                None => best_round = Some(round),
                _ => {}
            }
        }
    }

    let consensus_price = best_round.map(|r| r.weighted_median_price).unwrap_or(0.0);
    let outcome_index = if consensus_price > 100.0 {
        0usize
    } else {
        1usize
    };

    if outcome_index < market.outcomes.len() {
        market.winning_outcome = Some(market.outcomes[outcome_index].clone());
    }
    market.resolved = true;
    ctx.db.market_state().market_id().update(market);

    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// REDUCER 7: schedule_stigmergy_decay
// ── Scheduled via a dedicated table ────────────────────────────────────────────

#[spacetimedb::table(accessor = stigmergy_decay_schedule, scheduled(schedule_stigmergy_decay))]
pub struct StigmergyDecaySchedule {
    #[primary_key]
    #[auto_inc]
    pub scheduled_id: u64,
    pub scheduled_at: ScheduleAt,
}

#[spacetimedb::reducer]
pub fn schedule_stigmergy_decay(ctx: &ReducerContext, _arg: StigmergyDecaySchedule) -> Result<(), String> {
    let now = ctx.timestamp;

    let expired: Vec<u64> = ctx.db.stigmergy_signal().iter()
        .filter(|s| now >= s.expires_at)
        .map(|s| s.signal_id)
        .collect();

    for sid in expired {
        ctx.db.stigmergy_signal().signal_id().delete(sid);
    }

    // Also decay non-expired signals
    let mut signal_ids: Vec<u64> = Vec::new();
    for signal in ctx.db.stigmergy_signal().iter() {
        if now < signal.expires_at {
            signal_ids.push(signal.signal_id);
        }
    }
    for sid in signal_ids {
        if let Some(mut signal) = ctx.db.stigmergy_signal().signal_id().find(sid) {
            signal.intensity *= signal.decay_factor;
            ctx.db.stigmergy_signal().signal_id().update(signal);
        }
    }

    // Stigmergy decay cycle complete
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════════════════
// INIT REDUCER: seed initial schedule for periodic stigmergy decay
// ═══════════════════════════════════════════════════════════════════════════════

#[spacetimedb::reducer(init)]
pub fn init(ctx: &ReducerContext) {
    // Schedule stigmergy decay to run every 10 minutes
    let ten_minutes = TimeDuration::from_micros(600_000_000);
    ctx.db.stigmergy_decay_schedule().insert(StigmergyDecaySchedule {
        scheduled_id: 0, // auto_inc
        scheduled_at: ten_minutes.into(),
    });
}
