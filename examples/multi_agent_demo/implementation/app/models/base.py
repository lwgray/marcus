"""
Base database configuration for SQLAlchemy models.

This module provides the declarative base and common functionality
for all database models.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamp fields.

    Attributes
    ----------
    created_at : DateTime
        Timestamp when the record was created
    updated_at : DateTime
        Timestamp when the record was last updated
    """

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BaseModel(Base, TimestampMixin):  # type: ignore[misc, valid-type]
    """
    Abstract base model with common fields.

    Attributes
    ----------
    id : Integer
        Primary key for the model
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
