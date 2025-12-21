"""
Smoke tests for Marcus basic functionality.

Fast sanity checks (<30 seconds total) to catch obvious breakage:
- Server initialization
- Core dependencies
- MCP tool registration
- Basic kanban connectivity
"""

import json
from typing import Any, Dict, List, cast
from unittest.mock import AsyncMock, patch

import pytest

from src.marcus_mcp.handlers import handle_tool_call
from src.marcus_mcp.server import MarcusServer
from tests.utils.base import BaseTestCase


@pytest.mark.unit
class TestMarcusSmoke(BaseTestCase):
    """Smoke tests for basic Marcus functionality."""

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_server_can_initialize(self) -> None:
        """
        Verify Marcus server can be created and initialized.

        This is the most basic smoke test - if this fails, everything fails.
        """
        server = await self._create_test_server()

        assert server is not None
        assert server.kanban_client is not None
        assert server.ai_engine is not None
        assert hasattr(server, "agent_status")
        assert hasattr(server, "agent_tasks")

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_core_tools_registered(self) -> None:
        """Verify all core MCP tools are properly registered."""
        from src.marcus_mcp.handlers import get_all_tool_names

        tool_names = get_all_tool_names()

        # Core agent tools must be present
        required_tools = [
            "ping",
            "register_agent",
            "get_agent_status",
            "request_next_task",
            "report_task_progress",
            "report_blocker",
            "get_project_status",
            "log_decision",
            "log_artifact",
            "get_task_context",
        ]

        for tool in required_tools:
            assert tool in tool_names, f"Required tool '{tool}' not registered"

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_ping_responds(self) -> None:
        """Verify basic connectivity via ping tool."""
        server = await self._create_test_server()

        result = await handle_tool_call("ping", {"echo": "test"}, server)
        data = self._parse_result(result)

        assert data["success"] is True
        assert data["status"] == "online"
        assert data["echo"] == "test"
        assert "timestamp" in data

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_agent_registration_works(self) -> None:
        """Verify basic agent registration."""
        server = await self._create_test_server()

        result = await handle_tool_call(
            "register_agent",
            {
                "agent_id": "smoke-test-agent",
                "name": "Smoke Test Agent",
                "role": "Developer",
                "skills": ["python"],
            },
            server,
        )

        data = self._parse_result(result)

        assert "success" in data or "error" not in data
        if "success" in data:
            assert data["success"] is True
            assert data["agent_id"] == "smoke-test-agent"
        assert "smoke-test-agent" in server.agent_status

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_kanban_client_connected(self) -> None:
        """Verify kanban client is connected and responsive."""
        server = await self._create_test_server()

        # Mock should respond to basic calls
        mock_kanban = cast(AsyncMock, server.kanban_client)
        mock_kanban.get_all_tasks.return_value = []

        # This should not raise
        tasks = await server.kanban_client.get_all_tasks()
        assert isinstance(tasks, list)

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_project_status_accessible(self) -> None:
        """Verify project status can be queried."""
        server = await self._create_test_server()

        result = await handle_tool_call("get_project_status", {}, server)
        data = self._parse_result(result)

        # Tool should respond (may say "no active project" which is valid)
        assert isinstance(data, dict)
        # Either success or a reasonable error about no active project
        assert (
            data.get("success") is not None
            or "project" in str(data.get("error", "")).lower()
        )

    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_ai_engine_available(self) -> None:
        """Verify AI engine is available for analysis."""
        server = await self._create_test_server()

        assert server.ai_engine is not None
        assert hasattr(server.ai_engine, "generate_task_instructions")
        assert hasattr(server.ai_engine, "analyze_blocker")

    async def _create_test_server(self) -> MarcusServer:
        """Create a test server with mocked dependencies."""
        import os

        os.environ["KANBAN_PROVIDER"] = "planka"

        with patch("src.marcus_mcp.server.get_config") as mock_config:
            mock_config.return_value = self.create_mock_config()

            server = MarcusServer()

        server.kanban_client = self.create_mock_kanban_client()
        server.kanban_client.board_id = "test-board-123"
        server.ai_engine = self.create_mock_ai_engine()
        server.assignment_monitor = None

        # Register test client with admin role for full access
        server._current_client_id = "test-client"
        server._registered_clients = {
            "test-client": {
                "client_type": "admin",
                "role": "test_admin",
                "metadata": {},
            }
        }

        return server

    def _parse_result(self, result: List[Any]) -> Dict[str, Any]:
        """Parse MCP tool result."""
        if result and len(result) > 0:
            return cast(Dict[str, Any], json.loads(result[0].text))
        return {}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
