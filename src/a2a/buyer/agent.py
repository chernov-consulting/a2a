"""Buying agent: plan, evaluate, negotiate, decide, and explain."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

from a2a.buyer.models import BuyerDecision, Mandate
from a2a.llm import LLMClient, LLMRecord, Message, get_client

if TYPE_CHECKING:
    from a2a.catalog.models import CatalogEntry

log = structlog.get_logger(__name__)

_RATIONALE_SCHEMA = """
{
  "mandate_alignment": "brief assessment of how well the offer meets the mandate",
  "key_factors": ["list of up to 5 decisive factors"],
  "counterfactual": "what would have changed the outcome",
  "price_assessment": "fair | overpriced | underpriced | unknown",
  "feature_gaps": ["required features not present"],
  "trust_assessment": "brief assessment of seller trust signals"
}
""".strip()


class BuyingAgent:
    """Autonomous buying agent.

    Evaluates a seller's offer against a mandate and negotiates (up to max_turns).
    Emits a structured decision and rationale for every outcome.
    """

    def __init__(
        self,
        mandate: Mandate,
        llm_client: LLMClient | None = None,
        model: str | None = None,
    ) -> None:
        self.mandate = mandate
        self._llm = llm_client or get_client()
        self._model = model
        self._records: list[LLMRecord] = []

    @property
    def llm_records(self) -> list[LLMRecord]:
        return list(self._records)

    def evaluate_and_negotiate(
        self,
        catalog: CatalogEntry,
        seller_messages: list[dict[str, str]],
        funnel_variant: str,
        max_turns: int | None = None,
    ) -> tuple[BuyerDecision, list[dict[str, str]]]:
        """Evaluate the seller's opening, negotiate, and return a decision.

        Args:
            catalog: The structured product catalog.
            seller_messages: The seller's opening messages (role + content dicts).
            funnel_variant: Which funnel the seller is using.
            max_turns: Override the mandate's max_negotiation_turns.

        Returns:
            (BuyerDecision, conversation_history)
        """
        turns = max_turns or self.mandate.max_negotiation_turns
        product_brief = catalog.as_agent_brief(funnel_variant)

        conversation: list[Message] = [
            Message("system", self.mandate.as_system_prompt()),
            Message(
                "user",
                f"You are evaluating the following product offering. "
                f"Assess it against your mandate, then respond to the seller.\n\n"
                f"Product information:\n{product_brief}\n\n"
                f"Seller's opening message:\n"
                + "\n".join(m["content"] for m in seller_messages),
            ),
        ]

        turn = 0
        history: list[dict[str, str]] = list(seller_messages)

        while turn < turns:
            record = self._llm.complete(
                messages=conversation,
                model=self._model,
                metadata={"step": f"buyer_turn_{turn + 1}", "archetype": self.mandate.archetype},
            )
            self._records.append(record)

            buyer_response = record.response
            conversation.append(Message("assistant", buyer_response))
            history.append({"role": "buyer", "content": buyer_response})

            # Check for terminal signals in the response
            lower = buyer_response.lower()
            if any(signal in lower for signal in ["i accept", "we accept", "deal", "agreed", "i'll take", "i will take"]):
                decision = self._make_decision("buy", buyer_response, catalog, turn + 1)
                return decision, history

            if any(signal in lower for signal in ["walk away", "no deal", "decline", "not interested", "pass on this"]):
                decision = self._make_decision("walk", buyer_response, catalog, turn + 1)
                return decision, history

            if any(signal in lower for signal in ["escalate", "need approval", "check with my", "refer to"]):
                decision = self._make_decision("escalate_to_human", buyer_response, catalog, turn + 1)
                return decision, history

            turn += 1
            if turn < turns:
                # Prompt the buyer to continue or close
                conversation.append(
                    Message(
                        "user",
                        "Continue the negotiation or make your final decision. "
                        "If you are making a final decision, clearly state 'I accept', "
                        "'I walk away', or 'I escalate to my principal'.",
                    )
                )

        # Timed out
        decision = self._make_decision("timeout", "Maximum negotiation turns reached.", catalog, turns)
        return decision, history

    def _make_decision(
        self,
        outcome: str,
        last_response: str,
        catalog: CatalogEntry,
        turns_used: int,
    ) -> BuyerDecision:
        rationale = self._extract_rationale(last_response, catalog)
        price = self._extract_price(last_response, catalog) if outcome == "buy" else None
        tier = self._extract_tier(last_response, catalog) if outcome == "buy" else None

        log.info(
            "buyer_decision",
            outcome=outcome,
            archetype=self.mandate.archetype,
            turns_used=turns_used,
            price=price,
        )
        return BuyerDecision(
            outcome=outcome,
            reason=last_response[:500],
            agreed_price_usd=price,
            agreed_tier=tier,
            rationale=rationale,
            negotiation_turns_used=turns_used,
        )

    def _extract_rationale(self, response: str, catalog: CatalogEntry) -> dict[str, Any]:
        """Ask the LLM to produce a structured rationale."""
        record = self._llm.complete(
            messages=[
                Message(
                    "system",
                    f"Extract a structured JSON rationale from the buyer's response. "
                    f"Match this schema:\n{_RATIONALE_SCHEMA}\n\n"
                    f"Return only valid JSON.",
                ),
                Message(
                    "user",
                    f"Buyer's response: {response[:1000]}\n\n"
                    f"Product: {catalog.product.name}",
                ),
            ],
            metadata={"step": "buyer_rationale"},
        )
        self._records.append(record)
        try:
            return json.loads(record.response)
        except json.JSONDecodeError:
            return {"raw": record.response[:500]}

    def _extract_price(self, response: str, catalog: CatalogEntry) -> float | None:
        import re

        patterns = [r"\$(\d+(?:\.\d+)?)", r"(\d+(?:\.\d+)?)\s*(?:USD|dollars?)"]
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return float(match.group(1))
        if catalog.product.pricing_tiers:
            cheapest = min(
                (t for t in catalog.product.pricing_tiers if t.price_usd is not None),
                key=lambda t: t.price_usd or float("inf"),
                default=None,
            )
            if cheapest:
                return cheapest.price_usd
        return None

    def _extract_tier(self, response: str, catalog: CatalogEntry) -> str | None:
        lower = response.lower()
        for tier in catalog.product.pricing_tiers:
            if tier.name.lower() in lower:
                return tier.name
        return None
