"""SwarmFi News Sentiment Price Agent

Estimates price impact from news sentiment analysis.
Uses keyword matching and simple NLP for demo mode.
"""

from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import get_logger
from shared.types import PriceSubmission
from price_agents.base import BasePriceAgent


class NewsAgent(BasePriceAgent):
    """Analyzes news sentiment to estimate price impact.

    In production, this would connect to news APIs (CryptoPanic,
    NewsAPI, etc.) and use a sentiment model to estimate price impact.

    For demo mode, it simulates news events and applies sentiment
    scoring to estimate price adjustments.

    Attributes:
        _sentiment_keywords: Keyword-to-sentiment mapping.
        _base_prices: Base prices for simulation.
        _price_cache: Cache of estimated prices.
        _news_buffer: Buffer of recent simulated news.
        _logger: Agent logger.
    """

    # Keyword sentiment mapping: keyword -> (sentiment_score, impact_factor)
    SENTIMENT_KEYWORDS: Dict[str, Tuple[float, float]] = {
        # Bullish
        "bullish": (0.8, 0.005),
        "breakout": (0.9, 0.008),
        "adoption": (0.7, 0.004),
        "partnership": (0.6, 0.003),
        "etf": (0.8, 0.006),
        "halving": (0.9, 0.010),
        "upgrade": (0.5, 0.002),
        "mainnet": (0.7, 0.005),
        "institutional": (0.6, 0.004),
        "rally": (0.8, 0.005),
        "surge": (0.7, 0.006),
        # Bearish
        "bearish": (-0.8, 0.005),
        "crash": (-0.9, 0.010),
        "hack": (-0.9, 0.012),
        "sec": (-0.5, 0.003),
        "ban": (-0.8, 0.008),
        "regulation": (-0.4, 0.002),
        "dump": (-0.7, 0.006),
        "liquidation": (-0.6, 0.004),
        "fraud": (-0.8, 0.008),
        "vulnerability": (-0.7, 0.005),
        # Neutral / volatility
        "volatile": (0.0, 0.003),
        "uncertain": (-0.2, 0.002),
        "fomc": (-0.1, 0.004),
        "fed": (-0.1, 0.003),
    }

    # Simulated news headlines for demo
    DEMO_HEADLINES: List[str] = [
        "Bitcoin ETF sees record inflows as institutional adoption accelerates",
        "Ethereum upgrade promises 10x scalability improvement",
        "Major exchange reports security vulnerability, users urged to transfer funds",
        "SEC delays decision on crypto ETF applications",
        "New partnership between DeFi protocol and major bank announced",
        "Bitcoin halving event approaches, miners prepare for reward reduction",
        "Crypto market experiences volatile trading amid FOMC uncertainty",
        "Hackers exploit bridge vulnerability, millions stolen",
        "SOL network achieves new throughput milestone with mainnet upgrade",
        "Regulatory crackdown fears cause market-wide sell-off",
        "Bullish sentiment returns as crypto rally gains momentum",
        "Central bank signals potential interest rate changes",
        "New institutional investor enters the crypto space with $500M allocation",
        "DeFi protocol suffers flash loan attack, liquidity impacted",
        "Blockchain adoption surges in developing nations",
    ]

    def __init__(
        self,
        name: str = "News Sentiment Agent",
        agent_address: str = "news_agent_001",
        stigmergy=None,
        demo_mode: bool = False,
    ) -> None:
        """Initialize the News Sentiment agent.

        Args:
            name: Agent name.
            agent_address: Agent identifier.
            stigmergy: Stigmergy field instance.
            demo_mode: Whether to generate simulated data.
        """
        super().__init__(name, agent_address, "news_sentiment", stigmergy)
        self._demo_mode = demo_mode
        self._price_cache: Dict[str, float] = {}
        self._news_buffer: List[Dict[str, Any]] = []
        self._logger = get_logger("PRICE/news")

    async def fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Estimate price based on news sentiment.

        Args:
            asset_pair: Trading pair (e.g. "BTC/USDT").

        Returns:
            PriceSubmission with sentiment-adjusted price estimate.
        """
        if self._demo_mode:
            return await self._demo_fetch_price(asset_pair)
        return await self._live_fetch_price(asset_pair)

    async def _live_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Fetch news and analyze sentiment from live sources.

        Args:
            asset_pair: Trading pair.

        Returns:
            PriceSubmission or None.
        """
        # Placeholder for live news API integration
        self._logger.info("Live news analysis not yet implemented, using simulation")
        return await self._demo_fetch_price(asset_pair)

    async def _demo_fetch_price(self, asset_pair: str) -> Optional[PriceSubmission]:
        """Simulate news sentiment analysis.

        Generates random news headlines, analyzes sentiment,
        and applies estimated price impact.

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

        # Pick a random headline
        headline = random.choice(self.DEMO_HEADLINES)

        # Analyze sentiment
        sentiment_score, impact = self._analyze_sentiment(headline)

        # Calculate price impact
        last = self._price_cache.get(asset_pair, base)
        price_change = last * impact * sentiment_score
        estimated_price = last + price_change

        # Add noise
        noise = random.gauss(0, base * 0.004)
        estimated_price += noise

        # Keep within bounds
        estimated_price = max(estimated_price, base * 0.85)
        estimated_price = min(estimated_price, base * 1.15)

        self._price_cache[asset_pair] = estimated_price

        # Confidence based on sentiment clarity
        abs_sentiment = abs(sentiment_score)
        confidence = 0.4 + (abs_sentiment * 0.4) + random.uniform(-0.05, 0.05)
        confidence = max(0.3, min(0.8, confidence))

        # Store news event
        self._news_buffer.append({
            "headline": headline,
            "sentiment": sentiment_score,
            "impact": impact,
            "asset": asset_pair,
            "timestamp": time.time(),
        })

        # Keep buffer manageable
        if len(self._news_buffer) > 50:
            self._news_buffer = self._news_buffer[-50:]

        self._logger.debug(
            f"News sentiment for {asset_pair}: score={sentiment_score:.2f}, "
            f"impact={impact:.4f}, price_adj={price_change:+.4f} "
            f"→ ${estimated_price:,.4f}"
        )

        # Get sentiment label for metadata
        if sentiment_score > 0.3:
            label = "BULLISH"
        elif sentiment_score < -0.3:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return PriceSubmission(
            asset_pair=asset_pair,
            price=round(estimated_price, 8),
            confidence=round(confidence, 4),
            source=self.source,
            agent_address=self.agent_address,
            metadata={
                "mode": "demo",
                "headline": headline,
                "sentiment_score": round(sentiment_score, 3),
                "sentiment_label": label,
                "impact_factor": impact,
                "price_change_pct": round(price_change / last * 100, 4) if last > 0 else 0,
            },
        )

    def _analyze_sentiment(self, text: str) -> Tuple[float, float]:
        """Analyze sentiment of text using keyword matching.

        Args:
            text: Text to analyze.

        Returns:
            Tuple of (sentiment_score, average_impact_factor).
        """
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        total_sentiment = 0.0
        total_impact = 0.0
        matches = 0

        for keyword, (sentiment, impact) in self.SENTIMENT_KEYWORDS.items():
            if keyword in words:
                total_sentiment += sentiment
                total_impact += impact
                matches += 1

        if matches == 0:
            # No matching keywords: slight random bias
            return random.uniform(-0.15, 0.15), 0.001

        avg_sentiment = total_sentiment / matches
        avg_impact = total_impact / matches

        return avg_sentiment, avg_impact

    def get_recent_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent news analysis results.

        Args:
            limit: Maximum items to return.

        Returns:
            List of recent news analysis results.
        """
        return self._news_buffer[-limit:]
