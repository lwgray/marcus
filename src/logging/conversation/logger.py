"""
Main conversation logger that composes specialized loggers.

This module provides the main ConversationLogger class that maintains
the original API while delegating to specialized logger components.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ConversationLoggerBase
from .pm_operations import PMOperationsLogger
from .system_monitoring import SystemMonitoringLogger
from .task_management import TaskManagementLogger
from .worker_communications import WorkerCommunicationLogger


class ConversationLogger:
    """
    Main conversation logger for the Marcus system.

    This class provides a unified interface for all conversation logging
    while delegating to specialized loggers for different aspects of
    the system.
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        """
        Initialize the conversation logger.

        Parameters
        ----------
        log_dir : str
            Directory for storing log files
        """
        self.log_dir = log_dir

        # Initialize specialized loggers
        self._worker_logger = WorkerCommunicationLogger(log_dir)
        self._pm_logger = PMOperationsLogger(log_dir)
        self._task_logger = TaskManagementLogger(log_dir)
        self._system_logger = SystemMonitoringLogger(log_dir)

        # Maintain compatibility attributes
        self.start_time = datetime.now()

    # Worker communication methods
    def log_worker_message(
        self,
        worker_id: str,
        direction: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log communication messages between workers and PM agent."""
        self._worker_logger.log_worker_message(worker_id, direction, message, metadata)

    # PM operation methods
    def log_pm_thinking(
        self,
        thought: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log Marcus' internal reasoning and thought processes."""
        self._pm_logger.log_pm_thinking(thought, context)

    def log_pm_decision(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: Optional[List[str]] = None,
        confidence_score: Optional[float] = None,
        decision_factors: Optional[Dict[str, Any]] = None,
        affected_tasks: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log formal decisions made by the PM agent."""
        self._pm_logger.log_pm_decision(
            decision,
            rationale,
            alternatives_considered,
            confidence_score,
            decision_factors,
            affected_tasks,
            metadata,
        )

    # Task management methods
    def log_task_assignment(
        self,
        task_id: str,
        worker_id: str,
        assignment_reason: str,
        task_details: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Log task assignment decisions with scoring rationale."""
        self._task_logger.log_task_assignment(
            task_id,
            worker_id,
            assignment_reason,
            task_details,
            score,
            alternatives_considered,
        )

    def log_progress_update(
        self,
        task_id: str,
        worker_id: str,
        progress_percentage: int,
        status: str,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log task progress updates from workers."""
        self._task_logger.log_progress_update(
            task_id,
            worker_id,
            progress_percentage,
            status,
            message,
            metrics,
        )

    def log_blocker(
        self,
        task_id: str,
        worker_id: str,
        blocker_description: str,
        blocker_type: str,
        severity: str = "medium",
        dependencies: Optional[List[str]] = None,
        proposed_solutions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log task blockers reported by workers."""
        self._task_logger.log_blocker(
            task_id,
            worker_id,
            blocker_description,
            blocker_type,
            severity,
            dependencies,
            proposed_solutions,
            metadata,
        )

    # System monitoring methods
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
        """Log overall system state and performance metrics."""
        self._system_logger.log_system_state(
            active_workers,
            tasks_in_progress,
            tasks_completed,
            tasks_blocked,
            queue_length,
            system_metrics,
            worker_states,
            performance_indicators,
        )
