"""
User model for authentication and authorization.

Handles user accounts, authentication, and relationships to projects and tasks.
"""

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.comment import Comment


class User(Base, TimestampMixin):
    """
    User entity for authentication and authorization.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing user ID
    username : str
        Unique username for login (max 80 characters)
    email : str
        Unique email address for user (max 120 characters)
    password_hash : str
        Bcrypt hashed password (max 255 characters)
    created_projects : list[Project]
        Projects created by this user
    assigned_tasks : list[Task]
        Tasks assigned to this user
    created_tasks : list[Task]
        Tasks created by this user
    comments : list[Comment]
        Comments written by this user
    created_at : datetime
        UTC timestamp when user was created
    updated_at : datetime
        UTC timestamp when user was last updated

    Notes
    -----
    - Passwords should be hashed using bcrypt before storage
    - Use Flask-Login or similar for session management
    - Username and email must be unique
    - Cascade deletes will remove all user's comments but preserve
      projects/tasks they created (reassign ownership before delete)
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Unique user identifier"
    )

    username: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique username for login"
    )

    email: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique email address"
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Bcrypt hashed password"
    )

    # Relationships
    created_projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="creator",
        foreign_keys="Project.created_by",
        cascade="all, delete-orphan",
        doc="Projects created by this user"
    )

    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="assignee",
        foreign_keys="Task.assigned_to",
        cascade="all, delete-orphan",
        doc="Tasks assigned to this user"
    )

    created_tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="creator",
        foreign_keys="Task.created_by",
        doc="Tasks created by this user"
    )

    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        doc="Comments written by this user"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_users_username_email", "username", "email"),
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
