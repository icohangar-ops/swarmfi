//! # Register Agent
//!
//! Register a new AI agent node in the SwarmFi oracle.
//! Mints an agent identity token (SPL Token) and stakes SOL into a PDA vault.

use anchor_lang::prelude::*;
use anchor_spl::token::{self, Token, Mint, TokenAccount, MintTo};
use crate::state::*;
use crate::errors::OracleError;

#[derive(Accounts)]
#[instruction(name: String, agent_type: AgentType, stake_amount: u64)]
pub struct RegisterAgent<'info> {
    #[account(
        mut,
        seeds = [b"oracle_config"],
        bump = config.bump,
        constraint = config.authority == authority.key() || config.admin == authority.key() @ OracleError::Unauthorized,
    )]
    pub config: Account<'info, OracleConfig>,

    #[account(
        init,
        payer = authority,
        space = 8 + AgentNode::INIT_SPACE,
        seeds = [b"agent_node", authority.key().as_ref()],
        bump
    )]
    pub agent_node: Account<'info, AgentNode>,

    /// Agent identity token mint (unique per agent)
    #[account(
        init,
        payer = authority,
        mint::decimals = 0,
        mint::authority = config,
        seeds = [b"agent_identity", authority.key().as_ref()],
        bump
    )]
    pub identity_mint: Account<'info, Mint>,

    /// Agent's token account to receive the identity token
    #[account(
        init,
        payer = authority,
        token::mint = identity_mint,
        token::authority = authority,
        seeds = [b"agent_token", authority.key().as_ref()],
        bump
    )]
    pub agent_token_account: Account<'info, TokenAccount>,

    /// PDA vault to hold agent stake
    #[account(
        mut,
        seeds = [b"agent_stake_vault", authority.key().as_ref()],
        bump
    )]
    pub stake_vault: SystemAccount<'info>,

    #[account(mut)]
    pub authority: Signer<'info>,

    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

pub fn handler(
    ctx: Context<RegisterAgent>,
    name: String,
    agent_type: AgentType,
    stake_amount: u64,
) -> Result<()> {
    require!(name.len() <= MAX_NAME_LEN, OracleError::AgentNameTooLong);
    require!(stake_amount > 0, OracleError::InsufficientStake);

    let config = &mut ctx.accounts.config;
    let agent_node = &mut ctx.accounts.agent_node;
    let clock = Clock::get()?;

    // Mint 1 agent identity token
    let cpi_accounts = MintTo {
        mint: ctx.accounts.identity_mint.to_account_info(),
        to: ctx.accounts.agent_token_account.to_account_info(),
        authority: config.to_account_info(),
    };
    let cpi_ctx = CpiContext::new_with_signer(
        ctx.accounts.token_program.to_account_info(),
        cpi_accounts,
        &[&[
            b"oracle_config",
            &[config.bump],
        ]],
    );
    token::mint_to(cpi_ctx, 1)?;

    // Transfer SOL stake to vault
    let vault_bump = *ctx.bumps.get("stake_vault").unwrap();
    let vault_seeds = &[
        b"agent_stake_vault",
        authority.key().as_ref(),
        &[vault_bump],
    ];
    let vault_key = Pubkey::create_program_address(vault_seeds, ctx.program_id)?;

    // Create the vault account if it doesn't exist
    let rent = Rent::get()?;
    let vault_space = 0;
    let vault_lamports = rent.minimum_balance(vault_space) + stake_amount;

    anchor_lang::system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            anchor_lang::system_program::Transfer {
                from: ctx.accounts.authority.to_account_info(),
                to: ctx.accounts.stake_vault.to_account_info(),
            },
        ),
        stake_amount,
    )?;

    // Populate agent node state
    agent_node.authority = ctx.accounts.authority.key();
    agent_node.name = name;
    agent_node.agent_type = agent_type;
    agent_node.identity_mint = ctx.accounts.identity_mint.key();
    agent_node.stake_amount = stake_amount;
    agent_node.reputation_score = 100; // Start at neutral
    agent_node.accuracy_score = 0;
    agent_node.total_submissions = 0;
    agent_node.is_active = true;
    agent_node.registered_at = clock.unix_timestamp;
    agent_node.last_submission_at = 0;
    agent_node.slash_count = 0;
    agent_node.bump = ctx.bumps.agent_node;

    // Update global config
    config.agent_count += 1;
    config.total_staked = config.total_staked.saturating_add(stake_amount);

    Ok(())
}
