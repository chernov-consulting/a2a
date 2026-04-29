# a2a — When Both Sides Are Agents

> **An open benchmark for agentic e-commerce.**
> We simulate full commercial transactions where both the buyer and the seller are AI agents,
> measure what happens to funnels, negotiations, and payments, and publish every result.

**Showcase:** [a2a.chernov.io](https://a2a.chernov.io) •
**Article:** [chernov.io/writing/when-both-sides-are-agents](https://chernov.io/writing/when-both-sides-are-agents/) •
**License (code):** Apache-2.0 • **License (content):** CC-BY-4.0

---

## The question

E-commerce funnels were built for human attention — urgency badges, countdown timers, social proof,
friction-optimised paywalls. When agents do the buying *and* the selling, none of that matters anymore.
But what *does* matter? How should a seller agent design its onboarding for an audience that doesn't click?
How should a buyer agent assemble its context? And when a transaction happens, can either side explain why?

This repo is an attempt to answer those questions experimentally, with versioned code and
reproducible results.

---

## Quick start

```bash
# 1. Install uv if you don't have it
curl -Lsf https://astral.sh/uv/install.sh | sh

# 2. Clone and enter
git clone https://github.com/chernov-consulting/a2a && cd a2a

# 3. Copy config templates
cp env.yaml.example env.yaml   # edit with your API keys
cp .env.example .env           # add provider keys here

# 4. Install dependencies
uv sync

# 5. Run a quick smoke test (uses a mock LLM, no API keys needed)
uv run pytest tests/ -x -q

# 6. Run the v0.1 SaaS subscription experiment
uv run a2a sim --experiment experiments/2026-05-saas-subscription/config.yaml

# 7. Generate the HTML report
uv run a2a report --experiment experiments/2026-05-saas-subscription/

# 8. Open the report
open experiments/2026-05-saas-subscription/report.html
```

---

## What gets simulated

```
Inputs (product URL/PDF + buyer brief)
  │
  ├─► Catalog fetcher → structured product schema
  │
  ├─► Seller agent   → funnel variant (API contract | rich schema | persuasion page)
  │
  └─► Buyer agent    → mandate (terse JSON | full transcript | annotated brief)
            │
            ▼
        A2A negotiation (≤3 turns)
            │
            ▼
        Decision: buy | walk | escalate_to_human | timeout
            │
            ▼
        L3 mock settlement  ←── no real money, ever
            │
            ▼
        JSONL ledger (tokens, latency, $cost, steps, outcome, rationale)
            │
            ▼
        HTML report + showcase site
```

**3 buyer archetypes × 3 seller funnel variants × 2 product categories = 18 cells, 30 dyads each.**

---

## Experiments

| Slug | Product | Status |
|---|---|---|
| [2026-05-saas-subscription](experiments/2026-05-saas-subscription/) | B2B SaaS observability tier | v0.1 |
| [2026-05-physical-good](experiments/2026-05-physical-good/) | Single-bottle wine subscription | v0.1 |

---

## Protocol samples

Runnable, versioned mini-examples in `src/a2a/protocols/`:

| Protocol | Layer | Status |
|---|---|---|
| [AP2](src/a2a/protocols/ap2/) | Authorization | v0.1 |
| [MCP](src/a2a/protocols/mcp/) | Intent | v0.1 |
| [A2A](src/a2a/protocols/a2a/) | Intent | v0.1 |
| [x402](src/a2a/protocols/x402/) | Intent + Authorization | v0.1 |
| [UCP](src/a2a/protocols/ucp/) | Intent | v0.1 |

---

## Citing this work

```
Chernov, A. (2026). When Both Sides Are Agents: A Versioned Open Benchmark
for Agentic E-Commerce. Chernov Consulting OÜ.
https://github.com/chernov-consulting/a2a
```

Full BibTeX in `NOTICE`.

---

## Contributing

Issues and PRs welcome. See `AGENTS.md` for code conventions, commit format, and security rules.
All contributors agree to license their contributions under Apache-2.0 (code) / CC-BY-4.0 (content).
