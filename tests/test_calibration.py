"""Tests for the row-4 calibration loop (agents/shared/calibration.py)."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from shared.calibration import (
    PROXY_RUN_WARNING_THRESHOLD,
    AgentOutcome,
    CalibrationLoop,
    bounded_update,
    score_round,
    softmax_reputations,
)


def test_score_round_fills_abs_error_and_skips_non_finite():
    agents = [
        AgentOutcome("a", 100.0),
        AgentOutcome("b", 110.0),
        AgentOutcome("c", float("nan")),
    ]
    scored = score_round(agents, 101.0)
    assert scored[0].abs_error == pytest.approx(1.0)
    assert scored[1].abs_error == pytest.approx(9.0)
    assert scored[2].abs_error is None


def test_softmax_reputations_favors_lower_error():
    scored = [
        AgentOutcome("accurate", 100.0, abs_error=0.5),
        AgentOutcome("sloppy", 100.0, abs_error=8.0),
    ]
    shares = softmax_reputations(scored)
    assert shares["accurate"] > shares["sloppy"]
    assert sum(shares.values()) == pytest.approx(1.0)


def test_softmax_reputations_equal_errors_equal_shares():
    scored = [
        AgentOutcome("a", 100.0, abs_error=2.0),
        AgentOutcome("b", 100.0, abs_error=2.0),
        AgentOutcome("c", 100.0, abs_error=2.0),
    ]
    shares = softmax_reputations(scored)
    assert all(shares[a] == pytest.approx(1 / 3) for a in ("a", "b", "c"))


def test_softmax_reputations_unscored_agent_gets_the_floor():
    scored = [
        AgentOutcome("a", 100.0, abs_error=1.0),
        AgentOutcome("ghost", 100.0, abs_error=None),
    ]
    shares = softmax_reputations(scored)
    assert shares["ghost"] == 0.05
    assert shares["a"] > shares["ghost"]


def test_bounded_update_one_round_cannot_flip_a_reputation():
    # Prior reputation 0.9 for the sloppy agent, softmax target ~0.1 for it.
    reputations = {"accurate": 0.1, "sloppy": 0.9}
    target = {"accurate": 0.9, "sloppy": 0.1}
    updated = bounded_update(reputations, target, learning_rate=0.1)
    # Bounded blend: still ordered like the prior after one round.
    assert updated["sloppy"] > updated["accurate"]
    # lr is hard-capped at 0.5 — even asking for more cannot dominate.
    extreme = bounded_update(reputations, target, learning_rate=10.0)
    assert extreme["sloppy"] == pytest.approx(0.9 * 0.5 + 0.1 * 0.5)


def test_bounded_update_clamps_and_preserves_missing_agents():
    updated = bounded_update({"a": 0.9}, {"a": 5.0, "new": 0.5}, learning_rate=0.5)
    assert updated["a"] == 1.0  # clamped, not overshooting
    assert updated["new"] == 0.5  # new agents join at the target share
    # Departed agents keep their last reputation rather than being erased.
    kept = bounded_update({"a": 0.7, "gone": 0.4}, {"a": 0.6}, learning_rate=0.1)
    assert kept["gone"] == 0.4


def test_calibration_loop_scores_previous_round_against_next_consensus():
    loop = CalibrationLoop()
    reps = {"fast": 0.5, "slow": 0.5}

    # Round 1: fast is accurate, slow is far off. Nothing to score yet.
    r1 = loop.on_consensus(
        1, reps, [AgentOutcome("fast", 100.0), AgentOutcome("slow", 130.0)]
    )
    assert r1 == reps  # no update without a realized price

    # Round 2 consensus lands at 101 — round 1's submissions are scored.
    r2 = loop.on_consensus(
        2,
        r1,
        [AgentOutcome("fast", 101.5), AgentOutcome("slow", 101.8)],
        realized_price=101.0,
    )
    assert r2["fast"] > r2["slow"]
    last = loop.history[0]
    assert last.scored and last.realized_source == "external"
    assert last.agents[0].abs_error == pytest.approx(1.0)
    assert last.agents[1].abs_error == pytest.approx(29.0)


def test_calibration_loop_next_consensus_proxy_when_no_external_price():
    loop = CalibrationLoop()
    reps = {"a": 0.5, "b": 0.5}
    loop.on_consensus(1, reps, [AgentOutcome("a", 100.0), AgentOutcome("b", 104.0)])
    # Round 2 with no realized_price: the current submissions' median (102.05)
    # proxies the realized price for round 1.
    loop.on_consensus(2, reps, [AgentOutcome("a", 102.0), AgentOutcome("b", 102.1)])
    last = loop.history[0]
    assert last.scored and last.realized_source == "next_consensus"
    assert last.realized_price == pytest.approx(102.05)


def test_calibration_loop_converges_toward_the_accurate_agent():
    loop = CalibrationLoop(learning_rate=0.1)
    reps = {"accurate": 0.3, "noisy": 0.3}
    for i in range(1, 40):
        submissions = [
            AgentOutcome("accurate", 100.0 + (i % 2) * 0.1),
            AgentOutcome("noisy", 100.0 + (8 if i % 2 == 0 else -8)),
        ]
        reps = loop.on_consensus(i, reps, submissions, realized_price=100.0)
    assert reps["accurate"] > reps["noisy"] * 2
    # And reputations stay inside the documented band.
    assert all(0.05 <= v <= 1.0 for v in reps.values())


def test_outcome_log_is_json_replayable():
    loop = CalibrationLoop()
    loop.on_consensus(1, {"a": 0.5}, [AgentOutcome("a", 100.0)])
    loop.on_consensus(2, {"a": 0.5}, [AgentOutcome("a", 101.0)], realized_price=100.5)
    log = loop.outcome_log()
    assert isinstance(log, list) and len(log) == 2
    scored_entry = log[0]
    assert scored_entry["scored"] is True
    assert scored_entry["realized_source"] == "external"
    roundtrip = json.loads(json.dumps(scored_entry))
    assert roundtrip["agents"][0]["abs_error"] == pytest.approx(0.5)


# ── Orchestrator wiring (agents/orchestrator/main.py) ────────────────────
#
# SwarmFiOrchestrator.__init__ boots chain clients, but the provenance
# contract under test lives in _on_consensus. Bind the real (unbound)
# method to a stub carrying exactly the attributes it touches so the
# wiring itself is what gets tested.


def _wiring_stub():
    """Build (stub, submissions, calibration_loop) for the wiring tests."""
    from types import SimpleNamespace

    from shared.calibration import CalibrationLoop

    loop = CalibrationLoop()
    submissions = [
        SimpleNamespace(agent_address="a", price=100.0),
        SimpleNamespace(agent_address="b", price=104.0),
    ]
    stub = SimpleNamespace(
        calibration=loop,
        _consensus_count=1,
        _external_realized_price=None,
        agent_manager=SimpleNamespace(
            get_pending_submissions=lambda: submissions,
            get_reputations=lambda: {"a": 0.5, "b": 0.5},
            set_reputation=lambda addr, rep: None,
        ),
    )
    return stub, submissions, loop


def _consensus_result(price=102.0):
    from shared.types import ConsensusResult

    return ConsensusResult(asset_pair="INIT/USDC", consensus_price=price)


def test_orchestrator_wiring_scores_consensus_only_rounds_as_next_consensus():
    """No oracle landed -> scored against the next_consensus proxy.

    Regression: _on_consensus passed consensus_price (a float that is never
    None) as realized_price, labeling every scored entry 'external' and
    making the proxy branch unreachable — freezing swarm consensus as
    market truth in the outcome log that feeds reputation weights.
    """
    import asyncio

    from orchestrator.main import SwarmFiOrchestrator

    stub, submissions, loop = _wiring_stub()
    result = _consensus_result(102.0)

    # Round 1 parks unscored.
    asyncio.run(SwarmFiOrchestrator._on_consensus(stub, result))
    assert loop.history[0].scored is False

    # Round 2 with no oracle price: round 1 must be scored against the
    # next_consensus proxy (median of round 2's submissions = 102.1 —
    # deliberately distinct from consensus_price 102.0 so the assertion
    # proves which value was used), never labeled 'external'.
    submissions[:] = [
        SimpleNamespace(agent_address="a", price=102.0),
        SimpleNamespace(agent_address="b", price=102.2),
    ]
    stub._consensus_count = 2
    asyncio.run(SwarmFiOrchestrator._on_consensus(stub, result))
    scored = loop.history[0]
    assert scored.scored is True
    assert scored.realized_source == "next_consensus"
    assert scored.realized_price == pytest.approx(102.1)


def test_orchestrator_wiring_records_external_price_only_when_oracle_lands():
    """An oracle price lands -> recorded as 'external', consumed once."""
    import asyncio

    from orchestrator.main import SwarmFiOrchestrator

    stub, submissions, loop = _wiring_stub()
    result = _consensus_result(102.0)

    # Round 1 parks; round 2 scores it against an oracle price that landed.
    asyncio.run(SwarmFiOrchestrator._on_consensus(stub, result))
    stub._consensus_count = 2
    stub._external_realized_price = 101.0
    asyncio.run(SwarmFiOrchestrator._on_consensus(stub, result))
    scored = loop.history[0]
    assert scored.scored is True
    assert scored.realized_source == "external"
    assert scored.realized_price == pytest.approx(101.0)
    # Consumed exactly once: a stale oracle price must not re-fire.
    assert stub._external_realized_price is None


def test_external_replay_can_supersede_next_consensus_proxies():
    """Consensus-only rounds stay supersede-able; oracle rounds stay distinct."""
    loop = CalibrationLoop()
    loop.on_consensus(1, {"a": 0.5}, [AgentOutcome("a", 100.0)])
    loop.on_consensus(2, {"a": 0.5}, [AgentOutcome("a", 102.0)])
    assert loop.history[0].scored is True
    assert loop.history[0].realized_source == "next_consensus"

    # A later round WITH a true oracle price records as external — and the
    # proxy row keeps its next_consensus label, so a replay that supersedes
    # proxy rows can correct it without touching oracle-scored rows.
    loop.on_consensus(3, {"a": 0.5}, [AgentOutcome("a", 103.0)], realized_price=101.5)
    assert loop.history[0].realized_source == "next_consensus"
    assert loop.history[1].realized_source == "external"
    # Round 3 is parked and unscored: its log entry has no source yet.
    sources = [entry["realized_source"] for entry in loop.outcome_log()]
    assert sources[:2] == ["next_consensus", "external"]
    assert sources[2] is None

def test_proxy_run_warning_fires_once_at_threshold_and_external_resets(caplog):
    """Herding guard: warn on the threshold crossing, reset on external."""
    loop = CalibrationLoop()
    reps = {"a": 0.5}
    import logging

    with caplog.at_level(logging.WARNING, logger="shared.calibration"):
        for i in range(1, PROXY_RUN_WARNING_THRESHOLD + 2):
            loop.on_consensus(i, reps, [AgentOutcome("a", 100.0 + i)])
    warnings = [r for r in caplog.records if "consecutive proxy-scored" in r.message]
    assert len(warnings) == 1  # exactly once, at the crossing
    # An external price resets the run depth...
    loop.on_consensus(
        99, reps, [AgentOutcome("a", 100.0)], realized_price=100.5
    )
    assert loop.consecutive_proxy_rounds == 0
    assert loop.history[-2].proxy_run_depth == 0
    # ...and a fresh proxy run starts counting from 1.
    loop.on_consensus(100, reps, [AgentOutcome("a", 100.2)])
    assert loop.history[-2].proxy_run_depth == 1
