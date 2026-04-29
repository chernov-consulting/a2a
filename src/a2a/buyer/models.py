"""Buyer-side models: mandate, archetypes, and decision records."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class BuyerArchetype(StrEnum):
    """Three buyer archetypes for the v0.1 experiment.

    These differ in how much context they carry and how they prioritise criteria.
    """

    PRICE_OPTIMISER = "price_optimiser"
    FEATURE_MATCHER = "feature_matcher"
    RISK_AVERSE = "risk_averse"


class MandateContext(StrEnum):
    """How richly the buyer's context is assembled."""

    TERSE_JSON = "terse_json"              # Short structured brief
    FULL_TRANSCRIPT = "full_transcript"    # Full conversation transcript as context
    ANNOTATED_BRIEF = "annotated_brief"    # Mid-length with inline rationale


class Mandate(BaseModel):
    """What the buying agent is authorised and instructed to do."""

    archetype: BuyerArchetype
    context_richness: MandateContext = Field(default=MandateContext.TERSE_JSON)
    budget_usd: float = Field(description="Maximum spend authorised")
    required_features: list[str] = Field(default_factory=list)
    preferred_features: list[str] = Field(default_factory=list)
    deal_breakers: list[str] = Field(default_factory=list)
    max_negotiation_turns: int = Field(default=3)
    principal_name: str = Field(default="Principal")
    additional_context: str = Field(default="")

    def as_system_prompt(self) -> str:
        """Render the mandate as a system prompt for the buying agent."""
        features = "\n".join(f"  - {f}" for f in self.required_features)
        preferred = "\n".join(f"  - {f}" for f in self.preferred_features)
        deal_breakers = "\n".join(f"  - {f}" for f in self.deal_breakers)

        archetype_guidance = {
            BuyerArchetype.PRICE_OPTIMISER: (
                "You prioritise the lowest total cost of ownership. "
                "If the price can be negotiated, negotiate firmly. "
                "Walk away if you cannot get within 20% of your target price."
            ),
            BuyerArchetype.FEATURE_MATCHER: (
                "You prioritise getting every required feature. "
                "You will pay a premium for the right feature set. "
                "Price is secondary to feature completeness."
            ),
            BuyerArchetype.RISK_AVERSE: (
                "You prioritise trust, SLAs, return policies, and vendor stability. "
                "You need clear guarantees before committing. "
                "You prefer established vendors with verifiable credentials."
            ),
        }[self.archetype]

        base = f"""You are an autonomous buying agent acting on behalf of {self.principal_name}.

Your archetype: {self.archetype.value}
{archetype_guidance}

Budget: up to ${self.budget_usd:.2f} (absolute maximum — never exceed this)
Required features (must-have):
{features or '  (none specified)'}
Preferred features (nice-to-have):
{preferred or '  (none specified)'}
Deal-breakers (walk away if present):
{deal_breakers or '  (none specified)'}

Negotiation rules:
- Maximum {self.max_negotiation_turns} negotiation turns. If no deal by turn {self.max_negotiation_turns}, walk away.
- Always state your reasoning clearly and cite specific product features or pricing details.
- After each decision, produce a structured rationale (JSON).
"""
        if self.additional_context:
            base += f"\nAdditional context:\n{self.additional_context}\n"
        return base


class BuyerDecision(BaseModel):
    """The buyer agent's final decision."""

    outcome: str  # buy | walk | escalate_to_human | timeout
    reason: str
    agreed_price_usd: float | None = Field(default=None)
    agreed_tier: str | None = Field(default=None)
    rationale: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured JSON rationale: mandate_alignment, key_factors, counterfactual",
    )
    negotiation_turns_used: int = Field(default=0)


# ── Pre-built mandates for v0.1 ─────────────────────────────────────────────

def price_optimiser_mandate(budget: float = 250.0) -> Mandate:
    return Mandate(
        archetype=BuyerArchetype.PRICE_OPTIMISER,
        context_richness=MandateContext.TERSE_JSON,
        budget_usd=budget,
        required_features=["metrics ingestion", "log retention", "alerting"],
        preferred_features=["AI anomaly detection", "SSO"],
        deal_breakers=["no trial period", "annual lock-in without monthly option"],
        principal_name="TechCorp Engineering",
    )


def feature_matcher_mandate(budget: float = 400.0) -> Mandate:
    return Mandate(
        archetype=BuyerArchetype.FEATURE_MATCHER,
        context_richness=MandateContext.ANNOTATED_BRIEF,
        budget_usd=budget,
        required_features=[
            "distributed tracing",
            "AI anomaly detection",
            "SOC 2 compliance",
            "30-day log retention",
        ],
        preferred_features=["dedicated CSM", "SLA credits", "SAML SSO"],
        deal_breakers=["no distributed tracing"],
        principal_name="FinServe Platform",
        additional_context=(
            "We are a regulated financial services company. Compliance certifications are non-negotiable. "
            "We have budget flexibility if the feature set is right."
        ),
    )


def risk_averse_mandate(budget: float = 350.0) -> Mandate:
    return Mandate(
        archetype=BuyerArchetype.RISK_AVERSE,
        context_richness=MandateContext.FULL_TRANSCRIPT,
        budget_usd=budget,
        required_features=["99.9% SLA", "support SLA", "data export capability"],
        preferred_features=["dedicated support", "audit logs", "data residency"],
        deal_breakers=["no SLA", "no refund policy", "unverifiable compliance claims"],
        principal_name="HealthData Systems",
        additional_context=(
            "We operate in a regulated healthcare environment. "
            "Vendor lock-in is a risk we take seriously. We need clear exit paths and data portability."
        ),
    )
