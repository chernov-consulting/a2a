"""MCP bench: simulate a buyer agent calling a seller's MCP tool server."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from a2a.protocols.mcp.models import (
    COMMERCE_TOOLS,
    MCPCheckoutResult,
    MCPSearchResult,
    MCPToolCall,
    MCPToolResult,
)

if TYPE_CHECKING:
    from pathlib import Path


class MockMCPServer:
    """Minimal in-process MCP server stub for benchmarking."""

    def __init__(self) -> None:
        self.tools = {t.name: t for t in COMMERCE_TOOLS}

    def call(self, call: MCPToolCall) -> MCPToolResult:
        if call.tool_name == "search_products":
            result = MCPSearchResult(
                products=[
                    {"id": "observeops-pro", "name": "ObserveOps Pro", "tier": "Pro", "price_usd": 299.0},
                    {"id": "observeops-starter", "name": "ObserveOps Starter", "tier": "Starter", "price_usd": 49.0},
                ],
                total_found=2,
            )
            return MCPToolResult(call_id=call.call_id, success=True, result=result.model_dump())

        if call.tool_name == "get_pricing":
            return MCPToolResult(
                call_id=call.call_id,
                success=True,
                result={
                    "tiers": [
                        {"name": "Starter", "price_usd": 49.0, "billing": "monthly"},
                        {"name": "Pro", "price_usd": 299.0, "billing": "monthly"},
                        {"name": "Enterprise", "price_usd": None, "billing": "annual"},
                    ],
                    "currency": "USD",
                },
            )

        if call.tool_name == "initiate_checkout":
            result = MCPCheckoutResult(
                order_id=str(uuid.uuid4())[:8],
                product_id=call.parameters.get("product_id", ""),
                tier=call.parameters.get("tier", ""),
                price_usd=299.0,
                status="confirmed",
                next_steps="Invoice sent to billing@techcorp.example. Provisioning starts within 5 minutes.",
            )
            return MCPToolResult(call_id=call.call_id, success=True, result=result.model_dump())

        return MCPToolResult(call_id=call.call_id, success=False, error=f"Unknown tool: {call.tool_name}")


def run(output_path: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    server = MockMCPServer()

    steps = []

    # 1. Buyer discovers available tools
    tool_names = list(server.tools.keys())
    steps.append("tools/list → " + str(tool_names))

    # 2. Buyer searches for products
    search_call = MCPToolCall(
        tool_name="search_products",
        parameters={"query": "observability platform", "max_budget_usd": 350.0, "required_features": ["metrics", "logs"]},
        call_id=str(uuid.uuid4())[:8],
    )
    search_result = server.call(search_call)
    steps.append(f"search_products → {search_result.result.get('total_found', 0)} products")

    # 3. Buyer gets pricing for best match
    pricing_call = MCPToolCall(
        tool_name="get_pricing",
        parameters={"product_id": "observeops-pro"},
        call_id=str(uuid.uuid4())[:8],
    )
    pricing_result = server.call(pricing_call)
    steps.append("get_pricing → " + str(len(pricing_result.result.get("tiers", []))) + " tiers")

    # 4. Buyer initiates checkout (Pro tier, within $350 budget)
    checkout_call = MCPToolCall(
        tool_name="initiate_checkout",
        parameters={
            "product_id": "observeops-pro",
            "tier": "Pro",
            "quantity": 1,
            "idempotency_key": str(uuid.uuid4()),
        },
        call_id=str(uuid.uuid4())[:8],
    )
    checkout_result = server.call(checkout_call)
    steps.append(f"initiate_checkout → {checkout_result.result.get('status')}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    record: dict[str, Any] = {
        "protocol": "mcp",
        "product": "ObserveOps Pro — Pro Tier",
        "outcome": "confirmed" if checkout_result.success else "failed",
        "final_price_usd": checkout_result.result.get("price_usd"),
        "latency_ms": latency_ms,
        "steps": steps,
        "tool_calls": 3,
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
