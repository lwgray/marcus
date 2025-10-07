"""
User-related Pydantic schemas.

This module defines request and response models for user management
endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):  # type: ignore[misc]
    """
    User response schema (without sensitive data).

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
    is_superuser : bool
        Whether the user has superuser privileges

    Examples
    --------
    >>> response = UserResponse(
    ...     id=1,
    ...     email="user@example.com",
    ...     full_name="John Doe",
    ...     is_active=True,
    ...     is_superuser=False
    ... )
    """

    id: int = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    is_active: bool = Field(..., description="Whether the account is active")
    is_superuser: bool = Field(
        ..., description="Whether the user has superuser privileges"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "email": "user@example.com",
                    "full_name": "John Doe",
                    "is_active": True,
                    "is_superuser": False,
                }
            ]
        },
    }


class UserUpdate(BaseModel):  # type: ignore[misc]
    """
    User update request schema.

    Attributes
    ----------
    email : EmailStr, optional
        New email address
    full_name : str, optional
        New full name
    password : str, optional
        New password (min 8 chars)

    Examples
    --------
    >>> request = UserUpdate(
    ...     email="newemail@example.com",
    ...     full_name="Jane Doe"
    ... )
    """

    email: EmailStr | None = Field(None, description="New email address")
    full_name: str | None = Field(None, max_length=255, description="New full name")
    password: str | None = Field(
        None,
        min_length=8,
        max_length=100,
        description="New password (min 8 chars)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"email": "newemail@example.com", "full_name": "Jane Doe"}]
        }
    }
