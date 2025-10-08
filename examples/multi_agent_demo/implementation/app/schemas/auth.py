"""
Pydantic schemas for authentication API endpoints.

Provides request/response validation for user registration, login,
token refresh, and authentication responses per auth-api-spec.yaml.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


class UserRegister(BaseModel):
    """
    Schema for user registration request.

    Validates email, username, and password according to security requirements:
    - Email: Valid email format
    - Username: 3-50 chars, alphanumeric + underscore
    - Password: 8-128 chars with complexity requirements
    """

    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["user@example.com"]
    )

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Unique username (alphanumeric and underscore only)",
        examples=["johndoe"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password meeting complexity requirements",
        examples=["SecureP@ssw0rd"]
    )

    @field_validator('password')
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """
        Validate password complexity requirements.

        Must contain:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Raises
        ------
        ValueError
            If password doesn't meet complexity requirements
        """
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserLogin(BaseModel):
    """
    Schema for user login request.

    Validates email and password for authentication.
    """

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )

    password: str = Field(
        ...,
        description="User password",
        examples=["SecureP@ssw0rd"]
    )


class TokenRefresh(BaseModel):
    """
    Schema for token refresh request.

    Validates refresh token for obtaining new access token.
    """

    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class UserResponse(BaseModel):
    """
    Schema for user data in responses.

    Returns user profile information without sensitive data.
    """

    id: int = Field(
        ...,
        description="Unique user identifier",
        examples=[1]
    )

    email: str = Field(
        ...,
        description="User email address",
        examples=["user@example.com"]
    )

    username: str = Field(
        ...,
        description="Username",
        examples=["johndoe"]
    )

    is_active: bool = Field(
        default=True,
        description="Whether user account is active",
        examples=[True]
    )

    is_verified: bool = Field(
        default=False,
        description="Whether email is verified",
        examples=[False]
    )

    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        examples=["2025-10-08T12:00:00Z"]
    )

    last_login: Optional[datetime] = Field(
        default=None,
        description="Last login timestamp",
        examples=["2025-10-08T15:30:00Z"]
    )

    class Config:
        """Pydantic configuration."""
        from_attributes = True  # Allow ORM model conversion


class TokenData(BaseModel):
    """
    Schema for token data in authentication responses.

    Contains JWT tokens and metadata.
    """

    access_token: str = Field(
        ...,
        description="JWT access token (15 min expiry)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    refresh_token: str = Field(
        ...,
        description="JWT refresh token (7 day expiry)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    token_type: str = Field(
        default="Bearer",
        description="Token type",
        examples=["Bearer"]
    )

    expires_in: int = Field(
        ...,
        description="Access token expiry in seconds",
        examples=[900]
    )

    user: UserResponse = Field(
        ...,
        description="User profile information"
    )


class TokenResponse(BaseModel):
    """
    Schema for successful authentication response.

    Standard API response format with token data.
    """

    success: bool = Field(
        default=True,
        description="Indicates successful operation",
        examples=[True]
    )

    message: str = Field(
        ...,
        description="Human-readable response message",
        examples=["Login successful", "User registered successfully"]
    )

    data: TokenData = Field(
        ...,
        description="Token and user data"
    )


class TokenRefreshResponse(BaseModel):
    """
    Schema for token refresh response.

    Returns new access token after refresh.
    """

    success: bool = Field(
        default=True,
        description="Indicates successful operation",
        examples=[True]
    )

    message: str = Field(
        ...,
        description="Human-readable response message",
        examples=["Token refreshed successfully"]
    )

    data: dict = Field(
        ...,
        description="New access token data",
        examples=[{
            "access_token": "eyJhbGci...",
            "token_type": "Bearer",
            "expires_in": 900
        }]
    )


class ErrorResponse(BaseModel):
    """
    Schema for error responses.

    Standard API error format with optional details.
    """

    success: bool = Field(
        default=False,
        description="Indicates failed operation",
        examples=[False]
    )

    error: str = Field(
        ...,
        description="Error message description",
        examples=["Invalid email or password", "Email already registered"]
    )

    details: Optional[dict] = Field(
        default=None,
        description="Additional error details (optional)"
    )


class LogoutRequest(BaseModel):
    """
    Schema for logout request.

    Requires refresh token to revoke.
    """

    refresh_token: str = Field(
        ...,
        description="JWT refresh token to revoke",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )


class SuccessResponse(BaseModel):
    """
    Schema for simple success responses.

    Used for operations like logout.
    """

    success: bool = Field(
        default=True,
        description="Indicates successful operation",
        examples=[True]
    )

    message: str = Field(
        ...,
        description="Human-readable response message",
        examples=["Logout successful"]
    )
