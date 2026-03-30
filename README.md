# SwarmFi — AI Swarm Intelligence DeFi Protocol on Initia

> Decentralized oracles, prediction markets, and auto-rebalancing vaults powered by stigmergy-based multi-agent coordination on the Initia appchain.

## Overview

SwarmFi is a DeFi protocol that harnesses **swarm intelligence** — the collective problem-solving behavior observed in ant colonies, bee swarms, and bird flocks — to create more resilient, accurate, and adaptive financial infrastructure. Built as an **OPinit optimistic rollup** on Initia using **WasmVM (CosmWasm)**, SwarmFi coordinates autonomous AI agents through a **stigmergy** mechanism (indirect communication via shared environment state) to power three core DeFi primitives: a decentralized oracle system, prediction markets, and auto-rebalancing yield vaults.

## Problem

DeFi today suffers from three critical failures: **oracle centralization** (single-point-of-failure price feeds), **prediction market illiquidity** (low participation and slow resolution), and **vault stagnation** (yield strategies that don't adapt to changing market conditions). Existing solutions rely on centralized operators, static strategies, and isolated data sources. SwarmFi addresses all three by deploying a self-coordinating swarm of specialized AI agents that continuously monitor, analyze, and act on-chain — without any single point of control.

## Solution

SwarmFi uses a multi-agent swarm architecture inspired by ant colony optimization. Each agent type (price feeders, risk analyzers, market makers, resolution agents) operates independently but coordinates through **stigmergy** — reading and writing to shared contract state rather than communicating directly. This produces emergent intelligence that is more robust, fault-tolerant, and adaptive than any single AI model or centralized operator.

### Core Modules

| Module | Description | Smart Contract |
|--------|-------------|----------------|
| **Swarm Oracle** | Multi-source price feeds aggregated via weighted consensus from CoinGecko, DEX, and news sentiment agents | `swarm-oracle` |
| **Prediction Markets** | Create, trade, and resolve binary and scalar markets with AI-assisted resolution | `prediction-market` |
| **Vault Manager** | Auto-rebalancing yield vaults that shift strategies based on real-time swarm risk analysis | `vault-manager` |
| **Reputation Registry** | On-chain agent reputation scoring and slashing for misbehavior | `reputation-registry` |
| **Bridge Adapter** | Cross-chain asset routing via Initia's Interwoven Bridge (L1 ↔ L2) | `bridge-adapter` |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Initia L1 (initiation-2)                    │
│   Gas Station ←→ OPinit Bots (Executor/Challenger) ←→ IBC      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────▼──────────────────┐
                │   SwarmFi Appchain (swarmfi-1) │
                │        WasmVM Rollup           │
                │                                │
                │  ┌──────────────────────────┐ │
                │  │  CosmWasm Contracts       │ │
                │  │  (5 core modules)        │ │
                │  └──────────┬───────────────┘ │
                │             │                  │
                │  ┌──────────▼───────────────┐ │
                │  │  AI Agent Swarm          │ │
                │  │  (Python orchestrator)   │ │
                │  │  - Price Agents (×3)     │ │
                │  │  - Risk Agents (×2)      │ │
                │  │  - Market Maker Agents   │ │
                │  │  - Resolution Agents     │ │
                │  └──────────────────────────┘ │
                └────────────────────────────────┘
```

## Initia Integration

SwarmFi leverages multiple Initia-native features:

- **InterwovenKit** (`@initia/interwovenkit-react`): Wallet connection and transaction handling across L1 and L2
- **Interwoven Bridge**: Cross-chain asset transfers between Initia L1 and SwarmFi L2 via IBC
- **Auto-signing / Session UX**: Enables autonomous agent operations without repeated wallet approvals
- **OPinit**: Optimistic rollup with fraud proofs for L2 security
- **.init Usernames**: Planned identity integration for agent and user profiles

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Appchain** | OPinit rollup on Initia (initiation-2) via Weave CLI |
| **Smart Contracts** | CosmWasm (Rust) — WasmVM track |
| **Frontend** | Next.js 15, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| **AI Agents** | Python (asyncio), stigmergy-based coordination |
| **Wallet SDK** | `@initia/interwovenkit-react` |
| **Cross-chain** | IBC relayer (Docker), Interwoven Bridge |

## Repository Structure

```
swarmfi/
├── .initia/
│   └── submission.json          # Hackathon submission metadata
├── frontend/                     # Next.js 15 SPA
│   ├── src/
│   │   ├── app/                  # 6 pages: Home, Dashboard, Markets, Vaults, Agents, Settings
│   │   ├── components/           # SwarmVisualization, Navbar, Footer, Sidebar
│   │   ├── hooks/                # useWallet hook
│   │   └── lib/                  # wallet.tsx, mock-data.ts
│   └── package.json
├── contracts/                    # 5 CosmWasm contracts (Rust)
│   ├── swarm-oracle/
│   ├── prediction-market/
│   ├── vault-manager/
│   ├── reputation-registry/
│   └── bridge-adapter/
├── agents/                       # Python AI swarm system
│   ├── orchestrator/             # Agent manager, health monitor
│   ├── price_agents/             # CoinGecko, DEX, news sentiment agents
│   ├── risk_agents/              # Risk analysis agents
│   ├── market_maker_agents/      # Automated market making
│   ├── resolution_agents/        # Market resolution agents
│   └── shared/                   # Stigmergy, consensus, config, chain interface
├── config/
│   └── swarmfi-rollup.json       # Rollup configuration
├── scripts/
│   └── deploy-appchain.sh        # Automated deployment script
├── docs/
│   ├── DEPLOYMENT.md             # Step-by-step Initia testnet deployment guide
│   └── demo/
│       ├── swarmfi-demo.mp4      # 41-second demo video
│       └── screenshots/          # 6 UI screenshots
└── assets/
    └── swarmfi-logo.png          # 1024×1024 project logo
```

## Quick Start

### Prerequisites

- Node.js 18+, npm
- Python 3.10+
- Docker + Docker Compose (for appchain deployment)
- Go 1.22+ (for building minitiad binary)
- Weave CLI v0.3.8+

### Frontend

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### AI Agents

```bash
cd agents
pip install -r requirements.txt
python -m orchestrator.main
```

### Appchain Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the complete step-by-step guide to deploy SwarmFi as an Interwoven Rollup on Initia testnet (`initiation-2`).

**Chain ID**: `swarmfi-1` | **Gas Denom**: `uswarm` | **VM**: WasmVM

### Automated Deployment

```bash
chmod +x scripts/deploy-appchain.sh
./scripts/deploy-appchain.sh
```

## Key Innovation: Stigmergy-Based Coordination

Unlike traditional multi-agent systems that communicate directly (and create bottlenecks), SwarmFi agents coordinate through **stigmergy** — reading and writing to shared CosmWasm contract state. This mirrors how ant colonies communicate through pheromone trails. Each agent:

1. **Senses**: Reads current market data from oracle contracts
2. **Evaluates**: Applies its specialized logic (price analysis, risk assessment, etc.)
3. **Acts**: Writes its assessment to contract state (e.g., price vote, risk score)
4. **Emerges**: The collective agent outputs produce superior aggregation (prices, predictions, strategy decisions)

This approach is inherently fault-tolerant (individual agent failures don't cascade), scalable (agents can join/leave dynamically), and resilient (no single point of failure).

## Demo

[Video Demo](docs/demo/swarmfi-demo.mp4) — 41-second walkthrough of the SwarmFi dashboard, prediction markets, vaults, and live agent monitoring.

## Links

- **GitHub**: [https://github.com/zan-maker/swarmfi](https://github.com/zan-maker/swarmfi)
- **BUIDL Plan**: [https://github.com/zan-maker/initiate-buidl-plan](https://github.com/zan-maker/initiate-buidl-plan)
- **Initia Docs**: [https://docs.initia.xyz](https://docs.initia.xyz)
- **Hackathon**: [https://dorahacks.io/hackathon/initiate](https://dorahacks.io/hackathon/initiate)

## License

MIT
