"""
Security utilities for authentication.

This module provides functions for password hashing and JWT token management.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from datetime import datetime, timedelta
from typing import Any

from app.config import get_settings
from jose import JWTError, jwt
from passlib.context import CryptContext

settings = get_settings()

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt with 12 rounds.

    Parameters
    ----------
    password : str
        Plain text password

    Returns
    -------
    str
        Bcrypt hashed password

    Examples
    --------
    >>> hashed = hash_password("SecurePassword123")
    >>> verify_password("SecurePassword123", hashed)
    True
    """
    return str(pwd_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Parameters
    ----------
    plain_password : str
        Plain text password to verify
    hashed_password : str
        Bcrypt hashed password

    Returns
    -------
    bool
        True if password matches hash, False otherwise

    Examples
    --------
    >>> hashed = hash_password("mypassword")
    >>> verify_password("mypassword", hashed)
    True
    >>> verify_password("wrongpassword", hashed)
    False
    """
    return bool(pwd_context.verify(plain_password, hashed_password))


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """
    Create a JWT access token.

    Parameters
    ----------
    data : dict[str, Any]
        Data to encode in the token (user_id, email, role)
    expires_delta : timedelta | None
        Token expiration time (default: from settings)

    Returns
    -------
    str
        Encoded JWT token

    Notes
    -----
    Token includes 'sub' (user_id), 'email', 'role', 'iat' (issued at),
    and 'exp' (expiration) claims.

    Examples
    --------
    >>> from datetime import timedelta
    >>> token_data = {"sub": "1", "email": "user@example.com", "role": "member"}
    >>> token = create_access_token(token_data, expires_delta=timedelta(hours=1))
    >>> isinstance(token, str)
    True
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)

    # Add standard JWT claims
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )

    return str(encoded_jwt)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and verify a JWT access token.

    Parameters
    ----------
    token : str
        JWT token to decode

    Returns
    -------
    dict[str, Any] | None
        Decoded token payload if valid, None if invalid or expired

    Notes
    -----
    Verifies token signature and expiration. Returns None for any
    validation errors.

    Examples
    --------
    >>> token_data = {"sub": "1", "email": "user@example.com", "role": "member"}
    >>> token = create_access_token(token_data)
    >>> payload = decode_access_token(token)
    >>> payload["sub"]
    '1'
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None
