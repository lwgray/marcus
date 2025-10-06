"""
Database connection and session management.

This module provides SQLAlchemy database engine, session factory,
and dependency injection for FastAPI routes.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from typing import Generator

from app.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

settings = get_settings()

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    pool_pre_ping=True,  # Verify connections before using
    echo=settings.debug,  # Log SQL in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Yields
    ------
    Session
        SQLAlchemy database session

    Notes
    -----
    This function is used as a FastAPI dependency to provide
    database sessions to route handlers. The session is automatically
    closed after the request completes.

    Examples
    --------
    >>> from fastapi import Depends
    >>> @app.get("/users/")
    >>> def get_users(db: Session = Depends(get_db)):
    >>>     return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
