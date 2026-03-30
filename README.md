# SwarmFi

AI swarm intelligence DeFi protocol on Initia. Agents coordinate via stigmergy to power decentralized oracles, prediction markets, and auto-rebalancing vaults. Built as an OPinit WasmVM rollup with CosmWasm and Python AI agents.

## Modules
- Swarm Oracle: Multi-source price feeds via weighted consensus
- Prediction Markets: Binary & scalar markets with AI resolution
- Vault Manager: Auto-rebalancing vaults driven by swarm risk
- Reputation Registry: On-chain agent scoring with slashing
- Bridge Adapter: Cross-chain routing via Interwoven Bridge

## Initia
InterwovenKit wallet SDK, Interwoven Bridge IBC, Auto-signing, OPinit

## Stack
CosmWasm (Rust), Next.js 15, Python, interwovenkit-react

## Run
cd frontend && npm i && npm run dev
cd agents && pip i -r requirements.txt && python -m orchestrator.main

Deploy: swarmfi-1 | uswarm | WasmVM | docs/DEPLOYMENT.md
Repo: github.com/zan-maker/swarmfi | Demo: docs/demo/swarmfi-demo.mp4
