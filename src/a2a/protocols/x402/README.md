# x402 — HTTP Payment Required Protocol

> **Layer:** Intent + Authorization (IMF three-layer model, Layers 1–2)
> **Version implemented:** x402 Draft 2025
> **Spec reference:** https://x402.org/

## What it does

x402 builds on the dormant HTTP 402 "Payment Required" status code to create an in-band
payment protocol for the web. An agent making an HTTP request to a paid endpoint receives:

```
HTTP/1.1 402 Payment Required
X-Payment-Required: {"scheme":"exact","network":"base","amount":"0.01","asset":"USDC","recipient":"0x..."}
```

The agent then attaches a payment proof (a signed cryptographic receipt) in the next request,
and the server verifies it before serving the resource.

**Why this matters for agentic commerce:**
x402 makes payment a natural part of the HTTP request cycle — no separate checkout flow,
no redirect, no human approval gate. An agent navigating paid APIs or data services
can handle payment inline, as just another HTTP header.

## Key insight for the article

x402 is the most radical simplification of the checkout flow.
It collapses Layer 1 (intent) and Layer 2 (authorization) into a single HTTP round-trip.
The "funnel" literally does not exist — the agent hits a URL, gets a 402, pays, and retries.

The tradeoff: x402 as specified uses on-chain stablecoin payments (USDC on Base).
That introduces settlement finality latency and gas costs.
For micropayments (API access, per-call pricing) this is elegant.
For larger B2B purchases, AP2 with off-chain settlement is likely more practical.

## Running the benchmark

```bash
uv run a2a bench x402
```

## Protocol flow

```
Agent                           HTTP Server (Seller)
  |                               |
  |--- GET /api/catalog -------->|
  |<-- 402 Payment Required -----|
  |    X-Payment-Required: {...}  |
  |                               |
  |   [Agent constructs payment]  |
  |                               |
  |--- GET /api/catalog -------->|
  |    X-Payment: <proof>         |
  |<-- 200 OK -------------------|
  |    (resource served)          |
  |                               |
  |--- POST /api/checkout ------->|
  |    X-Payment: <proof>         |
  |<-- 200 OK -------------------|
  |    (order confirmation)       |
```
