"""
Database models for the Task Management Platform.

This package contains all SQLAlchemy ORM models for the application,
following the database schema designed in database_schema.sql.
"""

from src.models.base import Base
from src.models.calendar_connection import (
    CalendarConnection,
    CalendarProvider,
    SyncStatus,
)
from src.models.project import Project
from src.models.tag import Tag, task_tags
from src.models.task import Task, TaskPriority, TaskStatus
from src.models.time_entry import TimeEntry
from src.models.user import User

__all__ = [
    "Base",
    "User",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Project",
    "Tag",
    "task_tags",
    "TimeEntry",
    "CalendarConnection",
    "CalendarProvider",
    "SyncStatus",
]
