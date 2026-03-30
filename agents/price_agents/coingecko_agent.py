"""SwarmFi CoinGecko Price Agent

Fetches cryptocurrency prices from the CoinGecko API.
"""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Dict, Optional

import aiohttp

from shared.logger import get_logger
from shared.types import PriceSubmission
from price_agents.base import BasePriceAgent


class CoinGeckoAgent(BasePriceAgent):
    """Fetches prices from the CoinGecko API.

    Uses the public CoinGecko v3 API to fetch real-time cryptocurrency
    prices. Falls back to demo mode simulation if API is unavailable.

    Attributes:
        base_url: CoinGecko API base URL.
        session: aiohttp client session.
        _rate_limit_remaining: Tracks API rate limit.
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Mapping from asset pair to CoinGecko IDs
    COINGECKO_IDS = {
        "BTC/USDT": "bitcoin",
        "ETH/USDT": "ethereum",
        "SOL/USDT": "solana",
        "AVAX/USDT": "avalanche-2",
        "DOT/USDT": "polkadot",
        "INIT/USDT": "initia",
    }

    def __init__(
        self,
        name: str = "CoinGecko Agent",
        agent_address: str = "coingecko_agent_001",
        stigmergy=None,
        demo_mode: bool = False,
    ) -> None:
        """Initialize the CoinGecko agent.

        Args:
            name: Agent name.
            agent_address: Agent identifier.
            stigmergy: Stigmergy field instance.
            demo_mode: Whether to generate simulated data.
        """
        super().__init__(name, agent_address, "coingecko", stigmergy)
        self._session: Optional[aiohttp.ClientSession] = None
        self._demo_mode = demo_mode
        self._price_cache: Dict[str, float] = {}
        self._logger = get_logger("PRICE/coingecko")

    async def fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch price from CoinGecko API or simulate in demo mode.

        Args:
            asset_pair: Trading pair (e.g. "BTC/USDT").

        Returns:
            PriceSubmission or None on failure.
        """
        if self._demo_mode:
            return await self._demo_fetch_price(asset_pair)

        return await self._live_fetch_price(asset_pair)

    async def _live_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch price from CoinGecko API.

        Args:
            asset_pair: Trading pair.

        Returns:
            PriceSubmission or None.
        """
        coin_id = self.COINGECKO_IDS.get(asset_pair)
        if not coin_id:
            self._logger.warning(f"Unknown asset pair: {asset_pair}")
            return None

        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
            )

        try:
            url = f"{self.BASE_URL}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_vol": "true",
                "include_last_updated_at": "true",
            }

            async with self._session.get(url, params=params) as resp:
                if resp.status == 429:
                    self._logger.warning("CoinGecko rate limit hit")
                    return self._cached_or_demo(asset_pair)
                resp.raise_for_status()
                data = await resp.json()

            coin_data = data.get(coin_id, {})
            price = coin_data.get("usd", 0.0)
            volume = coin_data.get("usd_24h_vol")

            if price <= 0:
                self._logger.warning(f"Invalid price from CoinGecko for {asset_pair}: {price}")
                return None

            self._price_cache[asset_pair] = price

            return PriceSubmission(
                asset_pair=asset_pair,
                price=price,
                confidence=0.90,
                source=self.source,
                agent_address=self.agent_address,
                volume_24h=volume,
                metadata={
                    "api": "coingecko_v3",
                    "coin_id": coin_id,
                },
            )

        except asyncio.TimeoutError:
            self._logger.warning(f"CoinGecko timeout for {asset_pair}")
            return self._cached_or_demo(asset_pair)
        except aiohttp.ClientError as e:
            self._logger.warning(f"CoinGecko HTTP error for {asset_pair}: {e}")
            return self._cached_or_demo(asset_pair)
        except Exception as e:
            self._logger.error(f"CoinGecko error for {asset_pair}: {e}")
            return self._cached_or_demo(asset_pair)

    async def _demo_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Generate simulated price data for demo mode.

        Uses a random walk around known base prices.

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

        # Random walk from last cached price
        last = self._price_cache.get(asset_pair, base)
        noise = random.gauss(0, base * 0.001)
        price = last + noise

        # CoinGecko has high accuracy
        price *= random.uniform(0.9998, 1.0002)
        price = max(price, base * 0.9)  # Floor at 90% of base
        price = min(price, base * 1.1)  # Ceiling at 110% of base

        self._price_cache[asset_pair] = price

        return PriceSubmission(
            asset_pair=asset_pair,
            price=round(price, 8),
            confidence=round(random.uniform(0.88, 0.95), 4),
            source=self.source,
            agent_address=self.agent_address,
            volume_24h=base * random.uniform(1000, 50000),
            metadata={"mode": "demo"},
        )

    def _cached_or_demo(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Return cached price or fall back to demo.

        Args:
            asset_pair: Trading pair.

        Returns:
            PriceSubmission from cache or demo.
        """
        if asset_pair in self._price_cache:
            price = self._price_cache[asset_pair]
            return PriceSubmission(
                asset_pair=asset_pair,
                price=price,
                confidence=0.7,  # Lower confidence for cached data
                source=f"{self.source}_cached",
                agent_address=self.agent_address,
                metadata={"mode": "cached"},
            )
        return None

    async def cleanup(self) -> None:
        """Clean up resources (close HTTP session)."""
        if self._session:
            await self._session.close()
            self._session = None
