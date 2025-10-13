"""
JWT token generation and validation for authentication.

Uses PyJWT with HS256 algorithm for token signing and validation.
Supports access tokens with configurable expiration times.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(hours=24)  # Default: 24 hours


class TokenError(Exception):
    """Base exception for token-related errors."""

    pass


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""

    pass


class TokenInvalidError(TokenError):
    """Raised when a token is invalid or malformed."""

    pass


def create_access_token(
    user_id: int,
    username: str,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a JWT access token for a user.

    Parameters
    ----------
    user_id : int
        Unique user identifier
    username : str
        Username for the token subject
    expires_delta : timedelta, optional
        Custom expiration time (default: 24 hours from JWT_EXPIRATION_DELTA)
    additional_claims : dict, optional
        Additional claims to include in the token payload

    Returns
    -------
    str
        Encoded JWT token

    Examples
    --------
    >>> token = create_access_token(user_id=1, username="john")
    >>> len(token) > 100
    True

    >>> # Custom expiration
    >>> from datetime import timedelta
    >>> short_token = create_access_token(
    ...     user_id=1,
    ...     username="john",
    ...     expires_delta=timedelta(minutes=15)
    ... )

    Notes
    -----
    Token payload includes:
    - sub: Subject (username)
    - user_id: User identifier
    - iat: Issued at timestamp
    - exp: Expiration timestamp
    - Additional custom claims if provided
    """
    if expires_delta is None:
        expires_delta = JWT_EXPIRATION_DELTA

    # Calculate expiration time (UTC)
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    # Build token payload
    payload = {
        "sub": username,  # Subject
        "user_id": user_id,
        "iat": now,  # Issued at
        "exp": expire,  # Expiration
    }

    # Add any additional claims
    if additional_claims:
        payload.update(additional_claims)

    # Encode and return token
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Parameters
    ----------
    token : str
        JWT token to verify

    Returns
    -------
    dict[str, Any]
        Decoded token payload containing user information

    Raises
    ------
    TokenExpiredError
        If the token has expired
    TokenInvalidError
        If the token is invalid or malformed

    Examples
    --------
    >>> token = create_access_token(user_id=1, username="john")
    >>> payload = verify_token(token)
    >>> payload['user_id']
    1
    >>> payload['sub']
    'john'

    Notes
    -----
    - Validates signature using JWT_SECRET_KEY
    - Checks expiration time automatically
    - Returns full payload including standard and custom claims
    """
    try:
        # Decode and verify token
        decoded: Dict[str, Any] = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True},  # Verify expiration
        )
        return decoded

    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")

    except InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid token: {str(e)}")


def get_current_user(token: str) -> Dict[str, Any]:
    """
    Extract user information from a JWT token.

    Parameters
    ----------
    token : str
        JWT access token

    Returns
    -------
    dict[str, Any]
        User information extracted from token:
        - user_id: User identifier
        - username: Username from subject claim
        - Additional claims if present

    Raises
    ------
    TokenExpiredError
        If the token has expired
    TokenInvalidError
        If the token is invalid or missing required claims

    Examples
    --------
    >>> token = create_access_token(user_id=1, username="john")
    >>> user = get_current_user(token)
    >>> user['user_id']
    1
    >>> user['username']
    'john'

    Notes
    -----
    This is a convenience function for extracting user info.
    It verifies the token and returns user-specific claims.
    """
    # Verify token first
    payload = verify_token(token)

    # Extract user information
    if "user_id" not in payload or "sub" not in payload:
        raise TokenInvalidError("Token missing required user claims")

    return {
        "user_id": payload["user_id"],
        "username": payload["sub"],
        **{
            k: v
            for k, v in payload.items()
            if k not in ["user_id", "sub", "iat", "exp"]
        },
    }


def refresh_token(old_token: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new token from an existing token (token refresh).

    Parameters
    ----------
    old_token : str
        Existing JWT token (may be expired)
    expires_delta : timedelta, optional
        Expiration time for new token

    Returns
    -------
    str
        New JWT token with updated expiration

    Raises
    ------
    TokenInvalidError
        If the old token is invalid (excluding expiration)

    Examples
    --------
    >>> old_token = create_access_token(user_id=1, username="john")
    >>> new_token = refresh_token(old_token)
    >>> new_token != old_token
    True

    Notes
    -----
    - Allows refreshing expired tokens (verify_exp=False)
    - Creates new token with same user_id and username
    - Resets issued_at and expiration times
    - Does not preserve additional custom claims
    """
    try:
        # Decode without verifying expiration
        payload = jwt.decode(
            old_token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": False},  # Don't verify expiration
        )

        # Create new token with same user info
        return create_access_token(
            user_id=payload["user_id"],
            username=payload["sub"],
            expires_delta=expires_delta,
        )

    except InvalidTokenError as e:
        raise TokenInvalidError(f"Cannot refresh invalid token: {str(e)}")


def decode_token_without_verification(token: str) -> Dict[str, Any]:
    """
    Decode a token without verification (for debugging only).

    Parameters
    ----------
    token : str
        JWT token to decode

    Returns
    -------
    dict[str, Any]
        Decoded token payload (unverified)

    Warnings
    --------
    This function does NOT verify the token signature or expiration.
    Use only for debugging or logging purposes, never for authentication.

    Examples
    --------
    >>> token = create_access_token(user_id=1, username="john")
    >>> payload = decode_token_without_verification(token)
    >>> 'user_id' in payload
    True
    """
    decoded: Dict[str, Any] = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    return decoded
