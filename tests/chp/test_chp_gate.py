"""R0 gate, foundation floor, and human-lock tests (mirrors the erp-ref CHP suite)."""

from __future__ import annotations

import time

import pytest
from chp import SessionStatus, ValidationResult, Verdict
from conftest import GOOD_PAIR, make_result, make_submissions
from shared.consensus import SwarmConsensus


class TestR0Gate:
    def test_passing_consensus_passes_r0(self, gate):
        evaluation = gate.evaluate_r0(make_result(), max_participants=3)
        assert evaluation.verdict == Verdict.PASS
        assert evaluation.results == {
            "Solvable": "PASS",
            "Scoped": "PASS",
            "Valid": "PASS",
            "Worth_it": "PASS",
        }

    def test_worth_it_fails_below_decision_grade_confidence(self, gate):
        outcome = gate.allow_submission(
            make_result(confidence=0.2),
            submissions=make_submissions(confidence=0.2),
            consensus_engine=SwarmConsensus(),
        )
        assert outcome.allowed is False
        assert outcome.r0_results["Worth_it"] == "FATAL"
        record = gate.ledger.get(outcome.decision_id)
        assert record["kind"] == "r0_refusal"

    def test_scoped_fails_on_malformed_pair(self, gate):
        result = make_result(pair="NOT_A_PAIR")
        outcome = gate.allow_submission(
            result,
            submissions=make_submissions(pair="NOT_A_PAIR"),
            consensus_engine=SwarmConsensus(),
        )
        assert outcome.allowed is False
        assert outcome.r0_results["Scoped"] == "FATAL"

    def test_solvable_fails_without_participants(self, gate):
        result = make_result(participants=0)
        result.participating_agents = []
        outcome = gate.allow_submission(
            result,
            submissions=make_submissions(),
            consensus_engine=SwarmConsensus(),
        )
        assert outcome.allowed is False
        assert outcome.r0_results["Solvable"] == "FATAL"

    def test_valid_fails_when_move_exceeds_state_bound(self, gate):
        gate.note_posted_price(GOOD_PAIR, 100.0)
        result = make_result(price=160.0)  # +60% vs last posted, cap is 25%
        outcome = gate.allow_submission(
            result,
            submissions=make_submissions(prices=(159.9, 160.1, 160.0)),
            consensus_engine=SwarmConsensus(),
        )
        assert outcome.allowed is False
        assert outcome.r0_results["Valid"] == "FATAL"

    def test_first_post_has_no_state_bound(self, gate):
        assert gate.evaluate_r0(make_result(price=90000.0)).results["Valid"] == "PASS"


class TestFoundationFloor:
    def test_floor_is_85_from_package_and_repo_config(self, gate):
        assert gate.floor == 85

    def test_floor_failure_below_85_is_refused(self, gate):
        # No consensus engine -> no replay parity evidence -> score 70 < 85.
        outcome = gate.allow_submission(
            make_result(),
            submissions=make_submissions(),
            consensus_engine=None,
        )
        assert outcome.allowed is False
        assert outcome.foundation_score == 70
        assert outcome.session_status == SessionStatus.REFRAME_REQUIRED.value
        record = gate.ledger.get(outcome.decision_id)
        assert record["kind"] == "floor_refusal"
        assert record["foundation_verdict"] == Verdict.REFRAME.value

    def test_replay_parity_mismatch_is_fatal(self, gate):
        # A compromised/aggregated value that the buffered submissions cannot
        # reproduce must never be posted.
        class TamperedEngine(SwarmConsensus):
            def compute_consensus(self, submissions, agents=None):
                replay = super().compute_consensus(submissions, agents)
                replay.consensus_price = replay.consensus_price * 1.5
                return replay

        outcome = gate.allow_submission(
            make_result(),
            submissions=make_submissions(),
            consensus_engine=TamperedEngine(),
        )
        assert outcome.allowed is False
        record = gate.ledger.get(outcome.decision_id)
        assert record["kind"] == "parity_mismatch"

    def test_full_pass_scores_100(self, locked_gate, engine):
        outcome = locked_gate.allow_submission(
            make_result(),
            submissions=make_submissions(),
            consensus_engine=engine,
            max_participants=3,
        )
        assert outcome.allowed is True
        assert outcome.foundation_score == 100
        assert outcome.session_status == SessionStatus.LOCKED.value


class TestHumanLock:
    def test_sessions_start_exploring(self, locked_gate, engine):
        result = make_result()
        assessment = locked_gate.assess_foundation(
            result,
            submissions=make_submissions(),
            consensus_engine=engine,
        )
        case, report = locked_gate.harden(result, assessment=assessment)
        assert case.status == SessionStatus.EXPLORING
        assert report.r0_verdict == Verdict.PASS

    def test_validation_requires_provisional_lock(self, locked_gate, engine):
        """apply_third_party_validation refuses a case that is not PROVISIONAL_LOCK."""
        result = make_result()
        assessment = locked_gate.assess_foundation(
            result, submissions=make_submissions(), consensus_engine=engine
        )
        case, _ = locked_gate.harden(result, assessment=assessment)
        assert case.status == SessionStatus.EXPLORING
        with pytest.raises(ValueError):
            locked_gate.lock(case, "ops-lead")

    def test_lock_flow_exploring_to_locked(self, locked_gate, engine):
        result = make_result()
        outcome = locked_gate.allow_submission(
            result, submissions=make_submissions(), consensus_engine=engine
        )
        assert outcome.allowed is True
        assert outcome.session_status == SessionStatus.LOCKED.value
        record = locked_gate.ledger.get(outcome.decision_id)
        assert record["kind"] == "oracle_post"
        assert record["session_status"] == SessionStatus.LOCKED.value
        assert record["confirmed_by"] == "ops-lead"
        assert record["r0_verdict"] == Verdict.PASS.value

    def test_human_lock_blocks_without_confirmer(self, gate, engine):
        outcome = gate.allow_submission(
            make_result(), submissions=make_submissions(), consensus_engine=engine
        )
        assert outcome.allowed is False
        assert outcome.session_status == SessionStatus.PROVISIONAL_LOCK.value
        record = gate.ledger.get(outcome.decision_id)
        assert record["kind"] == "human_lock_required"
        assert record["confirmed_by"] is None

    def test_human_lock_off_allows_provisional_post(self, tmp_path, engine):
        from shared.chp_gate import SwarmfiChpGate

        gate = SwarmfiChpGate.from_env(
            {
                "SWARMFI_CHP_DECISIONS_PATH": str(tmp_path / "ledger.jsonl"),
                "SWARMFI_CHP_REQUIRE_HUMAN_LOCK": "0",
            }
        )
        outcome = gate.allow_submission(
            make_result(), submissions=make_submissions(), consensus_engine=engine
        )
        assert outcome.allowed is True
        assert outcome.session_status == SessionStatus.PROVISIONAL_LOCK.value
        record = gate.ledger.get(outcome.decision_id)
        assert record["session_status"] == SessionStatus.PROVISIONAL_LOCK.value

    def test_reject_returns_case_to_exploring(self, gate, engine):
        from chp import ThirdPartyValidation, apply_third_party_validation

        result = make_result()
        assessment = gate.assess_foundation(
            result, submissions=make_submissions(), consensus_engine=engine
        )
        case, _ = gate.harden(result, assessment=assessment)
        # REJECT is only reachable through the same PROVISIONAL_LOCK stage:
        case.status = SessionStatus.PROVISIONAL_LOCK
        status = apply_third_party_validation(
            case,
            ThirdPartyValidation(
                validator="ops-lead",
                item=case.decision_id,
                challenge="Confirm the post",
                result=ValidationResult.REJECT,
                rationale="state assertion failed review",
            ),
        )
        assert status == SessionStatus.EXPLORING
        assert case.flip_criteria


class TestFailClosed:
    def test_gate_exception_is_reported_not_hidden(self, gate, engine, caplog):
        class ExplodingEngine:
            min_submissions = 2

            def compute_consensus(self, submissions, agents=None):
                raise RuntimeError("engine exploded")

        # The engine explosion is contained inside replay parity -> refusal.
        outcome = gate.allow_submission(
            make_result(),
            submissions=make_submissions(),
            consensus_engine=ExplodingEngine(),
        )
        assert outcome.allowed is False
        assert "replay raised" in " ".join(outcome.findings)


class TestTimeStability:
    def test_decision_ids_are_unique_per_round(self, locked_gate, engine):
        ids = set()
        for _ in range(2):
            outcome = locked_gate.allow_submission(
                make_result(),
                submissions=make_submissions(),
                consensus_engine=engine,
            )
            ids.add(outcome.decision_id)
            time.sleep(0.01)
        assert len(ids) == 2
