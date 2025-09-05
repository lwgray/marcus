"""
Marcus Error Handling Strategies

Advanced error handling patterns for autonomous agent environments:
- Retry policies with exponential backoff
- Circuit breaker pattern for external services
- Fallback mechanisms for graceful degradation
- Error aggregation for batch operations
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from .error_framework import (
    ErrorContext,
    ErrorSeverity,
    IntegrationError,
    MarcusBaseError,
    NetworkTimeoutError,
    TransientError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class RetryPolicy(Enum):
    """Retry policy types."""

    NONE = "none"
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    JITTERED_EXPONENTIAL = "jittered_exponential"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    multiplier: float = 2.0
    jitter: bool = True
    retry_on: tuple[type[Exception], ...] = (TransientError, IntegrationError)
    stop_on: tuple[
        type[Exception], ...
    ] = ()  # Exceptions that stop retries (empty by default)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes to close from half-open
    timeout: float = 60.0  # Seconds before trying half-open
    monitor_window: float = 300.0  # Seconds to track failures
    max_failures_per_window: int = 10


@dataclass
class CircuitBreakerStatus:
    """Current status of a circuit breaker."""

    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None
    failure_history: List[datetime] = field(default_factory=list)


class CircuitBreaker:
    """
    Circuit breaker implementation for external service calls.

    Prevents cascading failures by temporarily blocking calls to failing services.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerStatus()
        self._circuit_lock: Optional[asyncio.Lock] = None

    @property
    def lock(self) -> asyncio.Lock:
        """Get circuit breaker lock, creating it if needed in the current event loop."""
        if self._circuit_lock is None:
            self._circuit_lock = asyncio.Lock()
        return self._circuit_lock

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection."""
        async with self.lock:
            # Check if circuit should transition states
            await self._update_state()

            # Block if circuit is open
            if self.state.state == CircuitBreakerState.OPEN:
                raise IntegrationError(
                    service_name=self.name,
                    operation="circuit_breaker_open",
                    context=ErrorContext(operation=f"circuit_breaker_{self.name}"),
                    remediation={
                        "immediate_action": f"Wait for circuit breaker to close (next attempt: {self.state.next_attempt_time})",
                        "fallback_strategy": "Use cached data or alternative service",
                        "long_term_solution": "Fix underlying service issues",
                    },
                    severity=ErrorSeverity.MEDIUM,
                )

        # Execute function
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            async with self.lock:
                await self._record_success()

            return result

        except Exception as e:
            # Record failure
            async with self.lock:
                await self._record_failure(e)
            raise

    async def _update_state(self) -> None:
        """Update circuit breaker state based on current conditions."""
        now = datetime.now()

        if self.state.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed to try half-open
            if self.state.next_attempt_time and now >= self.state.next_attempt_time:
                self.state.state = CircuitBreakerState.HALF_OPEN
                self.state.success_count = 0
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")

        elif self.state.state == CircuitBreakerState.HALF_OPEN:
            # Check if enough successes to close
            if self.state.success_count >= self.config.success_threshold:
                self.state.state = CircuitBreakerState.CLOSED
                self.state.failure_count = 0
                self.state.failure_history.clear()
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")

        # Clean old failures from history
        cutoff_time = now - timedelta(seconds=self.config.monitor_window)
        self.state.failure_history = [
            failure_time
            for failure_time in self.state.failure_history
            if failure_time > cutoff_time
        ]

    async def _record_success(self) -> None:
        """Record a successful operation."""
        if self.state.state == CircuitBreakerState.HALF_OPEN:
            self.state.success_count += 1

            # Check if we should transition to CLOSED
            if self.state.success_count >= self.config.success_threshold:
                self.state.state = CircuitBreakerState.CLOSED
                self.state.failure_count = 0
                self.state.failure_history.clear()
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")

        logger.debug(f"Circuit breaker {self.name} recorded success")

    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed operation."""
        now = datetime.now()
        self.state.failure_count += 1
        self.state.last_failure_time = now
        self.state.failure_history.append(now)

        # Check if should open circuit
        if (
            self.state.state == CircuitBreakerState.CLOSED
            and self.state.failure_count >= self.config.failure_threshold
        ):
            self.state.state = CircuitBreakerState.OPEN
            self.state.next_attempt_time = now + timedelta(seconds=self.config.timeout)
            logger.warning(
                f"Circuit breaker {self.name} OPENED due to {self.state.failure_count} failures"
            )

        elif self.state.state == CircuitBreakerState.HALF_OPEN:
            # Failed while half-open, go back to open
            self.state.state = CircuitBreakerState.OPEN
            self.state.next_attempt_time = now + timedelta(seconds=self.config.timeout)
            self.state.success_count = 0
            logger.warning(f"Circuit breaker {self.name} returned to OPEN state")

        logger.debug(f"Circuit breaker {self.name} recorded failure: {exception}")


class RetryHandler:
    """
    Advanced retry handler with multiple backoff strategies.

    Supports exponential backoff, jitter, and configurable retry policies.
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        context: Optional[ErrorContext] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute function with retry logic."""
        last_exception = None
        context = context or ErrorContext()

        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if not self._should_retry(e):
                    raise e  # Non-retryable errors are raised immediately

                # Check if we should stop retrying (max attempts reached)
                if self._should_stop_retry(e, attempt):
                    break  # Exit loop to wrap in IntegrationError

                # Calculate delay and wait
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        f"Retry attempt {attempt + 1}/{self.config.max_attempts} "
                        f"after {delay:.2f}s for {context.operation}",
                        extra={
                            "correlation_id": context.correlation_id,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "exception": str(e),
                        },
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted - wrap in IntegrationError to indicate retry failure
        service_name = "unknown"
        operation = context.operation or "unknown"

        # Extract service name from NetworkTimeoutError if available
        if isinstance(last_exception, NetworkTimeoutError) and hasattr(
            last_exception, "service_name"
        ):
            service_name = last_exception.service_name
        elif isinstance(last_exception, IntegrationError):
            service_name = last_exception.service_name
            operation = last_exception.operation

        raise IntegrationError(
            service_name=service_name,
            operation=operation,
            context=context,
            remediation={
                "immediate_action": "Check service availability",
                "long_term_solution": "Implement better error handling",
                "retry_strategy": f"Already retried {self.config.max_attempts} times",
            },
            cause=last_exception,
        )

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if exception should trigger a retry."""
        # Don't retry if exception type is in stop_on list
        for stop_type in self.config.stop_on:
            if isinstance(exception, stop_type):
                return False

        # If retry_on is empty, retry on any exception not in stop_on
        if not self.config.retry_on:
            return True

        # Retry if exception type is in retry_on list
        for retry_type in self.config.retry_on:
            if isinstance(exception, retry_type):
                return True

        return False

    def _should_stop_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should stop retrying based on exception and attempt."""
        # Stop if max attempts reached
        if attempt >= self.config.max_attempts - 1:
            return True

        # Stop for certain exception types
        if isinstance(exception, MarcusBaseError) and not exception.retryable:
            return True

        return False

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt."""
        if self.config.max_attempts == 1:
            return 0

        delay = self.config.base_delay * (self.config.multiplier**attempt)
        delay = min(delay, self.config.max_delay)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            secure_random = secrets.SystemRandom()
            jitter = secure_random.uniform(0, delay * 0.1)  # 10% jitter
            delay += jitter

        return delay


class FallbackHandler:
    """
    Handles fallback strategies for graceful degradation.

    Provides multiple fallback options when primary operations fail.
    """

    def __init__(self, name: str):
        self.name = name
        self.fallback_functions: List[Tuple[int, Callable[..., Any]]] = []
        self.cache: Dict[str, Any] = {}

    def add_fallback(self, func: Callable[..., Any], priority: int = 0) -> None:
        """Add a fallback function with priority (lower = higher priority)."""
        self.fallback_functions.append((priority, func))
        self.fallback_functions.sort(key=lambda x: x[0])  # Sort by priority

    async def execute_with_fallback(
        self,
        primary_func: Callable[..., Any],
        *args: Any,
        cache_key: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute primary function with fallback options."""
        context = context or ErrorContext()

        # Try primary function
        try:
            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = primary_func(*args, **kwargs)

            # Cache successful result
            if cache_key:
                self.cache[cache_key] = result

            return result

        except Exception as primary_error:
            logger.warning(
                f"Primary function failed for {self.name}: {primary_error}",
                extra={"correlation_id": context.correlation_id},
            )

            # Try fallback functions
            for priority, fallback_func in self.fallback_functions:
                try:
                    logger.info(
                        f"Trying fallback (priority {priority}) for {self.name}",
                        extra={"correlation_id": context.correlation_id},
                    )

                    if asyncio.iscoroutinefunction(fallback_func):
                        result = await fallback_func(*args, **kwargs)
                    else:
                        result = fallback_func(*args, **kwargs)

                    logger.info(
                        f"Fallback succeeded for {self.name}",
                        extra={"correlation_id": context.correlation_id},
                    )
                    return result

                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback failed for {self.name}: {fallback_error}",
                        extra={"correlation_id": context.correlation_id},
                    )
                    continue

            # Try cached result
            if cache_key and cache_key in self.cache:
                logger.info(
                    f"Using cached result for {self.name}",
                    extra={"correlation_id": context.correlation_id},
                )
                return self.cache[cache_key]

            # All fallbacks failed, enhance original error
            if isinstance(primary_error, MarcusBaseError):
                primary_error.remediation.fallback_strategy = (
                    "All fallback strategies exhausted"
                )
                raise primary_error
            else:
                raise IntegrationError(
                    service_name=self.name,
                    operation=context.operation or "unknown",
                    context=context,
                    remediation={
                        "immediate_action": "All fallback strategies failed",
                        "long_term_solution": "Improve fallback mechanisms",
                        "escalation_path": "Contact system administrator",
                        "fallback_strategy": "All fallback strategies exhausted",
                    },
                    cause=primary_error,
                )


class ErrorAggregator:
    """
    Aggregates errors from batch operations.

    Collects multiple errors and provides summary reporting.
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.errors: List[MarcusBaseError] = []
        self.successes: int = 0
        self.total_operations: int = 0

    def add_success(self) -> None:
        """Record a successful operation."""
        self.successes += 1
        self.total_operations += 1

    def add_error(
        self, error: Exception, item_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an error to the aggregation."""
        self.total_operations += 1

        if isinstance(error, MarcusBaseError):
            # Enhance existing Marcus error with batch context
            error.context.custom_context = error.context.custom_context or {}
            error.context.custom_context.update(
                {
                    "batch_operation": self.operation_name,
                    "item_context": item_context or {},
                }
            )
            self.errors.append(error)
        else:
            # Convert regular exception to Marcus error
            marcus_error = IntegrationError(
                service_name="batch_operation",
                operation=self.operation_name,
                context=ErrorContext(
                    operation=self.operation_name,
                    custom_context={
                        "batch_operation": self.operation_name,
                        "item_context": item_context or {},
                        "original_error": str(error),
                    },
                ),
                cause=error,
            )
            self.errors.append(marcus_error)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of batch operation results."""
        error_summary: Dict[str, List[Dict[str, Any]]] = {}
        for error in self.errors:
            error_type = error.__class__.__name__
            if error_type not in error_summary:
                error_summary[error_type] = []
            error_summary[error_type].append(
                {
                    "message": error.message,
                    "correlation_id": error.context.correlation_id,
                    "item_context": (
                        error.context.custom_context.get("item_context", {})
                        if error.context.custom_context
                        else {}
                    ),
                }
            )

        return {
            "operation": self.operation_name,
            "total_operations": self.total_operations,
            "successes": self.successes,
            "errors": len(self.errors),
            "success_rate": (
                self.successes / self.total_operations
                if self.total_operations > 0
                else 0
            ),
            "error_summary": error_summary,
        }

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0

    def get_critical_errors(self) -> List[MarcusBaseError]:
        """Get only critical errors from the batch."""
        return [e for e in self.errors if e.severity == ErrorSeverity.CRITICAL]

    def raise_if_critical(self) -> None:
        """Raise exception if any critical errors were encountered."""
        critical_errors = self.get_critical_errors()
        if critical_errors:
            # Raise the first critical error with batch context
            critical_error = critical_errors[0]
            critical_error.context.custom_context = (
                critical_error.context.custom_context or {}
            )
            critical_error.context.custom_context.update(
                {
                    "critical_errors_in_batch": len(critical_errors),
                    "total_errors_in_batch": len(self.errors),
                    "batch_summary": self.get_summary(),
                }
            )
            raise critical_error


# =============================================================================
# DECORATORS FOR EASY USAGE
# =============================================================================


def with_retry(
    config: Optional[RetryConfig] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for adding retry logic to functions."""
    retry_config = config or RetryConfig()

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            retry_handler = RetryHandler(retry_config)
            context = ErrorContext(operation=func.__name__)
            return await retry_handler.execute(func, *args, context=context, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_circuit_breaker(
    name: str, config: Optional[CircuitBreakerConfig] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for adding circuit breaker protection to functions."""
    circuit_breaker = CircuitBreaker(name, config)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await circuit_breaker.call(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_fallback(
    *fallback_functions: Callable[..., Any]
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for adding fallback functions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            fallback_handler = FallbackHandler(func.__name__)

            # Add fallback functions
            for i, fallback_func in enumerate(fallback_functions):
                fallback_handler.add_fallback(fallback_func, priority=i)

            context = ErrorContext(operation=func.__name__)
            return await fallback_handler.execute_with_fallback(
                func, *args, context=context, **kwargs
            )

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# =============================================================================
# STRATEGY REGISTRY
# =============================================================================


class ErrorStrategyRegistry:
    """Registry for managing error handling strategies across the application."""

    def __init__(self) -> None:
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.fallback_handlers: Dict[str, FallbackHandler] = {}
        self.retry_configs: Dict[str, RetryConfig] = {}

    def get_circuit_breaker(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name, config)
        return self.circuit_breakers[name]

    def get_fallback_handler(self, name: str) -> FallbackHandler:
        """Get or create a fallback handler."""
        if name not in self.fallback_handlers:
            self.fallback_handlers[name] = FallbackHandler(name)
        return self.fallback_handlers[name]

    def register_retry_config(self, operation: str, config: RetryConfig) -> None:
        """Register a retry configuration for an operation."""
        self.retry_configs[operation] = config

    def get_retry_config(self, operation: str) -> RetryConfig:
        """Get retry configuration for an operation."""
        return self.retry_configs.get(operation, RetryConfig())

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all circuit breakers."""
        status = {}
        for name, cb in self.circuit_breakers.items():
            status[name] = {
                "state": cb.state.state.value,
                "failure_count": cb.state.failure_count,
                "last_failure": (
                    cb.state.last_failure_time.isoformat()
                    if cb.state.last_failure_time
                    else None
                ),
                "next_attempt": (
                    cb.state.next_attempt_time.isoformat()
                    if cb.state.next_attempt_time
                    else None
                ),
            }
        return status


# Global registry instance
error_strategy_registry: ErrorStrategyRegistry = ErrorStrategyRegistry()
