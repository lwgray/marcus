"""
Database Schema Design for Task Management API.

This module defines the SQLAlchemy models for User, Project, Task, and Comment
with proper relationships and constraints.

Author: Foundation Agent
Task: Design Authentication System (task_authentication_system_design)
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all database models."""

    pass


class UserRole(enum.Enum):
    """User role enumeration."""

    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"
    VIEWER = "viewer"


class TaskStatus(enum.Enum):
    """Task status enumeration."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TaskPriority(enum.Enum):
    """Task priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class User(Base):
    """
    User model for authentication and authorization.

    Attributes
    ----------
    id : int
        Primary key
    email : str
        Unique email address for login
    username : str
        Unique username
    password_hash : str
        Bcrypt hashed password
    first_name : str
        User's first name
    last_name : str
        User's last name
    role : UserRole
        User's system role
    is_active : bool
        Account active status
    is_verified : bool
        Email verification status
    created_at : datetime
        Account creation timestamp
    updated_at : datetime
        Last update timestamp
    last_login : datetime
        Last login timestamp

    Relationships
    -------------
    projects_owned : List[Project]
        Projects created by this user
    project_memberships : List[ProjectMember]
        Project memberships
    tasks_created : List[Task]
        Tasks created by this user
    tasks_assigned : List[Task]
        Tasks assigned to this user
    comments : List[Comment]
        Comments made by this user
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login = Column(DateTime, nullable=True)

    # Relationships
    projects_owned = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    project_memberships = relationship(
        "ProjectMember", back_populates="user", cascade="all, delete-orphan"
    )
    tasks_created = relationship(
        "Task", foreign_keys="Task.created_by_id", back_populates="creator"
    )
    tasks_assigned = relationship(
        "Task", foreign_keys="Task.assigned_to_id", back_populates="assignee"
    )
    comments = relationship(
        "Comment", back_populates="author", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return string representation of User."""
        return (
            f"<User(id={self.id}, username='{self.username}', "
            f"email='{self.email}')>"
        )


class Project(Base):
    """
    Project model for organizing tasks.

    Attributes
    ----------
    id : int
        Primary key
    name : str
        Project name
    description : str
        Project description
    owner_id : int
        Foreign key to User (project owner)
    is_archived : bool
        Archive status
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp

    Relationships
    -------------
    owner : User
        Project owner
    members : List[ProjectMember]
        Project members
    tasks : List[Task]
        Tasks in this project
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    is_archived = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="projects_owned")
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (Index("ix_projects_owner_id", "owner_id"),)

    def __repr__(self) -> str:
        """Return string representation of Project."""
        return f"<Project(id={self.id}, name='{self.name}')>"


class ProjectMember(Base):
    """
    Project membership model for access control.

    Attributes
    ----------
    id : int
        Primary key
    project_id : int
        Foreign key to Project
    user_id : int
        Foreign key to User
    role : UserRole
        Member's role in this project
    joined_at : datetime
        Membership start timestamp

    Relationships
    -------------
    project : Project
        Associated project
    user : User
        Associated user
    """

    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(SQLEnum(UserRole), default=UserRole.MEMBER, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")

    # Constraints
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_user"),
        Index("ix_project_members_project_id", "project_id"),
        Index("ix_project_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of ProjectMember."""
        return (
            f"<ProjectMember(project_id={self.project_id}, "
            f"user_id={self.user_id}, role={self.role})>"
        )


class Task(Base):
    """
    Task model for work items.

    Attributes
    ----------
    id : int
        Primary key
    title : str
        Task title
    description : str
        Task description
    project_id : int
        Foreign key to Project
    created_by_id : int
        Foreign key to User (creator)
    assigned_to_id : int
        Foreign key to User (assignee)
    status : TaskStatus
        Current task status
    priority : TaskPriority
        Task priority level
    due_date : datetime
        Due date
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp
    completed_at : datetime
        Completion timestamp

    Relationships
    -------------
    project : Project
        Associated project
    creator : User
        User who created the task
    assignee : User
        User assigned to the task
    comments : List[Comment]
        Comments on this task
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    status = Column(SQLEnum(TaskStatus), default=TaskStatus.TODO, nullable=False)
    priority = Column(
        SQLEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False
    )

    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", back_populates="tasks")
    creator = relationship(
        "User", foreign_keys=[created_by_id], back_populates="tasks_created"
    )
    assignee = relationship(
        "User", foreign_keys=[assigned_to_id], back_populates="tasks_assigned"
    )
    comments = relationship(
        "Comment", back_populates="task", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_assigned_to_id", "assigned_to_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
    )

    def __repr__(self) -> str:
        """Return string representation of Task."""
        return f"<Task(id={self.id}, title='{self.title}', " f"status={self.status})>"


class Comment(Base):
    """
    Comment model for task discussions.

    Attributes
    ----------
    id : int
        Primary key
    content : str
        Comment text
    task_id : int
        Foreign key to Task
    author_id : int
        Foreign key to User
    created_at : datetime
        Creation timestamp
    updated_at : datetime
        Last update timestamp

    Relationships
    -------------
    task : Task
        Associated task
    author : User
        Comment author
    """

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    task_id = Column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    author_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")

    # Indexes
    __table_args__ = (
        Index("ix_comments_task_id", "task_id"),
        Index("ix_comments_author_id", "author_id"),
    )

    def __repr__(self) -> str:
        """Return string representation of Comment."""
        return (
            f"<Comment(id={self.id}, task_id={self.task_id}, "
            f"author_id={self.author_id})>"
        )
