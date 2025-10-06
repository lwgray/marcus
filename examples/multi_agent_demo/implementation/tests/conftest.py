"""
Pytest configuration and shared fixtures.

This module provides common test fixtures for database, FastAPI client,
and test data generation.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from datetime import timedelta
from typing import Generator

import pytest
from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models import Base, User
from app.utils.security import create_access_token, hash_password
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

settings = get_settings()

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")  # type: ignore[misc]
def db_session() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.

    Yields
    ------
    Session
        SQLAlchemy session connected to test database

    Notes
    -----
    Creates all tables before the test and drops them after.
    Each test gets a clean database state.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")  # type: ignore[misc]
def client(db_session: Session) -> TestClient:
    """
    Create FastAPI test client with overridden database dependency.

    Parameters
    ----------
    db_session : Session
        Test database session

    Returns
    -------
    TestClient
        FastAPI test client

    Notes
    -----
    Overrides the get_db dependency to use the test database session.
    """

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture  # type: ignore[misc]
def sample_user_data() -> dict[str, str]:
    """
    Provide sample user registration data.

    Returns
    -------
    dict[str, str]
        User registration data
    """
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "SecurePass123",  # pragma: allowlist secret
        "first_name": "Test",
        "last_name": "User",
    }


@pytest.fixture  # type: ignore[misc]
def sample_login_data() -> dict[str, str]:
    """
    Provide sample login credentials.

    Returns
    -------
    dict[str, str]
        Login credentials
    """
    return {
        "email": "test@example.com",
        "password": "SecurePass123",  # pragma: allowlist secret
    }


@pytest.fixture  # type: ignore[misc]
def test_user(db_session: Session) -> User:
    """
    Create a test user in the database.

    Parameters
    ----------
    db_session : Session
        Test database session

    Returns
    -------
    User
        Created test user model

    Notes
    -----
    Creates a user with email 'testuser@example.com', username 'testuser',
    and password 'TestPass123' (hashed with bcrypt).
    """
    user = User(
        email="testuser@example.com",
        username="testuser",
        password_hash=hash_password("TestPass123"),  # pragma: allowlist secret
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture  # type: ignore[misc]
def auth_headers(test_user: User) -> dict[str, str]:
    """
    Create valid JWT authentication headers for test user.

    Parameters
    ----------
    test_user : User
        Test user to create token for

    Returns
    -------
    dict[str, str]
        Authentication headers with Bearer token

    Notes
    -----
    Creates a JWT token valid for the default expiration time
    configured in settings (60 minutes).
    """
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "role": test_user.role.value,
    }
    access_token = create_access_token(
        token_data, expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )
    return {"Authorization": f"Bearer {access_token}"}
