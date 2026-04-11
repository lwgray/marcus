"""
Shared pytest fixtures and configuration for Marcus tests.

This module provides common fixtures and configuration for the Marcus test suite,
including MCP session management, test board creation, and custom pytest markers.

Notes
-----
This configuration file is automatically loaded by pytest and provides shared
resources for all tests in the suite.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

import pytest

# Add src to path for imports (must happen before Marcus imports below)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))


# GH-320 PR 2: provide a minimal valid Marcus config for the whole
# test suite by writing one to /tmp and pointing MARCUS_CONFIG at it.
#
# Why this is necessary
# ---------------------
# ``AdvancedPRDParser.__init__`` (and anything that constructs
# ``NaturalLanguageProjectCreator``) instantiates ``LLMAbstraction``
# which calls ``get_config()`` → ``MarcusConfig.from_file()`` →
# ``validate()``. In CI there is no ``config_marcus.json`` in the
# working directory, so ``from_file`` returns defaults with
# ``anthropic_api_key=None``, and ``validate()`` raises because the
# default provider is ``anthropic``.
#
# Why the env var alone doesn't work
# ----------------------------------
# Setting ``ANTHROPIC_API_KEY`` does NOT fix this. The default config
# does not consult environment variables directly — only ``${VAR}``
# substitutions inside a config file do, and without a config file
# there is nothing to substitute into.
#
# Why seeding ``_config`` alone doesn't work
# ------------------------------------------
# Pre-populating ``marcus_config._config`` in conftest.py survives
# the initial import, but ~20 tests in ``tests/unit/ai/test_openai_provider.py``
# reset ``marcus_config._config = None`` in their fixture setup to
# patch ``get_config``. When any test runs after one of those, the
# next call to ``get_config()`` hits ``from_file`` again and fails
# with the same error because there is still no config file on disk.
#
# The fix
# -------
# Write a minimal valid config file to a stable temp path and point
# ``MARCUS_CONFIG`` at it. Now any code path — including the
# openai_provider fixtures that reset the cache — will re-load the
# valid config from disk instead of crashing on defaults.
#
# This must happen at conftest.py module-level so it runs before
# pytest collects any test file that imports
# ``src.ai.advanced.prd.advanced_parser`` or
# ``src.integrations.nlp_tools``. Pytest processes conftest.py before
# collecting test modules.
def _install_test_config() -> None:
    """Install a minimal valid Marcus config for the test session."""
    # Stable path so reruns within a session find the same file.
    # ``gettempdir`` respects TMPDIR on macOS and /tmp on Linux.
    test_config_path = Path(tempfile.gettempdir()) / "marcus_test_config.json"

    # Write every time so test runs are deterministic regardless of
    # leftover state in /tmp.
    test_config_path.write_text(
        json.dumps(
            {
                "ai": {
                    "provider": "anthropic",
                    "anthropic_api_key": "test-key-not-real",
                    "model": "claude-3-5-sonnet-latest",
                    "max_tokens": 4096,
                    "temperature": 0.7,
                }
            }
        )
    )

    # Point MARCUS_CONFIG at the test file so every code path that
    # calls ``os.getenv("MARCUS_CONFIG", "config_marcus.json")`` picks
    # it up instead of the missing default path.
    os.environ["MARCUS_CONFIG"] = str(test_config_path)


_install_test_config()

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
