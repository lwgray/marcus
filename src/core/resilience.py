"""
Resilience patterns for Marcus enhanced features.

Provides decorators and utilities for graceful degradation, circuit breakers,
and retry logic to ensure Marcus continues working even when components fail.
"""

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: type = Exception


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open

    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        if self.state == "open":
            # Check if we should try half-open
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed > self.config.recovery_timeout:
                    self.state = "half-open"
                    return False
            return True
        return False

    def record_success(self) -> None:
        """Record successful call."""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.config.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker '{self.name}' opened after "
                f"{self.failure_count} failures"
            )


# Global circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def with_fallback(
    fallback_func: Callable[..., Any], log_errors: bool = True
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Add graceful degradation with fallback function.

    Example
    -------
    @with_fallback(use_memory_storage)
    async def store_to_database(data):
        await db.store(data)
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.warning(f"{func.__name__} failed: {e}, using fallback")
                if asyncio.iscoroutinefunction(fallback_func):
                    return await fallback_func(*args, **kwargs)
                return fallback_func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.warning(f"{func.__name__} failed: {e}, using fallback")
                return fallback_func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def with_retry(
    config: Optional[RetryConfig] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Add retry logic with exponential backoff.

    Example
    -------
    @with_retry(RetryConfig(max_attempts=5))
    async def call_external_api():
        return await api.call()
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        # Last attempt, don't retry
                        break

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )

                    # Add jitter if enabled
                    if config.jitter:
                        # Use cryptographically secure random for jitter
                        secure_random = secrets.SystemRandom()
                        delay *= 0.5 + secure_random.random()

                    logger.debug(
                        f"{func.__name__} attempt {attempt + 1} failed, "
                        f"retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

            logger.error(f"{func.__name__} failed after {config.max_attempts} attempts")
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("No exception captured")

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt == config.max_attempts - 1:
                        break

                    delay = min(
                        config.base_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )

                    if config.jitter:
                        # Use cryptographically secure random for jitter
                        secure_random = secrets.SystemRandom()
                        delay *= 0.5 + secure_random.random()

                    logger.debug(
                        f"{func.__name__} attempt {attempt + 1} failed, "
                        f"retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            logger.error(f"{func.__name__} failed after {config.max_attempts} attempts")
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("No exception captured")

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def with_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Add circuit breaker pattern.

    Example
    -------
    @with_circuit_breaker("external_api")
    async def call_external_api():
        return await api.call()
    """
    if config is None:
        config = CircuitBreakerConfig()

    # Get or create circuit breaker
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    breaker = _circuit_breakers[name]

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if breaker.is_open():
                raise Exception(f"Circuit breaker '{name}' is open")

            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                if isinstance(e, config.expected_exception):
                    breaker.record_failure()
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if breaker.is_open():
                raise Exception(f"Circuit breaker '{name}' is open")

            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                if isinstance(e, config.expected_exception):
                    breaker.record_failure()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class GracefulDegradation:
    """Context manager for graceful degradation.

    Example
    -------
    async with GracefulDegradation(fallback=use_cache) as gd:
        result = await gd.try_primary(fetch_from_database)
        if not result:
            result = await gd.fallback()
    """

    def __init__(
        self,
        primary: Optional[Callable[..., Any]] = None,
        fallback: Optional[Callable[..., Any]] = None,
        log_errors: bool = True,
    ):
        self.primary = primary
        self.fallback = fallback
        self.log_errors = log_errors
        self._primary_failed = False
        self._primary_exception: Optional[Exception] = None

    async def __aenter__(self) -> "GracefulDegradation":
        """Enter async context manager."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Exit async context manager."""
        return False

    async def try_primary(
        self, func: Optional[Callable[..., Any]] = None, *args: Any, **kwargs: Any
    ) -> Any:
        """Try the primary function."""
        if func is None:
            func = self.primary

        if func is None:
            raise ValueError("No primary function provided")

        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            self._primary_failed = True
            self._primary_exception = e
            if self.log_errors:
                logger.warning(f"Primary function failed: {e}")
            return None

    async def use_fallback(self, *args: Any, **kwargs: Any) -> Any:
        """Use the fallback function."""
        if self.fallback is None:
            raise ValueError("No fallback function provided")

        if asyncio.iscoroutinefunction(self.fallback):
            return await self.fallback(*args, **kwargs)
        return self.fallback(*args, **kwargs)


# Pre-configured decorators for common use cases
resilient_persistence = with_fallback(
    lambda *args, **kwargs: logger.warning("Persistence unavailable, data not saved"),
    log_errors=True,
)

resilient_external_call = with_retry(RetryConfig(max_attempts=3, base_delay=1.0))

resilient_ai_call = with_circuit_breaker(
    "ai_provider", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
)
