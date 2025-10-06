"""
Unit tests for KanbanClient credential security.

This module provides focused tests on credential handling security,
ensuring that sensitive information is handled appropriately and
hardcoded defaults are properly justified.
"""

import os
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from src.integrations.kanban_client import KanbanClient
from src.integrations.kanban_client_with_create import KanbanClientWithCreate


def selective_path_exists_for_config(return_value=False):
    """
    Create a selective Path.exists mock that allows kanban-mcp path to work.

    Parameters
    ----------
    return_value : bool
        What to return for config_marcus.json (default False)
    """
    original_exists = Path.exists
    def selective_exists(self):
        if "config_marcus.json" in str(self):
            return return_value
        return original_exists(self)
    return selective_exists


class TestKanbanCredentialSecurity:
    """
    Test suite focused on credential security aspects of KanbanClient.

    Tests ensure that credentials are handled securely and that hardcoded
    defaults are only used in development scenarios where they are acceptable.
    """

    def test_hardcoded_defaults_only_used_as_fallback(self):
        """Test that hardcoded defaults are only used when no other source is available."""
        # Mock no config file and empty environment
        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(False)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Should set defaults only because no other source was available
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"
            assert mock_env["PLANKA_AGENT_EMAIL"] == "demo@demo.demo"
            assert mock_env["PLANKA_BASE_URL"] == "http://localhost:3333"

    def test_config_credentials_take_precedence_over_defaults(self):
        """Test that config file credentials override defaults."""
        config = {
            "planka": {
                "base_url": "https://production.planka.com",
                "email": "production@company.com",
                "password": "secure-production-password",
            }
        }

        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(True)),
            patch(
                "builtins.open",
                mock_open(
                    read_data='{"planka": {"base_url": "https://production.planka.com", "email": "production@company.com", "password": "secure-production-password"}}'
                ),
            ),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Should use config values, not defaults
            assert mock_env["PLANKA_BASE_URL"] == "https://production.planka.com"
            assert mock_env["PLANKA_AGENT_EMAIL"] == "production@company.com"
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "secure-production-password"

    def test_environment_variables_take_precedence_over_defaults(self):
        """Test that existing environment variables are not overwritten."""
        existing_env = {
            "PLANKA_BASE_URL": "https://staging.planka.com",
            "PLANKA_AGENT_EMAIL": "staging@company.com",
            "PLANKA_AGENT_PASSWORD": "staging-password",
        }

        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(False)),
            patch(
                "src.integrations.kanban_client.os.environ", existing_env.copy()
            ) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Should preserve existing environment values
            assert mock_env["PLANKA_BASE_URL"] == "https://staging.planka.com"
            assert mock_env["PLANKA_AGENT_EMAIL"] == "staging@company.com"
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "staging-password"

    def test_precedence_order_config_over_env_over_defaults(self):
        """Test that config takes precedence over env, which takes precedence over defaults."""
        # Set up environment with some values
        existing_env = {
            "PLANKA_BASE_URL": "http://env.planka.com",
            # Missing PLANKA_AGENT_EMAIL and PLANKA_AGENT_PASSWORD in env
        }

        # Config with partial override
        config_content = '{"planka": {"email": "config@company.com"}}'

        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(True)),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch(
                "src.integrations.kanban_client.os.environ", existing_env.copy()
            ) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Config should override: email from config
            assert mock_env["PLANKA_AGENT_EMAIL"] == "config@company.com"
            # Env should be preserved: base_url from environment
            assert mock_env["PLANKA_BASE_URL"] == "http://env.planka.com"
            # Default should fill gaps: password gets default
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"

    def test_kanban_client_with_create_uses_same_security_pattern(self):
        """Test that KanbanClientWithCreate follows same credential security pattern."""
        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(False)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            # Parent class initialization will set defaults
            client = KanbanClientWithCreate()

            # Additional credential ensure should not change existing values
            original_password = mock_env["PLANKA_AGENT_PASSWORD"]
            client._ensure_planka_credentials()

            # Should be unchanged after ensure call
            assert mock_env["PLANKA_AGENT_PASSWORD"] == original_password
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"

    def test_credential_security_with_empty_config_sections(self):
        """Test credential handling when config has empty planka section."""
        config_content = '{"planka": {}, "project_id": "test"}'

        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(True)),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Should fall back to defaults for empty planka section
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"
            assert mock_env["PLANKA_AGENT_EMAIL"] == "demo@demo.demo"
            assert mock_env["PLANKA_BASE_URL"] == "http://localhost:3333"

    def test_credential_security_with_null_values_in_config(self):
        """Test credential handling when config has null values."""
        config_content = '{"planka": {"password": null, "email": null}}'

        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(True)),
            patch("builtins.open", mock_open(read_data=config_content)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # Should fall back to defaults for null values (they're falsy)
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"
            assert mock_env["PLANKA_AGENT_EMAIL"] == "demo@demo.demo"

    def test_hardcoded_demo_credentials_are_development_only(self):
        """Test that demo credentials are clearly identified as development defaults."""
        # This test verifies our security assumption that "demo" credentials
        # are acceptable for development environments
        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(False)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr"),
        ):
            client = KanbanClient()

            # The demo values should be obviously for development/testing
            assert mock_env["PLANKA_AGENT_PASSWORD"] == "demo"
            assert "demo" in mock_env["PLANKA_AGENT_EMAIL"]
            assert "localhost" in mock_env["PLANKA_BASE_URL"]

            # These are clearly not production values - they contain "demo" and "localhost"
            # which makes them safe as development defaults

    def test_no_credentials_leaked_in_logs_or_errors(self):
        """Test that credential values are not exposed in error messages."""
        # This test ensures that even development defaults don't get logged
        with (
            patch("pathlib.Path.exists", selective_path_exists_for_config(False)),
            patch("src.integrations.kanban_client.os.environ", {}) as mock_env,
            patch("sys.stderr") as mock_stderr,
        ):
            client = KanbanClient()

            # Check that stderr calls don't contain credential values
            stderr_calls = [
                call.args
                for call in mock_stderr.write.call_args_list
                if mock_stderr.write.call_args_list
            ]

            # In this test case, no config file exists, so error messages are written
            # Verify that even error messages don't contain the actual credential values
            for call_args in stderr_calls:
                if call_args:
                    message = str(call_args[0]) if call_args else ""
                    # Should not contain the actual password
                    assert (
                        "demo" not in message.lower()
                        or "password" not in message.lower()
                    )
