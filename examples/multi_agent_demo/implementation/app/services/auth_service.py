"""
Authentication service for user registration, login, and token management.

Handles business logic for JWT-based authentication including:
- User registration with password hashing
- User login with credential validation
- Access and refresh token generation
- Token refresh and revocation
- User session management
"""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import RefreshToken, User
from app.schemas.auth import UserRegister, UserLogin
from app.security.jwt_handler import create_access_token
from app.security.password import hash_password, verify_password


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class UserAlreadyExistsError(Exception):
    """Raised when attempting to register duplicate user."""
    pass


class TokenError(Exception):
    """Raised when token operations fail."""
    pass


class AuthService:
    """
    Authentication service for user and token management.

    Provides methods for user registration, login, token operations,
    and session management with comprehensive error handling.
    """

    # Token expiration times (from design spec)
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    def __init__(self, db: AsyncSession):
        """
        Initialize authentication service.

        Parameters
        ----------
        db : AsyncSession
            Database session for async operations
        """
        self.db = db

    async def register_user(
        self,
        user_data: UserRegister,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """
        Register a new user and generate authentication tokens.

        Parameters
        ----------
        user_data : UserRegister
            User registration data (email, username, password)
        ip_address : str, optional
            IP address of registration request
        user_agent : str, optional
            User agent string from request

        Returns
        -------
        tuple[User, str, str]
            (user object, access_token, refresh_token)

        Raises
        ------
        UserAlreadyExistsError
            If email or username already exists
        """
        # Check if user already exists
        existing_user = await self._get_user_by_email_or_username(
            user_data.email, user_data.username
        )
        if existing_user:
            if existing_user.email == user_data.email:
                raise UserAlreadyExistsError("Email already registered")
            else:
                raise UserAlreadyExistsError("Username already taken")

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
            is_active=True,
            is_verified=False,  # Email verification required
            last_login=datetime.now(timezone.utc),
        )

        self.db.add(user)
        await self.db.flush()  # Get user ID without committing

        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token = await self._create_refresh_token(
            user, ip_address, user_agent
        )

        await self.db.commit()
        await self.db.refresh(user)

        return user, access_token, refresh_token

    async def login_user(
        self,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and generate tokens.

        Parameters
        ----------
        login_data : UserLogin
            Login credentials (email, password)
        ip_address : str, optional
            IP address of login request
        user_agent : str, optional
            User agent string from request

        Returns
        -------
        tuple[User, str, str]
            (user object, access_token, refresh_token)

        Raises
        ------
        AuthenticationError
            If credentials are invalid or account is inactive
        """
        # Get user by email
        user = await self._get_user_by_email(login_data.email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(login_data.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        # Check if account is active
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Update last login
        user.last_login = datetime.now(timezone.utc)

        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token = await self._create_refresh_token(
            user, ip_address, user_agent
        )

        await self.db.commit()
        await self.db.refresh(user)

        return user, access_token, refresh_token

    async def refresh_access_token(
        self, refresh_token_string: str
    ) -> Tuple[str, User]:
        """
        Generate new access token from refresh token.

        Parameters
        ----------
        refresh_token_string : str
            JWT refresh token string

        Returns
        -------
        tuple[str, User]
            (new_access_token, user object)

        Raises
        ------
        TokenError
            If refresh token is invalid, expired, or revoked
        """
        # Hash the refresh token to find it in database
        token_hash = self._hash_token(refresh_token_string)

        # Query refresh token with user
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .options(selectinload(RefreshToken.user))
        )
        result = await self.db.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            raise TokenError("Invalid refresh token")

        if refresh_token.is_revoked:
            raise TokenError("Refresh token has been revoked")

        if refresh_token.expires_at <= datetime.now(timezone.utc):
            raise TokenError("Refresh token has expired")

        # Get user
        user = refresh_token.user
        if not user.is_active:
            raise TokenError("User account is deactivated")

        # Generate new access token
        access_token = self._create_access_token(user)

        return access_token, user

    async def revoke_refresh_token(self, refresh_token_string: str) -> None:
        """
        Revoke a refresh token (logout).

        Parameters
        ----------
        refresh_token_string : str
            JWT refresh token string to revoke

        Raises
        ------
        TokenError
            If refresh token not found
        """
        token_hash = self._hash_token(refresh_token_string)

        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        refresh_token = result.scalar_one_or_none()

        if not refresh_token:
            raise TokenError("Invalid refresh token")

        # Revoke token
        refresh_token.revoke()
        await self.db.commit()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID.

        Parameters
        ----------
        user_id : int
            User identifier

        Returns
        -------
        User or None
            User object if found, None otherwise
        """
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired refresh tokens from database.

        Should be run periodically as a maintenance task.

        Returns
        -------
        int
            Number of tokens cleaned up
        """
        stmt = select(RefreshToken).where(
            RefreshToken.expires_at <= datetime.now(timezone.utc)
        )
        result = await self.db.execute(stmt)
        expired_tokens = result.scalars().all()

        for token in expired_tokens:
            await self.db.delete(token)

        await self.db.commit()
        return len(expired_tokens)

    # Private helper methods

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_user_by_email_or_username(
        self, email: str, username: str
    ) -> Optional[User]:
        """Get user by email or username."""
        stmt = select(User).where(
            (User.email == email) | (User.username == username)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def _create_access_token(self, user: User) -> str:
        """
        Create JWT access token for user.

        Parameters
        ----------
        user : User
            User object

        Returns
        -------
        str
            JWT access token
        """
        expires_delta = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

        # Get user roles (if they exist)
        roles = [role.role.value for role in user.roles] if hasattr(user, 'roles') and user.roles else ["user"]

        additional_claims = {
            "email": user.email,
            "roles": roles,
            "type": "access",
        }

        return create_access_token(
            user_id=user.id,
            username=user.username,
            expires_delta=expires_delta,
            additional_claims=additional_claims,
        )

    async def _create_refresh_token(
        self,
        user: User,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> str:
        """
        Create and store refresh token.

        Parameters
        ----------
        user : User
            User object
        ip_address : str, optional
            IP address where token was issued
        user_agent : str, optional
            User agent string

        Returns
        -------
        str
            Refresh token string
        """
        # Generate refresh token (using timestamp + user ID for uniqueness)
        token_data = f"{user.id}:{datetime.now(timezone.utc).isoformat()}"
        refresh_token_string = hashlib.sha256(token_data.encode()).hexdigest()

        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.REFRESH_TOKEN_EXPIRE_DAYS
        )

        # Hash token for storage
        token_hash = self._hash_token(refresh_token_string)

        # Create refresh token record
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.add(refresh_token)

        return refresh_token_string

    def _hash_token(self, token: str) -> str:
        """
        Hash token for secure storage.

        Parameters
        ----------
        token : str
            Token string to hash

        Returns
        -------
        str
            SHA-256 hash of token
        """
        return hashlib.sha256(token.encode()).hexdigest()
