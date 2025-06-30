# Marcus Error Handling Framework

## Overview

The Marcus Error Handling Framework provides a comprehensive, structured approach to error management in autonomous agent environments. It includes custom exception hierarchies, intelligent retry strategies, circuit breaker patterns, fallback mechanisms, and real-time error monitoring.

## Key Features

- **Structured Exception Hierarchy**: Domain-specific error types with rich context
- **Intelligent Retry Strategies**: Exponential backoff, jitter, and configurable policies  
- **Circuit Breaker Pattern**: Prevents cascading failures from external services
- **Fallback Mechanisms**: Graceful degradation when primary operations fail
- **Error Monitoring**: Real-time pattern detection and health monitoring
- **Rich Context**: Comprehensive error context for autonomous agent debugging
- **Multiple Response Formats**: MCP, JSON API, user-friendly, logging formats

## Architecture

```
Marcus Error Framework
├── Core Framework (error_framework.py)
│   ├── Exception Hierarchy
│   ├── Error Context System
│   └── Remediation Suggestions
├── Error Strategies (error_strategies.py)
│   ├── Retry Handlers
│   ├── Circuit Breakers
│   ├── Fallback Handlers
│   └── Error Aggregation
├── Response Formatting (error_responses.py)
│   ├── MCP Protocol Format
│   ├── JSON API Format
│   ├── User-Friendly Format
│   └── Logging Format
└── Monitoring System (error_monitoring.py)
    ├── Pattern Detection
    ├── Correlation Tracking
    ├── Health Monitoring
    └── Alert System
```

## Error Type Hierarchy

### Base Error Classes

```python
MarcusBaseError (base)
├── TransientError (auto-retryable)
│   ├── NetworkTimeoutError
│   ├── ServiceUnavailableError
│   ├── RateLimitError
│   └── TemporaryResourceError
├── ConfigurationError (user-fixable)
│   ├── MissingCredentialsError
│   ├── InvalidConfigurationError
│   ├── MissingDependencyError
│   └── EnvironmentError
├── BusinessLogicError (logic violations)
│   ├── TaskAssignmentError
│   ├── WorkflowViolationError
│   ├── ValidationError
│   └── StateConflictError
├── IntegrationError (external services)
│   ├── KanbanIntegrationError
│   ├── AIProviderError
│   ├── AuthenticationError
│   └── ExternalServiceError
├── SecurityError (critical security)
│   ├── AuthorizationError
│   ├── WorkspaceSecurityError
│   └── PermissionError
└── SystemError (critical system)
    ├── ResourceExhaustionError
    ├── CorruptedStateError
    ├── DatabaseError
    └── CriticalDependencyError
```

## Quick Start

### Basic Error Usage

```python
from src.core.error_framework import (
    NetworkTimeoutError, ErrorContext, RemediationSuggestion
)

# Create error with context
context = ErrorContext(
    operation="kanban_sync",
    agent_id="agent_123",
    task_id="task_456"
)

remediation = RemediationSuggestion(
    immediate_action="Retry connection to Kanban service",
    fallback_strategy="Use cached task data",
    long_term_solution="Check Kanban service health"
)

raise NetworkTimeoutError(
    service_name="planka_board",
    timeout_seconds=30,
    context=context,
    remediation=remediation
)
```

### Using Error Context Manager

```python
from src.core.error_framework import error_context

with error_context("sync_tasks", agent_id="agent_123", task_id="task_456"):
    # Any errors raised here will automatically include context
    sync_task_with_kanban()
```

### Retry Strategies

```python
from src.core.error_strategies import RetryHandler, RetryConfig

# Configure retry behavior
config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=60.0,
    multiplier=2.0,
    jitter=True
)

retry_handler = RetryHandler(config)

# Execute with retry
result = await retry_handler.execute(
    sync_with_external_service,
    context=ErrorContext(operation="external_sync")
)
```

### Circuit Breaker Pattern

```python
from src.core.error_strategies import CircuitBreaker, CircuitBreakerConfig

# Configure circuit breaker
config = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=2,
    timeout=60.0
)

circuit_breaker = CircuitBreaker("kanban_service", config)

# Execute with circuit breaker protection
result = await circuit_breaker.call(call_kanban_api)
```

### Fallback Mechanisms

```python
from src.core.error_strategies import FallbackHandler

fallback_handler = FallbackHandler("task_creation")

# Add fallback functions in priority order
fallback_handler.add_fallback(create_task_locally, priority=1)
fallback_handler.add_fallback(queue_for_later, priority=2)

# Execute with fallbacks
result = await fallback_handler.execute_with_fallback(
    create_task_on_kanban,
    task_data,
    cache_key="task_123"
)
```

### Error Response Formatting

```python
from src.core.error_responses import (
    ErrorResponseFormatter, ResponseFormat, create_error_response
)

# Format for MCP protocol
mcp_response = create_error_response(error, ResponseFormat.MCP)

# Format for user display
user_response = create_error_response(error, ResponseFormat.USER_FRIENDLY)

# Format for logging
log_response = create_error_response(error, ResponseFormat.LOGGING)
```

### Error Monitoring

```python
from src.core.error_monitoring import setup_error_monitoring, record_error_for_monitoring

# Setup monitoring with alerts
def alert_callback(pattern):
    print(f"Error pattern detected: {pattern.description}")

monitor = setup_error_monitoring(
    storage_path="logs/error_monitoring.json",
    enable_patterns=True,
    alert_callback=alert_callback
)

# Record errors for monitoring
record_error_for_monitoring(error)

# Get health status
health = monitor.generate_health_report()
print(f"System health: {health['health_status']} ({health['health_score']}/100)")
```

## Decorators for Easy Usage

### Retry Decorator

```python
from src.core.error_strategies import with_retry, RetryConfig

@with_retry(RetryConfig(max_attempts=3, base_delay=2.0))
async def sync_task_data():
    # Function will be retried on transient errors
    pass
```

### Circuit Breaker Decorator

```python
from src.core.error_strategies import with_circuit_breaker, CircuitBreakerConfig

@with_circuit_breaker("ai_service", CircuitBreakerConfig(failure_threshold=3))
async def call_ai_provider():
    # Function protected by circuit breaker
    pass
```

### Fallback Decorator

```python
from src.core.error_strategies import with_fallback

async def fallback_analysis():
    return {"confidence": 0.1, "result": "fallback_analysis"}

@with_fallback(fallback_analysis)
async def ai_analysis():
    # Primary analysis with fallback
    pass
```

## Error Categories and Handling

### Transient Errors (Auto-retryable)
- **When**: Temporary service outages, network timeouts, rate limits
- **Behavior**: Automatically retried with exponential backoff
- **Examples**: `NetworkTimeoutError`, `ServiceUnavailableError`, `RateLimitError`

### Configuration Errors (User-fixable)
- **When**: Missing credentials, invalid configuration, environment issues
- **Behavior**: Not retried, requires user intervention
- **Examples**: `MissingCredentialsError`, `InvalidConfigurationError`

### Business Logic Errors (Logic violations)
- **When**: Workflow violations, validation failures, state conflicts
- **Behavior**: Not retried, indicates logic issues
- **Examples**: `TaskAssignmentError`, `ValidationError`

### Integration Errors (External services)
- **When**: External service failures, API errors, authentication issues
- **Behavior**: Retryable with circuit breaker protection
- **Examples**: `KanbanIntegrationError`, `AIProviderError`

### Security Errors (Critical security)
- **When**: Authorization failures, permission violations, security breaches
- **Behavior**: Not retried, immediate escalation
- **Examples**: `AuthorizationError`, `WorkspaceSecurityError`

### System Errors (Critical system)
- **When**: Resource exhaustion, database failures, critical dependencies
- **Behavior**: Not retried, requires system intervention
- **Examples**: `ResourceExhaustionError`, `DatabaseError`

## Error Context System

### Context Information
- **Operation Context**: What operation was being performed
- **Agent Context**: Which agent, current task, agent state
- **System Context**: Resource usage, configuration state
- **Integration Context**: External service states
- **Correlation ID**: For tracing across operations
- **Timestamp**: When error occurred
- **Custom Context**: Additional context specific to operation

### Using Error Context

```python
# Manual context creation
context = ErrorContext(
    operation="task_assignment",
    agent_id="agent_123",
    task_id="task_456",
    integration_name="planka_board",
    custom_context={
        "board_id": "board_789",
        "user_id": "user_abc"
    }
)

# Context manager (automatic context injection)
with error_context("task_assignment", agent_id="agent_123"):
    assign_task_to_agent()
```

## Response Formats

### MCP Protocol Format
```json
{
  "success": false,
  "error": {
    "code": "KANBAN_INTEGRATION_ERROR",
    "message": "Failed to create task on Kanban board",
    "type": "KanbanIntegrationError",
    "severity": "medium",
    "retryable": true,
    "context": {
      "operation": "create_task",
      "agent_id": "agent_123",
      "correlation_id": "corr_456"
    },
    "remediation": {
      "immediate": "Retry task creation",
      "fallback": "Create task locally"
    }
  }
}
```

### User-Friendly Format
```
Unable to create task on Kanban board due to connection timeout.

💡 What to do: Retry task creation in 30 seconds
🔄 Alternative: Task will be created locally and synced later
```

## Monitoring and Alerting

### Pattern Detection
- **Frequency Patterns**: Same error occurring repeatedly
- **Burst Patterns**: Many errors in short time period
- **Agent Patterns**: High error rate from specific agent
- **Cascade Patterns**: Related errors occurring in sequence

### Health Monitoring
- **Health Score**: 0-100 based on error rates and patterns
- **Health Status**: Excellent, Good, Fair, Poor, Critical
- **Recommendations**: Automated suggestions for improvement

### Alert Configuration
```python
def custom_alert_handler(pattern):
    if pattern.severity == AlertSeverity.CRITICAL:
        send_slack_alert(pattern)
    elif pattern.severity == AlertSeverity.ERROR:
        log_to_monitoring_system(pattern)

monitor.add_alert_callback(custom_alert_handler)
```

## Best Practices

### Error Creation
1. **Use appropriate error types** for the situation
2. **Provide rich context** with operation, agent, and task information
3. **Include actionable remediation** suggestions
4. **Set appropriate severity** levels
5. **Use correlation IDs** for tracing related operations

### Error Handling
1. **Let transient errors retry** automatically
2. **Use circuit breakers** for external service calls
3. **Implement fallbacks** for critical operations
4. **Log errors appropriately** for debugging
5. **Monitor error patterns** for system health

### Performance Considerations
1. **Avoid excessive retries** that could amplify problems
2. **Use jitter** in retry delays to prevent thundering herd
3. **Set reasonable timeouts** for circuit breakers
4. **Limit error history** to prevent memory issues
5. **Batch error operations** when possible

## Integration with Existing Code

### MCP Tools Integration
```python
from src.core.error_responses import handle_mcp_tool_error

async def mcp_tool_function(arguments):
    try:
        # Tool implementation
        return {"success": True, "result": result}
    except Exception as e:
        return handle_mcp_tool_error(e, "tool_name", arguments)
```

### Legacy Error Conversion
```python
from src.core.error_framework import ExternalServiceError, ErrorContext

try:
    legacy_function()
except Exception as e:
    # Convert legacy exception to Marcus error
    raise ExternalServiceError(
        service_name="legacy_service",
        error_details=str(e),
        context=ErrorContext(operation="legacy_operation"),
        cause=e
    )
```

## Configuration

### Environment Variables
```bash
# Error monitoring
MARCUS_ERROR_MONITORING_ENABLED=true
MARCUS_ERROR_STORAGE_PATH=logs/error_monitoring.json
MARCUS_ERROR_PATTERN_DETECTION=true

# Retry configuration
MARCUS_DEFAULT_MAX_RETRIES=3
MARCUS_DEFAULT_BASE_DELAY=1.0
MARCUS_DEFAULT_MAX_DELAY=60.0

# Circuit breaker configuration
MARCUS_CIRCUIT_BREAKER_ENABLED=true
MARCUS_DEFAULT_FAILURE_THRESHOLD=5
MARCUS_DEFAULT_SUCCESS_THRESHOLD=2
```

### Runtime Configuration
```python
from src.core.error_strategies import error_strategy_registry

# Register custom retry config for specific operations
error_strategy_registry.register_retry_config(
    "critical_operation",
    RetryConfig(max_attempts=5, base_delay=2.0)
)

# Get circuit breaker for service
kanban_cb = error_strategy_registry.get_circuit_breaker(
    "kanban_service",
    CircuitBreakerConfig(failure_threshold=3)
)
```

## Troubleshooting

### Common Issues

1. **High Error Rates**
   - Check recent deployments or configuration changes
   - Review error patterns for common root causes
   - Monitor external service health

2. **Circuit Breakers Opening**
   - Verify external service availability
   - Check authentication credentials
   - Review service rate limits

3. **Retry Loops**
   - Ensure error types are correctly classified
   - Check retry configuration for appropriate limits
   - Monitor for non-retryable errors being retried

4. **Missing Error Context**
   - Use error context managers for automatic context injection
   - Ensure context is passed through call chains
   - Add custom context for domain-specific information

### Debugging Tools

```python
# Get detailed error information
error_details = error_monitor.get_error_details(correlation_id)

# Search for related errors
related_errors = error_monitor.search_errors(
    agent_id="agent_123",
    hours=24
)

# Get system health
health_report = error_monitor.generate_health_report()

# Check circuit breaker status
cb_status = error_strategy_registry.get_health_status()
```

## Examples

See the `tests/unit/core/` directory for comprehensive examples of:
- Error creation and handling
- Retry strategies and circuit breakers  
- Fallback mechanisms
- Error monitoring and pattern detection
- Response formatting for different contexts

## Migration Guide

### From Legacy Error Handling

1. **Replace generic Exception handling** with specific Marcus error types
2. **Add error context** to all error creation points
3. **Implement retry strategies** for transient operations
4. **Add circuit breakers** for external service calls
5. **Convert error responses** to use standard formatting

### Example Migration

**Before:**
```python
try:
    call_external_service()
except Exception as e:
    return {"success": False, "error": str(e)}
```

**After:**
```python
from src.core.error_framework import error_context
from src.core.error_strategies import with_retry, with_circuit_breaker
from src.core.error_responses import create_error_response, ResponseFormat

@with_retry()
@with_circuit_breaker("external_service")
async def call_external_service_safe():
    with error_context("external_call", agent_id=current_agent_id):
        return await call_external_service()

try:
    result = await call_external_service_safe()
    return {"success": True, "result": result}
except Exception as e:
    return create_error_response(e, ResponseFormat.MCP)
```