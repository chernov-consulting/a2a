"""x402 HTTP Payment Required protocol models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class X402PaymentRequirement(BaseModel):
    """Embedded in HTTP 402 response headers."""

    scheme: str = Field(default="exact", description="Payment scheme: exact | upto")
    network: str = Field(default="base", description="Blockchain network, e.g. 'base', 'ethereum'")
    amount: str = Field(description="Amount as string to preserve precision, e.g. '0.01'")
    asset: str = Field(default="USDC", description="Asset ticker")
    recipient: str = Field(description="Recipient address (0x...)")
    description: str = Field(default="", description="Human-readable description of what is being paid for")
    expires_at: str | None = Field(default=None, description="ISO-8601 expiry for this payment requirement")
    memo: str | None = Field(default=None, description="Optional on-chain memo")


class X402PaymentProof(BaseModel):
    """Attached to subsequent HTTP requests in the X-Payment header."""

    scheme: str
    network: str
    amount: str
    asset: str
    recipient: str
    tx_hash: str = Field(description="On-chain transaction hash (or mock hash in bench mode)")
    payer: str = Field(description="Payer address")
    signed_at: str = Field(description="ISO-8601 timestamp of signing")
    signature: str = Field(description="ECDSA signature over the payment details")


class X402Response(BaseModel):
    """Server response after verifying a payment proof."""

    status: str  # ok | payment_invalid | payment_expired | amount_insufficient
    resource: dict[str, object] | None = None
    error: str | None = None
