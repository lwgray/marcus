"""
Gridlock Detection System for Marcus.

Detects when the project is in a gridlock state:
- Agents actively requesting tasks
- Tasks exist but are all blocked by dependencies
- No forward progress possible

This is a CRITICAL failure mode that requires immediate intervention.
"""

import logging
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.core.models import Task, TaskStatus

logger = logging.getLogger(__name__)


class GridlockDetector:
    """
    Detects project gridlock situations.

    Gridlock occurs when:
    1. Agents are actively requesting tasks (N requests in M minutes)
    2. Tasks exist in TODO state
    3. All TODO tasks are blocked by dependencies
    4. No tasks are actively IN_PROGRESS or being worked on

    This indicates the project cannot make forward progress.
    """

    def __init__(
        self,
        request_threshold: int = 3,
        time_window_minutes: int = 5,
        alert_cooldown_minutes: int = 10,
    ):
        """
        Initialize gridlock detector.

        Parameters
        ----------
        request_threshold : int
            Number of failed task requests to trigger detection
        time_window_minutes : int
            Time window to count requests
        alert_cooldown_minutes : int
            Minutes to wait between gridlock alerts
        """
        self.request_threshold = request_threshold
        self.time_window = timedelta(minutes=time_window_minutes)
        self.alert_cooldown = timedelta(minutes=alert_cooldown_minutes)

        # Track recent task requests that got no task
        self.recent_no_task_requests: deque = deque(maxlen=20)

        # Track last alert time
        self.last_alert_time: Optional[datetime] = None

    def record_no_task_response(self, agent_id: str) -> None:
        """
        Record that an agent requested a task but none were available.

        Parameters
        ----------
        agent_id : str
            Agent that requested task
        """
        self.recent_no_task_requests.append(
            {
                "agent_id": agent_id,
                "timestamp": datetime.now(),
            }
        )

    def check_for_gridlock(
        self,
        tasks: List[Task],
        agent_requests_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Check if project is in gridlock state.

        Parameters
        ----------
        tasks : List[Task]
            All project tasks
        agent_requests_count : Optional[int]
            Override request count (for testing)

        Returns
        -------
        Dict[str, Any]
            Gridlock detection result with diagnosis
        """
        now = datetime.now()

        # Clean old requests outside time window
        cutoff = now - self.time_window
        while (
            self.recent_no_task_requests
            and self.recent_no_task_requests[0]["timestamp"] < cutoff
        ):
            self.recent_no_task_requests.popleft()

        # Count recent failed requests
        recent_requests = (
            agent_requests_count
            if agent_requests_count is not None
            else len(self.recent_no_task_requests)
        )

        # Analyze task state
        todo_tasks = [t for t in tasks if t.status == TaskStatus.TODO]
        in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        done_tasks = [t for t in tasks if t.status == TaskStatus.DONE]

        # Check if all TODO tasks are blocked
        blocked_tasks = []
        for task in todo_tasks:
            if task.dependencies:
                # Check if any dependency is not done
                dep_ids = task.dependencies
                for dep_id in dep_ids:
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if not dep_task or dep_task.status != TaskStatus.DONE:
                        blocked_tasks.append(task)
                        break

        # GRIDLOCK CONDITIONS:
        # 1. Multiple recent failed task requests
        # 2. TODO tasks exist
        # 3. ALL TODO tasks are blocked
        # 4. Few/no tasks actively in progress

        is_gridlock = (
            recent_requests >= self.request_threshold
            and len(todo_tasks) > 0
            and len(blocked_tasks) == len(todo_tasks)
            and len(in_progress_tasks) <= 1  # At most 1 task being worked on
        )

        # Check alert cooldown
        should_alert = is_gridlock
        if self.last_alert_time and (now - self.last_alert_time) < self.alert_cooldown:
            should_alert = False

        if should_alert:
            self.last_alert_time = now

        result = {
            "is_gridlock": is_gridlock,
            "should_alert": should_alert,
            "severity": "critical" if is_gridlock else "normal",
            "metrics": {
                "recent_failed_requests": recent_requests,
                "total_tasks": len(tasks),
                "todo_tasks": len(todo_tasks),
                "blocked_tasks": len(blocked_tasks),
                "in_progress_tasks": len(in_progress_tasks),
                "done_tasks": len(done_tasks),
                "time_window_minutes": self.time_window.total_seconds() / 60,
            },
            "diagnosis": self._generate_diagnosis(
                is_gridlock,
                recent_requests,
                todo_tasks,
                blocked_tasks,
                in_progress_tasks,
            ),
        }

        if is_gridlock:
            logger.critical(
                f"🚨 GRIDLOCK DETECTED: {recent_requests} failed task requests, "
                f"{len(blocked_tasks)}/{len(todo_tasks)} TODO tasks blocked, "
                f"{len(in_progress_tasks)} in progress"
            )

        return result

    def _generate_diagnosis(
        self,
        is_gridlock: bool,
        recent_requests: int,
        todo_tasks: List[Task],
        blocked_tasks: List[Task],
        in_progress_tasks: List[Task],
    ) -> str:
        """Generate human-readable diagnosis."""
        if not is_gridlock:
            return "No gridlock detected. Project is progressing normally."

        diagnosis_parts = [
            "🚨 PROJECT GRIDLOCK DETECTED",
            "",
            "SYMPTOMS:",
            f"  • {recent_requests} agents requested tasks but none available",
            f"  • {len(todo_tasks)} tasks exist in TODO state",
            f"  • ALL {len(blocked_tasks)} TODO tasks are blocked by dependencies",
            f"  • Only {len(in_progress_tasks)} task(s) in progress",
            "",
            "ROOT CAUSE:",
            "  Likely circular dependencies or missing tasks that unlock work.",
            "",
            "IMMEDIATE ACTIONS REQUIRED:",
            "  1. Run diagnostics: diagnose_project() or capture_stall_snapshot()",
            "  2. Check for circular dependencies in task graph",
            "  3. Verify in-progress tasks haven't stalled (check lease status)",
            "  4. Consider manually unblocking a task to break the deadlock",
            "",
            f"BLOCKED TASKS ({len(blocked_tasks)}):",
        ]

        for task in blocked_tasks[:5]:  # Show first 5
            diagnosis_parts.append(f"  • {task.name} (ID: {task.id})")
            if task.dependencies:
                diagnosis_parts.append(
                    f"    Waiting for: {', '.join(task.dependencies[:3])}"
                )

        if len(blocked_tasks) > 5:
            diagnosis_parts.append(f"  ... and {len(blocked_tasks) - 5} more")

        return "\n".join(diagnosis_parts)

    def reset_alert_cooldown(self) -> None:
        """Reset alert cooldown (for testing or manual intervention)."""
        self.last_alert_time = None

    def get_statistics(self) -> Dict[str, Any]:
        """Get current detector statistics."""
        now = datetime.now()
        cutoff = now - self.time_window

        recent_requests = [
            r for r in self.recent_no_task_requests if r["timestamp"] >= cutoff
        ]

        return {
            "recent_failed_requests": len(recent_requests),
            "time_window_minutes": self.time_window.total_seconds() / 60,
            "request_threshold": self.request_threshold,
            "alert_cooldown_minutes": self.alert_cooldown.total_seconds() / 60,
            "last_alert": (
                self.last_alert_time.isoformat() if self.last_alert_time else None
            ),
        }
