"""
Authentication API routes.

This module provides endpoints for user registration, login, and profile access.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from datetime import timedelta

from app.config import get_settings
from app.database import get_db
from app.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.middleware.auth import get_current_user
from app.models import User
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse
from app.services import user_service
from app.utils.security import create_access_token
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(  # type: ignore[misc]
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_data: UserCreate, db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Register a new user.

    Parameters
    ----------
    user_data : UserCreate
        User registration data
    db : Session
        Database session

    Returns
    -------
    TokenResponse
        JWT token and user information

    Raises
    ------
    HTTPException
        409 Conflict if user already exists
        400 Bad Request if validation fails
    """
    try:
        # Create user
        user = user_service.create_user(db, user_data)

        # Generate JWT token
        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        access_token = create_access_token(
            token_data, expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
        )

        # Return token and user data
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",  # nosec B106
            expires_in=settings.jwt_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(user),
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)


@router.post("/login", response_model=TokenResponse)  # type: ignore[misc]
def login_user(
    credentials: LoginRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Login user and return JWT token.

    Parameters
    ----------
    credentials : LoginRequest
        User login credentials
    db : Session
        Database session

    Returns
    -------
    TokenResponse
        JWT token and user information

    Raises
    ------
    HTTPException
        401 Unauthorized if credentials are invalid
    """
    try:
        # Authenticate user
        user = user_service.authenticate_user(
            db, credentials.email, credentials.password
        )

        # Generate JWT token
        token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
        access_token = create_access_token(
            token_data, expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
        )

        # Return token and user data
        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",  # nosec B106
            expires_in=settings.jwt_expire_minutes * 60,  # Convert to seconds
            user=UserResponse.model_validate(user),
        )

    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message)


@router.get("/me", response_model=UserResponse)  # type: ignore[misc]
def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current authenticated user's information.

    Parameters
    ----------
    current_user : User
        Current authenticated user

    Returns
    -------
    UserResponse
        Current user information
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=TokenResponse)  # type: ignore[misc]
def refresh_token(current_user: User = Depends(get_current_user)) -> TokenResponse:
    """
    Refresh access token for authenticated user.

    Parameters
    ----------
    current_user : User
        Current authenticated user

    Returns
    -------
    TokenResponse
        New JWT token and user information
    """
    # Generate new JWT token
    token_data = {
        "sub": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
    }
    access_token = create_access_token(
        token_data, expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )

    # Return new token and user data
    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",  # nosec B106
        expires_in=settings.jwt_expire_minutes * 60,  # Convert to seconds
        user=UserResponse.model_validate(current_user),
    )
