//! # SwarmFi Oracle — Contract Business Logic
//!
//! Core handlers for instantiate, execute, and query entry-points.

use crate::error::ContractError;
use crate::msg::{
    AgentsResponse, AgentResponse, ConsensusPriceResponse, ExecuteMsg, InstantiateMsg,
    PriceFeedResponse, QueryMsg, StigmergySignalResponse, StigmergySignalsResponse,
};
use crate::state::{
    agents, Config, ConsensusPrice, PriceFeed, StigmergySignal, CONFIG, CONSENSUS_PRICES,
    PRICE_FEEDS, SIGNAL_COUNTER, STIGMERGY_SIGNALS,
};
use cosmwasm_std::{
    to_json_binary, Addr, Deps, DepsMut, Env, MessageInfo, Order, Response, StdResult, Timestamp,
    Uint128,
};

// ── Instantiate ───────────────────────────────────────────────────

/// Creates the contract and stores initial configuration.
pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    _info: MessageInfo,
    msg: InstantiateMsg,
) -> Result<Response, ContractError> {
    let config = Config {
        owner: deps.api.addr_validate(&msg.owner)?,
        admin: deps.api.addr_validate(&msg.admin)?,
        min_agents_for_consensus: msg.min_agents_for_consensus,
        max_age_seconds: msg.max_age_seconds,
        acceptable_deviation_bps: msg.acceptable_deviation_bps,
    };
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new()
        .add_attribute("action", "instantiate")
        .add_attribute("owner", &config.owner)
        .add_attribute("admin", &config.admin))
}

// ── Execute dispatch ──────────────────────────────────────────────

pub fn execute(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    msg: ExecuteMsg,
) -> Result<Response, ContractError> {
    match msg {
        ExecuteMsg::RegisterAgent { name, agent_type } => {
            execute_register_agent(deps, env, info, name, agent_type)
        }
        ExecuteMsg::SubmitPrice {
            asset_pair,
            price,
            confidence,
        } => execute_submit_price(deps, env, info, asset_pair, price, confidence),
        ExecuteMsg::SubmitStigmergySignal {
            signal_type,
            data_hash,
            strength,
            decay_rate,
        } => execute_submit_stigmergy_signal(
            deps,
            env,
            info,
            signal_type,
            data_hash,
            strength,
            decay_rate,
        ),
        ExecuteMsg::UpdateAgentReputation {
            agent,
            reputation_delta,
            accuracy_delta,
        } => execute_update_agent_reputation(deps, env, info, agent, reputation_delta, accuracy_delta),
        ExecuteMsg::UpdateConfig {
            admin,
            min_agents_for_consensus,
            max_age_seconds,
            acceptable_deviation_bps,
        } => execute_update_config(
            deps,
            env,
            info,
            admin,
            min_agents_for_consensus,
            max_age_seconds,
            acceptable_deviation_bps,
        ),
    }
}

// ── Execute implementations ───────────────────────────────────────

/// Register a new AI agent. Fails if the address is already registered.
fn execute_register_agent(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    name: String,
    agent_type: String,
) -> Result<Response, ContractError> {
    let sender = info.sender;

    // Prevent duplicate registration.
    if agents().may_load(deps.storage, &sender)?.is_some() {
        return Err(ContractError::AgentAlreadyRegistered {
            address: sender.to_string(),
        });
    }

    let agent = crate::state::Agent {
        address: sender.clone(),
        name,
        agent_type,
        reputation_score: 100u64, // start at neutral 100
        total_submissions: 0,
        accuracy_score: 0,
        is_active: true,
        registered_at: env.block.time,
    };
    agents().save(deps.storage, &sender, &agent)?;

    Ok(Response::new()
        .add_attribute("action", "register_agent")
        .add_attribute("agent", &sender))
}

/// Agent submits a price. Stores the feed and potentially computes a
/// weighted-median consensus price when enough agents have submitted.
fn execute_submit_price(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    asset_pair: String,
    price: Uint128,
    confidence: u8,
) -> Result<Response, ContractError> {
    if price.is_zero() {
        return Err(ContractError::ZeroPrice {});
    }
    if confidence == 0 {
        return Err(ContractError::InvalidConfidence {});
    }

    let sender = info.sender;
    let agent = agents()
        .load(deps.storage, &sender)
        .map_err(|_| ContractError::AgentNotFound {
            address: sender.to_string(),
        })?;

    if !agent.is_active {
        return Err(ContractError::AgentInactive {});
    }

    // Weight is proportional to reputation score.
    let consensus_weight = Uint128::from(agent.reputation_score);

    let feed = PriceFeed {
        asset_pair: asset_pair.clone(),
        price,
        confidence,
        submitted_by: sender.clone(),
        submitted_at: env.block.time,
        consensus_weight,
        agent_signatures: vec![sender.to_string()],
    };

    // Store keyed by (asset_pair, agent_address).
    PRICE_FEEDS.save(deps.storage, (&asset_pair, &sender), &feed)?;

    // Increment agent's submission count.
    let mut updated_agent = agent;
    updated_agent.total_submissions += 1;
    agents().save(deps.storage, &sender, &updated_agent)?;

    // Attempt consensus computation.
    let mut attrs = vec![
        ("action", "submit_price".to_string()),
        ("asset_pair", asset_pair.clone()),
        ("agent", sender.to_string()),
    ];

    if let Some(consensus) = try_compute_consensus(deps.as_ref(), &env, &asset_pair)? {
        CONSENSUS_PRICES.save(deps.storage, &asset_pair, &consensus)?;
        attrs.push(("consensus_price", consensus.price.to_string()));
        attrs.push(("agent_count", consensus.agent_count.to_string()));
    }

    Ok(Response::new().add_attributes(attrs))
}

/// Deposit a stigmergy coordination signal.
fn execute_submit_stigmergy_signal(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    signal_type: String,
    data_hash: String,
    strength: Uint128,
    decay_rate: u64,
) -> Result<Response, ContractError> {
    if strength.is_zero() {
        return Err(ContractError::ZeroSignalStrength {});
    }

    let sender = info.sender;
    let id: u64 = SIGNAL_COUNTER.may_load(deps.storage)?.unwrap_or(0) + 1;
    SIGNAL_COUNTER.save(deps.storage, &id)?;

    let signal = StigmergySignal {
        signal_type: signal_type.clone(),
        from_agent: sender.clone(),
        data_hash,
        strength,
        deposited_at: env.block.time,
        decay_rate,
    };
    STIGMERGY_SIGNALS.save(deps.storage, id, &signal)?;

    Ok(Response::new()
        .add_attribute("action", "submit_stigmergy_signal")
        .add_attribute("signal_id", id.to_string())
        .add_attribute("signal_type", signal_type)
        .add_attribute("from_agent", &sender))
}

/// Admin updates a specific agent's reputation / accuracy scores.
fn execute_update_agent_reputation(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    agent_addr: String,
    reputation_delta: i64,
    accuracy_delta: i64,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    if info.sender != config.admin {
        return Err(ContractError::Unauthorized {
            role: "admin".to_string(),
        });
    }

    let agent_addr = deps.api.addr_validate(&agent_addr)?;
    let mut agent = agents()
        .load(deps.storage, &agent_addr)
        .map_err(|_| ContractError::AgentNotFound {
            address: agent_addr.to_string(),
        })?;

    // Apply deltas with saturating arithmetic.
    if reputation_delta >= 0 {
        agent.reputation_score = agent
            .reputation_score
            .saturating_add(reputation_delta.unsigned_abs());
    } else {
        agent.reputation_score = agent.reputation_score.saturating_sub(reputation_delta.unsigned_abs());
    }

    if accuracy_delta >= 0 {
        agent.accuracy_score = agent
            .accuracy_score
            .saturating_add(accuracy_delta.unsigned_abs());
    } else {
        agent.accuracy_score = agent.accuracy_score.saturating_sub(accuracy_delta.unsigned_abs());
    }

    agents().save(deps.storage, &agent_addr, &agent)?;

    Ok(Response::new()
        .add_attribute("action", "update_agent_reputation")
        .add_attribute("agent", &agent_addr)
        .add_attribute("reputation", agent.reputation_score.to_string())
        .add_attribute("accuracy", agent.accuracy_score.to_string()))
}

/// Owner updates global configuration parameters.
fn execute_update_config(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    admin: Option<String>,
    min_agents_for_consensus: Option<u32>,
    max_age_seconds: Option<u64>,
    acceptable_deviation_bps: Option<u64>,
) -> Result<Response, ContractError> {
    let mut config = CONFIG.load(deps.storage)?;
    if info.sender != config.owner {
        return Err(ContractError::Unauthorized {
            role: "owner".to_string(),
        });
    }

    if let Some(admin_str) = admin {
        config.admin = deps.api.addr_validate(&admin_str)?;
    }
    if let Some(v) = min_agents_for_consensus {
        config.min_agents_for_consensus = v;
    }
    if let Some(v) = max_age_seconds {
        config.max_age_seconds = v;
    }
    if let Some(v) = acceptable_deviation_bps {
        config.acceptable_deviation_bps = v;
    }
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new().add_attribute("action", "update_config"))
}

// ── Query dispatch ────────────────────────────────────────────────

pub fn query(deps: Deps, env: Env, msg: QueryMsg) -> StdResult<cosmwasm_std::Binary> {
    match msg {
        QueryMsg::GetPrice { asset_pair } => {
            let sender = deps.api.addr_validate(&asset_pair)?; // misuse, but we need *some* address
            let _ = sender; // we actually just use the string key
            to_json_binary(&query_price(deps, &asset_pair)?)
        }
        QueryMsg::GetAgent { address } => {
            to_json_binary(&query_agent(deps, address)?)
        }
        QueryMsg::ListAgents { start_after, limit } => {
            to_json_binary(&query_list_agents(deps, start_after, limit)?)
        }
        QueryMsg::GetConsensusPrice { asset_pair } => {
            to_json_binary(&query_consensus_price(deps, env, &asset_pair)?)
        }
        QueryMsg::GetStigmergySignals {
            signal_type,
            start_after,
            limit,
        } => to_json_binary(&query_stigmergy_signals(
            deps,
            env,
            signal_type,
            start_after,
            limit,
        )?),
    }
}

fn query_price(deps: Deps, asset_pair: &str) -> StdResult<PriceFeedResponse> {
    // Return the latest submission across all agents (pick the first loaded
    // in storage). In production you'd keep a "latest feed" index per pair.
    // For now we iterate and return the most recent.
    let feeds: Vec<PriceFeed> = PRICE_FEEDS
        .prefix(asset_pair)
        .range(deps.storage, None, None, Order::Descending)
        .filter_map(|item| item.ok().map(|(_, v)| v))
        .collect();

    let feed = feeds.into_iter().next().ok_or(cosmwasm_std::StdError::NotFound {
        kind: "PriceFeed".to_string(),
    })?;

    Ok(PriceFeedResponse {
        asset_pair: feed.asset_pair,
        price: feed.price,
        confidence: feed.confidence,
        submitted_by: feed.submitted_by.to_string(),
        submitted_at: feed.submitted_at,
        consensus_weight: feed.consensus_weight,
        agent_signatures: feed.agent_signatures,
    })
}

fn query_agent(deps: Deps, address: String) -> StdResult<AgentResponse> {
    let addr = deps.api.addr_validate(&address)?;
    let agent = agents().load(deps.storage, &addr)?;
    Ok(AgentResponse {
        address: agent.address.to_string(),
        name: agent.name,
        agent_type: agent.agent_type,
        reputation_score: agent.reputation_score,
        total_submissions: agent.total_submissions,
        accuracy_score: agent.accuracy_score,
        is_active: agent.is_active,
        registered_at: agent.registered_at,
    })
}

fn query_list_agents(
    deps: Deps,
    start_after: Option<String>,
    limit: Option<u32>,
) -> StdResult<AgentsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after
        .map(|s| deps.api.addr_validate(&s))
        .transpose()?;

    let agents_list: Vec<AgentResponse> = agents()
        .range(deps.storage, start.as_ref(), None, Order::Ascending)
        .take(limit)
        .filter_map(|item| item.ok())
        .map(|(_, a)| AgentResponse {
            address: a.address.to_string(),
            name: a.name,
            agent_type: a.agent_type,
            reputation_score: a.reputation_score,
            total_submissions: a.total_submissions,
            accuracy_score: a.accuracy_score,
            is_active: a.is_active,
            registered_at: a.registered_at,
        })
        .collect();

    Ok(AgentsResponse {
        agents: agents_list,
    })
}

fn query_consensus_price(
    deps: Deps,
    env: Env,
    asset_pair: &str,
) -> StdResult<ConsensusPriceResponse> {
    match CONSENSUS_PRICES.may_load(deps.storage, asset_pair)? {
        Some(c) => Ok(ConsensusPriceResponse {
            asset_pair: c.asset_pair,
            price: c.price,
            agent_count: c.agent_count,
            computed_at: c.computed_at,
            confidence: c.confidence,
        }),
        None => {
            // Attempt a fresh computation.
            match try_compute_consensus(deps, &env, asset_pair)? {
                Some(c) => Ok(ConsensusPriceResponse {
                    asset_pair: c.asset_pair,
                    price: c.price,
                    agent_count: c.agent_count,
                    computed_at: c.computed_at,
                    confidence: c.confidence,
                }),
                None => Err(cosmwasm_std::StdError::NotFound {
                    kind: "ConsensusPrice".to_string(),
                }),
            }
        }
    }
}

fn query_stigmergy_signals(
    deps: Deps,
    env: Env,
    signal_type: Option<String>,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<StigmergySignalsResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let config = CONFIG.load(deps.storage)?;
    let max_age = config.max_age_seconds;
    let cutoff = env.block.time.minus_seconds(max_age);

    let signals: Vec<StigmergySignalResponse> = STIGMERGY_SIGNALS
        .range(deps.storage, start_after.map(Bound::inclusive_bound), None, Order::Ascending)
        .take(limit)
        .filter_map(|item| item.ok().map(|(_, s)| s))
        .filter(|s| s.deposited_at > cutoff)
        .filter(|s| {
            signal_type
                .as_ref()
                .map(|t| s.signal_type == *t)
                .unwrap_or(true)
        })
        .map(|s| {
            // Apply decay: current_strength = strength * (1 - decay_rate * elapsed_seconds / 10000)
            let elapsed = s.deposited_at.seconds() as u128;
            let now = env.block.time.seconds() as u128;
            let decay_numerator = s.decay_rate as u128 * (now - elapsed);
            let decayed = if decay_numerator >= 10_000u128 {
                Uint128::zero()
            } else {
                s.strength.multiply_ratio(10_000u128 - decay_numerator, 10_000u128)
            };

            StigmergySignalResponse {
                signal_type: s.signal_type,
                from_agent: s.from_agent.to_string(),
                data_hash: s.data_hash,
                strength: decayed,
                deposited_at: s.deposited_at,
                decay_rate: s.decay_rate,
            }
        })
        .collect();

    Ok(StigmergySignalsResponse { signals })
}

// ── Helpers ───────────────────────────────────────────────────────

use cosmwasm_std::Bound;

/// Attempt to compute a weighted-median consensus price for the given
/// asset pair. Returns `None` if not enough recent, in-range submissions.
///
/// **Algorithm:**
/// 1. Load all price feeds for the pair submitted within `max_age_seconds`.
/// 2. Filter out submissions whose price deviates more than
///    `acceptable_deviation_bps` from the simple median (outlier removal).
/// 3. If enough agents remain, compute the **weighted median** where each
///    agent's vote is weighted by its reputation-based `consensus_weight`.
fn try_compute_consensus(
    deps: Deps,
    env: &Env,
    asset_pair: &str,
) -> Result<Option<ConsensusPrice>, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    let cutoff = env.block.time.minus_seconds(config.max_age_seconds);

    // 1. Collect recent feeds.
    let feeds: Vec<PriceFeed> = PRICE_FEEDS
        .prefix(asset_pair)
        .range(deps.storage, None, None, Order::Ascending)
        .filter_map(|item| item.ok().map(|(_, v)| v))
        .filter(|f| f.submitted_at > cutoff)
        .collect();

    let agent_count = feeds.len() as u32;
    if agent_count < config.min_agents_for_consensus {
        return Ok(None);
    }

    // 2. Simple median for outlier detection.
    let mut prices: Vec<Uint128> = feeds.iter().map(|f| f.price).collect();
    prices.sort();
    let median_price = prices[prices.len() / 2];

    // One basis-point = 10_000.
    let deviation_threshold = median_price.multiply_ratio(
        config.acceptable_deviation_bps,
        10_000u128,
    );

    // Filter to in-range feeds.
    let in_range: Vec<&PriceFeed> = feeds
        .iter()
        .filter(|f| {
            if f.price > median_price {
                f.price - median_price <= deviation_threshold
            } else {
                median_price - f.price <= deviation_threshold
            }
        })
        .collect();

    if in_range.len() < config.min_agents_for_consensus as usize {
        return Ok(None);
    }

    // 3. Weighted median — expand each price `weight` times, then take median.
    let mut weighted: Vec<(Uint128, Uint128)> = in_range
        .iter()
        .map(|f| (f.price, f.consensus_weight))
        .collect();
    weighted.sort_by_key(|(p, _)| *p);

    let total_weight: Uint128 = weighted.iter().map(|(_, w)| *w).sum();
    let mut cumulative = Uint128::zero();
    let mut weighted_median = Uint128::zero();

    for (price, weight) in &weighted {
        cumulative += *weight;
        if cumulative >= total_weight / Uint128::from(2u128) {
            weighted_median = *price;
            break;
        }
    }

    // Average confidence.
    let avg_confidence = (in_range.iter().map(|f| f.confidence as u32).sum::<u32>()
        / in_range.len() as u32) as u8;

    Ok(Some(ConsensusPrice {
        asset_pair: asset_pair.to_string(),
        price: weighted_median,
        agent_count: in_range.len() as u32,
        computed_at: env.block.time,
        confidence: avg_confidence,
    }))
}
