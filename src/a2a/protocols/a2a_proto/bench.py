"""A2A bench: simulate buyer and seller agents exchanging A2A messages."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from a2a.protocols.a2a_proto.models import (
    A2AAgentCard,
    A2AMessage,
    A2ASkill,
    A2ATask,
    A2ATaskUpdate,
)


class MockA2ASellerAgent:
    """Minimal in-process A2A seller agent stub."""

    def __init__(self) -> None:
        self.agent_card = A2AAgentCard(
            name="ObserveOps Sales Agent",
            description="Autonomous sales agent for ObserveOps — the observability platform for engineering teams.",
            url="https://api.observeops.example/a2a",
            skills=[
                A2ASkill(id="product-discovery", name="Product Discovery", description="Search and compare ObserveOps plans"),
                A2ASkill(id="pricing-negotiation", name="Pricing Negotiation", description="Negotiate pricing within authorised bounds"),
                A2ASkill(id="checkout", name="Checkout", description="Initiate a purchase and return an order ID"),
            ],
        )
        self._tasks: dict[str, A2ATask] = {}

    def submit_task(self, message: str, session_id: str | None = None) -> A2ATask:
        task = A2ATask(
            id=str(uuid.uuid4())[:8],
            session_id=session_id,
            status="working",
            messages=[A2AMessage(role="user", parts=[{"type": "text", "content": message}])],
        )
        self._tasks[task.id] = task
        return task

    def process_task(self, task_id: str) -> A2ATaskUpdate:
        task = self._tasks[task_id]
        content = task.messages[-1].parts[0].get("content", "")

        if "find" in content.lower() or "search" in content.lower():
            artifact = {
                "type": "product_recommendation",
                "products": [{"name": "ObserveOps Pro", "tier": "Pro", "price_usd": 299.0, "match_score": 0.92}],
            }
            return A2ATaskUpdate(task_id=task_id, status="completed", artifact=artifact, final=True)

        if "checkout" in content.lower() or "purchase" in content.lower():
            artifact = {
                "type": "order_confirmation",
                "order_id": str(uuid.uuid4())[:8],
                "product": "ObserveOps Pro",
                "tier": "Pro",
                "price_usd": 299.0,
                "status": "confirmed",
            }
            return A2ATaskUpdate(task_id=task_id, status="completed", artifact=artifact, final=True)

        return A2ATaskUpdate(
            task_id=task_id,
            status="completed",
            message=A2AMessage(role="agent", parts=[{"type": "text", "content": "How can I help you today?"}]),
            final=True,
        )


def run(output_path: Path | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    seller = MockA2ASellerAgent()
    steps = []

    # 1. Buyer discovers seller Agent Card
    agent_card = seller.agent_card
    steps.append(f"GET /.well-known/agent → {agent_card.name} ({len(agent_card.skills)} skills)")

    # 2. Buyer submits discovery task
    session_id = str(uuid.uuid4())[:8]
    task1 = seller.submit_task(
        "Find the best observability platform for a 30-engineer team. Budget: $350/month. "
        "Required: distributed tracing, log retention ≥30 days, SOC 2.",
        session_id=session_id,
    )
    update1 = seller.process_task(task1.id)
    products = update1.artifact.get("products", []) if update1.artifact else []
    steps.append(f"task:discovery → {len(products)} products recommended")

    # 3. Buyer submits checkout task
    task2 = seller.submit_task("Proceed with checkout for ObserveOps Pro tier.", session_id=session_id)
    update2 = seller.process_task(task2.id)
    order = update2.artifact or {}
    steps.append(f"task:checkout → order {order.get('order_id', '?')}, status: {order.get('status', '?')}")

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)
    record: dict[str, Any] = {
        "protocol": "a2a",
        "product": "ObserveOps Pro — Pro Tier",
        "outcome": order.get("status", "unknown"),
        "final_price_usd": order.get("price_usd"),
        "latency_ms": latency_ms,
        "steps": steps,
        "tasks_submitted": 2,
        "agent_card_skills": [s.id for s in agent_card.skills],
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
