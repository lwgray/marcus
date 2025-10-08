"""
Shared pytest fixtures for all tests.

Provides fixtures for:
- Database session management
- Test client configuration
- Sample data factories
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import the actual Base and models from the app
from app.models.base import Base
from app.models import User, RefreshToken, Project, Task, Comment, UserRole  # noqa: F401

# Test database URL (file-based SQLite for async compatibility)
# Use a temp file that gets cleaned up after tests
import tempfile
import os
TEST_DB_FILE = os.path.join(tempfile.gettempdir(), "test_db.sqlite")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_FILE}"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """
    Create async test database engine.

    Uses in-memory SQLite for fast test execution.
    Recreates schema for each test function.

    Yields
    ------
    AsyncEngine
        Test database engine
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

    # Clean up test database file
    if os.path.exists(TEST_DB_FILE):
        os.remove(TEST_DB_FILE)


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """
    Create async database session for tests.

    Each test gets a fresh session with clean tables.

    Parameters
    ----------
    db_engine : AsyncEngine
        Test database engine

    Yields
    ------
    AsyncSession
        Test database session
    """
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_user_data():
    """
    Provide sample user registration data.

    Returns
    -------
    dict
        User registration data
    """
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecureP@ssw0rd123",  # pragma: allowlist secret
        "full_name": "Test User",
    }


@pytest.fixture
def sample_login_data():
    """
    Provide sample login credentials.

    Returns
    -------
    dict
        Login credentials
    """
    return {
        "email": "test@example.com",
        "password": "SecureP@ssw0rd123",  # pragma: allowlist secret
    }
