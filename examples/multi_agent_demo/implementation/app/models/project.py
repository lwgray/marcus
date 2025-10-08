"""
Project model for managing projects.

Handles project entities, ownership, and relationships to tasks.
"""

from datetime import date
from sqlalchemy import String, Text, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.task import Task


class Project(Base, TimestampMixin):
    """
    Project entity for organizing tasks.

    Attributes
    ----------
    id : int
        Primary key, auto-incrementing project ID
    name : str
        Project name (max 200 characters)
    description : str, optional
        Detailed project description
    start_date : date, optional
        Project start date
    end_date : date, optional
        Project end date
    created_by : int
        Foreign key to User who created the project
    creator : User
        User who created this project
    tasks : list[Task]
        Tasks belonging to this project
    created_at : datetime
        UTC timestamp when project was created
    updated_at : datetime
        UTC timestamp when project was last updated

    Notes
    -----
    - Projects cascade delete to all associated tasks
    - Tasks cascade delete to all associated comments
    - Creator relationship uses back_populates for bidirectional navigation
    - End date should be validated to be after start date in business logic
    """

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Unique project identifier"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        doc="Project name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed project description"
    )

    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Project start date"
    )

    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="Project end date"
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to user who created the project"
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="created_projects",
        foreign_keys=[created_by],
        doc="User who created this project"
    )

    tasks: Mapped[list["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        doc="Tasks belonging to this project"
    )

    # Indexes for performance
    __table_args__ = (
        Index("ix_projects_created_by_name", "created_by", "name"),
        Index("ix_projects_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        """String representation of Project."""
        return f"<Project(id={self.id}, name='{self.name}', created_by={self.created_by})>"
