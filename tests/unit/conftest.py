"""
Common test fixtures for unit tests
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.marcus_mcp.server import MarcusServer


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("KANBAN_PROVIDER", "planka")
    monkeypatch.setenv("GITHUB_OWNER", "test-owner")
    monkeypatch.setenv("GITHUB_REPO", "test-repo")


@pytest.fixture
def mock_kanban_client():
    """Create a mock kanban client"""
    client = AsyncMock()
    client.get_available_tasks = AsyncMock(return_value=[])
    client.get_all_tasks = AsyncMock(return_value=[])
    client.get_task_by_id = AsyncMock(return_value=None)
    client.update_task = AsyncMock()
    client.create_task = AsyncMock()
    client.add_comment = AsyncMock()
    client.get_board_summary = AsyncMock(return_value={})
    # Add missing methods
    client.update_task_progress = AsyncMock()
    return client


@pytest.fixture
def marcus_server(mock_env_vars, mock_kanban_client):
    """Create a Marcus server instance with mocks"""
    server = MarcusServer()
    server.kanban_client = mock_kanban_client
    # Don't start the assignment monitor in tests
    server.assignment_monitor = None
    return server
