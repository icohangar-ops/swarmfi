//! # Get Reputation (Read-only)
//!
//! View function that returns an agent's reputation data.
//! In Anchor, read operations are done by deserializing accounts directly.

use anchor_lang::prelude::*;
use crate::state::*;

#[derive(Accounts)]
pub struct GetReputation<'info> {
    #[account(
        seeds = [b"agent_reputation", agent.key().as_ref()],
        bump = agent_reputation.bump,
    )]
    pub agent_reputation: Account<'info, AgentReputation>,

    /// CHECK: Agent address to look up
    pub agent: AccountInfo<'info>,
}

pub fn handler(_ctx: Context<GetReputation>) -> Result<()> {
    // The reputation data is accessible via the agent_reputation account.
    // Clients read this account directly to get reputation data.
    // No state mutation needed.
    Ok(())
}
