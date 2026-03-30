//! # SwarmFi Reputation Registry — Contract Business Logic

use crate::error::ContractError;
use crate::msg::{
    AgentReputationResponse, BadgeResponse, BadgesResponse, ExecuteMsg, InstantiateMsg,
    QueryMsg, TopAgentsResponse, UserBadgesResponse, UserReputationResponse,
};
use crate::state::{
    AgentReputation, Badge, Config, ReputationTier, UserReputation, AGENT_REPUTATIONS,
    BADGE_COUNT, BADGES, CONFIG, USER_REPUTATIONS,
};
use cosmwasm_std::{
    to_json_binary, Addr, Binary, Deps, DepsMut, Env, MessageInfo, Order, Response, StdResult,
    Timestamp, Uint128,
};

// ── Instantiate ───────────────────────────────────────────────────

pub fn instantiate(
    deps: DepsMut,
    _env: Env,
    _info: MessageInfo,
    msg: InstantiateMsg,
) -> Result<Response, ContractError> {
    let config = Config {
        admin: deps.api.addr_validate(&msg.admin)?,
    };
    CONFIG.save(deps.storage, &config)?;

    Ok(Response::new()
        .add_attribute("action", "instantiate")
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
        ExecuteMsg::RecordAgentTask {
            agent,
            successful,
            accuracy_delta,
        } => execute_record_agent_task(deps, env, info, agent, successful, accuracy_delta),
        ExecuteMsg::UpdateAgentTier { agent, tier } => {
            execute_update_agent_tier(deps, env, info, agent, tier)
        }
        ExecuteMsg::AwardBadge {
            recipient,
            badge_id,
        } => execute_award_badge(deps, env, info, recipient, badge_id),
        ExecuteMsg::RecordUserPrediction {
            user,
            correct,
            volume,
        } => execute_record_user_prediction(deps, env, info, user, correct, volume),
        ExecuteMsg::CreateBadge {
            name,
            description,
            icon,
        } => execute_create_badge(deps, env, info, name, description, icon),
    }
}

// ── Execute implementations ───────────────────────────────────────

/// Record a completed task for an agent, updating task counts,
/// accuracy, reliability, and auto-tier.
fn execute_record_agent_task(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    agent_str: String,
    successful: bool,
    accuracy_delta: i64,
) -> Result<Response, ContractError> {
    // Only the oracle contract or admin can record tasks.
    let config = CONFIG.load(deps.storage)?;
    if info.sender != config.admin {
        return Err(ContractError::Unauthorized {
            role: "admin".to_string(),
        });
    }

    let agent_addr = deps.api.addr_validate(&agent_str)?;
    let mut rep = AGENT_REPUTATIONS
        .may_load(deps.storage, &agent_addr)?
        .unwrap_or_else(|| AgentReputation {
            agent_address: agent_addr.clone(),
            total_tasks: 0,
            successful_tasks: 0,
            accuracy_score: 0,
            reliability_score: 0,
            tier: ReputationTier::Bronze,
            updated_at: env.block.time,
        });

    rep.total_tasks += 1;
    if successful {
        rep.successful_tasks += 1;
    }

    // Apply accuracy delta.
    if accuracy_delta >= 0 {
        rep.accuracy_score = rep
            .accuracy_score
            .saturating_add(accuracy_delta.unsigned_abs());
    } else {
        let sub = accuracy_delta.unsigned_abs();
        if rep.accuracy_score < sub {
            rep.accuracy_score = 0;
        } else {
            rep.accuracy_score -= sub;
        }
    }
    // Clamp to 1000.
    rep.accuracy_score = rep.accuracy_score.min(1000);

    // Reliability = successful / total * 10000.
    if rep.total_tasks > 0 {
        rep.reliability_score = (rep.successful_tasks as u64 * 10_000) / rep.total_tasks as u64;
    }

    // Auto-tier based on accuracy.
    rep.tier = ReputationTier::from_score(rep.accuracy_score);
    rep.updated_at = env.block.time;

    AGENT_REPUTATIONS.save(deps.storage, &agent_addr, &rep)?;

    Ok(Response::new()
        .add_attribute("action", "record_agent_task")
        .add_attribute("agent", &agent_addr)
        .add_attribute("successful", successful.to_string())
        .add_attribute("accuracy", rep.accuracy_score.to_string())
        .add_attribute("tier", rep.tier.as_str()))
}

/// Admin manually sets an agent's tier (override auto-tier).
fn execute_update_agent_tier(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    agent_str: String,
    tier_str: String,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let agent_addr = deps.api.addr_validate(&agent_str)?;
    let tier = ReputationTier::from_string(&tier_str);

    let mut rep = AGENT_REPUTATIONS
        .load(deps.storage, &agent_addr)
        .map_err(|_| ContractError::AgentNotFound {
            address: agent_str,
        })?;

    rep.tier = tier;
    rep.updated_at = env.block.time;
    AGENT_REPUTATIONS.save(deps.storage, &agent_addr, &rep)?;

    Ok(Response::new()
        .add_attribute("action", "update_agent_tier")
        .add_attribute("agent", &agent_addr)
        .add_attribute("tier", tier.as_str()))
}

/// Award a badge to a user or agent.
fn execute_award_badge(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    recipient_str: String,
    badge_id: u64,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    // Ensure badge exists.
    if BADGES.may_load(deps.storage, badge_id)?.is_none() {
        return Err(ContractError::BadgeNotFound { id: badge_id });
    }

    let recipient = deps.api.addr_validate(&recipient_str)?;

    // Try user reputation first, then agent.
    let mut is_user = false;
    if let Ok(mut user_rep) = USER_REPUTATIONS.may_load(deps.storage, &recipient) {
        if let Some(ref mut ur) = user_rep {
            if !ur.badges.contains(&badge_id) {
                ur.badges.push(badge_id);
            }
            USER_REPUTATIONS.save(deps.storage, &recipient, ur)?;
            is_user = true;
        }
    }

    if !is_user {
        // Try as agent — agents don't have badges in this design, but we
        // store on user reputation for universality. If no user rep exists,
        // create one.
        let mut user_rep = USER_REPUTATIONS
            .may_load(deps.storage, &recipient)?
            .unwrap_or_else(|| UserReputation {
                address: recipient.clone(),
                total_bets: 0,
                correct_bets: 0,
                volume_contributed: Uint128::zero(),
                badges: vec![],
                created_at: _env.block.time,
            });
        if !user_rep.badges.contains(&badge_id) {
            user_rep.badges.push(badge_id);
        }
        USER_REPUTATIONS.save(deps.storage, &recipient, &user_rep)?;
    }

    Ok(Response::new()
        .add_attribute("action", "award_badge")
        .add_attribute("recipient", &recipient)
        .add_attribute("badge_id", badge_id.to_string()))
}

/// Record a user prediction outcome for reputation tracking.
fn execute_record_user_prediction(
    deps: DepsMut,
    env: Env,
    info: MessageInfo,
    user_str: String,
    correct: bool,
    volume: Uint128,
) -> Result<Response, ContractError> {
    // Can be called by the prediction-market contract or admin.
    let config = CONFIG.load(deps.storage)?;
    if info.sender != config.admin {
        return Err(ContractError::Unauthorized {
            role: "admin".to_string(),
        });
    }

    let user_addr = deps.api.addr_validate(&user_str)?;
    let mut rep = USER_REPUTATIONS
        .may_load(deps.storage, &user_addr)?
        .unwrap_or_else(|| UserReputation {
            address: user_addr.clone(),
            total_bets: 0,
            correct_bets: 0,
            volume_contributed: Uint128::zero(),
            badges: vec![],
            created_at: env.block.time,
        });

    rep.total_bets += 1;
    if correct {
        rep.correct_bets += 1;
    }
    rep.volume_contributed += volume;

    USER_REPUTATIONS.save(deps.storage, &user_addr, &rep)?;

    Ok(Response::new()
        .add_attribute("action", "record_user_prediction")
        .add_attribute("user", &user_addr)
        .add_attribute("correct", correct.to_string())
        .add_attribute("volume", volume.to_string()))
}

/// Admin creates a new badge definition.
fn execute_create_badge(
    deps: DepsMut,
    _env: Env,
    info: MessageInfo,
    name: String,
    description: String,
    icon: String,
) -> Result<Response, ContractError> {
    let config = CONFIG.load(deps.storage)?;
    ensure!(info.sender == config.admin, ContractError::Unauthorized {
        role: "admin".to_string(),
    });

    let badge_id = BADGE_COUNT.may_load(deps.storage)?.unwrap_or(0) + 1;
    BADGE_COUNT.save(deps.storage, &badge_id)?;

    let badge = Badge {
        id: badge_id,
        name,
        description,
        icon,
    };
    BADGES.save(deps.storage, badge_id, &badge)?;

    Ok(Response::new()
        .add_attribute("action", "create_badge")
        .add_attribute("badge_id", badge_id.to_string()))
}

// ── Query dispatch ────────────────────────────────────────────────

pub fn query(deps: Deps, _env: Env, msg: QueryMsg) -> StdResult<Binary> {
    match msg {
        QueryMsg::GetAgentReputation { agent } => {
            to_json_binary(&query_agent_reputation(deps, agent)?)
        }
        QueryMsg::GetUserReputation { address } => {
            to_json_binary(&query_user_reputation(deps, address)?)
        }
        QueryMsg::ListTopAgents { start_after, limit } => {
            to_json_binary(&query_list_top_agents(deps, start_after, limit)?)
        }
        QueryMsg::ListBadges { start_after, limit } => {
            to_json_binary(&query_list_badges(deps, start_after, limit)?)
        }
        QueryMsg::GetUserBadges { address } => {
            to_json_binary(&query_user_badges(deps, address)?)
        }
    }
}

fn query_agent_reputation(deps: Deps, agent: String) -> StdResult<AgentReputationResponse> {
    let addr = deps.api.addr_validate(&agent)?;
    let rep = AGENT_REPUTATIONS.load(deps.storage, &addr)?;
    Ok(AgentReputationResponse {
        agent_address: rep.agent_address.to_string(),
        total_tasks: rep.total_tasks,
        successful_tasks: rep.successful_tasks,
        accuracy_score: rep.accuracy_score,
        reliability_score: rep.reliability_score,
        tier: rep.tier.as_str().to_string(),
        updated_at: rep.updated_at,
    })
}

fn query_user_reputation(deps: Deps, address: String) -> StdResult<UserReputationResponse> {
    let addr = deps.api.addr_validate(&address)?;
    let rep = USER_REPUTATIONS.load(deps.storage, &addr)?;
    Ok(UserReputationResponse {
        address: rep.address.to_string(),
        total_bets: rep.total_bets,
        correct_bets: rep.correct_bets,
        volume_contributed: rep.volume_contributed,
        badges: rep.badges,
        created_at: rep.created_at,
    })
}

fn query_list_top_agents(
    deps: Deps,
    start_after: Option<u32>,
    limit: Option<u32>,
) -> StdResult<TopAgentsResponse> {
    let limit = limit.unwrap_or(20) as usize;
    let min_score = start_after.unwrap_or(1001);

    let agents: Vec<AgentReputationResponse> = AGENT_REPUTATIONS
        .range(deps.storage, None, None, Order::Ascending)
        .filter_map(|item| item.ok().map(|(_, r)| r))
        .filter(|r| r.accuracy_score < min_score as u64)
        .collect::<Vec<_>>();

    // Sort descending by accuracy_score.
    let mut sorted = agents;
    sorted.sort_by(|a, b| b.accuracy_score.cmp(&a.accuracy_score));

    Ok(TopAgentsResponse {
        agents: sorted
            .into_iter()
            .take(limit)
            .map(|r| AgentReputationResponse {
                agent_address: r.agent_address.to_string(),
                total_tasks: r.total_tasks,
                successful_tasks: r.successful_tasks,
                accuracy_score: r.accuracy_score,
                reliability_score: r.reliability_score,
                tier: r.tier.as_str().to_string(),
                updated_at: r.updated_at,
            })
            .collect(),
    })
}

fn query_list_badges(
    deps: Deps,
    start_after: Option<u64>,
    limit: Option<u32>,
) -> StdResult<BadgesResponse> {
    let limit = limit.unwrap_or(30) as usize;
    let start = start_after.map(cosmwasm_std::Bound::inclusive_bound);

    let badges: Vec<BadgeResponse> = BADGES
        .range(deps.storage, start, None, Order::Ascending)
        .take(limit)
        .filter_map(|item| item.ok())
        .map(|(_, b)| BadgeResponse {
            id: b.id,
            name: b.name,
            description: b.description,
            icon: b.icon,
        })
        .collect();

    Ok(BadgesResponse { badges })
}

fn query_user_badges(deps: Deps, address: String) -> StdResult<UserBadgesResponse> {
    let addr = deps.api.addr_validate(&address)?;
    let rep = USER_REPUTATIONS.load(deps.storage, &addr)?;
    Ok(UserBadgesResponse {
        address: rep.address.to_string(),
        badge_ids: rep.badges,
    })
}

use cosmwasm_std::ensure;
