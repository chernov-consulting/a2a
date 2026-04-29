"""Pydantic models for product catalog entries."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PricingTier(BaseModel):
    """A single pricing tier."""

    name: str = Field(description="Tier name, e.g. 'Starter', 'Pro', 'Enterprise'")
    price_usd: float | None = Field(default=None, description="Monthly or one-time price in USD; None = 'contact us'")
    billing_period: str = Field(default="monthly", description="monthly | annual | one-time | usage-based")
    features: list[str] = Field(default_factory=list)
    is_negotiable: bool = Field(default=False)
    min_quantity: int | None = Field(default=None)
    max_quantity: int | None = Field(default=None)


class ProductSchema(BaseModel):
    """Machine-readable structured schema — the 'API contract' for agents."""

    name: str
    category: str  # saas | physical | service | subscription
    short_description: str = Field(max_length=280)
    features: list[str] = Field(default_factory=list)
    pricing_tiers: list[PricingTier] = Field(default_factory=list)
    currency: str = Field(default="USD")
    availability: str = Field(default="available", description="available | limited | out_of_stock | region_restricted")
    shipping: str | None = Field(default=None, description="For physical goods: estimated delivery")
    return_policy: str | None = Field(default=None)
    trust_signals: list[str] = Field(default_factory=list, description="Certifications, reviews, guarantees")
    terms_url: str | None = Field(default=None)
    api_endpoint: str | None = Field(default=None, description="Checkout / purchase API if available")
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class CatalogEntry(BaseModel):
    """Full product catalog entry, as ingested from one or more sources."""

    product: ProductSchema
    source_urls: list[str] = Field(default_factory=list)
    ingestion_notes: str = Field(default="")
    raw_text_excerpt: str = Field(default="", description="First 2000 chars of the raw scraped/parsed text")

    def as_agent_brief(self, funnel_variant: str = "api_contract") -> str:
        """Render a seller-facing product brief in the specified funnel variant format.

        funnel_variant:
          api_contract      — machine-readable JSON schema only
          rich_schema       — JSON schema + feature narrative + competitive positioning
          persuasion_page   — marketing copy + psychological triggers + testimonials
        """
        p = self.product
        if funnel_variant == "api_contract":
            import json
            return json.dumps(p.model_dump(exclude={"raw_metadata"}), indent=2)

        if funnel_variant == "rich_schema":
            tiers = "\n".join(
                f"  - {t.name}: ${t.price_usd or 'contact'}/{t.billing_period} "
                f"({'negotiable' if t.is_negotiable else 'fixed'}) — {', '.join(t.features[:3])}"
                for t in p.pricing_tiers
            )
            return (
                f"# {p.name}\n\n"
                f"**Category:** {p.category} | **Availability:** {p.availability}\n\n"
                f"{p.short_description}\n\n"
                f"## Features\n" + "\n".join(f"- {f}" for f in p.features) + "\n\n"
                f"## Pricing\n{tiers}\n\n"
                f"**Trust signals:** {', '.join(p.trust_signals)}\n"
            )

        # persuasion_page — human-style marketing copy
        best_tier = min((t for t in p.pricing_tiers if t.price_usd), key=lambda t: t.price_usd or float("inf"), default=None)
        price_anchor = f"starting at ${best_tier.price_usd}/{best_tier.billing_period}" if best_tier else "custom pricing"
        return (
            f"# {p.name} — Transform Your Business\n\n"
            f"**{p.short_description}**\n\n"
            f"Join thousands of satisfied customers who have already made the switch. {price_anchor}.\n\n"
            f"✓ {' ✓ '.join(p.features[:5])}\n\n"
            f"{'  '.join(p.trust_signals)}\n\n"
            f"[Start free trial] [Book a demo] [Compare plans]\n"
        )
