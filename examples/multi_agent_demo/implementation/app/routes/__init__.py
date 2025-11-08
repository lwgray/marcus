"""
API routes package for Task Management API.

This package contains FastAPI router modules for:
- Auth: Authentication and JWT token endpoints
- Users: User management endpoints
"""

from app.routes.auth import router as auth_router

__all__ = ["auth_router"]
