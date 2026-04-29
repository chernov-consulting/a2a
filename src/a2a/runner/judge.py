"""Judge LLM: independently scores buyer and seller rationales."""

from __future__ import annotations

import json
from typing import Any

import structlog

from a2a.llm import LLMClient, LLMRecord, Message, get_client

log = structlog.get_logger(__name__)

_JUDGE_SYSTEM = """
You are an independent evaluator scoring the quality of reasoning in an AI-to-AI commercial transaction.

You will receive:
1. The buyer's stated mandate (requirements, budget, archetype)
2. The seller's product offering
3. The buyer's rationale for their decision
4. The seller's rationale for their response

Score each rationale on these dimensions (0–10 each):
- citation_quality: Does the rationale cite specific product features, prices, or terms?
- mandate_alignment: Does the buyer's rationale align with their stated mandate?
- counterfactual_quality: Is there a meaningful counterfactual (what would have changed the outcome)?
- internal_consistency: Is the reasoning internally consistent, with no contradictions?
- commercial_soundness: Is the decision commercially sensible given the constraints?

Return a JSON object:
{
  "buyer": {
    "citation_quality": <0-10>,
    "mandate_alignment": <0-10>,
    "counterfactual_quality": <0-10>,
    "internal_consistency": <0-10>,
    "commercial_soundness": <0-10>,
    "total": <average>,
    "notes": "brief comment"
  },
  "seller": {
    "citation_quality": <0-10>,
    "mandate_alignment": <0-10>,
    "counterfactual_quality": <0-10>,
    "internal_consistency": <0-10>,
    "commercial_soundness": <0-10>,
    "total": <average>,
    "notes": "brief comment"
  },
  "transaction_quality": "brief overall assessment"
}
""".strip()


class JudgeLLM:
    """Independent LLM judge for rationale quality scoring."""

    def __init__(self, llm_client: LLMClient | None = None, model: str | None = None) -> None:
        self._llm = llm_client or get_client()
        self._model = model

    def score(
        self,
        mandate_summary: str,
        product_name: str,
        outcome: str,
        buyer_rationale: dict[str, Any],
        seller_rationale: dict[str, Any],
    ) -> tuple[dict[str, Any], LLMRecord]:
        """Score buyer and seller rationales. Returns (scores, llm_record)."""
        user_prompt = (
            f"Buyer mandate summary:\n{mandate_summary}\n\n"
            f"Product: {product_name}\n"
            f"Transaction outcome: {outcome}\n\n"
            f"Buyer rationale:\n{json.dumps(buyer_rationale, indent=2)}\n\n"
            f"Seller rationale:\n{json.dumps(seller_rationale, indent=2)}"
        )

        record = self._llm.complete(
            messages=[
                Message("system", _JUDGE_SYSTEM),
                Message("user", user_prompt),
            ],
            model=self._model,
            metadata={"step": "judge_score"},
        )

        try:
            scores: dict[str, Any] = json.loads(record.response)
        except json.JSONDecodeError:
            scores = {"error": "parse_failed", "raw": record.response[:500]}

        log.info(
            "judge_score",
            product=product_name,
            outcome=outcome,
            buyer_total=scores.get("buyer", {}).get("total"),
            seller_total=scores.get("seller", {}).get("total"),
        )
        return scores, record
