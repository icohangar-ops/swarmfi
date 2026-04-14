//! # Update Agent Reputation
//!
//! Admin updates an agent's reputation and accuracy scores.

use anchor_lang::prelude::*;
use crate::state::*;
use crate::errors::OracleError;

#[derive(Accounts)]
pub struct UpdateAgentReputation<'info> {
    #[account(
        seeds = [b"oracle_config"],
        bump = config.bump,
        constraint = config.admin == authority.key() @ OracleError::Unauthorized,
    )]
    pub config: Account<'info, OracleConfig>,

    #[account(
        mut,
        seeds = [b"agent_node", agent_authority.key().as_ref()],
        bump = agent_node.bump,
    )]
    pub agent_node: Account<'info, AgentNode>,

    /// CHECK: Must match the agent_node's authority
    pub agent_authority: AccountInfo<'info>,

    pub authority: Signer<'info>,
}

pub fn handler(
    ctx: Context<UpdateAgentReputation>,
    reputation_delta: i64,
    accuracy_delta: i64,
) -> Result<()> {
    let agent_node = &mut ctx.accounts.agent_node;

    // Verify agent_authority matches
    require!(
        ctx.accounts.agent_authority.key() == agent_node.authority,
        OracleError::AgentNotFound
    );

    // Apply reputation delta with saturating arithmetic
    if reputation_delta >= 0 {
        agent_node.reputation_score = agent_node
            .reputation_score
            .saturating_add(reputation_delta.unsigned_abs() as u64);
    } else {
        agent_node.reputation_score = agent_node
            .reputation_score
            .saturating_sub(reputation_delta.unsigned_abs() as u64);
    }

    // Clamp reputation to 0-1000
    agent_node.reputation_score = agent_node.reputation_score.min(1000);

    // Apply accuracy delta
    if accuracy_delta >= 0 {
        agent_node.accuracy_score = agent_node
            .accuracy_score
            .saturating_add(accuracy_delta.unsigned_abs() as u64);
    } else {
        agent_node.accuracy_score = agent_node
            .accuracy_score
            .saturating_sub(accuracy_delta.unsigned_abs() as u64);
    }

    // Clamp accuracy to 0-1000
    agent_node.accuracy_score = agent_node.accuracy_score.min(1000);

    // Auto-deactivate if reputation drops below threshold
    if agent_node.reputation_score < 10 {
        agent_node.is_active = false;
    }

    Ok(())
}
