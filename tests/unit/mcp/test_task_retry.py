"""
Unit tests for intelligent task retry functionality
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.models import Priority, Task, TaskAssignment, TaskStatus
from src.marcus_mcp.tools.task import calculate_retry_after_seconds


class TestCalculateRetryAfterSeconds:
    """Test suite for intelligent wait time calculation"""

    @pytest.mark.asyncio
    async def test_no_tasks_in_progress_returns_default(self):
        """Test returns default 5 min when no tasks in progress"""
        # Arrange
        mock_state = Mock()
        mock_state.agent_tasks = {}  # No tasks assigned
        mock_state.project_tasks = []

        # Act
        result = await calculate_retry_after_seconds(mock_state)

        # Assert
        assert result["retry_after_seconds"] == 300  # 5 minutes
        assert "No tasks currently in progress" in result["reason"]
        assert "blocking_task" not in result

    @pytest.mark.asyncio
    async def test_calculates_eta_from_progress(self):
        """Test calculates ETA based on current task progress"""
        # Arrange
        mock_state = Mock()

        # Task that started 30 min ago and is 75% done
        # Expected: 30 min / 75% = 40 min total, 10 min remaining
        task = Task(
            id="task_1",
            name="Database Setup",
            description="Setup DB",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
            labels=["backend"],
        )
        task.progress = 75  # 75% done

        assignment = TaskAssignment(
            task_id="task_1",
            task_name="Database Setup",
            description="Setup DB",
            instructions="Do it",
            estimated_hours=1.0,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to="agent_1",
            assigned_at=datetime.now() - timedelta(minutes=30),  # Started 30 min ago
            due_date=None,
        )

        mock_state.agent_tasks = {"agent_1": assignment}
        mock_state.project_tasks = [task]

        # Mock memory (not needed for progress-based calculation)
        mock_memory = AsyncMock()
        mock_memory.get_global_median_duration = AsyncMock(return_value=1.0)
        mock_state.memory = mock_memory

        # Act
        result = await calculate_retry_after_seconds(mock_state)

        # Assert
        # Should be roughly 10 minutes (600 seconds) + 10% buffer
        # 600 + 60 = 660 seconds = 11 minutes
        assert 600 <= result["retry_after_seconds"] <= 720  # Allow some margin
        assert "Database Setup" in result["reason"]
        assert "blocking_task" not in result

    @pytest.mark.asyncio
    async def test_uses_historical_median_when_no_progress(self):
        """Test falls back to historical median when progress is 0"""
        # Arrange
        mock_state = Mock()

        # Task with no progress yet
        task = Task(
            id="task_1",
            name="API Development",
            description="Build API",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["backend"],
        )
        task.progress = 0  # No progress yet

        assignment = TaskAssignment(
            task_id="task_1",
            task_name="API Development",
            description="Build API",
            instructions="Do it",
            estimated_hours=2.0,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to="agent_1",
            assigned_at=datetime.now() - timedelta(minutes=5),
            due_date=None,
        )

        mock_state.agent_tasks = {"agent_1": assignment}
        mock_state.project_tasks = [task]

        # Mock memory with 2-hour historical median
        mock_memory = AsyncMock()
        mock_memory.get_global_median_duration = AsyncMock(return_value=2.0)
        mock_state.memory = mock_memory

        # Act
        result = await calculate_retry_after_seconds(mock_state)

        # Assert
        # Should use 2 hour median: 2 * 3600 = 7200 seconds + 10% buffer
        # But capped at 1 hour (3600 seconds)
        assert result["retry_after_seconds"] == 3600  # Capped at 1 hour
        assert "API Development" in result["reason"]

    @pytest.mark.asyncio
    async def test_picks_soonest_completion(self):
        """Test picks task with soonest completion when multiple tasks in progress"""
        # Arrange
        mock_state = Mock()

        # Task 1: Will complete in ~10 minutes (75% done, started 30 min ago)
        task1 = Task(
            id="task_1",
            name="Quick Task",
            description="Fast",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=1.0,
        )
        task1.progress = 75

        assignment1 = TaskAssignment(
            task_id="task_1",
            task_name="Quick Task",
            description="Fast",
            instructions="Do it",
            estimated_hours=1.0,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to="agent_1",
            assigned_at=datetime.now() - timedelta(minutes=30),
            due_date=None,
        )

        # Task 2: Will complete in ~60 minutes (50% done, started 60 min ago)
        task2 = Task(
            id="task_2",
            name="Slow Task",
            description="Slow",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            assigned_to="agent_2",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
        )
        task2.progress = 50

        assignment2 = TaskAssignment(
            task_id="task_2",
            task_name="Slow Task",
            description="Slow",
            instructions="Do it",
            estimated_hours=2.0,
            priority=Priority.HIGH,
            dependencies=[],
            assigned_to="agent_2",
            assigned_at=datetime.now() - timedelta(minutes=60),
            due_date=None,
        )

        mock_state.agent_tasks = {"agent_1": assignment1, "agent_2": assignment2}
        mock_state.project_tasks = [task1, task2]

        mock_memory = AsyncMock()
        mock_memory.get_global_median_duration = AsyncMock(return_value=1.0)
        mock_state.memory = mock_memory

        # Act
        result = await calculate_retry_after_seconds(mock_state)

        # Assert
        # Should pick task1 (soonest) - verify by checking the reason contains Quick Task
        assert "Quick Task" in result["reason"]
        assert "blocking_task" not in result

    @pytest.mark.asyncio
    async def test_caps_maximum_wait_at_one_hour(self):
        """Test wait time is capped at 1 hour maximum"""
        # Arrange
        mock_state = Mock()

        # Task that will take a very long time
        task = Task(
            id="task_1",
            name="Long Task",
            description="Takes forever",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.LOW,
            assigned_to="agent_1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=10.0,
        )
        task.progress = 0  # No progress

        assignment = TaskAssignment(
            task_id="task_1",
            task_name="Long Task",
            description="Takes forever",
            instructions="Do it",
            estimated_hours=10.0,
            priority=Priority.LOW,
            dependencies=[],
            assigned_to="agent_1",
            assigned_at=datetime.now() - timedelta(minutes=10),
            due_date=None,
        )

        mock_state.agent_tasks = {"agent_1": assignment}
        mock_state.project_tasks = [task]

        # Mock memory with very long median (10 hours)
        mock_memory = AsyncMock()
        mock_memory.get_global_median_duration = AsyncMock(return_value=10.0)
        mock_state.memory = mock_memory

        # Act
        result = await calculate_retry_after_seconds(mock_state)

        # Assert
        # Should be capped at 1 hour (3600 seconds)
        assert result["retry_after_seconds"] == 3600
