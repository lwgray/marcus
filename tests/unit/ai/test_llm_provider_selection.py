"""
Unit tests for LLM provider selection logic.

Tests that configured providers are respected and environment variables
don't leak through when an explicit provider is configured.
"""

import os
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.ai.providers.llm_abstraction import LLMAbstraction


class TestLLMProviderSelection:
    """Test suite for provider selection behavior"""

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before each test"""
        env_backup = {}
        keys_to_clean = [
            "CLAUDE_API_KEY",
            "OPENAI_API_KEY",
            "MARCUS_LOCAL_LLM_PATH",
            "MARCUS_LLM_PROVIDER",
        ]

        # Backup and remove
        for key in keys_to_clean:
            if key in os.environ:
                env_backup[key] = os.environ[key]
                del os.environ[key]

        yield

        # Restore
        for key, value in env_backup.items():
            os.environ[key] = value

    def test_local_provider_ignores_openai_env_var(self, clean_env):
        """
        Test that when provider='local' is configured,
        OpenAI env var doesn't cause OpenAI provider to initialize
        """
        # Set up environment with OpenAI key
        os.environ["OPENAI_API_KEY"] = "sk-fake-openai-key-for-testing"

        # Mock config to return local provider
        mock_config = Mock()
        mock_config.ai.provider = "local"
        mock_config.ai.local_model = "test-model"
        mock_config.ai.local_url = "http://localhost:11434/v1"
        mock_config.ai.local_key = "none"
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.openai_api_key = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should only have local provider
            assert "local" in llm.providers
            assert "openai" not in llm.providers
            assert "anthropic" not in llm.providers
            assert llm.current_provider == "local"

    def test_openai_provider_ignores_local_env_var(self, clean_env):
        """
        Test that when provider='openai' is configured,
        local LLM env var doesn't cause local provider to initialize
        """
        # Set up environment with local LLM path
        os.environ["MARCUS_LOCAL_LLM_PATH"] = "test-local-model"

        # Mock config to return OpenAI provider with valid key
        mock_config = Mock()
        mock_config.ai.provider = "openai"
        mock_config.ai.openai_api_key = "sk-fake-openai-key"
        mock_config.ai.model = "gpt-3.5-turbo"
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should only have OpenAI provider
            assert "openai" in llm.providers
            assert "local" not in llm.providers
            assert "anthropic" not in llm.providers

    def test_no_provider_configured_initializes_all_available(self, clean_env):
        """
        Test that when no provider is explicitly configured,
        all providers with valid credentials are initialized (backward compat)
        """
        # Set up environment with multiple keys
        os.environ["OPENAI_API_KEY"] = "sk-fake-openai-key-for-testing"
        os.environ["MARCUS_LOCAL_LLM_PATH"] = "test-model"

        # Mock config with no provider specified
        mock_config = Mock()
        mock_config.ai.provider = ""
        mock_config.ai.openai_api_key = "sk-fake-openai-key"
        mock_config.ai.local_model = "test-model"
        mock_config.ai.local_url = "http://localhost:11434/v1"
        mock_config.ai.local_key = "none"
        mock_config.ai.anthropic_api_key = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should have both providers
            assert "openai" in llm.providers
            assert "local" in llm.providers

    def test_anthropic_provider_ignores_other_env_vars(self, clean_env):
        """
        Test that when provider='anthropic' is configured,
        other provider env vars don't leak through
        """
        # Set up environment with other keys
        os.environ["OPENAI_API_KEY"] = "sk-fake-openai-key"
        os.environ["MARCUS_LOCAL_LLM_PATH"] = "test-model"

        # Mock config to return Anthropic provider
        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        mock_config.ai.anthropic_api_key = "sk-ant-fake-key-for-testing"
        mock_config.ai.model = "claude-3-haiku-20240307"
        mock_config.ai.openai_api_key = None
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should only have Anthropic provider
            assert "anthropic" in llm.providers
            assert "openai" not in llm.providers
            assert "local" not in llm.providers
            assert llm.current_provider == "anthropic"

    def test_explicit_config_overrides_env_var(self, clean_env):
        """
        Test that explicit config values override environment variables
        """
        # Set environment with one model
        os.environ["MARCUS_LOCAL_LLM_PATH"] = "env-model"

        # Mock config with different model
        mock_config = Mock()
        mock_config.ai.provider = "local"
        mock_config.ai.local_model = "config-model"
        mock_config.ai.local_url = "http://localhost:11434/v1"
        mock_config.ai.local_key = "none"
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.openai_api_key = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should use config value, not env var
            assert llm.providers["local"].model == "config-model"


@pytest.mark.unit
class TestAnthropicEnvVarIsolation:
    """Verify Marcus never writes ANTHROPIC_API_KEY into os.environ.

    If ANTHROPIC_API_KEY leaks into Marcus's env, every ``claude``
    subprocess Marcus spawns (Epictetus, project creator, workers,
    monitor) inherits it and switches from Claude Code subscription
    billing to API billing. Marcus must read keys from config or
    ``CLAUDE_API_KEY``, then pass them to providers explicitly.
    """

    @pytest.fixture
    def clean_anthropic_env(self):
        """Snapshot and clear ANTHROPIC_API_KEY/CLAUDE_API_KEY before each test."""
        backup = {}
        for key in ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"):
            if key in os.environ:
                backup[key] = os.environ[key]
                del os.environ[key]
        yield
        for key in ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"):
            if key in os.environ:
                del os.environ[key]
        for key, value in backup.items():
            os.environ[key] = value

    def test_anthropic_init_does_not_set_anthropic_api_key(
        self, clean_anthropic_env: None
    ) -> None:
        """Initializing the Anthropic provider must NOT set ANTHROPIC_API_KEY in env."""
        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        mock_config.ai.anthropic_api_key = "sk-ant-fake-key-for-testing-purposes"
        mock_config.ai.model = "claude-3-haiku-20240307"
        mock_config.ai.openai_api_key = None
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

        assert "ANTHROPIC_API_KEY" not in os.environ, (
            "Marcus must not pollute os.environ with ANTHROPIC_API_KEY — "
            "it would force Claude Code subprocesses to bill the API instead "
            "of using the user's subscription."
        )

    def test_claude_api_key_env_var_is_read(self, clean_anthropic_env: None) -> None:
        """When config has no key, Marcus must read CLAUDE_API_KEY from env."""
        os.environ["CLAUDE_API_KEY"] = "sk-ant-fake-claude-key-for-testing-purposes"

        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.model = "claude-3-haiku-20240307"
        mock_config.ai.openai_api_key = None
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

        assert "anthropic" in llm.providers, (
            "Marcus must initialize the Anthropic provider when CLAUDE_API_KEY "
            "is set in the environment."
        )
        # And the leak-prevention invariant still holds
        assert "ANTHROPIC_API_KEY" not in os.environ

    def test_anthropic_api_key_env_var_is_NOT_read(
        self, clean_anthropic_env: None
    ) -> None:
        """ANTHROPIC_API_KEY must be ignored even when set in env.

        With only ANTHROPIC_API_KEY in env (no CLAUDE_API_KEY, no config key),
        the Anthropic provider must NOT initialize. ``_initialize_providers``
        raises ``RuntimeError`` when the configured provider failed to init
        (Marcus #531), which is the correct outcome — that proves the env
        var was ignored.
        """
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-this-should-be-ignored-completely"

        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.model = "claude-3-haiku-20240307"
        mock_config.ai.openai_api_key = None
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            with pytest.raises(RuntimeError, match="ai.provider='anthropic' is set"):
                llm._initialize_providers()

        # Even after the failed initialization attempt, the providers dict
        # must NOT contain anthropic — that's the bright-line invariant.
        assert "anthropic" not in llm.providers, (
            "Marcus must not fall back to ANTHROPIC_API_KEY — that env var "
            "belongs to Claude Code's subscription auth."
        )


class TestProviderLockdownRegression:
    """Regression: real OpenAI key in config must not leak past
    ``provider: anthropic`` setting (Marcus #531).

    The earlier code gated only the env-var fallback by configured
    provider; the init block ran whenever
    ``config.ai.openai_api_key`` was non-empty — and Marcus's
    ``config_marcus.json`` substitutes ``${OPENAI_API_KEY}`` into
    that field, so a shell-exported OpenAI key silently joined the
    fallback chain alongside Anthropic. When Anthropic momentarily
    failed, Marcus cascaded to OpenAI and billed real tokens to the
    OpenAI key without the user knowing.

    These tests reproduce the exact leak condition (config carries
    BOTH keys; provider explicitly set to one) and assert the other
    provider stays out of ``self.providers``.
    """

    @pytest.fixture
    def env_with_real_openai_key(self):
        """Reproduce the user's environment: real openai key in env."""
        prev = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "sk-proj-s8abcdef1234567890abcdef"
        yield
        if prev is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = prev

    def test_openai_excluded_when_provider_is_anthropic(self, env_with_real_openai_key):
        """Provider=anthropic + real OpenAI key in config: no OpenAI provider."""
        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        # Reproduce config_marcus.json's substituted state: anthropic
        # AND openai keys both present.
        mock_config.ai.anthropic_api_key = "sk-ant-api03-fake-for-test-1234567890"
        mock_config.ai.openai_api_key = "sk-proj-s8abcdef1234567890abcdef"
        mock_config.ai.model = "claude-sonnet-4-6"
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()
            assert "anthropic" in llm.providers
            assert "openai" not in llm.providers, (
                "OpenAI provider must NOT initialize when provider=anthropic, "
                "even if openai_api_key is non-empty"
            )
            assert "openai" not in llm.fallback_providers

    def test_anthropic_excluded_when_provider_is_openai(self, env_with_real_openai_key):
        """Provider=openai + real Anthropic key in config: no Anthropic provider."""
        mock_config = Mock()
        mock_config.ai.provider = "openai"
        mock_config.ai.anthropic_api_key = "sk-ant-api03-fake-for-test-1234567890"
        mock_config.ai.openai_api_key = "sk-proj-s8abcdef1234567890abcdef"
        mock_config.ai.model = "gpt-4o-mini"
        mock_config.ai.local_model = None

        with patch("src.config.marcus_config.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()
            assert "openai" in llm.providers
            assert "anthropic" not in llm.providers
            assert "anthropic" not in llm.fallback_providers

    def test_hard_fail_when_configured_provider_does_not_initialize(self):
        """Refusing silent fallback: missing anthropic key + provider=anthropic raises."""
        mock_config = Mock()
        mock_config.ai.provider = "anthropic"
        # Explicitly no anthropic key but a real openai key present —
        # the earlier code would silently fall back to OpenAI.
        mock_config.ai.anthropic_api_key = None
        mock_config.ai.openai_api_key = "sk-proj-s8abcdef1234567890abcdef"
        mock_config.ai.model = "claude-sonnet-4-6"
        mock_config.ai.local_model = None

        # Clear CLAUDE_API_KEY too so the env-var fallback can't satisfy it.
        prev = os.environ.pop("CLAUDE_API_KEY", None)
        try:
            with patch("src.config.marcus_config.get_config", return_value=mock_config):
                with pytest.raises(RuntimeError, match="ai.provider='anthropic'"):
                    llm = LLMAbstraction()
                    llm._initialize_providers()
        finally:
            if prev is not None:
                os.environ["CLAUDE_API_KEY"] = prev
