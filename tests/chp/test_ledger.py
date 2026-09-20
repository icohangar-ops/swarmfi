"""Decision ledger round trip + tamper detection (mirrors the erp-ref CHP suite)."""

from __future__ import annotations

import json

import pytest
from conftest import make_result, make_submissions
from shared.consensus import SwarmConsensus


def _sealed_entry(gate, decision_id: str, payload: dict) -> dict:
    """Append a record through the same sealing path the gate uses."""
    import hashlib

    from chp import build_payload_envelope

    body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    entry = {
        "decision_id": decision_id,
        "created_at": "2026-01-01T00:00:00+00:00",
        "body": body,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "envelope": build_payload_envelope(body, route="ORACLE_POST").render(),
    }
    gate.ledger.append(entry)
    return entry


class TestLedgerRoundTrip:
    def test_append_list_get(self, gate):
        _sealed_entry(gate, "decision-1", {"n": 1})
        _sealed_entry(gate, "decision-2", {"n": 2})

        records = gate.ledger.list(10)
        assert [r["decision_id"] for r in records] == ["decision-2", "decision-1"]
        assert all(r["envelope_valid"] for r in records)
        assert all(r["integrity_valid"] for r in records)

        single = gate.ledger.get("decision-1")
        assert single is not None
        assert json.loads(single["body"])["n"] == 1
        assert gate.ledger.get("missing") is None

    def test_envelope_is_structure_only(self, gate):
        """The CHP envelope validates framing, not content — the ledger's own
        digest is what carries integrity."""
        _sealed_entry(gate, "decision-1", {"n": 1})
        record = gate.ledger.get("decision-1")

        # Tamper ONLY the envelope framing characters -> envelope invalid,
        # body digest still fine.
        tampered = record["envelope"].replace("BEGIN_PAYLOAD", "BEGIN_PLAYLOAD", 1)
        from chp import validate_payload_envelope

        assert validate_payload_envelope(tampered) is False
        assert validate_payload_envelope(record["envelope"]) is True


class TestTamperDetection:
    def test_body_tamper_reads_as_integrity_invalid(self, gate, tmp_path):
        _sealed_entry(gate, "decision-1", {"amount": 100})

        # Tamper the sealed body in place: bump the amount without fixing
        # the digest.
        path = gate.ledger.path
        lines = path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        entry["body"] = entry["body"].replace("100", "9999")
        lines[0] = json.dumps(entry, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        record = gate.ledger.get("decision-1")
        assert record is not None
        assert record["integrity_valid"] is False
        assert record["envelope_valid"] is True  # framing untouched

    def test_digest_tamper_reads_as_integrity_invalid(self, gate):
        _sealed_entry(gate, "decision-1", {"amount": 100})
        path = gate.ledger.path
        lines = path.read_text(encoding="utf-8").splitlines()
        entry = json.loads(lines[0])
        entry["body_sha256"] = "0" * 64
        lines[0] = json.dumps(entry, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert gate.ledger.get("decision-1")["integrity_valid"] is False

    def test_corrupt_line_surfaces_on_read(self, gate):
        _sealed_entry(gate, "decision-1", {"amount": 100})
        path = gate.ledger.path
        path.write_text(path.read_text(encoding="utf-8") + "not-json\n", encoding="utf-8")
        # A corrupt trailing line surfaces on read as an exception the caller
        # sees — the ledger never silently drops it.
        with pytest.raises(json.JSONDecodeError):
            gate.ledger.list(10)


class TestGateSealsRealDecisions:
    def test_allowed_and_refused_rounds_land_in_ledger(self, locked_gate, engine):
        allowed = locked_gate.allow_submission(
            make_result(), submissions=make_submissions(), consensus_engine=engine
        )
        assert allowed.allowed is True

        refused = locked_gate.allow_submission(
            make_result(confidence=0.2),
            submissions=make_submissions(confidence=0.2),
            consensus_engine=SwarmConsensus(),
        )
        assert refused.allowed is False

        records = locked_gate.ledger.list(10)
        assert len(records) == 2
        assert records[0]["kind"] == "r0_refusal"
        assert records[1]["kind"] == "oracle_post"
        assert all(r["integrity_valid"] and r["envelope_valid"] for r in records)
