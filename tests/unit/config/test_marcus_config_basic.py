"""Unit tests for basic MarcusConfig functionality.

This test file verifies the core configuration loading and structure.
"""

import json
import os
from pathlib import Path

import pytest

from src.config.marcus_config import (
    AISettings,
    KanbanSettings,
    MarcusConfig,
    MCPSettings,
    get_config,
    reload_config,
)


class TestMarcusConfigBasic:
    """Test suite for basic MarcusConfig operations."""

    def test_default_config_creation(self) -> None:
        """Test that default config can be created."""
        config = MarcusConfig()

        assert config.ai.provider == "anthropic"
        assert config.kanban.provider == "planka"
        assert config.features.events is True
        assert config.log_level == "INFO"

    def test_dataclass_structure(self) -> None:
        """Test that dataclass structure works with type hints."""
        config = MarcusConfig()

        # Test that we can access nested configs
        assert isinstance(config.ai, AISettings)
        assert isinstance(config.kanban, KanbanSettings)
        assert isinstance(config.mcp, MCPSettings)

        # Test that we have type-safe attribute access
        assert hasattr(config.ai, "anthropic_api_key")
        assert hasattr(config.kanban, "planka_base_url")
        assert hasattr(config.mcp, "timeout")

    def test_load_config_from_file(self, tmp_path: Path) -> None:
        """Test loading config from JSON file."""
        # Create test config
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "openai", "openai_api_key": "test-key-123"},
            "kanban": {"provider": "github", "board_name": "Test Board"},
            "log_level": "DEBUG",
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        config = MarcusConfig.from_file(str(config_file))

        # Verify
        assert config.ai.provider == "openai"
        assert config.ai.openai_api_key == "test-key-123"
        assert config.kanban.provider == "github"
        assert config.kanban.board_name == "Test Board"
        assert config.log_level == "DEBUG"

    def test_env_var_substitution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ${ENV_VAR} syntax works."""
        # Set environment variable
        monkeypatch.setenv("TEST_API_KEY", "secret-key-from-env")

        # Create config with env var reference
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "${TEST_API_KEY}"}
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        # Load config
        config = MarcusConfig.from_file(str(config_file))

        # Verify env var was substituted
        assert config.ai.anthropic_api_key == "secret-key-from-env"

    def test_backward_compatibility_planka(self, tmp_path: Path) -> None:
        """Test that old 'planka' config key still works."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "planka": {
                "base_url": "http://localhost:3333",
                "email": "test@test.com",
                "password": "testpass",  # pragma: allowlist secret
            },
            "ai": {"provider": "anthropic", "anthropic_api_key": "test-key"},
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Should map to kanban.planka_* fields
        assert config.kanban.planka_base_url == "http://localhost:3333"
        assert config.kanban.planka_email == "test@test.com"
        assert config.kanban.planka_password == "testpass"

    def test_nonexistent_config_returns_defaults(self, tmp_path: Path) -> None:
        """Test that missing config file returns defaults."""
        nonexistent_file = tmp_path / "does_not_exist.json"

        config = MarcusConfig.from_file(str(nonexistent_file))

        # Should return default config
        assert config.ai.provider == "anthropic"
        assert config.kanban.provider == "planka"

    def test_nested_transport_config(self, tmp_path: Path) -> None:
        """Test that nested transport config loads correctly."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "transport": {
                "type": "http",
                "http": {"host": "127.0.0.1", "port": 9999, "path": "/api"},
            },
            "ai": {"provider": "anthropic", "anthropic_api_key": "test-key"},
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

        assert config.transport.http_host == "127.0.0.1"
        assert config.transport.http_port == 9999
        assert config.transport.http_path == "/api"
