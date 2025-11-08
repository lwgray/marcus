"""
Unit tests for the assignment lease system.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.assignment_lease import (
    AssignmentLease,
    AssignmentLeaseManager,
    LeaseMonitor,
    LeaseStatus,
)
from src.core.models import Priority, Task, TaskStatus


class TestAssignmentLease:
    """Test suite for AssignmentLease data class."""

    def test_lease_creation(self):
        """Test basic lease creation."""
        now = datetime.now()
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
        now = datetime.now()

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
        now = datetime.now()

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
        now = datetime.now()
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
                "assigned_at": datetime.now().isoformat(),
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
            created_at=datetime.now(),
            updated_at=datetime.now(),
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
            assigned_at=datetime.now() - timedelta(hours=5),
            lease_expires=datetime.now() - timedelta(hours=1),
            last_renewed=datetime.now() - timedelta(hours=5),
        )
        lease_manager.active_leases["task-123"] = lease

        # Try to renew
        renewed_lease = await lease_manager.renew_lease("task-123", 50, "Progress")

        assert renewed_lease is None

    @pytest.mark.asyncio
    async def test_check_expired_leases(self, lease_manager):
        """Test detection of expired leases."""
        now = datetime.now()

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
            assigned_at=datetime.now() - timedelta(hours=5),
            lease_expires=datetime.now() - timedelta(hours=1),
            last_renewed=datetime.now() - timedelta(hours=5),
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
        now = datetime.now()

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
        now = datetime.now()

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
        """Test that monitor recovers expired leases."""
        # Set up expired leases
        expired_lease = Mock()
        expired_lease.task_id = "task-123"
        mock_lease_manager.check_expired_leases.return_value = [expired_lease]

        # Start monitor
        await lease_monitor.start()

        # Wait for at least one check cycle
        await asyncio.sleep(1.5)

        # Stop monitor
        await lease_monitor.stop()

        # Verify recovery was attempted
        mock_lease_manager.check_expired_leases.assert_called()
        mock_lease_manager.recover_expired_lease.assert_called_with(expired_lease)
