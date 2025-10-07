"""
Authentication-related Pydantic schemas.

This module defines request and response models for authentication
endpoints including registration and login.
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterRequest(BaseModel):  # type: ignore[misc]
    """
    User registration request schema.

    Attributes
    ----------
    email : EmailStr
        Valid email address
    password : str
        Password (min 8 chars, must contain uppercase, lowercase, digit, special char)
    full_name : str, optional
        User's full name

    Examples
    --------
    >>> request = UserRegisterRequest(
    ...     email="user@example.com",
    ...     password="SecurePass123!",  # pragma: allowlist secret
    ...     full_name="John Doe"
    ... )
    """

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (min 8 chars, must include uppercase, lowercase, "
        "digit, and special character)",
    )
    full_name: str | None = Field(
        None, max_length=255, description="User's full name (optional)"
    )

    @field_validator("password")  # type: ignore[misc]
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength requirements.

        Parameters
        ----------
        v : str
            Password to validate

        Returns
        -------
        str
            Validated password

        Raises
        ------
        ValueError
            If password doesn't meet strength requirements
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!",  # pragma: allowlist secret
                    "full_name": "John Doe",
                }
            ]
        }
    }


class UserRegisterResponse(BaseModel):  # type: ignore[misc]
    """
    User registration response schema.

    Attributes
    ----------
    id : int
        User's unique identifier
    email : str
        User's email address
    full_name : str, optional
        User's full name
    is_active : bool
        Whether the account is active
    access_token : str
        JWT access token for authentication
    token_type : str
        Token type (always "bearer")

    Examples
    --------
    >>> response = UserRegisterResponse(
    ...     id=1,
    ...     email="user@example.com",
    ...     full_name="John Doe",
    ...     is_active=True,
    ...     access_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
    ...     token_type="bearer"
    ... )
    """

    id: int = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    is_active: bool = Field(..., description="Whether the account is active")
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class LoginRequest(BaseModel):  # type: ignore[misc]
    """
    User login request schema.

    Attributes
    ----------
    email : EmailStr
        User's email address
    password : str
        User's password

    Examples
    --------
    >>> request = LoginRequest(
    ...     email="user@example.com",
    ...     password="SecurePass123!"  # pragma: allowlist secret
    ... )
    """

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "password": "SecurePass123!",  # pragma: allowlist secret
                }
            ]
        }
    }


class TokenResponse(BaseModel):  # type: ignore[misc]
    """
    JWT token response schema.

    Attributes
    ----------
    access_token : str
        JWT access token
    token_type : str
        Token type (always "bearer")

    Examples
    --------
    >>> response = TokenResponse(
    ...     access_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
    ...     token_type="bearer"
    ... )
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class LoginResponse(BaseModel):  # type: ignore[misc]
    """
    User login response schema.

    Attributes
    ----------
    id : int
        User's unique identifier
    email : str
        User's email address
    full_name : str, optional
        User's full name
    is_active : bool
        Whether the account is active
    access_token : str
        JWT access token for authentication
    token_type : str
        Token type (always "bearer")

    Examples
    --------
    >>> response = LoginResponse(
    ...     id=1,
    ...     email="user@example.com",
    ...     full_name="John Doe",
    ...     is_active=True,
    ...     access_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
    ...     token_type="bearer"
    ... )
    """

    id: int = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    is_active: bool = Field(..., description="Whether the account is active")
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }
