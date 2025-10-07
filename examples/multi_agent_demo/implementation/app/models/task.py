"""
Task model for task management.

This module defines the Task model which represents individual tasks
within projects, with assignees and status tracking.
"""

import enum

from app.models.base import BaseModel
from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class TaskStatus(str, enum.Enum):
    """
    Enumeration of possible task statuses.

    Attributes
    ----------
    TODO : str
        Task is not yet started
    IN_PROGRESS : str
        Task is currently being worked on
    COMPLETED : str
        Task has been completed
    CANCELLED : str
        Task was cancelled
    """

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    """
    Enumeration of task priority levels.

    Attributes
    ----------
    LOW : str
        Low priority task
    MEDIUM : str
        Medium priority task
    HIGH : str
        High priority task
    URGENT : str
        Urgent priority task
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(BaseModel):  # type: ignore[misc]
    """
    Task model for individual work items.

    Attributes
    ----------
    id : int
        Primary key (inherited from BaseModel)
    title : str
        Task title
    description : str, optional
        Detailed task description
    status : TaskStatus
        Current task status (default: TODO)
    priority : TaskPriority
        Task priority level (default: MEDIUM)
    project_id : int
        Foreign key to Project this task belongs to
    assignee_id : int, optional
        Foreign key to User assigned to this task
    created_at : datetime
        Timestamp when task was created (inherited from TimestampMixin)
    updated_at : datetime
        Timestamp when task was last updated (inherited from TimestampMixin)

    Relationships
    -------------
    project : Project
        Project this task belongs to
    assignee : User, optional
        User assigned to this task
    comments : list[Comment]
        Comments on this task
    """

    __tablename__ = "tasks"

    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        Enum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True
    )
    priority = Column(
        Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, index=True
    )
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")
    comments = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of Task."""
        return (
            f"<Task(id={self.id}, title='{self.title}', "
            f"status='{self.status.value}')>"
        )
