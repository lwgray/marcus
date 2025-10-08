"""
Unit tests for JWT token handling.

Tests JWT token creation, verification, and user extraction.
"""

import pytest
import time
from datetime import timedelta
import jwt as pyjwt
from app.security.jwt_handler import (
    create_access_token,
    verify_token,
    get_current_user,
    refresh_token,
    decode_token_without_verification,
    TokenExpiredError,
    TokenInvalidError,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
)


class TestCreateAccessToken:
    """Test suite for access token creation."""

    def test_create_access_token_returns_string(self) -> None:
        """Test that create_access_token returns a JWT string."""
        # Act
        token = create_access_token(user_id=1, username="testuser")

        # Assert
        assert isinstance(token, str)
        assert len(token) > 100  # JWTs are typically long

    def test_create_access_token_includes_user_data(self) -> None:
        """Test that token includes user ID and username."""
        # Act
        token = create_access_token(user_id=42, username="john")
        payload = decode_token_without_verification(token)

        # Assert
        assert payload["user_id"] == 42
        assert payload["sub"] == "john"

    def test_create_access_token_includes_timestamps(self) -> None:
        """Test that token includes iat and exp claims."""
        # Act
        token = create_access_token(user_id=1, username="test")
        payload = decode_token_without_verification(token)

        # Assert
        assert "iat" in payload  # Issued at
        assert "exp" in payload  # Expiration

    def test_create_access_token_custom_expiration(self) -> None:
        """Test creating token with custom expiration."""
        # Arrange
        short_expiration = timedelta(minutes=5)

        # Act
        token = create_access_token(
            user_id=1, username="test", expires_delta=short_expiration
        )
        payload = decode_token_without_verification(token)

        # Assert
        exp_diff = payload["exp"] - payload["iat"]
        assert exp_diff == 300  # 5 minutes in seconds

    def test_create_access_token_additional_claims(self) -> None:
        """Test adding custom claims to token."""
        # Arrange
        custom_claims = {"role": "admin", "permissions": ["read", "write"]}

        # Act
        token = create_access_token(
            user_id=1, username="admin", additional_claims=custom_claims
        )
        payload = decode_token_without_verification(token)

        # Assert
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]


class TestVerifyToken:
    """Test suite for token verification."""

    def test_verify_token_valid_token(self) -> None:
        """Test verifying a valid token."""
        # Arrange
        token = create_access_token(user_id=1, username="test")

        # Act
        payload = verify_token(token)

        # Assert
        assert payload["user_id"] == 1
        assert payload["sub"] == "test"

    def test_verify_token_expired_token(self) -> None:
        """Test that expired tokens raise TokenExpiredError."""
        # Arrange - create token with negative expiration
        expired_token = create_access_token(
            user_id=1,
            username="test",
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        # Act & Assert
        with pytest.raises(TokenExpiredError) as exc_info:
            verify_token(expired_token)
        assert "expired" in str(exc_info.value).lower()

    def test_verify_token_invalid_signature(self) -> None:
        """Test that tokens with invalid signature raise TokenInvalidError."""
        # Arrange - create token with wrong secret
        invalid_token = pyjwt.encode(
            {"user_id": 1, "sub": "test"},
            "wrong-secret",
            algorithm=JWT_ALGORITHM
        )

        # Act & Assert
        with pytest.raises(TokenInvalidError):
            verify_token(invalid_token)

    def test_verify_token_malformed_token(self) -> None:
        """Test that malformed tokens raise TokenInvalidError."""
        # Arrange
        malformed_token = "not.a.valid.jwt.token"

        # Act & Assert
        with pytest.raises(TokenInvalidError):
            verify_token(malformed_token)

    def test_verify_token_empty_string(self) -> None:
        """Test that empty string raises TokenInvalidError."""
        # Act & Assert
        with pytest.raises(TokenInvalidError):
            verify_token("")


class TestGetCurrentUser:
    """Test suite for extracting user from token."""

    def test_get_current_user_valid_token(self) -> None:
        """Test extracting user info from valid token."""
        # Arrange
        token = create_access_token(user_id=123, username="john")

        # Act
        user = get_current_user(token)

        # Assert
        assert user["user_id"] == 123
        assert user["username"] == "john"

    def test_get_current_user_with_additional_claims(self) -> None:
        """Test that additional claims are included."""
        # Arrange
        token = create_access_token(
            user_id=1,
            username="admin",
            additional_claims={"role": "admin"}
        )

        # Act
        user = get_current_user(token)

        # Assert
        assert user["role"] == "admin"

    def test_get_current_user_expired_token(self) -> None:
        """Test that expired token raises TokenExpiredError."""
        # Arrange
        expired_token = create_access_token(
            user_id=1,
            username="test",
            expires_delta=timedelta(seconds=-1)
        )

        # Act & Assert
        with pytest.raises(TokenExpiredError):
            get_current_user(expired_token)

    def test_get_current_user_missing_user_id(self) -> None:
        """Test that token missing user_id raises error."""
        # Arrange - manually create token without user_id
        token = pyjwt.encode(
            {"sub": "test"},  # Missing user_id
            JWT_SECRET_KEY,
            algorithm=JWT_ALGORITHM
        )

        # Act & Assert
        with pytest.raises(TokenInvalidError) as exc_info:
            get_current_user(token)
        assert "missing required user claims" in str(exc_info.value).lower()


class TestRefreshToken:
    """Test suite for token refresh functionality."""

    def test_refresh_token_creates_new_token(self) -> None:
        """Test that refresh creates a new token."""
        # Arrange
        old_token = create_access_token(user_id=1, username="test")

        # Wait to ensure different timestamp
        time.sleep(1)

        # Act
        new_token = refresh_token(old_token)

        # Assert
        assert new_token != old_token
        assert isinstance(new_token, str)

    def test_refresh_token_preserves_user_data(self) -> None:
        """Test that refreshed token has same user data."""
        # Arrange
        old_token = create_access_token(user_id=42, username="john")

        # Act
        new_token = refresh_token(old_token)
        new_payload = verify_token(new_token)

        # Assert
        assert new_payload["user_id"] == 42
        assert new_payload["sub"] == "john"

    def test_refresh_token_works_with_expired_token(self) -> None:
        """Test that expired tokens can be refreshed."""
        # Arrange
        expired_token = create_access_token(
            user_id=1,
            username="test",
            expires_delta=timedelta(seconds=-1)
        )

        # Act
        new_token = refresh_token(expired_token)

        # Assert
        # New token should be valid
        payload = verify_token(new_token)
        assert payload["user_id"] == 1

    def test_refresh_token_updates_expiration(self) -> None:
        """Test that refreshed token has new expiration."""
        # Arrange
        old_token = create_access_token(user_id=1, username="test")
        old_payload = decode_token_without_verification(old_token)

        # Wait to ensure different timestamps
        time.sleep(1)

        # Act
        new_token = refresh_token(old_token)
        new_payload = decode_token_without_verification(new_token)

        # Assert
        assert new_payload["iat"] > old_payload["iat"]
        assert new_payload["exp"] > old_payload["exp"]

    def test_refresh_token_custom_expiration(self) -> None:
        """Test refreshing with custom expiration."""
        # Arrange
        old_token = create_access_token(user_id=1, username="test")
        custom_exp = timedelta(hours=48)

        # Act
        new_token = refresh_token(old_token, expires_delta=custom_exp)
        new_payload = decode_token_without_verification(new_token)

        # Assert
        exp_diff = new_payload["exp"] - new_payload["iat"]
        assert exp_diff == 48 * 3600  # 48 hours in seconds

    def test_refresh_token_invalid_token(self) -> None:
        """Test that invalid token cannot be refreshed."""
        # Act & Assert
        with pytest.raises(TokenInvalidError):
            refresh_token("invalid.jwt.token")


class TestDecodeWithoutVerification:
    """Test suite for unverified token decoding."""

    def test_decode_without_verification_returns_payload(self) -> None:
        """Test that decode returns payload without verification."""
        # Arrange
        token = create_access_token(user_id=1, username="test")

        # Act
        payload = decode_token_without_verification(token)

        # Assert
        assert payload["user_id"] == 1
        assert payload["sub"] == "test"

    def test_decode_without_verification_expired_token(self) -> None:
        """Test that expired tokens can still be decoded."""
        # Arrange
        expired_token = create_access_token(
            user_id=1,
            username="test",
            expires_delta=timedelta(seconds=-1)
        )

        # Act - Should NOT raise exception
        payload = decode_token_without_verification(expired_token)

        # Assert
        assert payload["user_id"] == 1
