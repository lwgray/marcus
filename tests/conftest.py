"""
Shared pytest fixtures and configuration for PM Agent tests
"""

import pytest
import asyncio
import os
import sys
from typing import AsyncGenerator
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mcp_session() -> AsyncGenerator[ClientSession, None]:
    """
    Provides an MCP session connected to the Kanban MCP server.
    This fixture handles the connection lifecycle.
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
def test_project_id():
    """The test project ID"""
    return "1533678301472621705"  # Task Master Test


@pytest.fixture
def test_board_name():
    """Generate a unique test board name"""
    return f"Test Board - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@pytest.fixture
async def test_board(mcp_session, test_project_id, test_board_name):
    """
    Creates a test board and cleans it up after the test.
    Returns the board data.
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
def mock_task_data():
    """Sample task data for testing"""
    return {
        "name": "Test Task",
        "description": "This is a test task",
        "labels": ["test", "automated"]
    }


# Markers for test organization
def pytest_configure(config):
    """Register custom markers"""
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