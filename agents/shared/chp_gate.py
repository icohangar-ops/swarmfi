"""Gate-only CHP integration for the SwarmFi decision path.

Integration decision (Phase 2 of the CHP rollout; pattern proven in
erp-control-plane commit 70678cc, api/genbi/chp.py):

- **Option (a) rejected.** icohangar-ops/chp-rust-pack was checked first: it
  is a Node marketing/asset pack (landing pages, memos, ``pack.json``), not a
  native Rust CHP crate — there is nothing to link into a Rust build.
- **Option (b) chosen, native core first.** The canonical Profile A substrate
  is now the ``chp-gate`` binary from icohangar-ops/chp-core-rs, pinned at
  v0.1.0 (main 794d61357100): each gate operation resolves the binary via
  ``CHP_GATE_BIN`` then ``chp-gate`` on ``PATH`` and drives its JSON-line
  stdio protocol (evaluate_r0_gate, foundation_floor, foundation_verdict,
  evaluate_devils_advocate, payload_build, payload_validate, ledger_*).
  Where the binary and the Python copy disagree, the pinned binary's
  semantics win. The pure-Python package
  ``consensus-hardening-protocol==0.1.1`` remains the documented fallback
  and gates in-process only when no binary resolves. The verified
  capital-moving path in this repository is Python
  (``orchestrator.main._consensus_loop`` ->
  ``agent_manager.compute_and_submit_consensus`` ->
  ``chain_interface.submit_price`` — the on-chain oracle post that marks
  perp positions and drives vault rebalances); it spawns the binary per
  gate operation through the same public interface. A stdlib JSON
  subprocess entry point is still provided (``python -m shared.chp_gate``)
  so a non-Python swarm process can drive the same gate — that bridge now
  prefers the native binary too and drops to the Python package only as
  the fallback.
- **Option (c) not taken.** An MCP client to ``@cubiczan/chp-mcp`` adds a
  server dependency and async transport to a deterministic, synchronous
  decision — heavier than the loop needs.

Gate shape (mirrors the erp-control-plane promotion gate):

1. **R0 gate — before any capital-moving output.** The consensus price post
   is *solvable* (a decision-grade consensus exists: finite positive price
   with participating agents — the position is computable from the swarm /
   portfolio state), *scoped* (a single well-formed asset pair with bounded
   confidence and dispersion), *valid* (the target price is sane and, where
   a last-posted state exists, within the configured move bound — the state
   assertion that stands in for external golden-market parity), and
   *worth_it* (confidence at or above the decision-grade threshold — a
   sub-threshold consensus must not move capital). Result keys are
   capitalized (``Solvable``, ``Scoped``, ``Valid``, ``Worth_it``); any
   ``FATAL`` result HALTs the submission.
2. **Deterministic adversary foundation pass** — guardrails 40 + bounded
   result 30 + golden parity 30. Parity is *replay parity*: the consensus
   engine recomputes the weighted median from the same buffered submissions
   (the swarm's own state is the golden reference; no external golden price
   exists for a perp oracle — documented per the task's "state assertions
   serve instead" allowance, which is applied to R0's Valid check). A parity
   mismatch is fatal. The foundation floor is the package's ``blockchain``
   floor (85), raised to ``.chp/R0_CONFIG.yaml``'s ``foundation.pass_threshold``
   when that is stricter. Below the floor the case lands ``REFRAME_REQUIRED``
   and the submission is refused.
3. **Human lock.** Sessions start ``EXPLORING``; a hardened case is set
   explicitly to ``PROVISIONAL_LOCK`` before third-party validation, and a
   named ``confirmed_by`` is required before ``apply_third_party_validation``
   locks it. ``SWARMFI_CHP_REQUIRE_HUMAN_LOCK`` defaults ON: capital only
   moves on a ``LOCKED`` decision.
4. **Decision ledger.** Append-only JSONL. The CHP payload envelope is
   structure-only, so the ledger seals each record with its own SHA-256
   ``body_sha256`` and re-validates envelope + body digest on every read
   (``integrity_valid``). Refusals are recorded too — the mechanical answer
   to "why didn't the swarm post?".

The gate fails closed: a gate error refuses the submission rather than
letting capital move ungated.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import math
import os
import re
import shutil
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from chp import (
    CHPOrchestrator,
    CHPReport,
    DecisionCase,
    Dossier,
    FoundationAttack,
    FoundationDisclosure,
    SessionStatus,
    ThirdPartyValidation,
    ValidationResult,
    Verdict,
    apply_third_party_validation,
    build_payload_envelope,
    validate_payload_envelope,
)
from chp.foundation import foundation_floor
from chp.gates import GateEvaluation, evaluate_r0_gate

logger = logging.getLogger("CHP")

# Deterministic adversary scoring (out of 100) — the erp-control-plane split.
_GUARDRAIL_POINTS = 40
_BOUNDED_RESULT_POINTS = 30
_PARITY_POINTS = 30
_FULL_SCORE = _GUARDRAIL_POINTS + _BOUNDED_RESULT_POINTS + _PARITY_POINTS

#: Package domain for this repo (``FOUNDATION_FLOORS["blockchain"] == 85``).
_DOMAIN = "blockchain"

_ASSET_PAIR = re.compile(r"^[A-Z0-9]{2,20}/[A-Z0-9]{2,20}$")
_PASS_THRESHOLD = re.compile(r"pass_threshold:\s*(\d+)")

# Replay tolerance: the consensus rounds to 8 decimals, so a faithful replay
# matches to floating noise.
_REPLAY_REL_TOLERANCE = 1e-6

_ENVELOPE_ROUTE = "ORACLE_POST"


class GateUnavailable(RuntimeError):
    """The gate substrate is unavailable — the gate refuses to run fail-closed.

    Raised when the Python CHP package is missing (fallback mode) or when a
    resolved native binary fails at call time (spawn error, timeout,
    unparseable or error response). Callers refuse the submission; the gate
    never degrades silently to the other substrate.
    """


# --------------------------------------------------------------------------
# Native substrate: the canonical chp-core-rs binary, with the in-repo
# Python package as the documented fallback. Resolution order per operation:
# CHP_GATE_BIN (executable file), then `chp-gate` on PATH, then Python.
# --------------------------------------------------------------------------

#: Canonical native core pin — where the binary and the Python fallback
#: disagree on a response value, THIS version's semantics win.
CHP_CORE_RS_PIN = "v0.1.0"

# The binary answers each method in microseconds; a longer wait is a wedged
# process, not a slow decision.
_NATIVE_TIMEOUT_S = 10.0


def resolve_gate_bin() -> Optional[str]:
    """Resolve the native chp-gate binary: CHP_GATE_BIN first, then PATH.

    ``None`` is the documented signal for the Python fallback. A
    ``CHP_GATE_BIN`` naming a missing or non-executable file logs a warning
    and falls through to ``PATH``; a resolvable binary that fails at *call
    time* raises :class:`GateUnavailable` instead of degrading to Python.
    """
    env_bin = os.environ.get("CHP_GATE_BIN", "").strip()
    if env_bin:
        if os.path.isfile(env_bin) and os.access(env_bin, os.X_OK):
            return env_bin
        logger.warning(
            "CHP_GATE_BIN=%r is not an executable file — falling through to PATH",
            env_bin,
        )
    return shutil.which("chp-gate")


def native_gate_call(binary: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """One chp-gate protocol round trip: one JSON request line in, one out.

    The binary is stateless and microsecond-cheap, so it is spawned per call
    rather than kept warm. An ``{"error": ...}`` response to a known method
    is a contract bug, not a recoverable condition — it surfaces as
    :class:`GateUnavailable` so every caller fails closed.
    """
    request = json.dumps({"method": method, "params": params}) + "\n"
    try:
        proc = subprocess.run(
            [binary],
            input=request,
            capture_output=True,
            encoding="utf-8",
            timeout=_NATIVE_TIMEOUT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GateUnavailable(f"chp-gate binary {binary!r} failed: {exc}") from exc
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.returncode != 0 or not lines:
        raise GateUnavailable(
            f"chp-gate binary {binary!r} produced no response "
            f"(exit {proc.returncode}): {proc.stderr.strip()[:200]}"
        )
    try:
        response = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise GateUnavailable(
            f"chp-gate binary {binary!r} sent an unparseable response: {exc}"
        ) from exc
    if "error" in response:
        raise GateUnavailable(f"chp-gate rejected {method}: {response['error']}")
    return response


def seal_payload_envelope(body: str, route: str) -> str:
    """Render the CHP payload envelope — native payload_build, Python fallback."""
    binary = resolve_gate_bin()
    if binary is None:
        return build_payload_envelope(body, route=route).render()
    rendered = native_gate_call(binary, "payload_build", {"body": body, "route": route})
    return str(rendered["rendered"])


def validate_payload_envelope_structure(rendered: str) -> bool:
    """Structure-only envelope check — native payload_validate, Python fallback."""
    binary = resolve_gate_bin()
    if binary is None:
        return validate_payload_envelope(rendered)
    response = native_gate_call(binary, "payload_validate", {"rendered": rendered})
    return bool(response["valid"])


@dataclass(frozen=True)
class FoundationAssessment:
    """The deterministic adversary's verdict on a would-be oracle post."""

    score: int
    domain: str
    findings: List[str] = field(default_factory=list)
    parity: Optional[Dict[str, Any]] = None
    replay_matched: bool = False


@dataclass(frozen=True)
class GateOutcome:
    """What the gate told the swarm loop about one would-be submission."""

    allowed: bool
    decision_id: str
    reason: str
    r0_results: Dict[str, str] = field(default_factory=dict)
    foundation_score: Optional[int] = None
    session_status: Optional[str] = None
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DecisionLedger:
    """Append-only JSONL of CHP decision records; integrity re-checked on read."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def append(self, entry: Dict[str, Any]) -> None:
        line = json.dumps(entry, ensure_ascii=False)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def _read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.path.exists():
                return []
            lines = self.path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Newest-first records with envelope and body digest re-validated on read."""
        return [self._checked(entry) for entry in self._read_all()[-limit:]][::-1]

    def get(self, decision_id: str) -> Optional[Dict[str, Any]]:
        for entry in reversed(self._read_all()):
            if entry.get("decision_id") == decision_id:
                return self._checked(entry)
        return None

    @staticmethod
    def _checked(entry: Dict[str, Any]) -> Dict[str, Any]:
        """Re-validate on read: envelope structure and the ledger's own digest.

        The CHP payload envelope validates structure only, so the ledger adds
        its own SHA-256 over the sealed body — a tampered record reads as
        ``integrity_valid: false``.
        """
        body = entry.get("body", "")
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return {
            **entry,
            "envelope_valid": validate_payload_envelope_structure(entry.get("envelope", "")),
            "integrity_valid": digest == entry.get("body_sha256"),
        }


class SwarmfiChpGate:
    """Runs a swarm consensus post through CHP: R0 -> foundation -> lock -> record."""

    def __init__(
        self,
        *,
        ledger_path: Path,
        require_human_lock: bool = True,
        confirmed_by: Optional[str] = None,
        min_confidence: float = 0.5,
        max_std_fraction: float = 0.10,
        max_price_move: float = 0.25,
        domain: str = _DOMAIN,
        config_path: Optional[Path] = None,
    ) -> None:
        self.ledger = DecisionLedger(ledger_path)
        self.require_human_lock = require_human_lock
        self.confirmed_by = confirmed_by
        self.min_confidence = min_confidence
        self.max_std_fraction = max_std_fraction
        self.max_price_move = max_price_move
        self.domain = domain
        self.config_path = config_path or (
            Path(__file__).resolve().parents[2] / ".chp" / "R0_CONFIG.yaml"
        )
        # Last posted on-chain price per asset pair — the portfolio-state
        # assertion behind R0's Valid check (see module docstring).
        self._last_posted: Dict[str, float] = {}

    # ------------------------------------------------------------- env setup
    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> SwarmfiChpGate:
        env = dict(os.environ if env is None else env)
        return cls(
            ledger_path=Path(
                env.get("SWARMFI_CHP_DECISIONS_PATH", "~/.swarmfi/chp_decisions.jsonl")
            ).expanduser(),
            require_human_lock=env.get("SWARMFI_CHP_REQUIRE_HUMAN_LOCK", "1").strip().lower()
            in {"1", "true", "yes"},
            confirmed_by=env.get("SWARMFI_CHP_CONFIRMED_BY") or None,
            min_confidence=float(env.get("SWARMFI_CHP_MIN_CONFIDENCE", "0.5")),
            max_std_fraction=float(env.get("SWARMFI_CHP_MAX_STD_FRACTION", "0.10")),
            max_price_move=float(env.get("SWARMFI_CHP_MAX_PRICE_MOVE", "0.25")),
            domain=env.get("SWARMFI_CHP_DOMAIN", _DOMAIN),
        )

    @property
    def floor(self) -> int:
        """DeFi floor: the package's domain floor, raised by R0_CONFIG when stricter."""
        binary = resolve_gate_bin()
        if binary is None:
            floor = foundation_floor(self.domain)
        else:
            floor = int(
                native_gate_call(binary, "foundation_floor", {"domain": self.domain})["floor"]
            )
        try:
            match = _PASS_THRESHOLD.search(self.config_path.read_text(encoding="utf-8"))
        except OSError:
            return floor
        if match:
            floor = max(floor, int(match.group(1)))
        return floor

    # -------------------------------------------------------- state tracking
    def note_posted_price(self, asset_pair: str, price: float) -> None:
        """Record the price actually posted on-chain (feeds R0's Valid assertion)."""
        self._last_posted[asset_pair] = float(price)

    # ------------------------------------------------------------------- R0
    def evaluate_r0(
        self,
        result: Any,
        *,
        max_participants: Optional[int] = None,
    ) -> GateEvaluation:
        """The pre-submission gate: HALT before any capital-moving output.

        ``result`` is duck-typed on the ``ConsensusResult`` shape so this
        module stays free of the pydantic models.
        """
        price = float(result.consensus_price)
        confidence = float(result.confidence)
        participants = list(result.participating_agents)
        pair = str(result.asset_pair).upper()

        last = self._last_posted.get(pair)
        within_move_bound = (
            last is None
            or last <= 0
            or abs(price / last - 1.0) <= self.max_price_move
        )

        return self._r0_evaluation(
            solvable=(
                math.isfinite(price)
                and price > 0
                and len(participants) >= 1
            ),
            scoped=(
                bool(_ASSET_PAIR.match(pair))
                and 0.0 <= confidence <= 1.0
                and math.isfinite(float(result.std_deviation))
                and (max_participants is None or len(participants) <= max_participants)
            ),
            valid=math.isfinite(price) and price > 0 and within_move_bound,
            worth_it=confidence >= self.min_confidence,
        )

    @staticmethod
    def _r0_evaluation(
        *, solvable: bool, scoped: bool, valid: bool, worth_it: bool
    ) -> GateEvaluation:
        """R0 verdicts from the native evaluate_r0_gate, or the Python gates.

        Both return the capitalized rows in declaration order and the
        PASS/HALT aggregation; the native rows arrive as ``[key, value]``
        pairs and are folded into the same ``GateEvaluation`` shape, so
        callers see one type.
        """
        binary = resolve_gate_bin()
        if binary is None:
            return evaluate_r0_gate(
                solvable=solvable, scoped=scoped, valid=valid, worth_it=worth_it
            )
        response = native_gate_call(
            binary,
            "evaluate_r0_gate",
            {
                "solvable": solvable,
                "scoped": scoped,
                "valid": valid,
                "worth_it": worth_it,
            },
        )
        return GateEvaluation(
            results={key: verdict for key, verdict in response["results"]},
            verdict=Verdict(response["verdict"]),
        )

    # ------------------------------------------------------------ foundation
    def assess_foundation(
        self,
        result: Any,
        *,
        submissions: List[Any],
        agents: Optional[List[Any]] = None,
        consensus_engine: Any = None,
        max_participants: Optional[int] = None,
    ) -> FoundationAssessment:
        """The deterministic adversary scores the would-be post (0-100)."""
        findings: List[str] = []
        score = 0

        pair = str(result.asset_pair).upper()
        price = float(result.consensus_price)
        confidence = float(result.confidence)
        participants = list(result.participating_agents)

        # Guardrails (40): structural legality of the would-be submission.
        stale = [s for s in submissions if getattr(s, "metadata", {}).get("stale") is True]
        guardrails_ok = (
            bool(submissions)
            and math.isfinite(price)
            and price > 0
            and 0.0 <= confidence <= 1.0
            and bool(participants)
            and all(float(s.price) > 0 for s in submissions)
            and len({str(s.asset_pair).upper() for s in submissions}) == 1
            and all(str(s.asset_pair).upper() == pair for s in submissions)
            and not stale
        )
        if guardrails_ok:
            score += _GUARDRAIL_POINTS
            findings.append(
                f"guardrails passed: {len(submissions)} submission(s) for {pair}, "
                "positive prices, bounded confidence, no stale inputs"
            )
        else:
            findings.append(
                "guardrail failure: malformed submission set (empty, stale, "
                "cross-pair, non-positive price, or unbounded confidence)"
            )

        # Bounded result (30): bounded participation and bounded dispersion.
        min_submissions = getattr(consensus_engine, "min_submissions", 2)
        std_deviation = float(result.std_deviation)
        std_fraction = std_deviation / price if price > 0 else math.inf
        if len(participants) < min_submissions:
            findings.append(
                f"unbounded result: {len(participants)} participant(s) below "
                f"min_submissions={min_submissions}"
            )
        elif max_participants is not None and len(participants) > max_participants:
            findings.append(
                f"unbounded result: {len(participants)} participant(s) above "
                f"registered max={max_participants}"
            )
        elif std_fraction > self.max_std_fraction:
            findings.append(
                f"unbounded result: std/price {std_fraction:.4f} above cap "
                f"{self.max_std_fraction:.4f}"
            )
        else:
            score += _BOUNDED_RESULT_POINTS
            findings.append(
                f"bounded result: {len(participants)} participant(s), "
                f"std/price {std_fraction:.4f} within cap {self.max_std_fraction:.4f}"
            )

        # Golden parity (30): deterministic replay of the consensus from the
        # same buffered submissions (the swarm's own state is the reference).
        parity: Optional[Dict[str, Any]] = None
        if consensus_engine is None:
            findings.append(
                "no consensus engine provided — replay parity evidence unavailable"
            )
        else:
            replay, replay_error = self._replay(consensus_engine, submissions, agents)
            if replay is None:
                findings.append(
                    f"replay parity unavailable: {replay_error}"
                )
            else:
                replay_price = float(replay.consensus_price)
                delta = abs(replay_price - price)
                tolerance = max(1e-8, _REPLAY_REL_TOLERANCE * abs(price))
                parity = {
                    "expected": price,
                    "actual": replay_price,
                    "delta": delta,
                    "tolerance": tolerance,
                    "within_tolerance": delta <= tolerance,
                }
                if delta <= tolerance:
                    score += _PARITY_POINTS
                    findings.append(
                        f"replay parity: engine recomputed {replay_price:.8f} for "
                        f"{pair}, submitted {price:.8f} (delta {delta:.2e})"
                    )
                else:
                    findings.append(
                        f"replay parity MISMATCH: engine recomputed "
                        f"{replay_price:.8f} for {pair}, submitted {price:.8f} "
                        f"(delta {delta:.2e} > {tolerance:.2e})"
                    )

        return FoundationAssessment(
            score=min(score, _FULL_SCORE),
            domain=self.domain,
            findings=findings,
            parity=parity,
            replay_matched=bool(parity and parity["within_tolerance"]),
        )

    @staticmethod
    def _replay(
        consensus_engine: Any,
        submissions: List[Any],
        agents: Optional[List[Any]],
    ) -> tuple[Optional[Any], str]:
        """Recompute consensus from the same inputs via the engine itself.

        ``compute_consensus`` appends to the engine's in-memory history; that
        side effect is undone so replay leaves no trace in swarm stats.
        """
        history = getattr(consensus_engine, "_history", None)
        try:
            replay = consensus_engine.compute_consensus(
                submissions=list(submissions), agents=agents
            )
        except Exception as exc:  # noqa: BLE001 — the gate owns failure framing
            replay = None
            replay_error = f"replay raised {type(exc).__name__}: {exc}"
        else:
            if replay is None:
                replay_error = "engine could not recompute a consensus"
            elif str(replay.asset_pair).upper() != str(submissions[0].asset_pair).upper():
                replay = None
                replay_error = "replay surfaced a different asset pair"
            else:
                replay_error = ""
        finally:
            if history is not None:
                del consensus_engine._history[len(history):]
        return replay, replay_error

    # --------------------------------------------------------------- session
    def harden(
        self,
        result: Any,
        *,
        assessment: FoundationAssessment,
        max_participants: Optional[int] = None,
    ) -> tuple[DecisionCase, CHPReport]:
        """Run the CHP session and open the case as PROVISIONAL_LOCK.

        Sessions start EXPLORING (the package default); a foundation score
        below the domain floor leaves the case REFRAME_REQUIRED — the caller
        refuses those rather than letting them self-certify.
        """
        pair = str(result.asset_pair).upper()
        price = float(result.consensus_price)
        confidence = float(result.confidence)
        participants = list(result.participating_agents)
        last = self._last_posted.get(pair)

        pair_slug = pair.replace("/", "-").lower()
        case = DecisionCase(
            decision_id=f"oracle-post-{int(result.timestamp * 1000)}-{pair_slug}",
            title=f"Post {pair} consensus price {price:.8f} to the on-chain oracle",
            domain=self.domain,
            created_at=dt.datetime.now(dt.UTC).isoformat(),
            owner="swarmfi-orchestrator",
            high_stakes=True,
            dossier=Dossier(
                core_problem=(
                    f"Post the swarm consensus price for {pair} to the on-chain "
                    "oracle — the post marks perp positions and can trigger vault "
                    "rebalances, so it moves capital"
                ),
                goal_state=[
                    "the on-chain oracle price reflects hardened swarm agreement"
                ],
                current_state=[
                    f"{len(participants)} agent submission(s) buffered for {pair}",
                    f"consensus {price:.8f} at confidence {confidence:.2f}",
                    (
                        f"last posted price for {pair}: {last:.8f}"
                        if last is not None
                        else f"no prior on-chain post for {pair}"
                    ),
                ],
                constraints=[
                    f"foundation floor {self.floor} (blockchain/DeFi)",
                    f"max std/price fraction {self.max_std_fraction}",
                    f"max move vs last posted price {self.max_price_move}",
                    "SWARMFI_CHP_REQUIRE_HUMAN_LOCK defaults ON",
                ],
                scope=[
                    f"asset_pair:{pair}",
                    "decision_class:oracle_price_post",
                ],
            ),
        )
        disclosure = FoundationDisclosure(
            weakest_assumptions=[
                "each buffered submission faithfully reflects its agent's data source",
                (
                    "the reputation-weighted median with outlier exclusion is the "
                    "right aggregation for perp pricing"
                ),
            ],
            invalidation_conditions=[
                (
                    "deterministic replay of the consensus from the buffered "
                    "submissions diverges from the submitted price"
                ),
                "the move vs the last posted price exceeds the configured bound",
            ],
            key_vulnerability=(
                "the oracle post has no external golden price — parity evidence is "
                "replay parity against the swarm's own buffered submissions"
            ),
        )
        attack = FoundationAttack(
            attack_summary="; ".join(assessment.findings),
            foundation_score=assessment.score,
            vulnerability_strike=(
                "without replay parity the post rests only on structural "
                "guardrails, not on a recomputable consensus"
            ),
            assumption_attacks=[
                "replay: recompute the consensus from the buffered submissions and compare",
                "state assertion: bound the move against the last posted price",
                "dispersion bound: std/price must stay under the configured cap",
            ],
        )

        binary = resolve_gate_bin()
        if binary is not None:
            return case, self._run_session_native(
                binary, case=case, disclosure=disclosure, attack=attack
            )
        # Fallback (no native binary): the Python package runs the session
        # in-process. Fresh orchestrator per case: the protocol registry is
        # in-memory state we do not rely on — the decision ledger is the
        # durable record.
        report = CHPOrchestrator().run_initial_session(
            case=case, foundation_disclosure=disclosure, foundation_attack=attack
        )
        return case, report

    @staticmethod
    def _run_session_native(
        binary: str,
        *,
        case: DecisionCase,
        disclosure: FoundationDisclosure,
        attack: FoundationAttack,
    ) -> CHPReport:
        """The session's reachable effects, decided by the chp-gate binary.

        run_initial_session's remaining branches are unreachable for a
        gate-constructed case: the registry is fresh (context PROCEED),
        model parity defaults to MINOR, and the session-internal R0
        recomputation passes whenever the loop's own R0 gate passed (the
        case carries scope, current state, and high stakes). What downstream
        code observes is the devil's-advocate validation, the foundation
        verdict, and the foundation_score/status assignment — driven here by
        the binary's evaluate_devils_advocate and foundation_verdict. The
        chp package's dataclasses remain the shared value shapes; every
        Profile A decision comes from the binary. The binary's method
        vocabulary does not expose disclosure/attack pair validation, so
        the native path relies on those texts being gate-constructed
        constants.
        """
        devil = native_gate_call(
            binary,
            "evaluate_devils_advocate",
            {
                # build_phase0_devils_advocate's field mapping, evaluated here
                # so the binary validates exactly what the Python round holds.
                "why_direction_wrong": attack.vulnerability_strike,
                "what_not_seeing": (
                    disclosure.invalidation_conditions[0]
                    if disclosure.invalidation_conditions
                    else "The invalidation path is under-specified."
                ),
                "false_consensus_risk": (
                    "Foundation agreement may reflect shared optimism unless "
                    "the disclosed weak assumptions survive attack."
                ),
                "structural_vulnerabilities": [
                    v
                    for v in (
                        attack.vulnerability_strike,
                        *attack.assumption_attacks[:2],
                    )
                    if v
                ][:3],
            },
        )
        if devil["errors"]:
            raise ValueError("; ".join(devil["errors"]))
        foundation = native_gate_call(
            binary,
            "foundation_verdict",
            {"score": attack.foundation_score, "domain": case.domain},
        )
        case.foundation_score = attack.foundation_score
        case.status = (
            SessionStatus.REFRAME_REQUIRED
            if foundation["verdict"] == Verdict.REFRAME.value
            else SessionStatus.EXPLORING
        )
        return CHPReport(
            case=case,
            foundation_disclosure=disclosure,
            foundation_attack=attack,
            r0_verdict=Verdict.PASS,
            foundation_verdict=Verdict(foundation["verdict"]),
            initial_packet="",
        )

    # ------------------------------------------------------------- human lock
    def lock(self, case: DecisionCase, confirmed_by: str) -> SessionStatus:
        """Third-party confirmation: PROVISIONAL_LOCK -> LOCKED.

        The binary's method vocabulary has no third-party-lock method — the
        lock is a case-state transition — so its reference semantics
        (status guard, validation log, CONFIRM -> LOCKED) run locally on the
        native path; the Python package applies them on the fallback.
        """
        validation = ThirdPartyValidation(
            validator=confirmed_by,
            item=case.decision_id,
            challenge=(
                "Confirm the consensus price post is solvable from the "
                "portfolio state and cleared the DeFi foundation floor"
            ),
            result=ValidationResult.CONFIRM,
            rationale="Named confirmer approved the oracle post via the swarm gate",
        )
        if resolve_gate_bin() is None:
            return apply_third_party_validation(case, validation)
        if case.status != SessionStatus.PROVISIONAL_LOCK:
            raise ValueError("third-party validation requires PROVISIONAL_LOCK status")
        case.third_party_log.append(validation)
        case.status = SessionStatus.LOCKED
        if validation.item not in case.locked_decisions:
            case.locked_decisions.append(validation.item)
        return case.status

    # ------------------------------------------------------------------ gate
    def allow_submission(
        self,
        result: Any,
        *,
        submissions: List[Any],
        agents: Optional[List[Any]] = None,
        consensus_engine: Any = None,
        max_participants: Optional[int] = None,
    ) -> GateOutcome:
        """Full gate run for one would-be oracle post. Fails closed."""
        pair = str(result.asset_pair).upper()

        evaluation = self.evaluate_r0(result, max_participants=max_participants)
        if evaluation.verdict != Verdict.PASS:
            failed = [
                name for name, res in evaluation.results.items() if res != "PASS"
            ]
            reason = "CHP R0 gate: the oracle post failed " + ", ".join(sorted(failed))
            return self._refuse(
                kind="r0_refusal",
                reason=reason,
                pair=pair,
                r0_results=dict(evaluation.results),
            )

        assessment = self.assess_foundation(
            result,
            submissions=submissions,
            agents=agents,
            consensus_engine=consensus_engine,
            max_participants=max_participants,
        )
        if assessment.parity is not None and not assessment.parity["within_tolerance"]:
            reason = (
                "CHP foundation: "
                + assessment.findings[-1]
                + " — a consensus contradicting its own replay must not be posted"
            )
            return self._refuse(
                kind="parity_mismatch",
                reason=reason,
                pair=pair,
                r0_results=dict(evaluation.results),
                assessment=assessment,
            )

        case, report = self.harden(
            result, assessment=assessment, max_participants=max_participants
        )
        if (
            report.foundation_verdict == Verdict.REFRAME
            or case.status == SessionStatus.REFRAME_REQUIRED
        ):
            reason = (
                f"CHP foundation: score {assessment.score} is below the "
                f"{self.domain} floor {self.floor} — the case is REFRAME_REQUIRED"
            )
            return self._refuse(
                kind="floor_refusal",
                reason=reason,
                pair=pair,
                r0_results=dict(evaluation.results),
                assessment=assessment,
                case=case,
                report=report,
            )

        # Explicit human-lock stage: PROVISIONAL_LOCK before validation, a
        # named confirmed_by before LOCKED.
        case.status = SessionStatus.PROVISIONAL_LOCK

        session_status = SessionStatus.PROVISIONAL_LOCK
        locked = False
        if self.confirmed_by:
            session_status = self.lock(case, self.confirmed_by)
            locked = session_status == SessionStatus.LOCKED
        if self.require_human_lock and not locked:
            reason = (
                "CHP human lock: SWARMFI_CHP_REQUIRE_HUMAN_LOCK is on and no "
                "confirmed_by is configured — the oracle post waits for a "
                "named human confirmation (SWARMFI_CHP_CONFIRMED_BY)"
            )
            self._record_decision(
                case=case,
                report=report,
                assessment=assessment,
                kind="human_lock_required",
                reason=reason,
                confirmed_by=None,
            )
            return GateOutcome(
                allowed=False,
                decision_id=case.decision_id,
                reason=reason,
                r0_results=dict(evaluation.results),
                foundation_score=assessment.score,
                session_status=session_status.value,
                findings=assessment.findings,
            )

        reason = (
            f"CHP gate passed: R0 PASS, foundation {assessment.score}/{self.floor}, "
            f"decision {session_status.value}"
        )
        self._record_decision(
            case=case,
            report=report,
            assessment=assessment,
            kind="oracle_post",
            reason=reason,
            confirmed_by=self.confirmed_by if locked else None,
        )
        return GateOutcome(
            allowed=True,
            decision_id=case.decision_id,
            reason=reason,
            r0_results=dict(evaluation.results),
            foundation_score=assessment.score,
            session_status=session_status.value,
            findings=assessment.findings,
        )

    # ---------------------------------------------------------------- record
    def _refuse(
        self,
        *,
        kind: str,
        reason: str,
        pair: str,
        r0_results: Dict[str, str],
        assessment: Optional[FoundationAssessment] = None,
        case: Optional[DecisionCase] = None,
        report: Optional[CHPReport] = None,
    ) -> GateOutcome:
        """Seal a refusal into the ledger and refuse the submission."""
        if case is not None and report is not None:
            self._record_decision(
                case=case,
                report=report,
                assessment=assessment,
                kind=kind,
                reason=reason,
                confirmed_by=None,
            )
            decision_id = case.decision_id
            session_status = case.status.value
            score = assessment.score if assessment else None
        else:
            decision_id = f"refusal-{uuid.uuid4().hex[:12]}"
            session_status = SessionStatus.HALT.value
            score = assessment.score if assessment else None
            body = json.dumps(
                {
                    "asset_pair": pair,
                    "decision_id": decision_id,
                    "kind": kind,
                    "reason": reason,
                    "r0_results": r0_results,
                },
                sort_keys=True,
                ensure_ascii=False,
            )
            self.ledger.append(
                {
                    "decision_id": decision_id,
                    "created_at": dt.datetime.now(dt.UTC).isoformat(),
                    "kind": kind,
                    "asset_pair": pair,
                    "session_status": session_status,
                    "r0_results": r0_results,
                    "reason": reason,
                    "body": body,
                    "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                    "envelope": seal_payload_envelope(body, _ENVELOPE_ROUTE),
                }
            )
        logger.error("CHP gate refusal (%s): %s", kind, reason)
        return GateOutcome(
            allowed=False,
            decision_id=decision_id,
            reason=reason,
            r0_results=r0_results,
            foundation_score=score,
            session_status=session_status,
            findings=list(assessment.findings) if assessment else [],
        )

    def _record_decision(
        self,
        *,
        case: DecisionCase,
        report: CHPReport,
        assessment: Optional[FoundationAssessment],
        kind: str,
        reason: str,
        confirmed_by: Optional[str],
    ) -> Dict[str, Any]:
        """Seal the decision into a CHP payload envelope and append the ledger."""
        body = json.dumps(
            {
                "asset_pair": getattr(case, "_asset_pair", None),
                "adversary_findings": assessment.findings if assessment else [],
                "confirmed_by": confirmed_by,
                "decision_id": case.decision_id,
                "domain": case.domain,
                "foundation_score": case.foundation_score,
                "locked_decisions": list(case.locked_decisions),
                "parity": assessment.parity if assessment else None,
                "r0_verdict": report.r0_verdict.value,
                "foundation_verdict": report.foundation_verdict.value,
                "title": case.title,
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        entry = {
            "decision_id": case.decision_id,
            "created_at": case.created_at,
            "kind": kind,
            "domain": case.domain,
            "session_status": case.status.value,
            "r0_verdict": report.r0_verdict.value,
            "foundation_verdict": report.foundation_verdict.value,
            "foundation_score": case.foundation_score,
            "confirmed_by": confirmed_by,
            "reason": reason,
            "body": body,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "envelope": seal_payload_envelope(body, _ENVELOPE_ROUTE),
        }
        self.ledger.append(entry)
        return entry


# --------------------------------------------------------------------------
# Subprocess bridge: `python -m shared.chp_gate` (run from the agents/ dir).
# Reads one JSON request on stdin, writes one JSON verdict on stdout — the
# small Python gate script a non-Python (e.g. Rust) swarm process can exec.
# Its external contract is frozen (tests pin it); internally the gate now
# resolves the native chp-gate binary first (CHP_GATE_BIN, then PATH) and
# the in-process Python package is the documented fallback.
# Request: {"consensus": {...ConsensusResult fields...}, "submissions": [...],
#           "agents": [...optional...], "last_posted_price": number|null,
#           "max_participants": int|null}
# Response: GateOutcome.to_dict()
# --------------------------------------------------------------------------
def _bridge_main() -> int:
    import sys

    raw = sys.stdin.read()
    try:
        request = json.loads(raw)
        consensus_data = request["consensus"]
        submission_data = request.get("submissions") or []
        agents_data = request.get("agents") or []
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        json.dump({"error": f"bad request: {exc}"}, sys.stderr)
        return 2

    consensus = SimpleNamespace(
        asset_pair=consensus_data["asset_pair"],
        consensus_price=consensus_data["consensus_price"],
        participating_agents=consensus_data.get("participating_agents", []),
        confidence=consensus_data.get("confidence", 0.0),
        timestamp=consensus_data.get("timestamp", 0.0),
        std_deviation=consensus_data.get("std_deviation", 0.0),
        num_outliers=consensus_data.get("num_outliers", 0),
        weighted_median=consensus_data.get("weighted_median", 0.0),
    )
    submissions = [
        SimpleNamespace(
            asset_pair=sub["asset_pair"],
            price=sub["price"],
            confidence=sub.get("confidence", 0.0),
            source=sub.get("source", ""),
            agent_address=sub.get("agent_address", ""),
            metadata=sub.get("metadata") or {},
        )
        for sub in submission_data
    ]
    agents = [
        SimpleNamespace(
            name=agent.get("name", ""),
            agent_type=agent.get("agent_type", "PRICE"),
            address=agent.get("address", ""),
            reputation=agent.get("reputation", 0.5),
        )
        for agent in agents_data
    ]

    gate = SwarmfiChpGate.from_env()
    last_price = request.get("last_posted_price")
    if last_price is not None and "asset_pair" in consensus_data:
        gate.note_posted_price(str(consensus_data["asset_pair"]), float(last_price))

    # Replay parity needs the same engine the live path uses.
    try:
        from shared.consensus import SwarmConsensus

        engine = SwarmConsensus()
    except Exception as exc:  # noqa: BLE001 — reported, never swallowed
        engine = None
        logger.warning("replay engine unavailable in bridge: %s", exc)

    outcome = gate.allow_submission(
        consensus,
        submissions=submissions,
        agents=agents if agents else None,
        consensus_engine=engine,
        max_participants=request.get("max_participants"),
    )
    json.dump(outcome.to_dict(), sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(_bridge_main())
