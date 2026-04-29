"""MCP (Model Context Protocol) commerce tool definitions and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MCPToolParameter(BaseModel):
    name: str
    type: str  # string | number | boolean | array | object
    description: str
    required: bool = True


class MCPToolDefinition(BaseModel):
    name: str
    description: str
    parameters: list[MCPToolParameter]
    return_schema: dict[str, Any] = Field(default_factory=dict)


class MCPToolCall(BaseModel):
    tool_name: str
    parameters: dict[str, Any]
    call_id: str


class MCPToolResult(BaseModel):
    call_id: str
    success: bool
    result: dict[str, Any]
    error: str | None = None


class MCPSearchResult(BaseModel):
    products: list[dict[str, Any]]
    total_found: int


class MCPCheckoutResult(BaseModel):
    order_id: str
    product_id: str
    tier: str
    price_usd: float
    status: str  # pending | confirmed | failed
    next_steps: str


# Standard commerce MCP tool manifest
COMMERCE_TOOLS: list[MCPToolDefinition] = [
    MCPToolDefinition(
        name="search_products",
        description="Search for products matching criteria. Returns structured results.",
        parameters=[
            MCPToolParameter(name="query", type="string", description="Natural language search query"),
            MCPToolParameter(name="max_budget_usd", type="number", description="Budget ceiling", required=False),
            MCPToolParameter(name="required_features", type="array", description="Must-have features", required=False),
            MCPToolParameter(name="category", type="string", description="Product category filter", required=False),
        ],
        return_schema={"products": "array", "total_found": "number"},
    ),
    MCPToolDefinition(
        name="get_pricing",
        description="Get detailed pricing for a specific product ID.",
        parameters=[MCPToolParameter(name="product_id", type="string", description="Product identifier")],
        return_schema={"tiers": "array", "currency": "string"},
    ),
    MCPToolDefinition(
        name="initiate_checkout",
        description="Initiate a purchase. Returns an order ID. Settlement is handled separately.",
        parameters=[
            MCPToolParameter(name="product_id", type="string", description="Product to purchase"),
            MCPToolParameter(name="tier", type="string", description="Pricing tier name"),
            MCPToolParameter(name="quantity", type="number", description="Units", required=False),
            MCPToolParameter(name="idempotency_key", type="string", description="Unique request key"),
        ],
        return_schema={"order_id": "string", "status": "string", "price_usd": "number"},
    ),
    MCPToolDefinition(
        name="get_order_status",
        description="Get the current status of an order.",
        parameters=[MCPToolParameter(name="order_id", type="string", description="Order identifier")],
        return_schema={"status": "string", "details": "object"},
    ),
]
