"""Tests for the row-4 calibration loop (agents/shared/calibration.py)."""

from __future__ import annotations

import json

import pytest
from shared.calibration import (
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
