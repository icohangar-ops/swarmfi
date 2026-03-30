"""SwarmFi DEX Aggregator Price Agent

Aggregates prices from decentralized exchange on-chain data.
In demo mode, simulates DEX price data.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import get_logger
from shared.types import PriceSubmission
from price_agents.base import BasePriceAgent


class DEXAgent(BasePriceAgent):
    """Aggregates prices from DEX on-chain data.

    In production, this would query multiple DEXes (Osmosis, Astroport,
    etc.) via RPC calls and aggregate the best prices.

    For demo mode, it simulates DEX prices with realistic spreads
    and slippage characteristics.

    Attributes:
        _dex_sources: List of simulated DEX sources.
        _price_cache: Cached prices per DEX source.
        _logger: Agent logger instance.
    """

    # Simulated DEX sources
    DEX_SOURCES = [
        {"name": "Osmosis", "fee_bps": 30, "reliability": 0.85},
        {"name": "Astroport", "fee_bps": 25, "reliability": 0.88},
        {"name": "WhiteWhale", "fee_bps": 35, "reliability": 0.75},
        {"name": "Diffusion", "fee_bps": 20, "reliability": 0.80},
    ]

    def __init__(
        self,
        name: str = "DEX Aggregator Agent",
        agent_address: str = "dex_agent_001",
        stigmergy=None,
        demo_mode: bool = False,
    ) -> None:
        """Initialize the DEX agent.

        Args:
            name: Agent name.
            agent_address: Agent identifier.
            stigmergy: Stigmergy field instance.
            demo_mode: Whether to generate simulated data.
        """
        super().__init__(name, agent_address, "dex_aggregator", stigmergy)
        self._demo_mode = demo_mode
        self._price_cache: Dict[str, Dict[str, float]] = {}
        self._logger = get_logger("PRICE/dex")

    async def fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch aggregated DEX price or simulate in demo mode.

        Args:
            asset_pair: Trading pair (e.g. "BTC/USDT").

        Returns:
            PriceSubmission with aggregated price.
        """
        if self._demo_mode:
            return await self._demo_fetch_price(asset_pair)
        return await self._live_fetch_price(asset_pair)

    async def _live_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch live DEX prices via on-chain queries.

        In a real implementation, this would query smart contracts
        on multiple DEXes via Initia RPC.

        Args:
            asset_pair: Trading pair.

        Returns:
            PriceSubmission or None.
        """
        # Placeholder: use demo mode until live DEX queries are implemented
        self._logger.info("Live DEX queries not yet implemented, using simulation")
        return await self._demo_fetch_price(asset_pair)

    async def _demo_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Generate simulated DEX prices with realistic characteristics.

        Simulates multiple DEX sources and aggregates them using
        volume-weighted average price (VWAP).

        Args:
            asset_pair: Trading pair.

        Returns:
            Simulated PriceSubmission.
        """
        base_prices = {
            "BTC/USDT": 67500.0,
            "ETH/USDT": 3450.0,
            "SOL/USDT": 178.0,
            "AVAX/USDT": 38.0,
            "INIT/USDT": 0.45,
            "DOT/USDT": 7.5,
        }

        base = base_prices.get(asset_pair, 100.0)

        # Generate prices from each DEX source
        dex_prices: List[Tuple[str, float, float]] = []  # (name, price, volume)

        for dex in self.DEX_SOURCES:
            # Each DEX has slightly different price due to fees and liquidity
            fee_impact = dex["fee_bps"] / 10000
            noise = random.gauss(0, base * 0.003)
            spread = random.uniform(-fee_impact * 2, fee_impact * 2)

            dex_price = base + noise + (base * spread)
            dex_price = max(dex_price, 0.0001)

            # Simulate volume (higher reliability = more volume)
            volume = base * random.uniform(100, 1000) * dex["reliability"]

            dex_prices.append((dex["name"], dex_price, volume))

        # VWAP calculation
        total_volume = sum(v for _, _, v in dex_prices)
        if total_volume == 0:
            return None

        vwap = sum(p * v for _, p, v in dex_prices) / total_volume

        # Confidence based on agreement between sources
        prices_only = [p for _, p, _ in dex_prices]
        price_range = max(prices_only) - min(prices_only)
        spread_pct = price_range / vwap if vwap > 0 else 1.0
        confidence = max(0.5, min(0.95, 1.0 - spread_pct * 10))

        # Cache for display
        self._price_cache[asset_pair] = {
            dex[0]: price for dex, price, _ in [
                ((name, price), price) for name, price, _ in dex_prices
            ]
        }

        self._logger.debug(
            f"DEX VWAP for {asset_pair}: ${vwap:,.4f} "
            f"(spread={spread_pct:.4f}, sources={len(dex_prices)})"
        )

        return PriceSubmission(
            asset_pair=asset_pair,
            price=round(vwap, 8),
            confidence=round(confidence, 4),
            source=self.source,
            agent_address=self.agent_address,
            volume_24h=total_volume,
            metadata={
                "mode": "demo",
                "sources": len(dex_prices),
                "vwap": vwap,
                "dex_spread_pct": round(spread_pct, 6),
                "per_dex": {
                    name: {"price": round(p, 8), "volume": round(v, 2)}
                    for name, p, v in dex_prices
                },
            },
        )

    async def fetch_from_single_dex(
        self,
        asset_pair: str,
        dex_name: str,
    ) -> Optional[float]:
        """Fetch price from a single DEX source.

        Args:
            asset_pair: Trading pair.
            dex_name: Name of the DEX.

        Returns:
            Price from the DEX, or None.
        """
        cached = self._price_cache.get(asset_pair, {})
        return cached.get(dex_name)
