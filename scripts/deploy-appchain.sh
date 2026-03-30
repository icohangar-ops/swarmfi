#!/usr/bin/env bash
#
# deploy-appchain.sh - SwarmFi Appchain Deployment on Initia Testnet
#
# This script automates the setup of the SwarmFi WasmVM appchain
# on the Initia testnet (initiation-2) using the Weave CLI.
#
# Usage:
#   chmod +x deploy-appchain.sh
#   ./deploy-appchain.sh           # Interactive mode
#   ./deploy-appchain.sh --install # Install prerequisites only
#   ./deploy-appchain.sh --reset   # Clean slate + fresh setup
#
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────
CHAIN_ID="swarmfi-1"
GAS_DENOM="uswarm"
MONIKER="swarmfi-operator"
VM="wasm"
WEAVE_VERSION="0.3.8"
L1_NETWORK="initiation-2"
GENESIS_BALANCE="1000000000000000000000000"  # 10^24 uswarm

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ── Helper Functions ───────────────────────────────────────────────────
info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

check_command() {
    if command -v "$1" &>/dev/null; then
        success "$1 is installed: $($1 --version 2>&1 | head -1)"
    else
        error "$1 is NOT installed. Please install it first."
    fi
}

separator() {
    echo -e "${CYAN}$(printf '─%.0s' {1..70})${NC}"
}

# ── Prerequisites Check ────────────────────────────────────────────────
check_prerequisites() {
    separator
    info "Checking prerequisites..."
    separator

    local missing=0

    if command -v go &>/dev/null; then
        local go_version=$(go version | grep -oP 'go\K[0-9]+\.[0-9]+')
        success "Go $(go version | grep -oP 'go[0-9.]+')"
        # Check Go >= 1.22
        local go_major=$(echo "$go_version" | cut -d. -f1)
        local go_minor=$(echo "$go_version" | cut -d. -f2)
        if [[ $go_major -lt 1 ]] || [[ $go_major -eq 1 && $go_minor -lt 22 ]]; then
            warn "Go version should be 1.22+. Current: $go_version"
            missing=1
        fi
    else
        warn "Go is NOT installed (needed to build minitiad from source)"
        warn "Install: https://go.dev/doc/install"
        missing=1
    fi

    if command -v docker &>/dev/null; then
        if docker info &>/dev/null 2>&1; then
            success "Docker is running: $(docker --version | grep -oP 'Docker version \K[0-9.]+')"
        else
            warn "Docker is installed but NOT running. Start it: sudo systemctl start docker"
            missing=1
        fi
    else
        warn "Docker is NOT installed (needed for IBC relayer)"
        warn "Install: https://docs.docker.com/engine/install/"
        missing=1
    fi

    if command -v docker-compose &>/dev/null || docker compose version &>/dev/null 2>&1; then
        success "Docker Compose is available"
    else
        warn "Docker Compose is NOT installed"
        missing=1
    fi

    if command -v lz4 &>/dev/null || dpkg -l | grep -q liblz4-1; then
        success "LZ4 compression is available"
    else
        warn "LZ4 is NOT installed. Install: apt-get install lz4 (Ubuntu) or brew install lz4 (macOS)"
        missing=1
    fi

    if [[ $missing -eq 1 ]]; then
        echo ""
        warn "Some prerequisites are missing. You can continue, but some features may not work."
        warn "Run './deploy-appchain.sh --install' to attempt auto-installation."
    fi
}

# ── Install Weave CLI ──────────────────────────────────────────────────
install_weave() {
    separator
    info "Installing Weave CLI v${WEAVE_VERSION}..."
    separator

    if command -v weave &>/dev/null; then
        local current_version=$(weave version 2>&1 || echo "unknown")
        if [[ "$current_version" == *"$WEAVE_VERSION"* ]]; then
            success "Weave CLI v${WEAVE_VERSION} is already installed"
            return 0
        else
            info "Updating Weave CLI from ${current_version} to v${WEAVE_VERSION}..."
        fi
    fi

    local arch=$(uname -m)
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')

    if [[ "$arch" == "x86_64" ]]; then
        arch="amd64"
    elif [[ "$arch" == "aarch64" ]]; then
        arch="arm64"
    else
        error "Unsupported architecture: $arch"
    fi

    local download_url="https://github.com/initia-labs/weave/releases/download/v${WEAVE_VERSION}/weave-${WEAVE_VERSION}-${os}-${arch}.tar.gz"
    local tmp_dir=$(mktemp -d)

    info "Downloading from: ${download_url}"
    wget -q --show-progress -O "${tmp_dir}/weave.tar.gz" "${download_url}" || \
        error "Failed to download Weave CLI"

    info "Extracting..."
    tar -xzf "${tmp_dir}/weave.tar.gz" -C "${tmp_dir}"

    info "Installing to /usr/local/bin/..."
    chmod +x "${tmp_dir}/weave"
    sudo mv "${tmp_dir}/weave" /usr/local/bin/weave 2>/dev/null || \
        mkdir -p "$HOME/.local/bin" && mv "${tmp_dir}/weave" "$HOME/.local/bin/weave" && \
        export PATH="$HOME/.local/bin:$PATH"

    rm -rf "${tmp_dir}"

    success "Weave CLI v$(weave version 2>&1) installed successfully!"
}

# ── Create SwarmFi Rollup Config ───────────────────────────────────────
create_rollup_config() {
    separator
    info "Creating SwarmFi rollup configuration..."
    separator

    local config_dir="${SCRIPT_DIR:-.}/config"
    mkdir -p "$config_dir"

    local config_file="${config_dir}/swarmfi-rollup.json"

    cat > "$config_file" << EOF
{
  "l2_config": {
    "chain_id": "${CHAIN_ID}",
    "denom": "${GAS_DENOM}",
    "moniker": "${MONIKER}"
  },
  "op_bridge": {
    "output_submission_interval": "30s",
    "output_finalization_period": "300s",
    "batch_submission_target": "initia",
    "enable_oracle": true
  }
}
EOF

    success "Rollup config created at: ${config_file}"
    echo ""
    info "Config contents:"
    cat "$config_file"
    echo ""
}

# ── Gas Station Setup ──────────────────────────────────────────────────
setup_gas_station() {
    separator
    info "Setting up Gas Station account..."
    separator

    if weave gas-station show &>/dev/null; then
        warn "Gas Station is already configured"
        weave gas-station show
        echo ""
        read -p "Do you want to reconfigure? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi

    info "Running: weave gas-station setup"
    info "Select 'Generate new account' when prompted."
    info ""
    warn "IMPORTANT: Save the mnemonic phrase securely!"
    info "After setup, fund the Initia address with at least 10 INIT from the testnet faucet."
    info "Faucet: https://discord.gg/initia or https://app.initia.xyz/faucet"
    echo ""

    weave gas-station setup

    echo ""
    success "Gas Station configured!"
    weave gas-station show
}

# ── Launch Rollup ──────────────────────────────────────────────────────
launch_rollup() {
    separator
    info "Launching SwarmFi rollup (${CHAIN_ID})..."
    separator

    local config_file="${SCRIPT_DIR:-.}/config/swarmfi-rollup.json"

    if [[ -f "$config_file" ]]; then
        info "Using config file: ${config_file}"
        info "Running: weave rollup launch --with-config ${config_file} --vm ${VM}"
        weave rollup launch --with-config "$config_file" --vm "$VM"
    else
        info "No config file found. Running interactive setup..."
        info "Running: weave init"
        echo ""
        info "When prompted, use these settings:"
        info "  - Action: Launch a new rollup"
        info "  - L1 Network: Testnet (initiation-2)"
        info "  - VM: ${VM}"
        info "  - Chain ID: ${CHAIN_ID}"
        info "  - Gas Denom: ${GAS_DENOM}"
        info "  - Moniker: ${MONIKER}"
        info "  - Submission Interval: 30s (default)"
        info "  - Finalization Period: 300s (default)"
        info "  - Data Availability: Initia L1"
        info "  - Oracle: Enable"
        info "  - System Keys: Generate new"
        info "  - Genesis Balance: ${GENESIS_BALANCE}"
        echo ""

        weave init
    fi

    success "SwarmFi rollup launched!"
    echo ""
}

# ── Setup OPinit Executor ─────────────────────────────────────────────
setup_opinit() {
    separator
    info "Setting up OPinit Executor..."
    separator

    info "Running: weave opinit init"
    info "When prompted:"
    info "  - Use detected keys: Yes"
    info "  - System key for Oracle: Generate new system key"
    info "  - Pre-fill data: Yes"
    info "  - Listen address: localhost:3000 (default)"
    echo ""

    weave opinit init

    info "Starting OPinit Executor..."
    weave opinit start

    success "OPinit Executor started!"
    echo ""
}

# ── Setup IBC Relayer ─────────────────────────────────────────────────
setup_relayer() {
    separator
    info "Setting up IBC Relayer..."
    separator

    if ! docker info &>/dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
    fi

    info "Running: weave relayer init"
    info "When prompted:"
    info "  - Rollup type: Local Rollup (${CHAIN_ID})"
    info "  - L1 RPC: http://localhost:26657 (default)"
    info "  - L1 LCD: http://localhost:1317 (default)"
    info "  - Channel method: Subscribe to transfer and nft-transfer"
    info "  - Channels: Select all"
    info "  - Challenger key: Yes"
    echo ""

    weave relayer init

    info "Starting IBC Relayer..."
    weave relayer start

    success "IBC Relayer started!"
    echo ""
}

# ── Import Gas Station Key ────────────────────────────────────────────
import_gas_station_key() {
    separator
    info "Importing Gas Station key for development..."
    separator

    local config_file="$HOME/.weave/config.json"

    if [[ ! -f "$config_file" ]]; then
        error "Weave config not found at ${config_file}. Run gas station setup first."
    fi

    local mnemonic
    mnemonic=$(jq -r '.common.gas_station.mnemonic // empty' "$config_file" 2>/dev/null)

    if [[ -z "$mnemonic" ]]; then
        error "Could not extract mnemonic from weave config."
    fi

    if command -v initiad &>/dev/null; then
        info "Importing into initiad (L1)..."
        echo "$mnemonic" | initiad keys add gas-station --recover --keyring-backend test \
            --coin-type 118 --key-type eth_secp256k1 2>/dev/null || true
        success "Gas Station key imported into initiad (L1)"
    else
        warn "initiad not found. Skipping L1 key import."
    fi

    if command -v minitiad &>/dev/null; then
        info "Importing into minitiad (L2)..."
        echo "$mnemonic" | minitiad keys add gas-station --recover --keyring-backend test \
            --coin-type 118 --key-type eth_secp256k1 2>/dev/null || true
        success "Gas Station key imported into minitiad (L2)"
    else
        warn "minitiad not found. Skipping L2 key import."
    fi

    echo ""
}

# ── Verify Deployment ─────────────────────────────────────────────────
verify_deployment() {
    separator
    info "Verifying SwarmFi deployment..."
    separator

    echo ""
    info "Gas Station Status:"
    weave gas-station show 2>/dev/null || warn "Could not query gas station"

    echo ""
    info "Rollup Status (RPC):"
    if curl -sf http://localhost:26657/status 2>/dev/null | jq -r '.result.node_info' 2>/dev/null; then
        success "Rollup RPC is responding"
    else
        warn "Rollup RPC is not responding at http://localhost:26657"
    fi

    echo ""
    info "Rollup Endpoints:"
    echo "  RPC:    http://localhost:26657"
    echo "  REST:   http://localhost:1317"
    echo "  gRPC:   localhost:9090"
    echo ""
    success "Deployment verification complete!"
}

# ── Reset Everything ──────────────────────────────────────────────────
reset_all() {
    separator
    warn "This will DELETE all Weave, Initia, Minitia, and OPinit data!"
    warn "This action cannot be undone."
    echo ""
    read -p "Type 'CONFIRM' to proceed: " -r
    echo ""

    if [[ "$REPLY" != "CONFIRM" ]]; then
        info "Aborted."
        exit 0
    fi

    info "Removing ~/.weave..."
    rm -rf ~/.weave

    info "Removing ~/.initia..."
    rm -rf ~/.initia

    info "Removing ~/.minitia..."
    rm -rf ~/.minitia

    info "Removing ~/.opinit..."
    rm -rf ~/.opinit

    info "Stopping weave-relayer Docker container..."
    docker rm -f weave-relayer 2>/dev/null || true

    success "All data has been reset!"
}

# ── Auto-Install Dependencies ─────────────────────────────────────────
auto_install() {
    separator
    info "Attempting to install prerequisites..."
    separator

    if [[ "$(uname -s)" == "Linux" ]]; then
        info "Detected Linux. Using apt-get..."

        if ! command -v go &>/dev/null; then
            info "Installing Go 1.22..."
            wget -q https://go.dev/dl/go1.22.0.linux-amd64.tar.gz -O /tmp/go.tar.gz
            sudo tar -C /usr/local -xzf /tmp/go.tar.gz
            rm /tmp/go.tar.gz
            export PATH=$PATH:/usr/local/go/bin
            echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
            success "Go installed"
        fi

        if ! command -v lz4 &>/dev/null; then
            info "Installing LZ4..."
            sudo apt-get update -qq && sudo apt-get install -y -qq lz4
            success "LZ4 installed"
        fi

        if ! command -v docker &>/dev/null; then
            warn "Docker requires manual installation: https://docs.docker.com/engine/install/"
        fi
    elif [[ "$(uname -s)" == "Darwin" ]]; then
        info "Detected macOS. Using Homebrew..."
        if ! command -v brew &>/dev/null; then
            error "Homebrew not installed. Install from: https://brew.sh"
        fi

        brew install go lz4 2>/dev/null || true
        brew install --cask docker 2>/dev/null || warn "Docker Desktop requires manual install"
    fi

    success "Auto-installation complete!"
}

# ── Main ──────────────────────────────────────────────────────────────
main() {
    # Resolve script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║           SwarmFi Appchain Deployer for Initia Testnet              ║${NC}"
    echo -e "${CYAN}║                                                                      ║${NC}"
    echo -e "${CYAN}║  Chain ID: ${CHAIN_ID}$(printf ' %.0s' $(seq 1 $((42 - ${#CHAIN_ID}))))║${NC}"
    echo -e "${CYAN}║  VM:      ${VM}$(printf ' %.0s' $(seq 1 $((42 - ${#VM}))))║${NC}"
    echo -e "${CYAN}║  Denom:   ${GAS_DENOM}$(printf ' %.0s' $(seq 1 $((42 - ${#GAS_DENOM}))))║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    case "${1:-}" in
        --install)
            auto_install
            install_weave
            exit 0
            ;;
        --reset)
            reset_all
            exit 0
            ;;
        --weave-only)
            install_weave
            exit 0
            ;;
        --config-only)
            create_rollup_config
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  (none)       Full interactive deployment"
            echo "  --install    Install prerequisites + Weave CLI"
            echo "  --weave-only Install Weave CLI only"
            echo "  --config-only Create rollup config file only"
            echo "  --reset      Delete all data and start fresh"
            echo "  --help       Show this help"
            exit 0
            ;;
    esac

    # Step 1: Check prerequisites
    check_prerequisites
    echo ""

    # Step 2: Install Weave CLI
    install_weave
    echo ""

    # Step 3: Create rollup config
    create_rollup_config
    echo ""

    # Step 4: Gas Station setup (interactive)
    setup_gas_station
    echo ""

    # Step 5: Bootstrap Initia node
    separator
    info "Bootstrapping Initia full node..."
    separator
    if [[ ! -d "$HOME/.initia" ]]; then
        weave initia init
        success "Initia node bootstrapped!"
    else
        warn "Initia node already configured at ~/.initia"
        info "To reset: weave initia stop && rm -rf ~/.initia"
    fi
    echo ""

    # Step 6: Launch the SwarmFi rollup
    launch_rollup
    echo ""

    # Step 7: OPinit Executor
    setup_opinit
    echo ""

    # Step 8: IBC Relayer
    setup_relayer
    echo ""

    # Step 9: Import keys
    import_gas_station_key
    echo ""

    # Step 10: Verify
    verify_deployment

    separator
    success "=========================================="
    success "  SwarmFi Appchain Deployment Complete!"
    success "=========================================="
    separator
    echo ""
    info "Your SwarmFi appchain is running with:"
    info "  Chain ID:  ${CHAIN_ID}"
    info "  RPC:       http://localhost:26657"
    info "  REST:      http://localhost:1317"
    info "  gRPC:      localhost:9090"
    echo ""
    info "Next steps:"
    info "  1. Verify the rollup is producing blocks: weave rollup log"
    info "  2. Check gas station balance: weave gas-station show"
    info "  3. View relayer logs: weave relayer log"
    info "  4. Start building your SwarmFi smart contracts!"
    echo ""
    info "To restart after reboot:"
    info "  weave initia start"
    info "  weave rollup start"
    info "  weave opinit start"
    info "  weave relayer start"
    echo ""
}

main "$@"
