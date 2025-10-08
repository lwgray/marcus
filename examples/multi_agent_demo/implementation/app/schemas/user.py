"""
Pydantic schemas for user management endpoints.

Provides request/response validation and serialization for user-related operations.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr = Field(..., description="User's email address")
    username: str = Field(
        ..., min_length=3, max_length=80, description="Unique username"
    )


class UserCreate(UserBase):
    """Schema for user registration/creation."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 chars, must include uppercase, lowercase, digit, special char)",
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format (alphanumeric + underscore only)."""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only letters, numbers, and underscores"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    email: Optional[EmailStr] = Field(None, description="New email address")
    username: Optional[str] = Field(
        None, min_length=3, max_length=80, description="New username"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format if provided."""
        if v is not None and not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only letters, numbers, and underscores"
            )
        return v


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (must meet security requirements)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate new password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserResponse(UserBase):
    """Schema for user data in responses (excludes password)."""

    id: int = Field(..., description="User ID")
    is_active: bool = Field(..., description="Whether account is active")
    is_verified: bool = Field(..., description="Whether email is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    roles: list[str] = Field(default_factory=list, description="User roles")

    class Config:
        """Pydantic configuration."""

        from_attributes = True  # Enable ORM mode for SQLAlchemy models


class UserListResponse(BaseModel):
    """Schema for paginated user list."""

    users: list[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of users per page")
    total_pages: int = Field(..., description="Total number of pages")


class UserSearchParams(BaseModel):
    """Schema for user search/filter parameters."""

    email: Optional[str] = Field(None, description="Filter by email (partial match)")
    username: Optional[str] = Field(
        None, description="Filter by username (partial match)"
    )
    role: Optional[str] = Field(None, description="Filter by role")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_verified: Optional[bool] = Field(None, description="Filter by verified status")
    page: int = Field(1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(
        20, ge=1, le=100, description="Number of results per page (1-100)"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="Sort field (created_at, username, email)",
        pattern="^(created_at|username|email|last_login)$",
    )
    sort_order: Optional[str] = Field(
        "desc", description="Sort order (asc or desc)", pattern="^(asc|desc)$"
    )


class RoleAssignment(BaseModel):
    """Schema for assigning/removing roles."""

    user_id: int = Field(..., description="User ID to assign role to")
    role: str = Field(
        ...,
        description="Role to assign (user, admin, moderator, super_admin)",
        pattern="^(user|admin|moderator|super_admin)$",
    )


class RoleResponse(BaseModel):
    """Schema for role assignment response."""

    id: int = Field(..., description="Role assignment ID")
    user_id: int = Field(..., description="User ID")
    role: str = Field(..., description="Role name")
    granted_at: datetime = Field(..., description="When role was granted")
    granted_by: Optional[int] = Field(None, description="Admin user who granted role")

    class Config:
        """Pydantic configuration."""

        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")


class SuccessResponse(BaseModel):
    """Schema for generic success responses."""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(None, description="Optional response data")
