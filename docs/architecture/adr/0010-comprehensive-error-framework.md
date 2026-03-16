# ADR 0010: Comprehensive Error Handling Framework

**Status:** Accepted

**Date:** 2024-11 (Post-MVP Enhancement)

**Deciders:** Marcus Core Team

---

## Context

Marcus integrates with multiple external systems and coordinates complex multi-agent workflows. Robust error handling is critical for:

### Requirements

1. **User-Friendly Errors:** Clear, actionable error messages
2. **Context Preservation:** Know what was happening when error occurred
3. **Retry Logic:** Automatic recovery from transient failures
4. **Circuit Breaking:** Prevent cascade failures
5. **Error Tracking:** Monitor patterns for debugging
6. **Structured Responses:** Consistent error format for MCP tools
7. **Developer Experience:** Easy to add proper error handling

### Common Error Scenarios

- **External Service Failures:** Kanban API down, AI service timeout
- **Configuration Issues:** Missing API keys, invalid settings
- **Business Logic Violations:** Invalid task dependencies, lease expiry
- **Resource Exhaustion:** Memory limits, database locks
- **Network Problems:** Timeouts, connection refused
- **Security Violations:** Unauthorized access, invalid credentials

### Problems with Generic Exceptions

```python
# ❌ Bad - generic exceptions
try:
    await kanban.create_card(task)
except Exception as e:
    # What went wrong? Network? Auth? Invalid data?
    # How should we retry? Should we retry at all?
    # What should we tell the user?
    return {"error": str(e)}  # Unhelpful!
```

---

## Decision

We will implement a **Comprehensive Error Handling Framework** with four layers:

1. **Custom Exception Hierarchy** - Domain-specific exceptions
2. **Error Strategies** - Retry, circuit breaker, fallback patterns
3. **Error Responses** - Structured error serialization
4. **Error Monitoring** - Pattern detection and tracking

---

## Implementation

### Layer 1: Custom Exception Hierarchy

```python
# src/core/error_framework.py

class MarcusBaseError(Exception):
    """Base exception for all Marcus errors"""

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext()
        self.recoverable = recoverable
        self.timestamp = datetime.now()

@dataclass
class ErrorContext:
    """Rich context for error reporting"""
    operation: str = ""
    project_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    additional_info: dict = field(default_factory=dict)

# Integration Errors (External Services)
class KanbanIntegrationError(MarcusBaseError):
    """Kanban provider integration failed"""

    def __init__(
        self,
        board_name: str,
        operation: str,
        original_error: Exception | None = None,
        context: ErrorContext | None = None
    ):
        message = f"Kanban operation '{operation}' failed on board '{board_name}'"
        if original_error:
            message += f": {str(original_error)}"

        super().__init__(
            message=message,
            context=context,
            recoverable=True  # Network errors are often transient
        )
        self.board_name = board_name
        self.operation = operation
        self.original_error = original_error

class AIProviderError(MarcusBaseError):
    """AI/LLM provider error"""

    def __init__(
        self,
        provider: str,
        operation: str,
        original_error: Exception | None = None,
        context: ErrorContext | None = None
    ):
        message = f"AI provider '{provider}' failed: {operation}"
        super().__init__(
            message=message,
            context=context,
            recoverable=True
        )
        self.provider = provider
        self.operation = operation

# Configuration Errors (Not Recoverable)
class MissingCredentialsError(MarcusBaseError):
    """Required credentials not found"""

    def __init__(
        self,
        service_name: str,
        credential_type: str
    ):
        super().__init__(
            message=f"Missing {credential_type} for {service_name}",
            recoverable=False  # Can't recover without config fix
        )
        self.service_name = service_name
        self.credential_type = credential_type

class InvalidConfigurationError(MarcusBaseError):
    """Configuration is invalid"""

    def __init__(self, config_key: str, reason: str):
        super().__init__(
            message=f"Invalid configuration for '{config_key}': {reason}",
            recoverable=False
        )
        self.config_key = config_key
        self.reason = reason

# Business Logic Errors
class TaskAssignmentError(MarcusBaseError):
    """Task assignment failed"""

    def __init__(
        self,
        task_id: str,
        agent_id: str,
        reason: str,
        context: ErrorContext | None = None
    ):
        super().__init__(
            message=f"Cannot assign task {task_id} to agent {agent_id}: {reason}",
            context=context,
            recoverable=False  # Business logic violations aren't retryable
        )
        self.task_id = task_id
        self.agent_id = agent_id
        self.reason = reason

class LeaseExpiredError(MarcusBaseError):
    """Task lease has expired"""

    def __init__(self, task_id: str, agent_id: str):
        super().__init__(
            message=f"Lease expired for task {task_id} assigned to {agent_id}",
            recoverable=True  # Can reassign
        )
        self.task_id = task_id
        self.agent_id = agent_id

# Resource Errors
class ResourceExhaustedError(MarcusBaseError):
    """System resources exhausted"""

    def __init__(self, resource_type: str, current: float, limit: float):
        super().__init__(
            message=f"{resource_type} exhausted: {current}/{limit}",
            recoverable=True  # May recover after cleanup
        )
        self.resource_type = resource_type
        self.current = current
        self.limit = limit

# Security Errors
class UnauthorizedError(MarcusBaseError):
    """Unauthorized access attempt"""

    def __init__(self, operation: str, resource: str):
        super().__init__(
            message=f"Unauthorized: {operation} on {resource}",
            recoverable=False  # Don't retry auth failures
        )
        self.operation = operation
        self.resource = resource
```

### Layer 2: Error Strategies

```python
# src/core/error_strategies.py

from functools import wraps
from typing import Callable, TypeVar, ParamSpec

P = ParamSpec("P")
T = TypeVar("T")

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

def with_retry(config: RetryConfig):
    """Decorator for automatic retry with exponential backoff"""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error = None

            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)

                except MarcusBaseError as e:
                    last_error = e

                    # Don't retry non-recoverable errors
                    if not e.recoverable:
                        raise

                    # Don't retry on last attempt
                    if attempt == config.max_attempts - 1:
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but for type safety
            raise last_error or RuntimeError("Retry loop failed unexpectedly")

        return wrapper
    return decorator

# Circuit Breaker Pattern
class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._state: Literal["closed", "open", "half_open"] = "closed"

    async def call(self, func: Callable[P, Awaitable[T]], *args: P.args, **kwargs: P.kwargs) -> T:
        """Execute function with circuit breaker protection"""

        # Check if circuit is open
        if self._state == "open":
            if self._should_attempt_reset():
                self._state = "half_open"
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open for {func.__name__}"
                )

        try:
            result = await func(*args, **kwargs)

            # Success - reset if in half-open state
            if self._state == "half_open":
                self._reset()

            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

    def _record_failure(self):
        """Record a failure"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            logger.error(f"Circuit breaker opened after {self._failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        if not self._last_failure_time:
            return True

        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _reset(self):
        """Reset circuit breaker to closed state"""
        self._failure_count = 0
        self._last_failure_time = None
        self._state = "closed"
        logger.info("Circuit breaker closed - service recovered")

# Decorator for circuit breaker
def with_circuit_breaker(name: str):
    """Decorator for circuit breaker protection"""
    breaker = CircuitBreaker()

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

# Fallback Pattern
def with_fallback(fallback_func: Callable[P, Awaitable[T]]):
    """Decorator for fallback on error"""

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except MarcusBaseError as e:
                if e.recoverable:
                    logger.warning(f"Primary function failed, using fallback: {e}")
                    return await fallback_func(*args, **kwargs)
                raise
        return wrapper
    return decorator
```

### Layer 3: Error Responses

```python
# src/core/error_responses.py

from enum import Enum

class ResponseFormat(Enum):
    """Error response format"""
    MCP_TOOL = "mcp_tool"     # For MCP tool responses
    JSON_API = "json_api"      # For HTTP API responses
    CLI = "cli"                # For CLI output

def create_error_response(
    error: Exception,
    format: ResponseFormat = ResponseFormat.MCP_TOOL,
    include_trace: bool = False
) -> dict:
    """Create structured error response"""

    if isinstance(error, MarcusBaseError):
        response = {
            "success": False,
            "error": {
                "type": type(error).__name__,
                "message": error.message,
                "recoverable": error.recoverable,
                "timestamp": error.timestamp.isoformat(),
            }
        }

        # Add context if available
        if error.context:
            response["error"]["context"] = {
                "operation": error.context.operation,
                "project_id": error.context.project_id,
                "task_id": error.context.task_id,
                "agent_id": error.context.agent_id,
                **error.context.additional_info
            }

        # Add specific error fields
        if isinstance(error, KanbanIntegrationError):
            response["error"]["board_name"] = error.board_name
            response["error"]["operation"] = error.operation

        if isinstance(error, TaskAssignmentError):
            response["error"]["task_id"] = error.task_id
            response["error"]["agent_id"] = error.agent_id

    else:
        # Generic error
        response = {
            "success": False,
            "error": {
                "type": "UnknownError",
                "message": str(error),
                "recoverable": False
            }
        }

    # Add stack trace for debugging (development only)
    if include_trace:
        import traceback
        response["error"]["trace"] = traceback.format_exc()

    return response

def handle_mcp_tool_error(
    error: Exception,
    tool_name: str,
    arguments: dict
) -> dict:
    """Standard error handler for MCP tools"""

    logger.error(
        f"Error in MCP tool '{tool_name}': {error}",
        extra={"tool": tool_name, "arguments": arguments}
    )

    # Record for monitoring
    record_error_for_monitoring(error)

    # Create response
    response = create_error_response(error, ResponseFormat.MCP_TOOL)

    # Add tool-specific context
    response["tool"] = tool_name
    response["arguments"] = arguments

    return response
```

### Layer 4: Error Monitoring

```python
# src/core/error_monitoring.py

from collections import defaultdict
from typing import Counter as CounterType

class ErrorMonitor:
    """Monitor and track error patterns"""

    def __init__(self):
        self._error_counts: CounterType[str] = Counter()
        self._error_history: list[tuple[datetime, Exception]] = []
        self._max_history = 1000

    def record_error(self, error: Exception):
        """Record an error for monitoring"""
        error_type = type(error).__name__

        # Update counts
        self._error_counts[error_type] += 1

        # Add to history
        self._error_history.append((datetime.now(), error))

        # Trim history if too large
        if len(self._error_history) > self._max_history:
            self._error_history = self._error_history[-self._max_history:]

        # Check for error spikes
        self._check_error_spike(error_type)

    def _check_error_spike(self, error_type: str):
        """Detect error spikes"""
        # Count recent errors of this type
        now = datetime.now()
        recent_window = timedelta(minutes=5)
        recent_count = sum(
            1 for timestamp, error in self._error_history
            if (now - timestamp) < recent_window
            and type(error).__name__ == error_type
        )

        # Alert if spike detected
        if recent_count > 10:
            logger.critical(
                f"Error spike detected: {error_type} occurred {recent_count} times "
                f"in last 5 minutes"
            )

    def get_error_summary(self) -> dict:
        """Get summary of errors"""
        return {
            "total_errors": len(self._error_history),
            "error_counts": dict(self._error_counts),
            "most_common": self._error_counts.most_common(5)
        }

# Global monitor instance
_error_monitor = ErrorMonitor()

def record_error_for_monitoring(error: Exception):
    """Record error for monitoring"""
    _error_monitor.record_error(error)

def get_error_summary() -> dict:
    """Get error monitoring summary"""
    return _error_monitor.get_error_summary()
```

---

## Usage Examples

### External Service Call with Retry

```python
@with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
@with_circuit_breaker("kanban_service")
async def sync_task_to_kanban(task: Task):
    """Sync task to Kanban board with retry and circuit breaker"""
    try:
        await kanban_provider.create_card(
            title=task.title,
            description=task.description
        )
    except httpx.TimeoutError as e:
        raise KanbanIntegrationError(
            board_name=task.project_id,
            operation="create_card",
            original_error=e,
            context=ErrorContext(
                operation="sync_task",
                task_id=task.id,
                project_id=task.project_id
            )
        )
```

### MCP Tool with Error Handling

```python
@server.call_tool()
async def assign_task(agent_id: str, task_id: str) -> dict:
    """Assign task to agent with proper error handling"""
    try:
        # Business logic
        assignment = await task_manager.assign_task(
            task_id=task_id,
            agent_id=agent_id
        )

        return {
            "success": True,
            "assignment": assignment.to_dict()
        }

    except Exception as e:
        return handle_mcp_tool_error(e, "assign_task", locals())
```

---

## Consequences

### Positive

✅ **Clear Error Messages**
- Users know what went wrong
- Actionable error information
- Rich context for debugging

✅ **Automatic Recovery**
- Retry transient failures
- Circuit breaker prevents cascades
- Fallback patterns for resilience

✅ **Better Monitoring**
- Track error patterns
- Detect spikes early
- Inform operational decisions

✅ **Developer Experience**
- Easy to add error handling
- Type-safe error responses
- Comprehensive documentation

✅ **Structured Responses**
- Consistent error format
- Machine-readable
- Client-friendly

### Negative

⚠️ **Increased Complexity**
- More code to maintain
- Learning curve for contributors

⚠️ **Performance Overhead**
- Retry delays
- Circuit breaker checks
- Monitoring overhead

---

## Related Decisions

- [ADR-0004: Async-First Design](./0004-async-first-design.md)
- [ADR-0006: Kanban Provider Abstraction](./0006-kanban-provider-abstraction.md)
- [ADR-0007: AI Provider Abstraction](./0007-ai-provider-abstraction.md)

---

## References

- [Resilience4j Patterns](https://resilience4j.readme.io/)
- [Release It! by Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/)

---

## Notes

This framework has dramatically improved Marcus's reliability and observability. Error rates have dropped, and when errors do occur, they're easy to diagnose and fix.
