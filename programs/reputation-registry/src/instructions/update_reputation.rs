//! # Update Reputation
//!
//! Update agent and user reputation records after oracle rounds,
//! prediction outcomes, and other events.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::ReputationError;

// ── Update Agent Reputation ─────────────────────────────────────────

#[derive(Accounts)]
pub struct UpdateReputation<'info> {
    #[account(
        seeds = [b"registry_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ ReputationError::Unauthorized,
    )]
    pub config: Account<'info, RegistryConfig>,

    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + AgentReputation::INIT_SPACE,
        seeds = [b"agent_reputation", agent.key().as_ref()],
        bump
    )]
    pub agent_reputation: Account<'info, AgentReputation>,

    /// CHECK: Agent address to update
    pub agent: AccountInfo<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<UpdateReputation>,
    successful: bool,
    accuracy_delta: i64,
) -> Result<()> {
    let config = &mut ctx.accounts.config;
    let rep = &mut ctx.accounts.agent_reputation;
    let clock = Clock::get()?;
    let is_new = rep.agent == Pubkey::default();

    if is_new {
        rep.agent = ctx.accounts.agent.key();
        rep.total_tasks = 0;
        rep.successful_tasks = 0;
        rep.accuracy_score = 0;
        rep.reliability_score = 0;
        rep.tier = ReputationTier::Bronze;
        rep.updated_at = clock.unix_timestamp;
        config.agent_count += 1;
    }

    // Update task counts
    rep.total_tasks += 1;
    if successful {
        rep.successful_tasks += 1;
    }

    // Apply accuracy delta
    if accuracy_delta >= 0 {
        rep.accuracy_score = rep
            .accuracy_score
            .saturating_add(accuracy_delta.unsigned_abs() as u64);
    } else {
        rep.accuracy_score = rep
            .accuracy_score
            .saturating_sub(accuracy_delta.unsigned_abs() as u64);
    }

    // Clamp to 1000
    rep.accuracy_score = rep.accuracy_score.min(1000);

    // Compute reliability: (successful / total) * 10000
    if rep.total_tasks > 0 {
        rep.reliability_score =
            (rep.successful_tasks as u64 * 10_000) / rep.total_tasks as u64;
    }

    // Auto-tier based on accuracy
    rep.tier = ReputationTier::from_score(rep.accuracy_score);
    rep.updated_at = clock.unix_timestamp;

    Ok(())
}

// ── Record User Prediction ─────────────────────────────────────────

#[derive(Accounts)]
pub struct RecordPrediction<'info> {
    #[account(
        seeds = [b"registry_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ ReputationError::Unauthorized,
    )]
    pub config: Account<'info, RegistryConfig>,

    #[account(
        init_if_needed,
        payer = authority,
        space = 8 + UserReputation::INIT_SPACE,
        seeds = [b"user_reputation", user.key().as_ref()],
        bump
    )]
    pub user_reputation: Account<'info, UserReputation>,

    /// CHECK: User address to record prediction for
    pub user: AccountInfo<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn record_prediction(
    ctx: Context<RecordPrediction>,
    correct: bool,
    volume: u64,
) -> Result<()> {
    let config = &mut ctx.accounts.config;
    let rep = &mut ctx.accounts.user_reputation;
    let clock = Clock::get()?;
    let is_new = rep.user == Pubkey::default();

    if is_new {
        rep.user = ctx.accounts.user.key();
        rep.total_bets = 0;
        rep.correct_bets = 0;
        rep.volume_contributed = 0;
        rep.badges = Vec::new();
        rep.created_at = clock.unix_timestamp;
        config.user_count += 1;
    }

    rep.total_bets += 1;
    if correct {
        rep.correct_bets += 1;
    }
    rep.volume_contributed = rep.volume_contributed.saturating_add(volume);

    Ok(())
}

// ── Create Badge ───────────────────────────────────────────────────

#[derive(Accounts)]
#[instruction(name: String, description: String, badge_uri: String)]
pub struct CreateBadge<'info> {
    #[account(
        seeds = [b"registry_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ ReputationError::Unauthorized,
    )]
    pub config: Account<'info, RegistryConfig>,

    #[account(
        init,
        payer = authority,
        space = 8 + Badge::INIT_SPACE,
        seeds = [b"badge", config.badge_count.to_le_bytes().as_ref()],
        bump
    )]
    pub badge: Account<'info, Badge>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn create_badge(
    ctx: Context<CreateBadge>,
    name: String,
    description: String,
    badge_uri: String,
) -> Result<()> {
    require!(name.len() <= MAX_BADGE_NAME_LEN, ReputationError::BadgeNameTooLong);
    require!(
        description.len() <= MAX_BADGE_DESC_LEN,
        ReputationError::BadgeDescriptionTooLong
    );
    require!(badge_uri.len() <= MAX_BADGE_URI_LEN, ReputationError::BadgeUriTooLong);

    let config = &mut ctx.accounts.config;
    let badge = &mut ctx.accounts.badge;

    badge.id = config.badge_count;
    badge.name = name;
    badge.description = description;
    badge.badge_uri = badge_uri;
    badge.bump = ctx.bumps.badge;

    config.badge_count += 1;

    Ok(())
}

// ── Award Badge ────────────────────────────────────────────────────

#[derive(Accounts)]
#[instruction(badge_id: u64)]
pub struct AwardBadge<'info> {
    #[account(
        seeds = [b"registry_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ ReputationError::Unauthorized,
    )]
    pub config: Account<'info, RegistryConfig>,

    #[account(
        seeds = [b"badge", badge_id.to_le_bytes().as_ref()],
        bump = badge.bump,
    )]
    pub badge: Account<'info, Badge>,

    #[account(
        mut,
        seeds = [b"user_reputation", recipient.key().as_ref()],
        bump = user_reputation.bump,
    )]
    pub user_reputation: Account<'info, UserReputation>,

    /// CHECK: Recipient of the badge
    pub recipient: AccountInfo<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,
}

pub fn award_badge(ctx: Context<AwardBadge>, badge_id: u64) -> Result<()> {
    let user_rep = &mut ctx.accounts.user_reputation;

    // Avoid duplicates
    if !user_rep.badges.contains(&badge_id) {
        require!(
            user_rep.badges.len() < MAX_BADGES,
            ReputationError::BadgeNameTooLong // reuse error
        );
        user_rep.badges.push(badge_id);
    }

    Ok(())
}
