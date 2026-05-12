"""
Unit tests verifying provider HTTP paths emit ``token_events`` rows.

Mocks the HTTP client on each provider so no network calls happen, then
asserts that a successful ``_call_*`` produces exactly one row in the
backing CostStore with the expected token counts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.cost_tracking.cost_recorder import (
    CostRecorder,
    PlannerContext,
    set_recorder,
)
from src.cost_tracking.cost_store import CostStore


@pytest.fixture
def store(tmp_path: Path) -> CostStore:
    """Tmp store with default seed prices."""
    s = CostStore(db_path=tmp_path / "costs.db")
    s.load_seed_prices()
    return s


@pytest.fixture
def recorder(store: CostStore) -> CostRecorder:
    """Bind a fresh enabled recorder to the module singleton."""
    rec = CostRecorder(store=store, enabled=True)
    set_recorder(rec)
    yield rec
    # Reset for downstream tests
    set_recorder(None)


def _mock_http_response(json_payload: dict[str, Any]) -> MagicMock:
    """Build a MagicMock that mimics httpx.Response.json() + raise_for_status()."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=json_payload)
    resp.status_code = 200
    return resp


class TestAnthropicProviderRecords:
    """anthropic_provider._call_claude must emit one event with cache fields."""

    @pytest.mark.asyncio
    async def test_call_claude_records_event(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """Successful Claude call writes one row with all four token fields."""
        from src.ai.providers.anthropic_provider import AnthropicProvider

        provider = AnthropicProvider.__new__(AnthropicProvider)
        provider.model = "claude-sonnet-4-6"
        provider.max_tokens = 100
        provider.temperature = 0.1
        provider.base_url = "https://api.anthropic.com/v1"
        provider.client = MagicMock()
        provider.client.post = AsyncMock(
            return_value=_mock_http_response(
                {
                    "id": "msg_test",
                    "model": "claude-sonnet-4-6",
                    "content": [{"text": "ok"}],
                    "usage": {
                        "input_tokens": 100,
                        "cache_creation_input_tokens": 200,
                        "cache_read_input_tokens": 400,
                        "output_tokens": 50,
                    },
                }
            )
        )

        with recorder.planner_context(
            PlannerContext(experiment_id="e1", project_id="p1")
        ):
            result = await provider._call_claude("hi", operation="parse_prd")

        assert result == "ok"
        row = store.conn.execute(
            "SELECT input_tokens, cache_creation_tokens, cache_read_tokens, "
            "output_tokens, operation, provider, request_id "
            "FROM token_events"
        ).fetchone()
        assert row == (100, 200, 400, 50, "parse_prd", "anthropic", "msg_test")


class TestLocalProviderRecords:
    """local_provider._call_local_llm must emit one event tagged 'local'."""

    @pytest.mark.asyncio
    async def test_call_local_llm_records_event(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """OpenAI-compatible response → one row with prompt_tokens / completion_tokens."""
        from src.ai.providers.local_provider import LocalLLMProvider

        provider = LocalLLMProvider.__new__(LocalLLMProvider)
        provider.model = "qwen-25-coder-q5"
        provider.max_tokens = 100
        provider.temperature = 0.1
        provider.base_url = "http://localhost:11434/v1"
        provider.client = MagicMock()
        provider.client.post = AsyncMock(
            return_value=_mock_http_response(
                {
                    "id": "cmpl_test",
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 30, "completion_tokens": 10},
                }
            )
        )

        with recorder.planner_context(
            PlannerContext(experiment_id="e2", project_id="p2")
        ):
            result = await provider._call_local_llm("hi")

        assert result == "ok"
        row = store.conn.execute(
            "SELECT input_tokens, output_tokens, provider FROM token_events"
        ).fetchone()
        assert row == (30, 10, "local")


class TestOpenAIProviderRecords:
    """openai_provider._call_openai must emit one event tagged 'openai'.

    Regression for #409 follow-up: OpenAI was the only provider
    missing this hook. Without it, every Anthropic→OpenAI fallback
    silently bypassed cost tracking — which is exactly what was
    happening on accounts without an Anthropic key, leaving the
    'planner' role entirely missing from project cost breakdowns.
    """

    @pytest.mark.asyncio
    async def test_call_openai_records_event(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """OpenAI completion writes one row with prompt/completion tokens."""
        from src.ai.providers.openai_provider import OpenAIProvider

        provider = OpenAIProvider.__new__(OpenAIProvider)
        provider.model = "gpt-3.5-turbo"
        provider.max_tokens = 100
        provider.temperature = 0.1
        provider.base_url = "https://api.openai.com/v1"
        provider.client = MagicMock()
        provider.client.post = AsyncMock(
            return_value=_mock_http_response(
                {
                    "id": "cmpl_test",
                    "model": "gpt-3.5-turbo-0125",
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 75, "completion_tokens": 40},
                }
            )
        )

        with recorder.planner_context(
            PlannerContext(experiment_id="e_oa", project_id="p_oa")
        ):
            result = await provider._call_openai([{"role": "user", "content": "hi"}])

        assert result == "ok"
        row = store.conn.execute(
            "SELECT input_tokens, output_tokens, provider, model, request_id "
            "FROM token_events"
        ).fetchone()
        assert row == (75, 40, "openai", "gpt-3.5-turbo-0125", "cmpl_test")


class TestCloudProviderRecords:
    """cloud_provider._call_cloud_llm must emit one event tagged 'cloud'."""

    @pytest.mark.asyncio
    async def test_call_cloud_llm_records_event(
        self, recorder: CostRecorder, store: CostStore
    ) -> None:
        """OpenAI-compatible response on cloud endpoint → 'cloud' provider tag."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        provider = CloudLLMProvider.__new__(CloudLLMProvider)
        provider.model = "deepseek-coder"
        provider.max_tokens = 100
        provider.temperature = 0.1
        provider.client = MagicMock()
        provider.client.post = AsyncMock(
            return_value=_mock_http_response(
                {
                    "id": "cmpl_cloud",
                    "choices": [{"message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 50, "completion_tokens": 25},
                }
            )
        )

        with recorder.planner_context(
            PlannerContext(experiment_id="e3", project_id="p3")
        ):
            result = await provider._call_cloud_llm("hi")

        assert result == "ok"
        row = store.conn.execute(
            "SELECT input_tokens, output_tokens, provider FROM token_events"
        ).fetchone()
        assert row == (50, 25, "cloud")
