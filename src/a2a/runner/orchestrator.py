"""Experiment orchestrator: runs all cells, records each dyad."""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

import structlog
import yaml
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from a2a.buyer.agent import BuyingAgent
from a2a.buyer.models import (
    BuyerArchetype,
    MandateContext,
    feature_matcher_mandate,
    price_optimiser_mandate,
    risk_averse_mandate,
)
from a2a.catalog.fetcher import physical_good_catalog, saas_subscription_catalog
from a2a.config import AppConfig, get_config
from a2a.llm import get_client
from a2a.runner.judge import JudgeLLM
from a2a.runner.ledger import Ledger
from a2a.runner.models import (
    DyadRecord,
    ExperimentConfig,
    ExperimentResult,
    FunnelStep,
)
from a2a.seller.agent import SellingAgent
from a2a.seller.models import FunnelVariant, SellerConfig

if TYPE_CHECKING:
    from pathlib import Path

    from a2a.catalog.models import CatalogEntry

log = structlog.get_logger(__name__)
console = Console()

_MANDATE_FACTORIES = {
    BuyerArchetype.PRICE_OPTIMISER: price_optimiser_mandate,
    BuyerArchetype.FEATURE_MATCHER: feature_matcher_mandate,
    BuyerArchetype.RISK_AVERSE: risk_averse_mandate,
}

_CATALOG_FACTORIES = {
    "saas_subscription": saas_subscription_catalog,
    "physical_good": physical_good_catalog,
}


class Orchestrator:
    """Runs a complete experiment: all cells, all dyads, full ledger."""

    def __init__(
        self,
        config: ExperimentConfig,
        experiment_dir: Path,
        app_config: AppConfig | None = None,
    ) -> None:
        self.config = config
        self.experiment_dir = experiment_dir
        self._app_cfg = app_config or get_config()
        self._llm = get_client(app_config)
        self._ledger = Ledger(experiment_dir / "results.jsonl")
        self._judge = JudgeLLM(self._llm, model=config.judge_model)

    @classmethod
    def from_config_file(cls, config_path: Path, app_config: AppConfig | None = None) -> Orchestrator:
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        exp_config = ExperimentConfig(**data)
        return cls(exp_config, config_path.parent, app_config)

    def run(self) -> ExperimentResult:
        result = ExperimentResult(config=self.config)

        catalog = self._load_catalog()
        cells = [
            (archetype, variant)
            for archetype in self.config.buyer_archetypes
            for variant in self.config.funnel_variants
        ]
        total_dyads = len(cells) * self.config.dyads_per_cell

        console.print(
            f"\n[bold cyan]a2a experiment[/bold cyan] [dim]{self.config.slug}[/dim]\n"
            f"  Product: {catalog.product.name}\n"
            f"  Cells: {len(cells)} | Dyads/cell: {self.config.dyads_per_cell} | "
            f"Total: {total_dyads}\n"
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Running dyads...", total=total_dyads)

            for archetype, funnel_variant in cells:
                for dyad_idx in range(self.config.dyads_per_cell):
                    seed = self.config.seed + hash((archetype, funnel_variant, dyad_idx)) % 10_000
                    rng = random.Random(seed)
                    _ = rng  # available for future stochastic decisions

                    dyad_record = self._run_dyad(
                        catalog=catalog,
                        archetype=archetype,
                        funnel_variant=funnel_variant,
                        dyad_idx=dyad_idx,
                        seed=seed,
                    )
                    result.dyad_records.append(dyad_record)
                    result.total_dyads += 1
                    self._ledger.append(dyad_record)
                    progress.advance(task)

        result.completed_at = datetime.utcnow()
        self._write_summary(result)

        console.print(
            f"\n[bold green]Done.[/bold green] "
            f"Buy rate: [bold]{result.buy_rate:.1%}[/bold] | "
            f"Total cost: [bold]${result.total_cost_usd:.4f}[/bold] | "
            f"Avg latency: [bold]{result.avg_latency_ms:.0f}ms[/bold]\n"
            f"Results: {self._ledger._path}\n"
        )
        return result

    def _load_catalog(self) -> CatalogEntry:
        factory = _CATALOG_FACTORIES.get(self.config.product_type)
        if factory:
            return factory()
        raise ValueError(f"Unknown product_type: {self.config.product_type!r}")

    def _run_dyad(
        self,
        catalog: CatalogEntry,
        archetype: BuyerArchetype,
        funnel_variant: FunnelVariant,
        dyad_idx: int,
        seed: int,
    ) -> DyadRecord:
        dyad_id = str(uuid.uuid4())[:8]
        t_start = time.perf_counter()

        mandate_factory = _MANDATE_FACTORIES[archetype]
        mandate = mandate_factory()
        mandate = mandate.model_copy(update={"max_negotiation_turns": self.config.max_negotiation_turns})

        seller_cfg = SellerConfig(funnel_variant=funnel_variant)
        seller = SellingAgent(catalog, seller_cfg, self._llm, model=self.config.seller_model)
        buyer = BuyingAgent(mandate, self._llm, model=self.config.buyer_model)

        funnel_steps: list[FunnelStep] = []
        conversation: list[dict[str, str]] = []
        all_llm_records = []

        # Step 1: Seller opens
        t1 = time.perf_counter()
        seller_opening = seller.open()
        opening_records = seller.llm_records[-1:]
        funnel_steps.append(FunnelStep(
            name="discovery",
            reached=True,
            latency_ms=(time.perf_counter() - t1) * 1000,
            tokens_in=sum(r.tokens_in for r in opening_records),
            tokens_out=sum(r.tokens_out for r in opening_records),
            cost_usd=sum(r.cost_usd for r in opening_records),
        ))
        all_llm_records.extend(opening_records)
        conversation.extend(seller_opening)

        # Step 2: Buyer evaluates
        t2 = time.perf_counter()
        buyer_decision, updated_conversation = buyer.evaluate_and_negotiate(
            catalog=catalog,
            seller_messages=seller_opening,
            funnel_variant=funnel_variant.value,
            max_turns=self.config.max_negotiation_turns,
        )
        eval_records = buyer.llm_records
        funnel_steps.append(FunnelStep(
            name="evaluation",
            reached=True,
            latency_ms=(time.perf_counter() - t2) * 1000,
            tokens_in=sum(r.tokens_in for r in eval_records),
            tokens_out=sum(r.tokens_out for r in eval_records),
            cost_usd=sum(r.cost_usd for r in eval_records),
        ))
        all_llm_records.extend(eval_records)
        conversation = updated_conversation

        # Negotiation step reached?
        turns_used = buyer_decision.negotiation_turns_used
        funnel_steps.append(FunnelStep(
            name="negotiation",
            reached=turns_used > 0,
            latency_ms=0.0,
        ))

        # Checkout reached?
        is_buy = buyer_decision.outcome == "buy"
        funnel_steps.append(FunnelStep(name="checkout", reached=is_buy))
        funnel_steps.append(FunnelStep(name="post_purchase", reached=is_buy))

        # Step 3: Judge scores rationales
        judge_scores: dict[str, object] = {}
        judge_record = None
        if buyer_decision.rationale or buyer_decision.outcome in {"buy", "walk"}:
            seller_last_rationale = (
                seller.llm_records[-1].metadata if seller.llm_records else {}
            )
            mandate_summary = (
                f"Archetype: {archetype}, Budget: ${mandate.budget_usd}, "
                f"Required: {', '.join(mandate.required_features[:3])}"
            )
            judge_scores, judge_record = self._judge.score(
                mandate_summary=mandate_summary,
                product_name=catalog.product.name,
                outcome=buyer_decision.outcome,
                buyer_rationale=buyer_decision.rationale,
                seller_rationale=dict(seller_last_rationale),
            )
            if judge_record:
                all_llm_records.append(judge_record)

        # Aggregate metrics
        total_tokens_in = sum(r.tokens_in for r in all_llm_records)
        total_tokens_out = sum(r.tokens_out for r in all_llm_records)
        total_cost = sum(r.cost_usd for r in all_llm_records)
        total_latency = (time.perf_counter() - t_start) * 1000

        reached_steps = sum(1 for s in funnel_steps if s.reached)
        conversion_rate = reached_steps / len(funnel_steps) if funnel_steps else 0.0

        list_price = None
        discount_pct = None
        if catalog.product.pricing_tiers:
            tier_prices = [t.price_usd for t in catalog.product.pricing_tiers if t.price_usd]
            if tier_prices:
                list_price = min(tier_prices)
        if list_price and buyer_decision.agreed_price_usd and list_price > 0:
            discount_pct = max(0.0, (list_price - buyer_decision.agreed_price_usd) / list_price * 100)

        return DyadRecord(
            dyad_id=dyad_id,
            experiment_slug=self.config.slug,
            buyer_archetype=archetype.value,
            funnel_variant=funnel_variant.value,
            mandate_context=MandateContext.TERSE_JSON.value,
            buyer_model=self.config.buyer_model,
            seller_model=self.config.seller_model,
            seed=seed,
            completed_at=datetime.utcnow(),
            outcome=buyer_decision.outcome,
            reason=buyer_decision.reason[:300],
            agreed_price_usd=buyer_decision.agreed_price_usd,
            agreed_tier=buyer_decision.agreed_tier,
            list_price_usd=list_price,
            discount_pct=discount_pct,
            negotiation_turns_used=turns_used,
            funnel_steps=funnel_steps,
            conversion_rate=conversion_rate,
            total_tokens_in=total_tokens_in,
            total_tokens_out=total_tokens_out,
            total_cost_usd=total_cost,
            total_latency_ms=round(total_latency, 1),
            buyer_rationale=buyer_decision.rationale,
            seller_rationale=dict(seller.llm_records[-1].metadata) if seller.llm_records else {},
            judge_score=dict(judge_scores),
            conversation_preview=conversation[:6],
        )

    def _write_summary(self, result: ExperimentResult) -> None:
        summary = {
            "slug": result.config.slug,
            "product_type": result.config.product_type,
            "total_dyads": result.total_dyads,
            "buy_rate": round(result.buy_rate, 4),
            "total_cost_usd": round(result.total_cost_usd, 6),
            "avg_latency_ms": round(result.avg_latency_ms, 1),
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }
        import json

        (self.experiment_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        log.info("experiment_complete", **summary)
