"""Shared fixtures for the SwarmFi CHP gate suite (mirrors the erp-control-plane CHP tests)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from shared.types import ConsensusResult, PriceSubmission

REPO_ROOT = Path(__file__).resolve().parents[2]

GOOD_PAIR = "BTC/USDT"


def make_submissions(
    pair: str = GOOD_PAIR,
    prices: tuple[float, ...] = (100.0, 100.2, 99.8),
    confidence: float = 0.9,
    metadata_extra: dict | None = None,
) -> list[PriceSubmission]:
    """A clean three-agent submission set around 100."""
    subs = []
    for i, price in enumerate(prices):
        meta = {"stale": False}
        if metadata_extra:
            meta.update(metadata_extra)
        subs.append(
            PriceSubmission(
                asset_pair=pair,
                price=price,
                confidence=confidence,
                source=f"agent_{i}",
                agent_address=f"agent_{i}",
                metadata=meta,
            )
        )
    return subs


def make_result(
    price: float = 100.0,
    confidence: float = 0.8,
    pair: str = GOOD_PAIR,
    std: float = 0.2,
    participants: int = 3,
) -> ConsensusResult:
    return ConsensusResult(
        asset_pair=pair,
        consensus_price=price,
        participating_agents=[f"agent_{i}" for i in range(participants)],
        confidence=confidence,
        timestamp=time.time(),
        std_deviation=std,
        num_outliers=0,
        weighted_median=price,
    )


@pytest.fixture
def gate(tmp_path: Path):
    """A gate with human lock ON (default) and a tmp ledger; no confirmer."""
    from shared.chp_gate import SwarmfiChpGate

    return SwarmfiChpGate.from_env(
        {"SWARMFI_CHP_DECISIONS_PATH": str(tmp_path / "chp_decisions.jsonl")}
    )


@pytest.fixture
def locked_gate(tmp_path: Path):
    """A gate with human lock ON and a named confirmer — capital may move."""
    from shared.chp_gate import SwarmfiChpGate

    return SwarmfiChpGate.from_env(
        {
            "SWARMFI_CHP_DECISIONS_PATH": str(tmp_path / "chp_decisions.jsonl"),
            "SWARMFI_CHP_CONFIRMED_BY": "ops-lead",
        }
    )


@pytest.fixture
def engine():
    """A real consensus engine for replay parity."""
    from shared.consensus import SwarmConsensus

    return SwarmConsensus()
