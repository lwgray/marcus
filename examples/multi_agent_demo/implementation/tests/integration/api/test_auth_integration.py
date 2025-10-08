"""
Integration tests for authentication endpoints.

Tests end-to-end authentication flows including:
- User registration with database persistence
- User login with JWT token generation
- Token refresh with database token management
- Protected endpoint access with JWT verification
"""

import pytest
from app.schemas.auth import UserLogin, UserRegister
from app.services.auth_service import AuthService, UserAlreadyExistsError, AuthenticationError
from app.security.jwt_handler import verify_token, TokenExpiredError
from app.security.password import verify_password
from datetime import timedelta


class TestUserRegistrationIntegration:
    """Integration tests for user registration flow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_register_user_creates_database_record(
        self,
        db_session,
        sample_user_data
    ):
        """
        Test that user registration creates a valid database record.

        Verifies:
        - User record is created in database
        - Password is properly hashed
        - Tokens are generated
        - User can be queried from database
        """
        # Arrange
        auth_service = AuthService(db_session)
        user_data = UserRegister(**sample_user_data)

        # Act
        user, access_token, refresh_token = await auth_service.register_user(
            user_data,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        # Assert - User was created
        assert user.id is not None
        assert user.email == sample_user_data["email"]
        assert user.username == sample_user_data["username"]
        assert user.is_active is True
        assert user.is_verified is False

        # Assert - Password was hashed
        assert user.password_hash != sample_user_data["password"]
        assert verify_password(sample_user_data["password"], user.password_hash)

        # Assert - Tokens were generated
        assert access_token is not None
        assert refresh_token is not None

        # Assert - Access token contains user data
        payload = verify_token(access_token)
        assert payload["user_id"] == user.id
        assert payload["sub"] == user.username

        # Assert - User can be queried
        queried_user = await auth_service.get_user_by_id(user.id)
        assert queried_user is not None
        assert queried_user.email == user.email

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_register_duplicate_email_fails(
        self,
        db_session,
        sample_user_data
    ):
        """
        Test that duplicate email registration fails.

        Verifies database constraint prevents duplicate emails.
        """
        # Arrange
        auth_service = AuthService(db_session)
        user_data = UserRegister(**sample_user_data)

        # Act - Register first user
        await auth_service.register_user(user_data)

        # Act & Assert - Try to register with same email
        with pytest.raises(UserAlreadyExistsError, match="Email already registered"):
            await auth_service.register_user(user_data)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_register_duplicate_username_fails(
        self,
        db_session,
        sample_user_data
    ):
        """
        Test that duplicate username registration fails.

        Verifies database constraint prevents duplicate usernames.
        """
        # Arrange
        auth_service = AuthService(db_session)
        user_data1 = UserRegister(**sample_user_data)

        # Register first user
        await auth_service.register_user(user_data1)

        # Create second user with same username, different email
        user_data2_dict = sample_user_data.copy()
        user_data2_dict["email"] = "different@example.com"
        user_data2 = UserRegister(**user_data2_dict)

        # Act & Assert - Try to register with same username
        with pytest.raises(UserAlreadyExistsError, match="Username already taken"):
            await auth_service.register_user(user_data2)


class TestUserLoginIntegration:
    """Integration tests for user login flow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_with_valid_credentials(
        self,
        db_session,
        sample_user_data,
        sample_login_data
    ):
        """
        Test successful login with valid credentials.

        Verifies:
        - Login succeeds with correct credentials
        - Tokens are generated
        - Last login timestamp is updated
        """
        # Arrange - Register user first
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        registered_user, _, _ = await auth_service.register_user(user_reg_data)

        login_data = UserLogin(**sample_login_data)

        # Act - Login
        user, access_token, refresh_token = await auth_service.login_user(
            login_data,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        # Assert - Login successful
        assert user.id == registered_user.id
        assert user.email == sample_login_data["email"]
        assert access_token is not None
        assert refresh_token is not None

        # Assert - Last login was updated
        assert user.last_login is not None

        # Assert - Token contains correct user data
        payload = verify_token(access_token)
        assert payload["user_id"] == user.id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_with_invalid_email(
        self,
        db_session,
        sample_login_data
    ):
        """Test login fails with non-existent email."""
        # Arrange
        auth_service = AuthService(db_session)
        login_data = UserLogin(**sample_login_data)

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.login_user(login_data)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_with_incorrect_password(
        self,
        db_session,
        sample_user_data,
        sample_login_data
    ):
        """Test login fails with incorrect password."""
        # Arrange - Register user
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        await auth_service.register_user(user_reg_data)

        # Create login with wrong password
        wrong_login_data = sample_login_data.copy()
        wrong_login_data["password"] = "WrongPassword123!"  # pragma: allowlist secret
        login_data = UserLogin(**wrong_login_data)

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.login_user(login_data)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_login_inactive_user_fails(
        self,
        db_session,
        sample_user_data,
        sample_login_data
    ):
        """Test login fails for deactivated user."""
        # Arrange - Register and deactivate user
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        user, _, _ = await auth_service.register_user(user_reg_data)

        # Deactivate user
        user.is_active = False
        await db_session.commit()

        login_data = UserLogin(**sample_login_data)

        # Act & Assert
        with pytest.raises(AuthenticationError, match="Account is deactivated"):
            await auth_service.login_user(login_data)


class TestTokenRefreshIntegration:
    """Integration tests for token refresh flow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_refresh_token_generates_new_access_token(
        self,
        db_session,
        sample_user_data
    ):
        """
        Test that refresh token generates a new access token.

        Verifies:
        - Refresh token is stored in database
        - New access token is generated
        - New access token is valid
        """
        # Arrange - Register user
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        user, _, refresh_token = await auth_service.register_user(user_reg_data)

        # Act - Refresh access token
        new_access_token, refreshed_user = await auth_service.refresh_access_token(
            refresh_token
        )

        # Assert - New token was generated
        assert new_access_token is not None

        # Assert - New token is valid
        payload = verify_token(new_access_token)
        assert payload["user_id"] == user.id
        assert payload["sub"] == user.username

        # Assert - User data matches
        assert refreshed_user.id == user.id

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_revoked_refresh_token_fails(
        self,
        db_session,
        sample_user_data
    ):
        """Test that revoked refresh tokens cannot be used."""
        # Arrange - Register user
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        user, _, refresh_token = await auth_service.register_user(user_reg_data)

        # Revoke the token
        await auth_service.revoke_refresh_token(refresh_token)

        # Act & Assert - Try to use revoked token
        from app.services.auth_service import TokenError
        with pytest.raises(TokenError, match="revoked"):
            await auth_service.refresh_access_token(refresh_token)


class TestTokenRevocationIntegration:
    """Integration tests for token revocation (logout) flow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_logout_revokes_refresh_token(
        self,
        db_session,
        sample_user_data
    ):
        """
        Test that logout properly revokes refresh token.

        Verifies:
        - Token is marked as revoked in database
        - Revoked token cannot be used for refresh
        """
        # Arrange - Register user
        auth_service = AuthService(db_session)
        user_reg_data = UserRegister(**sample_user_data)
        user, _, refresh_token = await auth_service.register_user(user_reg_data)

        # Act - Logout (revoke token)
        await auth_service.revoke_refresh_token(refresh_token)

        # Assert - Token is revoked and cannot be used
        from app.services.auth_service import TokenError
        with pytest.raises(TokenError, match="revoked"):
            await auth_service.refresh_access_token(refresh_token)


class TestEndToEndAuthFlow:
    """End-to-end authentication workflow tests."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_authentication_workflow(
        self,
        db_session,
        sample_user_data,
        sample_login_data
    ):
        """
        Test complete authentication workflow: register → login → refresh → logout.

        Verifies entire authentication lifecycle works correctly.
        """
        # Arrange
        auth_service = AuthService(db_session)

        # Step 1: Register
        user_reg_data = UserRegister(**sample_user_data)
        user, reg_access_token, reg_refresh_token = await auth_service.register_user(
            user_reg_data
        )
        assert user.id is not None
        assert reg_access_token is not None

        # Step 2: Login
        login_data = UserLogin(**sample_login_data)
        login_user, login_access_token, login_refresh_token = await auth_service.login_user(
            login_data
        )
        assert login_user.id == user.id
        assert login_access_token is not None

        # Step 3: Refresh access token
        new_access_token, _ = await auth_service.refresh_access_token(
            login_refresh_token
        )
        assert new_access_token is not None
        assert new_access_token != login_access_token

        # Step 4: Logout (revoke refresh token)
        await auth_service.revoke_refresh_token(login_refresh_token)

        # Assert - Revoked token cannot be used
        from app.services.auth_service import TokenError
        with pytest.raises(TokenError, match="revoked"):
            await auth_service.refresh_access_token(login_refresh_token)
