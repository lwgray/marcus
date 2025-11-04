"""
Unit tests for get_optimal_agent_count timing bug (GH-XXX).

Tests verify that get_optimal_agent_count returns correct count immediately
after create_project, without requiring request_next_task to be called first.

Bug: get_optimal_agent_count returned 0 tasks after create_project but 40 tasks
after request_next_task. Root cause: refresh_project_state() migration timing.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.server import MarcusServer


class TestGetOptimalAgentCountTiming:
    """Test get_optimal_agent_count works immediately after project creation."""

    @pytest.fixture
    async def mock_server(self):
        """Create a mock Marcus server with subtask_manager."""
        server = MarcusServer(None)

        # Mock kanban client
        server.kanban_client = Mock()
        server.kanban_client.get_all_tasks = AsyncMock()

        # Create real subtask_manager
        from src.marcus_mcp.coordinator.subtask_manager import SubtaskManager

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name
        server.subtask_manager = SubtaskManager(state_file=temp_file)

        # Initialize state
        server.project_tasks = []
        server._subtasks_migrated = False

        return server

    @pytest.fixture
    def parent_tasks(self):
        """Create mock parent tasks."""
        return [
            Task(
                id=f"task_{i}",
                name=f"Parent Task {i}",
                description=f"Description for task {i}",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[],
                labels=[],
            )
            for i in range(1, 11)  # 10 parent tasks
        ]

    @pytest.fixture
    def subtasks_data(self):
        """Create subtask data for 10 parents (3 subtasks each = 30 total)."""
        return [
            {
                "name": f"Subtask {j} for Task {i}",
                "description": f"Subtask description {j}",
                "estimated_hours": 1.0,
                "dependencies": [],
            }
            for i in range(1, 11)
            for j in range(1, 4)
        ]

    @pytest.mark.asyncio
    async def test_project_tasks_populated_after_first_refresh(
        self, mock_server, parent_tasks, subtasks_data
    ):
        """Test that project_tasks includes subtasks after first refresh."""
        # Arrange - simulate what create_project does
        # 1. Add subtasks to subtask_manager (without project_tasks reference)
        for i, parent_task in enumerate(parent_tasks):
            parent_id = parent_task.id
            task_subtasks = subtasks_data[i * 3 : (i + 1) * 3]
            mock_server.subtask_manager.add_subtasks(
                parent_task_id=parent_id,
                subtasks=task_subtasks,
                project_tasks=None,  # Not passed during create_project!
            )

        # 2. Mock kanban_client to return parent tasks
        mock_server.kanban_client.get_all_tasks.return_value = parent_tasks

        # Act - call refresh_project_state like create_project does
        await mock_server.refresh_project_state()

        # Assert
        assert mock_server.project_tasks is not None, "project_tasks should not be None"
        assert len(mock_server.project_tasks) == 40, (
            f"Expected 40 tasks (10 parents + 30 subtasks), "
            f"got {len(mock_server.project_tasks)}"
        )

        # Verify parents are included
        parent_ids = [t.id for t in parent_tasks]
        project_task_ids = [t.id for t in mock_server.project_tasks]
        for parent_id in parent_ids:
            assert parent_id in project_task_ids, f"Parent {parent_id} missing!"

        # Verify subtasks are included
        subtask_count = sum(
            1 for t in mock_server.project_tasks if getattr(t, "is_subtask", False)
        )
        assert subtask_count == 30, f"Expected 30 subtasks, got {subtask_count}"

    @pytest.mark.asyncio
    async def test_migration_runs_only_once(self, mock_server, parent_tasks):
        """Test that migration only runs once, even with multiple refreshes."""
        # Arrange
        subtasks = [
            {
                "name": f"Subtask {i}",
                "description": f"Description {i}",
                "estimated_hours": 1.0,
                "dependencies": [],
            }
            for i in range(3)
        ]
        mock_server.subtask_manager.add_subtasks(
            parent_task_id=parent_tasks[0].id,
            subtasks=subtasks,
            project_tasks=None,
        )
        mock_server.kanban_client.get_all_tasks.return_value = parent_tasks[:1]

        # Act - refresh twice
        await mock_server.refresh_project_state()
        first_count = len(mock_server.project_tasks)

        await mock_server.refresh_project_state()
        second_count = len(mock_server.project_tasks)

        # Assert - count should be same (no duplicate subtasks)
        assert (
            first_count == 4
        ), f"Expected 4 tasks after first refresh, got {first_count}"
        assert second_count == 4, (
            f"Expected 4 tasks after second refresh, got {second_count}. "
            "This indicates subtasks were migrated twice!"
        )

    @pytest.mark.asyncio
    async def test_empty_kanban_response_doesnt_break_migration(
        self, mock_server, parent_tasks, subtasks_data
    ):
        """Test migration when kanban returns empty list initially."""
        # Arrange - add subtasks to subtask_manager
        for i, parent_task in enumerate(parent_tasks):
            parent_id = parent_task.id
            task_subtasks = subtasks_data[i * 3 : (i + 1) * 3]
            mock_server.subtask_manager.add_subtasks(
                parent_task_id=parent_id, subtasks=task_subtasks, project_tasks=None
            )

        # First refresh: Kanban returns empty (Planka hasn't persisted yet)
        mock_server.kanban_client.get_all_tasks.return_value = []

        # Act
        await mock_server.refresh_project_state()

        # Assert - migration should skip because no parent tasks exist
        assert (
            len(mock_server.project_tasks) == 0
        ), "Should be empty when Kanban returns no tasks"

        # Now simulate second refresh (after Planka persists)
        mock_server.kanban_client.get_all_tasks.return_value = parent_tasks

        # Act - refresh again
        await mock_server.refresh_project_state()

        # Assert - NOW migration should work
        # But migration already ran once, so _subtasks_migrated is True
        # This is the BUG! Migration won't run again because flag is set.
        # Expected: 40 tasks (10 parents + 30 subtasks)
        # Actual: 10 tasks (only parents, subtasks skipped)

        # This test documents the bug - migration ran with empty parent list,
        # set the flag to True, then subsequent refreshes can't migrate anymore
        assert len(mock_server.project_tasks) >= 40, (
            f"BUG: Expected 40 tasks after second refresh with parent tasks, "
            f"got {len(mock_server.project_tasks)}. Migration flag prevents retry."
        )
