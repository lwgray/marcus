"""
Unit tests for Worker MCP Client
"""

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.worker.client import WorkerMCPClient


class MockClientSession:
    """Mock ClientSession for testing"""

    def __init__(self):
        self.initialize = AsyncMock()
        self.list_tools = AsyncMock(
            return_value=[
                Mock(name="register_agent"),
                Mock(name="request_next_task"),
                Mock(name="report_task_progress"),
                Mock(name="report_blocker"),
                Mock(name="get_project_status"),
            ]
        )
        self.call_tool = AsyncMock()


class TestWorkerMCPClient:
    """Test cases for WorkerMCPClient"""

    @pytest.fixture
    def client(self):
        """Create a WorkerMCPClient instance"""
        return WorkerMCPClient()

    @pytest.fixture
    def mock_session(self):
        """Create a mock session"""
        return MockClientSession()

    def test_initialization(self, client):
        """Test client initialization"""
        assert client.session is None

    @pytest.mark.asyncio
    async def test_register_agent(self, client, mock_session):
        """Test agent registration"""
        # Setup mock response
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "success": True,
                        "message": "Agent registered successfully",
                        "agent_id": "test-agent-001",
                    }
                )
            )
        ]
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call register_agent
        result = await client.register_agent(
            "test-agent-001", "Test Agent", "Backend Developer", ["python", "testing"]
        )

        # Verify
        assert result["success"] is True
        assert result["agent_id"] == "test-agent-001"
        mock_session.call_tool.assert_called_once_with(
            "register_agent",
            arguments={
                "agent_id": "test-agent-001",
                "name": "Test Agent",
                "role": "Backend Developer",
                "skills": ["python", "testing"],
            },
        )

    @pytest.mark.asyncio
    async def test_request_next_task(self, client, mock_session):
        """Test task request"""
        # Setup mock response
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "has_task": True,
                        "task": {
                            "id": "task-123",
                            "title": "Test Task",
                            "priority": "high",
                            "estimated_hours": 4,
                        },
                    }
                )
            )
        ]
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call request_next_task
        result = await client.request_next_task("test-agent-001")

        # Verify
        assert result["has_task"] is True
        assert result["task"]["id"] == "task-123"
        mock_session.call_tool.assert_called_once_with(
            "request_next_task", arguments={"agent_id": "test-agent-001"}
        )

    @pytest.mark.asyncio
    async def test_report_task_progress(self, client, mock_session):
        """Test progress reporting"""
        # Setup mock response
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {"success": True, "message": "Progress updated successfully"}
                )
            )
        ]
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call report_task_progress
        result = await client.report_task_progress(
            "test-agent-001", "task-123", "in_progress", 50, "Halfway done"
        )

        # Verify
        assert result["success"] is True
        mock_session.call_tool.assert_called_once_with(
            "report_task_progress",
            arguments={
                "agent_id": "test-agent-001",
                "task_id": "task-123",
                "status": "in_progress",
                "progress": 50,
                "message": "Halfway done",
            },
        )

    @pytest.mark.asyncio
    async def test_report_blocker(self, client, mock_session):
        """Test blocker reporting"""
        # Setup mock response
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "success": True,
                        "suggestions": ["Try solution A", "Try solution B"],
                        "escalated": False,
                    }
                )
            )
        ]
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call report_blocker
        result = await client.report_blocker(
            "test-agent-001", "task-123", "Missing API credentials", "medium"
        )

        # Verify
        assert result["success"] is True
        assert len(result["suggestions"]) == 2
        mock_session.call_tool.assert_called_once_with(
            "report_blocker",
            arguments={
                "agent_id": "test-agent-001",
                "task_id": "task-123",
                "blocker_description": "Missing API credentials",
                "severity": "medium",
            },
        )

    @pytest.mark.asyncio
    async def test_get_project_status(self, client, mock_session):
        """Test getting project status"""
        # Setup mock response
        mock_result = Mock()
        mock_result.content = [
            Mock(
                text=json.dumps(
                    {
                        "success": True,
                        "project_state": {
                            "total_tasks": 25,
                            "completed_tasks": 10,
                            "in_progress_tasks": 5,
                        },
                        "metrics": {"velocity": 2.5, "completion_rate": 0.4},
                    }
                )
            )
        ]
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call get_project_status
        result = await client.get_project_status()

        # Verify
        assert result["success"] is True
        assert result["project_state"]["total_tasks"] == 25
        mock_session.call_tool.assert_called_once_with(
            "get_project_status", arguments={}
        )

    @pytest.mark.asyncio
    async def test_no_session_error(self, client):
        """Test error when no session is established"""
        with pytest.raises(RuntimeError, match="Not connected to Marcus"):
            await client.register_agent("test", "Test", "Developer", [])

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, client, mock_session):
        """Test handling of empty responses"""
        # Setup mock response with no content
        mock_result = Mock()
        mock_result.content = []
        mock_session.call_tool.return_value = mock_result

        # Set session
        client.session = mock_session

        # Call method
        result = await client.request_next_task("test-agent-001")

        # Verify empty dict returned
        assert result == {}

    @pytest.mark.asyncio
    @patch("src.worker.client.stdio_client")
    @patch("src.worker.client.ClientSession")
    async def test_connect_to_marcus(
        self, mock_client_session, mock_stdio_client, client
    ):
        """Test connecting to Marcus"""
        # Setup mocks
        mock_read_stream = AsyncMock()
        mock_write_stream = AsyncMock()
        mock_session_instance = MockClientSession()

        @asynccontextmanager
        async def mock_stdio_context(params):
            yield (mock_read_stream, mock_write_stream)

        @asynccontextmanager
        async def mock_session_context(read, write):
            yield mock_session_instance

        mock_stdio_client.return_value = mock_stdio_context(None)
        mock_client_session.return_value = mock_session_context(None, None)

        # Test connection
        async with client.connect_to_marcus() as session:
            assert session == mock_session_instance
            assert client.session == mock_session_instance
            mock_session_instance.initialize.assert_called_once()
            mock_session_instance.list_tools.assert_called_once()
