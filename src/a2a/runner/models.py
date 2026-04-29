"""Runner data models: experiment config and per-dyad ledger records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from a2a.buyer.models import BuyerArchetype, MandateContext
from a2a.seller.models import FunnelVariant


class ExperimentConfig(BaseModel):
    """Complete specification for one experiment run."""

    slug: str = Field(description="URL-safe experiment identifier, e.g. '2026-05-saas-subscription'")
    product_type: str = Field(description="saas_subscription | physical_good")
    description: str = Field(default="")
    seed: int = Field(default=42)
    dyads_per_cell: int = Field(default=30, ge=1)
    max_negotiation_turns: int = Field(default=3, ge=1)
    buyer_model: str = Field(default="openai/gpt-4o")
    seller_model: str = Field(default="anthropic/claude-3-5-sonnet-20241022")
    judge_model: str = Field(default="openai/gpt-4o-mini")
    buyer_archetypes: list[BuyerArchetype] = Field(
        default_factory=lambda: list(BuyerArchetype)
    )
    funnel_variants: list[FunnelVariant] = Field(
        default_factory=lambda: list(FunnelVariant)
    )
    mandate_contexts: list[MandateContext] = Field(
        default_factory=lambda: [MandateContext.TERSE_JSON]
    )
    autonomy: str = Field(default="full_auto")


class FunnelStep(BaseModel):
    """One step in the conversion funnel."""

    name: str  # discovery | evaluation | negotiation_turn_N | checkout | post_purchase
    reached: bool = False
    latency_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0


class DyadRecord(BaseModel):
    """Complete record for one buyer-seller dyad (one simulated transaction)."""

    dyad_id: str
    experiment_slug: str
    buyer_archetype: str
    funnel_variant: str
    mandate_context: str
    buyer_model: str
    seller_model: str
    seed: int
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

    # Outcome
    outcome: str  # buy | walk | escalate_to_human | timeout
    reason: str = ""
    agreed_price_usd: float | None = None
    agreed_tier: str | None = None
    list_price_usd: float | None = None
    discount_pct: float | None = None

    # Negotiation
    negotiation_turns_used: int = 0

    # Funnel steps
    funnel_steps: list[FunnelStep] = Field(default_factory=list)
    conversion_rate: float | None = None  # proportion of funnel steps reached

    # Observability
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0

    # Rationales
    buyer_rationale: dict[str, Any] = Field(default_factory=dict)
    seller_rationale: dict[str, Any] = Field(default_factory=dict)
    judge_score: dict[str, Any] = Field(default_factory=dict)

    # Full conversation (trimmed for the ledger)
    conversation_preview: list[dict[str, str]] = Field(default_factory=list)

    def as_ledger_line(self) -> dict[str, Any]:
        """Serialise for the JSONL ledger."""
        return self.model_dump(mode="json")


class ExperimentResult(BaseModel):
    """Aggregate results for a complete experiment."""

    config: ExperimentConfig
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    total_dyads: int = 0
    dyad_records: list[DyadRecord] = Field(default_factory=list)

    @property
    def buy_rate(self) -> float:
        if not self.dyad_records:
            return 0.0
        return sum(1 for d in self.dyad_records if d.outcome == "buy") / len(self.dyad_records)

    @property
    def total_cost_usd(self) -> float:
        return sum(d.total_cost_usd for d in self.dyad_records)

    @property
    def avg_latency_ms(self) -> float:
        if not self.dyad_records:
            return 0.0
        return sum(d.total_latency_ms for d in self.dyad_records) / len(self.dyad_records)
