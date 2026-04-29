"""Selling agent: funnel, pricing, negotiation, and rationale."""

from __future__ import annotations

import json
from typing import Any

import structlog

from a2a.catalog.models import CatalogEntry
from a2a.llm import LLMClient, LLMRecord, Message, get_client
from a2a.seller.models import FunnelVariant, SellerConfig, SellerDecision

log = structlog.get_logger(__name__)

_SELLER_SYSTEM = """
You are an autonomous selling agent for {product_name}.

Your funnel approach: {funnel_variant}

Your objective: close the deal at the best price for your company.
- Maximum discount from list price: {max_discount_pct}%
- You may offer custom pricing if it brings the deal to close.
- Always state your reasoning. Cite specific product capabilities.
- After each response, append a JSON block tagged [SELLER_RATIONALE] with this structure:
  {{
    "action": "present | counter_offer | accept | reject | escalate",
    "offered_price_usd": <number or null>,
    "offered_tier": "<tier name or null>",
    "reasoning": "<why this response>"
  }}

Product context will be provided in the first user message.
""".strip()

_SELLER_RATIONALE_SCHEMA = """
{
  "action": "present | counter_offer | accept | reject | escalate",
  "offered_price_usd": number or null,
  "offered_tier": "string or null",
  "reasoning": "string — why this action and price",
  "buyer_signal": "what the buyer's last message indicated about their intent"
}
""".strip()


class SellingAgent:
    """Autonomous selling agent.

    Opens with the configured funnel variant, then negotiates within discount bounds.
    Emits a structured rationale at each step for the judge LLM to evaluate.
    """

    def __init__(
        self,
        catalog: CatalogEntry,
        seller_config: SellerConfig | None = None,
        llm_client: LLMClient | None = None,
        model: str | None = None,
    ) -> None:
        self.catalog = catalog
        self.config = seller_config or SellerConfig()
        self._llm = llm_client or get_client()
        self._model = model
        self._records: list[LLMRecord] = []

    @property
    def llm_records(self) -> list[LLMRecord]:
        return list(self._records)

    def open(self) -> list[dict[str, str]]:
        """Generate the seller's opening message using the configured funnel variant."""
        product_brief = self.catalog.as_agent_brief(self.config.funnel_variant.value)

        system = _SELLER_SYSTEM.format(
            product_name=self.catalog.product.name,
            funnel_variant=self.config.funnel_variant.value,
            max_discount_pct=self.config.max_discount_pct,
        )

        opening_prompt = (
            f"Generate an opening message to present this product to a potential buyer. "
            f"Use the {self.config.funnel_variant.value} funnel approach.\n\n"
            f"Product information:\n{product_brief}"
        )

        record = self._llm.complete(
            messages=[
                Message("system", system),
                Message("user", opening_prompt),
            ],
            model=self._model,
            metadata={"step": "seller_open", "funnel": self.config.funnel_variant.value},
        )
        self._records.append(record)

        return [{"role": "seller", "content": record.response}]

    def respond(
        self,
        buyer_message: str,
        conversation_history: list[dict[str, str]],
        turn: int,
    ) -> SellerDecision:
        """Respond to the buyer's message."""
        system = _SELLER_SYSTEM.format(
            product_name=self.catalog.product.name,
            funnel_variant=self.config.funnel_variant.value,
            max_discount_pct=self.config.max_discount_pct,
        )

        history_text = "\n".join(
            f"[{m['role'].upper()}]: {m['content']}" for m in conversation_history[-6:]
        )

        record = self._llm.complete(
            messages=[
                Message("system", system),
                Message(
                    "user",
                    f"Conversation so far:\n{history_text}\n\n"
                    f"Buyer's latest message:\n{buyer_message}\n\n"
                    f"This is turn {turn}. Respond as the seller. "
                    f"Append your [SELLER_RATIONALE] JSON block.",
                ),
            ],
            model=self._model,
            metadata={"step": f"seller_turn_{turn}", "funnel": self.config.funnel_variant.value},
        )
        self._records.append(record)

        message, rationale = self._parse_response(record.response)
        log.info(
            "seller_response",
            turn=turn,
            action=rationale.get("action", "unknown"),
            price=rationale.get("offered_price_usd"),
        )

        return SellerDecision(
            action=rationale.get("action", "present"),
            message=message,
            offered_price_usd=rationale.get("offered_price_usd"),
            offered_tier=rationale.get("offered_tier"),
            rationale=rationale,
        )

    def _parse_response(self, raw: str) -> tuple[str, dict[str, Any]]:
        """Split the raw response into message text and JSON rationale."""
        if "[SELLER_RATIONALE]" in raw:
            parts = raw.split("[SELLER_RATIONALE]", 1)
            message = parts[0].strip()
            try:
                rationale: dict[str, Any] = json.loads(parts[1].strip())
                return message, rationale
            except json.JSONDecodeError:
                pass

        # Fallback: extract the last JSON block
        import re

        json_blocks = re.findall(r"\{[^{}]+\}", raw, re.DOTALL)
        if json_blocks:
            try:
                rationale = json.loads(json_blocks[-1])
                message = raw[: raw.rfind("{")].strip()
                return message, rationale
            except json.JSONDecodeError:
                pass

        return raw.strip(), {"action": "present", "reasoning": "no rationale block found"}
