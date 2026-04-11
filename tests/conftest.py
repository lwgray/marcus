"""
Shared pytest fixtures and configuration for Marcus tests.

This module provides common fixtures and configuration for the Marcus test suite,
including MCP session management, test board creation, and custom pytest markers.

Notes
-----
This configuration file is automatically loaded by pytest and provides shared
resources for all tests in the suite.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict

import pytest

# GH-320 PR 2: ensure a dummy ANTHROPIC_API_KEY is set before any
# test imports happen. ``AdvancedPRDParser.__init__`` (and anything
# that constructs ``NaturalLanguageProjectCreator``) instantiates
# ``LLMAbstraction`` which validates Marcus config on first call.
# In CI, no config file exists and no env var is set, so validation
# fails with "anthropic_api_key is not set" and any test that touches
# the decomposer crashes at construction time. Unit tests never make
# real LLM calls, so a placeholder is safe.
#
# This must run BEFORE any test module imports src.ai.advanced.prd
# or src.integrations.nlp_tools, which is why it lives at conftest.py
# module level (pytest processes conftest.py before collecting test
# files). Per-file ``os.environ.setdefault`` calls in individual test
# modules aren't guaranteed to run early enough because pytest import
# order depends on collection order, and earlier test files that
# accidentally import Marcus config modules can poison the cache.
if not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = "test-key-not-real"

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import domain-specific fixtures
pytest_plugins = [
    "tests.fixtures.fixtures_core",
    "tests.fixtures.fixtures_ai",
    "tests.fixtures.fixtures_integration",
]


# Session event-loop fixture removed as of this commit.
#
# A previous version of this conftest defined a session-scoped
# ``event_loop`` fixture that called ``asyncio.new_event_loop()``
# without ``asyncio.set_event_loop(loop)``. Combined with
# ``pytest.ini``'s ``asyncio_mode = auto`` and
# ``asyncio_default_fixture_loop_scope = function``, the two
# loop-management systems conflicted: pytest-asyncio would create
# function-scoped loops, close them after each async test, and any
# later synchronous test calling ``asyncio.get_event_loop()`` would
# hit ``RuntimeError: There is no current event loop in thread
# 'MainThread'``.
#
# This was the root cause of ~680 full-sweep test failures that were
# invisible to ``pytest -m unit`` (the PR-blocking CI job) because
# the contaminated tests don't carry the ``unit`` marker. The nightly
# full-suite CI job was red for 100+ consecutive days before this
# fix was merged.
#
# pytest-asyncio 0.21+ manages event loops automatically via
# ``asyncio_mode = auto`` and ``asyncio_default_fixture_loop_scope``.
# Custom ``event_loop`` fixtures are deprecated and should not be
# defined — they produce undefined behavior, which is exactly what
# happened here. The fix: let pytest-asyncio handle it.


@pytest.fixture
async def mcp_session() -> AsyncGenerator[ClientSession, None]:
    """
    Provide an MCP session connected to the Kanban MCP server.

    This fixture handles the complete lifecycle of an MCP client session,
    including connection setup, initialization, and cleanup.

    Yields
    ------
    ClientSession
        An initialized MCP client session ready for tool calls.

    Notes
    -----
    The session connects to a local Kanban MCP server running on Node.js.
    Requires the Kanban MCP server to be installed and accessible.

    Examples
    --------
    >>> async def test_kanban_operation(mcp_session):
    ...     result = await mcp_session.call_tool("some_tool", {"param": "value"})
    ...     assert result is not None
    """
    server_params = StdioServerParameters(
        command="/opt/homebrew/bin/node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env={
            "PLANKA_BASE_URL": "http://localhost:3333",
            "PLANKA_AGENT_EMAIL": "demo@demo.demo",
            "PLANKA_AGENT_PASSWORD": "demo",
        },
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


@pytest.fixture
def test_project_id() -> str:
    """
    Provide the test project ID.

    Returns
    -------
    str
        The ID of the "Task Master Test" project used for testing.

    Notes
    -----
    This project should exist in the Kanban system before running tests.
    """
    return "1533678301472621705"  # Task Master Test


@pytest.fixture
def test_board_name() -> str:
    """
    Generate a unique test board name.

    Creates a timestamped board name to ensure uniqueness across test runs
    and prevent naming conflicts.

    Returns
    -------
    str
        A unique board name with timestamp.

    Examples
    --------
    >>> test_board_name()
    'Test Board - 2024-01-15 14:30:45'
    """
    return f"Test Board - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"


@pytest.fixture
async def test_board(
    mcp_session: ClientSession, test_project_id: str, test_board_name: str
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Create a test board and clean it up after the test.

    This fixture creates a temporary board for testing purposes and ensures
    it is deleted after the test completes, preventing test pollution.

    Parameters
    ----------
    mcp_session : ClientSession
        The MCP session for making API calls.
    test_project_id : str
        The ID of the test project.
    test_board_name : str
        The name for the test board.

    Yields
    ------
    Dict[str, Any]
        The created board data including ID and other properties.

    Notes
    -----
    The board is automatically deleted in the cleanup phase, even if the test fails.

    Examples
    --------
    >>> async def test_board_operations(test_board):
    ...     assert test_board["id"] is not None
    ...     assert test_board["name"] == test_board_name
    """
    # Create board
    result = await mcp_session.call_tool(
        "mcp_kanban_project_board_manager",
        {
            "action": "create_board",
            "projectId": test_project_id,
            "name": test_board_name,
            "position": 1,
        },
    )

    board_data = None
    if hasattr(result, "content") and result.content:
        import json

        board_data = json.loads(result.content[0].text)

    yield board_data

    # Cleanup
    if board_data and board_data.get("id"):
        try:
            await mcp_session.call_tool(
                "mcp_kanban_project_board_manager",
                {"action": "delete_board", "boardId": board_data["id"]},
            )
        except Exception:
            pass  # Board might already be deleted


@pytest.fixture
def mock_task_data() -> Dict[str, Any]:
    """
    Provide sample task data for testing.

    Returns
    -------
    Dict[str, Any]
        A dictionary containing standard task fields for testing.

    Notes
    -----
    This fixture provides a consistent task structure for tests that need
    to create or manipulate tasks.

    Examples
    --------
    >>> def test_task_creation(mock_task_data):
    ...     assert mock_task_data["name"] == "Test Task"
    ...     assert "test" in mock_task_data["labels"]
    """
    return {
        "name": "Test Task",
        "description": "This is a test task",
        "labels": ["test", "automated"],
    }


# Markers for test organization
def pytest_configure(config: pytest.Config) -> None:
    """
    Register custom markers for test organization.

    This function is called by pytest during initialization to register
    custom markers that can be used to categorize and filter tests.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object.

    Notes
    -----
    Markers can be used with pytest's -m flag to run specific test categories:
    - `pytest -m integration` runs only integration tests
    - `pytest -m "not slow"` runs all tests except slow ones

    Examples
    --------
    >>> @pytest.mark.integration
    ... async def test_full_workflow():
    ...     pass

    >>> @pytest.mark.unit
    ... def test_single_function():
    ...     pass
    """
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "kanban: mark test as requiring Kanban MCP server"
    )
