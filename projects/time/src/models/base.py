"""
Base model and database configuration.

This module provides the declarative base for all SQLAlchemy models
and common functionality shared across models.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# Declarative base for all models
Base = declarative_base()


class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps.

    Automatically tracks creation and modification times for all models.

    Attributes
    ----------
    created_at : datetime
        When the record was created (auto-set)
    updated_at : datetime
        When the record was last updated (auto-updated)
    """

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When this record was created",
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        doc="When this record was last updated",
    )


def generate_uuid() -> str:
    """
    Generate a UUID string for primary keys.

    Returns
    -------
    str
        UUID string
    """
    return str(uuid.uuid4())
