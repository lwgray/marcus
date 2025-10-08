"""
Security utilities for Task Management API.

This package provides:
- Password hashing and verification with bcrypt
- JWT token generation and validation
- Input sanitization utilities
- Rate limiting configuration
"""

from app.security.password import hash_password, verify_password
from app.security.jwt_handler import create_access_token, verify_token, get_current_user
from app.security.sanitizer import sanitize_html, sanitize_text
from app.security.rate_limit import limiter, configure_rate_limiting

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_token",
    "get_current_user",
    "sanitize_html",
    "sanitize_text",
    "limiter",
    "configure_rate_limiting",
]
