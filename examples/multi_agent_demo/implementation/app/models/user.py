"""
User model for authentication and user management.

This module defines the User model with email/password authentication
and relationships to projects, tasks, and comments.
"""

from app.models.base import BaseModel
from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship


class User(BaseModel):  # type: ignore[misc]
    """
    User model for authentication and authorization.

    Attributes
    ----------
    id : int
        Primary key (inherited from BaseModel)
    email : str
        Unique email address for the user
    hashed_password : str
        Bcrypt hashed password
    full_name : str, optional
        User's full name
    is_active : bool
        Whether the user account is active (default: True)
    is_superuser : bool
        Whether the user has superuser privileges (default: False)
    created_at : datetime
        Timestamp when user was created (inherited from TimestampMixin)
    updated_at : datetime
        Timestamp when user was last updated (inherited from TimestampMixin)

    Relationships
    -------------
    projects : list[Project]
        Projects owned by this user
    tasks : list[Task]
        Tasks assigned to this user
    comments : list[Comment]
        Comments created by this user
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Relationships
    projects = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tasks = relationship(
        "Task",
        back_populates="assignee",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    comments = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of User."""
        return f"<User(id={self.id}, email='{self.email}')>"
