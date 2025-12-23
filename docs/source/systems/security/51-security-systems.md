# Marcus Security Systems

## Overview

The Marcus Security Systems provide basic authentication and role-based access control (RBAC) for controlling access to Marcus MCP tools based on client type.

### What the System Does

The Security Systems provide:
- **Client Authentication**: Clients identify themselves and establish their access level
- **Role-Based Access Control**: Different client types (observer, developer, agent, admin) have access to different tool sets
- **Audit Logging**: Registration and authentication events are logged for audit purposes
- **Session Management**: Track registered clients and their access permissions

## System Architecture

```
Marcus Security Architecture
├── Authentication Layer
│   ├── Client Registration
│   └── Session Tracking
└── Authorization Layer
    ├── Role-Based Tool Access
    └── Permission Enforcement
```

## Client Types and Tool Access

### Observer
Read-only access for monitoring, analytics, and project management:
- Project visibility (status, listing)
- Agent monitoring
- Board health checks
- Analytics and metrics
- Prediction tools
- Pipeline monitoring (if enabled)

### Developer
Project creation and management capabilities:
- All observer permissions
- Project creation (NLP-based)
- Feature addition
- Project switching and updates
- Task context viewing

### Agent
AI agent workflow tools:
- Agent registration
- Task assignment requests
- Progress reporting
- Blocker reporting
- Decision and artifact logging
- Experiment tracking

### Admin
Full access to all Marcus tools.

## Technical Implementation

### Core Module
**Location**: `src/marcus_mcp/tools/auth.py`

**Key Functions**:
- `authenticate()`: Register client and establish role-based access
- `get_client_tools()`: Get tools available to a specific client
- `get_tool_definitions_for_client()`: Filter tool definitions by client access

### Authentication Flow

```python
# 1. Client authenticates
result = await authenticate(
    client_id="seneca-001",
    client_type="observer",
    role="analytics",
    metadata={"version": "2.0"}
)

# 2. Marcus assigns tool access based on client_type
# 3. Client receives list of available tools
# 4. Future tool calls are filtered by permission
```

### Role Configuration

Tool access is defined in `ROLE_TOOLS` dictionary mapping client types to allowed tools. Default tools (ping, authenticate) are available before registration.

## Integration with Marcus Ecosystem

### MCP Server Integration
The authentication system integrates with the MCP server's tool listing mechanism to filter tools shown to each client based on their permissions.

### Audit Integration
All authentication events are logged via the audit logger for compliance and debugging.

## What This System Doesn't Do

The following security features are **not currently implemented**:
- Code security scanning
- Vulnerability detection
- Workspace isolation/sandboxing
- Threat detection and response
- Encrypted communication channels
- Multi-factor authentication
- JWT token services
- Dependency checking
- Static code analysis

These may be added in future releases as security requirements evolve.

## Implementation Status

**Implemented (~30%)**:
- Basic client authentication
- Role-based access control
- Audit logging of auth events
- Session tracking

**Not Implemented (~70%)**:
- Advanced security features listed above
- Code scanning and vulnerability detection
- Encryption and secure communication
- Threat detection

## Usage Example

```python
# Authenticate Seneca as observer
result = await authenticate(
    client_id="seneca-prod",
    client_type="observer",
    role="analytics",
    metadata={"environment": "production"}
)

# Result includes available tools
print(result["available_tools"])  # List of allowed tools

# Authenticate an AI agent
result = await authenticate(
    client_id="agent-backend-01",
    client_type="agent",
    role="backend_developer",
    metadata={"capabilities": ["python", "api"]}
)
```

## Future Evolution

Potential enhancements as requirements emerge:
- Enhanced authentication mechanisms (API keys, tokens)
- Fine-grained permissions beyond role-based access
- Tool-level access control (e.g., read-only vs. read-write)
- Security scanning for generated code
- Workspace isolation for agent operations
