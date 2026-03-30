# SwarmFi Appchain Deployment on Initia Testnet

## Overview

This document describes how to deploy the **SwarmFi** appchain as an Interwoven Rollup on the Initia testnet (`initiation-2`). SwarmFi uses the **WasmVM** (Rust/CosmWasm) track for its smart contracts and backend-heavy AI/tooling features.

**Chain ID:** `swarmfi-1`
**Gas Denom:** `uswarm`
**L1 Network:** Initia Testnet (`initiation-2`)
**VM Type:** WasmVM

---

## Prerequisites

Before running the deployment, ensure your machine has:

| Requirement | Version | Purpose |
|---|---|---|
| **Operating System** | Linux or macOS | Weave CLI support |
| **Go** | 1.22+ | Building appchain binaries (minitiad) |
| **Docker + Docker Compose** | Latest | Running IBC relayer |
| **Node.js + npm** | 18+ | Optional: relayer on same machine |
| **LZ4** | Any | Compression tool (`apt-get install lz4` or `brew install lz4`) |
| **curl / wget** | Any | Downloading binaries |

### Verify Prerequisites

```bash
go version          # go1.22+ or higher
docker --version    # Docker Engine
docker compose version
node --version      # v18+ (optional)
npm --version       # (optional)
lz4 --version       # or just verify lz4 is installed
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Initia L1 (initiation-2)                    │
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐ │
│   │ Gas Station   │    │ OPinit Bots  │    │  IBC Relayer (Docker)│ │
│   │ (funds infra) │───>│  - Executor  │    │  (L1 <-> L2 bridge)  │ │
│   └──────────────┘    │  - Challenger│    └──────────────────────┘ │
│                        └──────┬───────┘                │            │
└───────────────────────────────│────────────────────────│────────────┘
                                │                        │
                    ┌───────────▼────────────────────────▼────────┐
                    │        SwarmFi Appchain (swarmfi-1)          │
                    │        WasmVM Rollup                         │
                    │                                              │
                    │   ┌────────────┐  ┌─────────────────────┐   │
                    │   │  minitiad  │  │  CosmWasm Contracts  │   │
                    │   │  (full node)│  │  (SwarmFi logic)    │   │
                    │   └────────────┘  └─────────────────────┘   │
                    │                                              │
                    │   RPC:  http://localhost:26657               │
                    │   LCD:  http://localhost:1317                │
                    │   gRPC: localhost:9090                        │
                    └──────────────────────────────────────────────┘
```

---

## Quick Start (Automated Script)

Run the full deployment script:

```bash
chmod +x scripts/deploy-appchain.sh
./scripts/deploy-appchain.sh
```

Or use the Weave CLI interactively (recommended for first-time setup):

```bash
weave init
```

---

## Manual Step-by-Step Deployment

### Step 1: Install Weave CLI

```bash
# Download the latest Weave binary (v0.3.8)
VERSION=$(curl -s https://api.github.com/repos/initia-labs/weave/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
wget https://github.com/initia-labs/weave/releases/download/v${VERSION}/weave-${VERSION}-linux-amd64.tar.gz
tar -xzf weave-${VERSION}-linux-amd64.tar.gz
chmod +x weave
sudo mv weave /usr/local/bin/

# Verify installation
weave version
```

**macOS alternative:**
```bash
brew install initia-labs/tap/weave
```

### Step 2: Set Up the Gas Station Account

The Gas Station is a dedicated L1 account that funds infrastructure components (OPinit bots, IBC relayer).

```bash
weave gas-station setup
```

Select **"Generate new account"** when prompted. **Save the mnemonic securely!**

After generation, you'll see two addresses:
- **Initia address** (starts with `init1...`)
- **Celestia address** (starts with `celestia1...`)

**Fund the Initia address** with at least **10 INIT tokens** from the testnet faucet:
- Go to: https://discord.gg/initia (faucet channel)
- Or use the Initia testnet faucet: https://app.initia.xyz/faucet

### Step 3: Bootstrap the Initia Node

```bash
weave initia init
```

This will:
1. Set up an Initia full node configuration
2. Start syncing with the `initiation-2` testnet
3. Save config to `~/.initia/config.toml` and `~/.initia/app.toml`

### Step 4: Launch the SwarmFi Rollup

#### Option A: Interactive Setup (Recommended)

```bash
weave init
```

When prompted, select:

| Prompt | Selection |
|---|---|
| Action | **Launch a new rollup** |
| L1 Network | **Testnet (initiation-2)** |
| Virtual Machine | **WasmVM** |
| Rollup Chain ID | `swarmfi-1` |
| Rollup Gas Denom | `uswarm` (or press Enter for default) |
| Node Moniker | `swarmfi-operator` (or your preferred name) |
| Submission Interval | `30s` (default) |
| Finalization Period | `300s` (default) |
| Data Availability | **Initia L1** |
| Oracle Price Feed | **Enable** |
| System Keys | **Generate new system keys** |
| System Accounts Funding | **Use the default preset** |
| Fee Whitelist | Leave empty (press Enter) |
| Add Gas Station to Genesis | **Yes** |
| Genesis Balance | `1000000000000000000000000` (10^24) |
| Additional Genesis Accounts | **No** |

Confirm with `continue` and then `y` to broadcast transactions.

#### Option B: Config File Deployment

Create a config file at `config/swarmfi-rollup.json`:

```json
{
  "l2_config": {
    "chain_id": "swarmfi-1",
    "denom": "uswarm",
    "moniker": "swarmfi-operator"
  },
  "op_bridge": {
    "output_submission_interval": "30s",
    "output_finalization_period": "300s",
    "batch_submission_target": "initia",
    "enable_oracle": true
  },
  "genesis_accounts": [
    {
      "address": "<YOUR_GAS_STATION_ADDRESS>",
      "coins": "1000000000000000000000000uswarm"
    }
  ]
}
```

Then launch:

```bash
weave rollup launch --with-config config/swarmfi-rollup.json --vm wasm
```

### Step 5: Start the OPinit Executor

```bash
weave opinit init
```

When prompted:
- Use detected keys: **Yes**
- System key for Oracle: **Generate new system key**
- Pre-fill data: **Yes**
- Listen address: `localhost:3000` (default)

Start the executor:
```bash
weave opinit start
```

### Step 6: Start the IBC Relayer

**Docker must be running!**

```bash
weave relayer init
```

When prompted:
- Rollup type: **Local Rollup (swarmfi-1)**
- L1 RPC: `http://localhost:26657` (default)
- L1 LCD: `http://localhost:1317` (default)
- Channel method: **Subscribe to transfer and nft-transfer IBC Channels**
- Channels: Select all (transfer + nft-transfer)
- Challenger key: **Yes**

Start the relayer:
```bash
weave relayer start
```

### Step 7: Import the Gas Station Key for Development

```bash
# Extract mnemonic from weave config
MNEMONIC=$(jq -r '.common.gas_station.mnemonic' ~/.weave/config.json)

# Import into initiad (L1) - for sending txs to L1
initiad keys add gas-station --recover --keyring-backend test --coin-type 118 --key-type eth_secp256k1 <<< "$MNEMONIC"

# Import into minitiad (L2) - for deploying contracts on SwarmFi
minitiad keys add gas-station --recover --keyring-backend test --coin-type 118 --key-type eth_secp256k1 <<< "$MNEMONIC"

# Verify
initiad keys list --keyring-backend test
minitiad keys list --keyring-backend test
```

### Step 8: Verify Everything is Running

```bash
# Check rollup status
curl -s http://localhost:26657/status | jq

# Check gas station balance
weave gas-station show

# View rollup logs
weave rollup log

# View relayer logs
weave relayer log
```

---

## Rollup Endpoints

After successful deployment, your SwarmFi appchain will be available at:

| Service | URL |
|---|---|
| **RPC** | `http://localhost:26657` |
| **REST/LCD** | `http://localhost:1317` |
| **gRPC** | `localhost:9090` |
| **JSON-RPC (EVM compat)** | `http://localhost:8545` |
| **JSON-RPC-WS** | `ws://localhost:8545` |

---

## Useful Weave CLI Commands

```bash
# General
weave version                    # Show weave version
weave analytics disable          # Disable telemetry

# Gas Station
weave gas-station setup          # Setup gas station account
weave gas-station show           # Show addresses and balances

# Rollup Management
weave rollup start               # Start rollup node
weave rollup stop                # Stop rollup node
weave rollup restart             # Restart rollup node
weave rollup log                 # Stream rollup logs

# OPinit Bots
weave opinit init                # Configure OPinit bot
weave opinit start               # Start OPinit bot
weave opinit stop                # Stop OPinit bot
weave opinit restart             # Restart OPinit bot
weave opinit log                 # Stream OPinit logs

# IBC Relayer
weave relayer init               # Configure IBC relayer
weave relayer start              # Start relayer
weave relayer stop               # Stop relayer
weave relayer restart            # Restart relayer
weave relayer log                # Stream relayer logs
```

---

## Resetting / Starting Fresh

To completely reset and start a new appchain:

```bash
rm -rf ~/.weave ~/.initia ~/.minitia ~/.opinit
docker rm -f weave-relayer 2>/dev/null
weave init
```

---

## Troubleshooting

### "Cannot connect to Docker daemon"
- Ensure Docker Desktop is running (`docker info`)
- On Linux: `sudo systemctl start docker`

### "Insufficient balance"
- Fund your Gas Station account with more INIT from the faucet

### "Port already in use"
- Check what's using port 26657: `lsof -i :26657`
- Stop existing services: `weave rollup stop`

### "minitiad binary not found"
- The binary is downloaded automatically by `weave init` during rollup launch
- Ensure Go 1.22+ is installed for building from source if auto-download fails

### InitiaScan Explorer Link
After launching, Weave provides an InitiaScan magic link to view your rollup in the block explorer.

---

## Security Notes

> **WARNING**: This setup is for **hackathon / rapid prototyping only**.

- Mnemonics are stored in `~/.weave/config.json` in plaintext
- `--keyring-backend test` is used (insecure, file-based)
- For production: use OS keychain, hardware wallets, separate accounts for Gas Station / Validator / Developer roles

---

## References

- [Initia Docs - Set Up Your Appchain](https://docs.initia.xyz/developers/developer-guides/tools/clis/weave-cli/installation)
- [Weave CLI GitHub](https://github.com/initia-labs/weave)
- [Initia Testnet Faucet](https://discord.gg/initia)
- [Initiate Hackathon Guide](https://docs.initia.xyz/developers/developer-guides/initiate-hackathon/get-started)
- [Weave CLI Rollup Launch](https://docs.initia.xyz/developers/developer-guides/tools/clis/weave-cli/rollup/launch)
