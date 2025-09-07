"""
Common test fixtures for unit tests using real implementations.
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context import Context
from src.marcus_mcp.server import MarcusServer

# Domain-specific fixtures are now imported in the root conftest.py


@pytest.fixture
def test_env_vars(monkeypatch):
    """Set up test environment variables with real values."""
    monkeypatch.setenv("KANBAN_PROVIDER", "planka")
    monkeypatch.setenv("GITHUB_OWNER", "test-owner")
    monkeypatch.setenv("GITHUB_REPO", "test-repo")
    monkeypatch.setenv("MARCUS_TEST_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def test_marcus_server(test_env_vars):
    """Create a Marcus server instance for testing.

    Uses real implementations but with test configuration.
    For tests requiring external services, use @pytest.mark.integration
    """
    server = MarcusServer()
    # Configure for testing but use real implementations
    server.test_mode = True
    # Don't start background services in unit tests
    server.assignment_monitor = None
    return server


@pytest.fixture
def test_context():
    """Create a real test context for Marcus operations."""
    context = Context()
    context.test_mode = True
    context.project_name = "Unit Test Project"
    return context
