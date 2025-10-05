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
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.assignment_persistence import AssignmentPersistence
from src.core.event_loop_utils import EventLoopLockManager
from src.core.models import Task, TaskStatus
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

    @property
    def time_remaining(self) -> timedelta:
        """Calculate time remaining on lease."""
        return self.lease_expires - datetime.now()

    @property
    def is_expired(self) -> bool:
        """Check if lease has expired."""
        return datetime.now() > self.lease_expires

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


class AssignmentLeaseManager:
    """Manages assignment leases with automatic expiration and renewal."""

    def __init__(
        self,
        kanban_client: KanbanInterface,
        assignment_persistence: AssignmentPersistence,
        default_lease_hours: float = 4.0,
        max_renewals: int = 10,
        warning_threshold_hours: float = 1.0,
        priority_multipliers: Optional[Dict[str, float]] = None,
        complexity_multipliers: Optional[Dict[str, float]] = None,
        grace_period_minutes: int = 30,
        renewal_decay_factor: float = 0.9,
        min_lease_hours: float = 1.0,
        max_lease_hours: float = 24.0,
        stuck_task_threshold_renewals: int = 5,
        enable_adaptive_leases: bool = True,
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
                Grace period after expiry before recovery.
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
        """
        self.kanban_client = kanban_client
        self.assignment_persistence = assignment_persistence
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

        # Active leases tracked in memory
        self.active_leases: Dict[str, AssignmentLease] = {}

        # Track lease history for analysis
        self.lease_history: List[Dict[str, Any]] = []

        # Lock manager for event loop safe operations
        self._lock_manager = EventLoopLockManager()

    @property
    def lease_lock(self) -> asyncio.Lock:
        """Get lease lock for the current event loop."""
        return self._lock_manager.get_lock()

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
            now = datetime.now()

            # Calculate initial lease duration
            base_hours = self.default_lease_hours

            if task and self.enable_adaptive_leases:
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

            # Calculate renewal duration
            renewal_duration = lease.calculate_renewal_duration(self)

            # Renew lease
            lease.last_renewed = datetime.now()
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
                    "timestamp": datetime.now().isoformat(),
                    "progress": progress,
                    "renewal_count": lease.renewal_count,
                    "new_expiry": lease.lease_expires.isoformat(),
                }
            )

            return lease

    async def check_expired_leases(self) -> List[AssignmentLease]:
        """
        Check for expired leases that need recovery.

        Returns
        -------
            List of expired leases (considering grace period)
        """
        expired_leases = []
        now = datetime.now()
        grace_delta = timedelta(minutes=self.grace_period_minutes)

        async with self.lease_lock:
            for task_id, lease in list(self.active_leases.items()):
                if lease.is_expired:
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

    async def recover_expired_lease(self, lease: AssignmentLease) -> bool:
        """
        Recover a task with an expired lease.

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

            # Remove from active leases
            async with self.lease_lock:
                if lease.task_id in self.active_leases:
                    del self.active_leases[lease.task_id]

            # Remove assignment from persistence
            await self.assignment_persistence.remove_assignment(lease.agent_id)

            # Update task status to TODO
            if hasattr(self.kanban_client, "update_task_status"):
                await self.kanban_client.update_task_status(
                    lease.task_id, TaskStatus.TODO
                )

                # Note: KanbanInterface.update_task doesn't support
                # additional parameters. Skip the update_task call to
                # avoid interface limitations
                pass

            # Track in history
            self.lease_history.append(
                {
                    "event": "lease_recovered",
                    "task_id": lease.task_id,
                    "agent_id": lease.agent_id,
                    "timestamp": datetime.now().isoformat(),
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
            assignment["last_progress_update"] = datetime.now().isoformat()
            await self.assignment_persistence.save_assignment(
                lease.agent_id,
                lease.task_id,
                assignment.get("assigned_at", datetime.now().isoformat()),
            )

    async def load_active_leases(self) -> None:
        """Load active leases from persistence on startup."""
        assignments = await self.assignment_persistence.load_assignments()

        for agent_id, assignment in assignments.items():
            task_id = assignment["task_id"]

            # Reconstruct lease from assignment
            lease = AssignmentLease(
                task_id=task_id,
                agent_id=agent_id,
                assigned_at=datetime.fromisoformat(assignment["assigned_at"]),
                lease_expires=datetime.fromisoformat(
                    assignment.get("lease_expires", datetime.now().isoformat())
                ),
                last_renewed=datetime.fromisoformat(
                    assignment.get("lease_renewed_at", assignment["assigned_at"])
                ),
                renewal_count=assignment.get("renewal_count", 0),
                progress_percentage=assignment.get("progress_percentage", 0),
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
        """Monitor lease."""
        while self._running:
            try:
                # Check for expired leases
                expired_leases = await self.lease_manager.check_expired_leases()

                # Recover expired leases
                for lease in expired_leases:
                    success = await self.lease_manager.recover_expired_lease(
                        lease
                    )
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

            except Exception as e:
                logger.error(f"Error in lease monitor: {e}")
                await asyncio.sleep(self.check_interval)
