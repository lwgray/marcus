"""
Common interface for all Kanban board integrations

This abstract base class defines the standard interface that all kanban
integrations (Planka, Linear, GitHub Projects) must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task, TaskStatus


class KanbanProvider(Enum):
    """Supported kanban providers"""

    PLANKA = "planka"
    LINEAR = "linear"
    GITHUB = "github"


class KanbanInterface(ABC):
    """
    Abstract base class for kanban board integrations

    All kanban providers must implement these methods to ensure
    consistent behavior across different platforms.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize kanban provider with configuration

        Args:
            config: Provider-specific configuration
                - For Planka: url, username, password
                - For Linear: api_key, team_id
                - For GitHub: token, owner, repo, project_number
        """
        self.config = config
        self.provider = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the kanban service

        Returns:
            bool: True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """Close connection to the kanban service"""
        pass

    @abstractmethod
    async def get_available_tasks(self) -> List[Task]:
        """
        Get all unassigned tasks from backlog/ready columns

        Returns:
            List of Task objects that are available for assignment
        """
        pass

    @abstractmethod
    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from the board regardless of status or assignment

        Returns:
            List of all Task objects on the board
        """
        pass

    @abstractmethod
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get a specific task by its ID

        Args:
            task_id: The task identifier

        Returns:
            Task object or None if not found
        """
        pass

    @abstractmethod
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task on the board

        Args:
            task_data: Dictionary containing:
                - name: Task title
                - description: Task description
                - priority: Priority level
                - labels: List of labels/tags
                - estimated_hours: Time estimate

        Returns:
            Created Task object
        """
        pass

    @abstractmethod
    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
        """
        Update an existing task

        Args:
            task_id: The task identifier
            updates: Dictionary of fields to update

        Returns:
            Updated Task object
        """
        pass

    @abstractmethod
    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """
        Assign a task to a worker

        Args:
            task_id: The task identifier
            assignee_id: The worker/user identifier

        Returns:
            bool: True if assignment successful
        """
        pass

    @abstractmethod
    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """
        Move task to a specific column/status

        Args:
            task_id: The task identifier
            column_name: Target column (e.g., "In Progress", "Done")

        Returns:
            bool: True if move successful
        """
        pass

    @abstractmethod
    async def add_comment(self, task_id: str, comment: str) -> bool:
        """
        Add a comment to a task

        Args:
            task_id: The task identifier
            comment: Comment text

        Returns:
            bool: True if comment added successfully
        """
        pass

    @abstractmethod
    async def get_project_metrics(self) -> Dict[str, Any]:
        """
        Get project metrics and statistics

        Returns:
            Dictionary containing:
                - total_tasks: Total number of tasks
                - backlog_tasks: Tasks in backlog
                - in_progress_tasks: Tasks being worked on
                - completed_tasks: Completed tasks
                - blocked_tasks: Blocked tasks
        """
        pass

    @abstractmethod
    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """
        Report a blocker on a task

        Args:
            task_id: The task identifier
            blocker_description: Description of the blocker
            severity: Blocker severity (low, medium, high)

        Returns:
            bool: True if blocker reported successfully
        """
        pass

    @abstractmethod
    async def update_task_progress(
        self, task_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """
        Update task progress

        Args:
            task_id: The task identifier
            progress_data: Dictionary containing:
                - progress: Percentage complete (0-100)
                - status: Current status
                - message: Progress message

        Returns:
            bool: True if update successful
        """
        pass

    # Helper methods that can be overridden if needed

    def normalize_priority(self, provider_priority: Any) -> Priority:
        """
        Normalize provider-specific priority to standard Priority enum

        Args:
            provider_priority: Provider's priority representation

        Returns:
            Standardized Priority enum value
        """
        # Default implementation - override in specific providers
        priority_map = {
            "urgent": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
            "none": Priority.LOW,
        }

        if isinstance(provider_priority, str):
            return priority_map.get(provider_priority.lower(), Priority.MEDIUM)
        return Priority.MEDIUM

    def normalize_status(self, provider_status: Any) -> TaskStatus:
        """
        Normalize provider-specific status to standard TaskStatus enum

        Args:
            provider_status: Provider's status representation

        Returns:
            Standardized TaskStatus enum value
        """
        # Default implementation - override in specific providers
        status_map = {
            "backlog": TaskStatus.BACKLOG,
            "todo": TaskStatus.BACKLOG,
            "ready": TaskStatus.READY,
            "in progress": TaskStatus.IN_PROGRESS,
            "in_progress": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "done": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
            "closed": TaskStatus.DONE,
        }

        if isinstance(provider_status, str):
            return status_map.get(provider_status.lower(), TaskStatus.BACKLOG)
        return TaskStatus.BACKLOG
