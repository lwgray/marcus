"""
Comment model for task discussions.

This module defines the Comment model which allows users to add
comments and discussions to tasks.
"""

from app.models.base import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship


class Comment(BaseModel):  # type: ignore[misc]
    """
    Comment model for task discussions.

    Attributes
    ----------
    id : int
        Primary key (inherited from BaseModel)
    content : str
        Comment text content
    task_id : int
        Foreign key to Task this comment belongs to
    author_id : int
        Foreign key to User who created this comment
    created_at : datetime
        Timestamp when comment was created (inherited from TimestampMixin)
    updated_at : datetime
        Timestamp when comment was last updated (inherited from TimestampMixin)

    Relationships
    -------------
    task : Task
        Task this comment belongs to
    author : User
        User who created this comment
    """

    __tablename__ = "comments"

    content = Column(Text, nullable=False)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")

    def __repr__(self) -> str:
        """Return string representation of Comment."""
        return (
            f"<Comment(id={self.id}, task_id={self.task_id}, "
            f"author_id={self.author_id})>"
        )
