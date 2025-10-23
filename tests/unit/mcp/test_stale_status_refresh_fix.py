"""
Unit tests for stale status refresh fix.

Verifies that refresh_project_state() correctly updates parent tasks
while preserving migrated subtasks.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.server import MarcusServer


@pytest.fixture
def mock_kanban_client():
    """Create a mock Kanban client."""
    client = AsyncMock()
    client.get_all_tasks = AsyncMock()
    return client


@pytest.fixture
def parent_task_todo():
    """Create a parent task in TODO status."""
    return Task(
        id="parent-1",
        name="Parent Task 1",
        description="A parent task",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=4.0,
        is_subtask=False,
    )


@pytest.fixture
def parent_task_in_progress():
    """Create the same parent task but IN_PROGRESS (updated on Kanban)."""
    return Task(
        id="parent-1",
        name="Parent Task 1",
        description="A parent task",
        status=TaskStatus.IN_PROGRESS,  # Status updated on Kanban
        priority=Priority.MEDIUM,
        assigned_to="agent-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=4.0,
        is_subtask=False,
    )


@pytest.fixture
def subtask():
    """Create a subtask."""
    return Task(
        id="subtask-1-1",
        name="Subtask 1.1",
        description="A subtask",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assigned_to="agent-1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=2.0,
        is_subtask=True,
        parent_task_id="parent-1",
        subtask_index=1,
    )


class TestStaleStatusRefreshFix:
    """Test suite for stale status refresh bug fix."""

    @pytest.mark.asyncio
    async def test_first_refresh_loads_parent_tasks_only(
        self, mock_kanban_client, parent_task_todo
    ):
        """Test first refresh loads parent tasks directly."""
        # Arrange
        server = MarcusServer()
        server.kanban_client = mock_kanban_client
        server._subtasks_migrated = False
        server.log_event = Mock()  # Mock event logging
        mock_kanban_client.get_all_tasks.return_value = [parent_task_todo]

        # Act
        await server.refresh_project_state()

        # Assert
        assert server.project_tasks == [parent_task_todo]
        assert len(server.project_tasks) == 1
        assert server.project_tasks[0].status == TaskStatus.TODO

    @pytest.mark.asyncio
    async def test_refresh_after_migration_preserves_subtasks(
        self, mock_kanban_client, parent_task_todo, subtask
    ):
        """Test refresh after migration preserves subtasks."""
        # Arrange
        server = MarcusServer()
        server.kanban_client = mock_kanban_client
        server._subtasks_migrated = True
        server.log_event = Mock()  # Mock event logging
        # In-memory state has parent + subtask
        server.project_tasks = [parent_task_todo, subtask]

        # Kanban returns only parent tasks (no subtasks)
        mock_kanban_client.get_all_tasks.return_value = [parent_task_todo]

        # Act
        await server.refresh_project_state()

        # Assert - Should have both parent and subtask
        assert len(server.project_tasks) == 2

        # Find parent and subtask
        parents = [t for t in server.project_tasks if not t.is_subtask]
        subtasks = [t for t in server.project_tasks if t.is_subtask]

        assert len(parents) == 1
        assert len(subtasks) == 1
        assert subtasks[0].id == "subtask-1-1"

    @pytest.mark.asyncio
    async def test_refresh_after_migration_updates_parent_status(
        self,
        mock_kanban_client,
        parent_task_todo,
        parent_task_in_progress,
        subtask,
    ):
        """Test refresh updates parent status from Kanban."""
        # Arrange
        server = MarcusServer()
        server.kanban_client = mock_kanban_client
        server._subtasks_migrated = True
        server.log_event = Mock()  # Mock event logging

        # In-memory state has parent in TODO + subtask
        server.project_tasks = [parent_task_todo, subtask]

        # Kanban now shows parent as IN_PROGRESS (was updated when assigned)
        mock_kanban_client.get_all_tasks.return_value = [parent_task_in_progress]

        # Act
        await server.refresh_project_state()

        # Assert - Parent should now be IN_PROGRESS
        assert len(server.project_tasks) == 2

        parents = [t for t in server.project_tasks if not t.is_subtask]
        subtasks = [t for t in server.project_tasks if t.is_subtask]

        assert len(parents) == 1
        assert len(subtasks) == 1

        # CRITICAL: Parent status should be refreshed from Kanban
        assert parents[0].status == TaskStatus.IN_PROGRESS  # Not TODO!
        assert subtasks[0].id == "subtask-1-1"  # Subtask preserved

    @pytest.mark.asyncio
    async def test_refresh_with_multiple_subtasks(
        self, mock_kanban_client, parent_task_in_progress
    ):
        """Test refresh preserves multiple subtasks."""
        # Arrange
        server = MarcusServer()
        server.kanban_client = mock_kanban_client
        server._subtasks_migrated = True
        server.log_event = Mock()  # Mock event logging

        # Create multiple subtasks
        subtask1 = Task(
            id="subtask-1-1",
            name="Subtask 1.1",
            description="First subtask",
            status=TaskStatus.DONE,
            is_subtask=True,
            parent_task_id="parent-1",
            subtask_index=1,
            assigned_to="agent-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            priority=Priority.MEDIUM,
        )
        subtask2 = Task(
            id="subtask-1-2",
            name="Subtask 1.2",
            description="Second subtask",
            status=TaskStatus.IN_PROGRESS,
            is_subtask=True,
            parent_task_id="parent-1",
            subtask_index=2,
            assigned_to="agent-2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            priority=Priority.MEDIUM,
        )
        subtask3 = Task(
            id="subtask-1-3",
            name="Subtask 1.3",
            description="Third subtask",
            status=TaskStatus.TODO,
            is_subtask=True,
            parent_task_id="parent-1",
            subtask_index=3,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            priority=Priority.MEDIUM,
        )

        # In-memory state
        old_parent = Task(
            id="parent-1",
            name="Parent Task 1",
            description="A parent task",
            status=TaskStatus.TODO,
            is_subtask=False,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
            priority=Priority.MEDIUM,
        )
        server.project_tasks = [old_parent, subtask1, subtask2, subtask3]

        # Kanban returns updated parent
        mock_kanban_client.get_all_tasks.return_value = [parent_task_in_progress]

        # Act
        await server.refresh_project_state()

        # Assert
        assert len(server.project_tasks) == 4  # 1 parent + 3 subtasks

        parents = [t for t in server.project_tasks if not t.is_subtask]
        subtasks = [t for t in server.project_tasks if t.is_subtask]

        assert len(parents) == 1
        assert len(subtasks) == 3

        # Parent status updated
        assert parents[0].status == TaskStatus.IN_PROGRESS

        # All subtasks preserved with correct statuses
        subtask_dict = {s.id: s for s in subtasks}
        assert subtask_dict["subtask-1-1"].status == TaskStatus.DONE
        assert subtask_dict["subtask-1-2"].status == TaskStatus.IN_PROGRESS
        assert subtask_dict["subtask-1-3"].status == TaskStatus.TODO
