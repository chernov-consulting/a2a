"""Tests for the JSONL ledger."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from a2a.runner.ledger import Ledger
from a2a.runner.models import DyadRecord, FunnelStep

if TYPE_CHECKING:
    from pathlib import Path


def _make_dyad(dyad_id: str = "abc12345", outcome: str = "buy") -> DyadRecord:
    return DyadRecord(
        dyad_id=dyad_id,
        experiment_slug="test-experiment",
        buyer_archetype="price_optimiser",
        funnel_variant="api_contract",
        mandate_context="terse_json",
        buyer_model="openai/gpt-4o",
        seller_model="anthropic/claude-3-5-sonnet",
        seed=42,
        outcome=outcome,
        reason="price within budget",
        agreed_price_usd=299.0,
        total_tokens_in=500,
        total_tokens_out=200,
        total_cost_usd=0.0012,
        total_latency_ms=3500.0,
        funnel_steps=[
            FunnelStep(name="discovery", reached=True),
            FunnelStep(name="evaluation", reached=True),
            FunnelStep(name="checkout", reached=True),
        ],
        conversion_rate=1.0,
        negotiation_turns_used=1,
    )


def test_ledger_append_and_read(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "test.jsonl")
    dyad = _make_dyad()
    ledger.append(dyad)

    records = ledger.read_all()
    assert len(records) == 1
    assert records[0]["dyad_id"] == "abc12345"
    assert records[0]["outcome"] == "buy"


def test_ledger_count(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "test.jsonl")
    assert ledger.count() == 0
    for i in range(5):
        ledger.append(_make_dyad(dyad_id=f"id{i}"))
    assert ledger.count() == 5


def test_ledger_multiple_appends_preserve_order(tmp_path: Path) -> None:
    ledger = Ledger(tmp_path / "test.jsonl")
    outcomes = ["buy", "walk", "timeout", "buy", "escalate_to_human"]
    for i, outcome in enumerate(outcomes):
        ledger.append(_make_dyad(dyad_id=f"id{i}", outcome=outcome))

    records = ledger.read_all()
    assert [r["outcome"] for r in records] == outcomes


def test_dyad_record_as_ledger_line() -> None:
    dyad = _make_dyad()
    line = dyad.as_ledger_line()
    assert isinstance(line, dict)
    assert line["dyad_id"] == "abc12345"
    assert line["total_cost_usd"] == 0.0012
    # JSON-serialisable
    json.dumps(line)


def test_ledger_survives_corrupt_line(tmp_path: Path) -> None:
    path = tmp_path / "test.jsonl"
    path.write_text('{"valid": true}\nnot_json\n{"also_valid": true}\n')
    ledger = Ledger(path)
    records = ledger.read_all()
    assert len(records) == 2
