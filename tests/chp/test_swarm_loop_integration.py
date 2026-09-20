"""Swarm-loop integration: the gate sits between consensus and the on-chain post."""

from __future__ import annotations

import asyncio

from conftest import GOOD_PAIR, make_submissions
from orchestrator.agent_manager import AgentManager
from shared.chp_gate import SwarmfiChpGate
from shared.config import Settings
from shared.consensus import SwarmConsensus
from shared.stigmergy import StigmergyField


def _manager(gate) -> AgentManager:
    settings = Settings(demo_mode=True)
    return AgentManager(
        settings=settings,
        stigmergy=StigmergyField(),
        consensus=SwarmConsensus(),
        chp_gate=gate,
    )


class TestSwarmLoopIntegration:
    def test_gated_consensus_reaches_submission_when_locked(self, locked_gate, engine):
        manager = _manager(locked_gate)

        async def run():
            for sub in make_submissions():
                await manager.collect_price_submission(sub)
            return await manager.compute_and_submit_consensus()

        result = asyncio.run(run())
        assert result is not None, "a locked, hardened consensus must reach submission"
        assert result.asset_pair == GOOD_PAIR

        record = locked_gate.ledger.get(
            f"oracle-post-{int(result.timestamp * 1000)}-btc-usdt"
        )
        assert record is not None
        assert record["kind"] == "oracle_post"
        assert record["session_status"] == "LOCKED"

    def test_r0_fatal_blocks_the_oracle_post(self, gate, engine):
        """Sub-decision-grade consensus: R0 Worth_it FATAL -> no submission."""
        manager = _manager(gate)

        async def run():
            for sub in make_submissions(prices=(50.0, 100.0, 300.0), confidence=0.05):
                await manager.collect_price_submission(sub)
            return await manager.compute_and_submit_consensus()

        result = asyncio.run(run())
        assert result is None, "a refused consensus must never reach submission"
        records = gate.ledger.list(10)
        assert records[0]["kind"] == "r0_refusal"
        assert records[0]["r0_results"]["Worth_it"] == "FATAL"
        # The buffers were cleared — nothing half-consumed survives a refusal.
        assert manager._price_submissions == []

    def test_floor_refusal_blocks_the_oracle_post(self, gate, monkeypatch):
        """Parity evidence unavailable -> score 70 < 85 floor -> REFRAME -> no post."""
        from shared import chp_gate as chp_gate_module

        monkeypatch.setattr(
            chp_gate_module.SwarmfiChpGate,
            "_replay",
            staticmethod(
                lambda engine, submissions, agents: (
                    None,
                    "engine could not recompute a consensus",
                )
            ),
        )
        manager = _manager(gate)

        async def run():
            for sub in make_submissions():
                await manager.collect_price_submission(sub)
            return await manager.compute_and_submit_consensus()

        result = asyncio.run(run())
        assert result is None
        records = gate.ledger.list(10)
        assert any(r["kind"] == "floor_refusal" for r in records)

    def test_ungated_manager_still_works_without_gate(self):
        """Backward compatibility: no gate wired -> previous behavior."""
        manager = _manager(None)

        async def run():
            for sub in make_submissions():
                await manager.collect_price_submission(sub)
            return await manager.compute_and_submit_consensus()

        result = asyncio.run(run())
        assert result is not None


class TestOrchestratorWiring:
    def test_orchestrator_constructs_and_wires_the_gate(self, tmp_path):
        """The real orchestrator wires a gate from env into its agent manager."""
        from orchestrator.main import SwarmFiOrchestrator

        settings = Settings(demo_mode=True)
        orchestrator = SwarmFiOrchestrator(settings)
        assert isinstance(orchestrator.chp_gate, SwarmfiChpGate)
        assert orchestrator.agent_manager.chp_gate is orchestrator.chp_gate
        assert orchestrator.chp_gate.require_human_lock is True

    def test_note_posted_price_feeds_next_round_state_assertion(self, gate):
        gate.note_posted_price(GOOD_PAIR, 100.0)
        assert gate._last_posted[GOOD_PAIR] == 100.0
        # A move beyond the cap flips R0 Valid to FATAL on the next round.
        evaluation = gate.evaluate_r0(
            type(
                "R",
                (),
                {
                    "consensus_price": 200.0,
                    "confidence": 0.9,
                    "participating_agents": ["a"],
                    "asset_pair": GOOD_PAIR,
                    "std_deviation": 0.1,
                },
            )
        )
        assert evaluation.results["Valid"] == "FATAL"
