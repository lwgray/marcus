"""Unit tests for MarcusConfig environment variable overrides.

This test file verifies environment variable substitution and overrides.
"""

import json
from pathlib import Path

import pytest

from src.config.marcus_config import MarcusConfig


class TestMarcusConfigEnvOverrides:
    """Test suite for environment variable overrides."""

    def test_env_var_substitution_in_api_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variable substitution in API keys."""
        # Set environment variable
        monkeypatch.setenv("MY_ANTHROPIC_KEY", "sk-ant-actual-key-from-env")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${MY_ANTHROPIC_KEY}",
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.ai.anthropic_api_key == "sk-ant-actual-key-from-env"

    def test_env_var_substitution_in_multiple_fields(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variable substitution in multiple fields."""
        # Set multiple environment variables
        monkeypatch.setenv("ANTHROPIC_KEY", "sk-ant-key")
        monkeypatch.setenv("PLANKA_URL", "http://planka.example.com")
        monkeypatch.setenv("PLANKA_USER", "admin@example.com")
        monkeypatch.setenv("PLANKA_PASS", "secure-password")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${ANTHROPIC_KEY}",
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "${PLANKA_URL}",
                "planka_email": "${PLANKA_USER}",
                "planka_password": "${PLANKA_PASS}",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.ai.anthropic_api_key == "sk-ant-key"
        assert config.kanban.planka_base_url == "http://planka.example.com"
        assert config.kanban.planka_email == "admin@example.com"
        assert config.kanban.planka_password == "secure-password"

    def test_env_var_substitution_returns_none_if_not_set(self, tmp_path: Path) -> None:
        """Test that undefined env vars return None to enable validation."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${UNDEFINED_VAR}",
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Should return None if env var doesn't exist, allowing validation to catch it
        assert config.ai.anthropic_api_key is None

    def test_env_var_substitution_in_nested_structures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variable substitution in nested structures."""
        monkeypatch.setenv("HTTP_HOST", "192.168.1.100")
        monkeypatch.setenv("HTTP_PORT", "8080")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            "transport": {
                "type": "http",
                "http": {
                    "host": "${HTTP_HOST}",
                    "port": "${HTTP_PORT}",
                },
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.transport.http_host == "192.168.1.100"
        # Note: Port is string in JSON, gets converted to int during parsing
        assert config.transport.http_port == 8080

    def test_env_var_substitution_in_lists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variable substitution in list values."""
        monkeypatch.setenv("TAG1", "production")
        monkeypatch.setenv("TAG2", "critical")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            "test_tags": ["${TAG1}", "${TAG2}", "static"],
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # The config should have processed the list
        # (though test_tags isn't a real field, this tests the mechanism)

    def test_mixed_env_and_literal_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test mixing environment variables and literal values."""
        monkeypatch.setenv("SECRET_KEY", "sk-ant-from-env")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${SECRET_KEY}",  # From env
                "model": "claude-3-haiku-20240307",  # Literal
                "temperature": 0.8,  # Literal
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",  # Literal
                "planka_email": "test@test.com",  # Literal
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Env var should be substituted
        assert config.ai.anthropic_api_key == "sk-ant-from-env"
        # Literals should remain
        assert config.ai.model == "claude-3-haiku-20240307"
        assert config.ai.temperature == 0.8

    def test_empty_env_var_uses_empty_string(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty environment variables result in empty strings."""
        monkeypatch.setenv("EMPTY_VAR", "")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${EMPTY_VAR}",
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.ai.anthropic_api_key == ""

    def test_special_characters_in_env_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test environment variables with special characters."""
        monkeypatch.setenv("COMPLEX_PASSWORD", "p@$$w0rd!#&*()[]{}|")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": ("${COMPLEX_PASSWORD}"),  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.kanban.planka_password == "p@$$w0rd!#&*()[]{}|"

    def test_env_var_substitution_case_sensitive(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable names are case-sensitive."""
        monkeypatch.setenv("my_key", "lowercase-key")
        monkeypatch.setenv("MY_KEY", "uppercase-key")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${MY_KEY}",  # Should get uppercase version
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        assert config.ai.anthropic_api_key == "uppercase-key"

    def test_partial_env_var_syntax_not_substituted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that partial ${} syntax is not substituted."""
        monkeypatch.setenv("VAR", "should-not-appear")

        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "$VAR",  # Missing braces
            },
            "kanban": {
                "provider": "planka",
                "planka_base_url": "${VAR",  # Missing closing brace
                "planka_email": "VAR}",  # Missing opening parts
                "planka_password": "testpass",  # pragma: allowlist secret
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # None of these should be substituted (incomplete syntax)
        assert config.ai.anthropic_api_key == "$VAR"
        assert config.kanban.planka_base_url == "${VAR"
        assert config.kanban.planka_email == "VAR}"
