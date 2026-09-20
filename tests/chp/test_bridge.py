"""Subprocess bridge: a non-Python swarm process drives the gate via `python -m shared.chp_gate`."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "agents"

REQUEST = {
    "consensus": {
        "asset_pair": "BTC/USDT",
        "consensus_price": 100.0,
        "participating_agents": ["agent_0", "agent_1", "agent_2"],
        "confidence": 0.8,
        "timestamp": 1758000000.0,
        "std_deviation": 0.2,
        "num_outliers": 0,
        "weighted_median": 100.0,
    },
    "submissions": [
        {
            "asset_pair": "BTC/USDT",
            "price": price,
            "confidence": 0.9,
            "source": f"agent_{i}",
            "agent_address": f"agent_{i}",
            "metadata": {"stale": False},
        }
        for i, price in enumerate((100.0, 100.2, 99.8))
    ],
}


def run_bridge(request: dict, ledger_path: Path, extra_env: dict | None = None) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": str(AGENTS_DIR),
            "SWARMFI_CHP_DECISIONS_PATH": str(ledger_path),
        }
    )
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, "-m", "shared.chp_gate"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(AGENTS_DIR),
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0, f"bridge failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestBridge:
    def test_locked_request_passes(self, tmp_path):
        outcome = run_bridge(
            REQUEST,
            tmp_path / "ledger.jsonl",
            {"SWARMFI_CHP_CONFIRMED_BY": "ops-lead"},
        )
        assert outcome["allowed"] is True
        assert outcome["session_status"] == "LOCKED"
        assert outcome["r0_results"]["Solvable"] == "PASS"
        # The refusal-free ledger holds the sealed decision.
        assert (tmp_path / "ledger.jsonl").exists()

    def test_unconfirmed_request_is_blocked(self, tmp_path):
        outcome = run_bridge(REQUEST, tmp_path / "ledger.jsonl")
        assert outcome["allowed"] is False
        assert outcome["session_status"] == "PROVISIONAL_LOCK"

    def test_refusal_is_reported(self, tmp_path):
        bad = json.loads(json.dumps(REQUEST))
        bad["consensus"]["confidence"] = 0.2
        outcome = run_bridge(bad, tmp_path / "ledger.jsonl")
        assert outcome["allowed"] is False
        assert outcome["r0_results"]["Worth_it"] == "FATAL"

    def test_bad_request_exits_nonzero(self, tmp_path):
        env = dict(os.environ)
        env.update(
            {
                "PYTHONPATH": str(AGENTS_DIR),
                "SWARMFI_CHP_DECISIONS_PATH": str(tmp_path / "ledger.jsonl"),
            }
        )
        proc = subprocess.run(
            [sys.executable, "-m", "shared.chp_gate"],
            input="not-json",
            capture_output=True,
            text=True,
            cwd=str(AGENTS_DIR),
            env=env,
            timeout=60,
        )
        assert proc.returncode == 2
        assert "bad request" in proc.stderr
