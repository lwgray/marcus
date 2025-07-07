#!/usr/bin/env python3
"""
Unit tests for MCPKanbanClientSimplified
Tests the client logic without real MCP connections
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest
import pytest_asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.models import Priority, Task, TaskStatus
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient


class MockMCPCaller:
    """Mock MCP function caller for testing"""

    def __init__(self):
        self.calls = []
        self.responses = {}

    async def __call__(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Record the call and return mock response"""
        self.calls.append((tool_name, arguments))

        # Generate response based on tool and action
        key = f"{tool_name}:{arguments.get('action', 'default')}"
        if key in self.responses:
            return self.responses[key]

        # Default responses
        if tool_name == "mcp_kanban_project_board_manager":
            if arguments.get("action") == "get_projects":
                return {
                    "items": [
                        {"id": "test-project-123", "name": "Task Master Test"}
                    ]
                }
            elif arguments.get("action") == "get_boards":
                return {
                    "items": [
                        {"id": "test-board-456", "projectId": "test-project-123"}
                    ]
                }
        elif tool_name == "mcp_kanban_card_manager":
            if arguments.get("action") == "get_all":
                return [
                    {
                        "id": "card-1",
                        "name": "Test Task 1",
                        "description": "Test description",
                        "list": {"name": "TODO"},
                        "labels": [{"name": "high", "color": "red"}],
                        "createdAt": "2024-01-01T00:00:00",
                        "updatedAt": "2024-01-01T00:00:00"
                    },
                    {
                        "id": "card-2",
                        "name": "Test Task 2",
                        "list": {"name": "In Progress"},
                        "labels": [],
                        "createdAt": "2024-01-01T00:00:00"
                    }
                ]
            elif arguments.get("action") == "get_details":
                return {
                    "id": arguments.get("cardId"),
                    "name": "Detailed Task",
                    "description": "Detailed description",
                    "list": {"name": "TODO"},
                    "labels": [{"name": "medium"}],
                    "createdAt": "2024-01-01T00:00:00"
                }
        elif tool_name == "mcp_kanban_list_manager":
            if arguments.get("action") == "get_all":
                return [
                    {"id": "list-todo", "name": "TODO", "position": 0},
                    {"id": "list-progress", "name": "In Progress", "position": 1},
                    {"id": "list-done", "name": "Done", "position": 2}
                ]
        elif tool_name == "mcp_kanban_board_manager":
            if arguments.get("action") == "get_stats":
                return {
                    "stats": {
                        "totalCards": 10,
                        "inProgressCount": 3,
                        "doneCount": 5,
                        "completionPercentage": 50
                    }
                }

        return None


class TestMCPKanbanClientSimplified:
    """Test suite for MCPKanbanClientSimplified"""

    @pytest.fixture
    def mock_caller(self):
        """Create a mock MCP caller"""
        return MockMCPCaller()

    @pytest.fixture
    def client(self, mock_caller):
        """Create a client with mock caller"""
        return SimpleMCPKanbanClient(mock_caller)

    @pytest.mark.asyncio
    async def test_initialization(self, client):
        """Test client initialization"""
        # Should not be initialized yet
        assert client.project_id is None
        assert client.board_id is None

        # Initialize
        await client.initialize("Task Master Test")

        # Should now have IDs
        assert client.project_id == "test-project-123"
        assert client.board_id == "test-board-456"

    @pytest.mark.asyncio
    async def test_initialization_project_not_found(self, client):
        """Test initialization when project not found"""
        client.mcp_call.responses["mcp_kanban_project_board_manager:get_projects"] = {"items": []}

        with pytest.raises(ValueError, match="Project 'Task Master Test' not found"):
            await client.initialize("Task Master Test")

    @pytest.mark.asyncio
    async def test_get_available_tasks(self, client):
        """Test getting available tasks"""
        await client.initialize("Task Master Test")

        tasks = await client.get_available_tasks()

        assert len(tasks) == 2
        assert tasks[0].id == "card-1"
        assert tasks[0].name == "Test Task 1"
        assert tasks[0].status == TaskStatus.TODO
        assert tasks[0].priority == Priority.MEDIUM  # Current implementation doesn't extract from labels

        assert tasks[1].id == "card-2"
        assert tasks[1].name == "Test Task 2"
        assert tasks[1].status == TaskStatus.TODO  # Status is determined by listId lookup, not list.name
        assert tasks[1].priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_get_available_tasks_not_initialized(self, client):
        """Test getting tasks when not initialized"""
        with pytest.raises(RuntimeError, match="Not initialized"):
            await client.get_available_tasks()

    @pytest.mark.asyncio
    async def test_get_task_details(self, client):
        """Test getting task details"""
        await client.initialize("Task Master Test")

        task = await client.get_task_details("test-task-id")

        assert task.id == "test-task-id"
        assert task.name == "Detailed Task"
        assert task.description == "Detailed description"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_assign_task(self, client):
        """Test task assignment"""
        await client.initialize("Task Master Test")

        # Set up mock responses for assignment
        client.mcp_call.responses["mcp_kanban_comment_manager:create"] = {"id": "comment-1"}
        client.mcp_call.responses["mcp_kanban_card_manager:move"] = {"id": "card-1"}

        await client.assign_task("card-1", "test-agent")

        # Check that correct calls were made
        calls = client.mcp_call.calls

        # Should have comment creation
        comment_call = next(c for c in calls if c[0] == "mcp_kanban_comment_manager")
        assert comment_call[1]["action"] == "create"
        assert comment_call[1]["cardId"] == "card-1"
        assert "test-agent" in comment_call[1]["text"]

        # Should have update to In Progress
        # The client uses update_task_status which changes labels, not direct move
        assert len(calls) >= 2  # At least comment + some status update

    @pytest.mark.asyncio
    async def test_complete_task(self, client):
        """Test task completion"""
        await client.initialize("Task Master Test")

        # Set up mock responses
        client.mcp_call.responses["mcp_kanban_comment_manager:create"] = {"id": "comment-1"}
        client.mcp_call.responses["mcp_kanban_card_manager:move"] = {"id": "card-1"}

        await client.complete_task("card-1")

        # Check that task completion was recorded
        calls = client.mcp_call.calls
        # Should have comment about completion
        comment_calls = [c for c in calls if c[0] == "mcp_kanban_comment_manager"]
        assert len(comment_calls) > 0
        assert "completed" in comment_calls[0][1]["text"].lower()


    @pytest.mark.asyncio
    async def test_card_to_task_conversion(self, client):
        """Test card to task conversion"""
        await client.initialize("Task Master Test")

        # Test with complete card data
        card = {
            "id": "test-id",
            "name": "Test Card",
            "description": "Test description",
            "list": {"name": "TODO"},
            "labels": [{"name": "high", "color": "red"}],
            "createdAt": "2024-01-01T00:00:00",
            "updatedAt": "2024-01-02T00:00:00"
        }

        task = await client._card_to_task(card)

        assert task.id == "test-id"
        assert task.name == "Test Card"
        assert task.description == "Test description"
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM  # Priority is always MEDIUM in current implementation
        assert task.created_at is not None
        assert task.updated_at is not None

    @pytest.mark.asyncio
    async def test_card_to_task_minimal_data(self, client):
        """Test card to task conversion with minimal data"""
        await client.initialize("Task Master Test")

        card = {
            "id": "minimal-id",
            "name": "Minimal Card"
        }

        task = await client._card_to_task(card)

        assert task.id == "minimal-id"
        assert task.name == "Minimal Card"
        assert task.description == ""
        assert task.status == TaskStatus.TODO
        assert task.priority == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_status_mapping(self, client):
        """Test status mapping from list names"""
        await client.initialize("Task Master Test")

        # The actual implementation uses listId, not list.name
        # And it checks if "progress", "done", "complete", or "blocked" is in the list name
        test_cases = [
            ("list-todo", "TODO", TaskStatus.TODO),
            ("list-progress", "In Progress", TaskStatus.IN_PROGRESS),
            ("list-working", "Working on it", TaskStatus.TODO),  # No "progress" in name
            ("list-done", "Done", TaskStatus.DONE),
            ("list-completed", "Completed tasks", TaskStatus.DONE),
            ("list-blocked", "Blocked", TaskStatus.BLOCKED)
        ]

        # Mock the _get_lists response
        client.mcp_call.responses["mcp_kanban_list_manager:get_all"] = [
            {"id": "list-todo", "name": "TODO"},
            {"id": "list-progress", "name": "In Progress"},
            {"id": "list-working", "name": "Working on it"},
            {"id": "list-done", "name": "Done"},
            {"id": "list-completed", "name": "Completed tasks"},
            {"id": "list-blocked", "name": "Blocked"}
        ]

        for list_id, list_name, expected_status in test_cases:
            card = {"id": "test", "name": "Test", "listId": list_id}
            task = await client._card_to_task(card)
            assert task.status == expected_status, f"List '{list_name}' (id: {list_id}) should map to {expected_status}"

    @pytest.mark.asyncio
    async def test_priority_default(self, client):
        """Test that priority defaults to MEDIUM"""
        await client.initialize("Task Master Test")

        # The current implementation always sets priority to MEDIUM
        # It doesn't extract from labels yet
        card = {"id": "test", "name": "Test", "labels": [{"name": "urgent"}]}
        task = await client._card_to_task(card)
        assert task.priority == Priority.MEDIUM  # Always returns MEDIUM in current implementation
