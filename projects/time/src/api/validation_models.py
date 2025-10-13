"""
Pydantic validation models with user-friendly error messages.

This module implements comprehensive input validation with clear,
helpful error messages that guide users to provide correct input.
"""

import re
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    """
    Task status enumeration with user-friendly values.

    Attributes
    ----------
    TODO : str
        Task not started yet
    IN_PROGRESS : str
        Currently working on this task
    COMPLETED : str
        Task is finished
    CANCELLED : str
        Task is no longer needed
    """

    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    """
    Task priority enumeration with clear levels.

    Attributes
    ----------
    LOW : str
        No rush, can be done anytime
    MEDIUM : str
        Normal priority, regular workflow
    HIGH : str
        Important, should be done soon
    URGENT : str
        Critical, needs immediate attention
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TaskCreate(BaseModel):
    """
    Schema for creating a new task with user-friendly validation.

    Attributes
    ----------
    title : str
        A clear, concise name for the task (3-200 characters)
    description : str, optional
        Additional details about the task
    status : TaskStatus, optional
        Current status (default: TODO)
    priority : TaskPriority, optional
        Priority level (default: MEDIUM)
    due_date : datetime, optional
        When this task needs to be completed
    start_date : datetime, optional
        When to start working on this task
    estimated_duration : int, optional
        Estimated time to complete in minutes (1-1440)
    tags : List[str], optional
        Tags for organizing tasks
    project_id : str, optional
        ID of the project this task belongs to
    parent_task_id : str, optional
        ID of parent task (for subtasks)
    recurrence_rule : str, optional
        iCal RRULE for recurring tasks

    Examples
    --------
    >>> task = TaskCreate(
    ...     title="Complete documentation",
    ...     description="Write comprehensive user guide",
    ...     priority=TaskPriority.HIGH,
    ...     due_date=datetime(2025, 10, 15, 17, 0)
    ... )
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="A clear, concise name for your task",
        examples=["Complete project documentation"],
    )

    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Additional details about the task (optional)",
        examples=["Write comprehensive user guide and API documentation"],
    )

    status: TaskStatus = Field(
        TaskStatus.TODO,
        description="Current task status (default: To Do)",
    )

    priority: TaskPriority = Field(
        TaskPriority.MEDIUM,
        description="Task priority level (default: Medium)",
    )

    due_date: Optional[datetime] = Field(
        None,
        description="When this task needs to be completed (optional)",
        examples=["2025-10-15T17:00:00Z"],
    )

    start_date: Optional[datetime] = Field(
        None,
        description="When to start working on this task (optional)",
        examples=["2025-10-10T09:00:00Z"],
    )

    estimated_duration: Optional[int] = Field(
        None,
        ge=1,
        le=1440,
        description="Estimated time to complete in minutes (1-1440, optional)",
        examples=[120],
    )

    tags: Optional[List[str]] = Field(
        None,
        max_length=10,
        description="Tags for organizing tasks (max 10, optional)",
        examples=[["documentation", "urgent"]],
    )

    project_id: Optional[str] = Field(
        None,
        description="ID of the project this task belongs to (optional)",
    )

    parent_task_id: Optional[str] = Field(
        None,
        description="ID of parent task for subtasks (optional)",
    )

    recurrence_rule: Optional[str] = Field(
        None,
        description="iCal RRULE for recurring tasks (optional)",
        examples=["FREQ=WEEKLY;BYDAY=MO,WE,FR"],
    )

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """
        Validate that title is not just whitespace.

        Parameters
        ----------
        v : str
            Title value to validate

        Returns
        -------
        str
            Cleaned title

        Raises
        ------
        ValueError
            If title is empty or only whitespace
        """
        if not v or not v.strip():
            raise ValueError(
                "Title is required and cannot be empty. "
                "Please provide a descriptive name for your task."
            )
        return v.strip()

    @field_validator("title")
    @classmethod
    def title_not_too_short(cls, v: str) -> str:
        """Validate minimum title length with helpful message."""
        if len(v) < 3:
            raise ValueError(
                "Title must be at least 3 characters long. "
                "Please provide a more descriptive task name."
            )
        return v

    @field_validator("description")
    @classmethod
    def description_clean(cls, v: Optional[str]) -> Optional[str]:
        """Clean and validate description."""
        if v:
            return v.strip()
        return v

    @field_validator("due_date")
    @classmethod
    def due_date_validation(cls, v: Optional[datetime]) -> Optional[datetime]:
        """
        Validate due date is reasonable.

        Provides helpful message if date is in the past.
        """
        if v:
            # Allow some grace period (1 hour) for timezone issues
            if v < datetime.utcnow() - timedelta(hours=1):
                raise ValueError(
                    "The due date appears to be in the past. "
                    "Please select a date and time in the future. "
                    "If you're in a different timezone, make sure to use "
                    "your local timezone setting."
                )
        return v

    @field_validator("estimated_duration")
    @classmethod
    def estimated_duration_validation(cls, v: Optional[int]) -> Optional[int]:
        """Validate estimated duration with helpful message."""
        if v is not None:
            if v < 1:
                raise ValueError(
                    "Estimated duration must be at least 1 minute. "
                    "For very short tasks, use 1 minute."
                )
            if v > 1440:
                raise ValueError(
                    "Estimated duration cannot exceed 1440 minutes (24 hours). "
                    "For longer tasks, consider breaking them into subtasks."
                )
        return v

    @field_validator("tags")
    @classmethod
    def tags_validation(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and clean tags."""
        if v:
            # Remove empty tags and trim whitespace
            cleaned_tags = [tag.strip() for tag in v if tag.strip()]

            # Check for duplicates
            if len(cleaned_tags) != len(set(cleaned_tags)):
                raise ValueError(
                    "Duplicate tags found. Please remove duplicate tag names."
                )

            # Validate tag names
            for tag in cleaned_tags:
                if len(tag) > 50:
                    raise ValueError(
                        f"Tag '{tag[:20]}...' is too long. "
                        "Tags must be 50 characters or less."
                    )
                if not re.match(r"^[a-zA-Z0-9_-]+$", tag):
                    raise ValueError(
                        f"Tag '{tag}' contains invalid characters. "
                        "Tags can only contain letters, numbers, "
                        "hyphens, and underscores."
                    )

            return cleaned_tags
        return v

    @model_validator(mode="after")
    def validate_date_relationship(self) -> "TaskCreate":
        """
        Validate relationship between start and due dates.

        Provides helpful message if dates are illogical.
        """
        if self.start_date and self.due_date:
            if self.start_date > self.due_date:
                raise ValueError(
                    "The start date cannot be after the due date. "
                    "Please adjust the dates so the start date comes first."
                )

        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Complete project documentation",
                "description": "Write comprehensive user guide and API docs",
                "status": "TODO",
                "priority": "HIGH",
                "due_date": "2025-10-15T17:00:00Z",
                "start_date": "2025-10-10T09:00:00Z",
                "estimated_duration": 120,
                "tags": ["documentation", "project-x"],
                "project_id": None,
                "parent_task_id": None,
            }
        }
    )


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.

    All fields are optional to allow partial updates.

    Attributes
    ----------
    title : str, optional
        Updated task title
    description : str, optional
        Updated description
    status : TaskStatus, optional
        Updated status
    priority : TaskPriority, optional
        Updated priority
    due_date : datetime, optional
        Updated due date
    start_date : datetime, optional
        Updated start date
    estimated_duration : int, optional
        Updated estimated duration
    actual_duration : int, optional
        Actual time spent (calculated from time entries)
    tags : List[str], optional
        Updated tags
    project_id : str, optional
        Updated project ID
    """

    title: Optional[str] = Field(
        None,
        min_length=3,
        max_length=200,
        description="Updated task title",
    )

    description: Optional[str] = Field(
        None,
        max_length=5000,
        description="Updated description",
    )

    status: Optional[TaskStatus] = Field(
        None,
        description="Updated task status",
    )

    priority: Optional[TaskPriority] = Field(
        None,
        description="Updated priority level",
    )

    due_date: Optional[datetime] = Field(
        None,
        description="Updated due date",
    )

    start_date: Optional[datetime] = Field(
        None,
        description="Updated start date",
    )

    estimated_duration: Optional[int] = Field(
        None,
        ge=1,
        le=1440,
        description="Updated estimated duration in minutes",
    )

    actual_duration: Optional[int] = Field(
        None,
        ge=0,
        description="Actual time spent (usually calculated)",
    )

    tags: Optional[List[str]] = Field(
        None,
        max_length=10,
        description="Updated tags",
    )

    project_id: Optional[str] = Field(
        None,
        description="Updated project ID",
    )

    # Reuse validators from TaskCreate
    _title_not_empty = field_validator("title")(TaskCreate.title_not_empty)
    _title_not_too_short = field_validator("title")(TaskCreate.title_not_too_short)
    _description_clean = field_validator("description")(TaskCreate.description_clean)
    _due_date_validation = field_validator("due_date")(TaskCreate.due_date_validation)
    _estimated_duration_validation = field_validator("estimated_duration")(
        TaskCreate.estimated_duration_validation
    )
    _tags_validation = field_validator("tags")(TaskCreate.tags_validation)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TaskUpdate":
        """Ensure at least one field is being updated."""
        if not any(
            getattr(self, field) is not None for field in self.model_fields.keys()
        ):
            raise ValueError(
                "Please provide at least one field to update. "
                "You haven't specified any changes."
            )
        return self


class TimeEntryCreate(BaseModel):
    """
    Schema for creating a manual time entry.

    Attributes
    ----------
    task_id : str
        ID of the task this time entry is for
    start_time : datetime
        When work started
    end_time : datetime
        When work ended
    description : str, optional
        Description of the work done
    """

    task_id: str = Field(
        ...,
        description="ID of the task this time entry is for",
    )

    start_time: datetime = Field(
        ...,
        description="When work started",
        examples=["2025-10-06T09:00:00Z"],
    )

    end_time: datetime = Field(
        ...,
        description="When work ended",
        examples=["2025-10-06T11:30:00Z"],
    )

    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Description of the work done (optional)",
        examples=["Wrote user documentation and created examples"],
    )

    @model_validator(mode="after")
    def validate_time_range(self) -> "TimeEntryCreate":
        """Validate that end time is after start time."""
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError(
                    "The end time must be after the start time. "
                    "Please check your time entry."
                )

            # Check for unreasonably long sessions
            duration = self.end_time - self.start_time
            if duration.total_seconds() > 24 * 3600:  # 24 hours
                raise ValueError(
                    "Time entry duration cannot exceed 24 hours. "
                    "For longer work periods, please create multiple entries."
                )

            # Warn about very short durations
            if duration.total_seconds() < 60:  # 1 minute
                raise ValueError(
                    "Time entry must be at least 1 minute long. "
                    "For very brief tasks, round up to 1 minute."
                )

        return self


class UserRegistration(BaseModel):
    """
    Schema for user registration with helpful validation.

    Attributes
    ----------
    email : str
        User's email address
    username : str
        Desired username (3-50 characters)
    password : str
        Password (minimum 8 characters)
    full_name : str
        User's full name
    timezone : str
        User's timezone (e.g., 'America/New_York')
    """

    email: str = Field(
        ...,
        description="Your email address",
        examples=["user@example.com"],
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Choose a username (3-50 characters)",
        examples=["johndoe"],
    )

    password: str = Field(
        ...,
        min_length=8,
        description="Create a secure password (minimum 8 characters)",
        examples=["SecurePass123!"],
    )

    full_name: str = Field(
        ...,
        max_length=255,
        description="Your full name",
        examples=["John Doe"],
    )

    timezone: str = Field(
        ...,
        description="Your timezone (e.g., 'America/New_York')",
        examples=["America/New_York"],
    )

    @field_validator("email")
    @classmethod
    def email_validation(cls, v: str) -> str:
        """Validate email format with helpful message."""
        v = v.strip().lower()

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, v):
            raise ValueError(
                "Please enter a valid email address " "(e.g., user@example.com)."
            )

        return v

    @field_validator("username")
    @classmethod
    def username_validation(cls, v: str) -> str:
        """Validate username format."""
        v = v.strip()

        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, "
                "hyphens, and underscores."
            )

        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validate password strength with helpful guidance."""
        if len(v) < 8:
            raise ValueError(
                "Password must be at least 8 characters long. "
                "Use a mix of letters, numbers, and symbols for better security."
            )

        # Check for basic complexity
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "For better security, include at least one uppercase letter, "
                "one lowercase letter, and one number in your password."
            )

        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "SecurePass123!",  # pragma: allowlist secret
                "full_name": "John Doe",
                "timezone": "America/New_York",
            }
        }
    )
