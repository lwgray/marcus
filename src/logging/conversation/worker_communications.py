"""
Worker communication logging functionality.

This module handles all logging related to worker-PM communications,
including status updates, task reports, and bidirectional messaging.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from .base import ConversationLoggerBase
from .conversation_types import ConversationType


class WorkerCommunicationLogger(ConversationLoggerBase):
    """
    Logger for worker-PM communications.

    Handles all communication between worker agents and the PM agent,
    including status updates, task completion reports, and blocker
    notifications.
    """

    def __init__(self, log_dir: str = "logs/conversations") -> None:
        """Initialize worker communication logger."""
        super().__init__(log_dir)
        self._setup_file_handlers()

    def _setup_file_handlers(self) -> None:
        """Set up file handlers for worker communications."""
        # Worker communication logs
        worker_handler = self._create_rotating_handler("worker_communications.jsonl")
        worker_handler.name = "worker"
        self.logger.addHandler(worker_handler)

    def log_worker_message(
        self,
        worker_id: str,
        direction: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log communication messages between workers and PM agent.

        Captures bidirectional communication with workers including status updates,
        task reports, blocker notifications, and responses. Automatically determines
        conversation type based on direction and includes comprehensive metadata.

        Parameters
        ----------
        worker_id : str
            Unique identifier for the worker agent involved in communication.
            Format typically follows pattern like 'worker_backend_1' or 'worker_ui_2'.
        direction : str
            Direction of communication flow. Valid values:
            - 'to_pm': Message from worker to Marcus
            - 'from_pm': Message from Marcus to worker
        message : str
            The actual communication message content. Can include status updates,
            task completion reports, questions, or blocker descriptions.
        metadata : Optional[Dict[str, Any]], default=None
            Additional context and structured data associated with the message.
            Common fields include:
            - task_id: Associated task identifier
            - timestamp: Custom timestamp (if different from log timestamp)
            - status: Current task or worker status
            - progress: Completion percentage
            - metrics: Performance or resource metrics

        Examples
        --------
        Worker reporting task completion:

        >>> logger.log_worker_message(
        ...     worker_id="worker_backend_1",
        ...     direction="to_pm",
        ...     message="Database migration completed successfully",
        ...     metadata={
        ...         "task_id": "TASK-456",
        ...         "completion_time": "2024-01-15T14:30:00Z",
        ...         "records_migrated": 150000,
        ...         "duration_minutes": 45
        ...     }
        ... )

        Marcus assigning new task:

        >>> logger.log_worker_message(
        ...     worker_id="worker_frontend_2",
        ...     direction="from_pm",
        ...     message="New high-priority UI component task assigned",
        ...     metadata={
        ...         "task_id": "TASK-789",
        ...         "priority": "high",
        ...         "estimated_hours": 8,
        ...         "dependencies": ["TASK-456"]
        ...     }
        ... )

        Worker reporting blocker:

        >>> logger.log_worker_message(
        ...     worker_id="worker_backend_3",
        ...     direction="to_pm",
        ...     message="Blocked: API rate limit exceeded",
        ...     metadata={
        ...         "task_id": "TASK-101",
        ...         "blocker_type": "external_dependency",
        ...         "severity": "high",
        ...         "estimated_delay_hours": 4
        ...     }
        ... )

        Notes
        -----
        Messages are automatically timestamped with ISO format.
        The conversation type is determined from the direction parameter.
        All worker communications are logged at INFO level for visibility.
        Large message content is automatically truncated if necessary.

        See Also
        --------
        log_progress_update : Specialized method for progress reporting
        log_blocker : Specialized method for blocker reporting
        ConversationType : Enumeration of conversation types
        """
        conversation_type = (
            ConversationType.WORKER_TO_PM
            if direction == "to_pm"
            else ConversationType.PM_TO_WORKER
        )

        entry = {
            "event": "worker_communication",
            "worker_id": worker_id,
            "conversation_type": conversation_type.value,
            "message": message,
            "metadata": self._sanitize_metadata(metadata),
        }

        self._log_entry(entry, "worker")
