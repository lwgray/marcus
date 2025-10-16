"""
Shared pytest fixtures for integration tests.

This module provides fixtures specifically for Kanban integration tests,
including proper mocking of kanban-mcp path detection.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def mock_kanban_mcp_path():
    """
    Mock kanban-mcp path to use KANBAN_MCP_PATH environment variable.

    This fixture ensures tests can find kanban-mcp by using the
    KANBAN_MCP_PATH environment variable, which should be set
    to the actual kanban-mcp location.

    This is an autouse fixture, so it applies to all tests in this directory
    automatically without needing to be explicitly requested.

    Returns
    -------
    str
        Path to kanban-mcp from environment variable

    Notes
    -----
    This fixture mocks `_get_kanban_mcp_path` to bypass file system checks
    and return the environment variable value directly. This solves issues
    in worktree environments where the default path detection fails.
    """
    kanban_path = os.getenv(
        "KANBAN_MCP_PATH", "/Users/lwgray/dev/kanban-mcp/dist/index.js"
    )

    with patch(
        "src.integrations.kanban_client.KanbanClient._get_kanban_mcp_path",
        return_value=kanban_path,
    ):
        yield kanban_path


@pytest.fixture
def mock_kanban_client_env(mock_kanban_mcp_path):
    """
    Provide a clean environment for KanbanClient tests.

    This fixture:
    - Mocks the kanban-mcp path detection
    - Provides a clean environ dict for tests to modify
    - Ensures workspace state loading returns None

    Yields
    ------
    dict
        Empty environment dictionary that tests can populate

    Examples
    --------
    >>> def test_something(mock_kanban_client_env):
    ...     with patch("src.integrations.kanban_client.os.environ", mock_kanban_client_env):
    ...         client = KanbanClient()  # Will use mocked environment
    """
    with patch(
        "src.integrations.kanban_client.KanbanClient._load_workspace_state",
        return_value=None,
    ):
        yield {}
