"""SwarmFi Agent Manager

Manages the lifecycle of AI agent instances: spawning, monitoring,
health checking, restarting, signal routing, and consensus computation.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from shared.config import Settings
from shared.consensus import SwarmConsensus
from shared.logger import COLORS, get_logger, log_section, log_table
from shared.stigmergy import StigmergyField
from shared.types import (
    AgentInfo,
    AgentStatus,
    AgentType,
    ConsensusResult,
    HealthCheck,
    PriceSubmission,
    RiskAssessment,
    StigmergySignal,
)
from orchestrator.health_monitor import HealthMonitor

logger = get_logger("ORCHESTRATOR")


class AgentInstance:
    """Represents a running agent instance.

    Attributes:
        agent_id: Unique identifier.
        agent_type: Type category.
        info: Agent metadata.
        task: The asyncio task running the agent.
        config: Agent-specific configuration.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        info: AgentInfo,
        task: asyncio.Task,
        config: Dict[str, Any],
    ) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.info = info
        self.task = task
        self.config = config
        self.started_at = time.time()
        self._output_queue: asyncio.Queue = asyncio.Queue()

    @property
    def uptime(self) -> float:
        """Seconds since agent was started."""
        return time.time() - self.started_at


class AgentManager:
    """Manages the lifecycle of AI agent instances.

    Responsibilities:
    - Spawn agents based on configuration
    - Monitor health via heartbeat
    - Restart failed agents
    - Route stigmergy signals between agents
    - Collect agent outputs for consensus computation

    Attributes:
        settings: Application settings.
        stigmergy: The shared stigmergy field.
        consensus: The consensus engine.
        health_monitor: Health monitoring system.
        _agents: Currently running agent instances.
        _price_submissions: Collected price submissions for consensus.
        _risk_assessments: Collected risk assessments.
        _output_handlers: Registered output handlers per agent type.
    """

    def __init__(
        self,
        settings: Settings,
        stigmergy: StigmergyField,
        consensus: SwarmConsensus,
    ) -> None:
        """Initialize the agent manager.

        Args:
            settings: Application settings.
            stigmergy: Shared stigmergy field.
            consensus: Consensus engine.
        """
        self.settings = settings
        self.stigmergy = stigmergy
        self.consensus = consensus

        self._agents: Dict[str, AgentInstance] = {}
        self._price_submissions: List[PriceSubmission] = []
        self._risk_assessments: List[RiskAssessment] = []
        self._output_handlers: Dict[AgentType, Callable] = {}
        self._on_consensus_callbacks: List[Callable] = []
        self._agent_counter = 0

        # Health monitor
        self.health_monitor = HealthMonitor(
            heartbeat_timeout=60.0,
            check_interval=15.0,
            max_restart_attempts=5,
        )
        self.health_monitor.set_failure_callback(self._on_agent_failure)

    async def start_agent(
        self,
        agent_type: AgentType,
        config: Optional[Dict[str, Any]] = None,
        run_fn: Optional[Callable] = None,
    ) -> str:
        """Spawn and start a new agent instance.

        Args:
            agent_type: Type of agent to spawn.
            config: Optional agent-specific configuration.
            run_fn: Async function to run the agent. If None, uses default.

        Returns:
            The agent ID of the spawned instance.
        """
        self._agent_counter += 1
        agent_id = f"{agent_type.value.lower()}_{self._agent_counter:03d}"
        config = config or {}

        # Generate a mock address for the agent
        agent_address = f"swarmfi1{agent_id}{hex(self._agent_counter)[2:].zfill(8)}"

        info = AgentInfo(
            name=config.get("name", f"{agent_type.value} Agent #{self._agent_counter}"),
            agent_type=agent_type,
            address=agent_address,
            status=AgentStatus.ACTIVE,
            reputation=config.get("reputation", 0.5),
            metadata=config.get("metadata", {}),
        )

        # Create the agent task
        if run_fn:
            task = asyncio.create_task(self._run_agent_wrapper(agent_id, run_fn, config))
        else:
            task = asyncio.create_task(self._run_demo_agent(agent_id, agent_type, config))

        instance = AgentInstance(
            agent_id=agent_id,
            agent_type=agent_type,
            info=info,
            task=task,
            config=config,
        )

        self._agents[agent_id] = instance

        # Register with health monitor
        self.health_monitor.register_agent(
            agent_id=agent_id,
            agent_info=info,
            restart_callback=lambda aid=agent_id: asyncio.create_task(
                self.restart_agent(aid)
            ),
        )

        logger.info(
            f"Agent spawned: {info.name} ({agent_id}) "
            f"[{agent_type.value}] addr={agent_address[:20]}..."
        )

        return agent_id

    async def stop_agent(self, agent_id: str) -> bool:
        """Stop a running agent.

        Args:
            agent_id: Agent to stop.

        Returns:
            True if agent was found and stopped.
        """
        instance = self._agents.get(agent_id)
        if not instance:
            logger.warning(f"Cannot stop agent {agent_id}: not found")
            return False

        instance.task.cancel()
        try:
            await instance.task
        except asyncio.CancelledError:
            pass

        instance.info.status = AgentStatus.IDLE
        self.health_monitor.unregister_agent(agent_id)

        logger.info(f"Agent stopped: {agent_id}")
        return True

    async def stop_all_agents(self) -> None:
        """Stop all running agents."""
        logger.info(f"Stopping {len(self._agents)} agents...")
        for agent_id in list(self._agents.keys()):
            await self.stop_agent(agent_id)

    async def restart_agent(self, agent_id: str) -> bool:
        """Restart a failed agent.

        Args:
            agent_id: Agent to restart.

        Returns:
            True if agent was successfully restarted.
        """
        instance = self._agents.get(agent_id)
        if not instance:
            return False

        logger.info(f"Restarting agent {agent_id}...")

        # Cancel old task
        instance.task.cancel()
        try:
            await instance.task
        except asyncio.CancelledError:
            pass

        # Create new task
        instance.info.status = AgentStatus.SYNCHRONIZING
        instance.started_at = time.time()

        if instance.config.get("run_fn"):
            instance.task = asyncio.create_task(
                self._run_agent_wrapper(agent_id, instance.config["run_fn"], instance.config)
            )
        else:
            instance.task = asyncio.create_task(
                self._run_demo_agent(agent_id, instance.agent_type, instance.config)
            )

        instance.info.status = AgentStatus.ACTIVE
        instance.info.last_heartbeat = time.time()

        logger.info(f"Agent restarted: {agent_id}")
        return True

    async def get_agent_status(self, agent_id: str) -> Optional[AgentInfo]:
        """Get the status of a specific agent.

        Args:
            agent_id: Agent to query.

        Returns:
            AgentInfo or None if not found.
        """
        instance = self._agents.get(agent_id)
        if instance:
            instance.info.uptime_seconds = instance.uptime
            return instance.info
        return None

    async def get_all_agents(self) -> Dict[str, AgentInfo]:
        """Get status of all running agents.

        Returns:
            Dictionary mapping agent IDs to their info.
        """
        result = {}
        for agent_id, instance in self._agents.items():
            instance.info.uptime_seconds = instance.uptime
            result[agent_id] = instance.info
        return result

    async def route_stigmergy(self, signal: StigmergySignal) -> None:
        """Route a stigmergy signal to the shared field.

        Args:
            signal: Signal to deposit.
        """
        await self.stigmergy.deposit_signal(signal)

    async def collect_price_submission(self, submission: PriceSubmission) -> None:
        """Collect a price submission from an agent.

        Submissions are buffered and periodically used for consensus.

        Args:
            submission: Price submission to collect.
        """
        self._price_submissions.append(submission)
        logger.debug(
            f"Price submission collected: {submission.asset_pair} = "
            f"{submission.price:.4f} from {submission.source}"
        )

    async def collect_risk_assessment(self, assessment: RiskAssessment) -> None:
        """Collect a risk assessment from an agent.

        Args:
            assessment: Risk assessment to collect.
        """
        self._risk_assessments.append(assessment)
        logger.debug(
            f"Risk assessment collected: {assessment.asset_pair} "
            f"vol={assessment.volatility_score:.3f} "
            f"liq_risk={assessment.liquidation_risk:.3f}"
        )

    async def compute_and_submit_consensus(self) -> Optional[ConsensusResult]:
        """Compute consensus from collected submissions and submit.

        Computes weighted median consensus, submits to chain,
        deposits stigmergy signal, and clears the buffer.

        Returns:
            ConsensusResult if consensus was reached.
        """
        if not self._price_submissions:
            return None

        # Get all agent infos for weighting
        agents = [
            instance.info for instance in self._agents.values()
            if instance.agent_type == AgentType.PRICE
        ]

        result = self.consensus.compute_consensus(
            submissions=self._price_submissions,
            agents=agents if agents else None,
        )

        if result:
            # Deposit consensus signal
            signal = StigmergySignal(
                signal_type="CONSENSUS_REACHED",
                from_agent="consensus_engine",
                data={
                    "asset_pair": result.asset_pair,
                    "price": result.consensus_price,
                    "confidence": result.confidence,
                    "participants": result.participating_agents,
                },
                strength=result.confidence,
                decay_rate=0.05,
                ttl_seconds=600.0,
            )
            await self.stigmergy.deposit_signal(signal)

            # Notify callbacks
            for callback in self._on_consensus_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result)
                    else:
                        callback(result)
                except Exception as e:
                    logger.error(f"Consensus callback error: {e}")

        # Clear buffer
        self._price_submissions.clear()
        self._risk_assessments.clear()

        return result

    def on_consensus(self, callback: Callable) -> None:
        """Register a callback for consensus results.

        Args:
            callback: Function called with ConsensusResult when consensus is reached.
        """
        self._on_consensus_callbacks.append(callback)

    async def print_status(self) -> None:
        """Print a status dashboard of all agents to the console."""
        agents = await self.get_all_agents()
        health = self.health_monitor.get_all_agent_health()
        signal_count = await self.stigmergy.get_signal_count()
        field_stats = self.stigmergy.get_stats()

        log_section("AGENT STATUS DASHBOARD")

        if agents:
            headers = ["Agent ID", "Name", "Type", "Status", "Uptime", "Rep"]
            rows = []
            for aid, info in agents.items():
                uptime_str = f"{info.uptime_seconds:.0f}s"
                rows.append([
                    aid[:16],
                    info.name[:20],
                    info.agent_type.value[:13],
                    info.status.value,
                    uptime_str,
                    f"{info.reputation:.2f}",
                ])
            log_table(headers, rows)
        else:
            logger.info("No agents running")

        logger.opt(colors=True).info(
            f"\n  {COLORS['DIM']}Stigmergy Signals:{COLORS['RESET']} {signal_count} active\n"
            f"  {COLORS['DIM']}Field Stats:{COLORS['RESET']} "
            f"deposited={field_stats['total_deposited']}, "
            f"sensed={field_stats['total_sensed']}, "
            f"expired={field_stats['total_expired']}, "
            f"decayed={field_stats['total_decayed']}\n"
            f"  {COLORS['DIM']}Consensus Confidence:{COLORS['RESET']} "
            f"{self.consensus.get_average_confidence():.1%}\n"
        )

    # ─── Private Methods ───────────────────────────────────────────────

    async def _run_agent_wrapper(
        self,
        agent_id: str,
        run_fn: Callable,
        config: Dict[str, Any],
    ) -> None:
        """Wrapper to run an agent function with error handling.

        Args:
            agent_id: Agent identifier.
            run_fn: Async function to run.
            config: Agent configuration.
        """
        instance = self._agents.get(agent_id)
        if not instance:
            return

        try:
            # Inject dependencies into config
            config["agent_id"] = agent_id
            config["agent_address"] = instance.info.address
            config["stigmergy"] = self.stigmergy
            config["manager"] = self

            await run_fn(config)
        except asyncio.CancelledError:
            logger.debug(f"Agent {agent_id} cancelled")
            raise
        except Exception as e:
            logger.error(f"Agent {agent_id} crashed: {e}")
            instance.info.status = AgentStatus.ERROR

    async def _run_demo_agent(
        self,
        agent_id: str,
        agent_type: AgentType,
        config: Dict[str, Any],
    ) -> None:
        """Run a demo agent that generates simulated data.

        Args:
            agent_id: Agent identifier.
            agent_type: Type of agent.
            config: Agent configuration.
        """
        import random

        instance = self._agents.get(agent_id)
        if not instance:
            return

        interval = config.get("interval", self.settings.get_agent_config(
            agent_type.value.lower().replace("market_maker", "market_maker")
        ).interval_seconds)

        assets = self.settings.assets
        agent_address = instance.info.address

        logger.info(
            f"Demo agent {agent_id} starting: "
            f"type={agent_type.value}, interval={interval}s, assets={assets}"
        )

        while True:
            try:
                await asyncio.sleep(interval)

                # Update heartbeat
                self.health_monitor.update_heartbeat(agent_id)
                instance.info.last_heartbeat = time.time()

                if agent_type == AgentType.PRICE:
                    await self._demo_price_tick(agent_id, agent_address, assets, config)
                elif agent_type == AgentType.RISK:
                    await self._demo_risk_tick(agent_id, agent_address, assets, config)
                elif agent_type == AgentType.MARKET_MAKER:
                    await self._demo_market_maker_tick(agent_id, agent_address, assets, config)
                elif agent_type == AgentType.RESOLUTION:
                    await self._demo_resolution_tick(agent_id, agent_address, config)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Demo agent {agent_id} error: {e}")
                instance.info.status = AgentStatus.ERROR
                await asyncio.sleep(5)
                instance.info.status = AgentStatus.ACTIVE

    async def _demo_price_tick(
        self,
        agent_id: str,
        agent_address: str,
        assets: List[str],
        config: Dict[str, Any],
    ) -> None:
        """Generate simulated price data for demo mode.

        Args:
            agent_id: Agent identifier.
            agent_address: Agent address.
            assets: Asset pairs to generate prices for.
            config: Agent config.
        """
        import random

        # Base prices for simulation
        base_prices = {
            "BTC/USDT": 67500.0,
            "ETH/USDT": 3450.0,
            "INIT/USDT": 0.45,
            "SOL/USDT": 178.0,
            "AVAX/USDT": 38.0,
        }

        sources = ["coingecko", "dex_aggregator", "news_sentiment"]
        source = sources[hash(agent_id) % len(sources)]

        for asset in assets:
            base = base_prices.get(asset, 100.0)
            # Random walk with slight drift
            noise = random.gauss(0, base * 0.002)
            price = base + noise

            # Add per-source bias
            if source == "coingecko":
                price *= random.uniform(0.9995, 1.0005)
            elif source == "dex_aggregator":
                price *= random.uniform(0.999, 1.001)
            elif source == "news_sentiment":
                price *= random.uniform(0.998, 1.002)

            confidence = random.uniform(0.7, 0.95)

            submission = PriceSubmission(
                asset_pair=asset,
                price=round(max(price, 0.0001), 8),
                confidence=confidence,
                source=source,
                agent_address=agent_address,
            )

            await self.collect_price_submission(submission)

            # Deposit stigmergy signal
            signal = StigmergySignal(
                signal_type="PRICE_UPDATE",
                from_agent=agent_address,
                data={"asset_pair": asset, "price": submission.price, "confidence": confidence},
                strength=confidence * 0.8,
                target_agents=[AgentType.PRICE],
                decay_rate=0.15,
                ttl_seconds=120.0,
            )
            await self.route_stigmergy(signal)

    async def _demo_risk_tick(
        self,
        agent_id: str,
        agent_address: str,
        assets: List[str],
        config: Dict[str, Any],
    ) -> None:
        """Generate simulated risk data for demo mode.

        Args:
            agent_id: Agent identifier.
            agent_address: Agent address.
            assets: Asset pairs.
            config: Agent config.
        """
        import random

        risk_types = ["volatility", "correlation", "liquidation"]
        risk_type = risk_types[hash(agent_id) % len(risk_types)]

        for asset in assets:
            assessment = RiskAssessment(
                asset_pair=asset,
                volatility_score=round(random.uniform(0.1, 0.8), 4),
                correlation_score=round(random.uniform(-0.5, 0.8), 4),
                liquidation_risk=round(random.uniform(0.0, 0.3), 4),
                agent_address=agent_address,
                horizon_minutes=60,
            )

            await self.collect_risk_assessment(assessment)

            signal = StigmergySignal(
                signal_type="RISK_ALERT",
                from_agent=agent_address,
                data={
                    "asset_pair": asset,
                    "risk_type": risk_type,
                    "volatility": assessment.volatility_score,
                    "liquidation_risk": assessment.liquidation_risk,
                },
                strength=assessment.volatility_score,
                target_agents=[AgentType.RISK, AgentType.MARKET_MAKER],
                decay_rate=0.1,
                ttl_seconds=180.0,
            )
            await self.route_stigmergy(signal)

    async def _demo_market_maker_tick(
        self,
        agent_id: str,
        agent_address: str,
        assets: List[str],
        config: Dict[str, Any],
    ) -> None:
        """Generate simulated market maker activity for demo mode.

        Args:
            agent_id: Agent identifier.
            agent_address: Agent address.
            assets: Asset pairs.
            config: Agent config.
        """
        import random

        # Simulate inventory check
        signal = StigmergySignal(
            signal_type="MARKET_EVENT",
            from_agent=agent_address,
            data={
                "action": "inventory_check",
                "assets": assets[:2],
                "balances": {a: random.randint(100, 10000) for a in assets[:2]},
            },
            strength=0.5,
            target_agents=[AgentType.MARKET_MAKER],
            decay_rate=0.2,
            ttl_seconds=60.0,
        )
        await self.route_stigmergy(signal)

    async def _demo_resolution_tick(
        self,
        agent_id: str,
        agent_address: str,
        config: Dict[str, Any],
    ) -> None:
        """Generate simulated resolution agent activity.

        Args:
            agent_id: Agent identifier.
            agent_address: Agent address.
            config: Agent config.
        """
        # Resolution agents periodically check for markets to resolve
        signal = StigmergySignal(
            signal_type="HEARTBEAT",
            from_agent=agent_address,
            data={"action": "resolution_scan", "markets_checked": 0},
            strength=0.3,
            decay_rate=0.3,
            ttl_seconds=30.0,
        )
        await self.route_stigmergy(signal)

    async def _on_agent_failure(self, agent_id: str, reason: str) -> None:
        """Handle agent failure event.

        Args:
            agent_id: Failed agent ID.
            reason: Failure reason.
        """
        logger.warning(f"Agent failure: {agent_id} — {reason}")
