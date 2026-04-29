"""AP2 — Agent Payments Protocol data models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AP2Mandate(BaseModel):
    """A signed mandate authorising an agent to transact within defined bounds."""

    version: str = Field(default="ap2-draft-2025-q4")
    agent_id: str = Field(description="Public key fingerprint or UUID of the agent")
    principal_id: str = Field(description="Identifier of the authorising principal")
    scope_categories: list[str] = Field(description="Allowed product categories, e.g. ['saas', 'subscription']")
    allowed_vendors: list[str] | None = Field(default=None, description="Explicit allow-list; null = any vendor in scope")
    max_transaction_usd: float = Field(description="Per-transaction spend ceiling")
    max_daily_usd: float = Field(description="Daily aggregate spend ceiling")
    max_monthly_usd: float = Field(description="Monthly aggregate spend ceiling")
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="Hard expiry")
    revocation_url: str | None = Field(default=None)
    signature: str = Field(default="", description="Base64-encoded Ed25519 signature of canonical JSON")

    def is_within_scope(self, category: str, amount_usd: float) -> bool:
        if category not in self.scope_categories:
            return False
        if amount_usd > self.max_transaction_usd:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True


class AP2MandateChallenge(BaseModel):
    """Challenge issued by the seller to verify the agent holds the private key."""

    nonce: str
    issued_at: datetime = Field(default_factory=datetime.utcnow)
    expires_in_seconds: int = Field(default=30)


class AP2ChallengeResponse(BaseModel):
    """Agent's signed response to the mandate challenge."""

    nonce: str
    agent_id: str
    signed_nonce: str  # Base64-encoded Ed25519 signature of nonce


class AP2AuthorizationToken(BaseModel):
    """Scoped, time-limited token returned after successful mandate verification."""

    token: str
    scope_categories: list[str]
    max_transaction_usd: float
    expires_at: datetime
    issued_to_agent: str


class AP2PurchaseRequest(BaseModel):
    """Agent's purchase request, presented with a valid authorization token."""

    token: str
    product_id: str
    tier: str
    quantity: int = Field(default=1)
    requested_price_usd: float
    idempotency_key: str  # Prevents duplicate execution


class AP2PurchaseConfirmation(BaseModel):
    """Seller's confirmation (or rejection) of the purchase request."""

    status: str  # confirmed | rejected
    reason: str | None = None
    transaction_id: str | None = None
    final_price_usd: float | None = None
    settled_at: datetime | None = None
