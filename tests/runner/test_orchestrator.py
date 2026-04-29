"""Tests for the experiment orchestrator (mocked LLM calls)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from a2a.buyer.models import BuyerArchetype
from a2a.llm import LLMRecord
from a2a.runner.models import ExperimentConfig
from a2a.runner.orchestrator import Orchestrator
from a2a.seller.models import FunnelVariant


def _mock_record(response: str = '{"outcome": "buy", "key_factors": ["price"]}') -> LLMRecord:
    return LLMRecord(
        model="mock/test",
        prompt_hash="abc12345",
        tokens_in=50,
        tokens_out=30,
        cost_usd=0.0001,
        latency_ms=100.0,
        response=response,
    )


BUY_RESPONSE = (
    "I accept this offer. The Pro tier at $299/month meets all our requirements. "
    "[SELLER_RATIONALE] {\"action\": \"accept\", \"offered_price_usd\": 299.0, "
    "\"offered_tier\": \"Pro\", \"reasoning\": \"meets mandate\"}"
)

WALK_RESPONSE = "I walk away from this offer. The price exceeds our budget."


@pytest.fixture
def minimal_config() -> ExperimentConfig:
    return ExperimentConfig(
        slug="test-minimal",
        product_type="saas_subscription",
        seed=42,
        dyads_per_cell=2,
        max_negotiation_turns=2,
        buyer_archetypes=[BuyerArchetype.PRICE_OPTIMISER],
        funnel_variants=[FunnelVariant.API_CONTRACT],
        buyer_model="mock/buyer",
        seller_model="mock/seller",
        judge_model="mock/judge",
    )


def test_orchestrator_runs_correct_number_of_dyads(
    tmp_path: Path, minimal_config: ExperimentConfig
) -> None:
    with patch("a2a.runner.orchestrator.get_client") as mock_get_client, \
         patch("a2a.runner.orchestrator.JudgeLLM") as mock_judge_cls:

        mock_client = MagicMock()
        mock_client.complete.side_effect = [
            _mock_record(BUY_RESPONSE),  # seller open
            _mock_record(BUY_RESPONSE),  # buyer eval (accept)
            _mock_record('{"mandate_alignment": "good"}'),  # buyer rationale
            _mock_record('{"buyer": {"total": 8}, "seller": {"total": 7}}'),  # judge
        ] * 10  # enough for dyads_per_cell=2

        mock_get_client.return_value = mock_client

        mock_judge = MagicMock()
        mock_judge.score.return_value = ({"buyer": {"total": 8}}, _mock_record("{}"))
        mock_judge_cls.return_value = mock_judge

        orch = Orchestrator(minimal_config, tmp_path)
        result = orch.run()

    assert result.total_dyads == 2
    assert len(result.dyad_records) == 2
    ledger_lines = (tmp_path / "results.jsonl").read_text().strip().split("\n")
    assert len(ledger_lines) == 2


def test_orchestrator_writes_summary(
    tmp_path: Path, minimal_config: ExperimentConfig
) -> None:
    with patch("a2a.runner.orchestrator.get_client") as mock_get_client, \
         patch("a2a.runner.orchestrator.JudgeLLM") as mock_judge_cls:

        mock_client = MagicMock()
        mock_client.complete.return_value = _mock_record(BUY_RESPONSE)
        mock_get_client.return_value = mock_client

        mock_judge = MagicMock()
        mock_judge.score.return_value = ({}, _mock_record("{}"))
        mock_judge_cls.return_value = mock_judge

        orch = Orchestrator(minimal_config, tmp_path)
        orch.run()

    summary_path = tmp_path / "summary.json"
    assert summary_path.exists()
    summary = json.loads(summary_path.read_text())
    assert summary["slug"] == "test-minimal"
    assert "buy_rate" in summary
    assert "total_cost_usd" in summary
