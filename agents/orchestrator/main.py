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
import json
import math
import os
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
from shared.calibration import CalibrationLoop
from shared.chain_interface import InitiaChainInterface
from shared.chp_gate import SwarmfiChpGate
from shared.config import Settings
from shared.consensus import SwarmConsensus
from shared.logger import (
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
)

from orchestrator.agent_manager import AgentManager

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
        self.chp_gate = SwarmfiChpGate.from_env()
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
            chp_gate=self.chp_gate,
        )

        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._start_time: float = 0.0
        self._consensus_count: int = 0

        # Row-4 calibration loop: bounded softmax reputation updates between
        # consensus rounds (agents/shared/calibration.py).
        # Slash-state seam: on-chain slashing is the adversarial track. The
        # operator supplies slashed addresses via SWARMFI_SLASHED_ADDRESSES
        # (comma-separated) until the on-chain slash feed is wired here; the
        # calibration loop never raises a slashed agent's reputation.
        self.calibration = CalibrationLoop(
            slashed_provider=lambda: {
                s.strip()
                for s in os.environ.get("SWARMFI_SLASHED_ADDRESSES", "").split(",")
                if s.strip()
            }
        )
        # External oracle price for the next calibration pass. None until a
        # real resolution price lands (note_realized_price); never fabricated
        # from consensus output — consensus_price is the swarm's own value,
        # not an external realization.
        self._external_realized_price: Optional[float] = None

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
        log_kv(
            "CHP Gate",
            f"ON ({self.chp_gate.domain}, floor {self.chp_gate.floor}, "
            f"human lock {'ON' if self.chp_gate.require_human_lock else 'OFF'})",
        )
        log_kv("CHP Decision Ledger", str(self.chp_gate.ledger.path))

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
                    if tx.success:
                        # Feed the gate's portfolio-state assertion (R0 Valid:
                        # the next post is bounded vs the last posted price).
                        self.chp_gate.note_posted_price(
                            result.asset_pair, result.consensus_price
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
        """Calibrate agent reputations between rounds (row 4).

        The previous round's submissions are scored against this round's
        consensus value (next-consensus proxy for the realized price —
        when an external resolution price lands, the calibration loop
        accepts it directly and supersedes the proxy), and reputation
        weights are updated with a bounded softmax blend: a single noisy
        round nudges weights, it cannot capture them. The participation
        boost this callback previously applied is replaced — it drifted
        reputations upward with no accuracy signal.
        """
        from shared.calibration import AgentOutcome

        submissions = self.agent_manager.get_pending_submissions()
        outcomes = [AgentOutcome(s.agent_address, s.price) for s in submissions]
        # Provenance: consensus_price is the swarm's own output, not an
        # external realization — passing it as realized_price would label
        # every scored entry "external" and freeze swarm consensus as
        # market truth in the outcome log. Pass an oracle price only when
        # one actually landed (note_realized_price); otherwise None lets
        # the loop record the honest next_consensus proxy.
        external_price = self._external_realized_price
        self._external_realized_price = None
        updated = self.calibration.on_consensus(
            self._consensus_count,
            self.agent_manager.get_reputations(),
            outcomes,
            realized_price=external_price,
        )
        for address, reputation in updated.items():
            self.agent_manager.set_reputation(address, reputation)
        if self.calibration.history and self.calibration.history[-1].scored:
            last = self.calibration.history[-1]
            logger.info(
                f"Calibration: round {last.round_index} scored against {last.realized_source} "
                f"price {last.realized_price:.6f} over {len(last.agents)} agents"
            )


    def note_realized_price(self, price: float) -> None:
        """Record an external oracle price for the next calibration pass.

        The hook a real oracle or resolution feed calls when a resolution
        price lands. Consumed exactly once by the next ``_on_consensus``
        and never derived from consensus output: until a feed is wired,
        every scored round stays labeled next_consensus and a later
        external replay can supersede it.
        """
        if math.isfinite(price) and price > 0:
            self._external_realized_price = price
        else:
            logger.warning(f"Ignoring non-positive or non-finite oracle price: {price}")


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
@click.option(
    "--list-chp-decisions",
    "list_chp_decisions",
    type=int,
    default=0,
    help="Print the N newest CHP decision-ledger records (integrity re-checked) and exit.",
)
@click.option(
    "--chp-decision",
    "chp_decision_id",
    type=str,
    default=None,
    help="Print one CHP decision-ledger record by decision id and exit.",
)
@click.option(
    "--chp-verify",
    is_flag=True,
    default=False,
    help="Re-validate integrity of every CHP decision-ledger record and exit.",
)
def main(
    demo: bool,
    config_path: Optional[str],
    log_level: Optional[str],
    duration: int,
    list_chp_decisions: int,
    chp_decision_id: Optional[str],
    chp_verify: bool,
) -> None:
    """🐝 SwarmFi AI Agent Orchestrator

    Manages the lifecycle of all AI agents, coordinates stigmergic
    communication, computes consensus, and submits results to Initia.
    """
    # CHP decision-ledger admin queries share the orchestrator entrypoint.
    gate = SwarmfiChpGate.from_env()
    if chp_decision_id:
        record = gate.ledger.get(chp_decision_id)
        if record is None:
            click.echo(f"no CHP decision record {chp_decision_id}", err=True)
            raise SystemExit(1)
        click.echo(json.dumps(record, indent=2))
        return
    if list_chp_decisions > 0:
        records = gate.ledger.list(list_chp_decisions)
        click.echo(json.dumps(records, indent=2))
        return
    if chp_verify:
        records = gate.ledger.list(limit=100000)
        invalid = [
            r for r in records
            if not r.get("integrity_valid") or not r.get("envelope_valid")
        ]
        click.echo(
            f"CHP decision ledger: {len(records)} record(s), "
            f"{len(invalid)} invalid"
        )
        for record in invalid:
            click.echo(
                f"  INVALID {record.get('decision_id')}: "
                f"integrity_valid={record.get('integrity_valid')} "
                f"envelope_valid={record.get('envelope_valid')}",
                err=True,
            )
        if invalid:
            raise SystemExit(1)
        return

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
