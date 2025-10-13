"""
User-friendly error response handling for the Task Management API.

This module implements the usability requirements for error handling,
providing clear, actionable error messages that help users understand
and recover from errors.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCategory(str, Enum):
    """
    Categories of errors for better user understanding.

    Attributes
    ----------
    VALIDATION : str
        User input validation errors
    AUTHENTICATION : str
        Authentication and authorization errors
    NOT_FOUND : str
        Resource not found errors
    CONFLICT : str
        Resource conflict errors
    RATE_LIMIT : str
        Rate limiting errors
    INTEGRATION : str
        External service integration errors
    SERVER : str
        Internal server errors
    """

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMIT = "rate_limit"
    INTEGRATION = "integration"
    SERVER = "server"


class UserFriendlyError:
    """
    Container for user-friendly error information.

    Attributes
    ----------
    error : str
        Error type/name
    message : str
        User-friendly error message
    details : Dict[str, List[str]], optional
        Field-specific error details
    next_steps : List[str], optional
        Suggested actions for error recovery
    documentation_url : str, optional
        Link to relevant documentation
    support_url : str, optional
        Link to support resources
    request_id : str
        Unique request identifier for support
    timestamp : str
        ISO 8601 timestamp of the error
    """

    def __init__(
        self,
        error: str,
        message: str,
        status_code: int,
        details: Optional[Dict[str, List[str]]] = None,
        next_steps: Optional[List[str]] = None,
        documentation_url: Optional[str] = None,
        support_url: Optional[str] = None,
    ):
        """
        Initialize a user-friendly error.

        Parameters
        ----------
        error : str
            Error type/name
        message : str
            User-friendly error message
        status_code : int
            HTTP status code
        details : Dict[str, List[str]], optional
            Field-specific error details
        next_steps : List[str], optional
            Suggested recovery actions
        documentation_url : str, optional
            Documentation link
        support_url : str, optional
            Support link
        """
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.next_steps = next_steps or []
        self.documentation_url = documentation_url
        self.support_url = support_url
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert error to dictionary for JSON response.

        Returns
        -------
        Dict[str, Any]
            Error data as dictionary
        """
        response: Dict[str, Any] = {
            "error": self.error,
            "message": self.message,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

        if self.details:
            response["details"] = self.details

        if self.next_steps:
            response["next_steps"] = self.next_steps

        if self.documentation_url:
            response["documentation_url"] = self.documentation_url

        if self.support_url:
            response["support_url"] = self.support_url

        return response


def validation_error(
    field_errors: Dict[str, List[str]],
    message: str = "Please fix the following errors:",
) -> UserFriendlyError:
    """
    Create a validation error with field-specific messages.

    Parameters
    ----------
    field_errors : Dict[str, List[str]]
        Dictionary mapping field names to error messages
    message : str, optional
        Overall error message

    Returns
    -------
    UserFriendlyError
        Formatted validation error

    Examples
    --------
    >>> errors = {
    ...     "title": ["Title is required and cannot be empty"],
    ...     "due_date": ["Date must be in the future"]
    ... }
    >>> error = validation_error(errors)
    >>> error.to_dict()
    """
    return UserFriendlyError(
        error="ValidationError",
        message=message,
        status_code=400,
        details=field_errors,
        documentation_url="https://docs.example.com/errors/validation",
    )


def authentication_error(
    message: str = "Please log in to access this resource.",
) -> UserFriendlyError:
    """
    Create an authentication error.

    Parameters
    ----------
    message : str, optional
        User-friendly auth error message

    Returns
    -------
    UserFriendlyError
        Formatted authentication error
    """
    return UserFriendlyError(
        error="AuthenticationError",
        message=message,
        status_code=401,
        next_steps=[
            "Log in to your account",
            "If you don't have an account, sign up first",
            "Check that you're using the correct credentials",
        ],
        documentation_url="https://docs.example.com/authentication",
    )


def authorization_error(
    message: str = "You don't have permission to perform this action.",
) -> UserFriendlyError:
    """
    Create an authorization error.

    Parameters
    ----------
    message : str, optional
        User-friendly authorization error message

    Returns
    -------
    UserFriendlyError
        Formatted authorization error
    """
    return UserFriendlyError(
        error="AuthorizationError",
        message=message,
        status_code=403,
        next_steps=[
            "Contact the resource owner to request access",
            "Check that you're logged in to the correct account",
        ],
        documentation_url="https://docs.example.com/permissions",
    )


def not_found_error(
    resource: str = "resource",
    message: Optional[str] = None,
) -> UserFriendlyError:
    """
    Create a not found error.

    Parameters
    ----------
    resource : str
        Name of the resource that wasn't found
    message : str, optional
        Custom error message

    Returns
    -------
    UserFriendlyError
        Formatted not found error

    Examples
    --------
    >>> error = not_found_error("task")
    >>> error.message
    'Task not found. It may have been deleted or you may not have access to it.'
    """
    if message is None:
        message = (
            f"{resource.title()} not found. It may have been deleted "
            f"or you may not have access to it."
        )

    return UserFriendlyError(
        error="NotFoundError",
        message=message,
        status_code=404,
        next_steps=[
            f"Check that the {resource} ID is correct",
            f"The {resource} may have been deleted by you or another user",
            "Try refreshing your list to see the latest data",
        ],
    )


def conflict_error(
    message: str,
    resolution_steps: Optional[List[str]] = None,
) -> UserFriendlyError:
    """
    Create a conflict error.

    Parameters
    ----------
    message : str
        Description of the conflict
    resolution_steps : List[str], optional
        Steps to resolve the conflict

    Returns
    -------
    UserFriendlyError
        Formatted conflict error
    """
    default_steps = [
        "Check for duplicate entries",
        "Try using a different name or value",
        "Refresh the page to see the latest data",
    ]

    return UserFriendlyError(
        error="ConflictError",
        message=message,
        status_code=409,
        next_steps=resolution_steps or default_steps,
    )


def rate_limit_error(
    retry_after: int = 60,
) -> UserFriendlyError:
    """
    Create a rate limit error.

    Parameters
    ----------
    retry_after : int
        Seconds until user can retry

    Returns
    -------
    UserFriendlyError
        Formatted rate limit error
    """
    return UserFriendlyError(
        error="RateLimitError",
        message=f"Too many requests. Please try again in {retry_after} seconds.",
        status_code=429,
        next_steps=[
            f"Wait {retry_after} seconds before trying again",
            "Consider batching your requests",
            "Contact support if you need a higher rate limit",
        ],
        documentation_url="https://docs.example.com/rate-limits",
    )


def calendar_sync_error(
    provider: str,
    reason: str,
) -> UserFriendlyError:
    """
    Create a calendar sync error.

    Parameters
    ----------
    provider : str
        Calendar provider name (Google, Microsoft, etc.)
    reason : str
        Reason for sync failure

    Returns
    -------
    UserFriendlyError
        Formatted calendar sync error
    """
    return UserFriendlyError(
        error="CalendarSyncError",
        message=f"Unable to sync with {provider} Calendar",
        status_code=502,
        details={"reason": [reason]},
        next_steps=[
            "Go to Settings > Calendar Connections",
            f"Click 'Reconnect' next to your {provider} Calendar",
            "Authorize the app again",
            "If the problem persists, try disconnecting and reconnecting your calendar",
        ],
        documentation_url="https://docs.example.com/calendar-sync-issues",
        support_url="https://support.example.com",
    )


def server_error(
    message: str = "Something went wrong on our end. Please try again.",
) -> UserFriendlyError:
    """
    Create a server error.

    Parameters
    ----------
    message : str, optional
        User-friendly server error message

    Returns
    -------
    UserFriendlyError
        Formatted server error
    """
    return UserFriendlyError(
        error="InternalServerError",
        message=message,
        status_code=500,
        next_steps=[
            "Try again in a few moments",
            "If the problem persists, contact support with the request ID",
            "Check our status page for any ongoing issues",
        ],
        support_url="https://support.example.com",
    )


def make_field_error_user_friendly(field: str, error_type: str) -> str:
    """
    Convert technical field errors to user-friendly messages.

    Parameters
    ----------
    field : str
        Field name
    error_type : str
        Type of error

    Returns
    -------
    str
        User-friendly error message

    Examples
    --------
    >>> make_field_error_user_friendly("title", "value_error.missing")
    'Title is required and cannot be empty.'
    >>> make_field_error_user_friendly("email", "value_error.email")
    'Please enter a valid email address (e.g., user@example.com).'
    """
    field_label = field.replace("_", " ").title()

    error_messages = {
        "value_error.missing": (f"{field_label} is required and cannot be empty."),
        "type_error.integer": f"{field_label} must be a valid number.",
        "type_error.string": f"{field_label} must be text.",
        "type_error.datetime": (f"{field_label} must be a valid date and time."),
        "value_error.email": (
            "Please enter a valid email address (e.g., user@example.com)."
        ),
        "value_error.url": ("Please enter a valid URL (e.g., https://example.com)."),
        "value_error.number.not_ge": (
            f"{field_label} must be greater than or equal to " "the minimum value."
        ),
        "value_error.number.not_le": (
            f"{field_label} must be less than or equal to " "the maximum value."
        ),
        "value_error.str.max_length": (
            f"{field_label} is too long. Please shorten it."
        ),
        "value_error.str.min_length": (
            f"{field_label} is too short. Please add more detail."
        ),
    }

    return error_messages.get(
        error_type,
        f"{field_label} has an invalid value. Please check and try again.",
    )
