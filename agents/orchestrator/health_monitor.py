"""SwarmFi Health Monitor

Monitors agent health through heartbeat checks and automatically
restarts failed agents.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional

from shared.logger import COLORS, get_logger
from shared.types import AgentInfo, AgentStatus, HealthCheck

logger = get_logger("ORCHESTRATOR")


class HealthMonitor:
    """Agent health checks and automatic restarts.

    Periodically monitors all registered agents by checking their
    heartbeats and response times. Agents that fail health checks
    are flagged and can be automatically restarted.

    Attributes:
        heartbeat_timeout: Seconds before an agent is considered unhealthy.
        check_interval: Seconds between health check cycles.
        max_restart_attempts: Max times to restart a failed agent.
        _agents: Registered agents and their metadata.
        _restart_counts: Restart attempt tracking.
        _health_history: Recent health check results.
        _on_agent_failure: Callback for agent failure events.
    """

    def __init__(
        self,
        heartbeat_timeout: float = 60.0,
        check_interval: float = 15.0,
        max_restart_attempts: int = 5,
    ) -> None:
        """Initialize the health monitor.

        Args:
            heartbeat_timeout: Seconds before agent is considered unhealthy.
            check_interval: Seconds between health check cycles.
            max_restart_attempts: Max restart attempts before giving up.
        """
        self.heartbeat_timeout = heartbeat_timeout
        self.check_interval = check_interval
        self.max_restart_attempts = max_restart_attempts

        self._agents: Dict[str, Dict[str, Any]] = {}
        self._restart_counts: Dict[str, int] = {}
        self._health_history: Dict[str, List[HealthCheck]] = {}
        self._on_agent_failure: Optional[Callable] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._stats = {
            "total_checks": 0,
            "failures_detected": 0,
            "restarts_triggered": 0,
        }

    def register_agent(
        self,
        agent_id: str,
        agent_info: AgentInfo,
        restart_callback: Optional[Callable] = None,
    ) -> None:
        """Register an agent for health monitoring.

        Args:
            agent_id: Unique agent identifier.
            agent_info: Agent information.
            restart_callback: Function to call to restart the agent.
        """
        self._agents[agent_id] = {
            "info": agent_info,
            "restart_callback": restart_callback,
            "registered_at": time.time(),
        }
        self._restart_counts[agent_id] = 0
        self._health_history[agent_id] = []
        logger.debug(f"Health monitor: registered agent {agent_id}")

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from health monitoring.

        Args:
            agent_id: Agent to remove.
        """
        self._agents.pop(agent_id, None)
        self._restart_counts.pop(agent_id, None)
        self._health_history.pop(agent_id, None)
        logger.debug(f"Health monitor: unregistered agent {agent_id}")

    def update_heartbeat(self, agent_id: str) -> None:
        """Update an agent's heartbeat timestamp.

        Called by agents or the agent manager when an agent sends a heartbeat.

        Args:
            agent_id: Agent that sent the heartbeat.
        """
        if agent_id in self._agents:
            self._agents[agent_id]["info"].last_heartbeat = time.time()

    def set_failure_callback(self, callback: Callable) -> None:
        """Set callback for agent failure events.

        Args:
            callback: Async function called with (agent_id, reason) on failure.
        """
        self._on_agent_failure = callback

    async def start(self) -> None:
        """Start the health monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(
            f"Health monitor started (interval={self.check_interval}s, "
            f"timeout={self.heartbeat_timeout}s)"
        )

    async def stop(self) -> None:
        """Stop the health monitoring loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Health monitor stopped. Stats: {self._stats}")

    async def check_agent(self, agent_id: str) -> HealthCheck:
        """Perform a health check on a specific agent.

        Args:
            agent_id: Agent to check.

        Returns:
            HealthCheck result.
        """
        start = time.time()
        self._stats["total_checks"] += 1

        if agent_id not in self._agents:
            return HealthCheck(
                agent_address=agent_id,
                healthy=False,
                error="Agent not registered",
                timestamp=time.time(),
            )

        agent_data = self._agents[agent_id]
        info = agent_data["info"]
        heartbeat_age = time.time() - info.last_heartbeat

        healthy = True
        error = None

        if heartbeat_age > self.heartbeat_timeout:
            healthy = False
            error = f"Heartbeat timeout ({heartbeat_age:.1f}s > {self.heartbeat_timeout}s)"
            self._stats["failures_detected"] += 1

        latency = (time.time() - start) * 1000

        check = HealthCheck(
            agent_address=agent_id,
            healthy=healthy,
            latency_ms=latency,
            error=error,
            last_heartbeat_age_seconds=heartbeat_age,
            timestamp=time.time(),
        )

        self._health_history[agent_id].append(check)
        # Keep last 100 checks
        if len(self._health_history[agent_id]) > 100:
            self._health_history[agent_id] = self._health_history[agent_id][-100:]

        return check

    async def check_all_agents(self) -> List[HealthCheck]:
        """Perform health checks on all registered agents.

        Returns:
            List of health check results.
        """
        results = []
        for agent_id in list(self._agents.keys()):
            check = await self.check_agent(agent_id)
            results.append(check)

            if not check.healthy:
                logger.warning(
                    f"Agent {agent_id} unhealthy: {check.error}"
                )
                await self._handle_failure(agent_id, check.error or "Unknown")

        return results

    def get_agent_uptime(self, agent_id: str) -> Optional[float]:
        """Get the uptime percentage for an agent.

        Args:
            agent_id: Agent to check.

        Returns:
            Uptime percentage (0-100) or None if not tracked.
        """
        history = self._health_history.get(agent_id, [])
        if not history:
            return None

        healthy_count = sum(1 for h in history if h.healthy)
        return (healthy_count / len(history)) * 100.0

    def get_all_agent_health(self) -> Dict[str, Dict[str, Any]]:
        """Get a summary of all agent health statuses.

        Returns:
            Dictionary of agent health summaries.
        """
        summary = {}
        for agent_id, agent_data in self._agents.items():
            info = agent_data["info"]
            history = self._health_history.get(agent_id, [])
            recent_healthy = sum(1 for h in history[-10:] if h.healthy) if history else 0
            recent_total = min(len(history), 10)

            summary[agent_id] = {
                "name": info.name,
                "type": info.agent_type.value,
                "status": info.status.value,
                "reputation": info.reputation,
                "healthy_recent": f"{recent_healthy}/{recent_total}",
                "restarts": self._restart_counts.get(agent_id, 0),
                "uptime_pct": self.get_agent_uptime(agent_id),
            }
        return summary

    def get_stats(self) -> Dict[str, int]:
        """Get health monitor statistics.

        Returns:
            Dictionary of monitor statistics.
        """
        return dict(self._stats)

    # ─── Private Methods ───────────────────────────────────────────────

    async def _monitor_loop(self) -> None:
        """Background loop that periodically checks all agents."""
        while self._running:
            try:
                await asyncio.sleep(self.check_interval)
                results = await self.check_all_agents()

                # Log summary if any issues
                unhealthy = [r for r in results if not r.healthy]
                if unhealthy:
                    logger.warning(
                        f"Health check: {len(unhealthy)}/{len(results)} agents unhealthy"
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)

    async def _handle_failure(self, agent_id: str, reason: str) -> None:
        """Handle an agent failure by attempting restart.

        Args:
            agent_id: Failed agent ID.
            reason: Failure reason.
        """
        # Call failure callback if set
        if self._on_agent_failure:
            try:
                if asyncio.iscoroutinefunction(self._on_agent_failure):
                    await self._on_agent_failure(agent_id, reason)
                else:
                    self._on_agent_failure(agent_id, reason)
            except Exception as e:
                logger.error(f"Failure callback error: {e}")

        # Attempt restart
        agent_data = self._agents.get(agent_id)
        if not agent_data:
            return

        restart_fn = agent_data.get("restart_callback")
        if not restart_fn:
            logger.warning(f"No restart callback for agent {agent_id}")
            return

        restart_count = self._restart_counts.get(agent_id, 0)
        if restart_count >= self.max_restart_attempts:
            logger.error(
                f"Agent {agent_id} exceeded max restart attempts "
                f"({self.max_restart_attempts}). Giving up."
            )
            agent_data["info"].status = AgentStatus.ERROR
            return

        self._restart_counts[agent_id] = restart_count + 1
        self._stats["restarts_triggered"] += 1

        logger.info(
            f"Restarting agent {agent_id} "
            f"(attempt {restart_count + 1}/{self.max_restart_attempts}) "
            f"due to: {reason}"
        )

        try:
            if asyncio.iscoroutinefunction(restart_fn):
                await restart_fn()
            else:
                restart_fn()
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
