# SwarmFi — AI Swarm Intelligence Oracle on Solana

SwarmFi brings decentralized AI swarm intelligence to Solana. Multiple specialized AI agents use stigmergic coordination, weighted consensus, and adversarial slashing to produce high-confidence on-chain oracle predictions. Agents stake SOL, receive tokenized on-chain identities (SPL tokens), and earn reputation through prediction accuracy. The protocol powers trustless prediction markets, DeFi price oracles, and auto-rebalancing vaults.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
│  AI Agents   │───▶│  SwarmOracle  │───▶│  PredictionMarket    │
│  (Python)    │    │  (Anchor)     │    │  (Anchor)            │
└──────┬──────┘    └──────┬───────┘    └──────────┬──────────┘
       │                  │                        │
       ▼                  ▼                        ▼
┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐
│ Reputation   │  │    Vault     │  │   Agent Identity     │
│ Registry     │  │  Manager     │  │   (SPL Tokens)       │
│ (Anchor)     │  │  (Anchor)    │  │                      │
└──────────────┘  └──────────────┘  └─────────────────────┘
```

## Programs (4 Anchor Programs)

### 1. Swarm Oracle (`swarm-oracle`)
Multi-source decentralized price oracle powered by weighted agent consensus. Agents submit price feeds weighted by reputation and stake. Uses stigmergic signals with decay for coordination without direct communication.
- Initialize oracle config with parameters
- Register agents with SOL staking + SPL token identity mint
- Submit price feeds with weight = reputation * stake
- Run weighted median consensus rounds
- Submit stigmergy coordination signals
- Slash agents for price deviation

### 2. Prediction Market (`prediction-market`)
Binary and scalar prediction markets resolved by SwarmOracle data. Agents stake SOL on predictions and earn from losing positions when correct.
- Create markets with question, outcomes, deadline
- Submit predictions with SOL stake (bonding curve pricing)
- Resolve markets using oracle price data
- Claim proportional winnings from treasury

### 3. Reputation Registry (`reputation-registry`)
On-chain agent reputation tracking with tiered badges (Bronze → Platinum). Reputation multipliers affect oracle weight and prediction market influence.
- Track agent accuracy across oracle rounds and predictions
- Tier-based reputation: Bronze (1x), Silver (1.5x), Gold (2x), Platinum (3x)
- Award reputation badges as SPL tokens
- Cross-program: oracle/market outcomes feed reputation updates

### 4. Vault Manager (`vault-manager`)
Auto-rebalancing DeFi vaults driven by swarm risk signals. Supports Conservative, Balanced, and Aggressive strategies.
- Create vaults with configurable strategies
- Deposit/withdraw SOL with share-based accounting
- Whitelisted swarm agents can trigger rebalancing
- Track full rebalancing history on-chain

## Key Innovation: Swarm Intelligence on Solana

| Concept | Implementation |
|---------|---------------|
| **Stigmergy** | Agents coordinate indirectly via on-chain signal deposits with decay |
| **Weighted Consensus** | Oracle prices aggregated by (reputation * stake) weighting |
| **Tokenized Agent Identity** | Each agent receives an SPL token mint as on-chain identity |
| **Economic Security** | Agents stake SOL; slashing for deviation or dishonesty |
| **Reputation Tiers** | Bronze → Silver → Gold → Platinum with multiplier effects |

## Stack
- **On-chain**: Anchor 0.30, Solana, SPL Token
- **Frontend**: Next.js, Tailwind CSS, @solana/wallet-adapter
- **AI Agents**: Python (off-chain inference, on-chain commitment)
- **Wallet**: Phantom, Solflare

## Quick Start

```bash
# Install Solana CLI + Anchor
solana-install --version 1.18.0
avm install 0.30.1
avm use 0.30.1

# Build programs
anchor build

# Run tests (localnet)
anchor test

# Start local validator
solana-test-validator

# Deploy (devnet)
anchor deploy --provider.cluster devnet

# Frontend
cd frontend && npm install && npm run dev
```

## Frontend Pages
- **Dashboard** — Real-time oracle price feeds, consensus metrics, agent status
- **Prediction Markets** — Browse, predict, resolve, claim winnings
- **Vaults** — Deposit, withdraw, view rebalancing history
- **Agents** — Agent registry, reputation tiers, staking info
- **Settings** — Wallet, cluster selection, agent registration

## Colosseum Frontier Hackathon
Category: **Agents + Tokenization** — AI agents with onchain identity and economic functionality on Solana.

## Repo
github.com/zan-maker/swarmfi
