"""
Database configuration and session management.

This module provides database connection setup, session management,
and utility functions for database operations.
"""

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Database URL from environment variable or default to SQLite for development
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./task_management.db")

# Create engine with appropriate configuration
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=5,  # Connection pool size
    max_overflow=10,  # Max overflow connections
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.

    Yields
    ------
    Session
        SQLAlchemy database session

    Examples
    --------
    >>> from fastapi import Depends
    >>> @app.get("/users/")
    >>> def read_users(db: Session = Depends(get_db)):
    >>>     return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.

    This function should be called on application startup to ensure
    all tables are created. In production, use Alembic for migrations.

    Examples
    --------
    >>> from app.database import init_db
    >>> init_db()
    """
    import app.models  # noqa: F401 - Import all models to register them
    from app.models.base import Base

    Base.metadata.create_all(bind=engine)
