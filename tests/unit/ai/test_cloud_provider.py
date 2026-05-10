"""
Unit tests for CloudLLMProvider.

Tests provider initialization, HTTP client configuration, API call
behaviour, and LLMAbstraction integration — all without network access.
"""

import os
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest

from src.ai.providers.base_provider import EffortEstimate, SemanticAnalysis
from src.core.models import Priority, Task, TaskStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(name: str = "Test task") -> Task:
    return Task(
        id="t1",
        name=name,
        description="A test task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=2.0,
    )


def _mock_config(
    max_tokens: int = 4096,
    temperature: float = 0.1,
) -> Mock:
    cfg = Mock()
    cfg.ai.max_tokens = max_tokens
    cfg.ai.temperature = temperature
    return cfg


def _mock_http_response(content: str) -> Mock:
    """Build a fake httpx.Response that returns an OpenAI-style payload."""
    resp = Mock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = {"choices": [{"message": {"content": content}}]}
    resp.raise_for_status = Mock()
    return resp


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCloudProviderInit:
    """Test CloudLLMProvider construction."""

    def test_stores_model_url_and_creates_client(self) -> None:
        """Provider must store model name and configure base_url on client."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            p = CloudLLMProvider(
                model="vendor/my-model",
                api_key="fw_test123",
                url="https://api.example.com/v1",
            )

        assert p.model == "vendor/my-model"
        assert p.base_url == "https://api.example.com/v1"

    def test_reads_max_tokens_and_temperature_from_config(self) -> None:
        """Provider must pull max_tokens and temperature from global config."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config(max_tokens=2048, temperature=0.3)
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            p = CloudLLMProvider(model="m", api_key="k", url="https://x.com/v1")

        assert p.max_tokens == 2048
        assert p.temperature == 0.3

    def test_bearer_token_set_in_client_headers(self) -> None:
        """Authorization header must carry the provided API key as Bearer."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            p = CloudLLMProvider(
                model="m", api_key="fw_secret_key", url="https://x.com/v1"
            )

        auth_header = dict(p.client.headers).get("authorization", "")
        assert auth_header == "Bearer fw_secret_key"

    def test_empty_url_raises_value_error(self) -> None:
        """CloudLLMProvider must reject an empty URL immediately."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            with pytest.raises(ValueError, match="cloud_url"):
                CloudLLMProvider(model="m", api_key="k", url="")

    def test_empty_api_key_raises_value_error(self) -> None:
        """CloudLLMProvider must reject an empty api_key immediately."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            with pytest.raises(ValueError, match="api_key"):
                CloudLLMProvider(model="m", api_key="", url="https://x.com/v1")

    def test_empty_model_raises_value_error(self) -> None:
        """CloudLLMProvider must reject an empty model name."""
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            with pytest.raises(ValueError, match="model"):
                CloudLLMProvider(model="", api_key="k", url="https://x.com/v1")


# ---------------------------------------------------------------------------
# _call_cloud_llm (internal HTTP call)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCloudProviderHTTPCall:
    """Test the internal _call_cloud_llm method."""

    @pytest.fixture
    def provider(self) -> Any:
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            return CloudLLMProvider(
                model="vendor/model",
                api_key="fw_key",
                url="https://api.example.com/v1",
            )

    @pytest.mark.asyncio
    async def test_posts_to_chat_completions_endpoint(self, provider: Any) -> None:
        """Must POST to /chat/completions with correct body."""
        fake_resp = _mock_http_response('{"task_intent": "test"}')
        provider.client.post = AsyncMock(return_value=fake_resp)

        await provider._call_cloud_llm("hello")

        provider.client.post.assert_called_once()
        call_kwargs = provider.client.post.call_args
        assert call_kwargs[0][0] == "/chat/completions"
        body = call_kwargs[1]["json"]
        assert body["model"] == "vendor/model"
        assert body["stream"] is False
        assert isinstance(body["messages"], list)

    @pytest.mark.asyncio
    async def test_returns_message_content(self, provider: Any) -> None:
        """Must return the text from choices[0].message.content."""
        provider.client.post = AsyncMock(
            return_value=_mock_http_response("hello world")
        )
        result = await provider._call_cloud_llm("prompt")
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_raises_on_http_error(self, provider: Any) -> None:
        """Must raise Exception (not fall back to Ollama) on 4xx/5xx."""
        err_resp = Mock(spec=httpx.Response)
        err_resp.status_code = 401
        err_resp.text = "Unauthorized"
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401", request=Mock(), response=err_resp
        )
        provider.client.post = AsyncMock(return_value=err_resp)

        with pytest.raises(Exception, match="Cloud LLM API error"):
            await provider._call_cloud_llm("prompt")

    @pytest.mark.asyncio
    async def test_strips_leading_think_blocks(self, provider: Any) -> None:
        """Must strip <think>...</think> prefix from reasoning models."""
        raw = "<think>internal reasoning</think>\n{}"
        provider.client.post = AsyncMock(return_value=_mock_http_response(raw))
        result = await provider._call_cloud_llm("prompt")
        assert "<think>" not in result
        assert result == "{}"

    @pytest.mark.asyncio
    async def test_uses_config_max_tokens_when_none_passed(self, provider: Any) -> None:
        """Default max_tokens must come from config, not hardcoded."""
        provider.max_tokens = 512
        fake_resp = _mock_http_response("ok")
        provider.client.post = AsyncMock(return_value=fake_resp)

        await provider._call_cloud_llm("prompt")

        body = provider.client.post.call_args[1]["json"]
        assert body["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_does_not_fall_back_to_ollama_on_404(self, provider: Any) -> None:
        """Cloud provider must NOT try Ollama native format on 404."""
        err_resp = Mock(spec=httpx.Response)
        err_resp.status_code = 404
        err_resp.text = "Not Found"
        err_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=err_resp
        )
        provider.client.post = AsyncMock(return_value=err_resp)

        with pytest.raises(Exception, match="Cloud LLM API error"):
            await provider._call_cloud_llm("prompt")

        # Must NOT make a second call (Ollama fallback would)
        assert provider.client.post.call_count == 1


# ---------------------------------------------------------------------------
# High-level methods delegate through _call_cloud_llm
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCloudProviderMethods:
    """Verify analyze_task / infer_dependencies use cloud call correctly."""

    @pytest.fixture
    def provider(self) -> Any:
        from src.ai.providers.cloud_provider import CloudLLMProvider

        cfg = _mock_config()
        with patch("src.config.marcus_config.get_config", return_value=cfg):
            return CloudLLMProvider(model="m", api_key="k", url="https://x.com/v1")

    @pytest.mark.asyncio
    async def test_analyze_task_returns_semantic_analysis(self, provider: Any) -> None:
        """analyze_task must return SemanticAnalysis even on parse failure."""
        provider.client.post = AsyncMock(
            return_value=_mock_http_response(
                '{"task_intent":"implement","semantic_dependencies":[],'
                '"risk_factors":[],"suggestions":[],"confidence":0.8,'
                '"reasoning":"ok","risk_assessment":{}}'
            )
        )
        result = await provider.analyze_task(_make_task(), {})
        assert isinstance(result, SemanticAnalysis)
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_analyze_task_returns_fallback_on_api_error(
        self, provider: Any
    ) -> None:
        """analyze_task must return a safe fallback when the API call fails."""
        provider.client.post = AsyncMock(side_effect=Exception("network error"))
        result = await provider.analyze_task(_make_task(), {})
        assert isinstance(result, SemanticAnalysis)
        assert result.confidence < 0.5


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAISettingsCloudValidation:
    """Validate MarcusConfig rejects bad cloud configurations."""

    def _make_config(self, **ai_overrides: Any) -> Any:
        from src.config.marcus_config import AISettings, MarcusConfig

        ai = AISettings(provider="cloud", **ai_overrides)
        cfg = MarcusConfig(ai=ai)
        return cfg

    def test_cloud_provider_requires_api_key(self) -> None:
        """Validation must fail when cloud_api_key is missing."""
        cfg = self._make_config(cloud_url="https://x.com/v1", model="vendor/model")
        with pytest.raises(ValueError, match="cloud_api_key"):
            cfg.validate()

    def test_cloud_provider_requires_url(self) -> None:
        """Validation must fail when cloud_url is missing."""
        cfg = self._make_config(cloud_api_key="fw_abc123", model="vendor/model")
        with pytest.raises(ValueError, match="cloud_url"):
            cfg.validate()

    def test_cloud_provider_valid_config_passes(self) -> None:
        """Validation must pass when both cloud_api_key and cloud_url are set."""
        cfg = self._make_config(
            cloud_api_key="fw_abc123",
            cloud_url="https://api.example.com/v1",
            model="accounts/fireworks/models/qwen2p5-coder-7b-instruct",
        )
        cfg.validate()  # Must not raise

    def test_cloud_provider_env_var_key_satisfies_validation(self) -> None:
        """Validation must pass when MARCUS_CLOUD_LLM_KEY is set even if
        cloud_api_key is absent from config (P2: honor env vars in validate)."""
        import os

        cfg = self._make_config(
            cloud_url="https://api.example.com/v1",
            model="vendor/model",
        )
        old = os.environ.pop("MARCUS_CLOUD_LLM_KEY", None)
        try:
            os.environ["MARCUS_CLOUD_LLM_KEY"] = "fw_from_env"
            cfg.validate()  # Must not raise
        finally:
            if old is not None:
                os.environ["MARCUS_CLOUD_LLM_KEY"] = old
            else:
                os.environ.pop("MARCUS_CLOUD_LLM_KEY", None)

    def test_cloud_provider_env_var_url_satisfies_validation(self) -> None:
        """Validation must pass when MARCUS_CLOUD_LLM_URL is set even if
        cloud_url is absent from config (P2: honor env vars in validate)."""
        import os

        cfg = self._make_config(
            cloud_api_key="fw_abc123",
            model="vendor/model",
        )
        old = os.environ.pop("MARCUS_CLOUD_LLM_URL", None)
        try:
            os.environ["MARCUS_CLOUD_LLM_URL"] = "https://env.example.com/v1"
            cfg.validate()  # Must not raise
        finally:
            if old is not None:
                os.environ["MARCUS_CLOUD_LLM_URL"] = old
            else:
                os.environ.pop("MARCUS_CLOUD_LLM_URL", None)

    def test_cloud_provider_rejects_anthropic_model_name(self) -> None:
        """Validation must fail when model looks like an Anthropic model
        (P2: Anthropic default claude-* names break non-Anthropic endpoints)."""
        cfg = self._make_config(
            cloud_api_key="fw_abc123",
            cloud_url="https://api.example.com/v1",
            model="claude-3-haiku-20240307",
        )
        with pytest.raises(ValueError, match="Anthropic model name"):
            cfg.validate()

    def test_cloud_provider_default_model_triggers_anthropic_warning(
        self,
    ) -> None:
        """The AISettings default model 'claude-3-haiku-20240307' must be
        rejected when provider='cloud' so users get a clear error instead of
        a cryptic API failure from the cloud endpoint."""
        from src.config.marcus_config import AISettings, MarcusConfig

        # Default model is claude-3-haiku-20240307 — must be caught
        ai = AISettings(
            provider="cloud",
            cloud_api_key="fw_abc123",
            cloud_url="https://api.example.com/v1",
        )
        cfg = MarcusConfig(ai=ai)
        with pytest.raises(ValueError, match="Anthropic model name"):
            cfg.validate()


# ---------------------------------------------------------------------------
# LLMAbstraction integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLLMAbstractionCloudProvider:
    """Verify LLMAbstraction initialises cloud provider from config."""

    @pytest.fixture
    def clean_env(self) -> Any:
        keys = [
            "CLAUDE_API_KEY",
            "OPENAI_API_KEY",
            "MARCUS_LOCAL_LLM_PATH",
            "MARCUS_CLOUD_LLM_KEY",
            "MARCUS_CLOUD_LLM_URL",
        ]
        backup = {k: os.environ.pop(k) for k in keys if k in os.environ}
        yield
        os.environ.update(backup)

    def test_cloud_provider_initialised_from_config(self, clean_env: Any) -> None:
        """When provider='cloud' is configured, only the cloud provider starts."""
        from src.ai.providers.llm_abstraction import LLMAbstraction

        mock_cfg = Mock()
        mock_cfg.ai.provider = "cloud"
        mock_cfg.ai.cloud_api_key = "fw_test_key"
        mock_cfg.ai.cloud_url = "https://api.example.com/v1"
        mock_cfg.ai.model = "vendor/model"
        mock_cfg.ai.max_tokens = 4096
        mock_cfg.ai.temperature = 0.1
        mock_cfg.ai.anthropic_api_key = None
        mock_cfg.ai.openai_api_key = None
        mock_cfg.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_cfg):
            llm = LLMAbstraction()
            llm._initialize_providers()

        assert "cloud" in llm.providers
        assert "anthropic" not in llm.providers
        assert "openai" not in llm.providers
        assert "local" not in llm.providers
        assert llm.current_provider == "cloud"

    def test_cloud_provider_picks_up_env_vars(self, clean_env: Any) -> None:
        """cloud_api_key and cloud_url can be supplied via env vars."""
        from src.ai.providers.llm_abstraction import LLMAbstraction

        os.environ["MARCUS_CLOUD_LLM_KEY"] = "fw_from_env"
        os.environ["MARCUS_CLOUD_LLM_URL"] = "https://env.example.com/v1"

        mock_cfg = Mock()
        mock_cfg.ai.provider = "cloud"
        mock_cfg.ai.cloud_api_key = None  # no config key
        mock_cfg.ai.cloud_url = None  # no config url
        mock_cfg.ai.model = "vendor/model"
        mock_cfg.ai.max_tokens = 4096
        mock_cfg.ai.temperature = 0.1
        mock_cfg.ai.anthropic_api_key = None
        mock_cfg.ai.openai_api_key = None
        mock_cfg.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_cfg):
            llm = LLMAbstraction()
            llm._initialize_providers()

        assert "cloud" in llm.providers
