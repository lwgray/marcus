"""
Base model configuration for SQLAlchemy ORM.

Provides shared base class and common utilities for all database models.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Naming convention for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Provides:
    - Consistent metadata with naming conventions
    - Common timestamp fields
    - Utility methods for serialization
    """

    metadata = metadata

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of model with column values.
        """
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }


class TimestampMixin:
    """
    Mixin providing automatic timestamp fields.

    Adds created_at and updated_at columns with automatic updates.
    All timestamps use UTC timezone.
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when record was created (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when record was last updated (UTC)",
    )
