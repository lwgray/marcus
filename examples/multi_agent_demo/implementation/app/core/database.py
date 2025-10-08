"""
Database configuration with connection pooling and performance optimizations.

This module configures SQLAlchemy with async support, connection pooling,
and query optimization settings to achieve <100ms response times for CRUD operations.
"""

from typing import AsyncGenerator
import os
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.orm import declarative_base

# Database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/task_management"  # pragma: allowlist secret
)

# Connection pool configuration for optimal performance
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "20"))  # Number of connections to maintain
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))  # Extra connections under load
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Seconds to wait for connection
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # Recycle connections after 1 hour
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# Query execution settings
ECHO_SQL = os.getenv("DB_ECHO_SQL", "false").lower() == "true"  # Log SQL queries
QUERY_TIMEOUT = int(os.getenv("DB_QUERY_TIMEOUT", "10000"))  # 10 seconds in milliseconds

# Base for declarative models
Base = declarative_base()


def create_engine():
    """
    Create async SQLAlchemy engine with optimized connection pooling.

    Connection Pool Configuration
    ------------------------------
    - pool_size: 20 persistent connections (balanced for typical web app load)
    - max_overflow: 10 additional connections during traffic spikes
    - pool_timeout: 30s timeout waiting for available connection
    - pool_recycle: 3600s (1h) to prevent stale connections
    - pool_pre_ping: True to check connection health before use

    Performance Benefits
    -------------------
    - Reduces connection overhead (50-100ms saved per request)
    - Maintains warm connections ready for queries
    - Automatically recovers from database disconnections
    - Prevents connection leaks with proper lifecycle management

    Returns
    -------
    AsyncEngine
        Configured async SQLAlchemy engine

    Examples
    --------
    >>> engine = create_engine()
    >>> async with engine.begin() as conn:
    ...     result = await conn.execute(select(User).limit(10))
    """
    # Use NullPool for testing, QueuePool for production
    poolclass = NullPool if "pytest" in os.getenv("_", "") else QueuePool

    engine = create_async_engine(
        DATABASE_URL,
        echo=ECHO_SQL,
        poolclass=poolclass,
        pool_size=POOL_SIZE if poolclass == QueuePool else None,
        max_overflow=MAX_OVERFLOW if poolclass == QueuePool else None,
        pool_timeout=POOL_TIMEOUT if poolclass == QueuePool else None,
        pool_recycle=POOL_RECYCLE if poolclass == QueuePool else None,
        pool_pre_ping=POOL_PRE_PING if poolclass == QueuePool else False,
        # Performance optimizations
        execution_options={
            "isolation_level": "READ COMMITTED",  # Balance between consistency and performance
        },
        connect_args={
            "server_settings": {
                "application_name": "task_management_api",
                "jit": "on",  # Enable JIT compilation for complex queries
            },
            "command_timeout": QUERY_TIMEOUT / 1000,  # Convert to seconds
            "timeout": QUERY_TIMEOUT / 1000,
        },
    )

    return engine


# Global engine instance
engine = create_engine()

# Session factory with optimized settings
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading after commit
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI to provide database sessions.

    Yields database session with automatic cleanup and error handling.
    Ensures connections are properly returned to the pool.

    Yields
    ------
    AsyncSession
        Database session for the request

    Examples
    --------
    >>> @app.get("/users")
    >>> async def list_users(db: AsyncSession = Depends(get_db)):
    ...     result = await db.execute(select(User).limit(10))
    ...     return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database schema.

    Creates all tables defined in SQLAlchemy models.
    Should be called once during application startup.

    Examples
    --------
    >>> @app.on_event("startup")
    >>> async def startup():
    ...     await init_db()
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections and cleanup resources.

    Should be called during application shutdown to ensure
    all connections are properly closed and returned to the pool.

    Examples
    --------
    >>> @app.on_event("shutdown")
    >>> async def shutdown():
    ...     await close_db()
    """
    await engine.dispose()


class DatabaseHealthCheck:
    """
    Database health check utility for monitoring connection pool status.

    Provides methods to verify database connectivity and pool health.
    """

    @staticmethod
    async def check_connection() -> bool:
        """
        Verify database connection is available and healthy.

        Returns
        -------
        bool
            True if connection is healthy, False otherwise

        Examples
        --------
        >>> is_healthy = await DatabaseHealthCheck.check_connection()
        >>> if not is_healthy:
        ...     logger.error("Database connection unhealthy")
        """
        try:
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
                return True
        except Exception:
            return False

    @staticmethod
    def get_pool_status() -> dict:
        """
        Get current connection pool statistics.

        Returns
        -------
        dict
            Pool status including size, checked_in, checked_out, overflow

        Examples
        --------
        >>> status = DatabaseHealthCheck.get_pool_status()
        >>> print(f"Active connections: {status['checked_out']}")
        """
        pool = engine.pool
        return {
            "size": pool.size() if hasattr(pool, "size") else None,
            "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else None,
            "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else None,
            "overflow": pool.overflow() if hasattr(pool, "overflow") else None,
            "total": pool.size() + pool.overflow()
            if hasattr(pool, "size") and hasattr(pool, "overflow")
            else None,
        }
