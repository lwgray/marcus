"""
Pydantic schemas package for request/response validation.

This package contains schemas for:
- Auth: Authentication and JWT token management
- User: User management and authentication
- Error/Success: Standard response formats
"""

from app.schemas.auth import (
    LogoutRequest,
    TokenData,
    TokenRefresh,
    TokenRefreshResponse,
    TokenResponse,
    UserLogin,
    UserRegister,
)
from app.schemas.user import (
    ErrorResponse,
    PasswordChange,
    RoleAssignment,
    RoleResponse,
    SuccessResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSearchParams,
    UserUpdate,
)

__all__ = [
    # Auth schemas
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "TokenRefresh",
    "TokenRefreshResponse",
    "TokenData",
    "LogoutRequest",
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
    "UserSearchParams",
    "PasswordChange",
    "RoleAssignment",
    "RoleResponse",
    "ErrorResponse",
    "SuccessResponse",
]
