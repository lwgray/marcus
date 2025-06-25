"""
Shared pytest fixtures and configuration for Marcus tests.

This module provides common fixtures and configuration for the Marcus test suite,
including MCP session management, test board creation, and custom pytest markers.

Notes
-----
This configuration file is automatically loaded by pytest and provides shared
resources for all tests in the suite.
"""

import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator, Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture(scope="session")
def event_loop() -> asyncio.AbstractEventLoop:
    """
    Create an event loop for the test session.
    
    This fixture provides a session-scoped event loop that persists for the
    entire test session, ensuring async tests can share the same loop.
    
    Yields
    ------
    asyncio.AbstractEventLoop
        The event loop instance for async operations.
    
    Notes
    -----
    The loop is automatically closed when the test session ends.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
            "PLANKA_AGENT_PASSWORD": "demo"
        }
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
    return f"Test Board - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@pytest.fixture
async def test_board(mcp_session: ClientSession, test_project_id: str, test_board_name: str) -> AsyncGenerator[Dict[str, Any], None]:
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
    result = await mcp_session.call_tool("mcp_kanban_project_board_manager", {
        "action": "create_board",
        "projectId": test_project_id,
        "name": test_board_name,
        "position": 1
    })
    
    board_data = None
    if hasattr(result, 'content') and result.content:
        import json
        board_data = json.loads(result.content[0].text)
    
    yield board_data
    
    # Cleanup
    if board_data and board_data.get("id"):
        try:
            await mcp_session.call_tool("mcp_kanban_project_board_manager", {
                "action": "delete_board",
                "boardId": board_data["id"]
            })
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
        "labels": ["test", "automated"]
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
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "kanban: mark test as requiring Kanban MCP server"
    )