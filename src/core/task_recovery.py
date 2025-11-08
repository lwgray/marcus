"""
Task Recovery System for handling abandoned and timed-out tasks.

This module provides mechanisms to recover tasks that are stuck in "In Progress"
status due to agent disconnections, timeouts, or other failures. It includes:
- Heartbeat tracking for active agents
- Automatic task status reset for abandoned tasks
- Task reassignment logic
- Recovery strategies based on task history
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.assignment_persistence import AssignmentPersistence
from src.core.models import Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface

logger = logging.getLogger(__name__)


class RecoveryReason(Enum):
    """Reasons for task recovery."""

    AGENT_TIMEOUT = "agent_timeout"
    AGENT_DISCONNECTED = "agent_disconnected"
    TASK_ABANDONED = "task_abandoned"
    MANUAL_RECOVERY = "manual_recovery"
    TASK_STUCK = "task_stuck"


class TaskRecoveryManager:
    """Manages recovery of abandoned and stuck tasks."""

    def __init__(
        self,
        kanban_client: KanbanInterface,
        assignment_persistence: AssignmentPersistence,
        agent_timeout_minutes: int = 30,
        task_stuck_hours: int = 24,
        max_recovery_attempts: int = 3,
    ):
        """
        Initialize the Task Recovery Manager.

        Parameters
        ----------
            kanban_client
                Interface to the kanban board.
            assignment_persistence
                Persistence layer for assignments.
            agent_timeout_minutes
                Minutes before considering agent timed out.
            task_stuck_hours
                Hours before considering task stuck.
            max_recovery_attempts
                Maximum recovery attempts before escalation.
        """
        self.kanban_client = kanban_client
        self.assignment_persistence = assignment_persistence
        self.agent_timeout_minutes = agent_timeout_minutes
        self.task_stuck_hours = task_stuck_hours
        self.max_recovery_attempts = max_recovery_attempts

        # Track agent heartbeats
        self.agent_heartbeats: Dict[str, datetime] = {}

        # Track task recovery attempts
        self.recovery_attempts: Dict[str, int] = {}

        # Track tasks being recovered to prevent duplicate recovery
        self.tasks_being_recovered: Set[str] = set()

        # Recovery history for pattern analysis
        self.recovery_history: List[Dict[str, Any]] = []

    async def update_agent_heartbeat(self, agent_id: str) -> None:
        """Update the last heartbeat timestamp for an agent."""
        self.agent_heartbeats[agent_id] = datetime.now()
        logger.debug(f"Updated heartbeat for agent {agent_id}")

    async def check_agent_health(self, agent_id: str) -> bool:
        """
        Check if an agent is healthy based on heartbeat.

        Returns
        -------
            True if agent is healthy, False if timed out
        """
        if agent_id not in self.agent_heartbeats:
            return False

        last_heartbeat = self.agent_heartbeats[agent_id]
        timeout_threshold = datetime.now() - timedelta(
            minutes=self.agent_timeout_minutes
        )

        return last_heartbeat > timeout_threshold

    async def find_abandoned_tasks(self) -> List[Tuple[Task, str, RecoveryReason]]:
        """
        Find tasks that need recovery.

        Returns
        -------
            List of tuples (task, agent_id, reason) for tasks needing recovery
        """
        abandoned_tasks = []

        try:
            # Get all in-progress tasks
            all_tasks = await self.kanban_client.get_all_tasks()
            in_progress_tasks = [
                t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS
            ]

            # Get current assignments
            assignments = await self.assignment_persistence.load_assignments()

            # Check each in-progress task
            for task in in_progress_tasks:
                # Skip if already being recovered
                if task.id in self.tasks_being_recovered:
                    continue

                # Check if task is assigned in our records
                agent_id = None
                for aid, assignment in assignments.items():
                    if assignment["task_id"] == task.id:
                        agent_id = aid
                        break

                if agent_id:
                    # Check agent health
                    if not await self.check_agent_health(agent_id):
                        abandoned_tasks.append(
                            (task, agent_id, RecoveryReason.AGENT_TIMEOUT)
                        )
                        continue

                    # Check if task is stuck (no progress for too long)
                    if await self._is_task_stuck(task, assignment):
                        abandoned_tasks.append(
                            (task, agent_id, RecoveryReason.TASK_STUCK)
                        )
                else:
                    # Task is in progress but not in our assignments
                    abandoned_tasks.append(
                        (task, "unknown", RecoveryReason.TASK_ABANDONED)
                    )

            # Also check for disconnected agents
            for agent_id, assignment in assignments.items():
                if not await self.check_agent_health(agent_id):
                    task_id = assignment["task_id"]
                    # Find the task
                    task_found: Optional[Task] = None
                    for t in all_tasks:
                        if t.id == task_id:
                            task_found = t
                            break

                    if (
                        task_found is not None
                        and task_found.id not in self.tasks_being_recovered
                    ):
                        if (
                            task_found,
                            agent_id,
                            RecoveryReason.AGENT_DISCONNECTED,
                        ) not in abandoned_tasks:
                            abandoned_tasks.append(
                                (
                                    task_found,
                                    agent_id,
                                    RecoveryReason.AGENT_DISCONNECTED,
                                )
                            )

        except Exception as e:
            logger.error(f"Error finding abandoned tasks: {e}")

        return abandoned_tasks

    async def _is_task_stuck(self, task: Task, assignment: Dict[str, Any]) -> bool:
        """Check if a task has been stuck without progress."""
        # Check last progress update time
        last_update = assignment.get("last_progress_update")
        if not last_update:
            # Use assignment time if no progress updates
            last_update = assignment.get("assigned_at", datetime.now().isoformat())

        if isinstance(last_update, str):
            last_update = datetime.fromisoformat(last_update)

        stuck_threshold = datetime.now() - timedelta(hours=self.task_stuck_hours)
        return last_update < stuck_threshold

    async def recover_task(
        self,
        task: Task,
        agent_id: str,
        reason: RecoveryReason,
        new_status: TaskStatus = TaskStatus.TODO,
    ) -> bool:
        """
        Recover an abandoned task.

        Parameters
        ----------
            task
                The task to recover.
            agent_id
                The agent who was working on the task.
            reason
                Reason for recovery.
            new_status
                Status to set the task to (default: TODO).

        Returns
        -------
            True if recovery successful, False otherwise
        """
        if task.id in self.tasks_being_recovered:
            logger.warning(f"Task {task.id} already being recovered")
            return False

        self.tasks_being_recovered.add(task.id)

        try:
            # Track recovery attempt
            self.recovery_attempts[task.id] = self.recovery_attempts.get(task.id, 0) + 1

            # Log recovery attempt
            recovery_entry = {
                "task_id": task.id,
                "agent_id": agent_id,
                "reason": reason.value,
                "timestamp": datetime.now().isoformat(),
                "attempt": self.recovery_attempts[task.id],
                "previous_status": task.status.value,
                "new_status": new_status.value,
            }
            self.recovery_history.append(recovery_entry)

            logger.info(
                f"Recovering task {task.id} from agent {agent_id} "
                f"(reason: {reason.value}, attempt: {self.recovery_attempts[task.id]})"
            )

            # Remove assignment from persistence
            if agent_id != "unknown":
                await self.assignment_persistence.remove_assignment(agent_id)

            # Update task status on kanban board
            if hasattr(self.kanban_client, "update_task_status"):
                await self.kanban_client.update_task_status(task.id, new_status)

                # Note: KanbanInterface.update_task doesn't support
                # additional parameters. Skip the update_task call to
                # avoid interface limitations
                pass
            else:
                logger.warning(
                    f"Kanban client {type(self.kanban_client).__name__} "
                    "doesn't support status updates"
                )
                return False

            # Check if we've hit max recovery attempts
            if self.recovery_attempts[task.id] >= self.max_recovery_attempts:
                logger.error(
                    f"Task {task.id} has been recovered "
                    f"{self.recovery_attempts[task.id]} times. "
                    f"Consider manual intervention or task redesign."
                )
                # Could trigger escalation here

            return True

        except Exception as e:
            logger.error(f"Error recovering task {task.id}: {e}")
            return False

        finally:
            self.tasks_being_recovered.discard(task.id)

    async def recover_all_abandoned_tasks(self) -> Dict[str, List[str]]:
        """
        Find and recover all abandoned tasks.

        Returns
        -------
            Dictionary with recovery results by reason
        """
        results: Dict[str, Any] = {"recovered": [], "failed": [], "by_reason": {}}

        abandoned_tasks = await self.find_abandoned_tasks()

        for task, agent_id, reason in abandoned_tasks:
            success = await self.recover_task(task, agent_id, reason)

            if success:
                recovered_list: List[str] = results["recovered"]
                recovered_list.append(task.id)
                if reason.value not in results["by_reason"]:
                    results["by_reason"][reason.value] = []
                by_reason_list: List[str] = results["by_reason"][reason.value]
                by_reason_list.append(task.id)
            else:
                failed_list: List[str] = results["failed"]
                failed_list.append(task.id)

        if results["recovered"]:
            logger.info(f"Recovered {len(results['recovered'])} abandoned tasks")

        return results

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get statistics about task recovery."""
        stats = {
            "active_agents": len(
                [
                    aid
                    for aid, hb in self.agent_heartbeats.items()
                    if datetime.now() - hb
                    < timedelta(minutes=self.agent_timeout_minutes)
                ]
            ),
            "total_agents": len(self.agent_heartbeats),
            "recovery_attempts": dict(self.recovery_attempts),
            "high_recovery_tasks": [
                tid
                for tid, count in self.recovery_attempts.items()
                if count >= self.max_recovery_attempts
            ],
            "recovery_history_count": len(self.recovery_history),
            "recent_recoveries": self.recovery_history[-10:],  # Last 10 recoveries
        }

        # Group recovery history by reason
        by_reason = {}
        for entry in self.recovery_history:
            reason = entry["reason"]
            if reason not in by_reason:
                by_reason[reason] = 0
            by_reason[reason] += 1
        stats["recoveries_by_reason"] = by_reason

        return stats

    async def manual_recover_task(self, task_id: str) -> bool:
        """
        Manually trigger recovery for a specific task.

        Parameters
        ----------
            task_id
                ID of the task to recover.

        Returns
        -------
            True if recovery successful
        """
        try:
            # Get task details
            all_tasks = await self.kanban_client.get_all_tasks()
            task = next((t for t in all_tasks if t.id == task_id), None)

            if not task:
                logger.error(f"Task {task_id} not found")
                return False

            if task.status != TaskStatus.IN_PROGRESS:
                logger.warning(
                    f"Task {task_id} is not in progress (status: {task.status})"
                )
                return False

            # Find agent assignment
            assignments = await self.assignment_persistence.load_assignments()
            agent_id = "unknown"
            for aid, assignment in assignments.items():
                if assignment["task_id"] == task_id:
                    agent_id = aid
                    break

            # Recover the task
            return await self.recover_task(
                task, agent_id, RecoveryReason.MANUAL_RECOVERY
            )

        except Exception as e:
            logger.error(f"Error in manual task recovery: {e}")
            return False

    def clear_agent_heartbeat(self, agent_id: str) -> None:
        """Clear heartbeat for a disconnected agent."""
        if agent_id in self.agent_heartbeats:
            del self.agent_heartbeats[agent_id]
            logger.info(f"Cleared heartbeat for disconnected agent {agent_id}")


class TaskRecoveryMonitor:
    """Background monitor for automatic task recovery."""

    def __init__(
        self, recovery_manager: TaskRecoveryManager, check_interval_minutes: int = 5
    ):
        """
        Initialize the recovery monitor.

        Parameters
        ----------
            recovery_manager
                The task recovery manager.
            check_interval_minutes
                How often to check for abandoned tasks.
        """
        self.recovery_manager = recovery_manager
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self._running = False
        self._monitor_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start the recovery monitor."""
        if self._running:
            logger.warning("Task recovery monitor already running")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Task recovery monitor started (interval: {self.check_interval}s)")

    async def stop(self) -> None:
        """Stop the recovery monitor."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Task recovery monitor stopped")

    async def _monitor_loop(self) -> None:
        """Monitor for task recovery."""
        while self._running:
            try:
                # Check and recover abandoned tasks
                results = await self.recovery_manager.recover_all_abandoned_tasks()

                if results["recovered"]:
                    logger.info(
                        f"Automatic recovery completed: "
                        f"{len(results['recovered'])} tasks recovered"
                    )

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Error in task recovery monitor: {e}")
                await asyncio.sleep(self.check_interval)
