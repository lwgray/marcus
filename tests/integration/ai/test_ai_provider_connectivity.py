"""
Integration tests for AI provider connectivity.

Verifies that OpenAI and Anthropic providers can authenticate,
send requests, and receive parseable responses from their APIs.

These tests require real API keys and make actual API calls.
They are skipped automatically when keys are not available.

Notes
-----
Run with: pytest tests/integration/ai/test_ai_provider_connectivity.py -m integration
"""

import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from src.ai.providers.anthropic_provider import AnthropicProvider
from src.ai.providers.base_provider import SemanticAnalysis
from src.ai.providers.openai_provider import OpenAIProvider
from src.core.models import Priority, Task, TaskStatus

# Skip conditions
has_openai_key = bool(os.getenv("OPENAI_API_KEY"))
has_anthropic_key = bool(os.getenv("ANTHROPIC_API_KEY"))


def _make_mock_config(
    provider: str,
    openai_key: str | None = None,
    anthropic_key: str | None = None,
    model: str | None = None,
) -> Mock:
    """
    Build a mock MarcusConfig for provider initialization.

    Parameters
    ----------
    provider : str
        Provider name ("openai" or "anthropic").
    openai_key : str or None
        OpenAI API key override.
    anthropic_key : str or None
        Anthropic API key override.
    model : str or None
        Model name override.

    Returns
    -------
    Mock
        Mock config object with ai attributes set.
    """
    mock = Mock()
    mock.ai.provider = provider
    mock.ai.openai_api_key = openai_key
    mock.ai.anthropic_api_key = anthropic_key
    mock.ai.model = model
    mock.ai.max_tokens = 256
    mock.ai.temperature = 0.0
    mock.ai.local_model = None
    mock.ai.local_url = None
    mock.ai.local_key = None
    return mock


def _make_test_task() -> Task:
    """
    Create a minimal Task fixture for provider tests.

    Returns
    -------
    Task
        A simple test task.
    """
    now = datetime.now(timezone.utc)
    return Task(
        id="test-connectivity-1",
        name="Add unit tests for login endpoint",
        description="Write pytest tests covering auth flow",
        priority=Priority.MEDIUM,
        status=TaskStatus.TODO,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=4.0,
        project_id="test-project",
    )


@pytest.mark.integration
class TestOpenAIProviderConnectivity:
    """Verify OpenAI provider can authenticate and get responses."""

    @pytest.fixture
    def provider(self) -> OpenAIProvider:
        """Create OpenAI provider with real API key."""
        config = _make_mock_config(
            provider="openai",
            openai_key=os.getenv("OPENAI_API_KEY"),
            model="gpt-4o-mini",
        )
        with patch("src.config.marcus_config.get_config", return_value=config):
            return OpenAIProvider()

    @pytest.mark.skipif(not has_openai_key, reason="OPENAI_API_KEY not set")
    @pytest.mark.asyncio
    async def test_complete_returns_nonempty_string(
        self, provider: OpenAIProvider
    ) -> None:
        """Test that complete() returns a non-empty string from OpenAI."""
        try:
            result = await provider.complete(
                "Reply with exactly: MARCUS_OK", max_tokens=32
            )
            assert isinstance(result, str)
            assert len(result) > 0
        except Exception as exc:
            if "429" in str(exc) or "quota" in str(exc).lower():
                pytest.skip("OpenAI quota exhausted")
            raise
        finally:
            await provider.close()

    @pytest.mark.skipif(not has_openai_key, reason="OPENAI_API_KEY not set")
    @pytest.mark.asyncio
    async def test_analyze_task_returns_semantic_analysis(
        self, provider: OpenAIProvider
    ) -> None:
        """Test that analyze_task() returns a valid SemanticAnalysis."""
        task = _make_test_task()
        context = {"project_type": "web_api", "tech_stack": ["Python"]}

        try:
            result = await provider.analyze_task(task, context)

            assert isinstance(result, SemanticAnalysis)
            assert isinstance(result.task_intent, str)
            assert len(result.task_intent) > 0
            assert 0.0 <= result.confidence <= 1.0
            # Fallback returns confidence=0.1 and
            # risk_factors=["ai_analysis_failed"]. Detect it so we
            # don't false-pass when the API is unreachable.
            if result.confidence <= 0.1 and "ai_analysis_failed" in result.risk_factors:
                pytest.skip("OpenAI API unreachable (quota or connectivity)")
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_invalid_key_raises_error(self) -> None:
        """Test that an invalid API key produces a clear error."""
        config = _make_mock_config(
            provider="openai",
            openai_key="sk-invalid-key-for-testing",
            model="gpt-4o-mini",
        )
        with patch("src.config.marcus_config.get_config", return_value=config):
            provider = OpenAIProvider()

        try:
            with pytest.raises(Exception, match="OpenAI API"):
                await provider.complete("test", max_tokens=8)
        finally:
            await provider.close()


@pytest.mark.integration
class TestAnthropicProviderConnectivity:
    """Verify Anthropic provider can authenticate and get responses."""

    @pytest.fixture
    def provider(self) -> AnthropicProvider:
        """Create Anthropic provider with real API key."""
        config = _make_mock_config(
            provider="anthropic",
            anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
            model="claude-3-haiku-20240307",
        )
        with patch("src.config.marcus_config.get_config", return_value=config):
            return AnthropicProvider()

    @pytest.mark.skipif(
        not has_anthropic_key,
        reason="ANTHROPIC_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_complete_returns_nonempty_string(
        self, provider: AnthropicProvider
    ) -> None:
        """Test that complete() returns a non-empty string from Anthropic."""
        try:
            result = await provider.complete(
                "Reply with exactly: MARCUS_OK", max_tokens=32
            )
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            await provider.close()

    @pytest.mark.skipif(
        not has_anthropic_key,
        reason="ANTHROPIC_API_KEY not set",
    )
    @pytest.mark.asyncio
    async def test_analyze_task_returns_semantic_analysis(
        self, provider: AnthropicProvider
    ) -> None:
        """Test that analyze_task() returns a valid SemanticAnalysis."""
        task = _make_test_task()
        context = {"project_type": "web_api", "tech_stack": ["Python"]}

        try:
            result = await provider.analyze_task(task, context)

            assert isinstance(result, SemanticAnalysis)
            assert isinstance(result.task_intent, str)
            assert len(result.task_intent) > 0
            assert 0.0 <= result.confidence <= 1.0
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_invalid_key_raises_error(self) -> None:
        """Test that an invalid API key produces a clear error."""
        config = _make_mock_config(
            provider="anthropic",
            anthropic_key="sk-ant-invalid-key-for-testing",
            model="claude-3-haiku-20240307",
        )
        with patch("src.config.marcus_config.get_config", return_value=config):
            provider = AnthropicProvider()

        try:
            with pytest.raises(Exception, match="Claude API"):
                await provider.complete("test", max_tokens=8)
        finally:
            await provider.close()
