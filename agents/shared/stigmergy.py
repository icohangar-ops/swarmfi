"""SwarmFi Stigmergy Communication Protocol

Implements indirect agent communication through a shared environment,
inspired by ant colony optimization (stigmergy).

Agents deposit signals (analogous to pheromone trails) that other agents
can sense. Signals decay over time, ensuring only recent information
influences agent behavior. This creates emergent coordination without
direct agent-to-agent messaging.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from shared.logger import COLORS, get_logger
from shared.types import AgentType, SignalType, StigmergySignal

logger = get_logger("STIGMERGY")


class StigmergyField:
    """Shared environment for stigmergic communication.

    Agents deposit and sense 'signals' in a shared field, similar to how
    ants leave and follow pheromone trails. Signals naturally decay over time,
    ensuring only recent information influences agent behavior.

    The field maintains signals in memory and provides thread-safe access
    for concurrent agent operations.

    Attributes:
        decay_rate: Default decay rate applied to all signals per tick.
        max_signals: Maximum number of signals to store before eviction.
        _signals: Internal signal storage keyed by signal type.
        _lock: Thread lock for concurrent access.
        _decay_task: Background task for periodic signal decay.
    """

    def __init__(self, decay_rate: float = 0.1, max_signals: int = 1000) -> None:
        """Initialize the stigmergy field.

        Args:
            decay_rate: Rate at which signals decay per tick (0.0 = no decay, 1.0 = instant).
            max_signals: Maximum signals to store before eviction.
        """
        self.decay_rate = decay_rate
        self.max_signals = max_signals
        self._signals: Dict[str, List[StigmergySignal]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._decay_task: Optional[asyncio.Task] = None
        self._running = False
        self._stats = {
            "total_deposited": 0,
            "total_sensed": 0,
            "total_expired": 0,
            "total_decayed": 0,
        }

    async def start(self, decay_interval: float = 5.0) -> None:
        """Start the stigmergy field background tasks.

        Args:
            decay_interval: Seconds between decay cycles.
        """
        if self._running:
            return
        self._running = True
        self._decay_task = asyncio.create_task(self._decay_loop(decay_interval))
        logger.info(
            f"Stigmergy field started (decay_rate={self.decay_rate}, "
            f"max_signals={self.max_signals}, interval={decay_interval}s)"
        )

    async def stop(self) -> None:
        """Stop the stigmergy field background tasks."""
        self._running = False
        if self._decay_task and not self._decay_task.done():
            self._decay_task.cancel()
            try:
                await self._decay_task
            except asyncio.CancelledError:
                pass
        logger.info(
            f"Stigmergy field stopped. Stats: {self._stats}"
        )

    async def deposit_signal(self, signal: StigmergySignal) -> str:
        """Deposit a new signal into the stigmergy field.

        The signal will be visible to agents based on its target_agents
        setting. If empty, all agents can sense it.

        Args:
            signal: The stigmergy signal to deposit.

        Returns:
            The signal ID.
        """
        async with self._lock:
            key = signal.signal_type.value
            self._signals[key].append(signal)
            self._stats["total_deposited"] += 1

            # Evict oldest signals if over capacity
            total = sum(len(v) for v in self._signals.values())
            if total > self.max_signals:
                await self._evict_oldest(total - self.max_signals + 100)

        logger.debug(
            f"Signal deposited: {signal.signal_type.value} from "
            f"{signal.from_agent[:12]}... (strength={signal.strength:.2f})"
        )
        return signal.id

    async def sense_signals(
        self,
        agent_type: Optional[AgentType] = None,
        signal_type: Optional[SignalType] = None,
        min_strength: float = 0.01,
        limit: int = 50,
    ) -> List[StigmergySignal]:
        """Sense signals from the stigmergy field.

        Agents call this to detect signals deposited by other agents.
        Only signals that match the agent's type and minimum strength
        threshold are returned, sorted by strength (strongest first).

        Args:
            agent_type: The type of agent sensing. If None, sense all signals.
            signal_type: Optional filter by signal type.
            min_strength: Minimum signal strength to return.
            limit: Maximum number of signals to return.

        Returns:
            List of matching signals sorted by strength descending.
        """
        current_time = time.time()
        matching: List[StigmergySignal] = []

        async with self._lock:
            types_to_check = [signal_type.value] if signal_type else list(self._signals.keys())

            for sig_type in types_to_check:
                for signal in self._signals.get(sig_type, []):
                    # Check TTL
                    if current_time - signal.timestamp > signal.ttl_seconds:
                        continue
                    # Check strength
                    if signal.strength < min_strength:
                        continue
                    # Check target agents
                    if signal.target_agents and agent_type and agent_type not in signal.target_agents:
                        continue
                    matching.append(signal)

            self._stats["total_sensed"] += len(matching)

        # Sort by strength descending
        matching.sort(key=lambda s: s.strength, reverse=True)
        return matching[:limit]

    async def decay_signals(self) -> int:
        """Apply decay to all signals in the field.

        Reduces the strength of each signal by its decay rate.
        Signals that reach zero strength are removed.

        Returns:
            Number of signals removed due to decay.
        """
        current_time = time.time()
        removed = 0

        async with self._lock:
            for sig_type in list(self._signals.keys()):
                surviving: List[StigmergySignal] = []
                for signal in self._signals[sig_type]:
                    # Check TTL expiration
                    if current_time - signal.timestamp > signal.ttl_seconds:
                        removed += 1
                        self._stats["total_expired"] += 1
                        continue

                    # Apply decay
                    signal.strength *= (1.0 - signal.decay_rate)

                    if signal.strength < 0.01:
                        removed += 1
                        self._stats["total_decayed"] += 1
                        continue

                    surviving.append(signal)

                self._signals[sig_type] = surviving

        return removed

    async def get_field_state(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get a snapshot of the current field state.

        Returns:
            Dictionary mapping signal types to lists of signal summaries.
        """
        current_time = time.time()
        state: Dict[str, List[Dict[str, Any]]] = {}

        async with self._lock:
            for sig_type, signals in self._signals.items():
                state[sig_type] = [
                    {
                        "id": s.id[:16],
                        "from": s.from_agent[:12],
                        "type": s.signal_type.value,
                        "strength": round(s.strength, 3),
                        "age_seconds": round(current_time - s.timestamp, 1),
                        "targets": [t.value for t in s.target_agents] if s.target_agents else ["ALL"],
                    }
                    for s in signals
                    if s.strength >= 0.01
                    and (current_time - s.timestamp) <= s.ttl_seconds
                ]

        return state

    def get_stats(self) -> Dict[str, int]:
        """Get stigmergy field statistics.

        Returns:
            Dictionary of field statistics.
        """
        return dict(self._stats)

    async def get_signal_count(self) -> int:
        """Get total number of active signals.

        Returns:
            Total active signal count.
        """
        async with self._lock:
            return sum(len(v) for v in self._signals.values())

    async def clear_field(self) -> None:
        """Remove all signals from the field."""
        async with self._lock:
            self._signals.clear()
        logger.info("Stigmergy field cleared")

    # ─── Private Methods ───────────────────────────────────────────────

    async def _decay_loop(self, interval: float) -> None:
        """Background loop that periodically decays signals.

        Args:
            interval: Seconds between decay cycles.
        """
        while self._running:
            try:
                await asyncio.sleep(interval)
                removed = await self.decay_signals()
                count = await self.get_signal_count()
                if removed > 0 or count > 0:
                    logger.debug(
                        f"Decay cycle: removed={removed}, active_signals={count}"
                    )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in decay loop: {e}")

    async def _evict_oldest(self, count: int) -> None:
        """Evict the oldest signals to stay within capacity.

        Args:
            count: Number of signals to evict.
        """
        all_signals: List[StigmergySignal] = []
        for signals in self._signals.values():
            all_signals.extend(signals)

        # Sort by timestamp (oldest first)
        all_signals.sort(key=lambda s: s.timestamp)

        to_remove = set()
        for signal in all_signals[:count]:
            to_remove.add(signal.id)

        for sig_type in self._signals:
            self._signals[sig_type] = [
                s for s in self._signals[sig_type] if s.id not in to_remove
            ]

        logger.debug(f"Evicted {len(to_remove)} oldest signals from field")


# ─── Global singleton ──────────────────────────────────────────────────

_stigmergy_instance: Optional[StigmergyField] = None


async def get_stigmergy_field(decay_rate: float = 0.1, max_signals: int = 1000) -> StigmergyField:
    """Get or create the global stigmergy field singleton.

    Args:
        decay_rate: Decay rate (only used on first creation).
        max_signals: Max signals (only used on first creation).

    Returns:
        The global StigmergyField instance.
    """
    global _stigmergy_instance
    if _stigmergy_instance is None:
        _stigmergy_instance = StigmergyField(
            decay_rate=decay_rate,
            max_signals=max_signals,
        )
    return _stigmergy_instance
