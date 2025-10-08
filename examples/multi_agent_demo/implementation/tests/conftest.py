"""
Shared pytest fixtures for all tests.

Provides fixtures for:
- Database session management
- Test client configuration
- Sample data factories
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import declarative_base


# Create a base for test models (import models after to register them)
Base = declarative_base()

# Import models to register with Base
try:
    from app.models import User, RefreshToken  # noqa: F401
except ImportError:
    # Models may not be available in all test scenarios
    pass

# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
