"""x402 bench: simulate an agent handling HTTP 402 payment flow."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from a2a.protocols.x402.models import X402PaymentProof, X402PaymentRequirement, X402Response

if TYPE_CHECKING:
    from pathlib import Path


def _mock_tx_hash(payer: str, recipient: str, amount: str) -> str:
    return "0x" + hashlib.sha256(f"{payer}:{recipient}:{amount}:{uuid.uuid4()}".encode()).hexdigest()[:40]


def _mock_sign(payload: str, private_key: str = "mock-key") -> str:
    return hashlib.sha256(f"{private_key}:{payload}".encode()).hexdigest()[:40]


class MockX402Server:
    """Minimal x402-capable HTTP server stub."""

    CATALOG_PRICE = X402PaymentRequirement(
        amount="0.001",
        asset="USDC",
        network="base",
        recipient="0xSellerAddress",
        description="Access to ObserveOps product catalog API",
    )
    CHECKOUT_PRICE = X402PaymentRequirement(
        amount="299.00",
        asset="USDC",
        network="base",
        recipient="0xSellerAddress",
        description="ObserveOps Pro — monthly subscription",
    )

    def get_catalog(self, payment_proof: X402PaymentProof | None = None) -> tuple[int, X402Response]:
        if payment_proof is None:
            return 402, X402Response(status="payment_required")
        if float(payment_proof.amount) < float(self.CATALOG_PRICE.amount):
            return 402, X402Response(status="amount_insufficient")
        return 200, X402Response(
            status="ok",
            resource={
                "products": [{"id": "observeops-pro", "name": "ObserveOps Pro", "price_usd": 299.0}]
            },
        )

    def post_checkout(self, payment_proof: X402PaymentProof | None = None) -> tuple[int, X402Response]:
        if payment_proof is None:
            return 402, X402Response(status="payment_required")
        if float(payment_proof.amount) < float(self.CHECKOUT_PRICE.amount):
            return 402, X402Response(status="amount_insufficient")
        return 200, X402Response(
            status="ok",
            resource={
                "order_id": str(uuid.uuid4())[:8],
                "product": "ObserveOps Pro",
                "tier": "Pro",
                "status": "confirmed",
            },
        )


def run(output_path: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    server = MockX402Server()
    payer_address = "0xBuyerAgentAddress"
    steps = []

    # 1. Agent hits catalog — gets 402
    status, resp = server.get_catalog()
    steps.append(f"GET /catalog → {status} (no payment)")

    # 2. Agent constructs and attaches micro-payment for catalog access
    catalog_proof = X402PaymentProof(
        scheme="exact",
        network="base",
        amount=server.CATALOG_PRICE.amount,
        asset="USDC",
        recipient=server.CATALOG_PRICE.recipient,
        tx_hash=_mock_tx_hash(payer_address, server.CATALOG_PRICE.recipient, server.CATALOG_PRICE.amount),
        payer=payer_address,
        signed_at=datetime.utcnow().isoformat(),
        signature=_mock_sign(f"{payer_address}:{server.CATALOG_PRICE.amount}"),
    )
    status, resp = server.get_catalog(catalog_proof)
    steps.append(f"GET /catalog (with X-Payment) → {status} — {resp.status}")

    # 3. Agent hits checkout with full payment
    checkout_proof = X402PaymentProof(
        scheme="exact",
        network="base",
        amount=server.CHECKOUT_PRICE.amount,
        asset="USDC",
        recipient=server.CHECKOUT_PRICE.recipient,
        tx_hash=_mock_tx_hash(payer_address, server.CHECKOUT_PRICE.recipient, server.CHECKOUT_PRICE.amount),
        payer=payer_address,
        signed_at=datetime.utcnow().isoformat(),
        signature=_mock_sign(f"{payer_address}:{server.CHECKOUT_PRICE.amount}"),
    )
    status, resp = server.post_checkout(checkout_proof)
    order = resp.resource or {}
    steps.append(f"POST /checkout (with X-Payment ${server.CHECKOUT_PRICE.amount}) → {status} — {order.get('status','?')}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    record: dict[str, Any] = {
        "protocol": "x402",
        "product": "ObserveOps Pro — Pro Tier",
        "outcome": order.get("status", "unknown"),
        "final_price_usd": float(server.CHECKOUT_PRICE.amount),
        "latency_ms": latency_ms,
        "steps": steps,
        "asset": "USDC",
        "network": "base",
        "layer_3": "mocked_onchain",
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
