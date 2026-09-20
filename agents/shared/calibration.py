"""
Calibration feedback loop for swarm reputation weights (propagation row 4).

Origin: pythia's engine.py calibration loop (Brier score -> softmax weights
between rounds). This port adapts the loop to continuous price consensus:
agents submit price *values*, not probabilities, so the Brier score's
continuous analog (squared error against the realized price) drives the
update, and reputation weights are recomputed between rounds via a softmax
over negative error.

Design constraints, inherited from the origin and the portfolio's
deterministic-learner discipline:

- **Bounded updates.** A single round can never flip a reputation: the new
  value is a convex blend of the old reputation and the round's softmax
  score (learning rate <= 0.5), clamped to [min_reputation, 1.0]. A noisy
  or adversarial round nudges; it does not capture.
- **Pure functions.** Scoring and updating are pure and unit-testable;
  the orchestrator only applies the returned values.
- **Honest provenance.** The realized price for round N is proxied by
  round N+1's consensus value until an external resolution price is
  available (market resolution or an oracle feed) — `resolve_price` can be
  passed directly and takes precedence. The proxy is recorded in the
  outcome log so a future external price feed can replay and supersede it.

Wiring: the orchestrator calls `CalibrationLoop.on_consensus(result)` each
round; it scores the previous round's submissions against the new consensus
value and applies bounded reputation updates through the agent manager.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import AbstractSet, Any, Dict, List, Optional

DEFAULT_LEARNING_RATE = 0.1
DEFAULT_TEMPERATURE = 0.5
MIN_REPUTATION = 0.05

logger = logging.getLogger(__name__)
# Herding guard (prelint concern 2): the next-consensus proxy reinforces
# agreement with the swarm's own output. After this many consecutive
# proxy-scored rounds with no external price, warn — the proxy is becoming
# the primary path, not the fallback.
PROXY_RUN_WARNING_THRESHOLD = 10


@dataclass
class AgentOutcome:
    """One agent's performance in one consensus round."""

    agent_address: str
    submitted_price: float
    abs_error: Optional[float] = None  # populated when scored


@dataclass
class RoundOutcome:
    """Everything needed to score one round once a realized price exists."""

    round_index: int
    submitted_at: float
    agents: List[AgentOutcome]
    realized_price: Optional[float] = None  # None until the next round resolves it
    realized_source: Optional[str] = None  # "next_consensus" or "external"
    proxy_run_depth: Optional[int] = None  # consecutive proxy rounds at scoring time
    scored: bool = False


def score_round(
    agents: List[AgentOutcome],
    realized_price: float,
) -> List[AgentOutcome]:
    """Fill in abs_error for each agent against the realized price.

    Pure: returns the scored copies, does not mutate inputs. Agents with a
    non-finite submitted price are left unscored (skipped by the update).
    """
    scored: List[AgentOutcome] = []
    for a in agents:
        err = abs(a.submitted_price - realized_price) if math.isfinite(a.submitted_price) else None
        scored.append(AgentOutcome(a.agent_address, a.submitted_price, err))
    return scored


def softmax_reputations(
    scored: List[AgentOutcome],
    temperature: float = DEFAULT_TEMPERATURE,
) -> Dict[str, float]:
    """Softmax over negative absolute error — lower error, higher share.

    Pure. Unscored agents receive the floor (they cannot earn weight from a
    round they did not score in). Equal errors give equal shares regardless
    of prior reputation: the prior is applied by the bounded blend, not here.
    """
    finite = [a for a in scored if a.abs_error is not None and math.isfinite(a.abs_error)]
    shares = {a.agent_address: MIN_REPUTATION for a in scored}
    if not finite:
        return shares
    # Stable softmax over -err / T. Errors are normalized by the median
    # error so the temperature is scale-free across markets.
    errs = sorted(a.abs_error for a in finite)  # type: ignore[arg-type]
    median_err = errs[len(errs) // 2] or 1.0
    max_term = -min(a.abs_error for a in finite) / median_err / temperature  # type: ignore[operator]
    exps = {
        a.agent_address: math.exp(-(a.abs_error / median_err) / temperature - max_term)
        for a in finite
    }
    total = sum(exps.values())
    for addr, e in exps.items():
        shares[addr] = e / total
    return shares


def bounded_update(
    reputations: Dict[str, float],
    target: Dict[str, float],
    learning_rate: float = DEFAULT_LEARNING_RATE,
    slashed: Optional[AbstractSet[str]] = None,
) -> Dict[str, float]:
    """Blend current reputations toward the round's softmax shares.

    Pure. new = (1 - lr) * old + lr * target, clamped to
    [MIN_REPUTATION, 1.0]. Agents absent from one side keep the other
    side's value (new agents join at the target share; departed agents
    keep their last reputation rather than being erased).

    Slash guard: an address in `slashed` is never blended above its
    current value — a reputation just written by an on-chain slash must
    not be silently restored by accurate-looking post-slash submissions.
    Downward adjustments still apply (the guard caps, it does not freeze).
    """
    slashed_set = slashed if slashed is not None else frozenset()
    lr = min(max(learning_rate, 0.0), 0.5)  # hard bound: one round cannot dominate
    blended = dict(reputations)
    for addr in set(reputations) | set(target):
        old = reputations.get(addr)
        new = target.get(addr)
        if old is None:
            blended[addr] = min(max(new, MIN_REPUTATION), 1.0)  # type: ignore[arg-type]
        elif new is None:
            blended[addr] = old
        else:
            value = min(max((1 - lr) * old + lr * new, MIN_REPUTATION), 1.0)
            if addr in slashed_set:
                value = min(value, old)  # never raise a slashed agent
            blended[addr] = value
    return blended


class CalibrationLoop:
    """Between-round calibration: record submissions, score on resolution.

    Round N's submissions are scored against round N+1's consensus value
    (next_consensus proxy) or against an externally supplied realized price
    when one is passed. Updates are bounded per `bounded_update`.
    """

    def __init__(
        self,
        learning_rate: float = DEFAULT_LEARNING_RATE,
        temperature: float = DEFAULT_TEMPERATURE,
        slashed_provider: Optional[Callable[[], AbstractSet[str]]] = None,
    ) -> None:
        self.learning_rate = learning_rate
        self.temperature = temperature
        # Slash-state source wired by the operator/orchestrator (on-chain
        # slashing is the adversarial track); the loop never guesses it.
        self._slashed_provider = slashed_provider
        self._pending: Optional[RoundOutcome] = None
        self.history: List[RoundOutcome] = []
        self.consecutive_proxy_rounds = 0

    def _slashed_addresses(self) -> frozenset:
        if self._slashed_provider is None:
            return frozenset()
        result = self._slashed_provider()
        return frozenset(result) if result is not None else frozenset()

    def on_consensus(
        self,
        round_index: int,
        reputations: Dict[str, float],
        submissions: List[AgentOutcome],
        realized_price: Optional[float] = None,
    ) -> Dict[str, float]:
        """Record this round and score the previous round's submissions.

        Returns the updated reputation map (empty dict = no scores yet).
        """
        updated = dict(reputations)

        # Resolve a pending round with an external price if provided,
        # otherwise with this round's consensus value as the proxy.
        if self._pending is not None:
            price = realized_price if realized_price is not None else self._median_of(submissions)
            if price is not None:
                source = "external" if realized_price is not None else "next_consensus"
                self._pending.agents = score_round(self._pending.agents, price)
                self._pending.realized_price = price
                self._pending.realized_source = source
                if source == "external":
                    self.consecutive_proxy_rounds = 0
                else:
                    self.consecutive_proxy_rounds += 1
                self._pending.proxy_run_depth = self.consecutive_proxy_rounds
                self._pending.scored = True
                if (
                    source == "next_consensus"
                    and self._pending.proxy_run_depth == PROXY_RUN_WARNING_THRESHOLD
                ):
                    logger.warning(
                        "%d consecutive proxy-scored rounds with no external "
                        "price — reputation is being fed by swarm consensus "
                        "(herding risk). Attach an external price feed or "
                        "freeze updates.",
                        self._pending.proxy_run_depth,
                    )
                shares = softmax_reputations(self._pending.agents, self.temperature)
                updated = bounded_update(
                    updated, shares, self.learning_rate, slashed=self._slashed_addresses()
                )

        # Park this round for the next call to score.
        self._pending = RoundOutcome(
            round_index=round_index,
            submitted_at=time.time(),
            agents=[AgentOutcome(a.agent_address, a.submitted_price) for a in submissions],
        )
        self.history.append(self._pending)
        return updated

    @staticmethod
    def _median_of(submissions: List[AgentOutcome]) -> Optional[float]:
        prices = sorted(a.submitted_price for a in submissions if math.isfinite(a.submitted_price))
        if not prices:
            return None
        mid = len(prices) // 2
        if len(prices) % 2 == 1:
            return prices[mid]
        return (prices[mid - 1] + prices[mid]) / 2

    def outcome_log(self) -> List[Dict[str, Any]]:
        """Replayable outcome log — one JSON-able record per round."""
        return [
            {
                "round": r.round_index,
                "submitted_at": r.submitted_at,
                "realized_price": r.realized_price,
                "realized_source": r.realized_source,
                "proxy_run_depth": r.proxy_run_depth,
                "scored": r.scored,
                "agents": [
                    {
                        "address": a.agent_address,
                        "price": a.submitted_price,
                        "abs_error": a.abs_error,
                    }
                    for a in r.agents
                ],
            }
            for r in self.history
        ]
