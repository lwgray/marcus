"""
Task Management API - FastAPI Application.

A production-ready REST API for task management with authentication,
user management, projects, tasks, and comments.
"""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from app.core.database import close_db, init_db
from app.routes import auth_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup and shutdown events.

    Handles database initialization on startup and cleanup on shutdown.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance

    Yields
    ------
    None
    """
    # Startup: Initialize database
    print("🚀 Starting Task Management API...")
    await init_db()
    print("✓ Database initialized")

    yield

    # Shutdown: Close database connections
    print("🛑 Shutting down Task Management API...")
    await close_db()
    print("✓ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title="Task Management API",
    description="A production-ready REST API for managing tasks, projects, and teams",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns
    -------
    dict
        Health status
    """
    return {"status": "healthy", "service": "task-management-api"}


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    """
    Root endpoint with API information.

    Returns
    -------
    dict
        API information
    """
    return {
        "name": "Task Management API",
        "version": "1.0.0",
        "docs": "/api/v1/docs",
        "health": "/health",
    }


# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])

# TODO: Add additional routers when implemented
# app.include_router(users_router, prefix="/api/v1/users", tags=["Users"])
# app.include_router(projects_router, prefix="/api/v1/projects", tags=["Projects"])
# app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["Tasks"])
# app.include_router(comments_router, prefix="/api/v1/comments", tags=["Comments"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.

    Parameters
    ----------
    request : Request
        The incoming request
    exc : Exception
        The exception that was raised

    Returns
    -------
    JSONResponse
        Error response
    """
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": (
                str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None
            ),
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "true").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
