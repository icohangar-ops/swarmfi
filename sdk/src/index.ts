/**
 * SwarmFi SDK — TypeScript Client for Solana Programs
 *
 * Provides typed wrappers around all SwarmFi Anchor program IDL calls.
 * Covers: SwarmOracle, PredictionMarket, ReputationRegistry, VaultManager.
 */

import * as anchor from "@coral-xyz/anchor";
import { BN } from "@coral-xyz/anchor";
import {
  PublicKey,
  Keypair,
  SystemProgram,
  Connection,
  Commitment,
} from "@solana/web3.js";
import {
  TOKEN_PROGRAM_ID,
  ASSOCIATED_TOKEN_PROGRAM_ID,
  createAssociatedTokenAccountInstruction,
  getAssociatedTokenAddressSync,
  mintTo,
} from "@solana/spl-token";

// ── Program IDs ────────────────────────────────────────────────────

export const SWARM_ORACLE_PROGRAM_ID = new PublicKey(
  "FsWBMoA5x5bSaZGJGYeCsSWaaBGJ4eCqGMPbQnMBnKNp"
);
export const PREDICTION_MARKET_PROGRAM_ID = new PublicKey(
  "PMkt1SxPMKp3f5xLKNJghKBBm9JvHZQCEMJKWGPn7x4D"
);
export const REPUTATION_REGISTRY_PROGRAM_ID = new PublicKey(
  "RepRGhYwcxEhMaSnZ3dKLCg3xNPEBcbNBjGEoTBDFZv"
);
export const VAULT_MANAGER_PROGRAM_ID = new PublicKey(
  "VltMgcHHAfKXkRBRyfzXhCZrN3NaE8kTGYhfPaCmjPQy"
);

// ── PDA Derivation Helpers ─────────────────────────────────────────

export function deriveOracleConfigPda(programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("oracle_config")], programId);
}

export function deriveAgentNodePda(authority: PublicKey, programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("agent_node"), authority.toBuffer()], programId);
}

export function deriveAgentIdentityMintPda(authority: PublicKey, programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("agent_identity"), authority.toBuffer()], programId);
}

export function deriveAgentStakeVaultPda(authority: PublicKey, programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("agent_stake_vault"), authority.toBuffer()], programId);
}

export function derivePriceFeedPda(assetPair: string, agent: PublicKey, programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("price_feed"), Buffer.from(assetPair), agent.toBuffer()],
    programId
  );
}

export function deriveConsensusRoundPda(assetPair: string, roundNum: number, programId: PublicKey = SWARM_ORACLE_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("consensus_round"), Buffer.from(assetPair), Buffer.from([roundNum])],
    programId
  );
}

export function deriveMarketConfigPda(programId: PublicKey = PREDICTION_MARKET_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("market_config")], programId);
}

export function deriveMarketPda(marketId: BN | number, programId: PublicKey = PREDICTION_MARKET_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("market"), new BN(marketId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function derivePredictionPda(marketId: BN | number, user: PublicKey, outcome: string, programId: PublicKey = PREDICTION_MARKET_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("prediction"), new BN(marketId).toArrayLike(Buffer, "le", 8), user.toBuffer(), Buffer.from(outcome)],
    programId
  );
}

export function deriveMarketTreasuryPda(programId: PublicKey = PREDICTION_MARKET_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("market_treasury")], programId);
}

export function deriveResolutionPda(marketId: BN | number, programId: PublicKey = PREDICTION_MARKET_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("resolution"), new BN(marketId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function deriveRegistryConfigPda(programId: PublicKey = REPUTATION_REGISTRY_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("registry_config")], programId);
}

export function deriveAgentReputationPda(agent: PublicKey, programId: PublicKey = REPUTATION_REGISTRY_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("agent_reputation"), agent.toBuffer()], programId);
}

export function deriveUserReputationPda(user: PublicKey, programId: PublicKey = REPUTATION_REGISTRY_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("user_reputation"), user.toBuffer()], programId);
}

export function deriveBadgePda(badgeId: BN | number, programId: PublicKey = REPUTATION_REGISTRY_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("badge"), new BN(badgeId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function deriveVaultConfigPda(programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("vault_config")], programId);
}

export function deriveVaultPda(vaultId: BN | number, programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("vault"), new BN(vaultId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function deriveVaultFundsPda(vaultId: BN | number, programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("vault_funds"), new BN(vaultId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function deriveVaultDepositPda(vaultId: BN | number, depositor: PublicKey, programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("vault_deposit"), new BN(vaultId).toArrayLike(Buffer, "le", 8), depositor.toBuffer()],
    programId
  );
}

export function deriveRebalanceRecordPda(recordId: BN | number, programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("rebalance_record"), new BN(recordId).toArrayLike(Buffer, "le", 8)],
    programId
  );
}

export function deriveWhitelistedAgentPda(agent: PublicKey, programId: PublicKey = VAULT_MANAGER_PROGRAM_ID): [PublicKey, number] {
  return PublicKey.findProgramAddressSync([Buffer.from("whitelisted_agent"), agent.toBuffer()], programId);
}

// ── SwarmOracleClient ─────────────────────────────────────────────

export class SwarmOracleClient {
  constructor(
    public program: anchor.Program,
    public connection: Connection
  ) {}

  get programId(): PublicKey {
    return this.program.programId;
  }

  async initialize(params: {
    authority: Keypair;
    minAgentsForConsensus: number;
    maxAgeSeconds: number;
    acceptableDeviationBps: number;
    slashRateBps: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    const [tokenMintPda] = PublicKey.findProgramAddressSync(
      [Buffer.from("agent_token_mint")],
      this.programId
    );

    return this.program.methods
      .initialize({
        minAgentsForConsensus: params.minAgentsForConsensus,
        maxAgeSeconds: params.maxAgeSeconds,
        acceptableDeviationBps: params.acceptableDeviationBps,
        slashRateBps: params.slashRateBps,
      })
      .accounts({
        config: configPda,
        agentTokenMint: tokenMintPda,
        authority: params.authority.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: SystemProgram.programId,
        rent: anchor.web3.SYSVAR_RENT_PUBKEY,
      })
      .signers([params.authority])
      .rpc();
  }

  async registerAgent(params: {
    authority: Keypair;
    name: string;
    agentType: { price: {} } | { risk: {} } | { marketMaker: {} } | { resolution: {} };
    stakeAmount: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    const [agentNodePda] = deriveAgentNodePda(params.authority.publicKey, this.programId);
    const [identityMintPda] = deriveAgentIdentityMintPda(params.authority.publicKey, this.programId);
    const [stakeVaultPda] = deriveAgentStakeVaultPda(params.authority.publicKey, this.programId);
    const [agentTokenAccount] = PublicKey.findProgramAddressSync(
      [Buffer.from("agent_token"), params.authority.publicKey.toBuffer()],
      this.programId
    );

    return this.program.methods
      .registerAgent(params.name, params.agentType, new BN(params.stakeAmount))
      .accounts({
        config: configPda,
        agentNode: agentNodePda,
        identityMint: identityMintPda,
        agentTokenAccount,
        stakeVault: stakeVaultPda,
        authority: params.authority.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: SystemProgram.programId,
        rent: anchor.web3.SYSVAR_RENT_PUBKEY,
      })
      .signers([params.authority])
      .rpc();
  }

  async submitPrice(params: {
    agentAuthority: Keypair;
    assetPair: string;
    price: number;
    confidence: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    const [agentNodePda] = deriveAgentNodePda(params.agentAuthority.publicKey, this.programId);
    const [priceFeedPda] = derivePriceFeedPda(
      params.assetPair,
      params.agentAuthority.publicKey,
      this.programId
    );

    return this.program.methods
      .submitPrice(params.assetPair, new BN(params.price), params.confidence)
      .accounts({
        config: configPda,
        agentNode: agentNodePda,
        priceFeed: priceFeedPda,
        agentAuthority: params.agentAuthority.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.agentAuthority])
      .rpc();
  }

  async runConsensus(params: {
    authority: Keypair;
    assetPair: string;
    priceFeeds: PublicKey[];
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    const [consensusRoundPda] = deriveConsensusRoundPda(
      params.assetPair,
      0, // round number
      this.programId
    );

    return this.program.methods
      .runConsensus(params.assetPair)
      .accounts({
        config: configPda,
        consensusRound: consensusRoundPda,
        authority: params.authority.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .remainingAccounts(
        params.priceFeeds.map((pk) => ({
          pubkey: pk,
          isSigner: false,
          isWritable: false,
        }))
      )
      .signers([params.authority])
      .rpc();
  }

  async updateAgentReputation(params: {
    authority: Keypair;
    agentAuthority: PublicKey;
    reputationDelta: number;
    accuracyDelta: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    const [agentNodePda] = deriveAgentNodePda(params.agentAuthority, this.programId);

    return this.program.methods
      .updateAgentReputation(params.reputationDelta, params.accuracyDelta)
      .accounts({
        config: configPda,
        agentNode: agentNodePda,
        agentAuthority: params.agentAuthority,
        authority: params.authority.publicKey,
      })
      .signers([params.authority])
      .rpc();
  }

  async fetchConfig(): Promise<any> {
    const [configPda] = deriveOracleConfigPda(this.programId);
    return this.program.account.oracleConfig.fetch(configPda);
  }

  async fetchAgentNode(authority: PublicKey): Promise<any> {
    const [agentNodePda] = deriveAgentNodePda(authority, this.programId);
    return this.program.account.agentNode.fetch(agentNodePda);
  }

  async fetchPriceFeed(assetPair: string, agent: PublicKey): Promise<any> {
    const [priceFeedPda] = derivePriceFeedPda(assetPair, agent, this.programId);
    return this.program.account.priceFeed.fetch(priceFeedPda);
  }
}

// ── PredictionMarketClient ─────────────────────────────────────────

export class PredictionMarketClient {
  constructor(
    public program: anchor.Program,
    public connection: Connection
  ) {}

  get programId(): PublicKey {
    return this.program.programId;
  }

  async initialize(params: {
    admin: Keypair;
    feeRateBps: number;
    maxMarkets: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveMarketConfigPda(this.programId);

    return this.program.methods
      .initialize(params.feeRateBps, params.maxMarkets)
      .accounts({
        config: configPda,
        admin: params.admin.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.admin])
      .rpc();
  }

  async createMarket(params: {
    creator: Keypair;
    question: string;
    description: string;
    outcomes: string[];
    endTime: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveMarketConfigPda(this.programId);
    const config = await this.program.account.marketConfig.fetch(configPda);
    const marketId = config.marketCount;
    const [marketPda] = deriveMarketPda(marketId, this.programId);
    const [treasuryPda] = deriveMarketTreasuryPda(this.programId);

    return this.program.methods
      .createMarket(params.question, params.description, params.outcomes, new BN(params.endTime))
      .accounts({
        config: configPda,
        market: marketPda,
        treasury: treasuryPda,
        creator: params.creator.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.creator])
      .rpc();
  }

  async submitPrediction(params: {
    user: Keypair;
    marketId: BN | number;
    outcome: string;
    amount: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveMarketConfigPda(this.programId);
    const [marketPda] = deriveMarketPda(params.marketId, this.programId);
    const [predictionPda] = derivePredictionPda(
      params.marketId,
      params.user.publicKey,
      params.outcome,
      this.programId
    );
    const [treasuryPda] = deriveMarketTreasuryPda(this.programId);

    return this.program.methods
      .submitPrediction(params.outcome, new BN(params.amount))
      .accounts({
        config: configPda,
        market: marketPda,
        prediction: predictionPda,
        user: params.user.publicKey,
        treasury: treasuryPda,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.user])
      .rpc();
  }

  async resolveMarket(params: {
    authority: Keypair;
    marketId: BN | number;
    winningOutcome: string;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveMarketConfigPda(this.programId);
    const [marketPda] = deriveMarketPda(params.marketId, this.programId);
    const [resolutionPda] = deriveResolutionPda(params.marketId, this.programId);

    return this.program.methods
      .resolveMarket(params.winningOutcome)
      .accounts({
        config: configPda,
        market: marketPda,
        resolution: resolutionPda,
        authority: params.authority.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.authority])
      .rpc();
  }

  async claimWinnings(params: {
    user: Keypair;
    marketId: BN | number;
    outcome: string;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveMarketConfigPda(this.programId);
    const [marketPda] = deriveMarketPda(params.marketId, this.programId);
    const [predictionPda] = derivePredictionPda(
      params.marketId,
      params.user.publicKey,
      params.outcome,
      this.programId
    );
    const [treasuryPda] = deriveMarketTreasuryPda(this.programId);

    return this.program.methods
      .claimWinnings()
      .accounts({
        config: configPda,
        market: marketPda,
        prediction: predictionPda,
        treasury: treasuryPda,
        user: params.user.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.user])
      .rpc();
  }

  async fetchConfig(): Promise<any> {
    const [configPda] = deriveMarketConfigPda(this.programId);
    return this.program.account.marketConfig.fetch(configPda);
  }

  async fetchMarket(marketId: BN | number): Promise<any> {
    const [marketPda] = deriveMarketPda(marketId, this.programId);
    return this.program.account.market.fetch(marketPda);
  }
}

// ── ReputationRegistryClient ───────────────────────────────────────

export class ReputationRegistryClient {
  constructor(
    public program: anchor.Program,
    public connection: Connection
  ) {}

  get programId(): PublicKey {
    return this.program.programId;
  }

  async initialize(params: {
    admin: Keypair;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveRegistryConfigPda(this.programId);

    return this.program.methods
      .initialize()
      .accounts({
        config: configPda,
        admin: params.admin.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.admin])
      .rpc();
  }

  async updateReputation(params: {
    authority: Keypair;
    agent: PublicKey;
    successful: boolean;
    accuracyDelta: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveRegistryConfigPda(this.programId);
    const [agentRepPda] = deriveAgentReputationPda(params.agent, this.programId);

    return this.program.methods
      .updateReputation(params.successful, params.accuracyDelta)
      .accounts({
        config: configPda,
        agentReputation: agentRepPda,
        agent: params.agent,
        authority: params.authority.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.authority])
      .rpc();
  }

  async recordPrediction(params: {
    authority: Keypair;
    user: PublicKey;
    correct: boolean;
    volume: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveRegistryConfigPda(this.programId);
    const [userRepPda] = deriveUserReputationPda(params.user, this.programId);

    return this.program.methods
      .recordPrediction(params.correct, new BN(params.volume))
      .accounts({
        config: configPda,
        userReputation: userRepPda,
        user: params.user,
        authority: params.authority.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.authority])
      .rpc();
  }

  async fetchAgentReputation(agent: PublicKey): Promise<any> {
    const [agentRepPda] = deriveAgentReputationPda(agent, this.programId);
    return this.program.account.agentReputation.fetch(agentRepPda);
  }

  async fetchUserReputation(user: PublicKey): Promise<any> {
    const [userRepPda] = deriveUserReputationPda(user, this.programId);
    return this.program.account.userReputation.fetch(userRepPda);
  }
}

// ── VaultManagerClient ─────────────────────────────────────────────

export class VaultManagerClient {
  constructor(
    public program: anchor.Program,
    public connection: Connection
  ) {}

  get programId(): PublicKey {
    return this.program.programId;
  }

  async initialize(params: {
    admin: Keypair;
    feeRateBps: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveVaultConfigPda(this.programId);

    return this.program.methods
      .initialize(params.feeRateBps)
      .accounts({
        config: configPda,
        admin: params.admin.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.admin])
      .rpc();
  }

  async createVault(params: {
    owner: Keypair;
    name: string;
    strategyType: { conservative: {} } | { balanced: {} } | { aggressive: {} };
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveVaultConfigPda(this.programId);
    const config = await this.program.account.vaultConfig.fetch(configPda);
    const vaultId = config.vaultCount;
    const [vaultPda] = deriveVaultPda(vaultId, this.programId);
    const [vaultFundsPda] = deriveVaultFundsPda(vaultId, this.programId);

    return this.program.methods
      .createVault(params.name, params.strategyType)
      .accounts({
        config: configPda,
        vault: vaultPda,
        vaultFunds: vaultFundsPda,
        owner: params.owner.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.owner])
      .rpc();
  }

  async deposit(params: {
    depositor: Keypair;
    vaultId: BN | number;
    amount: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveVaultConfigPda(this.programId);
    const [vaultPda] = deriveVaultPda(params.vaultId, this.programId);
    const [depositPda] = deriveVaultDepositPda(params.vaultId, params.depositor.publicKey, this.programId);
    const [vaultFundsPda] = deriveVaultFundsPda(params.vaultId, this.programId);

    return this.program.methods
      .deposit(new BN(params.amount))
      .accounts({
        config: configPda,
        vault: vaultPda,
        deposit: depositPda,
        vaultFunds: vaultFundsPda,
        depositor: params.depositor.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.depositor])
      .rpc();
  }

  async withdraw(params: {
    depositor: Keypair;
    vaultId: BN | number;
    shareAmount: number;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveVaultConfigPda(this.programId);
    const [vaultPda] = deriveVaultPda(params.vaultId, this.programId);
    const [depositPda] = deriveVaultDepositPda(params.vaultId, params.depositor.publicKey, this.programId);
    const [vaultFundsPda] = deriveVaultFundsPda(params.vaultId, this.programId);

    return this.program.methods
      .withdraw(new BN(params.shareAmount))
      .accounts({
        config: configPda,
        vault: vaultPda,
        deposit: depositPda,
        vaultFunds: vaultFundsPda,
        depositor: params.depositor.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.depositor])
      .rpc();
  }

  async rebalance(params: {
    agent: Keypair;
    vaultId: BN | number;
    fromAsset: string;
    toAsset: string;
    amount: number;
    reason: string;
  }): Promise<anchor.web3.TransactionSignature> {
    const [configPda] = deriveVaultConfigPda(this.programId);
    const [vaultPda] = deriveVaultPda(params.vaultId, this.programId);
    const [whitelistedPda] = deriveWhitelistedAgentPda(params.agent.publicKey, this.programId);
    const [recordPda] = deriveRebalanceRecordPda(0, this.programId);

    return this.program.methods
      .rebalance(params.fromAsset, params.toAsset, new BN(params.amount), params.reason)
      .accounts({
        config: configPda,
        vault: vaultPda,
        whitelisted: whitelistedPda,
        rebalanceRecord: recordPda,
        agent: params.agent.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([params.agent])
      .rpc();
  }

  async fetchConfig(): Promise<any> {
    const [configPda] = deriveVaultConfigPda(this.programId);
    return this.program.account.vaultConfig.fetch(configPda);
  }

  async fetchVault(vaultId: BN | number): Promise<any> {
    const [vaultPda] = deriveVaultPda(vaultId, this.programId);
    return this.program.account.vault.fetch(vaultPda);
  }

  async fetchDeposit(vaultId: BN | number, depositor: PublicKey): Promise<any> {
    const [depositPda] = deriveVaultDepositPda(vaultId, depositor, this.programId);
    return this.program.account.vaultDeposit.fetch(depositPda);
  }
}

// ── Convenience: Create all clients ────────────────────────────────

export interface SwarmFiClients {
  oracle: SwarmOracleClient;
  predictionMarket: PredictionMarketClient;
  reputation: ReputationRegistryClient;
  vault: VaultManagerClient;
}

export function createClients(
  provider: anchor.AnchorProvider,
  oracleProgram?: anchor.Program,
  marketProgram?: anchor.Program,
  reputationProgram?: anchor.Program,
  vaultProgram?: anchor.Program
): SwarmFiClients {
  return {
    oracle: new SwarmOracleClient(
      oracleProgram || (provider as any).program,
      provider.connection
    ),
    predictionMarket: new PredictionMarketClient(
      marketProgram || (provider as any).program,
      provider.connection
    ),
    reputation: new ReputationRegistryClient(
      reputationProgram || (provider as any).program,
      provider.connection
    ),
    vault: new VaultManagerClient(
      vaultProgram || (provider as any).program,
      provider.connection
    ),
  };
}
