"""
Authentication API routes for user registration, login, and token management.

Implements JWT-based authentication endpoints per auth-api-spec.yaml:
- POST /auth/register: Register new user
- POST /auth/login: Authenticate user
- POST /auth/refresh: Refresh access token
- POST /auth/logout: Revoke refresh token
- GET /auth/me: Get current user profile
"""

from datetime import timedelta
from typing import Annotated

from app.schemas.auth import (
    ErrorResponse,
    LogoutRequest,
    SuccessResponse,
    TokenData,
    TokenRefresh,
    TokenRefreshResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.security.jwt_handler import TokenExpiredError, TokenInvalidError, verify_token
from app.services.auth_service import (
    AuthenticationError,
    AuthService,
    TokenError,
    UserAlreadyExistsError,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

# Router configuration
router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Dependency to get database session
async def get_db() -> AsyncSession:
    """
    Dependency to provide database session.

    This is a placeholder - actual implementation will be provided
    by the database configuration module.

    Yields
    ------
    AsyncSession
        Database session for async operations
    """
    # TODO: Import from app.database once created
    raise NotImplementedError("Database session dependency not configured")


# Dependency to get current user from JWT token
async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract and validate current user from Authorization header.

    Parameters
    ----------
    authorization : str
        Authorization header with Bearer token
    db : AsyncSession
        Database session

    Returns
    -------
    dict
        User information from token

    Raises
    ------
    HTTPException
        401 if token is missing, invalid, or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    # Extract token from "Bearer <token>"
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    # Verify token
    try:
        payload = verify_token(token)
        return payload
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except TokenInvalidError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "User successfully registered",
            "model": TokenResponse,
        },
        400: {
            "description": "Invalid input (validation error)",
            "model": ErrorResponse,
        },
        409: {
            "description": "User already exists",
            "model": ErrorResponse,
        },
    },
)
async def register(
    user_data: UserRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Register a new user account.

    Creates a new user with email and password, returns JWT tokens
    for immediate authentication.

    Parameters
    ----------
    user_data : UserRegister
        User registration data (email, username, password)
    request : Request
        FastAPI request object for extracting metadata
    db : AsyncSession
        Database session

    Returns
    -------
    TokenResponse
        Success response with access/refresh tokens and user data

    Raises
    ------
    HTTPException
        400 for validation errors
        409 if email or username already exists
    """
    auth_service = AuthService(db)

    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user, access_token, refresh_token = await auth_service.register_user(
            user_data, ip_address, user_agent
        )

        # Build response
        user_response = UserResponse.model_validate(user)
        token_data = TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response,
        )

        return TokenResponse(
            success=True,
            message="User registered successfully",
            data=token_data,
        )

    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Login successful",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid credentials",
            "model": ErrorResponse,
        },
        429: {
            "description": "Too many login attempts",
            "model": ErrorResponse,
        },
    },
)
async def login(
    login_data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.

    Validates credentials and returns access/refresh tokens for
    authenticated sessions.

    Parameters
    ----------
    login_data : UserLogin
        Login credentials (email, password)
    request : Request
        FastAPI request object
    db : AsyncSession
        Database session

    Returns
    -------
    TokenResponse
        Success response with tokens and user data

    Raises
    ------
    HTTPException
        401 if credentials are invalid or account is inactive
    """
    auth_service = AuthService(db)

    # Extract request metadata
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        user, access_token, refresh_token = await auth_service.login_user(
            login_data, ip_address, user_agent
        )

        # Build response
        user_response = UserResponse.model_validate(user)
        token_data = TokenData(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_response,
        )

        return TokenResponse(
            success=True,
            message="Login successful",
            data=token_data,
        )

    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Token refreshed successfully",
            "model": TokenRefreshResponse,
        },
        401: {
            "description": "Invalid or expired refresh token",
            "model": ErrorResponse,
        },
    },
)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
) -> TokenRefreshResponse:
    """
    Refresh access token using refresh token.

    Generates a new access token from a valid refresh token.

    Parameters
    ----------
    token_data : TokenRefresh
        Refresh token data
    db : AsyncSession
        Database session

    Returns
    -------
    TokenRefreshResponse
        New access token with metadata

    Raises
    ------
    HTTPException
        401 if refresh token is invalid, expired, or revoked
    """
    auth_service = AuthService(db)

    try:
        new_access_token, user = await auth_service.refresh_access_token(
            token_data.refresh_token
        )

        return TokenRefreshResponse(
            success=True,
            message="Token refreshed successfully",
            data={
                "access_token": new_access_token,
                "token_type": "Bearer",
                "expires_in": AuthService.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            },
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.post(
    "/logout",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Logout successful",
            "model": SuccessResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
    },
)
async def logout(
    logout_data: LogoutRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse:
    """
    Logout user by revoking refresh token.

    Revokes the provided refresh token to invalidate the session.

    Parameters
    ----------
    logout_data : LogoutRequest
        Logout request with refresh token
    current_user : dict
        Current authenticated user
    db : AsyncSession
        Database session

    Returns
    -------
    SuccessResponse
        Success message

    Raises
    ------
    HTTPException
        401 if not authenticated or token is invalid
    """
    auth_service = AuthService(db)

    try:
        await auth_service.revoke_refresh_token(logout_data.refresh_token)

        return SuccessResponse(
            success=True,
            message="Logout successful",
        )

    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "User profile retrieved",
            "model": UserResponse,
        },
        401: {
            "description": "Unauthorized",
            "model": ErrorResponse,
        },
    },
)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get authenticated user's profile.

    Returns the current user's profile information from the JWT token.

    Parameters
    ----------
    current_user : dict
        Current authenticated user from token
    db : AsyncSession
        Database session

    Returns
    -------
    UserResponse
        User profile data

    Raises
    ------
    HTTPException
        401 if not authenticated
        404 if user not found
    """
    auth_service = AuthService(db)

    # Get user from database
    user = await auth_service.get_user_by_id(current_user["user_id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)
