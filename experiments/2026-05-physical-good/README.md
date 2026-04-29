# Experiment: 2026-05-physical-good

> **Product:** Terroir Direct — Single-Bottle Wine Subscription
> **Status:** Config ready — run with `uv run a2a sim --experiment experiments/2026-05-physical-good/config.yaml`
> **Version:** v0.1

## Setup

```bash
cp .env.example .env
# Edit .env with your OPENAI_API_KEY and ANTHROPIC_API_KEY

uv run a2a sim --experiment experiments/2026-05-physical-good/config.yaml
uv run a2a report --experiment experiments/2026-05-physical-good/ --open-browser
```

## Design

Identical cell structure to `2026-05-saas-subscription` for apples-to-apples comparison.
The key contrast: physical goods have shipping, return policy, and different trust signal types.

Expected research findings (hypothesis):
- `risk_averse` buyer archetype shows higher relative sensitivity to return policy and trust signals for physical goods vs. SaaS
- `persuasion_page` funnel may perform relatively better for physical goods (emotional product) than SaaS
- `api_contract` funnel will perform worse for physical goods (less standardised schema)

## Research questions

Same three questions as the SaaS experiment, plus:
4. **Product type effect:** Do funnel variant effectiveness rankings hold across product categories, or does the physical/digital distinction change the optimal seller strategy?
