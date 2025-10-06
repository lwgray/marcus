"""
Integration tests for authentication API endpoints.

This module tests the complete authentication flow including registration,
login, profile access, and token refresh.

Author: Foundation Agent
Task: Implement User Management (task-1615093381082383756)
"""

from datetime import timedelta

import pytest
from app.config import get_settings
from app.models import User
from app.utils.security import create_access_token
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

settings = get_settings()


@pytest.mark.integration
class TestAuthRegistration:
    """Test suite for user registration endpoint."""

    def test_register_user_success(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test successful user registration returns token and user data."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "New",
            "last_name": "User",
        }

        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/register", json=user_data
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == settings.jwt_expire_minutes * 60
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["username"] == user_data["username"]
        assert data["user"]["first_name"] == user_data["first_name"]
        assert data["user"]["last_name"] == user_data["last_name"]
        assert "id" in data["user"]
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

        # Verify user was created in database
        user = db_session.query(User).filter(User.email == user_data["email"]).first()
        assert user is not None
        assert user.username == user_data["username"]
        assert user.is_active is True

    def test_register_user_duplicate_email(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test registration with duplicate email returns 409 Conflict."""
        # Arrange - create first user
        first_user = {
            "email": "duplicate@example.com",
            "username": "firstuser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "First",
            "last_name": "User",
        }
        client.post(f"{settings.api_v1_prefix}/auth/register", json=first_user)

        # Act - try to register with same email but different username
        second_user = {
            "email": "duplicate@example.com",
            "username": "seconduser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "Second",
            "last_name": "User",
        }
        response = client.post(
            f"{settings.api_v1_prefix}/auth/register", json=second_user
        )

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["detail"].lower()

    def test_register_user_duplicate_username(
        self, client: TestClient, db_session: Session
    ) -> None:
        """Test registration with duplicate username returns 409 Conflict."""
        # Arrange - create first user
        first_user = {
            "email": "first@example.com",
            "username": "duplicateuser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "First",
            "last_name": "User",
        }
        client.post(f"{settings.api_v1_prefix}/auth/register", json=first_user)

        # Act - try to register with same username but different email
        second_user = {
            "email": "second@example.com",
            "username": "duplicateuser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "Second",
            "last_name": "User",
        }
        response = client.post(
            f"{settings.api_v1_prefix}/auth/register", json=second_user
        )

        # Assert
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already taken" in response.json()["detail"].lower()

    def test_register_user_weak_password(self, client: TestClient) -> None:
        """Test registration with weak password returns 422 Validation Error."""
        # Arrange
        user_data = {
            "email": "weakpass@example.com",
            "username": "weakpassuser",
            "password": "weak",  # Too short  # pragma: allowlist secret
            "first_name": "Weak",
            "last_name": "Password",
        }

        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/register", json=user_data
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        errors = response.json()["detail"]
        assert any("password" in str(error).lower() for error in errors)

    def test_register_user_invalid_email(self, client: TestClient) -> None:
        """Test registration with invalid email format returns 422 Validation Error."""
        # Arrange
        user_data = {
            "email": "not-an-email",
            "username": "testuser",
            "password": "SecurePass123",  # pragma: allowlist secret
            "first_name": "Test",
            "last_name": "User",
        }

        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/register", json=user_data
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.integration
class TestAuthLogin:
    """Test suite for user login endpoint."""

    def test_login_user_success(self, client: TestClient, test_user: User) -> None:
        """Test successful login returns token and user data."""
        # Arrange
        credentials = {
            "email": test_user.email,
            "password": "TestPass123",  # pragma: allowlist secret
        }

        # Act
        response = client.post(f"{settings.api_v1_prefix}/auth/login", json=credentials)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == settings.jwt_expire_minutes * 60
        assert data["user"]["email"] == test_user.email
        assert data["user"]["username"] == test_user.username
        assert "password" not in data["user"]

    def test_login_user_invalid_email(self, client: TestClient) -> None:
        """Test login with non-existent email returns 401 Unauthorized."""
        # Arrange
        credentials = {
            "email": "nonexistent@example.com",
            "password": "TestPass123",  # pragma: allowlist secret
        }

        # Act
        response = client.post(f"{settings.api_v1_prefix}/auth/login", json=credentials)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_login_user_invalid_password(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test login with incorrect password returns 401 Unauthorized."""
        # Arrange
        credentials = {
            "email": test_user.email,
            "password": "WrongPassword123",  # pragma: allowlist secret
        }

        # Act
        response = client.post(f"{settings.api_v1_prefix}/auth/login", json=credentials)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()

    def test_login_inactive_user(
        self, client: TestClient, db_session: Session, test_user: User
    ) -> None:
        """Test login with inactive account returns 401 Unauthorized."""
        # Arrange - deactivate user
        test_user.is_active = False
        db_session.commit()

        credentials = {
            "email": test_user.email,
            "password": "TestPass123",  # pragma: allowlist secret
        }

        # Act
        response = client.post(f"{settings.api_v1_prefix}/auth/login", json=credentials)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "inactive" in response.json()["detail"].lower()


@pytest.mark.integration
class TestAuthProfile:
    """Test suite for authenticated profile endpoints."""

    def test_get_current_user_success(
        self, client: TestClient, test_user: User, auth_headers: dict[str, str]
    ) -> None:
        """Test GET /auth/me returns current user data with valid token."""
        # Act
        response = client.get(f"{settings.api_v1_prefix}/auth/me", headers=auth_headers)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert "password" not in data
        assert "password_hash" not in data

    def test_get_current_user_no_token(self, client: TestClient) -> None:
        """Test GET /auth/me without token returns 403 Forbidden."""
        # Act
        response = client.get(f"{settings.api_v1_prefix}/auth/me")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_user_invalid_token(self, client: TestClient) -> None:
        """Test GET /auth/me with invalid token returns 401 Unauthorized."""
        # Arrange
        headers = {"Authorization": "Bearer invalid.token.here"}

        # Act
        response = client.get(f"{settings.api_v1_prefix}/auth/me", headers=headers)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_expired_token(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test GET /auth/me with expired token returns 401 Unauthorized."""
        # Arrange - create expired token
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value,
        }
        expired_token = create_access_token(
            token_data, expires_delta=timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        # Act
        response = client.get(f"{settings.api_v1_prefix}/auth/me", headers=headers)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_deleted_user(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        auth_headers: dict[str, str],
    ) -> None:
        """Test GET /auth/me with valid token but deleted user returns 401."""
        # Arrange - delete user but keep token valid
        db_session.delete(test_user)
        db_session.commit()

        # Act
        response = client.get(f"{settings.api_v1_prefix}/auth/me", headers=auth_headers)

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.integration
class TestAuthRefresh:
    """Test suite for token refresh endpoint."""

    def test_refresh_token_success(
        self, client: TestClient, test_user: User, auth_headers: dict[str, str]
    ) -> None:
        """Test POST /auth/refresh returns new token with valid credentials."""
        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/refresh", headers=auth_headers
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == settings.jwt_expire_minutes * 60
        assert data["user"]["email"] == test_user.email
        assert data["user"]["username"] == test_user.username
        # Token is valid and can be used
        assert len(data["access_token"]) > 0

    def test_refresh_token_no_auth(self, client: TestClient) -> None:
        """Test POST /auth/refresh without token returns 403 Forbidden."""
        # Act
        response = client.post(f"{settings.api_v1_prefix}/auth/refresh")

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_refresh_token_invalid_token(self, client: TestClient) -> None:
        """Test POST /auth/refresh with invalid token returns 401 Unauthorized."""
        # Arrange
        headers = {"Authorization": "Bearer invalid.token.here"}

        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/refresh", headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_expired_token(
        self, client: TestClient, test_user: User
    ) -> None:
        """Test POST /auth/refresh with expired token returns 401 Unauthorized."""
        # Arrange - create expired token
        token_data = {
            "sub": str(test_user.id),
            "email": test_user.email,
            "role": test_user.role.value,
        }
        expired_token = create_access_token(
            token_data, expires_delta=timedelta(seconds=-1)
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        # Act
        response = client.post(
            f"{settings.api_v1_prefix}/auth/refresh", headers=headers
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
