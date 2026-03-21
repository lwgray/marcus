"""
Unit tests for progressive timeout strategy in assignment lease system.

Tests the implementation of data-driven progressive timeouts that adapt based on:
- Task progress percentage
- Number of progress updates received
- Task complexity/estimation

This uses TDD approach - tests written BEFORE implementation.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.assignment_lease import AssignmentLease, AssignmentLeaseManager
from src.core.models import Priority, Task, TaskStatus


@pytest.fixture
def mock_kanban_client():
    """Create mock kanban client."""
    client = AsyncMock()
    client.get_task = AsyncMock()
    client.update_task_status = AsyncMock()
    # Default: get_task_by_id returns None (task not found on board)
    # Tests that need board activity checking override this explicitly
    client.get_task_by_id = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_assignment_persistence():
    """Create mock assignment persistence."""
    persistence = AsyncMock()
    persistence.load_assignments = AsyncMock(return_value={})
    persistence.save_assignment = AsyncMock()
    persistence.remove_assignment = AsyncMock()
    persistence.get_assignment = AsyncMock(return_value=None)
    return persistence


@pytest.fixture
def lease_manager_aggressive(mock_kanban_client, mock_assignment_persistence):
    """Create lease manager with aggressive (90s) initial timeout."""
    return AssignmentLeaseManager(
        kanban_client=mock_kanban_client,
        assignment_persistence=mock_assignment_persistence,
        default_lease_hours=0.025,  # 90 seconds
        grace_period_minutes=0.5,  # 30 seconds
        min_lease_hours=0.0167,  # 60 seconds minimum
        max_lease_hours=0.0333,  # 120 seconds maximum
    )


class TestProgressiveTimeoutCalculation:
    """Test progressive timeout calculation based on task state."""

    def test_calculate_timeout_no_updates_yet(self, lease_manager_aggressive):
        """Test timeout for task with no progress updates yet (strict)."""
        # Phase 1: No updates - strict timeout
        lease_seconds, grace_seconds = (
            lease_manager_aggressive.calculate_adaptive_timeout(
                progress=0, update_count=0, has_recent_activity=False
            )
        )

        # Should use strict timeout (60s)
        assert lease_seconds == 60
        assert grace_seconds == 20
        assert lease_seconds + grace_seconds == 80  # Total: 80s

    def test_calculate_timeout_first_update(self, lease_manager_aggressive):
        """Test timeout after first progress update (moderate)."""
        # Phase 2: First update received - moderate timeout
        lease_seconds, grace_seconds = (
            lease_manager_aggressive.calculate_adaptive_timeout(
                progress=5, update_count=1, has_recent_activity=True
            )
        )

        # Should use moderate timeout (90s)
        assert lease_seconds == 90
        assert grace_seconds == 30
        assert lease_seconds + grace_seconds == 120  # Total: 2 min

    def test_calculate_timeout_good_progress(self, lease_manager_aggressive):
        """Test timeout for task with good progress (25-75%) (conservative)."""
        # Phase 3: Task making progress - conservative timeout
        for progress in [25, 40, 50, 65, 74]:
            lease_seconds, grace_seconds = (
                lease_manager_aggressive.calculate_adaptive_timeout(
                    progress=progress, update_count=3, has_recent_activity=True
                )
            )

            # Should use conservative timeout (120s)
            assert lease_seconds == 120
            assert grace_seconds == 30
            assert lease_seconds + grace_seconds == 150  # Total: 2.5 min

    def test_calculate_timeout_near_completion(self, lease_manager_aggressive):
        """Test timeout for task near completion (>75%) (fast)."""
        # Phase 4: Near completion - fast detection
        for progress in [75, 80, 90, 95]:
            lease_seconds, grace_seconds = (
                lease_manager_aggressive.calculate_adaptive_timeout(
                    progress=progress, update_count=5, has_recent_activity=True
                )
            )

            # Should use fast timeout (60s)
            assert lease_seconds == 60
            assert grace_seconds == 15
            assert lease_seconds + grace_seconds == 75  # Total: 1.25 min


class TestSmartRecoveryChecks:
    """Test smart recovery checks without heartbeat."""

    @pytest.mark.asyncio
    async def test_should_recover_no_progress(self, lease_manager_aggressive):
        """Test recovery when task has 0% progress."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=10),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=5),
            progress_percentage=0,  # No progress
            renewal_count=0,
        )

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should recover - no progress made
        assert should_recover is True

    @pytest.mark.asyncio
    async def test_should_not_recover_with_progress_first_time(
        self, lease_manager_aggressive
    ):
        """Test that task with progress gets grace extension on first expiry."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=10),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=2),
            progress_percentage=40,  # Has progress
            renewal_count=1,
        )

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should NOT recover - has progress, first expiry
        assert should_recover is False

    @pytest.mark.asyncio
    async def test_should_recover_with_progress_after_max_renewals(
        self, lease_manager_aggressive
    ):
        """Test recovery when renewal count exceeds threshold."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=10),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=3),
            progress_percentage=40,
            renewal_count=3,  # Too many renewals
        )

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should recover - too many renewals, likely stuck
        assert should_recover is True

    @pytest.mark.asyncio
    async def test_should_not_recover_recent_board_activity(
        self, lease_manager_aggressive, mock_kanban_client
    ):
        """Test that recent board activity prevents recovery."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=10),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=2),
            progress_percentage=0,  # No progress reported
            renewal_count=0,
        )

        # Mock task with recent board update
        mock_task = Mock()
        mock_task.updated_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        mock_kanban_client.get_task_by_id.return_value = mock_task

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should NOT recover - board shows recent activity
        assert should_recover is False

    @pytest.mark.asyncio
    async def test_should_recover_old_board_activity(
        self, lease_manager_aggressive, mock_kanban_client
    ):
        """Test recovery when board activity is old."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=10),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=5),
            progress_percentage=0,
            renewal_count=0,
        )

        # Mock task with old board update
        mock_task = Mock()
        mock_task.updated_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        mock_kanban_client.get_task_by_id.return_value = mock_task

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should recover - board activity is stale
        assert should_recover is True


class TestAggressiveVsConservativeTimeouts:
    """Test that aggressive timeouts enable faster recovery."""

    @pytest.mark.asyncio
    async def test_aggressive_timeout_detects_failure_fast(
        self, lease_manager_aggressive, mock_kanban_client, mock_assignment_persistence
    ):
        """Test that 90s timeout enables 2min total recovery time."""
        task = Task(
            id="task-1",
            name="Test Task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
        )

        # Create lease with aggressive timeout
        lease = await lease_manager_aggressive.create_lease("task-1", "agent-1", task)

        # Check lease duration
        duration = (lease.lease_expires - lease.assigned_at).total_seconds()

        # Phase 1 (unproven agent) = 60s, clamped to min_lease_hours (60s)
        assert 55 <= duration <= 65  # Allow small variance

        # Total recovery time with grace (60s lease + 30s grace = 90s)
        total_recovery = duration + (lease_manager_aggressive.grace_period_minutes * 60)

        # Should be ~90 seconds total for unproven agents
        assert 85 <= total_recovery <= 95

    def test_progressive_timeout_phases(self, lease_manager_aggressive):
        """Test all four phases of progressive timeout."""
        # Phase 1: Unproven (60s + 20s = 80s)
        p1_lease, p1_grace = lease_manager_aggressive.calculate_adaptive_timeout(
            progress=0, update_count=0, has_recent_activity=False
        )
        assert p1_lease + p1_grace == 80

        # Phase 2: Working (90s + 30s = 120s)
        p2_lease, p2_grace = lease_manager_aggressive.calculate_adaptive_timeout(
            progress=10, update_count=1, has_recent_activity=True
        )
        assert p2_lease + p2_grace == 120

        # Phase 3: Proven (120s + 30s = 150s)
        p3_lease, p3_grace = lease_manager_aggressive.calculate_adaptive_timeout(
            progress=50, update_count=3, has_recent_activity=True
        )
        assert p3_lease + p3_grace == 150

        # Phase 4: Finishing (60s + 15s = 75s)
        p4_lease, p4_grace = lease_manager_aggressive.calculate_adaptive_timeout(
            progress=85, update_count=5, has_recent_activity=True
        )
        assert p4_lease + p4_grace == 75

        # Verify progression: P4 < P1 < P2 < P3
        # (Finishing < Unproven < Working < Proven)
        assert p4_lease + p4_grace < p1_lease + p1_grace
        assert p1_lease + p1_grace < p2_lease + p2_grace
        assert p2_lease + p2_grace < p3_lease + p3_grace


class TestFalsePositiveReduction:
    """Test strategies to reduce false positive recovery."""

    @pytest.mark.asyncio
    async def test_grace_extension_for_progressed_task(self, lease_manager_aggressive):
        """Test that tasks with progress get grace extension."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=3),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=5),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=1),
            progress_percentage=60,  # Significant progress
            renewal_count=1,
        )

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should NOT recover - task has significant progress
        assert should_recover is False

    @pytest.mark.asyncio
    async def test_no_grace_for_zero_progress(self, lease_manager_aggressive):
        """Test that tasks with 0% progress don't get grace extension."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=3),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=5),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=1),
            progress_percentage=0,  # No progress
            renewal_count=0,
        )

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should recover - no progress made
        assert should_recover is True

    @pytest.mark.asyncio
    async def test_board_activity_check_protects_working_agent(
        self, lease_manager_aggressive, mock_kanban_client
    ):
        """Test that board activity check prevents false positive."""
        lease = AssignmentLease(
            task_id="task-1",
            agent_id="agent-1",
            assigned_at=datetime.now(timezone.utc) - timedelta(minutes=3),
            lease_expires=datetime.now(timezone.utc) - timedelta(seconds=5),
            last_renewed=datetime.now(timezone.utc) - timedelta(minutes=2),
            progress_percentage=30,
            renewal_count=0,
        )

        # Agent updated board 45 seconds ago (recent)
        mock_task = Mock()
        mock_task.updated_at = datetime.now(timezone.utc) - timedelta(seconds=45)
        mock_kanban_client.get_task_by_id.return_value = mock_task

        should_recover = await lease_manager_aggressive.should_recover_expired_lease(
            lease
        )

        # Should NOT recover - board shows agent is working
        assert should_recover is False


class TestDataDrivenDecisions:
    """Test that timeout decisions are based on actual data (64s median)."""

    def test_timeouts_based_on_median_delay(self, lease_manager_aggressive):
        """Test that timeouts account for 64s median update delay."""
        # Median delay is 64 seconds
        # 90s timeout covers median + buffer
        # 120s with grace covers 75th percentile (118s)

        # Phase 2 (working): 90s lease
        lease_seconds, grace_seconds = (
            lease_manager_aggressive.calculate_adaptive_timeout(
                progress=10, update_count=1, has_recent_activity=True
            )
        )

        # 90s covers median (64s) + 26s buffer
        assert lease_seconds > 64  # Covers median
        assert lease_seconds + grace_seconds >= 118  # Covers 75th percentile

    def test_aggressive_timeout_accepts_calculated_risk(self, lease_manager_aggressive):
        """Test that 90s timeout accepts ~36% false positive risk."""
        # At 90s timeout:
        # - Coverage: 64% of normal updates
        # - False positive: 36% risk
        # - But with smart checks, reduces to ~5-8%

        lease_seconds, _ = lease_manager_aggressive.calculate_adaptive_timeout(
            progress=10, update_count=1, has_recent_activity=True
        )

        # 90s = 64th percentile (from data analysis)
        assert lease_seconds == 90

        # This is aggressive by design:
        # User can't spawn agents on demand, so fast detection
        # is more important than avoiding false positives
