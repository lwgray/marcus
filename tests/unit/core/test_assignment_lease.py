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
        # Recovery uses update_task to atomically clear status + assigned_to
        mock_kanban_client.update_task.assert_called_once_with(
            "task-123", {"status": TaskStatus.TODO, "assigned_to": None}
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
        manager.active_leases = {}
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


class TestUpdateTimestampPersistence:
    """Test that update_timestamps survive persist/load cycle."""

    @pytest.mark.asyncio
    async def test_load_active_leases_restores_update_timestamps(self):
        """Test that update_timestamps are restored from persistence."""
        from src.core.assignment_persistence import AssignmentPersistence

        now = datetime.now(timezone.utc)
        timestamps = [
            (now - timedelta(seconds=180)).isoformat(),
            (now - timedelta(seconds=120)).isoformat(),
            (now - timedelta(seconds=60)).isoformat(),
        ]

        mock_persistence = Mock(spec=AssignmentPersistence)
        mock_persistence.load_assignments = AsyncMock(
            return_value={
                "agent-001": {
                    "task_id": "task-123",
                    "assigned_at": now.isoformat(),
                    "lease_expires": (now + timedelta(minutes=2)).isoformat(),
                    "lease_renewed_at": now.isoformat(),
                    "renewal_count": 3,
                    "progress_percentage": 50,
                    "update_timestamps": timestamps,
                }
            }
        )

        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )
        await lease_manager.load_active_leases()

        lease = lease_manager.active_leases["task-123"]
        assert len(lease.update_timestamps) == 3
        assert all(ts.tzinfo is not None for ts in lease.update_timestamps)

    @pytest.mark.asyncio
    async def test_load_active_leases_handles_missing_timestamps(self):
        """Test that missing update_timestamps defaults to empty list."""
        from src.core.assignment_persistence import AssignmentPersistence

        now = datetime.now(timezone.utc)
        mock_persistence = Mock(spec=AssignmentPersistence)
        mock_persistence.load_assignments = AsyncMock(
            return_value={
                "agent-001": {
                    "task_id": "task-456",
                    "assigned_at": now.isoformat(),
                    "lease_expires": (now + timedelta(minutes=2)).isoformat(),
                    "lease_renewed_at": now.isoformat(),
                    "renewal_count": 0,
                    "progress_percentage": 0,
                }
            }
        )

        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )
        await lease_manager.load_active_leases()

        lease = lease_manager.active_leases["task-456"]
        assert lease.update_timestamps == []

    @pytest.mark.asyncio
    async def test_persist_lease_saves_update_timestamps(self):
        """Test that _persist_lease includes update_timestamps."""
        from src.core.assignment_persistence import AssignmentPersistence

        now = datetime.now(timezone.utc)
        mock_persistence = Mock(spec=AssignmentPersistence)
        existing_assignment: dict[str, Any] = {
            "task_id": "task-789",
            "assigned_at": now.isoformat(),
        }
        mock_persistence.get_assignment = AsyncMock(return_value=existing_assignment)
        mock_persistence.save_assignment = AsyncMock()

        lease_manager = AssignmentLeaseManager(
            kanban_client=Mock(),
            assignment_persistence=mock_persistence,
        )

        lease = AssignmentLease(
            task_id="task-789",
            agent_id="agent-001",
            assigned_at=now,
            lease_expires=now + timedelta(minutes=2),
            last_renewed=now,
            update_timestamps=[
                now - timedelta(seconds=60),
                now,
            ],
        )

        await lease_manager._persist_lease(lease)

        assert "update_timestamps" in existing_assignment
        assert len(existing_assignment["update_timestamps"]) == 2


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

            # Should include key guidance for worktree recovery
            assert "agent-001" in instructions
            assert "marcus/agent-001" in instructions  # Branch name
            assert "git merge" in instructions  # Merge dead agent's branch
            assert "30%" in instructions


class TestExpiredLeaseProgressCapture:
    """
    Regression coverage for Issue #342: ``renew_lease`` must
    capture the agent's latest progress value even when the lease
    itself cannot be renewed because it's already expired.

    The dashboard-v70 Epictetus audit documented the exact bug:
    agent reported 25% then 50%, but the 50% report arrived after
    the lease silently expired. Without this capture, the renewal
    path returned None and dropped the 50% value on the floor.
    When the monitor later recovered the lease, the recovery
    context showed 25% (or 0% after a false-positive recovery
    recreated the lease), causing the recovering agent to rebuild
    from scratch — 341 lines of ghost source + 506 lines of ghost
    tests.

    The fix: on the ``lease.is_expired`` path in ``renew_lease``,
    still mutate ``lease.progress_percentage`` to reflect the
    agent's latest self-reported value before returning None.
    Guarded with ``>`` so the snapshot never regresses.
    """

    @pytest.fixture
    def mock_kanban_client(self):
        client = Mock()
        client.update_task_status = AsyncMock()
        client.update_task = AsyncMock()
        client.add_comment = AsyncMock()
        return client

    @pytest.fixture
    def mock_persistence(self):
        persistence = Mock()
        persistence.get_assignment = AsyncMock(return_value=None)
        persistence.save_assignment = AsyncMock()
        persistence.remove_assignment = AsyncMock()
        persistence.load_assignments = AsyncMock(return_value={})
        return persistence

    @pytest.fixture
    def lease_manager(self, mock_kanban_client, mock_persistence):
        return AssignmentLeaseManager(
            mock_kanban_client, mock_persistence, default_lease_hours=4.0
        )

    @pytest.fixture
    def real_task(self):
        """
        Use a REAL ``Task`` dataclass, not a Mock. This is the
        anti-trap from the first attempt at this fix: Mock()
        allowed inventing a ``progress`` attribute that the real
        Task class doesn't have, so the fix looked right in test
        but was a no-op in production. Real Task objects here
        force the fix to work on fields that actually exist.
        """
        return Task(
            id="task-342",
            name="Stale Progress Task",
            description="Test",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            estimated_hours=0.1,
            dependencies=[],
            labels=[],
            assigned_to="agent-001",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
        )

    async def _insert_expired_lease(
        self,
        manager: AssignmentLeaseManager,
        task_id: str,
        agent_id: str,
        initial_progress: int,
    ) -> AssignmentLease:
        """
        Insert an expired lease directly into ``active_leases`` so
        ``renew_lease`` has a target to operate on. Bypasses
        ``create_lease`` to avoid tripping on side effects.
        """
        now = datetime.now(timezone.utc)
        expired = AssignmentLease(
            task_id=task_id,
            agent_id=agent_id,
            assigned_at=now - timedelta(hours=2),
            lease_expires=now - timedelta(hours=1),
            last_renewed=now - timedelta(hours=2),
            progress_percentage=initial_progress,
        )
        async with manager.lease_lock:
            manager.active_leases[task_id] = expired
        return expired

    @pytest.mark.asyncio
    async def test_expired_lease_renewal_captures_higher_progress(self, lease_manager):
        """
        The bug scenario: lease expired at 25%, agent reports 50%
        via renew_lease. Renewal fails (lease is expired), but the
        50% value must land in ``lease.progress_percentage`` so
        the later recovery carries it forward.
        """
        expired = await self._insert_expired_lease(
            lease_manager, "task-342", "agent-001", initial_progress=25
        )

        result = await lease_manager.renew_lease(
            task_id="task-342", progress=50, message="halfway"
        )

        # Renewal still fails — lease can't be un-expired
        assert result is None
        # But the snapshot was updated
        assert expired.progress_percentage == 50
        assert expired.last_progress_message == "halfway"

    @pytest.mark.asyncio
    async def test_expired_lease_renewal_does_not_regress_progress(self, lease_manager):
        """
        Defensive: if a late report arrives out of order with a
        lower progress value, we must not regress the snapshot.
        Only strictly-higher values replace the stored progress.
        """
        expired = await self._insert_expired_lease(
            lease_manager, "task-342", "agent-001", initial_progress=50
        )

        result = await lease_manager.renew_lease(
            task_id="task-342", progress=30, message="out of order"
        )

        assert result is None
        assert expired.progress_percentage == 50  # preserved
        # last_progress_message also preserved because we only
        # update it when progress actually advances
        assert expired.last_progress_message != "out of order"

    @pytest.mark.asyncio
    async def test_recovery_uses_captured_progress_after_expired_update(
        self, lease_manager, real_task
    ):
        """
        End-to-end: agent reports 50% via renew_lease on an
        expired lease, then the monitor recovers the lease. The
        recovery context must show 50%, not the original 25%.
        This closes the dashboard-v70 loop.
        """
        # 1. Lease is expired at 25%
        expired = await self._insert_expired_lease(
            lease_manager, "task-342", "agent-001", initial_progress=25
        )

        # 2. Agent reports late progress — renewal fails, but
        #    capture fires.
        await lease_manager.renew_lease(
            task_id="task-342", progress=50, message="halfway"
        )
        assert expired.progress_percentage == 50

        # 3. Monitor recovers the lease. Recovery context must
        #    reflect the captured value, not the stale snapshot.
        with patch.object(lease_manager, "_find_task", return_value=real_task):
            success = await lease_manager.recover_expired_lease(expired)

        assert success
        assert real_task.recovery_info is not None
        assert real_task.recovery_info.previous_progress == 50
        assert "50%" in real_task.recovery_info.instructions
        # Lease history also tracks the corrected value
        assert lease_manager.lease_history[-1]["progress_at_recovery"] == 50

    @pytest.mark.asyncio
    async def test_expired_lease_renewal_still_returns_none(self, lease_manager):
        """
        The capture must not accidentally un-expire the lease.
        ``renew_lease`` still returns None on expired leases so
        the caller's "No active lease" fallback path triggers
        correctly. This test pins that contract explicitly so a
        future refactor doesn't silently start returning the
        lease object from the expired branch.
        """
        expired = await self._insert_expired_lease(
            lease_manager, "task-342", "agent-001", initial_progress=0
        )

        result = await lease_manager.renew_lease(
            task_id="task-342", progress=80, message="almost done"
        )

        assert result is None
        assert expired.is_expired  # lease remains expired
        assert expired.progress_percentage == 80  # but progress captured
