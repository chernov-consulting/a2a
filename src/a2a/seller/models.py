"""Seller-side models: funnel variants and seller config."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FunnelVariant(StrEnum):
    """Three seller funnel variants for the v0.1 experiment.

    These differ in how the seller presents the product to the buyer agent.
    This is the core research question on the seller side:
    'What does onboarding look like when your audience is an agent?'
    """

    API_CONTRACT = "api_contract"
    """Pure machine-readable JSON schema — no marketing copy."""

    RICH_SCHEMA = "rich_schema"
    """JSON schema + feature narrative + structured trust signals + competitive positioning."""

    PERSUASION_PAGE = "persuasion_page"
    """Human-style marketing copy with emotional triggers — tests if agents respond to it."""


class SellerConfig(BaseModel):
    """Configuration for the selling agent."""

    funnel_variant: FunnelVariant = Field(default=FunnelVariant.RICH_SCHEMA)
    max_discount_pct: float = Field(default=15.0, ge=0.0, le=50.0, description="Max discount % from list price")
    allow_custom_tier: bool = Field(default=False)
    emphasise_trust: bool = Field(default=True)
    rationale_required: bool = Field(default=True, description="Force a structured rationale after each negotiation step")


class SellerDecision(BaseModel):
    """The seller agent's response at a negotiation step."""

    action: str  # present | counter_offer | accept | reject | escalate
    message: str
    offered_price_usd: float | None = Field(default=None)
    offered_tier: str | None = Field(default=None)
    rationale: dict[str, object] = Field(default_factory=dict)
