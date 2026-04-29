"""UCP — Google Universal Commerce Protocol data models.

Represents the January 2026 launch version of UCP, based on public spec documentation.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UCPPricingSpec(BaseModel):
    amount: float
    currency: str = "USD"
    billing_period: str = "monthly"
    is_negotiable: bool = False


class UCPProduct(BaseModel):
    """A UCP-compliant product object (JSON-LD/schema.org Product subset)."""

    id: str
    name: str
    description: str
    category: str
    url: str
    pricing: list[UCPPricingSpec]
    features: list[str] = Field(default_factory=list)
    availability: str = "InStock"
    trust_signals: list[str] = Field(default_factory=list)
    machine_readable_schema: dict[str, Any] = Field(default_factory=dict)

    def to_json_ld(self) -> dict[str, Any]:
        """Render as JSON-LD schema.org Product."""
        return {
            "@context": "https://schema.org",
            "@type": "Product",
            "@id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "url": self.url,
            "offers": [
                {
                    "@type": "Offer",
                    "price": p.amount,
                    "priceCurrency": p.currency,
                    "availability": f"https://schema.org/{self.availability}",
                }
                for p in self.pricing
            ],
        }


class UCPSearchQuery(BaseModel):
    category: str
    budget_max_usd: float | None = None
    required_features: list[str] = Field(default_factory=list)
    agent_id: str | None = None


class UCPSearchResponse(BaseModel):
    products: list[UCPProduct]
    total: int
    query_echo: UCPSearchQuery


class UCPNativeCheckoutRequest(BaseModel):
    product_id: str
    tier_name: str
    quantity: int = 1
    buyer_agent_id: str
    mandate_token: str | None = None  # AP2 token if available
    idempotency_key: str


class UCPNativeCheckoutResponse(BaseModel):
    order_id: str
    status: str  # confirmed | pending | failed
    product_id: str
    final_price_usd: float
    fulfillment_eta: str | None = None
