"""
Authentication middleware for FastAPI.

This module provides dependency functions for extracting and validating
JWT tokens and loading authenticated users.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from app.database import get_db
from app.models import User
from app.utils.security import decode_access_token
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

# HTTP Bearer token scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the currently authenticated user from JWT token.

    Parameters
    ----------
    credentials : HTTPAuthorizationCredentials
        HTTP Bearer credentials containing JWT token
    db : Session
        Database session

    Returns
    -------
    User
        Authenticated user model

    Raises
    ------
    HTTPException
        401 Unauthorized if token is invalid, expired, or user not found
        401 Unauthorized if user account is inactive

    Notes
    -----
    This dependency extracts the JWT token from the Authorization header,
    verifies it, and loads the user from the database.

    Examples
    --------
    >>> from fastapi import Depends
    >>> @app.get("/protected")
    >>> def protected_route(current_user: User = Depends(get_current_user)):
    >>>     return {"user_id": current_user.id}
    """
    # Extract token
    token = credentials.credentials

    # Decode and verify token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user ID from token
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load user from database
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get current active user (convenience wrapper).

    Parameters
    ----------
    current_user : User
        Current authenticated user

    Returns
    -------
    User
        Active user model

    Notes
    -----
    This is a convenience dependency that explicitly ensures the user
    is active (already checked in get_current_user).
    """
    return current_user
