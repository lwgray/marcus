"""
Comment model for task discussions.

Handles comment entities and relationships to tasks and users.
"""

from sqlalchemy import Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class Comment(Base, TimestampMixin):
    """
    Comment entity for task discussions and updates.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing comment ID
    text : str
        Comment text content
    user_id : int
        Foreign key to User who wrote the comment
    task_id : int
        Foreign key to Task this comment belongs to
    author : User
        User who wrote this comment
    task : Task
        Task this comment is associated with
    created_at : datetime
        UTC timestamp when comment was created
    updated_at : datetime
        UTC timestamp when comment was last updated

    Notes
    -----
    - Comments are cascade deleted when parent task is deleted
    - Comments are cascade deleted when author user is deleted
    - Use updated_at to track edited comments
    - Text field supports markdown formatting in application layer
    """

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Unique comment identifier"
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Comment text content"
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user who wrote the comment"
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to task this comment belongs to"
    )

    # Relationships
    author: Mapped["User"] = relationship(
        "User",
        back_populates="comments",
        doc="User who wrote this comment"
    )

    task: Mapped["Task"] = relationship(
        "Task",
        back_populates="comments",
        doc="Task this comment is associated with"
    )

    # Indexes for common query patterns
    __table_args__ = (
        Index("ix_comments_task_created", "task_id", "created_at"),
        Index("ix_comments_user_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of Comment."""
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<Comment(id={self.id}, task_id={self.task_id}, author_id={self.user_id}, text='{text_preview}')>"
