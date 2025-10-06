"""
Custom exceptions for the application.

This module defines custom exception classes for consistent
error handling across the API.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from typing import Any, Optional


class TaskManagementError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        """
        Initialize error.

        Parameters
        ----------
        message : str
            Human-readable error message
        details : Optional[dict[str, Any]]
            Additional error details
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class UserAlreadyExistsError(TaskManagementError):
    """Raised when attempting to create a user that already exists."""

    pass


class UserNotFoundError(TaskManagementError):
    """Raised when a user cannot be found."""

    pass


class InvalidCredentialsError(TaskManagementError):
    """Raised when login credentials are invalid."""

    pass


class UnauthorizedError(TaskManagementError):
    """Raised when user is not authorized for an action."""

    pass


class ValidationError(TaskManagementError):
    """Raised when input validation fails."""

    pass
