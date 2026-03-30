"""SwarmFi Base Price Agent

Abstract base class for all price data agents. Each concrete agent
fetches price data from a specific source and submits it for consensus.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from shared.logger import COLORS, get_logger
from shared.stigmergy import StigmergyField
from shared.types import (
    AgentType,
    PriceSubmission,
    SignalType,
    StigmergySignal,
)


class BasePriceAgent(ABC):
    """Base class for all price data agents.

    Each agent:
    1. Periodically fetches price data from its source
    2. Deposits a stigmergy signal with its findings
    3. Senses other agents' signals to adjust its confidence
    4. Submits price to consensus via the orchestrator

    Attributes:
        name: Human-readable agent name.
        agent_address: Unique identifier for this agent.
        source: Identifier of the data source.
        stigmergy: Shared stigmergy field for communication.
        _running: Whether the agent is currently running.
        _last_prices: Cache of last fetched prices.
        _submission_callback: Callback to submit prices to orchestrator.
    """

    def __init__(
        self,
        name: str,
        agent_address: str,
        source: str,
        stigmergy: Optional[StigmergyField] = None,
    ) -> None:
        """Initialize the base price agent.

        Args:
            name: Human-readable agent name.
            agent_address: Unique agent identifier / address.
            source: Data source identifier.
            stigmergy: Shared stigmergy field instance.
        """
        self.name = name
        self.agent_address = agent_address
        self.source = source
        self.stigmergy = stigmergy
        self._running = False
        self._last_prices: Dict[str, float] = {}
        self._submission_callback: Optional[callable] = None
        self._logger = get_logger(f"PRICE/{source}")

    def set_submission_callback(self, callback: callable) -> None:
        """Set the callback for submitting prices to the orchestrator.

        Args:
            callback: Async function accepting a PriceSubmission.
        """
        self._submission_callback = callback

    async def run(
        self,
        assets: List[str],
        interval: int = 30,
    ) -> None:
        """Main agent loop. Periodically fetches and submits prices.

        Args:
            assets: List of asset pairs to fetch prices for.
            interval: Seconds between fetch cycles.
        """
        self._running = True
        self._logger.info(
            f"{self.name} starting: assets={assets}, interval={interval}s"
        )

        while self._running:
            try:
                cycle_start = time.time()

                # Sense other agents' signals to adjust confidence
                await self.sense_and_adapt()

                # Fetch prices for all assets
                for asset in assets:
                    try:
                        submission = await self.fetch_price(asset)
                        if submission:
                            await self.deposit_signal(submission)
                            await self._submit(submission)
                            self._last_prices[asset] = submission.price
                    except Exception as e:
                        self._logger.error(
                            f"Error fetching {asset} price: {e}"
                        )

                # Deposit heartbeat
                if self.stigmergy:
                    await self.stigmergy.deposit_signal(
                        StigmergySignal(
                            signal_type=SignalType.HEARTBEAT,
                            from_agent=self.agent_address,
                            data={"agent": self.name, "source": self.source},
                            strength=0.2,
                            decay_rate=0.5,
                            ttl_seconds=60.0,
                        )
                    )

                # Sleep for remaining interval
                elapsed = time.time() - cycle_start
                sleep_time = max(0, interval - elapsed)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Agent loop error: {e}")
                await asyncio.sleep(5)

        self._logger.info(f"{self.name} stopped")

    def stop(self) -> None:
        """Signal the agent to stop its main loop."""
        self._running = False

    @abstractmethod
    async def fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch the current price for an asset pair.

        Must be implemented by subclasses.

        Args:
            asset_pair: Trading pair (e.g. "BTC/USDT").

        Returns:
            PriceSubmission with the fetched price, or None on failure.
        """
        ...

    async def sense_and_adapt(self) -> None:
        """Sense other agents' stigmergy signals and adjust behavior.

        Reads signals from the stigmergy field to adjust confidence
        based on what other price agents have found.
        """
        if not self.stigmergy:
            return

        try:
            signals = await self.stigmergy.sense_signals(
                agent_type=AgentType.PRICE,
                signal_type=SignalType.PRICE_UPDATE,
                min_strength=0.1,
                limit=20,
            )

            if signals:
                # Adjust internal state based on signals
                for signal in signals:
                    if signal.from_agent == self.agent_address:
                        continue
                    data = signal.data
                    asset = data.get("asset_pair", "")
                    other_price = data.get("price", 0)

                    if asset in self._last_prices and other_price > 0:
                        my_price = self._last_prices[asset]
                        deviation = abs(my_price - other_price) / other_price

                        if deviation > 0.01:
                            self._logger.debug(
                                f"Price deviation detected for {asset}: "
                                f"mine={my_price:.4f} other={other_price:.4f} "
                                f"dev={deviation:.2%}"
                            )

        except Exception as e:
            self._logger.debug(f"Error sensing signals: {e}")

    async def deposit_signal(self, submission: PriceSubmission) -> None:
        """Deposit a stigmergy signal about the price fetch.

        Args:
            submission: The price submission to signal about.
        """
        if not self.stigmergy:
            return

        signal = StigmergySignal(
            signal_type=SignalType.PRICE_UPDATE,
            from_agent=self.agent_address,
            data={
                "asset_pair": submission.asset_pair,
                "price": submission.price,
                "confidence": submission.confidence,
                "source": self.source,
            },
            strength=submission.confidence * 0.8,
            target_agents=[AgentType.PRICE],
            decay_rate=0.15,
            ttl_seconds=120.0,
        )

        await self.stigmergy.deposit_signal(signal)

    async def _submit(self, submission: PriceSubmission) -> None:
        """Submit a price submission to the orchestrator.

        Args:
            submission: The price submission.
        """
        if self._submission_callback:
            try:
                if asyncio.iscoroutinefunction(self._submission_callback):
                    await self._submission_callback(submission)
                else:
                    self._submission_callback(submission)
            except Exception as e:
                self._logger.error(f"Submission callback error: {e}")
