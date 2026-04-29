"""Tests for the LLM wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from a2a.llm import LLMClient, LLMRecord, Message, get_client
from a2a.config import AppConfig
from a2a.exceptions import LLMError


def _make_mock_response(content: str = "hello") -> MagicMock:
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = content
    resp.usage.prompt_tokens = 10
    resp.usage.completion_tokens = 5
    return resp


def test_llm_record_tokens_total() -> None:
    record = LLMRecord(
        model="test",
        prompt_hash="abc",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.001,
        latency_ms=100.0,
        response="test",
    )
    assert record.tokens_total == 150


def test_llm_record_as_dict() -> None:
    record = LLMRecord(
        model="test/model",
        prompt_hash="abc123",
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.001,
        latency_ms=100.0,
        response="hello world",
    )
    d = record.as_dict()
    assert d["model"] == "test/model"
    assert d["tokens_total"] == 150
    assert "response_preview" in d


def test_hash_messages_deterministic() -> None:
    msgs = [Message("user", "hello"), Message("assistant", "world")]
    h1 = LLMClient._hash_messages(msgs)
    h2 = LLMClient._hash_messages(msgs)
    assert h1 == h2
    assert len(h1) == 16


def test_hash_messages_different_for_different_content() -> None:
    msgs1 = [Message("user", "hello")]
    msgs2 = [Message("user", "goodbye")]
    assert LLMClient._hash_messages(msgs1) != LLMClient._hash_messages(msgs2)


@patch("a2a.llm.litellm")
def test_complete_success(mock_litellm: MagicMock) -> None:
    mock_litellm.completion.return_value = _make_mock_response("test response")
    mock_litellm.completion_cost.return_value = 0.0001
    mock_litellm.suppress_debug_info = True
    mock_litellm.success_callback = []
    mock_litellm.failure_callback = []

    cfg = AppConfig(openai_api_key="sk-test")
    client = LLMClient(cfg)
    record = client.complete(
        messages=[Message("user", "hello")],
        model="openai/gpt-4o-mini",
    )
    assert record.response == "test response"
    assert record.tokens_in == 10
    assert record.tokens_out == 5
    assert record.cost_usd == 0.0001


@patch("a2a.llm.litellm")
def test_complete_raises_llm_error_on_exception(mock_litellm: MagicMock) -> None:
    mock_litellm.completion.side_effect = RuntimeError("network error")
    mock_litellm.suppress_debug_info = True
    mock_litellm.success_callback = []
    mock_litellm.failure_callback = []

    cfg = AppConfig(openai_api_key="sk-test")
    client = LLMClient(cfg)
    with pytest.raises(LLMError, match="LLM call failed"):
        client.complete(messages=[Message("user", "hello")])
