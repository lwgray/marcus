"""Unit tests for MarcusConfig validation.

This test file verifies the validation logic in MarcusConfig.
"""

import json
from pathlib import Path

import pytest

from src.config.marcus_config import AISettings, KanbanSettings, MarcusConfig


class TestMarcusConfigValidation:
    """Test suite for MarcusConfig validation."""

    def test_validation_passes_with_valid_anthropic_config(
        self, tmp_path: Path
    ) -> None:
        """Test that validation passes with valid Anthropic configuration."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test-key"},
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
        # Should not raise
        config.validate()

    def test_validation_fails_missing_anthropic_key(self, tmp_path: Path) -> None:
        """Test that validation fails when Anthropic key is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic"},  # Missing anthropic_api_key
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

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "anthropic_api_key is not set" in str(exc_info.value)

    def test_validation_fails_missing_openai_key(self, tmp_path: Path) -> None:
        """Test that validation fails when OpenAI key is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "openai"},  # Missing openai_api_key
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

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "openai_api_key is not set" in str(exc_info.value)

    def test_validation_fails_invalid_temperature(self, tmp_path: Path) -> None:
        """Test that validation fails with invalid temperature."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "sk-ant-test",
                "temperature": 1.5,  # Invalid: > 1.0
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

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "temperature must be between 0.0 and 1.0" in str(exc_info.value)

    def test_validation_fails_missing_planka_url(self, tmp_path: Path) -> None:
        """Test that validation fails when Planka URL is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
                # Missing planka_base_url
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "planka_base_url is not set" in str(exc_info.value)

    def test_validation_fails_missing_github_token(self, tmp_path: Path) -> None:
        """Test that validation fails when GitHub token is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "github",
                "github_owner": "test-owner",
                "github_repo": "test-repo",
                # Missing github_token
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "github_token is not set" in str(exc_info.value)

    def test_validation_fails_missing_github_owner_repo(self, tmp_path: Path) -> None:
        """Test that validation fails when GitHub owner/repo is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "github",
                "github_token": "ghp_test",
                # Missing github_owner and github_repo
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "github_owner or github_repo is not set" in str(exc_info.value)

    def test_validation_fails_missing_linear_api_key(self, tmp_path: Path) -> None:
        """Test that validation fails when Linear API key is missing."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "linear",
                # Missing linear_api_key
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "linear_api_key is not set" in str(exc_info.value)

    def test_validation_fails_invalid_port(self, tmp_path: Path) -> None:
        """Test that validation fails with invalid HTTP port."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            "transport": {"type": "http", "http": {"port": 99999}},  # Invalid port
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        assert "port must be between 1-65535" in str(exc_info.value)

    def test_validation_passes_when_ai_disabled(self, tmp_path: Path) -> None:
        """Test that validation skips AI checks when AI is disabled."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "enabled": False,
                "provider": "anthropic",
                # No API key needed when disabled
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
        # Should not raise even without API key
        config.validate()

    def test_validation_creates_directories(self, tmp_path: Path) -> None:
        """Test that validation creates data and cache directories."""
        config_file = tmp_path / "test_config.json"
        data_dir = tmp_path / "data"
        cache_dir = tmp_path / "cache"

        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            "data_dir": str(data_dir),
            "cache_dir": str(cache_dir),
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))
        config.validate()

        # Directories should be created
        assert data_dir.exists()
        assert cache_dir.exists()

    def test_validation_fails_with_unresolved_env_placeholder(
        self, tmp_path: Path
    ) -> None:
        """Test that validation catches unresolved environment variable placeholders.

        This is a critical security test - unresolved placeholders like
        ${ANTHROPIC_API_KEY} should be treated as missing values (None), not
        as literal strings. This prevents the API provider from attempting to
        use the placeholder string as an actual API key.
        """
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "anthropic_api_key": "${UNDEFINED_ANTHROPIC_KEY}",  # Env var not set
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

        # Config should have None for the API key (not the literal "${...}" string)
        assert config.ai.anthropic_api_key is None

        # Validation should fail because Anthropic key is required
        with pytest.raises(ValueError) as exc_info:
            config.validate()

        error_msg = str(exc_info.value)
        assert "anthropic_api_key is not set" in error_msg

    def test_validation_aggregates_multiple_errors(self, tmp_path: Path) -> None:
        """Test that validation reports all errors at once."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {
                "provider": "anthropic",
                "temperature": 2.0,  # Invalid
                # Missing anthropic_api_key
            },
            "kanban": {
                "provider": "planka",
                # Missing all planka fields
            },
            "transport": {"type": "http", "http": {"port": 0}},  # Invalid port
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        with pytest.raises(ValueError) as exc_info:
            config.validate()

        error_msg = str(exc_info.value)
        # Should contain multiple errors
        assert "anthropic_api_key is not set" in error_msg
        assert "temperature must be between 0.0 and 1.0" in error_msg
        assert "planka_base_url is not set" in error_msg
        assert "port must be between 1-65535" in error_msg
