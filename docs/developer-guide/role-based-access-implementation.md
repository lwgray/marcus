# Role-Based Access Control Implementation

## Overview

Marcus implements role-based access control (RBAC) for organization and preventing accidental misuse. This is **not** a security feature - real security happens at the deployment level.

## Implementation Details

### 1. Client Registration

Clients authenticate using the `authenticate` tool:

```python
await authenticate(
    client_id="seneca-001",
    client_type="observer",  # observer, developer, agent, admin
    role="analytics",
    metadata={"tool": "seneca", "version": "1.0"}
)
```

### 2. Role Definitions

Located in `src/marcus_mcp/tools/auth.py`:

- **Observer**: Read-only access, analytics, monitoring
- **Developer**: Project management, feature creation
- **Agent**: Task execution, progress reporting
- **Admin**: Full access (no authentication required)

### 3. Access Control Flow

1. Client calls `authenticate` → Gets list of allowed tools
2. Client calls any tool → Access checked against allowed tools
3. Access denied → Error returned with allowed tools list
4. Access granted → Tool executes normally

### 4. Audit Logging

All actions are logged to `data/audit_logs/`:

- **Client registrations**: Who registered, when, what type
- **Tool calls**: Who called what, arguments, duration, success/failure
- **Access denials**: Who was denied access to what and why
- **Sessions**: Connection/disconnection events

### 5. Usage Analytics

The `get_usage_report` tool (available to observers) provides:

- Total events and unique clients
- Breakdown by client type and tool
- Error rates and insights
- Time-based filtering

## Code Structure

```
src/marcus_mcp/
├── tools/
│   ├── auth.py           # Role definitions and registration
│   └── audit_tools.py    # Usage analytics
├── audit.py              # Audit logging implementation
├── client_manager.py     # Client session management
└── handlers.py           # Tool call handling with RBAC
```

## Key Features

### Dynamic Tool Discovery

Clients can discover their available tools after registration. The tool list changes based on their role.

### Session Tracking

Each client session is tracked with:
- Client ID and type
- Role and metadata
- Last activity time
- Allowed tools

### Audit Trail

Comprehensive logging for:
- Debugging issues
- Understanding usage patterns
- Tracking who does what
- Performance monitoring

## Integration Points

### 1. Tool Handlers

```python
# In handle_tool_call
allowed_tools = get_client_tools(client_id, state)
if name not in allowed_tools:
    # Log access denial
    # Return error
```

### 2. Client Registration

```python
# In authenticate
# Store client info
state._registered_clients[client_id] = client_info
# Track current client
state._current_client_id = client_id
# Log registration
await audit_logger.log_registration(...)
```

### 3. Audit Integration

```python
# After successful tool call
await audit_logger.log_tool_call(
    client_id=client_id,
    client_type=client_type,
    tool_name=name,
    arguments=arguments,
    result=result,
    duration_ms=duration_ms,
    success=True,
)
```

## Usage Examples

### Observer (Seneca)
```python
# Register as observer
authenticate("seneca-001", "observer", "analytics")
# Can use: get_project_status, pipeline tools, get_usage_report
# Cannot use: create_project, request_next_task
```

### Developer (Human)
```python
# Register as developer
authenticate("user-john", "developer", "frontend")
# Can use: create_project, add_feature, get_task_context
# Cannot use: request_next_task, register_agent
```

### Agent (AI Worker)
```python
# Register as agent
authenticate("agent-01", "agent", "backend")
# Can use: request_next_task, report_progress, log_artifact
# Cannot use: create_project, pipeline tools
```

## Important Notes

1. **Not for Security**: This system prevents accidents, not malicious actors
2. **Open Source**: Anyone can modify the code to bypass restrictions
3. **Real Security**: Deploy behind authentication proxy, use network isolation
4. **Audit Everything**: Comprehensive logging helps debug issues

## Future Enhancements

1. **Custom Roles**: Define project-specific roles
2. **Tool Groups**: Bundle related tools together
3. **Usage Quotas**: Limit tool usage by role (soft limits)
4. **Real-time Monitoring**: WebSocket feed of audit events
