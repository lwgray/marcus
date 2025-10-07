"""
Project model for organizing tasks.

This module defines the Project model which serves as a container
for related tasks and belongs to a user.
"""

from app.models.base import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship


class Project(BaseModel):  # type: ignore[misc]
    """
    Project model for grouping related tasks.

    Attributes
    ----------
    id : int
        Primary key (inherited from BaseModel)
    name : str
        Project name
    description : str, optional
        Detailed project description
    owner_id : int
        Foreign key to User who owns this project
    created_at : datetime
        Timestamp when project was created (inherited from TimestampMixin)
    updated_at : datetime
        Timestamp when project was last updated (inherited from TimestampMixin)

    Relationships
    -------------
    owner : User
        User who owns this project
    tasks : list[Task]
        Tasks belonging to this project
    """

    __tablename__ = "projects"

    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
    tasks = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return string representation of Project."""
        return f"<Project(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
