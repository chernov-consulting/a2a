"""Shared test fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from a2a.llm import LLMClient, LLMRecord, Message


@pytest.fixture
def mock_llm_record() -> LLMRecord:
    return LLMRecord(
        model="mock/test-model",
        prompt_hash="abc12345",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.0002,
        latency_ms=120.0,
        response='{"outcome": "buy", "reason": "meets requirements", "price": 299.0}',
    )


@pytest.fixture
def mock_llm_client(mock_llm_record: LLMRecord) -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.complete.return_value = mock_llm_record
    client.llm_records = [mock_llm_record]
    return client
