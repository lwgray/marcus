"""
Unit tests for the assignment lease system.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.assignment_lease import (
    AssignmentLease,
    AssignmentLeaseManager,
    LeaseMonitor,
    LeaseStatus,
)
from src.core.models import Priority, RecoveryInfo, Task, TaskStatus


class TestAssignmentLease:
    """Test suite for AssignmentLease data class."""

    def test_lease_creation(self):
        """Test basic lease creation."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=4)

        lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=now,
            lease_expires=expires,
            last_renewed=now,
        )

        assert lease.task_id == "task-123"
        assert lease.agent_id == "agent-001"
        assert not lease.is_expired
        assert lease.status == LeaseStatus.ACTIVE

    def test_lease_expiration(self):
        """Test lease expiration detection."""
        now = datetime.now(timezone.utc)

        # Create expired lease
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=now - timedelta(hours=5),
            lease_expires=now - timedelta(hours=1),
            last_renewed=now - timedelta(hours=5),
        )

        assert expired_lease.is_expired
        assert expired_lease.status == LeaseStatus.EXPIRED

    def test_lease_expiring_soon(self):
        """Test detection of leases expiring soon."""
        now = datetime.now(timezone.utc)

        # Lease expiring in 30 minutes
        expiring_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=now,
            lease_expires=now + timedelta(minutes=30),
            last_renewed=now,
        )

        assert expiring_lease.is_expiring_soon
        assert expiring_lease.status == LeaseStatus.EXPIRING_SOON
        assert not expiring_lease.is_expired

    def test_renewal_duration_calculation(self):
        """Test lease renewal duration calculation."""
        now = datetime.now(timezone.utc)
        base_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=now,
            lease_expires=now + timedelta(hours=4),
            last_renewed=now,
        )

        # High progress - shorter renewal
        base_lease.progress_percentage = 80
        duration = base_lease.calculate_renewal_duration()
        assert duration == timedelta(hours=2.0)

        # Medium progress
        base_lease.progress_percentage = 60
        duration = base_lease.calculate_renewal_duration()
        assert duration == timedelta(hours=3.0)

        # Low progress with many renewals - stuck task
        base_lease.progress_percentage = 20
        base_lease.renewal_count = 3
        duration = base_lease.calculate_renewal_duration()
        assert duration == timedelta(hours=2.0)

        # Complex task
        base_lease.estimated_hours = 10
        base_lease.progress_percentage = 50
        base_lease.renewal_count = 1  # Reset renewal count
        duration = base_lease.calculate_renewal_duration()
        assert duration == timedelta(hours=6.0)  # 4 * 1.5


class TestAssignmentLeaseManager:
    """Test suite for AssignmentLeaseManager."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock kanban client."""
        client = Mock()
        client.update_task_status = AsyncMock()
        client.update_task = AsyncMock()
        return client

    @pytest.fixture
    def mock_persistence(self):
        """Create mock assignment persistence."""
        persistence = Mock()
        persistence.get_assignment = AsyncMock(
            return_value={
                "task_id": "task-123",
                "assigned_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        persistence.save_assignment = AsyncMock()
        persistence.remove_assignment = AsyncMock()
        persistence.load_assignments = AsyncMock(return_value={})
        return persistence

    @pytest.fixture
    def lease_manager(self, mock_kanban_client, mock_persistence):
        """Create lease manager instance."""
        return AssignmentLeaseManager(
            mock_kanban_client, mock_persistence, default_lease_hours=4.0
        )

    @pytest.mark.asyncio
    async def test_create_lease(self, lease_manager):
        """Test lease creation."""
        task = Task(
            id="task-123",
            name="Test Task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
        )

        lease = await lease_manager.create_lease("task-123", "agent-001", task)

        assert lease.task_id == "task-123"
        assert lease.agent_id == "agent-001"
        assert lease.estimated_hours == 5.0
        assert not lease.is_expired
        assert "task-123" in lease_manager.active_leases

    @pytest.mark.asyncio
    async def test_renew_lease(self, lease_manager):
        """Test lease renewal."""
        # Create initial lease
        lease = await lease_manager.create_lease("task-123", "agent-001")

        initial_expiry = lease.lease_expires

        # Renew lease
        renewed_lease = await lease_manager.renew_lease("task-123", 50, "Halfway done")

        assert renewed_lease is not None
        assert renewed_lease.renewal_count == 1
        assert renewed_lease.progress_percentage == 50
        assert renewed_lease.lease_expires > initial_expiry

    @pytest.mark.asyncio
    async def test_renew_expired_lease_fails(self, lease_manager):
        """Test that expired leases cannot be renewed."""
        # Create expired lease
        lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=5),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        lease_manager.active_leases["task-123"] = lease

        # Try to renew
        renewed_lease = await lease_manager.renew_lease("task-123", 50, "Progress")

        assert renewed_lease is None

    @pytest.mark.asyncio
    async def test_check_expired_leases(self, lease_manager):
        """Test detection of expired leases."""
        now = datetime.now(timezone.utc)

        # Add mix of leases
        active_lease = AssignmentLease(
            task_id="task-active",
            agent_id="agent-001",
            assigned_at=now,
            lease_expires=now + timedelta(hours=2),
            last_renewed=now,
        )

        expired_lease = AssignmentLease(
            task_id="task-expired",
            agent_id="agent-002",
            assigned_at=now - timedelta(hours=5),
            lease_expires=now - timedelta(hours=1),
            last_renewed=now - timedelta(hours=5),
        )

        lease_manager.active_leases = {
            "task-active": active_lease,
            "task-expired": expired_lease,
        }

        expired = await lease_manager.check_expired_leases()

        assert len(expired) == 1
        assert expired[0].task_id == "task-expired"

    @pytest.mark.asyncio
    async def test_recover_expired_lease(
        self, lease_manager, mock_kanban_client, mock_persistence
    ):
        """Test recovery of expired lease."""
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=5),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=5),
            progress_percentage=30,
        )

        lease_manager.active_leases["task-123"] = expired_lease

        success = await lease_manager.recover_expired_lease(expired_lease)

        assert success
        assert "task-123" not in lease_manager.active_leases
        mock_persistence.remove_assignment.assert_called_once_with("agent-001")
        mock_kanban_client.update_task_status.assert_called_once_with(
            "task-123", TaskStatus.TODO
        )

    @pytest.mark.asyncio
    async def test_get_expiring_leases(self, lease_manager):
        """Test getting leases that are expiring soon."""
        now = datetime.now(timezone.utc)

        # Add various leases
        lease_manager.active_leases = {
            "task-active": AssignmentLease(
                task_id="task-active",
                agent_id="agent-001",
                assigned_at=now,
                lease_expires=now + timedelta(hours=4),
                last_renewed=now,
            ),
            "task-expiring": AssignmentLease(
                task_id="task-expiring",
                agent_id="agent-002",
                assigned_at=now,
                lease_expires=now + timedelta(minutes=30),
                last_renewed=now,
            ),
            "task-expired": AssignmentLease(
                task_id="task-expired",
                agent_id="agent-003",
                assigned_at=now - timedelta(hours=5),
                lease_expires=now - timedelta(hours=1),
                last_renewed=now - timedelta(hours=5),
            ),
        }

        expiring = await lease_manager.get_expiring_leases()

        assert len(expiring) == 1
        assert expiring[0].task_id == "task-expiring"

    def test_lease_statistics(self, lease_manager):
        """Test lease statistics calculation."""
        now = datetime.now(timezone.utc)

        # Add various leases
        lease_manager.active_leases = {
            "task-1": AssignmentLease(
                task_id="task-1",
                agent_id="agent-001",
                assigned_at=now,
                lease_expires=now + timedelta(hours=4),
                last_renewed=now,
                renewal_count=2,
            ),
            "task-2": AssignmentLease(
                task_id="task-2",
                agent_id="agent-002",
                assigned_at=now,
                lease_expires=now + timedelta(minutes=30),
                last_renewed=now,
                renewal_count=8,
            ),
            "task-3": AssignmentLease(
                task_id="task-3",
                agent_id="agent-003",
                assigned_at=now - timedelta(hours=5),
                lease_expires=now - timedelta(hours=1),
                last_renewed=now - timedelta(hours=5),
                renewal_count=12,
            ),
        }

        stats = lease_manager.get_lease_statistics()

        assert stats["total_active"] == 3
        assert stats["expired"] == 1
        assert stats["expiring_soon"] == 1
        assert stats["high_renewal_count"] == 1  # Only task-3 has >= 10 renewals
        assert stats["average_renewal_count"] == (2 + 8 + 12) / 3


class TestLeaseMonitor:
    """Test suite for LeaseMonitor."""

    @pytest.fixture
    def mock_lease_manager(self):
        """Create mock lease manager."""
        manager = Mock()
        manager.load_active_leases = AsyncMock()
        manager.check_expired_leases = AsyncMock(return_value=[])
        manager.recover_expired_lease = AsyncMock(return_value=True)
        manager.get_lease_statistics = Mock(
            return_value={"total_active": 0, "expiring_soon": 0, "expired": 0}
        )
        manager.get_expiring_leases = AsyncMock(return_value=[])
        return manager

    @pytest.fixture
    def lease_monitor(self, mock_lease_manager):
        """Create lease monitor instance."""
        return LeaseMonitor(mock_lease_manager, check_interval_seconds=1)

    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, lease_monitor):
        """Test starting and stopping the monitor."""
        await lease_monitor.start()
        assert lease_monitor._running
        assert lease_monitor._monitor_task is not None

        await lease_monitor.stop()
        assert not lease_monitor._running

    @pytest.mark.asyncio
    async def test_monitor_recovers_expired_leases(
        self, lease_monitor, mock_lease_manager
    ):
        """Test that monitor recovers expired leases with smart checks."""
        # Set up expired leases
        expired_lease = Mock()
        expired_lease.task_id = "task-123"
        mock_lease_manager.check_expired_leases.return_value = [expired_lease]

        # Mock smart recovery check to allow recovery
        mock_lease_manager.should_recover_expired_lease = AsyncMock(return_value=True)

        # Start monitor
        await lease_monitor.start()

        # Wait for at least one check cycle
        await asyncio.sleep(1.5)

        # Stop monitor
        await lease_monitor.stop()

        # Verify recovery was attempted
        mock_lease_manager.check_expired_leases.assert_called()
        mock_lease_manager.should_recover_expired_lease.assert_called_with(
            expired_lease
        )
        mock_lease_manager.recover_expired_lease.assert_called_with(expired_lease)


class TestNaiveDatetimeBackwardsCompatibility:
    """Test suite for backwards compatibility with naive datetime persistence."""

    @pytest.mark.asyncio
    async def test_load_active_leases_handles_naive_datetimes(self):
        """Test that load_active_leases normalizes naive datetimes to UTC."""
        from src.core.assignment_persistence import AssignmentPersistence

        # Arrange - create mock persistence with NAIVE datetime strings
        # (simulating old data saved with naive datetime.isoformat())
        mock_persistence = Mock(spec=AssignmentPersistence)

        # Create naive datetime (no timezone info)
        # Simulating old data by stripping timezone from a UTC datetime
        aware_now = datetime.now(timezone.utc)
        naive_now = aware_now.replace(tzinfo=None)  # Strip timezone
        naive_iso = naive_now.isoformat()  # No +00:00 suffix

        old_assignment = {
            "task_id": "task-123",
            "assigned_at": naive_iso,  # Naive datetime string
            "lease_expires": naive_iso,  # Naive datetime string
            "lease_renewed_at": naive_iso,  # Naive datetime string
            "renewal_count": 0,
            "progress_percentage": 0,
        }

        mock_persistence.load_assignments = AsyncMock(
            return_value={"agent-001": old_assignment}
        )

        # Create lease manager with mock persistence
        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )

        # Act - load the old naive datetime assignments
        await lease_manager.load_active_leases()

        # Assert - lease should be created successfully
        assert len(lease_manager.active_leases) == 1
        lease = lease_manager.active_leases["task-123"]

        # All datetimes should be timezone-aware (UTC)
        assert lease.assigned_at.tzinfo is not None
        assert lease.assigned_at.tzinfo == timezone.utc
        assert lease.lease_expires.tzinfo is not None
        assert lease.lease_expires.tzinfo == timezone.utc
        assert lease.last_renewed.tzinfo is not None
        assert lease.last_renewed.tzinfo == timezone.utc

        # Should be able to call is_expired without TypeError
        _ = lease.is_expired  # This would raise TypeError before the fix

    @pytest.mark.asyncio
    async def test_load_active_leases_preserves_aware_datetimes(self):
        """Test that timezone-aware datetimes are preserved as-is."""
        from src.core.assignment_persistence import AssignmentPersistence

        # Arrange - create mock persistence with AWARE datetime strings
        mock_persistence = Mock(spec=AssignmentPersistence)

        aware_now = datetime.now(timezone.utc)
        aware_iso = aware_now.isoformat()  # Has +00:00 suffix

        new_assignment = {
            "task_id": "task-456",
            "assigned_at": aware_iso,
            "lease_expires": aware_iso,
            "lease_renewed_at": aware_iso,
            "renewal_count": 0,
            "progress_percentage": 0,
        }

        mock_persistence.load_assignments = AsyncMock(
            return_value={"agent-002": new_assignment}
        )

        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )

        # Act
        await lease_manager.load_active_leases()

        # Assert
        assert len(lease_manager.active_leases) == 1
        lease = lease_manager.active_leases["task-456"]

        # All datetimes should be timezone-aware (UTC)
        assert lease.assigned_at.tzinfo == timezone.utc
        assert lease.lease_expires.tzinfo == timezone.utc
        assert lease.last_renewed.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_load_active_leases_mixed_naive_and_aware(self):
        """Test loading a mix of old naive and new aware datetimes."""
        from src.core.assignment_persistence import AssignmentPersistence

        mock_persistence = Mock(spec=AssignmentPersistence)

        # Old assignment with naive datetimes
        # Simulating old data by stripping timezone from a UTC datetime
        aware_now = datetime.now(timezone.utc)
        naive_now = aware_now.replace(tzinfo=None)  # Strip timezone
        old_assignment = {
            "task_id": "old-task",
            "assigned_at": naive_now.isoformat(),
            "lease_expires": naive_now.isoformat(),
            "lease_renewed_at": naive_now.isoformat(),
            "renewal_count": 0,
            "progress_percentage": 0,
        }

        # New assignment with aware datetimes
        aware_now = datetime.now(timezone.utc)
        new_assignment = {
            "task_id": "new-task",
            "assigned_at": aware_now.isoformat(),
            "lease_expires": aware_now.isoformat(),
            "lease_renewed_at": aware_now.isoformat(),
            "renewal_count": 0,
            "progress_percentage": 0,
        }

        mock_persistence.load_assignments = AsyncMock(
            return_value={
                "agent-old": old_assignment,
                "agent-new": new_assignment,
            }
        )

        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )

        # Act
        await lease_manager.load_active_leases()

        # Assert - both leases loaded successfully
        assert len(lease_manager.active_leases) == 2

        old_lease = lease_manager.active_leases["old-task"]
        new_lease = lease_manager.active_leases["new-task"]

        # Both should be timezone-aware now
        assert old_lease.assigned_at.tzinfo == timezone.utc
        assert new_lease.assigned_at.tzinfo == timezone.utc

        # Both should be comparable without TypeError
        assert old_lease.time_remaining  # Computed successfully
        assert new_lease.time_remaining  # Computed successfully


class TestRecoveryInfo:
    """Test suite for RecoveryInfo dataclass."""

    def test_recovery_info_creation(self):
        """Test basic RecoveryInfo creation."""
        now = datetime.now(timezone.utc)
        recovery_info = RecoveryInfo(
            recovered_at=now,
            recovered_from_agent="agent-001",
            previous_progress=50,
            time_spent_minutes=120.5,
            recovery_reason="lease_expired",
            instructions="Check git history for previous work",
        )

        assert recovery_info.recovered_from_agent == "agent-001"
        assert recovery_info.previous_progress == 50
        assert recovery_info.time_spent_minutes == 120.5
        assert recovery_info.recovery_reason == "lease_expired"
        assert "git history" in recovery_info.instructions

    def test_recovery_info_to_dict(self):
        """Test RecoveryInfo serialization to dictionary."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        recovery_info = RecoveryInfo(
            recovered_at=now,
            recovered_from_agent="agent-001",
            previous_progress=50,
            time_spent_minutes=120.5,
            recovery_reason="lease_expired",
            instructions="Check git history",
            recovery_expires_at=expires,
        )

        data = recovery_info.to_dict()

        assert data["recovered_from_agent"] == "agent-001"
        assert data["previous_progress"] == 50
        assert data["time_spent_minutes"] == 120.5
        assert data["recovery_reason"] == "lease_expired"
        assert data["instructions"] == "Check git history"
        assert data["recovery_expires_at"] == expires.isoformat()

    def test_recovery_info_from_dict(self):
        """Test RecoveryInfo deserialization from dictionary."""
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=24)

        data = {
            "recovered_at": now.isoformat(),
            "recovered_from_agent": "agent-001",
            "previous_progress": 50,
            "time_spent_minutes": 120.5,
            "recovery_reason": "lease_expired",
            "instructions": "Check git history",
            "recovery_expires_at": expires.isoformat(),
        }

        recovery_info = RecoveryInfo.from_dict(data)

        assert recovery_info.recovered_from_agent == "agent-001"
        assert recovery_info.previous_progress == 50
        assert recovery_info.time_spent_minutes == 120.5
        assert recovery_info.recovery_reason == "lease_expired"
        assert recovery_info.recovery_expires_at is not None

    def test_recovery_info_optional_expiration(self):
        """Test RecoveryInfo with no expiration."""
        now = datetime.now(timezone.utc)
        recovery_info = RecoveryInfo(
            recovered_at=now,
            recovered_from_agent="agent-001",
            previous_progress=50,
            time_spent_minutes=120.5,
            recovery_reason="lease_expired",
            instructions="Check git history",
        )

        assert recovery_info.recovery_expires_at is None

        data = recovery_info.to_dict()
        assert data["recovery_expires_at"] is None


class TestRecoveryHandoffDualWrite:
    """Test suite for recovery handoff dual-write (task model + Kanban)."""

    @pytest.fixture
    def mock_kanban_client(self):
        """Create mock kanban client with comment support."""
        client = Mock()
        client.update_task_status = AsyncMock()
        client.add_comment = AsyncMock()
        return client

    @pytest.fixture
    def mock_persistence(self):
        """Create mock assignment persistence."""
        persistence = Mock()
        persistence.get_assignment = AsyncMock(return_value=None)
        persistence.save_assignment = AsyncMock()
        persistence.remove_assignment = AsyncMock()
        persistence.load_assignments = AsyncMock(return_value={})
        return persistence

    @pytest.fixture
    def lease_manager(self, mock_kanban_client, mock_persistence):
        """Create lease manager instance."""
        return AssignmentLeaseManager(
            mock_kanban_client, mock_persistence, default_lease_hours=4.0
        )

    @pytest.fixture
    def mock_task(self):
        """Create a mock task for testing."""
        task = Task(
            id="task-123",
            name="Test Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to="agent-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
        )
        return task

    @pytest.mark.asyncio
    async def test_recover_expired_lease_creates_recovery_info(
        self, lease_manager, mock_task
    ):
        """Test that recovery populates task.recovery_info."""
        # Arrange
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=2),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=2),
            progress_percentage=30,
            last_progress_message="Working on it",
        )

        # Mock the internal _find_task method to return our mock task
        with patch.object(lease_manager, "_find_task", return_value=mock_task):
            # Act
            success = await lease_manager.recover_expired_lease(expired_lease)

            # Assert
            assert success
            assert mock_task.recovery_info is not None
            assert mock_task.recovery_info.recovered_from_agent == "agent-001"
            assert mock_task.recovery_info.previous_progress == 30
            assert mock_task.recovery_info.recovery_reason == "lease_expired"
            assert mock_task.recovery_info.time_spent_minutes > 0

    @pytest.mark.asyncio
    async def test_recover_expired_lease_dual_writes_to_kanban(
        self, lease_manager, mock_kanban_client, mock_task
    ):
        """Test that recovery writes BOTH to task model AND Kanban comment."""
        # Arrange
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=2),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=2),
            progress_percentage=30,
        )

        # Mock the internal _find_task method
        with patch.object(lease_manager, "_find_task", return_value=mock_task):
            # Act
            success = await lease_manager.recover_expired_lease(expired_lease)

            # Assert dual-write
            assert success

            # 1. Task model should have recovery_info
            assert mock_task.recovery_info is not None

            # 2. Kanban comment should be posted
            mock_kanban_client.add_comment.assert_called_once()
            comment_call = mock_kanban_client.add_comment.call_args
            assert comment_call[0][0] == "task-123"  # task_id
            comment_text = comment_call[0][1]
            assert "TASK RECOVERED FROM AGENT agent-001" in comment_text
            assert "30%" in comment_text

    @pytest.mark.asyncio
    async def test_recovery_continues_if_kanban_comment_fails(
        self, lease_manager, mock_kanban_client, mock_task
    ):
        """Test that recovery succeeds even if Kanban comment fails."""
        # Arrange
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=2),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=2),
            progress_percentage=30,
        )

        # Make Kanban comment fail
        mock_kanban_client.add_comment.side_effect = Exception("Kanban unavailable")

        with patch.object(lease_manager, "_find_task", return_value=mock_task):
            # Act - should not raise exception
            success = await lease_manager.recover_expired_lease(expired_lease)

            # Assert - recovery still succeeds
            assert success
            assert mock_task.recovery_info is not None

    @pytest.mark.asyncio
    async def test_recovery_info_includes_24hour_expiration(
        self, lease_manager, mock_task
    ):
        """Test that recovery info includes 24-hour expiration."""
        # Arrange
        now = datetime.now(timezone.utc)
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=now - timedelta(hours=2),
            lease_expires=now - timedelta(hours=1),
            last_renewed=now - timedelta(hours=2),
            progress_percentage=30,
        )

        with patch.object(lease_manager, "_find_task", return_value=mock_task):
            # Act
            await lease_manager.recover_expired_lease(expired_lease)

            # Assert
            assert mock_task.recovery_info is not None
            assert mock_task.recovery_info.recovery_expires_at is not None

            # Should expire in approximately 24 hours
            expiry_delta = mock_task.recovery_info.recovery_expires_at - datetime.now(
                timezone.utc
            )
            assert 23 <= expiry_delta.total_seconds() / 3600 <= 25  # 23-25 hours

    @pytest.mark.asyncio
    async def test_recovery_info_includes_git_instructions(
        self, lease_manager, mock_task
    ):
        """Test that recovery info includes helpful git instructions."""
        # Arrange
        expired_lease = AssignmentLease(
            task_id="task-123",
            agent_id="agent-001",
            assigned_at=datetime.now(timezone.utc) - timedelta(hours=2),
            lease_expires=datetime.now(timezone.utc) - timedelta(hours=1),
            last_renewed=datetime.now(timezone.utc) - timedelta(hours=2),
            progress_percentage=30,
        )

        with patch.object(lease_manager, "_find_task", return_value=mock_task):
            # Act
            await lease_manager.recover_expired_lease(expired_lease)

            # Assert
            assert mock_task.recovery_info is not None
            instructions = mock_task.recovery_info.instructions

            # Should include key guidance
            assert "agent-001" in instructions
            assert "git log" in instructions or "git" in instructions.lower()
            assert "30%" in instructions
            assert "avoid duplicated work" in instructions.lower()
