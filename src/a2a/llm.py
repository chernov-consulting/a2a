"""Single LLM client wrapper.

Every model call in the codebase goes through ``LLMClient.complete()``.
No other module may call litellm or provider SDKs directly.

Each call returns an ``LLMRecord`` capturing the full observability envelope:
tokens, latency, cost, model, a SHA-256 hash of the prompt, and the raw response.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

import litellm
import structlog

from a2a.config import AppConfig, get_config
from a2a.exceptions import LLMError

log = structlog.get_logger(__name__)

# Suppress litellm's verbose startup banner and success logging
litellm.suppress_debug_info = True
litellm.success_callback = []
litellm.failure_callback = []


@dataclass(frozen=True)
class Message:
    """A single chat message."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMRecord:
    """Full observability record for a single LLM call."""

    model: str
    prompt_hash: str  # SHA-256 hex of the serialised messages
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: float
    response: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tokens_total(self) -> int:
        return self.tokens_in + self.tokens_out

    def as_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "prompt_hash": self.prompt_hash,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "tokens_total": self.tokens_total,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "response_preview": self.response[:200],
            "metadata": self.metadata,
        }


class LLMClient:
    """Thin, instrumented litellm wrapper.

    Usage::

        client = LLMClient(config)
        record = client.complete(
            model="openai/gpt-4o",
            messages=[Message("user", "Hello")],
            metadata={"step": "buyer_plan"},
        )
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        self._cfg = config or get_config()
        self._set_api_keys()

    def _set_api_keys(self) -> None:
        import os

        if self._cfg.openai_api_key:
            os.environ.setdefault("OPENAI_API_KEY", self._cfg.openai_api_key)
        if self._cfg.anthropic_api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", self._cfg.anthropic_api_key)
        if self._cfg.google_api_key:
            os.environ.setdefault("GOOGLE_API_KEY", self._cfg.google_api_key)
        if self._cfg.openrouter_api_key:
            os.environ.setdefault("OPENROUTER_API_KEY", self._cfg.openrouter_api_key)

    @staticmethod
    def _hash_messages(messages: list[Message]) -> str:
        payload = "|".join(f"{m.role}:{m.content}" for m in messages)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def complete(
        self,
        messages: list[Message],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LLMRecord:
        """Call the LLM and return a fully-instrumented record."""
        resolved_model = model or self._cfg.models.buyer_model
        resolved_temp = temperature if temperature is not None else self._cfg.models.temperature
        resolved_max = max_tokens or self._cfg.models.max_tokens
        prompt_hash = self._hash_messages(messages)
        raw_messages = [{"role": m.role, "content": m.content} for m in messages]

        log.debug(
            "llm_call",
            model=resolved_model,
            prompt_hash=prompt_hash,
            n_messages=len(messages),
        )

        t0 = time.perf_counter()
        try:
            response = litellm.completion(
                model=resolved_model,
                messages=raw_messages,
                temperature=resolved_temp,
                max_tokens=resolved_max,
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            log.error(
                "llm_call_failed",
                model=resolved_model,
                prompt_hash=prompt_hash,
                latency_ms=round(latency_ms, 1),
                error=str(exc),
            )
            raise LLMError(f"LLM call failed ({resolved_model}): {exc}") from exc

        latency_ms = (time.perf_counter() - t0) * 1000
        usage = response.usage  # type: ignore[union-attr]
        tokens_in = getattr(usage, "prompt_tokens", 0) or 0
        tokens_out = getattr(usage, "completion_tokens", 0) or 0

        try:
            cost_usd = litellm.completion_cost(completion_response=response)
        except Exception:
            cost_usd = 0.0

        text = response.choices[0].message.content or ""  # type: ignore[union-attr]

        record = LLMRecord(
            model=resolved_model,
            prompt_hash=prompt_hash,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=round(latency_ms, 1),
            response=text,
            metadata=metadata or {},
        )

        log.info(
            "llm_call_complete",
            model=resolved_model,
            prompt_hash=prompt_hash,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=round(cost_usd, 6),
            latency_ms=round(latency_ms, 1),
        )
        return record


_default_client: LLMClient | None = None


def get_client(config: AppConfig | None = None) -> LLMClient:
    """Return (or create) the default process-level LLM client."""
    global _default_client
    if _default_client is None or config is not None:
        _default_client = LLMClient(config)
    return _default_client
