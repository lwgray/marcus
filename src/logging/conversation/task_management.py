"""
Task management logging functionality.

This module handles all logging related to task lifecycle management,
including assignments, progress updates, and blocker reporting.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import ConversationLoggerBase
from .conversation_types import ConversationType


class TaskManagementLogger(ConversationLoggerBase):
    """
    Logger for task management operations.

    Handles logging of task assignments, progress updates, and blocker
    reports throughout the task lifecycle.
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        """Initialize task management logger."""
        super().__init__(log_dir)
        self._setup_file_handlers()

    def _setup_file_handlers(self) -> None:
        """Set up file handlers for task management logs."""
        # Task management logs
        task_handler = self._create_rotating_handler("task_management.jsonl")
        task_handler.name = "task"
        self.logger.addHandler(task_handler)

        # Blocker-specific logs
        blocker_handler = self._create_rotating_handler("blockers.jsonl")
        blocker_handler.name = "blocker"
        self.logger.addHandler(blocker_handler)

    def log_task_assignment(
        self,
        task_id: str,
        worker_id: str,
        assignment_reason: str,
        task_details: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Log task assignment decisions with scoring rationale.

        Parameters
        ----------
        task_id : str
            Unique task identifier
        worker_id : str
            ID of worker receiving assignment
        assignment_reason : str
            Explanation for assignment decision
        task_details : dict, optional
            Task information (priority, estimated_hours, etc.)
        score : float, optional
            Assignment match score (0.0-1.0)
        alternatives_considered : list, optional
            Other workers considered with scores
        """
        entry = {
            "event": "task_assignment",
            "task_id": task_id,
            "worker_id": worker_id,
            "assignment_reason": assignment_reason,
            "task_details": self._sanitize_metadata(task_details),
            "score": score,
            "alternatives_considered": alternatives_considered or [],
        }

        self._log_entry(entry, "task")

    def log_progress_update(
        self,
        task_id: str,
        worker_id: str,
        progress_percentage: int,
        status: str,
        message: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log task progress updates from workers.

        Parameters
        ----------
        task_id : str
            Task being updated
        worker_id : str
            Worker providing update
        progress_percentage : int
            Completion percentage (0-100)
        status : str
            Current status (in_progress, testing, review)
        message : str, optional
            Progress description
        metrics : dict, optional
            Performance metrics
        """
        entry = {
            "event": "progress_update",
            "task_id": task_id,
            "worker_id": worker_id,
            "progress_percentage": progress_percentage,
            "status": status,
            "message": message,
            "metrics": self._sanitize_metadata(metrics),
        }

        self._log_entry(entry, "task")

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
        """
        Log task blockers reported by workers.

        Parameters
        ----------
        task_id : str
            Blocked task ID
        worker_id : str
            Worker reporting blocker
        blocker_description : str
            Detailed blocker description
        blocker_type : str
            Category (technical, dependency, resource, external)
        severity : str
            Impact level (low, medium, high, critical)
        dependencies : list, optional
            Related tasks or resources
        proposed_solutions : list, optional
            Worker's suggested resolutions
        metadata : dict, optional
            Additional context
        """
        entry = {
            "event": "blocker_reported",
            "task_id": task_id,
            "worker_id": worker_id,
            "blocker_description": blocker_description,
            "blocker_type": blocker_type,
            "severity": severity,
            "dependencies": dependencies or [],
            "proposed_solutions": proposed_solutions or [],
            "metadata": self._sanitize_metadata(metadata),
        }

        self._log_entry(entry, "blocker")
        # Also log to main task management
        self._log_entry(entry, "task")
