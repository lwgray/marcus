"""
SQLAlchemy models for Task Management API.

This module defines the core database models for the task management system,
including User, Project, Task, and Comment entities with proper relationships.
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all SQLAlchemy models."""

    pass


class TaskStatus(enum.Enum):
    """Enumeration for task status values."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class TaskPriority(enum.Enum):
    """Enumeration for task priority values."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class User(Base):
    """
    User model representing authenticated users.

    Attributes
    ----------
    id : int
        Primary key
    email : str
        Unique email address for authentication
    username : str
        Unique username
    hashed_password : str
        Bcrypt hashed password
    full_name : str, optional
        User's full name
    is_active : bool
        Whether the user account is active
    created_at : datetime
        Timestamp of user creation
    updated_at : datetime
        Timestamp of last update

    Relationships
    -------------
    projects : List[Project]
        Projects owned by this user
    tasks : List[Task]
        Tasks assigned to this user
    comments : List[Comment]
        Comments created by this user
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    projects = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="assignee")
    comments = relationship(
        "Comment", back_populates="author", cascade="all, delete-orphan"
    )


class Project(Base):
    """
    Project model representing task containers.

    Attributes
    ----------
    id : int
        Primary key
    name : str
        Project name
    description : str, optional
        Project description
    owner_id : int
        Foreign key to User
    is_active : bool
        Whether the project is active
    created_at : datetime
        Timestamp of project creation
    updated_at : datetime
        Timestamp of last update

    Relationships
    -------------
    owner : User
        User who owns this project
    tasks : List[Task]
        Tasks belonging to this project
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")


class Task(Base):
    """
    Task model representing individual work items.

    Attributes
    ----------
    id : int
        Primary key
    title : str
        Task title
    description : str, optional
        Detailed task description
    status : TaskStatus
        Current status of the task
    priority : TaskPriority
        Task priority level
    project_id : int
        Foreign key to Project
    assignee_id : int, optional
        Foreign key to User (assigned user)
    due_date : datetime, optional
        Task due date
    created_at : datetime
        Timestamp of task creation
    updated_at : datetime
        Timestamp of last update
    completed_at : datetime, optional
        Timestamp when task was completed

    Relationships
    -------------
    project : Project
        Project this task belongs to
    assignee : User, optional
        User assigned to this task
    comments : List[Comment]
        Comments on this task
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False, index=True
    )
    priority = Column(
        SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False, index=True
    )
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    assignee_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")
    comments = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )


class Comment(Base):
    """
    Comment model representing task comments.

    Attributes
    ----------
    id : int
        Primary key
    content : str
        Comment text content
    task_id : int
        Foreign key to Task
    author_id : int
        Foreign key to User
    created_at : datetime
        Timestamp of comment creation
    updated_at : datetime
        Timestamp of last update

    Relationships
    -------------
    task : Task
        Task this comment belongs to
    author : User
        User who authored this comment
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
