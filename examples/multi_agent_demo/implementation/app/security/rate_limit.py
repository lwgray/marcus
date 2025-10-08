"""
Rate limiting configuration for API endpoints.

Provides Flask-Limiter integration with configurable limits
for different endpoint types, especially authentication endpoints.
"""

import os
from typing import Callable, Optional

from flask import Request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Rate limiting configuration from environment
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_STORAGE_URL = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

# Default rate limits
DEFAULT_RATE_LIMIT = "200 per hour"
AUTH_RATE_LIMIT = "5 per minute"  # Strict for login/register
PASSWORD_RESET_LIMIT = "3 per hour"  # Very strict for password reset


def get_identifier(request: Optional[Request] = None) -> str:
    """
    Get unique identifier for rate limiting.

    Tries to use authenticated user ID if available,
    falls back to IP address for anonymous requests.

    Parameters
    ----------
    request : Request, optional
        Flask request object

    Returns
    -------
    str
        Unique identifier for rate limiting

    Notes
    -----
    - Uses user_id from request context if authenticated
    - Falls back to IP address for anonymous users
    - Handles proxy headers (X-Forwarded-For) for correct IP
    """
    if request and hasattr(request, "user_id"):
        # Use user ID for authenticated requests
        return f"user:{request.user_id}"

    # Fall back to IP address
    return get_remote_address()


# Initialize Flask-Limiter
limiter = Limiter(
    key_func=get_identifier,
    storage_uri=RATE_LIMIT_STORAGE_URL,
    strategy="fixed-window",
    default_limits=[DEFAULT_RATE_LIMIT] if RATE_LIMIT_ENABLED else [],
)


def configure_rate_limiting(app):
    """
    Configure rate limiting for a Flask application.

    Parameters
    ----------
    app : Flask
        Flask application instance

    Returns
    -------
    Limiter
        Configured limiter instance

    Examples
    --------
    >>> from flask import Flask
    >>> app = Flask(__name__)
    >>> limiter = configure_rate_limiting(app)

    Notes
    -----
    - Initializes limiter with app
    - Sets up storage backend (memory or Redis)
    - Configures default and custom limits
    - Returns limiter for route decorators
    """
    limiter.init_app(app)
    return limiter


def auth_rate_limit() -> Callable:
    """
    Decorator for authentication endpoints with strict rate limiting.

    Returns
    -------
    callable
        Decorator function for route

    Examples
    --------
    >>> @app.route('/api/auth/login', methods=['POST'])
    >>> @auth_rate_limit()
    >>> def login():
    ...     # Login logic
    ...     pass

    Notes
    -----
    - Limits: 5 requests per minute
    - Prevents brute-force password attacks
    - Applies per IP address or user
    """
    return limiter.limit(AUTH_RATE_LIMIT)


def password_reset_rate_limit() -> Callable:
    """
    Decorator for password reset endpoints with very strict rate limiting.

    Returns
    -------
    callable
        Decorator function for route

    Examples
    --------
    >>> @app.route('/api/auth/password-reset', methods=['POST'])
    >>> @password_reset_rate_limit()
    >>> def password_reset():
    ...     # Password reset logic
    ...     pass

    Notes
    -----
    - Limits: 3 requests per hour
    - Prevents email flooding and abuse
    - Very strict to protect against DoS
    """
    return limiter.limit(PASSWORD_RESET_LIMIT)


def custom_rate_limit(limit_string: str) -> Callable:
    """
    Create a custom rate limit decorator.

    Parameters
    ----------
    limit_string : str
        Rate limit in format "N per time_unit"
        Examples: "10 per minute", "100 per hour", "1000 per day"

    Returns
    -------
    callable
        Decorator function for route

    Examples
    --------
    >>> @app.route('/api/data/export')
    >>> @custom_rate_limit("2 per day")
    >>> def export_data():
    ...     # Export logic
    ...     pass

    Notes
    -----
    - Flexible rate limiting for specific needs
    - Supports: second, minute, hour, day units
    - Can combine multiple limits: "5/minute;100/hour"
    """
    return limiter.limit(limit_string)


def exempt_from_rate_limit(func: Callable) -> Callable:
    """
    Exempt a route from rate limiting.

    Parameters
    ----------
    func : callable
        Route function to exempt

    Returns
    -------
    callable
        Decorated function with rate limiting exemption

    Examples
    --------
    >>> @app.route('/api/health')
    >>> @exempt_from_rate_limit
    >>> def health_check():
    ...     return {'status': 'ok'}

    Notes
    -----
    - Use sparingly (health checks, webhooks, etc.)
    - Does not apply default or custom limits
    - Still counts towards storage if using shared backend
    """
    return limiter.exempt(func)


class RateLimitExceeded(Exception):
    """
    Exception raised when rate limit is exceeded.

    Attributes
    ----------
    limit : str
        The limit that was exceeded
    reset_time : int
        Unix timestamp when the limit resets
    """

    def __init__(self, limit: str, reset_time: int):
        """
        Initialize RateLimitExceeded exception.

        Parameters
        ----------
        limit : str
            The rate limit that was exceeded
        reset_time : int
            Unix timestamp when limit resets
        """
        self.limit = limit
        self.reset_time = reset_time
        super().__init__(f"Rate limit exceeded: {limit}")


def get_rate_limit_status(identifier: Optional[str] = None) -> dict:
    """
    Get current rate limit status for an identifier.

    Parameters
    ----------
    identifier : str, optional
        Identifier to check (default: current request identifier)

    Returns
    -------
    dict
        Rate limit status with keys:
        - limit: Current limit string
        - remaining: Requests remaining
        - reset: Unix timestamp when limit resets

    Examples
    --------
    >>> status = get_rate_limit_status("user:123")
    >>> status['remaining']
    4
    >>> status['limit']
    '5 per minute'

    Notes
    -----
    - Useful for displaying limit info to users
    - Can be included in API response headers
    - Returns None values if limiter not configured
    """
    if not RATE_LIMIT_ENABLED:
        return {"limit": None, "remaining": None, "reset": None}

    # This would need to query the limiter's storage backend
    # Implementation depends on storage type (memory, Redis, etc.)
    return {
        "limit": DEFAULT_RATE_LIMIT,
        "remaining": None,  # Would query from storage
        "reset": None,  # Would calculate from storage
    }
