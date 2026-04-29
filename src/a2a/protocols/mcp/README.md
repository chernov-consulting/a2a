# MCP — Model Context Protocol

> **Layer:** Intent and Orchestration (IMF three-layer model, Layer 1)
> **Version implemented:** MCP 2025-11
> **Spec reference:** https://modelcontextprotocol.io/specification/2025-11

## What it does

MCP (Model Context Protocol), developed by Anthropic and now broadly adopted,
standardises how AI agents access external **tools** and **data sources**.
In the commerce context, MCP enables:

- An agent to call a **catalog tool** to search and compare products
- An agent to call a **checkout tool** to initiate a purchase
- An agent to call a **post-purchase tool** for returns, tracking, or support

The protocol runs over JSON-RPC 2.0. The server exposes a manifest of available tools;
the agent calls tools by name with typed parameters; the server returns structured results.

## Key insight for the article

MCP is the "API documentation becomes the storefront" principle made concrete.
A merchant who publishes an MCP server is, in effect, publishing a machine-readable
product catalog and checkout interface. The agent doesn't need to navigate a web page.
It reads the tool manifest, calls `search_products(query=..., budget=...)`,
compares the structured results, and calls `initiate_checkout(product_id=..., tier=...)`.

The 70-screen human onboarding flow becomes a tool manifest with six fields.

## Running the benchmark

```bash
uv run a2a bench mcp
```

## Protocol flow

```
Agent                           MCP Server (Seller)
  |                               |
  |--- initialize -------------->|  (negotiate capabilities)
  |<-- InitializeResult ---------|
  |                               |
  |--- tools/list -------------->|  (discover available tools)
  |<-- ToolList -----------------|
  |    [search_products,          |
  |     get_pricing,              |
  |     initiate_checkout,        |
  |     get_order_status]         |
  |                               |
  |--- tools/call (search) ----->|
  |<-- ToolResult ---------------|
  |                               |
  |--- tools/call (checkout) --->|
  |<-- ToolResult (order_id) ----|
```
