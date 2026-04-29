"""UCP bench: simulate a buyer agent using Google's Universal Commerce Protocol."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from a2a.protocols.ucp.models import (
    UCPNativeCheckoutRequest,
    UCPNativeCheckoutResponse,
    UCPProduct,
    UCPPricingSpec,
    UCPSearchQuery,
    UCPSearchResponse,
)


class MockUCPMerchantFeed:
    """Minimal UCP merchant feed stub."""

    PRODUCTS = [
        UCPProduct(
            id="observeops-pro",
            name="ObserveOps Pro",
            description="Production-grade observability for engineering teams.",
            category="SoftwareApplication",
            url="https://observeops.example/pricing",
            pricing=[
                UCPPricingSpec(amount=299.0, billing_period="monthly"),
                UCPPricingSpec(amount=2699.0, billing_period="annual"),
            ],
            features=["metrics", "logs", "traces", "AI anomaly detection", "SSO", "SOC 2"],
            trust_signals=["SOC 2 Type II", "GDPR"],
        ),
        UCPProduct(
            id="observeops-starter",
            name="ObserveOps Starter",
            description="Observability for small teams.",
            category="SoftwareApplication",
            url="https://observeops.example/pricing",
            pricing=[UCPPricingSpec(amount=49.0, billing_period="monthly")],
            features=["metrics", "logs", "community support"],
        ),
    ]

    def search(self, query: UCPSearchQuery) -> UCPSearchResponse:
        results = [
            p for p in self.PRODUCTS
            if (query.budget_max_usd is None or any(t.amount <= query.budget_max_usd for t in p.pricing))
            and all(f.lower() in " ".join(p.features).lower() for f in query.required_features[:2])
        ]
        return UCPSearchResponse(products=results, total=len(results), query_echo=query)

    def native_checkout(self, req: UCPNativeCheckoutRequest) -> UCPNativeCheckoutResponse:
        product = next((p for p in self.PRODUCTS if p.id == req.product_id), None)
        if not product:
            return UCPNativeCheckoutResponse(
                order_id="", status="failed", product_id=req.product_id, final_price_usd=0.0
            )
        price = product.pricing[0].amount
        return UCPNativeCheckoutResponse(
            order_id=str(uuid.uuid4())[:8],
            status="confirmed",
            product_id=req.product_id,
            final_price_usd=price,
            fulfillment_eta="Provisioning in 5 minutes",
        )


def run(output_path: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    feed = MockUCPMerchantFeed()
    steps = []

    # 1. Agent issues structured discovery query
    query = UCPSearchQuery(
        category="SoftwareApplication",
        budget_max_usd=350.0,
        required_features=["metrics", "SOC 2"],
        agent_id="buyer-agent-" + str(uuid.uuid4())[:6],
    )
    search_resp = feed.search(query)
    steps.append(f"UCP search → {search_resp.total} products matching (budget: ${query.budget_max_usd})")

    # 2. Agent inspects JSON-LD for best match
    best = search_resp.products[0] if search_resp.products else None
    if best:
        json_ld = best.to_json_ld()
        steps.append(f"JSON-LD parsed → {best.name}, {len(best.features)} features")

    # 3. Agent initiates Native Checkout
    if best:
        checkout_req = UCPNativeCheckoutRequest(
            product_id=best.id,
            tier_name="Pro",
            buyer_agent_id=query.agent_id or "buyer",
            idempotency_key=str(uuid.uuid4()),
        )
        checkout_resp = feed.native_checkout(checkout_req)
        steps.append(f"Native Checkout → order {checkout_resp.order_id}, status: {checkout_resp.status}")
    else:
        checkout_resp = UCPNativeCheckoutResponse(
            order_id="", status="failed", product_id="", final_price_usd=0.0
        )

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    record: dict[str, Any] = {
        "protocol": "ucp",
        "product": best.name if best else "none",
        "outcome": checkout_resp.status,
        "final_price_usd": checkout_resp.final_price_usd,
        "latency_ms": latency_ms,
        "steps": steps,
        "products_discovered": search_resp.total,
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
