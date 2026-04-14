#!/bin/bash
# SwarmFi Solana Deployment Script
echo "=== Deploying SwarmFi Protocol to Solana ==="

# Build all programs
echo "Building Anchor programs..."
anchor build

# Deploy to localnet
echo "Deploying to localnet..."
anchor deploy --provider.cluster localnet

echo "=== SwarmFi deployment complete ==="
echo "Oracle Program ID: FsWBMoA5x5bSaZGJGYeCsSWaaBGJ4eCqGMPbQnMBnKNp"
echo "Prediction Market Program ID: PMkt1SxPMKp3f5xLKNJghKBBm9JvHZQCEMJKWGPn7x4D"
echo "Reputation Registry Program ID: RepRGhYwcxEhMaSnZ3dKLCg3xNPEBcbNBjGEoTBDFZv"
echo "Vault Manager Program ID: VltMgcHHAfKXkRBRyfzXhCZrN3NaE8kTGYhfPaCmjPQy"
