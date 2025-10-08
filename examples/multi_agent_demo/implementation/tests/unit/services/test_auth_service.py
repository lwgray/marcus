"""
Unit tests for authentication service.

Tests user registration, login, token operations, and session management.
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

from app.models import RefreshToken, User
from app.schemas.auth import UserLogin, UserRegister
from app.services.auth_service import (
    AuthenticationError,
    AuthService,
    TokenError,
    UserAlreadyExistsError,
)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.add = Mock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def auth_service(mock_db):
    """Create AuthService instance with mock database."""
    return AuthService(mock_db)


@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    user = User(
        id=1,
        email="test@example.com",
        username="testuser",
        password_hash="$2b$12$hashed_password",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    user.roles = []
    user.refresh_tokens = []
    return user


class TestUserRegistration:
    """Test suite for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, auth_service, mock_db):
        """Test successful user registration."""
        # Arrange
        user_data = UserRegister(
            email="new@example.com",
            username="newuser",
            password="SecureP@ssw0rd123"
        )

        # Mock no existing user
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Act
        with patch('app.services.auth_service.hash_password') as mock_hash:
            mock_hash.return_value = "$2b$12$hashed"
            user, access_token, refresh_token = await auth_service.register_user(
                user_data, "127.0.0.1", "TestAgent"
            )

        # Assert
        assert mock_db.add.called
        assert mock_db.flush.called
        assert mock_db.commit.called
        assert access_token is not None
        assert refresh_token is not None

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, auth_service, mock_db, sample_user):
        """Test registration with existing email."""
        # Arrange
        user_data = UserRegister(
            email="test@example.com",
            username="different",
            password="SecureP@ssw0rd123"
        )

        # Mock existing user with same email
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_user)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError, match="Email already registered"):
            await auth_service.register_user(user_data)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, auth_service, mock_db):
        """Test registration with existing username."""
        # Arrange
        user_data = UserRegister(
            email="new@example.com",
            username="testuser",
            password="SecureP@ssw0rd123"
        )

        # Mock existing user with different email but same username
        existing_user = User(
            id=2,
            email="different@example.com",
            username="testuser",
            password_hash="hash"
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_user)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(UserAlreadyExistsError, match="Username already taken"):
            await auth_service.register_user(user_data)


class TestUserLogin:
    """Test suite for user login."""

    @pytest.mark.asyncio
    async def test_login_success(self, auth_service, mock_db, sample_user):
        """Test successful login."""
        # Arrange
        login_data = UserLogin(
            email="test@example.com",
            password="SecureP@ssw0rd123"
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_user)
        mock_db.execute.return_value = mock_result

        # Act
        with patch('app.services.auth_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            user, access_token, refresh_token = await auth_service.login_user(
                login_data, "127.0.0.1", "TestAgent"
            )

        # Assert
        assert user == sample_user
        assert access_token is not None
        assert refresh_token is not None
        assert mock_db.commit.called
        assert sample_user.last_login is not None

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, auth_service, mock_db):
        """Test login with non-existent email."""
        # Arrange
        login_data = UserLogin(
            email="nonexistent@example.com",
            password="password"
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.login_user(login_data)

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, auth_service, mock_db, sample_user):
        """Test login with incorrect password."""
        # Arrange
        login_data = UserLogin(
            email="test@example.com",
            password="WrongPassword123!"
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_user)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch('app.services.auth_service.verify_password') as mock_verify:
            mock_verify.return_value = False
            with pytest.raises(AuthenticationError, match="Invalid email or password"):
                await auth_service.login_user(login_data)

    @pytest.mark.asyncio
    async def test_login_inactive_account(self, auth_service, mock_db, sample_user):
        """Test login with deactivated account."""
        # Arrange
        login_data = UserLogin(
            email="test@example.com",
            password="SecureP@ssw0rd123"
        )

        sample_user.is_active = False

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_user)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch('app.services.auth_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            with pytest.raises(AuthenticationError, match="Account is deactivated"):
                await auth_service.login_user(login_data)


class TestTokenRefresh:
    """Test suite for token refresh operations."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, auth_service, mock_db, sample_user):
        """Test successful token refresh."""
        # Arrange
        refresh_token_string = "valid_refresh_token"

        # Create mock refresh token
        refresh_token = RefreshToken(
            id=1,
            user_id=sample_user.id,
            token_hash="hashed_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        refresh_token.user = sample_user

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=refresh_token)
        mock_db.execute.return_value = mock_result

        # Act
        with patch.object(auth_service, '_hash_token') as mock_hash:
            mock_hash.return_value = "hashed_token"
            new_access_token, user = await auth_service.refresh_access_token(
                refresh_token_string
            )

        # Assert
        assert new_access_token is not None
        assert user == sample_user

    @pytest.mark.asyncio
    async def test_refresh_token_not_found(self, auth_service, mock_db):
        """Test refresh with invalid token."""
        # Arrange
        refresh_token_string = "invalid_token"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch.object(auth_service, '_hash_token'):
            with pytest.raises(TokenError, match="Invalid refresh token"):
                await auth_service.refresh_access_token(refresh_token_string)

    @pytest.mark.asyncio
    async def test_refresh_token_revoked(self, auth_service, mock_db, sample_user):
        """Test refresh with revoked token."""
        # Arrange
        refresh_token_string = "revoked_token"

        refresh_token = RefreshToken(
            id=1,
            user_id=sample_user.id,
            token_hash="hashed_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=True,
        )
        refresh_token.user = sample_user

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=refresh_token)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch.object(auth_service, '_hash_token') as mock_hash:
            mock_hash.return_value = "hashed_token"
            with pytest.raises(TokenError, match="Refresh token has been revoked"):
                await auth_service.refresh_access_token(refresh_token_string)

    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, auth_service, mock_db, sample_user):
        """Test refresh with expired token."""
        # Arrange
        refresh_token_string = "expired_token"

        refresh_token = RefreshToken(
            id=1,
            user_id=sample_user.id,
            token_hash="hashed_token",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
            is_revoked=False,
        )
        refresh_token.user = sample_user

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=refresh_token)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch.object(auth_service, '_hash_token') as mock_hash:
            mock_hash.return_value = "hashed_token"
            with pytest.raises(TokenError, match="Refresh token has expired"):
                await auth_service.refresh_access_token(refresh_token_string)

    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user(self, auth_service, mock_db, sample_user):
        """Test refresh with inactive user account."""
        # Arrange
        refresh_token_string = "valid_token"

        sample_user.is_active = False

        refresh_token = RefreshToken(
            id=1,
            user_id=sample_user.id,
            token_hash="hashed_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )
        refresh_token.user = sample_user

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=refresh_token)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch.object(auth_service, '_hash_token') as mock_hash:
            mock_hash.return_value = "hashed_token"
            with pytest.raises(TokenError, match="User account is deactivated"):
                await auth_service.refresh_access_token(refresh_token_string)


class TestTokenRevocation:
    """Test suite for token revocation (logout)."""

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, auth_service, mock_db):
        """Test successful token revocation."""
        # Arrange
        refresh_token_string = "valid_token"

        refresh_token = RefreshToken(
            id=1,
            user_id=1,
            token_hash="hashed_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_revoked=False,
        )

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=refresh_token)
        mock_db.execute.return_value = mock_result

        # Act
        with patch.object(auth_service, '_hash_token') as mock_hash:
            mock_hash.return_value = "hashed_token"
            await auth_service.revoke_refresh_token(refresh_token_string)

        # Assert
        assert refresh_token.is_revoked is True
        assert refresh_token.revoked_at is not None
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_revoke_token_not_found(self, auth_service, mock_db):
        """Test revoke with invalid token."""
        # Arrange
        refresh_token_string = "invalid_token"

        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Act & Assert
        with patch.object(auth_service, '_hash_token'):
            with pytest.raises(TokenError, match="Invalid refresh token"):
                await auth_service.revoke_refresh_token(refresh_token_string)


class TestHelperMethods:
    """Test suite for helper methods."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, auth_service, mock_db, sample_user):
        """Test get user by ID when user exists."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=sample_user)
        mock_db.execute.return_value = mock_result

        # Act
        user = await auth_service.get_user_by_id(1)

        # Assert
        assert user == sample_user

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, auth_service, mock_db):
        """Test get user by ID when user doesn't exist."""
        # Arrange
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result

        # Act
        user = await auth_service.get_user_by_id(999)

        # Assert
        assert user is None

    def test_hash_token(self, auth_service):
        """Test token hashing produces consistent results."""
        # Arrange
        token = "test_token_123"

        # Act
        hash1 = auth_service._hash_token(token)
        hash2 = auth_service._hash_token(token)

        # Assert
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 produces 64 hex characters

    def test_create_access_token(self, auth_service, sample_user):
        """Test access token creation."""
        # Act
        token = auth_service._create_access_token(sample_user)

        # Assert
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are lengthy


class TestCleanupExpiredTokens:
    """Test suite for token cleanup operations."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, auth_service, mock_db):
        """Test cleanup removes expired tokens."""
        # Arrange
        expired_token1 = RefreshToken(
            id=1,
            user_id=1,
            token_hash="hash1",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        expired_token2 = RefreshToken(
            id=2,
            user_id=1,
            token_hash="hash2",
            expires_at=datetime.now(timezone.utc) - timedelta(days=2)
        )

        mock_result = Mock()
        mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[expired_token1, expired_token2])))
        mock_db.execute.return_value = mock_result
        mock_db.delete = AsyncMock()

        # Act
        count = await auth_service.cleanup_expired_tokens()

        # Assert
        assert count == 2
        assert mock_db.delete.call_count == 2
        assert mock_db.commit.called
