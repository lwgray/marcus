"""Unit tests for MarcusConfig security settings.

This test file verifies security-related configuration defaults,
particularly network binding settings.
"""

import json
from pathlib import Path

import pytest

from src.config.marcus_config import MarcusConfig, TransportSettings


class TestMarcusConfigSecurity:
    """Test suite for MarcusConfig security settings."""

    def test_default_http_host_is_localhost(self) -> None:
        """Test that default HTTP host is 127.0.0.1 (localhost) for security.

        This ensures the service doesn't bind to all interfaces by default,
        which would expose it to external network access.
        """
        config = MarcusConfig()

        assert config.transport.http_host == "127.0.0.1"

    def test_custom_http_host_from_config(self, tmp_path: Path) -> None:
        """Test that custom HTTP host can be set via config file."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test-key"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            "transport": {
                "type": "http",
                "http": {"host": "0.0.0.0", "port": 4298},
            },
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Custom host should be respected
        assert config.transport.http_host == "0.0.0.0"

    def test_transport_settings_default_is_secure(self) -> None:
        """Test TransportSettings dataclass has secure defaults."""
        transport = TransportSettings()

        assert transport.http_host == "127.0.0.1"
        assert transport.type == "http"
        assert 1 <= transport.http_port <= 65535

    def test_config_with_missing_transport_uses_secure_default(
        self, tmp_path: Path
    ) -> None:
        """Test that config without transport section uses secure defaults."""
        config_file = tmp_path / "test_config.json"
        config_data = {
            "ai": {"provider": "anthropic", "anthropic_api_key": "sk-ant-test-key"},
            "kanban": {
                "provider": "planka",
                "planka_base_url": "http://localhost:3333",
                "planka_email": "test@test.com",
                "planka_password": "testpass",  # pragma: allowlist secret
            },
            # No transport section - should use defaults
        }

        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = MarcusConfig.from_file(str(config_file))

        # Should use secure default
        assert config.transport.http_host == "127.0.0.1"
