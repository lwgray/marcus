"""
Unit tests for authentication schemas.

Tests Pydantic validation for registration, login, and token schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenRefresh,
    UserResponse,
    TokenData,
    TokenResponse,
    ErrorResponse,
    LogoutRequest,
)


class TestUserRegisterSchema:
    """Test suite for user registration schema validation."""

    def test_valid_registration(self):
        """Test valid registration data."""
        # Arrange & Act
        user = UserRegister(
            email="test@example.com",
            username="testuser",
            password="SecureP@ssw0rd123"
        )

        # Assert
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.password == "SecureP@ssw0rd123"

    def test_invalid_email_format(self):
        """Test registration with invalid email."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="invalid-email",
                username="testuser",
                password="SecureP@ssw0rd123"
            )

        assert "email" in str(exc_info.value)

    def test_username_too_short(self):
        """Test registration with username < 3 characters."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                username="ab",
                password="SecureP@ssw0rd123"
            )

        assert "username" in str(exc_info.value)

    def test_username_too_long(self):
        """Test registration with username > 50 characters."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                username="a" * 51,
                password="SecureP@ssw0rd123"
            )

        assert "username" in str(exc_info.value)

    def test_username_invalid_characters(self):
        """Test registration with invalid username characters."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                username="test-user!",
                password="SecureP@ssw0rd123"
            )

        assert "username" in str(exc_info.value)

    def test_password_too_short(self):
        """Test registration with password < 8 characters."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="Short1!"
            )

        assert "password" in str(exc_info.value)

    def test_password_too_long(self):
        """Test registration with password > 128 characters."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="A1!" + "a" * 126
            )

        assert "password" in str(exc_info.value)

    def test_password_missing_uppercase(self):
        """Test password without uppercase letter."""
        # Act & Assert
        with pytest.raises(ValidationError, match="uppercase"):
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="securep@ssw0rd123"
            )

    def test_password_missing_lowercase(self):
        """Test password without lowercase letter."""
        # Act & Assert
        with pytest.raises(ValidationError, match="lowercase"):
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="SECUREP@SSW0RD123"
            )

    def test_password_missing_digit(self):
        """Test password without digit."""
        # Act & Assert
        with pytest.raises(ValidationError, match="digit"):
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="SecureP@ssword"
            )

    def test_password_missing_special(self):
        """Test password without special character."""
        # Act & Assert
        with pytest.raises(ValidationError, match="special character"):
            UserRegister(
                email="test@example.com",
                username="testuser",
                password="SecurePassword123"
            )


class TestUserLoginSchema:
    """Test suite for user login schema validation."""

    def test_valid_login(self):
        """Test valid login data."""
        # Arrange & Act
        login = UserLogin(
            email="test@example.com",
            password="any_password"
        )

        # Assert
        assert login.email == "test@example.com"
        assert login.password == "any_password"

    def test_invalid_email(self):
        """Test login with invalid email format."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(
                email="not-an-email",
                password="password"
            )

        assert "email" in str(exc_info.value)

    def test_missing_password(self):
        """Test login without password."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            UserLogin(email="test@example.com")

        assert "password" in str(exc_info.value)


class TestTokenRefreshSchema:
    """Test suite for token refresh schema validation."""

    def test_valid_refresh_token(self):
        """Test valid refresh token data."""
        # Arrange & Act
        refresh = TokenRefresh(
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )

        # Assert
        assert refresh.refresh_token.startswith("eyJh")

    def test_missing_refresh_token(self):
        """Test refresh without token."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            TokenRefresh()

        assert "refresh_token" in str(exc_info.value)


class TestUserResponseSchema:
    """Test suite for user response schema."""

    def test_valid_user_response(self):
        """Test valid user response data."""
        # Arrange & Act
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=datetime.now(),
            last_login=None
        )

        # Assert
        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.last_login is None

    def test_user_response_with_last_login(self):
        """Test user response with last login timestamp."""
        # Arrange
        now = datetime.now()

        # Act
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=True,
            created_at=now,
            last_login=now
        )

        # Assert
        assert user.last_login == now


class TestTokenDataSchema:
    """Test suite for token data schema."""

    def test_valid_token_data(self):
        """Test valid token data structure."""
        # Arrange
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=datetime.now()
        )

        # Act
        token_data = TokenData(
            access_token="access_token_string",
            refresh_token="refresh_token_string",
            token_type="Bearer",
            expires_in=900,
            user=user
        )

        # Assert
        assert token_data.access_token == "access_token_string"
        assert token_data.refresh_token == "refresh_token_string"
        assert token_data.token_type == "Bearer"
        assert token_data.expires_in == 900
        assert token_data.user.id == 1

    def test_token_data_default_type(self):
        """Test token data with default Bearer type."""
        # Arrange
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=datetime.now()
        )

        # Act
        token_data = TokenData(
            access_token="access",
            refresh_token="refresh",
            expires_in=900,
            user=user
        )

        # Assert
        assert token_data.token_type == "Bearer"


class TestTokenResponseSchema:
    """Test suite for token response schema."""

    def test_valid_token_response(self):
        """Test valid token response structure."""
        # Arrange
        user = UserResponse(
            id=1,
            email="test@example.com",
            username="testuser",
            is_active=True,
            is_verified=False,
            created_at=datetime.now()
        )

        token_data = TokenData(
            access_token="access",
            refresh_token="refresh",
            token_type="Bearer",
            expires_in=900,
            user=user
        )

        # Act
        response = TokenResponse(
            success=True,
            message="Login successful",
            data=token_data
        )

        # Assert
        assert response.success is True
        assert response.message == "Login successful"
        assert response.data.access_token == "access"


class TestErrorResponseSchema:
    """Test suite for error response schema."""

    def test_error_response_basic(self):
        """Test basic error response."""
        # Act
        error = ErrorResponse(
            success=False,
            error="Something went wrong"
        )

        # Assert
        assert error.success is False
        assert error.error == "Something went wrong"
        assert error.details is None

    def test_error_response_with_details(self):
        """Test error response with details."""
        # Act
        error = ErrorResponse(
            success=False,
            error="Validation error",
            details={"field": "email", "issue": "invalid format"}
        )

        # Assert
        assert error.details is not None
        assert error.details["field"] == "email"


class TestLogoutRequestSchema:
    """Test suite for logout request schema."""

    def test_valid_logout_request(self):
        """Test valid logout request."""
        # Act
        logout = LogoutRequest(
            refresh_token="token_to_revoke"
        )

        # Assert
        assert logout.refresh_token == "token_to_revoke"

    def test_missing_refresh_token(self):
        """Test logout without token."""
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            LogoutRequest()

        assert "refresh_token" in str(exc_info.value)
