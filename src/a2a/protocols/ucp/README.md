# UCP — Google Universal Commerce Protocol

> **Layer:** Intent and Orchestration (IMF three-layer model, Layer 1)
> **Version implemented:** UCP 2026-01 (launch version)
> **Spec reference:** https://developers.google.com/merchant/ucp

## What it does

Google's Universal Commerce Protocol (launched January 2026) provides a **shared grammar**
for how AI agents discover, compare, and transact with merchants across the web.
It underpins "Native Checkout" in Google Search AI Mode and Gemini — letting users (or agents)
complete purchases from retailers like Etsy and Wayfair without leaving the Google AI surface.

UCP defines:
- **Product Discovery Schema:** structured JSON-LD describing products in a way AI agents can consume
- **Comparison Interface:** a normalised format for price, availability, and feature comparison
- **Intent Handoff:** how an agent passes a verified purchase intent to the merchant's checkout
- **Post-Purchase Hooks:** delivery coordination, returns management, satisfaction signals

## Key insight for the article

UCP is Google's answer to the question: "what replaces the search result and product page
for an agent-mediated world?"

For merchants, UCP compliance is the new SEO. A product that is not in the UCP
product graph is invisible to Google AI agents. But unlike SEO — where you optimise for
human attention signals (clicks, dwell time, bounce rate) — UCP optimisation means
structured data completeness, schema validity, and pricing accuracy.

**The Apps Forum Lisbon 2026 signal made concrete:** "separate content for AI discovery agents"
is UCP compliance. The merchants who got there first have a structural discovery advantage.

## Running the benchmark

```bash
uv run a2a bench ucp
```

## Protocol flow

```
Buyer Agent (Google AI)         UCP Merchant Feed
  |                               |
  |--- Search Intent ----------->| (structured query: category + features + budget)
  |<-- Product Graph Slice -------|
  |    (UCP product objects)      |
  |                               |
  |--- Comparison Request ------->| (normalised feature/price matrix)
  |<-- Comparison Response -------|
  |                               |
  |--- Purchase Intent -----------| (selected product + mandate check)
  |<-- Checkout URL / Deep Link --|
  |    or Native Checkout Token   |
  |                               |
  |--- Native Checkout -----------| (token + payment method)
  |<-- Order Confirmation --------|
```
