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


class _RateLimited(Exception):
    """Internal marker raised on an HTTP 429 from CoinGecko."""


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

    # Defaults mirror AgentConfig; can be overridden via constructor.
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_FETCH_INTERVAL = 15.0
    # Base backoff (seconds) for the exponential retry loop.
    _BACKOFF_BASE = 0.5
    _BACKOFF_CAP = 8.0

    def __init__(
        self,
        name: str = "CoinGecko Agent",
        agent_address: str = "coingecko_agent_001",
        stigmergy=None,
        demo_mode: bool = False,
        max_retries: int = DEFAULT_MAX_RETRIES,
        fetch_interval: float = DEFAULT_FETCH_INTERVAL,
    ) -> None:
        """Initialize the CoinGecko agent.

        Args:
            name: Agent name.
            agent_address: Agent identifier.
            stigmergy: Stigmergy field instance.
            demo_mode: Whether to generate simulated data.
            max_retries: Max retry attempts for transient HTTP failures
                (honors AgentConfig.max_retries).
            fetch_interval: Expected seconds between fetch cycles. Cached
                fallback prices older than 2x this value are treated as
                stale and excluded from consensus.
        """
        super().__init__(name, agent_address, "coingecko", stigmergy)
        self._session: Optional[aiohttp.ClientSession] = None
        self._demo_mode = demo_mode
        self._price_cache: Dict[str, float] = {}
        # Wall-clock timestamp of when each cached price was last refreshed.
        self._price_cache_ts: Dict[str, float] = {}
        self._max_retries = max(0, int(max_retries))
        self._fetch_interval = float(fetch_interval)
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

        # Bounded exponential-backoff retry loop honoring max_retries.
        # Total attempts = max_retries + 1 (initial try plus retries).
        last_error: Optional[Exception] = None
        attempts = self._max_retries + 1
        for attempt in range(attempts):
            try:
                return await self._fetch_once(asset_pair, coin_id)
            except _RateLimited:
                # Rate limiting is unlikely to clear within a few hundred ms;
                # fall back to cached/demo immediately rather than hammering.
                self._logger.warning("CoinGecko rate limit hit")
                return self._cached_or_demo(asset_pair)
            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                last_error = e
                if attempt < attempts - 1:
                    delay = self._backoff_delay(attempt)
                    self._logger.warning(
                        f"CoinGecko transient error for {asset_pair} "
                        f"(attempt {attempt + 1}/{attempts}): {e}; "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                self._logger.warning(
                    f"CoinGecko failed for {asset_pair} after {attempts} "
                    f"attempt(s): {e}"
                )
            except Exception as e:
                # Non-transient error: do not retry.
                self._logger.error(f"CoinGecko error for {asset_pair}: {e}")
                return self._cached_or_demo(asset_pair)

        # Exhausted retries on transient failures.
        return self._cached_or_demo(asset_pair)

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with full jitter, capped.

        Args:
            attempt: Zero-based attempt index.

        Returns:
            Delay in seconds before the next retry.
        """
        ceiling = min(self._BACKOFF_CAP, self._BACKOFF_BASE * (2 ** attempt))
        return random.uniform(0.0, ceiling)

    async def _fetch_once(self, asset_pair: str, coin_id: str) -> Optional[PriceSubmission]:
        """Perform a single CoinGecko price fetch.

        Args:
            asset_pair: Trading pair.
            coin_id: CoinGecko coin identifier.

        Returns:
            PriceSubmission on success, or None for a non-retryable bad payload.

        Raises:
            _RateLimited: On HTTP 429.
            asyncio.TimeoutError / aiohttp.ClientError: On transient failures
                (caught by the retry loop).
        """
        url = f"{self.BASE_URL}/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_vol": "true",
            "include_last_updated_at": "true",
        }

        async with self._session.get(url, params=params) as resp:
            if resp.status == 429:
                raise _RateLimited()
            resp.raise_for_status()
            data = await resp.json()

        coin_data = data.get(coin_id, {})
        price = coin_data.get("usd", 0.0)
        volume = coin_data.get("usd_24h_vol")

        if price <= 0:
            self._logger.warning(f"Invalid price from CoinGecko for {asset_pair}: {price}")
            return None

        self._price_cache[asset_pair] = price
        self._price_cache_ts[asset_pair] = time.time()

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
                "stale": False,
            },
        )

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
        self._price_cache_ts[asset_pair] = time.time()

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

        Cached fallbacks carry a staleness timestamp. If the cached value is
        older than 2x the fetch interval it is marked stale so the consensus
        engine can exclude it.

        Args:
            asset_pair: Trading pair.

        Returns:
            PriceSubmission from cache or demo.
        """
        if asset_pair in self._price_cache:
            price = self._price_cache[asset_pair]
            cached_at = self._price_cache_ts.get(asset_pair, 0.0)
            age = time.time() - cached_at if cached_at else float("inf")
            stale_after = 2.0 * self._fetch_interval
            is_stale = age > stale_after

            if is_stale:
                self._logger.warning(
                    f"Cached CoinGecko price for {asset_pair} is stale "
                    f"(age={age:.1f}s > {stale_after:.1f}s); "
                    f"excluding from consensus"
                )

            return PriceSubmission(
                asset_pair=asset_pair,
                price=price,
                # Lower confidence for cached data; lower still when stale.
                confidence=0.3 if is_stale else 0.7,
                source=f"{self.source}_cached",
                agent_address=self.agent_address,
                metadata={
                    "mode": "cached",
                    "stale": is_stale,
                    "cache_age_seconds": round(age, 3) if cached_at else None,
                    "cached_at": cached_at or None,
                },
            )
        return None

    async def cleanup(self) -> None:
        """Clean up resources (close HTTP session)."""
        if self._session:
            await self._session.close()
            self._session = None
