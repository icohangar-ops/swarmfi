"""SwarmFi Chain Interface

Interface to submit agent data to SwarmFi CosmWasm contracts on Initia.
Includes a MockMode for demo/hackathon use without a live node.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, List, Optional

from shared.logger import COLORS, get_logger, log_kv, log_section
from shared.types import (
    PriceSubmission,
    RebalanceRecommendation,
    StigmergySignal,
    TxResponse,
)

logger = get_logger("CHAIN")


class InitiaChainInterface:
    """Submits agent data to SwarmFi CosmWasm contracts on Initia.

    For the hackathon demo, this includes a MockMode that simulates
    blockchain submissions without requiring a live node.

    In mock mode, all submissions are stored in memory and printed to
    the console with colored output for visual feedback.

    Attributes:
        rpc_url: Initia RPC endpoint URL.
        chain_id: Initia chain identifier.
        private_key: Agent private key for signing.
        mock_mode: Whether mock mode is enabled.
        _mock_submissions: Stored mock submissions.
    """

    def __init__(
        self,
        rpc_url: str = "https://rpc.testnet.initia.xyz",
        chain_id: str = "initiation-1",
        private_key: str = "",
        mock_mode: bool = False,
    ) -> None:
        """Initialize the chain interface.

        Args:
            rpc_url: Initia RPC endpoint URL.
            chain_id: Initia chain ID.
            private_key: Agent private key (hex string).
            mock_mode: Start in mock mode.
        """
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.private_key = private_key
        self.mock_mode = mock_mode

        self._mock_submissions: List[Dict[str, Any]] = []
        self._tx_counter = 0
        self._block_height = 1000000

        if mock_mode:
            logger.info("Mock mode enabled — submissions will be simulated")

    def enable_mock_mode(self) -> None:
        """Enable mock mode.

        In mock mode, no actual blockchain transactions are made.
        All submissions are stored in memory and logged to console.
        """
        self.mock_mode = True
        logger.info("Mock mode ENABLED")

    def disable_mock_mode(self) -> None:
        """Disable mock mode and attempt real blockchain submissions."""
        self.mock_mode = False
        logger.info("Mock mode DISABLED — live blockchain submissions enabled")

    def get_mock_submissions(self) -> List[Dict[str, Any]]:
        """Get all mock submissions made so far.

        Returns:
            List of mock submission dictionaries.
        """
        return list(self._mock_submissions)

    def clear_mock_submissions(self) -> None:
        """Clear all stored mock submissions."""
        self._mock_submissions.clear()

    async def submit_price(
        self,
        contract_addr: str,
        submission: PriceSubmission,
    ) -> TxResponse:
        """Submit a price oracle update to the contract.

        Args:
            contract_addr: The oracle contract address.
            submission: The price submission data.

        Returns:
            TxResponse with transaction details.
        """
        if self.mock_mode:
            return await self._mock_submit_price(contract_addr, submission)
        return await self._live_submit_price(contract_addr, submission)

    async def submit_stigmergy(
        self,
        contract_addr: str,
        signal: StigmergySignal,
    ) -> TxResponse:
        """Submit a stigmergy signal to the contract.

        Args:
            contract_addr: The stigmergy contract address.
            signal: The stigmergy signal data.

        Returns:
            TxResponse with transaction details.
        """
        if self.mock_mode:
            return await self._mock_submit_stigmergy(contract_addr, signal)
        return await self._live_submit_stigmergy(contract_addr, signal)

    async def trigger_rebalance(
        self,
        contract_addr: str,
        rec: RebalanceRecommendation,
    ) -> TxResponse:
        """Trigger a vault rebalance transaction.

        Args:
            contract_addr: The vault contract address.
            rec: The rebalance recommendation.

        Returns:
            TxResponse with transaction details.
        """
        if self.mock_mode:
            return await self._mock_trigger_rebalance(contract_addr, rec)
        return await self._live_trigger_rebalance(contract_addr, rec)

    async def resolve_market(
        self,
        contract_addr: str,
        market_id: str,
        outcome: str,
    ) -> TxResponse:
        """Resolve a prediction market.

        Args:
            contract_addr: The market contract address.
            market_id: The market to resolve.
            outcome: The winning outcome.

        Returns:
            TxResponse with transaction details.
        """
        if self.mock_mode:
            return await self._mock_resolve_market(contract_addr, market_id, outcome)
        return await self._live_resolve_market(contract_addr, market_id, outcome)

    def _generate_mock_tx_hash(self) -> str:
        """Generate a mock transaction hash.

        Returns:
            A mock hex transaction hash.
        """
        self._tx_counter += 1
        raw = f"mock_tx_{self._tx_counter}_{time.time()}"
        return "0x" + hashlib.sha256(raw.encode()).hexdigest()

    # ─── Mock Mode Implementations ────────────────────────────────────

    async def _mock_submit_price(
        self,
        contract_addr: str,
        submission: PriceSubmission,
    ) -> TxResponse:
        """Simulate a price submission in mock mode.

        Args:
            contract_addr: Contract address.
            submission: Price submission.

        Returns:
            Mock TxResponse.
        """
        self._block_height += 1
        tx_hash = self._generate_mock_tx_hash()

        mock_data = {
            "type": "submit_price",
            "contract": contract_addr,
            "asset_pair": submission.asset_pair,
            "price": submission.price,
            "confidence": submission.confidence,
            "source": submission.source,
            "agent": submission.agent_address,
            "tx_hash": tx_hash,
            "block": self._block_height,
            "timestamp": time.time(),
        }
        self._mock_submissions.append(mock_data)

        # Colored console output
        logger.opt(colors=True).info(
            f"{COLORS['GREEN']}✓{COLORS['RESET']} "
            f"{COLORS['BOLD']}PRICE ORACLE UPDATE{COLORS['RESET']}\n"
            f"  {COLORS['DIM']}Tx:{COLORS['RESET']} {tx_hash[:24]}...\n"
            f"  {COLORS['DIM']}Pair:{COLORS['RESET']} {submission.asset_pair}\n"
            f"  {COLORS['DIM']}Price:{COLORS['RESET']} ${submission.price:,.4f}\n"
            f"  {COLORS['DIM']}Conf:{COLORS['RESET']} {submission.confidence:.0%} "
            f"│ {COLORS['DIM']}Source:{COLORS['RESET']} {submission.source}\n"
            f"  {COLORS['DIM']}Agent:{COLORS['RESET']} {submission.agent_address[:16]}...\n"
            f"  {COLORS['DIM']}Block:{COLORS['RESET']} {self._block_height:,}"
        )

        return TxResponse(
            success=True,
            tx_hash=tx_hash,
            height=self._block_height,
            gas_used=65_000,
            data={"asset_pair": submission.asset_pair, "price": submission.price},
        )

    async def _mock_submit_stigmergy(
        self,
        contract_addr: str,
        signal: StigmergySignal,
    ) -> TxResponse:
        """Simulate a stigmergy submission in mock mode.

        Args:
            contract_addr: Contract address.
            signal: Stigmergy signal.

        Returns:
            Mock TxResponse.
        """
        self._block_height += 1
        tx_hash = self._generate_mock_tx_hash()

        targets_str = ", ".join(t.value for t in signal.target_agents) if signal.target_agents else "ALL"

        mock_data = {
            "type": "submit_stigmergy",
            "contract": contract_addr,
            "signal_type": signal.signal_type.value,
            "from_agent": signal.from_agent,
            "strength": signal.strength,
            "tx_hash": tx_hash,
            "block": self._block_height,
        }
        self._mock_submissions.append(mock_data)

        logger.opt(colors=True).info(
            f"{COLORS['YELLOW']}◆{COLORS['RESET']} "
            f"{COLORS['BOLD']}STIGMERGY SIGNAL{COLORS['RESET']}\n"
            f"  {COLORS['DIM']}Tx:{COLORS['RESET']} {tx_hash[:24]}...\n"
            f"  {COLORS['DIM']}Type:{COLORS['RESET']} {signal.signal_type.value}\n"
            f"  {COLORS['DIM']}From:{COLORS['RESET']} {signal.from_agent[:16]}...\n"
            f"  {COLORS['DIM']}Strength:{COLORS['RESET']} {signal.strength:.2f} │ "
            f"{COLORS['DIM']}Targets:{COLORS['RESET']} {targets_str}\n"
            f"  {COLORS['DIM']}Block:{COLORS['RESET']} {self._block_height:,}"
        )

        return TxResponse(
            success=True,
            tx_hash=tx_hash,
            height=self._block_height,
            gas_used=45_000,
            data={"signal_type": signal.signal_type.value},
        )

    async def _mock_trigger_rebalance(
        self,
        contract_addr: str,
        rec: RebalanceRecommendation,
    ) -> TxResponse:
        """Simulate a rebalance trigger in mock mode.

        Args:
            contract_addr: Contract address.
            rec: Rebalance recommendation.

        Returns:
            Mock TxResponse.
        """
        self._block_height += 1
        tx_hash = self._generate_mock_tx_hash()

        mock_data = {
            "type": "trigger_rebalance",
            "contract": contract_addr,
            "vault_id": rec.vault_id,
            "from_asset": rec.from_asset,
            "to_asset": rec.to_asset,
            "amount": rec.amount,
            "tx_hash": tx_hash,
            "block": self._block_height,
        }
        self._mock_submissions.append(mock_data)

        urgency_bar = "█" * int(rec.urgency * 10) + "░" * (10 - int(rec.urgency * 10))

        logger.opt(colors=True).info(
            f"{COLORS['RED']}⚡{COLORS['RESET']} "
            f"{COLORS['BOLD']}VAULT REBALANCE{COLORS['RESET']}\n"
            f"  {COLORS['DIM']}Tx:{COLORS['RESET']} {tx_hash[:24]}...\n"
            f"  {COLORS['DIM']}Vault:{COLORS['RESET']} {rec.vault_id}\n"
            f"  {COLORS['DIM']}Action:{COLORS['RESET']} {rec.amount:,.2f} {rec.from_asset} → {rec.to_asset}\n"
            f"  {COLORS['DIM']}Urgency:{COLORS['RESET']} [{urgency_bar}] {rec.urgency:.0%}\n"
            f"  {COLORS['DIM']}Reason:{COLORS['RESET']} {rec.reason}\n"
            f"  {COLORS['DIM']}Block:{COLORS['RESET']} {self._block_height:,}"
        )

        return TxResponse(
            success=True,
            tx_hash=tx_hash,
            height=self._block_height,
            gas_used=120_000,
            data={"vault_id": rec.vault_id},
        )

    async def _mock_resolve_market(
        self,
        contract_addr: str,
        market_id: str,
        outcome: str,
    ) -> TxResponse:
        """Simulate a market resolution in mock mode.

        Args:
            contract_addr: Contract address.
            market_id: Market identifier.
            outcome: Winning outcome.

        Returns:
            Mock TxResponse.
        """
        self._block_height += 1
        tx_hash = self._generate_mock_tx_hash()

        mock_data = {
            "type": "resolve_market",
            "contract": contract_addr,
            "market_id": market_id,
            "outcome": outcome,
            "tx_hash": tx_hash,
            "block": self._block_height,
        }
        self._mock_submissions.append(mock_data)

        logger.opt(colors=True).info(
            f"{COLORS['CYAN']}✦{COLORS['RESET']} "
            f"{COLORS['BOLD']}MARKET RESOLVED{COLORS['RESET']}\n"
            f"  {COLORS['DIM']}Tx:{COLORS['RESET']} {tx_hash[:24]}...\n"
            f"  {COLORS['DIM']}Market:{COLORS['RESET']} {market_id}\n"
            f"  {COLORS['DIM']}Outcome:{COLORS['RESET']} {COLORS['GREEN']}{outcome}{COLORS['RESET']}\n"
            f"  {COLORS['DIM']}Block:{COLORS['RESET']} {self._block_height:,}"
        )

        return TxResponse(
            success=True,
            tx_hash=tx_hash,
            height=self._block_height,
            gas_used=80_000,
            data={"market_id": market_id, "outcome": outcome},
        )

    # ─── Live Mode (Placeholder) ─────────────────────────────────────

    async def _live_submit_price(
        self,
        contract_addr: str,
        submission: PriceSubmission,
    ) -> TxResponse:
        """Submit price to live Initia blockchain.

        This is a placeholder that would use cosmpy or cosmjs
        to submit a real transaction to the CosmWasm contract.

        Args:
            contract_addr: Contract address.
            submission: Price submission.

        Returns:
            TxResponse from the blockchain.
        """
        logger.warning("Live blockchain submission not yet implemented")
        return TxResponse(
            success=False,
            error="Live submission not implemented",
        )

    async def _live_submit_stigmergy(
        self,
        contract_addr: str,
        signal: StigmergySignal,
    ) -> TxResponse:
        """Submit stigmergy signal to live Initia blockchain.

        Args:
            contract_addr: Contract address.
            signal: Stigmergy signal.

        Returns:
            TxResponse from the blockchain.
        """
        logger.warning("Live blockchain submission not yet implemented")
        return TxResponse(
            success=False,
            error="Live submission not implemented",
        )

    async def _live_trigger_rebalance(
        self,
        contract_addr: str,
        rec: RebalanceRecommendation,
    ) -> TxResponse:
        """Trigger rebalance on live Initia blockchain.

        Args:
            contract_addr: Contract address.
            rec: Rebalance recommendation.

        Returns:
            TxResponse from the blockchain.
        """
        logger.warning("Live blockchain submission not yet implemented")
        return TxResponse(
            success=False,
            error="Live submission not implemented",
        )

    async def _live_resolve_market(
        self,
        contract_addr: str,
        market_id: str,
        outcome: str,
    ) -> TxResponse:
        """Resolve market on live Initia blockchain.

        Args:
            contract_addr: Contract address.
            market_id: Market identifier.
            outcome: Winning outcome.

        Returns:
            TxResponse from the blockchain.
        """
        logger.warning("Live blockchain submission not yet implemented")
        return TxResponse(
            success=False,
            error="Live submission not implemented",
        )

    async def get_block_height(self) -> int:
        """Get the current block height.

        Returns:
            Current block height (mock or live).
        """
        if self.mock_mode:
            return self._block_height
        # Placeholder for live query
        return 0

    def get_total_mock_gas_used(self) -> int:
        """Get total gas used by all mock submissions.

        Returns:
            Total mock gas used.
        """
        return sum(s.get("gas_used", 0) for s in self._mock_submissions if isinstance(s, dict))
