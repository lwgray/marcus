"""Common interface for all Kanban board integrations.

This abstract base class defines the standard interface that all kanban
integrations (Planka, Linear, GitHub Projects) must implement.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from src.core.models import Priority, Task, TaskStatus


class KanbanProvider(Enum):
    """Supported kanban providers."""

    PLANKA = "planka"
    LINEAR = "linear"
    GITHUB = "github"


class KanbanInterface(ABC):
    """
    Abstract base class for kanban board integrations.

    All kanban providers must implement these methods to ensure
    consistent behavior across different platforms.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize kanban provider with configuration.

        Parameters
        ----------
        config : Dict[str, Any]
            Provider-specific configuration
            - For Planka: url, username, password
            - For Linear: api_key, team_id
            - For GitHub: token, owner, repo, project_number
        """
        self.config = config
        self.provider: Optional[KanbanProvider] = None

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the kanban service.

        Returns
        -------
        bool
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the kanban service."""
        pass

    @abstractmethod
    async def get_available_tasks(self) -> List[Task]:
        """
        Get all unassigned tasks from backlog/ready columns.

        Returns
        -------
        List[Task]
            List of Task objects that are available for assignment
        """
        pass

    @abstractmethod
    async def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from the board regardless of status or assignment.

        Returns
        -------
        List[Task]
            List of all Task objects on the board
        """
        pass

    @abstractmethod
    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get a specific task by its ID.

        Parameters
        ----------
        task_id : str
            The task identifier

        Returns
        -------
        Optional[Task]
            Task object or None if not found
        """
        pass

    @abstractmethod
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task on the board.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Dictionary containing:
                - name: Task title
                - description: Task description
                - priority: Priority level
                - labels: List of labels/tags
                - estimated_hours: Time estimate

        Returns
        -------
        Task
            Created Task object
        """
        pass

    @abstractmethod
    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[Task]:
        """
        Update an existing task.

        Parameters
        ----------
        task_id : str
            The task identifier
        updates : Dict[str, Any]
            Dictionary of fields to update

        Returns
        -------
        Optional[Task]
            Updated Task object
        """
        pass

    @abstractmethod
    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """
        Assign a task to a worker.

        Parameters
        ----------
        task_id : str
            The task identifier
        assignee_id : str
            The worker/user identifier

        Returns
        -------
        bool
            True if assignment successful
        """
        pass

    @abstractmethod
    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """
        Move task to a specific column/status.

        Parameters
        ----------
        task_id : str
            The task identifier
        column_name : str
            Target column (e.g., "In Progress", "Done")

        Returns
        -------
        bool
            True if move successful
        """
        pass

    @abstractmethod
    async def add_comment(self, task_id: str, comment: str) -> bool:
        """
        Add a comment to a task.

        Parameters
        ----------
        task_id : str
            The task identifier
        comment : str
            Comment text

        Returns
        -------
        bool
            True if comment added successfully
        """
        pass

    @abstractmethod
    async def get_project_metrics(self) -> Dict[str, Any]:
        """
        Get project metrics and statistics.

        Returns
        -------
        Dict[str, Any]
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
        Report a blocker on a task.

        Parameters
        ----------
        task_id : str
            The task identifier
        blocker_description : str
            Description of the blocker
        severity : str
            Blocker severity (low, medium, high)

        Returns
        -------
        bool
            True if blocker reported successfully
        """
        pass

    @abstractmethod
    async def update_task_progress(
        self, task_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """
        Update task progress.

        Parameters
        ----------
        task_id : str
            The task identifier
        progress_data : Dict[str, Any]
            Dictionary containing:
                - progress: Percentage complete (0-100)
                - status: Current status
                - message: Progress message

        Returns
        -------
        bool
            True if update successful
        """
        pass

    # Helper methods that can be overridden if needed

    def normalize_priority(self, provider_priority: Any) -> Priority:
        """
        Normalize provider-specific priority to standard Priority enum.

        Parameters
        ----------
        provider_priority : Any
            Provider's priority representation

        Returns
        -------
        Priority
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
        Normalize provider-specific status to standard TaskStatus enum.

        Parameters
        ----------
        provider_status : Any
            Provider's status representation

        Returns
        -------
        TaskStatus
            Standardized TaskStatus enum value
        """
        # Default implementation - override in specific providers
        status_map = {
            "backlog": TaskStatus.TODO,
            "todo": TaskStatus.TODO,
            "ready": TaskStatus.TODO,
            "in progress": TaskStatus.IN_PROGRESS,
            "in_progress": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "on hold": TaskStatus.BLOCKED,  # Treat "On Hold" same as "Blocked"
            "done": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
            "closed": TaskStatus.DONE,
        }

        if isinstance(provider_status, str):
            return status_map.get(provider_status.lower(), TaskStatus.TODO)
        return TaskStatus.TODO

    # Attachment/artifact methods - these provide a generic interface
    # for design document sharing across different kanban providers

    @abstractmethod
    async def upload_attachment(
        self,
        task_id: str,
        filename: str,
        content: Union[str, bytes],
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upload an attachment to a task.

        This method provides a generic interface for uploading design artifacts,
        documentation, and other files to tasks across different kanban providers.

        Parameters
        ----------
        task_id : str
            The task identifier (provider-specific format)
        filename : str
            Name for the attachment
        content : Union[str, bytes]
            File content (base64 string or bytes)
        content_type : Optional[str]
            MIME type (e.g., 'application/json', 'text/markdown')

        Returns
        -------
        Dict[str, Any]
            Dict with attachment details including:
            - success: bool indicating if upload was successful
            - data: Dict containing:
                - id: Attachment identifier
                - filename: The filename
                - url: URL to access the attachment (if available)
                - size: File size in bytes
            - error: Error message if success is False
        """
        pass

    @abstractmethod
    async def get_attachments(self, task_id: str) -> Dict[str, Any]:
        """
        Get all attachments for a task.

        Parameters
        ----------
        task_id : str
            The task identifier

        Returns
        -------
        Dict[str, Any]
            Dict containing:
            - success: bool
            - data: List of attachment objects with:
                - id: Attachment identifier
                - filename: The filename
                - url: URL to access the attachment
                - created_at: Creation timestamp (ISO format)
                - created_by: User who uploaded it (if available)
            - error: Error message if success is False
        """
        pass

    @abstractmethod
    async def download_attachment(
        self, attachment_id: str, filename: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download an attachment.

        Parameters
        ----------
        attachment_id : str
            The attachment ID
        filename : str
            The filename (required by some providers)
        task_id : Optional[str]
            Optional task ID (required by some providers)

        Returns
        -------
        Dict[str, Any]
            Dict containing:
            - success: bool
            - data: Dict with:
                - content: Base64 encoded file content
                - filename: The filename
                - content_type: MIME type if available
            - error: Error message if success is False
        """
        pass

    async def delete_attachment(
        self, attachment_id: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete an attachment (optional - not all providers support this).

        Parameters
        ----------
        attachment_id : str
            The attachment ID
        task_id : Optional[str]
            Optional task ID (required by some providers)

        Returns
        -------
        Dict[str, Any]
            Dict containing:
            - success: bool
            - error: Error message if not supported or failed
        """
        return {
            "success": False,
            "error": "Attachment deletion not supported by this provider",
        }

    async def update_attachment(
        self,
        attachment_id: str,
        filename: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update attachment metadata (optional - not all providers support this).

        Parameters
        ----------
        attachment_id : str
            The attachment ID
        filename : Optional[str]
            New filename
        task_id : Optional[str]
            Optional task ID (required by some providers)

        Returns
        -------
        Dict[str, Any]
            Dict containing:
            - success: bool
            - data: Updated attachment info if successful
            - error: Error message if not supported or failed
        """
        return {
            "success": False,
            "error": "Attachment updates not supported by this provider",
        }
