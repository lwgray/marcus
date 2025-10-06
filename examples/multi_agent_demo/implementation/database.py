"""
Database configuration and initialization for Task Management API.

This module provides database connection setup, session management,
and initialization utilities for SQLAlchemy models.
"""

import os
from typing import Generator

from models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Database URL configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./task_management.db",  # Default to SQLite for development
)

# Engine configuration
# For SQLite, we use StaticPool to share connection across threads (testing)
# For PostgreSQL/MySQL in production, use default pooling
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL query logging
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """
    Create all database tables based on SQLAlchemy models.

    This should be called once during application initialization.
    For production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use only for testing or reset.
    """
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to provide database sessions.

    Yields
    ------
    Session
        SQLAlchemy database session

    Examples
    --------
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database with tables and optional seed data.

    This is a convenience function for development/testing.
    """
    create_tables()
    print(f"Database initialized successfully at: {DATABASE_URL}")


if __name__ == "__main__":
    # For direct execution: python database.py
    init_db()
