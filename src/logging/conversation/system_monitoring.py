"""
System monitoring and state logging functionality.

This module handles logging of overall system health, resource utilization,
and performance metrics.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import ConversationLoggerBase


class SystemMonitoringLogger(ConversationLoggerBase):
    """
    Logger for system state and performance monitoring.

    Captures system-wide metrics, resource utilization, and health
    indicators for performance analysis and optimization.
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        """Initialize system monitoring logger."""
        super().__init__(log_dir)
        self._setup_file_handlers()

    def _setup_file_handlers(self) -> None:
        """Set up file handlers for system monitoring logs."""
        # System state logs
        system_handler = self._create_rotating_handler("system_state.jsonl")
        system_handler.name = "system"
        self.logger.addHandler(system_handler)

    def log_system_state(
        self,
        active_workers: int,
        tasks_in_progress: int,
        tasks_completed: int,
        tasks_blocked: int = 0,
        queue_length: int = 0,
        system_metrics: Optional[Dict[str, Any]] = None,
        worker_states: Optional[Dict[str, str]] = None,
        performance_indicators: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Log overall system state and performance metrics.

        Captures comprehensive system health snapshot including worker
        availability, task queue status, resource utilization, and
        performance indicators for monitoring and optimization.

        Parameters
        ----------
        active_workers : int
            Number of currently active worker agents processing tasks.
        tasks_in_progress : int
            Count of tasks currently being processed across all workers.
        tasks_completed : int
            Total completed tasks in current session or time window.
        tasks_blocked : int, default=0
            Number of tasks currently blocked by dependencies or issues.
        queue_length : int, default=0
            Number of tasks waiting for assignment in backlog.
        system_metrics : dict, optional
            Resource utilization metrics including:
            - cpu_usage: CPU utilization percentage (0.0-1.0)
            - memory_usage: Memory utilization percentage (0.0-1.0)
            - api_calls_remaining: Available API quota
            - kanban_sync_latency: Board synchronization delay in ms
        worker_states : dict, optional
            Current state of each worker agent. Keys are worker IDs,
            values are states (idle, busy, blocked, offline).
        performance_indicators : dict, optional
            System performance metrics including:
            - avg_task_completion_time: Average task duration in hours
            - throughput_per_hour: Tasks completed per hour
            - assignment_efficiency: Successful assignment ratio
            - blocker_resolution_time: Average blocker resolution hours

        Examples
        --------
        Basic system state logging:

        >>> logger.log_system_state(
        ...     active_workers=5,
        ...     tasks_in_progress=12,
        ...     tasks_completed=45,
        ...     tasks_blocked=2,
        ...     queue_length=8
        ... )

        Comprehensive state with metrics:

        >>> logger.log_system_state(
        ...     active_workers=5,
        ...     tasks_in_progress=12,
        ...     tasks_completed=45,
        ...     tasks_blocked=2,
        ...     queue_length=8,
        ...     system_metrics={
        ...         "cpu_usage": 0.75,
        ...         "memory_usage": 0.60,
        ...         "api_calls_remaining": 850,
        ...         "kanban_sync_latency": 125.5
        ...     },
        ...     worker_states={
        ...         "worker_backend_1": "busy",
        ...         "worker_backend_2": "busy",
        ...         "worker_frontend_1": "idle",
        ...         "worker_test_1": "blocked",
        ...         "worker_devops_1": "busy"
        ...     },
        ...     performance_indicators={
        ...         "avg_task_completion_time": 3.5,
        ...         "throughput_per_hour": 2.8,
        ...         "assignment_efficiency": 0.92,
        ...         "blocker_resolution_time": 1.2
        ...     }
        ... )

        Notes
        -----
        System state should be logged periodically (e.g., every 5 minutes)
        for trend analysis. Sudden changes in metrics may indicate issues
        requiring attention. All numeric metrics are stored as floats for
        consistent analysis.
        """
        entry = {
            "event": "system_state",
            "active_workers": active_workers,
            "tasks_in_progress": tasks_in_progress,
            "tasks_completed": tasks_completed,
            "tasks_blocked": tasks_blocked,
            "queue_length": queue_length,
            "system_metrics": self._sanitize_metadata(system_metrics),
            "worker_states": worker_states or {},
            "performance_indicators": performance_indicators or {},
        }

        self._log_entry(entry, "system")
