"""Product catalog fetcher.

Ingests one or more sources (URLs, PDFs, plain text) into a structured CatalogEntry.
Uses the LLM to extract structured product information from raw text.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import httpx
import structlog
from pydantic import ValidationError

from a2a.catalog.models import CatalogEntry, PricingTier, ProductSchema
from a2a.config import AppConfig, get_config
from a2a.exceptions import CatalogError
from a2a.llm import LLMClient, LLMRecord, Message, get_client

log = structlog.get_logger(__name__)

_EXTRACT_SYSTEM = """
You are a product information extractor. Given raw text from a product page, PDF, or document,
extract structured product information and return it as valid JSON matching this schema:

{
  "name": "string",
  "category": "saas | physical | service | subscription",
  "short_description": "string (max 280 chars)",
  "features": ["string"],
  "pricing_tiers": [
    {
      "name": "string",
      "price_usd": number or null,
      "billing_period": "monthly | annual | one-time | usage-based",
      "features": ["string"],
      "is_negotiable": boolean,
      "min_quantity": number or null,
      "max_quantity": number or null
    }
  ],
  "currency": "USD",
  "availability": "available | limited | out_of_stock | region_restricted",
  "shipping": "string or null",
  "return_policy": "string or null",
  "trust_signals": ["string"],
  "terms_url": "string or null",
  "api_endpoint": "string or null"
}

Return only valid JSON, no markdown fences, no explanation.
""".strip()


class CatalogFetcher:
    """Fetch and structure product information from one or more sources."""

    def __init__(
        self,
        config: AppConfig | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self._cfg = config or get_config()
        self._llm = llm_client or get_client(config)
        self._http = httpx.Client(
            timeout=self._cfg.catalog.fetch_timeout_s,
            follow_redirects=True,
            headers={"User-Agent": "a2a-catalog-fetcher/0.1 (+https://a2a.chernov.io)"},
        )

    def fetch(self, sources: list[str]) -> tuple[CatalogEntry, list[LLMRecord]]:
        """Fetch product information from one or more sources.

        Args:
            sources: List of URLs, file paths (PDF / txt), or raw text snippets.

        Returns:
            A tuple of (CatalogEntry, list of LLMRecord for observability).
        """
        raw_texts: list[str] = []
        source_urls: list[str] = []
        llm_records: list[LLMRecord] = []

        for source in sources:
            text, url = self._load_source(source)
            raw_texts.append(text[:4000])  # truncate per source to stay within context
            if url:
                source_urls.append(url)

        combined = "\n\n---\n\n".join(raw_texts)
        excerpt = combined[:2000]

        product, record = self._extract_product(combined, source_urls)
        llm_records.append(record)

        entry = CatalogEntry(
            product=product,
            source_urls=source_urls,
            ingestion_notes=f"Fetched {len(sources)} source(s)",
            raw_text_excerpt=excerpt,
        )
        log.info("catalog_fetched", name=product.name, category=product.category, sources=len(sources))
        return entry, llm_records

    def _load_source(self, source: str) -> tuple[str, str | None]:
        """Load text from a URL, file path, or raw text."""
        if source.startswith(("http://", "https://")):
            return self._fetch_url(source), source
        p = Path(source)
        if p.exists():
            if p.suffix.lower() == ".pdf":
                return self._read_pdf(p), str(p)
            return p.read_text(encoding="utf-8", errors="replace")[:8000], str(p)
        # Treat as raw text
        return source, None

    def _fetch_url(self, url: str) -> str:
        try:
            resp = self._http.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "pdf" in content_type:
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                    f.write(resp.content)
                    return self._read_pdf(Path(f.name))
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:8000]
        except Exception as exc:
            raise CatalogError(f"Failed to fetch {url}: {exc}") from exc

    def _read_pdf(self, path: Path) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = reader.pages[: self._cfg.catalog.max_pdf_pages]
            return "\n".join(page.extract_text() or "" for page in pages)[:8000]
        except Exception as exc:
            raise CatalogError(f"Failed to read PDF {path}: {exc}") from exc

    def _extract_product(
        self, raw_text: str, source_urls: list[str]
    ) -> tuple[ProductSchema, LLMRecord]:
        context_hint = f"Sources: {', '.join(source_urls[:3])}" if source_urls else ""
        user_prompt = f"{context_hint}\n\n{raw_text[:6000]}"

        record = self._llm.complete(
            messages=[
                Message("system", _EXTRACT_SYSTEM),
                Message("user", user_prompt),
            ],
            model=self._cfg.models.judge_model,  # cheaper model for extraction
            metadata={"step": "catalog_extract"},
        )

        try:
            import json

            data: dict[str, Any] = json.loads(record.response)
            product = ProductSchema(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            log.warning("catalog_extract_fallback", error=str(exc))
            # Build a minimal product from any text we can find
            product = _minimal_product_from_text(raw_text, source_urls)

        return product, record


def _minimal_product_from_text(text: str, sources: list[str]) -> ProductSchema:
    """Fallback: build a minimal ProductSchema from raw text when LLM extraction fails."""
    name = (sources[0].split("/")[-1].replace("-", " ").title() if sources else "Unknown Product")
    return ProductSchema(
        name=name[:64],
        category="saas",
        short_description=text[:280],
        pricing_tiers=[PricingTier(name="Standard", price_usd=0.0)],
    )


# ── Pre-built catalog entries for the v0.1 experiments ──────────────────────

def saas_subscription_catalog() -> CatalogEntry:
    """Pre-built catalog for the B2B SaaS observability tier experiment."""
    return CatalogEntry(
        product=ProductSchema(
            name="ObserveOps Pro",
            category="saas",
            short_description=(
                "Production-grade observability platform: metrics, logs, traces, and "
                "AI-powered anomaly detection for engineering teams shipping at scale."
            ),
            features=[
                "Unlimited metrics ingestion up to 100k series",
                "14-day log retention",
                "Distributed tracing with <1ms overhead",
                "AI anomaly detection with root-cause hints",
                "Slack, PagerDuty, Opsgenie integrations",
                "SOC 2 Type II certified",
                "99.9% SLA with credits",
                "SSO / SAML 2.0",
            ],
            pricing_tiers=[
                PricingTier(
                    name="Starter",
                    price_usd=49.0,
                    billing_period="monthly",
                    features=["Up to 10 hosts", "7-day retention", "Community support"],
                    is_negotiable=False,
                ),
                PricingTier(
                    name="Pro",
                    price_usd=299.0,
                    billing_period="monthly",
                    features=["Up to 50 hosts", "30-day retention", "Email support", "AI anomaly detection"],
                    is_negotiable=True,
                ),
                PricingTier(
                    name="Enterprise",
                    price_usd=None,
                    billing_period="annual",
                    features=["Unlimited hosts", "Custom retention", "Dedicated CSM", "SLA credits"],
                    is_negotiable=True,
                ),
            ],
            availability="available",
            trust_signals=["SOC 2 Type II", "GDPR compliant", "4.8/5 on G2 (1,200+ reviews)"],
            terms_url="https://observeops.example/terms",
            api_endpoint="https://api.observeops.example/v1/checkout",
        ),
        source_urls=["https://observeops.example/pricing"],
        ingestion_notes="Pre-built v0.1 fixture — B2B SaaS observability tier.",
    )


def physical_good_catalog() -> CatalogEntry:
    """Pre-built catalog for the physical good (wine subscription) experiment."""
    return CatalogEntry(
        product=ProductSchema(
            name="Terroir Direct — Single-Bottle Wine Subscription",
            category="subscription",
            short_description=(
                "Monthly delivery of one hand-selected bottle from independent European vineyards. "
                "Natural, biodynamic, and minimal-intervention wines. No lock-in."
            ),
            features=[
                "One premium bottle per month (75cl)",
                "Curated by a certified sommelier",
                "Detailed tasting notes and food pairings included",
                "Free shipping above $60 basket",
                "Pause or cancel any time",
                "Quarterly cellar tour option",
            ],
            pricing_tiers=[
                PricingTier(
                    name="Essentials",
                    price_usd=35.0,
                    billing_period="monthly",
                    features=["1 bottle/month", "Tasting notes", "Community forum access"],
                    is_negotiable=False,
                ),
                PricingTier(
                    name="Collector",
                    price_usd=75.0,
                    billing_period="monthly",
                    features=["1 premium bottle/month", "Sommelier chat", "Early access to allocations"],
                    is_negotiable=True,
                ),
            ],
            availability="available",
            shipping="Delivered within 3–5 business days (EU/UK). Signature required.",
            return_policy="Full refund within 14 days if bottle is damaged or corked.",
            trust_signals=["Certified B Corporation", "4.9/5 on Trustpilot (3,400+ reviews)", "Featured in Decanter"],
            terms_url="https://terroirdirect.example/terms",
        ),
        source_urls=["https://terroirdirect.example/subscribe"],
        ingestion_notes="Pre-built v0.1 fixture — physical good wine subscription.",
    )
