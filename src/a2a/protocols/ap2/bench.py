"""AP2 benchmark: run a toy purchase through the AP2 protocol and emit a ledger record."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from a2a.protocols.ap2.models import (
    AP2AuthorizationToken,
    AP2ChallengeResponse,
    AP2Mandate,
    AP2MandateChallenge,
    AP2PurchaseConfirmation,
    AP2PurchaseRequest,
)

if TYPE_CHECKING:
    from pathlib import Path


def _sign(payload: str, key: str = "mock-private-key") -> str:
    """Mock Ed25519 signature (SHA-256 HMAC for the bench — real impl uses cryptography lib)."""
    return hashlib.sha256(f"{key}:{payload}".encode()).hexdigest()[:32]


def run(output_path: Path | None = None) -> dict[str, Any]:
    """Execute one full AP2 transaction and return (or write) a ledger record."""
    t0 = time.perf_counter()
    protocol = "ap2"
    product = "ObserveOps Pro — Pro Tier"
    price_usd = 299.0
    agent_id = str(uuid.uuid4())[:8]

    # 1. Agent presents mandate
    mandate = AP2Mandate(
        agent_id=agent_id,
        principal_id="TechCorp-Engineering",
        scope_categories=["saas", "subscription"],
        max_transaction_usd=350.0,
        max_daily_usd=500.0,
        max_monthly_usd=2000.0,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    mandate_json = mandate.model_dump_json()
    mandate_sig = _sign(mandate_json)
    mandate = mandate.model_copy(update={"signature": mandate_sig})

    # 2. Seller validates mandate and issues challenge
    assert mandate.is_within_scope("saas", price_usd), "Mandate scope check failed"
    challenge = AP2MandateChallenge(nonce=str(uuid.uuid4()))

    # 3. Agent responds to challenge
    AP2ChallengeResponse(
        nonce=challenge.nonce,
        agent_id=agent_id,
        signed_nonce=_sign(challenge.nonce, key=agent_id),
    )

    # 4. Seller issues authorization token
    auth_token = AP2AuthorizationToken(
        token=str(uuid.uuid4()),
        scope_categories=mandate.scope_categories,
        max_transaction_usd=mandate.max_transaction_usd,
        expires_at=mandate.expires_at,
        issued_to_agent=agent_id,
    )

    # 5. Agent submits purchase request
    purchase_req = AP2PurchaseRequest(
        token=auth_token.token,
        product_id="observeops-pro",
        tier="Pro",
        quantity=1,
        requested_price_usd=price_usd,
        idempotency_key=str(uuid.uuid4()),
    )

    # 6. Seller confirms (Layer 3 mocked)
    assert purchase_req.requested_price_usd <= auth_token.max_transaction_usd
    confirmation = AP2PurchaseConfirmation(
        status="confirmed",
        transaction_id=str(uuid.uuid4()),
        final_price_usd=price_usd,
        settled_at=datetime.utcnow(),
    )

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    record: dict[str, Any] = {
        "protocol": protocol,
        "product": product,
        "outcome": confirmation.status,
        "final_price_usd": confirmation.final_price_usd,
        "latency_ms": latency_ms,
        "steps": ["mandate_presented", "challenge_issued", "challenge_responded", "token_issued", "purchase_submitted", "confirmed"],
        "mandate_scope_check": "passed",
        "layer_3": "mocked",
        "timestamp": datetime.utcnow().isoformat(),
    }

    line = json.dumps(record)
    if output_path:
        with output_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line)

    return record


if __name__ == "__main__":
    run()
