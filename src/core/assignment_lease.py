"""
Assignment Lease System for automatic task recovery.

This module implements a lease-based assignment system where tasks are assigned
with time-limited leases that must be renewed through progress reports. Tasks
with expired leases are automatically returned to the TODO state for reassignment.

Key features:
- Automatic lease renewal on progress reports
- Configurable lease durations based on task complexity
- Escalation for tasks with excessive renewals
- Integration with assignment persistence
"""

import asyncio
import logging
import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

from src.core.assignment_persistence import AssignmentPersistence
from src.core.event_loop_utils import EventLoopLockManager
from src.core.models import RecoveryInfo, Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface

logger = logging.getLogger(__name__)


class LeaseStatus(Enum):
    """Status of an assignment lease."""

    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # Less than 1 hour remaining
    EXPIRED = "expired"
    RENEWED = "renewed"


@dataclass
class AssignmentLease:
    """Represents a time-limited assignment lease."""

    task_id: str
    agent_id: str
    assigned_at: datetime
    lease_expires: datetime
    last_renewed: datetime
    renewal_count: int = 0
    estimated_hours: float = 4.0  # From task estimation
    progress_percentage: int = 0
    last_progress_message: str = ""
    grace_period_seconds: Optional[float] = None  # Per-lease adaptive grace
    update_timestamps: list[datetime] = field(default_factory=list)

    @property
    def median_update_interval(self) -> Optional[float]:
        """Calculate median seconds between progress updates.

        Returns
        -------
        Optional[float]
            Median interval in seconds, or None if fewer than 2 timestamps.
        """
        if len(self.update_timestamps) < 2:
            return None
        sorted_ts = sorted(self.update_timestamps)
        intervals = [
            (sorted_ts[i] - sorted_ts[i - 1]).total_seconds()
            for i in range(1, len(sorted_ts))
        ]
        return statistics.median(intervals)

    @property
    def time_remaining(self) -> timedelta:
        """Calculate time remaining on lease."""
        return self.lease_expires - datetime.now(timezone.utc)

    @property
    def is_expired(self) -> bool:
        """Check if lease has expired."""
        return datetime.now(timezone.utc) > self.lease_expires

    @property
    def is_expiring_soon(self) -> bool:
        """Check if lease expires within 1 hour."""
        return self.time_remaining < timedelta(hours=1)

    @property
    def status(self) -> LeaseStatus:
        """Get current lease status."""
        if self.is_expired:
            return LeaseStatus.EXPIRED
        elif self.is_expiring_soon:
            return LeaseStatus.EXPIRING_SOON
        else:
            return LeaseStatus.ACTIVE

    def calculate_renewal_duration(
        self, lease_manager: Optional["AssignmentLeaseManager"] = None
    ) -> timedelta:
        """
        Calculate renewal duration based on progress and history.

        Parameters
        ----------
            lease_manager
                Optional reference to lease manager for config.

        Returns
        -------
            Renewal duration (adaptive based on multiple factors)
        """
        base_hours = 4.0

        # Adjust based on progress
        if self.progress_percentage > 75:
            # Near completion, shorter renewal
            base_hours = 2.0
        elif self.progress_percentage > 50:
            base_hours = 3.0
        elif self.progress_percentage < 25 and self.renewal_count > 2:
            # Low progress with multiple renewals - might be stuck
            base_hours = 2.0

        # Adjust based on task complexity
        if self.estimated_hours > 8:
            # Complex task, allow more time
            base_hours *= 1.5

        # Apply renewal decay if configured
        if lease_manager and hasattr(lease_manager, "renewal_decay_factor"):
            decay_factor = lease_manager.renewal_decay_factor**self.renewal_count
            base_hours *= decay_factor

        # Cap renewals for tasks that are taking too long
        if self.renewal_count > 5:
            base_hours = min(base_hours, 2.0)

        # Apply bounds if lease manager available
        if lease_manager:
            base_hours = max(
                lease_manager.min_lease_hours,
                min(lease_manager.max_lease_hours, base_hours),
            )

        return timedelta(hours=base_hours)


def _ensure_timezone_aware(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware (UTC).

    Normalizes naive datetimes from old persistence data to UTC.
    This prevents TypeErrors when comparing with timezone-aware datetimes.

    Parameters
    ----------
    dt : datetime
        Datetime to normalize (may be naive or aware)

    Returns
    -------
    datetime
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it was meant to be UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AssignmentLeaseManager:
    """Manages assignment leases with automatic expiration and renewal."""

    def __init__(
        self,
        kanban_client: KanbanInterface,
        assignment_persistence: AssignmentPersistence,
        default_lease_hours: float = 0.025,  # 90 seconds (aggressive)
        max_renewals: int = 10,
        warning_threshold_hours: float = 0.0167,  # 1 min (was 1.0 hr)
        priority_multipliers: Optional[Dict[str, float]] = None,
        complexity_multipliers: Optional[Dict[str, float]] = None,
        grace_period_minutes: float = 0.5,  # 30 seconds grace period
        renewal_decay_factor: float = 0.9,
        min_lease_hours: float = 0.0167,  # Minimum 60 seconds
        max_lease_hours: float = 0.0333,  # Maximum 120 seconds
        stuck_task_threshold_renewals: int = 5,
        enable_adaptive_leases: bool = True,
        task_list: Optional[List[Task]] = None,
        silence_multiplier: float = 1.5,
    ):
        """
        Initialize the lease manager.

        Parameters
        ----------
            kanban_client
                Interface to kanban board.
            assignment_persistence
                Assignment persistence layer.
            default_lease_hours
                Default lease duration in hours.
            max_renewals
                Maximum allowed renewals before escalation.
            warning_threshold_hours
                Hours before expiry to warn.
            priority_multipliers
                Lease duration multipliers by priority.
            complexity_multipliers
                Lease duration multipliers by label/type.
            grace_period_minutes
                Grace period in minutes (float) after expiry before recovery.
            renewal_decay_factor
                Factor to reduce renewal duration over time.
            min_lease_hours
                Minimum allowed lease duration.
            max_lease_hours
                Maximum allowed lease duration.
            stuck_task_threshold_renewals
                Renewals before considering task stuck.
            enable_adaptive_leases
                Enable smart lease duration adjustments.
            task_list
                Optional reference to project tasks for recovery info updates.
        """
        self.kanban_client = kanban_client
        self.assignment_persistence = assignment_persistence
        self.task_list = task_list if task_list is not None else []
        self.default_lease_hours = default_lease_hours
        self.max_renewals = max_renewals
        self.warning_threshold_hours = warning_threshold_hours

        # Advanced configuration
        self.priority_multipliers = priority_multipliers or {
            "critical": 0.5,  # Shorter leases for urgent tasks
            "high": 0.75,
            "medium": 1.0,
            "low": 1.5,
        }
        self.complexity_multipliers = complexity_multipliers or {
            "simple": 0.5,
            "complex": 1.5,
            "research": 2.0,
            "epic": 3.0,
        }
        self.grace_period_minutes = grace_period_minutes
        self.renewal_decay_factor = renewal_decay_factor
        self.min_lease_hours = min_lease_hours
        self.max_lease_hours = max_lease_hours
        self.stuck_task_threshold_renewals = stuck_task_threshold_renewals
        self.enable_adaptive_leases = enable_adaptive_leases
        self.silence_multiplier = silence_multiplier

        # Active leases tracked in memory
        self.active_leases: Dict[str, AssignmentLease] = {}

        # Optional callback invoked after a successful recovery
        # Server sets this to clean up in-memory tracking structures
        # (agent_tasks, tasks_being_assigned) that lease manager
        # can't access directly.
        self.on_recovery_callback: Optional[Callable[[str, str], None]] = None

        # Track lease history for analysis (max 1000 entries to prevent memory leak)
        self.lease_history: Deque[Dict[str, Any]] = deque(maxlen=1000)

        # Lock manager for event loop safe operations
        self._lock_manager = EventLoopLockManager()

    @property
    def lease_lock(self) -> asyncio.Lock:
        """Get lease lock for the current event loop."""
        return self._lock_manager.get_lock()

    def update_task_list(self, task_list: List[Task]) -> None:
        """
        Update the task list reference.

        Called by MarcusServer when project_tasks is refreshed.

        Parameters
        ----------
        task_list : List[Task]
            Updated list of project tasks
        """
        self.task_list = task_list

    async def create_lease(
        self, task_id: str, agent_id: str, task: Optional[Task] = None
    ) -> AssignmentLease:
        """
        Create a new assignment lease.

        Parameters
        ----------
            task_id
                ID of the task being assigned.
            agent_id
                ID of the agent receiving assignment.
            task
                Optional task object for additional context.

        Returns
        -------
            Created assignment lease
        """
        async with self.lease_lock:
            now = datetime.now(timezone.utc)

            # Calculate initial lease duration
            # Use progressive timeout phase-1 if in aggressive mode
            if self.default_lease_hours < 1.0:
                # Aggressive mode: Use phase-1 timeout for unproven agents
                lease_seconds, _ = self.calculate_adaptive_timeout(
                    progress=0, update_count=0, has_recent_activity=False
                )
                base_hours = lease_seconds / 3600
            else:
                # Conservative mode: Use default or task-based estimation
                base_hours = self.default_lease_hours

            # Only use task-based estimation if default is conservative (> 1 hour)
            if task and self.enable_adaptive_leases and self.default_lease_hours > 1.0:
                # Use task estimation if available
                if task.estimated_hours:
                    base_hours = task.estimated_hours

                # Apply priority multiplier
                if hasattr(task, "priority"):
                    priority_mult = self.priority_multipliers.get(
                        task.priority.value.lower(), 1.0
                    )
                    base_hours *= priority_mult

                # Apply complexity multiplier based on labels
                if hasattr(task, "labels"):
                    for label in task.labels:
                        label_lower = label.lower()
                        if label_lower in self.complexity_multipliers:
                            base_hours *= self.complexity_multipliers[label_lower]
                            break  # Use first matching complexity

            # Enforce min/max bounds
            base_hours = max(
                self.min_lease_hours, min(self.max_lease_hours, base_hours)
            )

            initial_duration = timedelta(hours=base_hours)

            lease = AssignmentLease(
                task_id=task_id,
                agent_id=agent_id,
                assigned_at=now,
                lease_expires=now + initial_duration,
                last_renewed=now,
                estimated_hours=task.estimated_hours if task else base_hours,
            )

            # Store lease
            self.active_leases[task_id] = lease

            # Update assignment persistence with lease info
            await self._persist_lease(lease)

            # Log lease creation
            logger.info(
                f"Created lease for task {task_id} to agent {agent_id} "
                f"(expires: {lease.lease_expires.isoformat()})"
            )

            # Track in history
            self.lease_history.append(
                {
                    "event": "lease_created",
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "timestamp": now.isoformat(),
                    "expires": lease.lease_expires.isoformat(),
                }
            )

            return lease

    async def renew_lease(
        self, task_id: str, progress: int, message: str = ""
    ) -> Optional[AssignmentLease]:
        """
        Renew an existing lease based on progress report.

        Uses progressive timeout strategy to adapt lease duration based on
        task progress and agent reliability.

        Parameters
        ----------
            task_id
                ID of the task.
            progress
                Current progress percentage.
            message
                Progress message.

        Returns
        -------
            Renewed lease or None if not found/expired
        """
        async with self.lease_lock:
            lease = self.active_leases.get(task_id)
            if not lease:
                logger.warning(f"No active lease found for task {task_id}")
                return None

            if lease.is_expired:
                logger.warning(f"Cannot renew expired lease for task {task_id}")
                return None

            # Update progress
            lease.progress_percentage = progress
            lease.last_progress_message = message

            # Track update timestamp for cadence-based recovery
            lease.update_timestamps.append(datetime.now(timezone.utc))

            # Use progressive timeout if in aggressive mode (< 1 hour default)
            if self.default_lease_hours < 1.0:
                # Progressive timeout mode: calculate based on progress
                lease_seconds, grace_seconds = self.calculate_adaptive_timeout(
                    progress=progress,
                    update_count=lease.renewal_count + 1,  # +1 for this renewal
                    has_recent_activity=True,  # Just reported progress
                )
                renewal_duration = timedelta(seconds=lease_seconds)
                lease.grace_period_seconds = float(grace_seconds)

                logger.info(
                    f"Progressive timeout for {task_id}: {lease_seconds}s "
                    f"+ {grace_seconds}s grace "
                    f"(progress={progress}%, updates={lease.renewal_count + 1})"
                )
            else:
                # Conservative mode: use old calculation logic
                renewal_duration = lease.calculate_renewal_duration(self)

            # Renew lease
            lease.last_renewed = datetime.now(timezone.utc)
            lease.lease_expires = lease.last_renewed + renewal_duration
            lease.renewal_count += 1

            # Check for excessive renewals
            if lease.renewal_count >= self.max_renewals:
                logger.warning(
                    f"Task {task_id} has been renewed {lease.renewal_count} times. "
                    f"Consider escalation or reassignment."
                )

            # Update persistence
            await self._persist_lease(lease)

            # Log renewal
            logger.info(
                f"Renewed lease for task {task_id} "
                f"(progress: {progress}%, expires: {lease.lease_expires.isoformat()})"
            )

            # Track in history
            self.lease_history.append(
                {
                    "event": "lease_renewed",
                    "task_id": task_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "progress": progress,
                    "renewal_count": lease.renewal_count,
                    "new_expiry": lease.lease_expires.isoformat(),
                }
            )

            return lease

    async def touch_lease(self, agent_id: str) -> bool:
        """
        Extend an agent's lease without changing progress.

        Called on any MCP tool activity to prove the agent is alive.
        This is a lightweight alternative to renew_lease that doesn't
        require progress data or update cadence tracking.

        Parameters
        ----------
        agent_id : str
            ID of the agent whose lease to extend.

        Returns
        -------
        bool
            True if a lease was touched, False if no active lease found.
        """
        async with self.lease_lock:
            # Find lease by agent_id
            lease = None
            for active_lease in self.active_leases.values():
                if active_lease.agent_id == agent_id:
                    lease = active_lease
                    break

            if not lease or lease.is_expired:
                return False

            # Extend by the current phase timeout
            lease_seconds, _ = self.calculate_adaptive_timeout(
                progress=lease.progress_percentage,
                update_count=max(lease.renewal_count, 1),
                has_recent_activity=True,
            )
            now = datetime.now(timezone.utc)
            lease.last_renewed = now
            lease.lease_expires = now + timedelta(seconds=lease_seconds)

            # Update timestamp for cadence tracking
            lease.update_timestamps.append(now)

            logger.debug(
                f"Touched lease for agent {agent_id} "
                f"(task {lease.task_id}, "
                f"expires: {lease.lease_expires.isoformat()})"
            )
            return True

    async def check_expired_leases(self) -> List[AssignmentLease]:
        """
        Check for expired leases that need recovery.

        Returns
        -------
            List of expired leases (considering grace period)
        """
        expired_leases = []
        now = datetime.now(timezone.utc)
        default_grace_delta = timedelta(minutes=self.grace_period_minutes)

        async with self.lease_lock:
            for task_id, lease in list(self.active_leases.items()):
                if lease.is_expired:
                    # Use per-lease adaptive grace if set, else global default
                    if lease.grace_period_seconds is not None:
                        grace_delta = timedelta(seconds=lease.grace_period_seconds)
                    else:
                        grace_delta = default_grace_delta
                    # Check if grace period has also expired
                    grace_deadline = lease.lease_expires + grace_delta
                    if now > grace_deadline:
                        expired_leases.append(lease)
                        logger.info(
                            f"Found expired lease: task {task_id} "
                            f"(expired: {lease.lease_expires.isoformat()}, "
                            f"grace ended: {grace_deadline.isoformat()})"
                        )
                    else:
                        logger.debug(
                            f"Lease expired but in grace period: task {task_id} "
                            f"(expires fully at: {grace_deadline.isoformat()})"
                        )

        return expired_leases

    def _find_task(self, task_id: str) -> Optional[Task]:
        """
        Find a task by ID in the task list.

        Parameters
        ----------
            task_id
                Task ID to find.

        Returns
        -------
            Task object if found, None otherwise
        """
        for task in self.task_list:
            if task.id == task_id:
                return task
        return None

    async def recover_expired_lease(self, lease: AssignmentLease) -> bool:
        """
        Recover a task with an expired lease.

        Implements dual-write pattern:
        1. Updates task model with structured RecoveryInfo (source of truth)
        2. Posts to Kanban comments for audit trail (observability)

        Parameters
        ----------
            lease
                The expired lease to recover.

        Returns
        -------
            True if recovery successful
        """
        try:
            logger.info(
                f"Recovering task {lease.task_id} from agent {lease.agent_id} "
                f"(expired: {lease.lease_expires.isoformat()})"
            )

            # Calculate time spent
            now = datetime.now(timezone.utc)
            time_spent = now - lease.assigned_at
            time_spent_minutes = time_spent.total_seconds() / 60

            # Create structured recovery info
            # In worktree mode, each agent works on branch marcus/<agent_id>
            previous_branch = f"marcus/{lease.agent_id}"

            recovery_info = RecoveryInfo(
                recovered_at=now,
                recovered_from_agent=lease.agent_id,
                previous_progress=lease.progress_percentage,
                time_spent_minutes=time_spent_minutes,
                recovery_reason="lease_expired",
                previous_agent_branch=previous_branch,
                instructions=(
                    f"⚠️ **RECOVERY ADDENDUM** - This task was recovered "
                    f"from agent {lease.agent_id}\n\n"
                    f"**FIRST: Pick up committed work from the previous "
                    f"agent:**\n"
                    f"```\n"
                    f"git merge {previous_branch} --no-edit\n"
                    f"```\n"
                    f"This merges any commits the previous agent made "
                    f"before they disconnected.\n\n"
                    f"**Then check what was done:**\n"
                    f"1. Run `git log {previous_branch}` to see their "
                    f"commits\n"
                    f"2. Check for artifacts or design documents\n"
                    f"3. Previous agent reached "
                    f"{lease.progress_percentage}%\n"
                    f"4. **Continue from where they left off** - "
                    f"don't restart from scratch\n\n"
                    f"**Recovery Context:**\n"
                    f"- Previous agent: {lease.agent_id}\n"
                    f"- Previous branch: {previous_branch}\n"
                    f"- Time they spent: "
                    f"{time_spent_minutes:.1f} minutes\n"
                    f"- Recovery reason: lease expired (no progress "
                    f"updates)\n"
                    f"- Your task: Complete the ORIGINAL task "
                    f"requirements, building on existing work\n"
                ),
                recovery_expires_at=now + timedelta(hours=24),
            )

            # 1. Update task model (source of truth) if task is available
            task = self._find_task(lease.task_id)
            if task:
                task.recovery_info = recovery_info
                # Clear ownership so task re-enters the assignment pool
                task.assigned_to = None
                logger.info(
                    f"Updated task {lease.task_id} model with recovery "
                    f"info, cleared assigned_to"
                )
            else:
                logger.warning(
                    f"Task {lease.task_id} not found in task list for "
                    f"recovery info update"
                )

            # 2. Dual-write to Kanban for audit trail
            # Don't fail entire recovery if Kanban write fails
            try:
                await self._create_recovery_handoff_comment(lease, recovery_info)
            except Exception as e:
                logger.warning(f"Failed to write recovery comment to Kanban: {e}")
                # Continue - task model update is what matters

            # Remove from active leases
            async with self.lease_lock:
                if lease.task_id in self.active_leases:
                    del self.active_leases[lease.task_id]

            # Remove assignment from persistence
            await self.assignment_persistence.remove_assignment(lease.agent_id)

            # Invoke recovery callback so server can clean in-memory state
            if self.on_recovery_callback is not None:
                try:
                    self.on_recovery_callback(lease.agent_id, lease.task_id)
                except Exception as e:
                    logger.warning(
                        f"Recovery callback failed for task " f"{lease.task_id}: {e}"
                    )

            # Reset task on board: status → TODO, clear assigned_to
            try:
                if hasattr(self.kanban_client, "update_task"):
                    await self.kanban_client.update_task(
                        lease.task_id,
                        {"status": TaskStatus.TODO, "assigned_to": None},
                    )
                elif hasattr(self.kanban_client, "update_task_status"):
                    # Fallback: at least reset status
                    await self.kanban_client.update_task_status(
                        lease.task_id, TaskStatus.TODO
                    )
                    logger.warning(
                        f"Kanban client lacks update_task — "
                        f"assigned_to not cleared on board for "
                        f"{lease.task_id}"
                    )
                else:
                    logger.warning(
                        f"Kanban client does not support task updates, "
                        f"task {lease.task_id} not updated on board"
                    )
            except Exception as e:
                logger.error(f"Failed to reset task {lease.task_id} on board: {e}")
                # Don't fail entire recovery if board update fails
                # In-memory state is already updated

            # Track in history
            self.lease_history.append(
                {
                    "event": "lease_recovered",
                    "task_id": lease.task_id,
                    "agent_id": lease.agent_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "progress_at_recovery": lease.progress_percentage,
                    "total_renewals": lease.renewal_count,
                }
            )

            return True

        except Exception as e:
            logger.error(f"Error recovering lease for task {lease.task_id}: {e}")
            return False

    async def get_expiring_leases(self) -> List[AssignmentLease]:
        """
        Get leases that are expiring soon.

        Returns
        -------
            List of leases expiring within warning threshold
        """
        expiring = []

        async with self.lease_lock:
            for lease in self.active_leases.values():
                if lease.is_expiring_soon and not lease.is_expired:
                    expiring.append(lease)

        return expiring

    async def _persist_lease(self, lease: AssignmentLease) -> None:
        """Persist lease information to assignment persistence."""
        assignment = await self.assignment_persistence.get_assignment(lease.agent_id)
        if assignment:
            assignment["lease_expires"] = lease.lease_expires.isoformat()
            assignment["lease_renewed_at"] = lease.last_renewed.isoformat()
            assignment["renewal_count"] = lease.renewal_count
            assignment["progress_percentage"] = lease.progress_percentage
            assignment["last_progress_update"] = datetime.now(timezone.utc).isoformat()
            assignment["update_timestamps"] = [
                ts.isoformat() for ts in lease.update_timestamps
            ]
            await self.assignment_persistence.save_assignment(
                lease.agent_id,
                lease.task_id,
                assignment.get("assigned_at", datetime.now(timezone.utc).isoformat()),
            )

    async def load_active_leases(self) -> None:
        """Load active leases from persistence on startup."""
        assignments = await self.assignment_persistence.load_assignments()

        for agent_id, assignment in assignments.items():
            task_id = assignment["task_id"]

            # Reconstruct lease from assignment
            # Normalize naive datetimes to UTC for backwards compatibility
            assigned_at = _ensure_timezone_aware(
                datetime.fromisoformat(assignment["assigned_at"])
            )
            lease_expires = _ensure_timezone_aware(
                datetime.fromisoformat(
                    assignment.get(
                        "lease_expires", datetime.now(timezone.utc).isoformat()
                    )
                )
            )
            last_renewed = _ensure_timezone_aware(
                datetime.fromisoformat(
                    assignment.get("lease_renewed_at", assignment["assigned_at"])
                )
            )

            # Restore update timestamps for cadence-based recovery
            raw_timestamps = assignment.get("update_timestamps", [])
            update_timestamps = [
                _ensure_timezone_aware(datetime.fromisoformat(ts))
                for ts in raw_timestamps
            ]

            lease = AssignmentLease(
                task_id=task_id,
                agent_id=agent_id,
                assigned_at=assigned_at,
                lease_expires=lease_expires,
                last_renewed=last_renewed,
                renewal_count=assignment.get("renewal_count", 0),
                progress_percentage=assignment.get("progress_percentage", 0),
                update_timestamps=update_timestamps,
            )

            self.active_leases[task_id] = lease

        logger.info(f"Loaded {len(self.active_leases)} active leases from persistence")

    def get_lease_statistics(self) -> Dict[str, Any]:
        """Get statistics about current leases."""
        stats: Dict[str, Any] = {
            "total_active": len(self.active_leases),
            "expired": 0,
            "expiring_soon": 0,
            "high_renewal_count": 0,
            "by_status": {},
            "average_renewal_count": 0,
        }

        total_renewals = 0

        for lease in self.active_leases.values():
            # Count by status
            status = lease.status.value
            by_status_dict: Dict[str, int] = stats["by_status"]
            by_status_dict[status] = by_status_dict.get(status, 0) + 1

            # Count specific conditions
            if lease.is_expired:
                expired_count: int = stats["expired"]
                stats["expired"] = expired_count + 1
            elif lease.is_expiring_soon:
                expiring_count: int = stats["expiring_soon"]
                stats["expiring_soon"] = expiring_count + 1

            if lease.renewal_count >= self.max_renewals:
                high_renewal_count: int = stats["high_renewal_count"]
                stats["high_renewal_count"] = high_renewal_count + 1

            total_renewals += lease.renewal_count

        if self.active_leases:
            stats["average_renewal_count"] = total_renewals / len(self.active_leases)

        return stats

    def calculate_adaptive_timeout(
        self, progress: int, update_count: int, has_recent_activity: bool
    ) -> tuple[int, int]:
        """
        Calculate adaptive timeout based on task state (progressive timeout).

        Parameters
        ----------
        progress : int
            Current progress percentage (0-100)
        update_count : int
            Number of progress updates received
        has_recent_activity : bool
            Whether task shows recent activity

        Returns
        -------
        tuple[int, int]
            (lease_seconds, grace_seconds) timeout configuration

        Notes
        -----
        Progressive timeout phases:
        - Phase 1 (Unproven): No updates yet → 60s + 20s = 80s total
        - Phase 2 (Working): First update → 90s + 30s = 120s total
        - Phase 3 (Proven): 25-75% progress → 120s + 30s = 150s total
        - Phase 4 (Finishing): >75% progress → 60s + 15s = 75s total
        """
        # Phase 1: No updates yet - strict timeout
        if update_count == 0:
            return (60, 20)

        # Phase 2: First update received - moderate timeout
        if update_count == 1:
            return (90, 30)

        # Phase 4: Near completion - fast detection
        if progress >= 75:
            return (60, 15)

        # Phase 3: Good progress (25-75%) - conservative timeout
        if progress >= 25:
            return (120, 30)

        # Default: working state
        return (90, 30)

    async def should_recover_expired_lease(self, lease: AssignmentLease) -> bool:
        """
        Determine if expired lease should be recovered using cadence detection.

        Compares time since last progress update against the agent's own
        median update interval * silence_multiplier. If the agent has been
        silent for longer than expected based on its established cadence,
        it's considered dead and the task should be recovered.

        Parameters
        ----------
        lease : AssignmentLease
            The expired lease to evaluate

        Returns
        -------
        bool
            True if task should be recovered, False to give more time

        Notes
        -----
        Real data from logs: median progress interval ~47s, mean ~60s.
        Default silence_multiplier is 1.5x — configurable via constructor.

        Fallback: if fewer than 2 progress updates exist (can't compute
        median), always recover since the agent has no established cadence.
        """
        now = datetime.now(timezone.utc)
        median_interval = lease.median_update_interval

        # Not enough data to compute cadence — recover
        if median_interval is None:
            logger.info(
                f"Task {lease.task_id}: no established update cadence "
                f"(updates={len(lease.update_timestamps)}), recovering"
            )
            return True

        # Calculate silence duration from last update
        if lease.update_timestamps:
            last_update = max(lease.update_timestamps)
            silence_seconds = (now - last_update).total_seconds()
        else:
            silence_seconds = (now - lease.assigned_at).total_seconds()

        threshold = median_interval * self.silence_multiplier

        if silence_seconds > threshold:
            logger.info(
                f"Task {lease.task_id}: silence={silence_seconds:.0f}s > "
                f"threshold={threshold:.0f}s "
                f"(median={median_interval:.0f}s * "
                f"{self.silence_multiplier}x), recovering"
            )
            return True

        logger.info(
            f"Task {lease.task_id}: silence={silence_seconds:.0f}s <= "
            f"threshold={threshold:.0f}s "
            f"(median={median_interval:.0f}s * "
            f"{self.silence_multiplier}x), extending grace"
        )
        return False

    async def _create_recovery_handoff_comment(
        self, lease: AssignmentLease, recovery_info: RecoveryInfo
    ) -> None:
        """
        Post recovery information to Kanban as a comment (audit trail).

        This is the dual-write for observability. The task model holds
        the authoritative recovery info that agents use.

        Parameters
        ----------
        lease : AssignmentLease
            The lease being recovered
        recovery_info : RecoveryInfo
            The structured recovery information
        """
        # Build handoff message from recovery info
        handoff_message = (
            f"⚠️ **TASK RECOVERED FROM AGENT "
            f"{recovery_info.recovered_from_agent}**\n\n"
            f"**Recovery Details:**\n"
            f"- Recovered at: "
            f"{recovery_info.recovered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"- Progress: {recovery_info.previous_progress}%\n"
            f"- Time spent: {recovery_info.time_spent_minutes:.1f} minutes\n"
            f"- Reason: {recovery_info.recovery_reason}\n\n"
            f"{recovery_info.instructions}"
        )

        # Add comment to Kanban board
        await self.kanban_client.add_comment(lease.task_id, handoff_message)

        logger.info(
            f"Added recovery handoff comment to Kanban for task {lease.task_id}"
        )


class LeaseMonitor:
    """Background monitor for lease expiration and recovery."""

    def __init__(
        self, lease_manager: AssignmentLeaseManager, check_interval_seconds: int = 60
    ):
        """
        Initialize the lease monitor.

        Parameters
        ----------
            lease_manager
                The lease manager instance.
            check_interval_seconds
                How often to check for expired leases.
        """
        self.lease_manager = lease_manager
        self.check_interval = check_interval_seconds
        self._running = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start monitoring for expired leases."""
        if self._running:
            logger.warning("Lease monitor already running")
            return

        # Load existing leases first
        await self.lease_manager.load_active_leases()

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Lease monitor started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop the lease monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Lease monitor stopped")

    async def _monitor_loop(self) -> None:
        """Monitor lease expiration and recover dead agents."""
        while self._running:
            try:
                # Check for expired leases
                expired_leases = await self.lease_manager.check_expired_leases()

                # Recover expired leases (with smart checks)
                for lease in expired_leases:
                    should_recover = (
                        await self.lease_manager.should_recover_expired_lease(lease)
                    )

                    if not should_recover:
                        logger.info(
                            f"Skipping recovery for {lease.task_id} "
                            f"(smart checks indicate agent still working)"
                        )
                        continue

                    success = await self.lease_manager.recover_expired_lease(lease)
                    if success:
                        logger.info(
                            f"Successfully recovered expired lease for "
                            f"task {lease.task_id}"
                        )
                    else:
                        logger.error(
                            f"Failed to recover expired lease for task {lease.task_id}"
                        )

                # Log statistics periodically
                stats = self.lease_manager.get_lease_statistics()
                if stats["total_active"] > 0:
                    logger.info(
                        f"Lease stats: {stats['total_active']} active, "
                        f"{stats['expiring_soon']} expiring soon, "
                        f"{stats['expired']} expired"
                    )

                # Check for expiring leases and log warnings
                expiring = await self.lease_manager.get_expiring_leases()
                for lease in expiring:
                    logger.warning(
                        f"Lease expiring soon: task {lease.task_id} "
                        f"(expires in {lease.time_remaining})"
                    )

                await asyncio.sleep(self.check_interval)

            except asyncio.CancelledError:
                logger.warning("Lease monitor cancelled")
                raise
            except Exception as e:
                logger.error(
                    f"Error in lease monitor: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(self.check_interval)

        logger.warning("Lease monitor loop exited")
