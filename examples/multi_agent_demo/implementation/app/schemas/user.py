"""
Pydantic schemas for User API endpoints.

This module defines request and response schemas for user-related operations.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """
    Base user schema with common fields.

    Attributes
    ----------
    email : EmailStr
        User email address
    username : str
        Unique username
    first_name : Optional[str]
        User's first name
    last_name : Optional[str]
        User's last name
    """

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """
    Schema for user registration.

    Attributes
    ----------
    password : str
        User password (minimum 8 characters)
    """

    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.

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
            If password doesn't meet requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    """
    Schema for updating user information.

    Attributes
    ----------
    first_name : Optional[str]
        Updated first name
    last_name : Optional[str]
        Updated last name
    email : Optional[EmailStr]
        Updated email address
    """

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """
    Schema for user response data.

    Attributes
    ----------
    id : int
        User ID
    email : str
        User email
    username : str
        Username
    first_name : Optional[str]
        First name
    last_name : Optional[str]
        Last name
    role : str
        User role
    is_active : bool
        Account active status
    is_verified : bool
        Email verification status
    created_at : datetime
        Account creation timestamp
    last_login : Optional[datetime]
        Last login timestamp
    """

    id: int
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    """
    Schema for login credentials.

    Attributes
    ----------
    email : EmailStr
        User email
    password : str
        User password
    """

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """
    Schema for authentication token response.

    Attributes
    ----------
    access_token : str
        JWT access token
    token_type : str
        Token type (Bearer)
    expires_in : int
        Token expiration time in seconds
    user : UserResponse
        User information
    """

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse
