# Experiment: 2026-05-saas-subscription

> **Product:** ObserveOps Pro — B2B SaaS Observability Platform
> **Status:** Config ready — run with `uv run a2a sim --experiment experiments/2026-05-saas-subscription/config.yaml`
> **Version:** v0.1

## Setup

```bash
# Copy and fill in your API keys
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and ANTHROPIC_API_KEY

# Run the experiment (540 dyads, ~$2–5 estimated LLM cost)
uv run a2a sim --experiment experiments/2026-05-saas-subscription/config.yaml

# Generate the HTML report
uv run a2a report --experiment experiments/2026-05-saas-subscription/ --open-browser
```

## Design

| Dimension | Values |
|---|---|
| Buyer archetypes | price_optimiser, feature_matcher, risk_averse |
| Seller funnel variants | api_contract, rich_schema, persuasion_page |
| Dyads per cell | 30 |
| Total dyads | 270 (3 × 3 × 30) |
| Max negotiation turns | 3 |
| Buyer model | openai/gpt-4o |
| Seller model | anthropic/claude-3-5-sonnet-20241022 |
| Judge model | openai/gpt-4o-mini |

## Research questions

1. **Buyer context:** Does a richer mandate (annotated brief vs terse JSON) produce better buy decisions and more coherent rationales?
2. **Seller funnel:** Which funnel variant (api_contract | rich_schema | persuasion_page) drives higher conversion? Does the persuasion page backfire with rational agents?
3. **Rationale quality:** Can agents produce citation-grounded rationales that a judge LLM would score ≥7/10?

## Expected outputs

- `results.jsonl` — one JSONL record per dyad
- `summary.json` — aggregate stats (buy rate, cost, latency)
- `report.html` — self-contained HTML report with Plotly charts
