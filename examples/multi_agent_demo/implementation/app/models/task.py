"""
Task model for task management and tracking.

Handles task entities, assignments, priorities, and relationships.
"""

from datetime import date
from enum import Enum as PyEnum
from sqlalchemy import String, Text, Date, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.project import Project
    from app.models.comment import Comment


class TaskStatus(PyEnum):
    """
    Task status enumeration.

    Values
    ------
    TODO : str
        Task not started
    IN_PROGRESS : str
        Task currently being worked on
    IN_REVIEW : str
        Task completed and awaiting review
    COMPLETED : str
        Task finished and approved
    BLOCKED : str
        Task blocked by external dependency
    """
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskPriority(PyEnum):
    """
    Task priority enumeration.

    Values
    ------
    LOW : str
        Low priority task
    MEDIUM : str
        Medium priority task
    HIGH : str
        High priority task
    CRITICAL : str
        Critical priority task requiring immediate attention
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(Base, TimestampMixin):
    """
    Task entity for work tracking and management.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing task ID
    title : str
        Task title (max 200 characters)
    description : str, optional
        Detailed task description
    due_date : date, optional
        Task due date
    status : TaskStatus
        Current task status (default: TODO)
    priority : TaskPriority
        Task priority level (default: MEDIUM)
    project_id : int
        Foreign key to parent Project
    assigned_to : int, optional
        Foreign key to User assigned to this task
    created_by : int
        Foreign key to User who created this task
    project : Project
        Parent project containing this task
    assignee : User, optional
        User assigned to work on this task
    creator : User
        User who created this task
    comments : list[Comment]
        Comments associated with this task
    created_at : datetime
        UTC timestamp when task was created
    updated_at : datetime
        UTC timestamp when task was last updated

    Notes
    -----
    - Tasks cascade delete to all associated comments
    - Deleting a project will cascade delete all its tasks
    - Deleting an assigned user will cascade delete their assigned tasks
    - Creator reference is preserved (nullable) if creator is deleted
    - Status and priority use Enum for type safety
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Unique task identifier"
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        doc="Task title"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed task description"
    )

    due_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        index=True,
        doc="Task due date"
    )

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False, length=20),
        nullable=False,
        default=TaskStatus.TODO,
        server_default=TaskStatus.TODO.value,
        index=True,
        doc="Current task status"
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, native_enum=False, length=20),
        nullable=False,
        default=TaskPriority.MEDIUM,
        server_default=TaskPriority.MEDIUM.value,
        index=True,
        doc="Task priority level"
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to parent project"
    )

    assigned_to: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Foreign key to assigned user"
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to user who created the task"
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks",
        doc="Parent project containing this task"
    )

    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_tasks",
        foreign_keys=[assigned_to],
        doc="User assigned to work on this task"
    )

    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_tasks",
        foreign_keys=[created_by],
        doc="User who created this task"
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
        doc="Comments associated with this task"
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_assigned_status", "assigned_to", "status"),
        Index("ix_tasks_priority_status", "priority", "status"),
        Index("ix_tasks_due_date_status", "due_date", "status"),
    )

    def __repr__(self) -> str:
        """String representation of Task."""
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"status={self.status.value}, priority={self.priority.value})>"
        )
