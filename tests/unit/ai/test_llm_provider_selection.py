"""
Unit tests for LLM provider selection logic.

Tests that configured providers are respected and environment variables
don't leak through when an explicit provider is configured.
"""

import os
from unittest.mock import Mock, patch

import pytest

from src.ai.providers.llm_abstraction import LLMAbstraction


class TestLLMProviderSelection:
    """Test suite for provider selection behavior"""

    @pytest.fixture
    def clean_env(self):
        """Clean environment variables before each test"""
        env_backup = {}
        keys_to_clean = [
            "ANTHROPIC_API_KEY",
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
        mock_config.get.side_effect = lambda key, default=None: {
            "ai": {
                "provider": "local",
                "local_model": "test-model",
                "local_url": "http://localhost:11434/v1",
                "local_key": "none",
            },
            "ai.provider": "local",
        }.get(key, default)

        with patch("src.config.config_loader.get_config", return_value=mock_config):
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
        mock_config.get.side_effect = lambda key, default=None: {
            "ai": {
                "provider": "openai",
                "openai_api_key": "sk-fake-openai-key",
            },
            "ai.provider": "openai",
        }.get(key, default)

        with patch("src.config.config_loader.get_config", return_value=mock_config):
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
        mock_config.get.side_effect = lambda key, default=None: {
            "ai": {},
            "ai.provider": "",
        }.get(key, default)

        with patch("src.config.config_loader.get_config", return_value=mock_config):
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
        mock_config.get.side_effect = lambda key, default=None: {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "sk-ant-fake-key-for-testing",
            },
            "ai.provider": "anthropic",
        }.get(key, default)

        with patch("src.config.config_loader.get_config", return_value=mock_config):
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
        mock_config.get.side_effect = lambda key, default=None: {
            "ai": {
                "provider": "local",
                "local_model": "config-model",
                "local_url": "http://localhost:11434/v1",
                "local_key": "none",
            },
            "ai.provider": "local",
        }.get(key, default)

        with patch("src.config.config_loader.get_config", return_value=mock_config):
            llm = LLMAbstraction()
            llm._initialize_providers()

            # Should use config value, not env var
            assert llm.providers["local"].model == "config-model"
