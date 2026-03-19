"""
Unit tests for task recovery system.

These tests document the current behavior of TaskRecoveryManager
before refactoring to remove unused heartbeat code.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.core.task_recovery import (
    RecoveryReason,
    TaskRecoveryManager,
    TaskRecoveryMonitor,
)


@pytest.fixture
def mock_kanban_client():
    """Create mock kanban client."""
    client = AsyncMock()
    client.get_all_tasks = AsyncMock(return_value=[])
    client.update_task_status = AsyncMock()
    return client


@pytest.fixture
def mock_assignment_persistence():
    """Create mock assignment persistence."""
    persistence = AsyncMock()
    persistence.load_assignments = AsyncMock(return_value={})
    persistence.remove_assignment = AsyncMock()
    return persistence


@pytest.fixture
def recovery_manager(mock_kanban_client, mock_assignment_persistence):
    """Create TaskRecoveryManager instance."""
    return TaskRecoveryManager(
        kanban_client=mock_kanban_client,
        assignment_persistence=mock_assignment_persistence,
        agent_timeout_minutes=30,
        task_stuck_hours=24,
        max_recovery_attempts=3,
    )


class TestTaskRecoveryManagerInit:
    """Test TaskRecoveryManager initialization."""

    def test_init_creates_tracking_dictionaries(
        self, mock_kanban_client, mock_assignment_persistence
    ):
        """Test that initialization creates required tracking structures."""
        manager = TaskRecoveryManager(
            kanban_client=mock_kanban_client,
            assignment_persistence=mock_assignment_persistence,
        )

        # Verify tracking structures exist
        assert hasattr(manager, "recovery_attempts")
        assert isinstance(manager.recovery_attempts, dict)
        assert len(manager.recovery_attempts) == 0

        assert hasattr(manager, "tasks_being_recovered")
        assert isinstance(manager.tasks_being_recovered, set)
        assert len(manager.tasks_being_recovered) == 0

        assert hasattr(manager, "recovery_history")
        assert isinstance(manager.recovery_history, list)
        assert len(manager.recovery_history) == 0

    def test_init_with_custom_timeouts(
        self, mock_kanban_client, mock_assignment_persistence
    ):
        """Test initialization with custom timeout values."""
        manager = TaskRecoveryManager(
            kanban_client=mock_kanban_client,
            assignment_persistence=mock_assignment_persistence,
            agent_timeout_minutes=60,
            task_stuck_hours=48,
            max_recovery_attempts=5,
        )

        assert manager.agent_timeout_minutes == 60
        assert manager.task_stuck_hours == 48
        assert manager.max_recovery_attempts == 5


class TestFindAbandonedTasks:
    """Test finding abandoned tasks."""

    @pytest.mark.asyncio
    async def test_find_abandoned_tasks_empty_board(self, recovery_manager):
        """Test finding abandoned tasks when board is empty."""
        abandoned = await recovery_manager.find_abandoned_tasks()

        assert abandoned == []

    @pytest.mark.asyncio
    async def test_find_abandoned_tasks_with_in_progress_no_assignment(
        self, recovery_manager, mock_kanban_client
    ):
        """Test task in progress but not in assignments."""
        # Create a task that's in progress
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        mock_kanban_client.get_all_tasks.return_value = [task]

        abandoned = await recovery_manager.find_abandoned_tasks()

        assert len(abandoned) == 1
        assert abandoned[0][0].id == "task-1"
        assert abandoned[0][1] == "unknown"
        assert abandoned[0][2] == RecoveryReason.TASK_ABANDONED

    @pytest.mark.asyncio
    async def test_find_abandoned_tasks_skips_already_recovering(
        self, recovery_manager, mock_kanban_client
    ):
        """Test that tasks already being recovered are skipped."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        mock_kanban_client.get_all_tasks.return_value = [task]

        # Mark task as being recovered
        recovery_manager.tasks_being_recovered.add("task-1")

        abandoned = await recovery_manager.find_abandoned_tasks()

        assert len(abandoned) == 0


class TestRecoverTask:
    """Test task recovery logic."""

    @pytest.mark.asyncio
    async def test_recover_task_success(
        self, recovery_manager, mock_kanban_client, mock_assignment_persistence
    ):
        """Test successful task recovery."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        success = await recovery_manager.recover_task(
            task, "agent-1", RecoveryReason.AGENT_TIMEOUT
        )

        assert success is True
        assert recovery_manager.recovery_attempts["task-1"] == 1
        assert len(recovery_manager.recovery_history) == 1
        assert recovery_manager.recovery_history[0]["task_id"] == "task-1"
        assert recovery_manager.recovery_history[0]["reason"] == "agent_timeout"

        # Verify calls
        mock_assignment_persistence.remove_assignment.assert_called_once_with("agent-1")
        mock_kanban_client.update_task_status.assert_called_once_with(
            "task-1", TaskStatus.TODO
        )

    @pytest.mark.asyncio
    async def test_recover_task_already_recovering(self, recovery_manager):
        """Test that recovery fails if task is already being recovered."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        # Mark task as being recovered
        recovery_manager.tasks_being_recovered.add("task-1")

        success = await recovery_manager.recover_task(
            task, "agent-1", RecoveryReason.AGENT_TIMEOUT
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_recover_task_max_attempts_warning(
        self, recovery_manager, mock_kanban_client, caplog
    ):
        """Test that warning is logged when max recovery attempts reached."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        # Set recovery attempts to max
        recovery_manager.recovery_attempts["task-1"] = 2
        recovery_manager.max_recovery_attempts = 3

        await recovery_manager.recover_task(
            task, "agent-1", RecoveryReason.AGENT_TIMEOUT
        )

        # Should now be at max (3)
        assert recovery_manager.recovery_attempts["task-1"] == 3

    @pytest.mark.asyncio
    async def test_recover_task_cleans_up_on_completion(self, recovery_manager):
        """Test that tasks_being_recovered is cleaned up after recovery."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        await recovery_manager.recover_task(
            task, "agent-1", RecoveryReason.AGENT_TIMEOUT
        )

        # Should be removed from tracking set
        assert "task-1" not in recovery_manager.tasks_being_recovered


class TestRecoveryStats:
    """Test recovery statistics."""

    def test_get_recovery_stats_empty(self, recovery_manager):
        """Test getting stats when no recoveries have occurred."""
        stats = recovery_manager.get_recovery_stats()

        assert stats["recovery_attempts"] == {}
        assert stats["high_recovery_tasks"] == []
        assert stats["recovery_history_count"] == 0
        assert stats["recent_recoveries"] == []
        assert stats["recoveries_by_reason"] == {}

    @pytest.mark.asyncio
    async def test_get_recovery_stats_after_recoveries(self, recovery_manager):
        """Test getting stats after some recoveries."""
        # Create and recover a task
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        await recovery_manager.recover_task(
            task, "agent-1", RecoveryReason.AGENT_TIMEOUT
        )

        stats = recovery_manager.get_recovery_stats()

        assert stats["recovery_attempts"] == {"task-1": 1}
        assert stats["high_recovery_tasks"] == []
        assert stats["recovery_history_count"] == 1
        assert len(stats["recent_recoveries"]) == 1
        assert stats["recoveries_by_reason"]["agent_timeout"] == 1


class TestManualRecovery:
    """Test manual recovery functionality."""

    @pytest.mark.asyncio
    async def test_manual_recover_task_success(
        self, recovery_manager, mock_kanban_client, mock_assignment_persistence
    ):
        """Test manual recovery of a task."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        mock_kanban_client.get_all_tasks.return_value = [task]
        mock_assignment_persistence.load_assignments.return_value = {
            "agent-1": {
                "task_id": "task-1",
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }
        }

        success = await recovery_manager.manual_recover_task("task-1")

        assert success is True
        assert len(recovery_manager.recovery_history) == 1
        assert recovery_manager.recovery_history[0]["reason"] == "manual_recovery"

    @pytest.mark.asyncio
    async def test_manual_recover_task_not_found(
        self, recovery_manager, mock_kanban_client
    ):
        """Test manual recovery when task not found."""
        mock_kanban_client.get_all_tasks.return_value = []

        success = await recovery_manager.manual_recover_task("task-1")

        assert success is False

    @pytest.mark.asyncio
    async def test_manual_recover_task_not_in_progress(
        self, recovery_manager, mock_kanban_client
    ):
        """Test manual recovery when task is not in progress."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.TODO,  # Not in progress
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        mock_kanban_client.get_all_tasks.return_value = [task]

        success = await recovery_manager.manual_recover_task("task-1")

        assert success is False


class TestTaskRecoveryMonitor:
    """Test TaskRecoveryMonitor."""

    def test_monitor_init(self, recovery_manager):
        """Test monitor initialization."""
        monitor = TaskRecoveryMonitor(recovery_manager, check_interval_minutes=5)

        assert monitor.recovery_manager == recovery_manager
        assert monitor.check_interval == 300  # 5 minutes in seconds
        assert monitor._running is False
        assert monitor._monitor_task is None

    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, recovery_manager):
        """Test starting and stopping the monitor."""
        monitor = TaskRecoveryMonitor(recovery_manager, check_interval_minutes=5)

        await monitor.start()
        assert monitor._running is True
        assert monitor._monitor_task is not None

        await monitor.stop()
        assert monitor._running is False


class TestIsTaskStuck:
    """Test task stuck detection."""

    @pytest.mark.asyncio
    async def test_task_stuck_no_progress_update(self, recovery_manager):
        """Test detecting stuck task with no progress updates."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        # Assignment with old timestamp
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        assignment = {
            "task_id": "task-1",
            "assigned_at": old_time.isoformat(),
        }

        is_stuck = await recovery_manager._is_task_stuck(task, assignment)

        assert is_stuck is True

    @pytest.mark.asyncio
    async def test_task_not_stuck_recent_update(self, recovery_manager):
        """Test that task with recent updates is not considered stuck."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=4.0,
        )

        # Assignment with recent progress update
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
        assignment = {
            "task_id": "task-1",
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "last_progress_update": recent_time.isoformat(),
        }

        is_stuck = await recovery_manager._is_task_stuck(task, assignment)

        assert is_stuck is False
