"""SwarmFi Agent Orchestrator — Main Entry Point

Manages the lifecycle of all AI agents, coordinates stigmergic
communication, computes consensus, and submits results to Initia.

Usage:
    python -m orchestrator.main --demo
    python -m orchestrator.main --config config/config.yaml
    python -m orchestrator.main --demo --log-level DEBUG
"""

from __future__ import annotations

import asyncio
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Ensure project root is in path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import click

from shared.config import Settings
from shared.consensus import SwarmConsensus
from shared.chain_interface import InitiaChainInterface
from shared.logger import (
    COLORS,
    get_logger,
    log_banner,
    log_kv,
    log_section,
    log_table,
    setup_logging,
)
from shared.stigmergy import StigmergyField
from shared.types import (
    AgentType,
    ConsensusResult,
    StigmergySignal,
)
from orchestrator.agent_manager import AgentManager
from orchestrator.health_monitor import HealthMonitor

logger = get_logger("ORCHESTRATOR")


class SwarmFiOrchestrator:
    """Main orchestrator for the SwarmFi agent system.

    Coordinates all agent types, manages the stigmergy field,
    computes consensus, and submits results to the Initia blockchain.

    Attributes:
        settings: Application settings.
        stigmergy: Shared stigmergy field.
        consensus: Consensus engine.
        chain: Blockchain interface.
        agent_manager: Agent lifecycle manager.
        _shutdown_event: Event to signal graceful shutdown.
        _tasks: Background tasks managed by the orchestrator.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the orchestrator.

        Args:
            settings: Application configuration.
        """
        self.settings = settings

        # Core components
        self.stigmergy = StigmergyField(
            decay_rate=settings.stigmergy_decay_rate,
            max_signals=settings.stigmergy_max_signals,
        )
        self.consensus = SwarmConsensus(
            threshold=settings.consensus_threshold,
            outlier_deviation=settings.outlier_deviation,
        )
        self.chain = InitiaChainInterface(
            rpc_url=settings.initia_rpc_url,
            chain_id=settings.initia_chain_id,
            private_key=settings.agent_private_key,
            mock_mode=settings.demo_mode,
        )
        self.agent_manager = AgentManager(
            settings=settings,
            stigmergy=self.stigmergy,
            consensus=self.consensus,
        )

        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._start_time: float = 0.0
        self._consensus_count: int = 0

        # Register consensus callback
        self.agent_manager.on_consensus(self._on_consensus)

    async def start(self) -> None:
        """Start the entire SwarmFi agent system.

        Initializes all components, spawns agents, and begins
        the main coordination loops.
        """
        self._start_time = time.time()

        log_banner("🐝  SWARMFI AI AGENT ORCHESTRATOR  🐝")

        log_section("SYSTEM CONFIGURATION")
        log_kv("Mode", "🟢 DEMO" if self.settings.demo_mode else "🔵 LIVE")
        log_kv("Chain ID", self.settings.initia_chain_id)
        log_kv("RPC", self.settings.initia_rpc_url)
        log_kv("Oracle Contract", self.settings.contracts.oracle[:24] + "...")
        log_kv("Market Contract", self.settings.contracts.market[:24] + "...")
        log_kv("Vault Contract", self.settings.contracts.vault[:24] + "...")
        log_kv("Assets", ", ".join(self.settings.assets))
        log_kv("Consensus Threshold", f"{self.settings.consensus_threshold:.0%}")
        log_kv("Stigmergy Decay", f"{self.settings.stigmergy_decay_rate:.2f}")
        log_kv("Log Level", self.settings.log_level)

        # Start stigmergy field
        await self.stigmergy.start(decay_interval=5.0)

        # Start health monitor
        await self.agent_manager.health_monitor.start()

        # Spawn agents
        log_section("SPAWNING AGENTS")
        await self._spawn_agents()

        # Show initial status
        await self.agent_manager.print_status()

        # Start background coordination loops
        log_section("STARTING COORDINATION LOOPS")
        self._tasks.append(asyncio.create_task(self._consensus_loop()))
        self._tasks.append(asyncio.create_task(self._status_display_loop()))
        self._tasks.append(asyncio.create_task(self._stigmergy_display_loop()))

        log_section("SWARMFI IS LIVE 🚀")
        logger.info("All systems operational. Press Ctrl+C to gracefully shutdown.\n")

        # Wait for shutdown
        await self._shutdown_event.wait()

    async def stop(self) -> None:
        """Gracefully shut down the entire system."""
        if self._shutdown_event.is_set():
            return

        self._shutdown_event.set()
        log_section("SHUTTING DOWN")

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Stop agents
        await self.agent_manager.stop_all_agents()

        # Stop health monitor
        await self.agent_manager.health_monitor.stop()

        # Stop stigmergy
        await self.stigmergy.stop()

        # Final stats
        uptime = time.time() - self._start_time
        health_stats = self.agent_manager.health_monitor.get_stats()
        field_stats = self.stigmergy.get_stats()

        log_section("FINAL STATISTICS")
        log_kv("Uptime", f"{uptime:.1f} seconds")
        log_kv("Consensus Rounds", str(self._consensus_count))
        log_kv("Avg Consensus Confidence", f"{self.consensus.get_average_confidence():.1%}")
        log_kv("Health Checks", str(health_stats.get("total_checks", 0)))
        log_kv("Signals Deposited", str(field_stats.get("total_deposited", 0)))
        log_kv("Mock Txns", str(len(self.chain.get_mock_submissions())))

        log_banner("SWARMFI SHUTDOWN COMPLETE")
        logger.info("Goodbye! 🐝\n")

    async def _spawn_agents(self) -> None:
        """Spawn all configured agents."""
        # Price agents (3 sources)
        price_sources = [
            {"name": "CoinGecko Agent", "source": "coingecko", "reputation": 0.85},
            {"name": "DEX Aggregator Agent", "source": "dex_aggregator", "reputation": 0.80},
            {"name": "News Sentiment Agent", "source": "news_sentiment", "reputation": 0.65},
        ]

        for src_config in price_sources:
            if self.settings.price_agent_config.enabled:
                await self.agent_manager.start_agent(
                    agent_type=AgentType.PRICE,
                    config=src_config,
                )

        # Risk agents (3 types)
        risk_types = [
            {"name": "Volatility Agent", "reputation": 0.75},
            {"name": "Correlation Agent", "reputation": 0.70},
            {"name": "Liquidation Agent", "reputation": 0.72},
        ]

        for risk_config in risk_types:
            if self.settings.risk_agent_config.enabled:
                await self.agent_manager.start_agent(
                    agent_type=AgentType.RISK,
                    config=risk_config,
                )

        # Market maker agents (2 types)
        mm_types = [
            {"name": "AMM Strategy Agent", "reputation": 0.78},
            {"name": "Inventory Agent", "reputation": 0.68},
        ]

        for mm_config in mm_types:
            if self.settings.market_maker_agent_config.enabled:
                await self.agent_manager.start_agent(
                    agent_type=AgentType.MARKET_MAKER,
                    config=mm_config,
                )

        # Resolution agents (2 types)
        res_types = [
            {"name": "Oracle Resolution Agent", "reputation": 0.90},
            {"name": "Community Resolution Agent", "reputation": 0.60},
        ]

        for res_config in res_types:
            if self.settings.resolution_agent_config.enabled:
                await self.agent_manager.start_agent(
                    agent_type=AgentType.RESOLUTION,
                    config=res_config,
                )

        total = sum(1 for v in [
            self.settings.price_agent_config.enabled,
            self.settings.risk_agent_config.enabled,
            self.settings.market_maker_agent_config.enabled,
            self.settings.resolution_agent_config.enabled,
        ] for _ in range(1))

        agent_count = len(self.agent_manager._agents)
        logger.info(f"Spawned {agent_count} agents across 4 categories")

    async def _consensus_loop(self) -> None:
        """Periodically compute consensus and submit to chain."""
        consensus_interval = 20.0  # seconds

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(consensus_interval)

                result = await self.agent_manager.compute_and_submit_consensus()

                if result:
                    self._consensus_count += 1

                    # Submit to chain
                    from shared.types import PriceSubmission

                    tx = await self.chain.submit_price(
                        contract_addr=self.settings.contracts.oracle,
                        submission=PriceSubmission(
                            asset_pair=result.asset_pair,
                            price=result.consensus_price,
                            confidence=result.confidence,
                            source="consensus",
                            agent_address="consensus_engine",
                        ),
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Consensus loop error: {e}")
                await asyncio.sleep(5)

    async def _status_display_loop(self) -> None:
        """Periodically display agent status dashboard."""
        status_interval = 30.0

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(status_interval)
                await self.agent_manager.print_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Status display error: {e}")

    async def _stigmergy_display_loop(self) -> None:
        """Periodically display stigmergy field state."""
        display_interval = 25.0

        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(display_interval)

                state = await self.stigmergy.get_field_state()
                total_signals = sum(len(v) for v in state.values())

                if total_signals > 0:
                    log_section("STIGMERGY FIELD STATE")

                    signal_counts = {
                        k: len(v) for k, v in sorted(state.items()) if v
                    }

                    if signal_counts:
                        headers = ["Signal Type", "Count", "Sample"]
                        rows = []
                        for sig_type, signals in signal_counts.items():
                            sample = signals[0] if signals else {}
                            from_str = sample.get("from", "???")
                            strength_str = str(sample.get("strength", 0))
                            rows.append([
                                sig_type,
                                str(len(signals)),
                                f"{from_str} ({strength_str})",
                            ])
                        log_table(headers, rows)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stigmergy display error: {e}")

    async def _on_consensus(self, result: ConsensusResult) -> None:
        """Callback when consensus is reached.

        Args:
            result: The consensus result.
        """
        # Update agent reputations based on participation
        for agent_id, instance in self.agent_manager._agents.items():
            if instance.info.address in result.participating_agents:
                # Slightly boost reputation for participation
                instance.info.reputation = min(
                    1.0, instance.info.reputation + 0.01
                )


# ─── CLI Entry Point ───────────────────────────────────────────────────


@click.command()
@click.option(
    "--demo",
    is_flag=True,
    default=False,
    help="Run in demo mode (no blockchain needed).",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to YAML config file.",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default=None,
    help="Override log level.",
)
@click.option(
    "--duration",
    type=int,
    default=120,
    help="Demo duration in seconds (0 = infinite).",
)
def main(
    demo: bool,
    config_path: Optional[str],
    log_level: Optional[str],
    duration: int,
) -> None:
    """🐝 SwarmFi AI Agent Orchestrator

    Manages the lifecycle of all AI agents, coordinates stigmergic
    communication, computes consensus, and submits results to Initia.
    """
    # Build settings
    if config_path:
        settings = Settings.from_yaml(config_path)
    else:
        settings = Settings()

    # Apply CLI overrides
    if demo:
        settings.demo_mode = True
    if log_level:
        settings.log_level = log_level

    # Setup logging
    setup_logging(settings.log_level)

    logger.info("Initializing SwarmFi Orchestrator...")

    # Create orchestrator
    orchestrator = SwarmFiOrchestrator(settings)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()

    def _signal_handler() -> None:
        logger.info("\nShutdown signal received...")
        asyncio.ensure_future(orchestrator.stop(), loop=loop)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: _signal_handler())

    # Run the orchestrator
    async def _run_with_duration() -> None:
        if duration > 0 and settings.demo_mode:
            logger.info(f"Demo will run for {duration} seconds")
            done, pending = await asyncio.wait(
                [orchestrator.start(), asyncio.sleep(duration)],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await orchestrator.stop()
        else:
            await orchestrator.start()

    try:
        loop.run_until_complete(_run_with_duration())
    except KeyboardInterrupt:
        loop.run_until_complete(orchestrator.stop())
    finally:
        loop.close()


if __name__ == "__main__":
    main()
