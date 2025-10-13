"""
Caching utilities for performance optimization.

Implements Redis-based caching for frequently accessed data to reduce
database load and achieve <100ms response times.
"""

from typing import Optional, Any, Callable, TypeVar, ParamSpec
from functools import wraps
import json
import hashlib
import os
from datetime import timedelta

try:
    import redis.asyncio as redis  # type: ignore[import-untyped]
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Type variables for generic decorators
P = ParamSpec('P')
T = TypeVar('T')


# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5 minutes


class CacheClient:
    """
    Async Redis cache client with automatic serialization.

    Provides high-level caching operations with JSON serialization,
    TTL management, and connection pooling.

    Examples
    --------
    >>> cache = CacheClient()
    >>> await cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)
    >>> user = await cache.get("user:123")
    >>> print(user["name"])  # "John"
    """

    def __init__(self) -> None:
        """Initialize Redis client with connection pooling."""
        self._client: Optional[Any] = None  # redis.Redis type not available
        self._enabled: bool = CACHE_ENABLED and REDIS_AVAILABLE

    async def connect(self) -> None:
        """
        Establish Redis connection with connection pooling.

        Connection pool automatically manages connections for optimal performance.
        """
        if not self._enabled:
            return

        try:
            self._client = await redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,  # Connection pool size
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            # Test connection
            await self._client.ping()
        except Exception:
            self._enabled = False
            self._client = None

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self._client:
            await self._client.close()

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        Optional[Any]
            Cached value (deserialized from JSON) or None if not found

        Examples
        --------
        >>> value = await cache.get("user:123")
        >>> if value is None:
        ...     # Cache miss - fetch from database
        ...     value = await fetch_from_db()
        """
        if not self._enabled or not self._client:
            return None

        try:
            value = await self._client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Parameters
        ----------
        key : str
            Cache key
        value : Any
            Value to cache (must be JSON serializable)
        ttl : Optional[int]
            Time-to-live in seconds (default: 300)

        Returns
        -------
        bool
            True if successful, False otherwise

        Examples
        --------
        >>> await cache.set("user:123", user_dict, ttl=600)  # Cache for 10 minutes
        """
        if not self._enabled or not self._client:
            return False

        try:
            ttl = ttl or CACHE_DEFAULT_TTL
            serialized = json.dumps(value)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Parameters
        ----------
        key : str
            Cache key to delete

        Returns
        -------
        bool
            True if deleted, False otherwise

        Examples
        --------
        >>> await cache.delete("user:123")  # Invalidate cache after update
        """
        if not self._enabled or not self._client:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Parameters
        ----------
        pattern : str
            Redis pattern (e.g., "user:*" to delete all user keys)

        Returns
        -------
        int
            Number of keys deleted

        Examples
        --------
        >>> deleted = await cache.delete_pattern("user:*")
        >>> print(f"Deleted {deleted} user cache entries")
        """
        if not self._enabled or not self._client:
            return 0

        try:
            keys: list[str] = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted: int = await self._client.delete(*keys)
                return deleted
            return 0
        except Exception:
            return 0

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Parameters
        ----------
        key : str
            Cache key

        Returns
        -------
        bool
            True if key exists, False otherwise
        """
        if not self._enabled or not self._client:
            return False

        try:
            result: int = await self._client.exists(key)
            return result > 0
        except Exception:
            return False


# Global cache instance
cache = CacheClient()


def cache_key(*args: Any, **kwargs: Any) -> str:
    """
    Generate consistent cache key from function arguments.

    Parameters
    ----------
    *args
        Positional arguments
    **kwargs
        Keyword arguments

    Returns
    -------
    str
        SHA256 hash of arguments

    Examples
    --------
    >>> key = cache_key("get_user", user_id=123)
    >>> # Always generates same key for same arguments
    """
    key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
    return hashlib.sha256(key_data.encode()).hexdigest()


def cached(
    ttl: int = CACHE_DEFAULT_TTL,
    key_prefix: str = "",
    key_builder: Optional[Callable[..., str]] = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to cache function results.

    Automatically caches function return values in Redis with the specified TTL.
    Subsequent calls with the same arguments return cached result.

    Parameters
    ----------
    ttl : int
        Time-to-live in seconds (default: 300)
    key_prefix : str
        Prefix for cache keys (e.g., "user:", "product:")
    key_builder : Optional[Callable]
        Custom function to build cache key from args/kwargs

    Returns
    -------
    Callable
        Decorated function with caching

    Examples
    --------
    >>> @cached(ttl=600, key_prefix="user:")
    >>> async def get_user(user_id: str):
    ...     # Expensive database query
    ...     return await db.query(User).filter(User.id == user_id).first()
    >>>
    >>> # First call - fetches from database and caches
    >>> user = await get_user("123")
    >>>
    >>> # Second call - returns from cache (much faster)
    >>> user = await get_user("123")
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Build cache key
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                key_suffix = cache_key(func.__name__, *args, **kwargs)

            cache_key_str = f"{key_prefix}{key_suffix}"

            # Try to get from cache
            cached_result = await cache.get(cache_key_str)
            if cached_result is not None:
                return cached_result  # type: ignore[no-any-return]

            # Cache miss - call function
            result = await func(*args, **kwargs)  # type: ignore[misc]

            # Cache the result
            if result is not None:
                await cache.set(cache_key_str, result, ttl=ttl)

            return result  # type: ignore[no-any-return]

        return wrapper  # type: ignore[return-value]
    return decorator


class CacheStrategy:
    """
    Predefined caching strategies for common use cases.

    Provides TTL recommendations based on data access patterns.
    """

    # User data - moderate TTL (users update profile occasionally)
    USER_PROFILE_TTL = 600  # 10 minutes

    # Authentication - short TTL (session data changes frequently)
    AUTH_SESSION_TTL = 300  # 5 minutes

    # User preferences - long TTL (rarely change)
    USER_PREFERENCES_TTL = 3600  # 1 hour

    # List operations - short TTL (data changes frequently)
    LIST_TTL = 60  # 1 minute

    # Static/reference data - very long TTL
    STATIC_DATA_TTL = 86400  # 24 hours

    @staticmethod
    def get_user_cache_key(user_id: str) -> str:
        """Generate cache key for user profile."""
        return f"user:{user_id}"

    @staticmethod
    def get_preferences_cache_key(user_id: str) -> str:
        """Generate cache key for user preferences."""
        return f"preferences:{user_id}"

    @staticmethod
    def get_auth_token_key(token_jti: str) -> str:
        """Generate cache key for JWT token blacklist."""
        return f"blacklist:{token_jti}"


async def invalidate_user_cache(user_id: str) -> None:
    """
    Invalidate all cache entries for a user.

    Call this after user updates to ensure fresh data.

    Parameters
    ----------
    user_id : str
        User ID

    Examples
    --------
    >>> # After updating user profile
    >>> await db.commit()
    >>> await invalidate_user_cache(user.id)
    """
    await cache.delete(CacheStrategy.get_user_cache_key(user_id))
    await cache.delete(CacheStrategy.get_preferences_cache_key(user_id))
