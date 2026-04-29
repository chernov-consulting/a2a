# A2A — Agent-to-Agent Protocol

> **Layer:** Intent and Orchestration (IMF three-layer model, Layer 1)
> **Version implemented:** A2A 2025-11
> **Spec reference:** https://google.github.io/A2A/

## What it does

A2A (Agent-to-Agent Protocol), an open standard supported by Google and a growing ecosystem,
defines how agents from **different vendors** discover and communicate with each other.
Without A2A, a buyer agent built on OpenAI's stack and a seller agent built on Anthropic's
stack have no standard way to exchange structured messages.

A2A introduces:
- **Agent Cards:** JSON manifests advertising an agent's capabilities and communication endpoint
- **Task lifecycle:** a standard state machine (submitted → working → completed | failed)
- **Streaming:** server-sent events for long-running multi-step tasks
- **Push notifications:** webhook-based status updates

In the commerce context, A2A enables a buyer agent to discover a seller's A2A endpoint,
open a task ("find and purchase the best observability platform for our stack"),
and receive structured updates as the seller agent negotiates, quotes, and closes.

## Key insight for the article

A2A solves the interoperability problem at the intent layer.
Before A2A, each platform had its own proprietary agent-to-agent messaging.
After A2A, an enterprise buyer agent can talk to any A2A-compliant seller,
regardless of who built the underlying models.

The merchant's A2A Agent Card is the machine-readable equivalent of a landing page.
GEO (Generative Engine Optimisation) — optimising content for AI discovery — starts here.

## Running the benchmark

```bash
uv run a2a bench a2a
```

## Protocol flow

```
Buyer Agent                     Seller Agent
  |                               |
  |--- GET /.well-known/agent --->|  (discover Agent Card)
  |<-- AgentCard -----------------|
  |                               |
  |--- POST /tasks/send -------->|  (submit task: "find observability product")
  |<-- TaskAccepted -------------|
  |    (task_id)                  |
  |                               |
  |--- GET /tasks/{id} --------->|  (poll or receive SSE)
  |<-- TaskUpdate (working) -----|
  |                               |
  |<-- TaskUpdate (completed) ---|
  |    (artifact: purchase intent)|
  |                               |
  |--- POST /tasks/send -------->|  (submit task: "proceed to checkout")
  |<-- TaskAccepted -------------|
  |<-- TaskUpdate (completed) ---|
  |    (artifact: order_id)       |
```
