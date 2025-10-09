"""
Unit tests for Task ID in card description metadata.

This module tests that task IDs are properly included in the card description
metadata when tasks are created, ensuring traceability between internal task
objects and their Planka card representations.
"""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.integrations.kanban_client_with_create import KanbanClientWithCreate


class TestTaskIdInDescription:
    """Test suite for Task ID metadata in card descriptions."""

    @pytest.fixture
    def mock_client_session(self):
        """Create a mock MCP client session."""
        session = AsyncMock()
        session.call_tool = AsyncMock()
        session.initialize = AsyncMock()
        return session

    @pytest.fixture
    def mock_stdio_client(self, mock_client_session):
        """Create a mock stdio client context manager."""

        @asynccontextmanager
        async def mock_stdio_context(*args, **kwargs):
            read = AsyncMock()
            write = AsyncMock()
            yield (read, write)

        return mock_stdio_context

    @pytest.fixture
    def mock_session_context(self, mock_client_session):
        """Create a mock ClientSession context manager."""

        @asynccontextmanager
        async def mock_session_ctx(*args, **kwargs):
            yield mock_client_session

        return mock_session_ctx

    @pytest.fixture
    def client(self):
        """Create a KanbanClientWithCreate instance for testing."""
        client = KanbanClientWithCreate()
        client.board_id = "test-board-123"
        return client

    def test_build_task_metadata_with_original_id(self, client):
        """Test that _build_task_metadata includes original_id in metadata."""
        # Arrange
        task_data = {
            "original_id": "task-abc-123",
            "estimated_hours": 8,
            "priority": "high",
            "dependencies": ["task-001", "task-002"],
        }

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        assert metadata is not None
        assert "📋 Task Metadata (Auto-generated)" in metadata
        assert "🏷️ Original ID: task-abc-123" in metadata
        assert "⏱️ Estimated: 8 hours" in metadata
        assert "🟠 Priority: HIGH" in metadata
        assert "🔗 Dependencies: task-001, task-002" in metadata

    def test_build_task_metadata_original_id_only(self, client):
        """Test metadata with only original_id (no other metadata)."""
        # Arrange
        task_data = {"original_id": "task-xyz-456"}

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        assert metadata is not None
        assert "🏷️ Original ID: task-xyz-456" in metadata
        # Should not include other metadata fields
        assert "Estimated" not in metadata
        assert "Priority" not in metadata
        assert "Dependencies" not in metadata

    def test_build_task_metadata_without_original_id(self, client):
        """Test metadata when original_id is not provided."""
        # Arrange
        task_data = {
            "estimated_hours": 4,
            "priority": "medium",
        }

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        assert metadata is not None
        # Should not include original_id line
        assert "Original ID" not in metadata
        assert "⏱️ Estimated: 4 hours" in metadata
        assert "🟡 Priority: MEDIUM" in metadata

    def test_build_task_metadata_empty_original_id(self, client):
        """Test metadata when original_id is empty string."""
        # Arrange
        task_data = {
            "original_id": "",
            "priority": "low",
        }

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        # Empty string should be falsy, so no Original ID line
        assert metadata is not None
        assert "Original ID" not in metadata

    def test_build_task_metadata_none_original_id(self, client):
        """Test metadata when original_id is None."""
        # Arrange
        task_data = {
            "original_id": None,
            "priority": "urgent",
        }

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        # None should be falsy, so no Original ID line
        assert metadata is not None
        assert "Original ID" not in metadata

    def test_build_task_metadata_no_metadata_at_all(self, client):
        """Test metadata returns None when no metadata fields provided."""
        # Arrange
        task_data = {"name": "Just a task name"}

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        assert metadata is None

    def test_build_task_metadata_priority_emojis(self, client):
        """Test correct priority emojis are used."""
        # Test each priority level
        priority_tests = [
            ("urgent", "🔴"),
            ("high", "🟠"),
            ("medium", "🟡"),
            ("low", "🟢"),
            ("unknown", "⚪"),  # Default for unknown priorities
        ]

        for priority_level, expected_emoji in priority_tests:
            # Arrange
            task_data = {"priority": priority_level, "original_id": "test-id"}

            # Act
            metadata = client._build_task_metadata(task_data)

            # Assert
            assert metadata is not None
            assert expected_emoji in metadata

    @pytest.mark.asyncio
    @patch("src.integrations.kanban_client_with_create.stdio_client")
    @patch("src.integrations.kanban_client_with_create.ClientSession")
    async def test_create_task_includes_original_id_in_description(
        self,
        mock_session_class,
        mock_stdio,
        client,
        mock_stdio_client,
        mock_session_context,
        mock_client_session,
    ):
        """Test that create_task includes original_id in the card description."""
        # Setup mocks
        mock_stdio.return_value = mock_stdio_client()
        mock_session_class.return_value = mock_session_context()

        # Track the description sent to card creation
        captured_description = None

        # Mock list response
        list_response = Mock()
        list_response.content = [
            Mock(text=json.dumps([{"id": "list-1", "name": "Backlog"}]))
        ]

        # Mock card creation response
        card_response = Mock()
        card_response.content = [
            Mock(
                text=json.dumps(
                    {
                        "id": "card-created-123",
                        "name": "Test Task",
                        "description": "Description with metadata",
                        "listId": "list-1",
                    }
                )
            )
        ]

        async def mock_call_tool(tool_name, params):
            nonlocal captured_description

            if tool_name == "mcp_kanban_list_manager":
                return list_response
            elif tool_name == "mcp_kanban_card_manager":
                # Capture the description parameter
                captured_description = params.get("description", "")
                return card_response
            else:
                return Mock(content=[Mock(text=json.dumps({"id": "default"}))])

        mock_client_session.call_tool = mock_call_tool

        # Arrange - task data WITH original_id
        task_data = {
            "name": "Test Task",
            "description": "User's task description",
            "original_id": "task-original-999",
            "priority": "high",
            "estimated_hours": 10,
        }

        # Act
        task = await client.create_task(task_data)

        # Assert
        assert task is not None
        assert captured_description is not None

        # Verify original_id is in the description sent to Planka
        assert "🏷️ Original ID: task-original-999" in captured_description
        # Verify user's description is preserved
        assert "User's task description" in captured_description
        # Verify metadata header is present
        assert "📋 Task Metadata (Auto-generated)" in captured_description

    @pytest.mark.asyncio
    @patch("src.integrations.kanban_client_with_create.stdio_client")
    @patch("src.integrations.kanban_client_with_create.ClientSession")
    async def test_create_task_metadata_appended_to_description(
        self,
        mock_session_class,
        mock_stdio,
        client,
        mock_stdio_client,
        mock_session_context,
        mock_client_session,
    ):
        """Test that metadata is properly appended to existing description."""
        # Setup mocks
        mock_stdio.return_value = mock_stdio_client()
        mock_session_class.return_value = mock_session_context()

        captured_description = None

        # Mock responses
        list_response = Mock()
        list_response.content = [
            Mock(text=json.dumps([{"id": "list-1", "name": "TODO"}]))
        ]

        card_response = Mock()
        card_response.content = [
            Mock(
                text=json.dumps({"id": "card-123", "name": "Task", "listId": "list-1"})
            )
        ]

        async def mock_call_tool(tool_name, params):
            nonlocal captured_description
            if tool_name == "mcp_kanban_list_manager":
                return list_response
            elif tool_name == "mcp_kanban_card_manager":
                captured_description = params.get("description", "")
                return card_response
            else:
                return Mock(content=[Mock(text=json.dumps({"id": "default"}))])

        mock_client_session.call_tool = mock_call_tool

        # Arrange
        task_data = {
            "name": "Task with Description",
            "description": "This is the main task description.\nIt has multiple lines.",
            "original_id": "task-multiline-001",
        }

        # Act
        await client.create_task(task_data)

        # Assert
        assert captured_description is not None
        # Original description should be at the start
        assert captured_description.startswith("This is the main task description.")
        # Metadata should be separated by double newline
        assert "\n\n📋 Task Metadata" in captured_description
        # Original ID should be after the metadata header
        assert "🏷️ Original ID: task-multiline-001" in captured_description

    @pytest.mark.asyncio
    @patch("src.integrations.kanban_client_with_create.stdio_client")
    @patch("src.integrations.kanban_client_with_create.ClientSession")
    async def test_create_task_empty_description_with_metadata(
        self,
        mock_session_class,
        mock_stdio,
        client,
        mock_stdio_client,
        mock_session_context,
        mock_client_session,
    ):
        """Test that metadata is used as description when no description provided."""
        # Setup mocks
        mock_stdio.return_value = mock_stdio_client()
        mock_session_class.return_value = mock_session_context()

        captured_description = None

        list_response = Mock()
        list_response.content = [
            Mock(text=json.dumps([{"id": "list-1", "name": "TODO"}]))
        ]

        card_response = Mock()
        card_response.content = [
            Mock(
                text=json.dumps({"id": "card-123", "name": "Task", "listId": "list-1"})
            )
        ]

        async def mock_call_tool(tool_name, params):
            nonlocal captured_description
            if tool_name == "mcp_kanban_list_manager":
                return list_response
            elif tool_name == "mcp_kanban_card_manager":
                captured_description = params.get("description", "")
                return card_response
            else:
                return Mock(content=[Mock(text=json.dumps({"id": "default"}))])

        mock_client_session.call_tool = mock_call_tool

        # Arrange - NO description, only metadata
        task_data = {
            "name": "Task without description",
            "original_id": "task-no-desc-123",
            "estimated_hours": 5,
        }

        # Act
        await client.create_task(task_data)

        # Assert
        assert captured_description is not None
        # Should start with metadata header (no preceding description)
        assert captured_description.startswith("📋 Task Metadata")
        assert "🏷️ Original ID: task-no-desc-123" in captured_description
        # Should NOT have double newlines at start
        assert not captured_description.startswith("\n\n")

    def test_build_task_metadata_ordering(self, client):
        """Test that metadata fields appear in expected order."""
        # Arrange
        task_data = {
            "original_id": "task-order-test",
            "estimated_hours": 6,
            "priority": "medium",
            "dependencies": ["dep-1"],
        }

        # Act
        metadata = client._build_task_metadata(task_data)

        # Assert
        assert metadata is not None
        lines = metadata.split("\n")

        # Header should be first
        assert lines[0] == "📋 Task Metadata (Auto-generated)"

        # Original ID should be second (first metadata field)
        assert "🏷️ Original ID" in lines[1]

        # Verify all expected fields are present
        metadata_lower = metadata.lower()
        assert "original id" in metadata_lower
        assert "estimated" in metadata_lower
        assert "priority" in metadata_lower
        assert "dependencies" in metadata_lower
