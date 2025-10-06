"""
Main FastAPI application entry point.

This module initializes the FastAPI application, configures middleware,
and registers all API routes.

Author: Foundation Agent
Task: Implement User Management (task_user_management_implement)
"""

from app.config import get_settings
from app.routes import auth
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="Task Management API",
    description="Production-quality REST API for task management",
    version="1.0.0",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")  # type: ignore[misc]
async def root() -> dict[str, str]:
    """
    Root endpoint for health check.

    Returns
    -------
    dict[str, str]
        Welcome message and API version
    """
    return {
        "message": "Task Management API",
        "version": "1.0.0",
        "docs": f"{settings.api_v1_prefix}/docs",
    }


@app.get("/health")  # type: ignore[misc]
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns
    -------
    dict[str, str]
        Health status
    """
    return {"status": "healthy"}


# Register routes
app.include_router(auth.router, prefix=settings.api_v1_prefix)
