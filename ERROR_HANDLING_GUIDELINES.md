# Marcus Error Handling Guidelines

## When to Use Marcus Error Framework vs Regular Exceptions

### ALWAYS Use Marcus Error Framework For:

#### 1. **External Service Interactions**
```python
# ✅ CORRECT - Use Marcus errors for external services
from src.core.error_framework import KanbanIntegrationError, AIProviderError

try:
    response = await kanban_client.create_task(task_data)
except httpx.TimeoutException:
    raise KanbanIntegrationError(
        board_name=board_name,
        operation="create_task",
        context=ErrorContext(operation="task_creation", agent_id=agent_id)
    )

# ❌ WRONG - Don't use generic exceptions
try:
    response = await kanban_client.create_task(task_data)
except httpx.TimeoutException as e:
    raise Exception(f"Kanban failed: {e}")
```

#### 2. **Agent Task Operations**
```python
# ✅ CORRECT - Use TaskAssignmentError for agent operations
from src.core.error_framework import TaskAssignmentError

if not agent.can_handle_task(task):
    raise TaskAssignmentError(
        task_id=task.id,
        agent_id=agent.id,
        reason="Agent lacks required skills",
        context=ErrorContext(operation="task_assignment")
    )

# ❌ WRONG - Don't use ValueError for business logic
if not agent.can_handle_task(task):
    raise ValueError("Agent can't handle task")
```

#### 3. **Configuration and Authentication Issues**
```python
# ✅ CORRECT - Use configuration errors
from src.core.error_framework import MissingCredentialsError

if not os.getenv('KANBAN_API_KEY'):
    raise MissingCredentialsError(
        service_name="kanban",
        credential_type="API key",
        context=ErrorContext(operation="kanban_init")
    )

# ❌ WRONG - Don't use generic exceptions
if not os.getenv('KANBAN_API_KEY'):
    raise Exception("Missing API key")
```

#### 4. **Resource and System Issues**
```python
# ✅ CORRECT - Use system errors
from src.core.error_framework import ResourceExhaustionError

if memory_usage > 0.95:
    raise ResourceExhaustionError(
        resource_type="memory",
        current_usage="95%",
        context=ErrorContext(operation="task_processing")
    )
```

#### 5. **Security Violations**
```python
# ✅ CORRECT - Use security errors
from src.core.error_framework import WorkspaceSecurityError

if not is_path_allowed(file_path):
    raise WorkspaceSecurityError(
        path=file_path,
        violation_type="unauthorized_access",
        context=ErrorContext(operation="file_access", agent_id=agent_id)
    )
```

### Use Regular Exceptions For:

#### 1. **Programming Errors (Internal Logic)**
```python
# ✅ CORRECT - Use ValueError for input validation
def validate_task_priority(priority):
    if priority not in ['low', 'medium', 'high']:
        raise ValueError(f"Invalid priority: {priority}")

# ✅ CORRECT - Use TypeError for type issues
def process_task(task):
    if not isinstance(task, Task):
        raise TypeError(f"Expected Task object, got {type(task)}")
```

#### 2. **Library-Specific Exceptions (Let them bubble up)**
```python
# ✅ CORRECT - Let library exceptions bubble up with context
try:
    data = json.loads(response_text)
except json.JSONDecodeError as e:
    # Add context then re-raise as Marcus error if needed for user-facing operations
    raise ExternalServiceError(
        service_name="api_service",
        error_details=f"Invalid JSON response: {e}",
        cause=e
    )
```

#### 3. **Standard Python Errors (When Appropriate)**
```python
# ✅ CORRECT - Use KeyError for missing dict keys (internal)
def get_required_field(data, field):
    try:
        return data[field]
    except KeyError:
        raise KeyError(f"Required field '{field}' missing from data")

# ✅ CORRECT - Use FileNotFoundError for file operations (internal)
def read_config_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # For user-facing operations, convert to Marcus error
        raise ConfigurationError(
            config_key="config_file",
            expected_format=f"File at {path}"
        )
```

## Error Context Guidelines

### ALWAYS Include Context For:

#### 1. **Operation Information**
```python
context = ErrorContext(
    operation="sync_kanban_tasks",      # What operation failed
    agent_id="agent_123",               # Which agent was involved
    task_id="task_456",                 # Specific task being processed
    integration_name="planka_board"     # External service involved
)
```

#### 2. **Agent-Specific Operations**
```python
with error_context("task_assignment", agent_id=agent.id, task_id=task.id):
    result = assign_task_to_agent(task, agent)
```

#### 3. **External Service Calls**
```python
with error_context("kanban_sync", integration_name="planka"):
    await sync_tasks_with_kanban()
```

## Retry Strategy Guidelines

### ALWAYS Use Retries For:

#### 1. **Network Operations**
```python
from src.core.error_strategies import with_retry, RetryConfig

@with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
async def call_external_api():
    # Network calls should be retried
    pass
```

#### 2. **Transient Service Failures**
```python
@with_retry(RetryConfig(max_attempts=5, base_delay=2.0, max_delay=30.0))
async def sync_with_kanban():
    # Service sync operations should be retried
    pass
```

### NEVER Retry For:

#### 1. **Authentication Failures**
```python
# ❌ WRONG - Don't retry auth failures
@with_retry()  # This will make auth failures worse
async def authenticate_with_service():
    pass

# ✅ CORRECT - Handle auth failures without retry
async def authenticate_with_service():
    try:
        return await auth_service.authenticate()
    except AuthException:
        raise AuthenticationError(service_name="auth_service")
```

#### 2. **Validation Errors**
```python
# ❌ WRONG - Don't retry validation failures
@with_retry()
def validate_task_data(data):
    if not data.get('title'):
        raise ValidationError(field_name="title")

# ✅ CORRECT - Validation errors should fail immediately
def validate_task_data(data):
    if not data.get('title'):
        raise ValidationError(field_name="title")
```

## Circuit Breaker Guidelines

### ALWAYS Use Circuit Breakers For:

#### 1. **External Service Dependencies**
```python
from src.core.error_strategies import with_circuit_breaker, CircuitBreakerConfig

@with_circuit_breaker("kanban_service", CircuitBreakerConfig(failure_threshold=3))
async def call_kanban_api():
    # External services should be protected by circuit breakers
    pass
```

#### 2. **AI Provider Calls**
```python
@with_circuit_breaker("openai", CircuitBreakerConfig(failure_threshold=5, timeout=120.0))
async def call_ai_provider():
    # AI providers should have circuit breaker protection
    pass
```

## Fallback Strategy Guidelines

### ALWAYS Provide Fallbacks For:

#### 1. **Critical Operations**
```python
from src.core.error_strategies import with_fallback

async def use_cached_tasks():
    return load_from_cache("tasks")

async def create_minimal_task():
    return {"id": "temp", "title": "Task (offline)", "status": "pending"}

@with_fallback(use_cached_tasks, create_minimal_task)
async def get_tasks_from_kanban():
    # Critical operations should have fallbacks
    pass
```

#### 2. **User-Facing Operations**
```python
async def offline_mode_response():
    return {"status": "offline", "message": "Working in offline mode"}

@with_fallback(offline_mode_response)
async def sync_user_data():
    # User-facing operations should degrade gracefully
    pass
```

## Response Formatting Guidelines

### For MCP Tool Responses:
```python
from src.core.error_responses import handle_mcp_tool_error

async def mcp_tool_function(arguments):
    try:
        result = await perform_operation(arguments)
        return {"success": True, "result": result}
    except Exception as e:
        return handle_mcp_tool_error(e, "tool_name", arguments)
```

### For API Responses:
```python
from src.core.error_responses import create_error_response, ResponseFormat

try:
    result = await api_operation()
    return {"success": True, "data": result}
except Exception as e:
    return create_error_response(e, ResponseFormat.JSON_API)
```

### For User Messages:
```python
try:
    result = await user_operation()
    return result
except Exception as e:
    user_response = create_error_response(e, ResponseFormat.USER_FRIENDLY)
    print(user_response["message"])
```

## Error Monitoring Guidelines

### ALWAYS Record Errors For:

#### 1. **Production Operations**
```python
from src.core.error_monitoring import record_error_for_monitoring

try:
    await critical_operation()
except MarcusBaseError as e:
    record_error_for_monitoring(e)
    raise
```

#### 2. **Agent Performance Tracking**
```python
try:
    result = await agent.execute_task(task)
except Exception as e:
    # Convert and record for monitoring
    marcus_error = TaskAssignmentError(
        task_id=task.id,
        agent_id=agent.id,
        reason=str(e),
        cause=e
    )
    record_error_for_monitoring(marcus_error)
    raise marcus_error
```

## Quick Decision Tree

```
Is this an error that users/agents need to handle?
├── YES → Use Marcus Error Framework
│   ├── External service? → Use IntegrationError + Circuit Breaker
│   ├── Configuration issue? → Use ConfigurationError (no retry)
│   ├── Security violation? → Use SecurityError (no retry, alert)
│   ├── Network/temporary? → Use TransientError + Retry
│   ├── Business logic? → Use BusinessLogicError (no retry)
│   └── System issue? → Use SystemError (no retry, alert)
└── NO → Use regular Python exceptions
    ├── Programming error? → ValueError, TypeError, etc.
    ├── Library error? → Let library exception bubble up
    └── Internal validation? → Standard Python exceptions
```

## Common Patterns

### 1. **External Service Call with Full Protection**
```python
from src.core.error_framework import error_context
from src.core.error_strategies import with_retry, with_circuit_breaker

@with_retry(RetryConfig(max_attempts=3))
@with_circuit_breaker("service_name")
async def protected_service_call():
    with error_context("service_call", agent_id=current_agent):
        return await external_service.call()
```

### 2. **Agent Task Processing**
```python
async def process_agent_task(agent_id, task_id):
    try:
        with error_context("task_processing", agent_id=agent_id, task_id=task_id):
            result = await execute_task_logic()
            return {"success": True, "result": result}
    except Exception as e:
        return handle_mcp_tool_error(e, "process_task", {"agent_id": agent_id, "task_id": task_id})
```

### 3. **Configuration Validation**
```python
def validate_service_config():
    if not os.getenv('API_KEY'):
        raise MissingCredentialsError(
            service_name="external_service",
            credential_type="API key"
        )
    
    if not is_valid_url(os.getenv('SERVICE_URL')):
        raise InvalidConfigurationError(
            config_key="SERVICE_URL",
            expected_format="Valid HTTP/HTTPS URL"
        )
```

### 4. **Graceful Degradation**
```python
async def get_task_suggestions():
    fallback_handler = FallbackHandler("task_suggestions")
    
    # Add fallbacks in priority order
    fallback_handler.add_fallback(get_cached_suggestions, priority=1)
    fallback_handler.add_fallback(get_basic_suggestions, priority=2)
    
    return await fallback_handler.execute_with_fallback(
        get_ai_powered_suggestions,
        cache_key="suggestions"
    )
```

## Remember

1. **Error types communicate intent** - choose the right type for the situation
2. **Context is crucial** - always provide operation, agent, and task information
3. **Retry smart, not hard** - only retry transient errors
4. **Circuit breakers prevent cascades** - use for all external dependencies
5. **Fallbacks enable resilience** - provide graceful degradation paths
6. **Monitor everything** - record errors for pattern analysis
7. **Format appropriately** - use the right format for the audience (MCP, API, user, logs)