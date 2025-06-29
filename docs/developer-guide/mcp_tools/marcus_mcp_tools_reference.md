# Marcus MCP Tools Reference

## Overview

Marcus provides a comprehensive set of MCP (Model Context Protocol) tools for managing AI-powered project management and task orchestration. These tools are exposed through the Marcus MCP server and can be used by Claude or other MCP-compatible clients.

## Code Organization

### Current Structure
The MCP tools are currently split across two files:

1. **Core Marcus Tools** (`/marcus_mcp_server.py` - lines 456-1180)
   - Agent management tools
   - Task assignment and progress tracking
   - Project status monitoring
   - System health checks

2. **Natural Language Tools** (`/src/integrations/mcp_natural_language_tools.py` - lines 516-650)
   - Project creation from natural language
   - Feature addition using AI

### Organization Assessment
**❌ Not Well Organized** - The tools should be better organized:
- MCP server file is too large (1200+ lines)
- Natural language tools are properly placed in integrations
- Core tools could be modularized into separate files by domain

### Recommended Structure
```
src/
├── mcp/
│   ├── __init__.py
│   ├── server.py              # Main MCP server
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── agent_tools.py     # Agent management
│   │   ├── task_tools.py      # Task operations
│   │   ├── project_tools.py   # Project monitoring
│   │   └── system_tools.py    # System health
│   └── handlers.py            # Tool handlers
```

---

## Tool Categories

### 1. Agent Management Tools

#### `register_agent`
**Purpose**: Register a new AI agent with the Marcus system

**Location**: `marcus_mcp_server.py:456-553`

**Parameters**:
- `agent_id` (string, required): Unique identifier for the agent
- `name` (string, required): Display name for the agent
- `role` (string, required): Agent's role (e.g., "Backend Developer", "Frontend Engineer")
- `skills` (array[string], optional): List of technical skills

**Returns**:
```json
{
  "success": true,
  "agent_id": "agent-123",
  "message": "Agent registered successfully",
  "assigned_tasks": 0
}
```

**Example**:
```python
await register_agent(
    agent_id="claude-001",
    name="Claude Backend Dev",
    role="Backend Developer",
    skills=["Python", "FastAPI", "PostgreSQL"]
)
```

---

#### `get_agent_status`
**Purpose**: Get current status and assignments for a specific agent

**Location**: `marcus_mcp_server.py:1001-1042`

**Parameters**:
- `agent_id` (string, required): ID of the agent to check

**Returns**:
```json
{
  "success": true,
  "agent": {
    "id": "agent-123",
    "name": "Claude Backend Dev",
    "role": "Backend Developer",
    "status": "working",
    "current_tasks": [
      {
        "id": "task-456",
        "name": "Implement user authentication",
        "status": "in_progress",
        "progress": 65
      }
    ],
    "skills": ["Python", "FastAPI"],
    "registered_at": "2025-06-28T10:00:00Z"
  }
}
```

---

#### `list_registered_agents`
**Purpose**: Get a list of all registered agents and their current status

**Location**: `marcus_mcp_server.py:1044-1070`

**Parameters**: None

**Returns**:
```json
{
  "success": true,
  "agents": [
    {
      "id": "agent-123",
      "name": "Claude Backend Dev",
      "role": "Backend Developer",
      "status": "available",
      "skills": ["Python", "FastAPI"],
      "current_task_count": 0
    }
  ],
  "total": 1,
  "active": 0,
  "available": 1
}
```

---

### 2. Task Management Tools

#### `request_next_task`
**Purpose**: Request the next optimal task assignment for an agent based on their skills and current workload

**Location**: `marcus_mcp_server.py:555-743`

**Parameters**:
- `agent_id` (string, required): Agent requesting a task

**Returns**:
```json
{
  "success": true,
  "task": {
    "id": "task-789",
    "name": "Create REST API endpoints",
    "description": "Implement CRUD operations for user management",
    "priority": "high",
    "estimated_hours": 8,
    "labels": ["backend", "api"],
    "dependencies": []
  },
  "assignment_reason": "Matched agent skills with task requirements"
}
```

**AI-Powered Features**:
- Uses skill matching algorithm
- Considers task dependencies
- Balances workload across agents
- Prioritizes based on project needs

---

#### `report_task_progress`
**Purpose**: Update progress on an assigned task

**Location**: `marcus_mcp_server.py:745-861`

**Parameters**:
- `agent_id` (string, required): Agent reporting progress
- `task_id` (string, required): Task being updated
- `status` (string, required): One of: "in_progress", "completed", "blocked"
- `progress` (integer, optional): Progress percentage (0-100)
- `message` (string, optional): Progress update message

**Returns**:
```json
{
  "success": true,
  "task_id": "task-789",
  "status": "in_progress",
  "progress": 75,
  "message": "Progress updated successfully"
}
```

---

#### `report_blocker`
**Purpose**: Report a blocking issue on a task that requires attention

**Location**: `marcus_mcp_server.py:863-951`

**Parameters**:
- `agent_id` (string, required): Agent reporting the blocker
- `task_id` (string, required): Blocked task ID
- `blocker_description` (string, required): Detailed description of the blocker
- `severity` (string, optional): "low", "medium", or "high" (default: "medium")

**Returns**:
```json
{
  "success": true,
  "blocker_id": "blocker-123",
  "task_id": "task-789",
  "severity": "high",
  "ai_suggestions": [
    "Check database connection settings",
    "Verify environment variables are set",
    "Review PostgreSQL logs for errors"
  ]
}
```

**AI Features**:
- Analyzes blocker description
- Provides intelligent suggestions
- Learns from resolved blockers

---

### 3. Project Monitoring Tools

#### `get_project_status`
**Purpose**: Get comprehensive project metrics and status

**Location**: `marcus_mcp_server.py:953-999`

**Parameters**: None

**Returns**:
```json
{
  "success": true,
  "project": {
    "total_tasks": 45,
    "completed": 12,
    "in_progress": 8,
    "blocked": 2,
    "completion_percentage": 26.7
  },
  "workers": {
    "total": 5,
    "active": 3,
    "available": 2
  },
  "provider": "planka"
}
```

---

### 4. System Health Tools

#### `ping`
**Purpose**: Check Marcus system connectivity and status

**Location**: `marcus_mcp_server.py:1072-1089`

**Parameters**:
- `echo` (string, optional): Message to echo back

**Returns**:
```json
{
  "success": true,
  "status": "online",
  "provider": "planka",
  "echo": "Hello Marcus!",
  "timestamp": "2025-06-28T15:30:00Z"
}
```

---

#### `check_assignment_health`
**Purpose**: Verify the health of the task assignment system

**Location**: `marcus_mcp_server.py:1110-1180`

**Parameters**: None

**Returns**:
```json
{
  "success": true,
  "health_status": "healthy",
  "checks": {
    "kanban_connection": true,
    "assignment_system": true,
    "persistence": true,
    "monitoring": true
  },
  "metrics": {
    "total_assignments": 156,
    "successful_assignments": 152,
    "failed_assignments": 4,
    "success_rate": 97.4
  },
  "issues": []
}
```

---

### 5. Natural Language Tools

#### `create_project`
**Purpose**: Create a complete project with tasks from natural language description

**Location**: `src/integrations/mcp_natural_language_tools.py:516-589`

**Parameters**:
- `description` (string, required): Natural language project description
- `project_name` (string, required): Name for the project
- `options` (object, optional):
  - `team_size` (integer): Number of developers (default: 3)
  - `tech_stack` (array[string]): Technologies to use
  - `deadline` (string): ISO format date

**Returns**:
```json
{
  "success": true,
  "project_name": "E-Commerce Platform",
  "tasks_created": 25,
  "phases": ["infrastructure", "backend", "frontend", "testing", "deployment"],
  "estimated_days": 45,
  "dependencies_mapped": 18,
  "risk_level": "medium",
  "confidence": 0.87,
  "created_at": "2025-06-28T15:45:00Z"
}
```

**AI Features**:
- Parses requirements using advanced NLP
- Generates comprehensive task breakdown
- Creates dependency graph
- Estimates timeline
- Assesses project risk

**Example**:
```python
await create_project(
    description="Build a real-time chat application with user authentication, 
                 private messaging, and group chat features",
    project_name="Chat App",
    options={
        "team_size": 4,
        "tech_stack": ["Node.js", "Socket.io", "React", "MongoDB"],
        "deadline": "2025-09-01"
    }
)
```

---

#### `add_feature`
**Purpose**: Add a new feature to an existing project using natural language

**Location**: `src/integrations/mcp_natural_language_tools.py:590-650`

**Parameters**:
- `feature_description` (string, required): Natural language feature description
- `integration_point` (string, optional): How to integrate the feature
  - `"auto_detect"` (default): AI determines best integration
  - `"after_current"`: Add after current tasks
  - `"parallel"`: Add as parallel work
  - `"new_phase"`: Create new project phase

**Returns**:
```json
{
  "success": true,
  "feature_name": "Email Notifications",
  "tasks_created": 5,
  "integration_point": "parallel",
  "affected_tasks": ["task-123", "task-456"],
  "estimated_hours": 16,
  "dependencies_added": 3
}
```

**AI Features**:
- Analyzes existing project structure
- Determines optimal integration point
- Creates feature-specific tasks
- Updates dependencies intelligently

---

## Usage Examples

### Complete Workflow Example

```python
# 1. Register an agent
agent = await register_agent(
    agent_id="claude-001",
    name="Claude",
    role="Full Stack Developer",
    skills=["Python", "React", "PostgreSQL"]
)

# 2. Create a project
project = await create_project(
    description="Build a task management system with user auth and REST API",
    project_name="Task Manager",
    options={"team_size": 2}
)

# 3. Request a task
task = await request_next_task(agent_id="claude-001")

# 4. Report progress
await report_task_progress(
    agent_id="claude-001",
    task_id=task["task"]["id"],
    status="in_progress",
    progress=50,
    message="Completed database schema design"
)

# 5. Hit a blocker
await report_blocker(
    agent_id="claude-001",
    task_id=task["task"]["id"],
    blocker_description="Cannot connect to PostgreSQL database",
    severity="high"
)

# 6. Check project status
status = await get_project_status()
```

---

## Error Handling

All tools follow a consistent error response format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE"
}
```

Common error codes:
- `AGENT_NOT_FOUND`: Agent ID doesn't exist
- `TASK_NOT_FOUND`: Task ID doesn't exist
- `INVALID_STATUS`: Invalid task status provided
- `NO_AVAILABLE_TASKS`: No tasks match agent's skills
- `KANBAN_CONNECTION_ERROR`: Cannot connect to kanban board
- `AI_ENGINE_ERROR`: AI processing failed

---

## Best Practices

1. **Agent Registration**: Register agents with accurate skills for optimal task matching
2. **Progress Updates**: Report progress regularly (at 25%, 50%, 75%, 100%)
3. **Blocker Reporting**: Report blockers immediately with detailed descriptions
4. **Natural Language**: Be specific in project/feature descriptions for better AI parsing
5. **Error Handling**: Always check the `success` field in responses

---

## Future Enhancements

1. **Tool Organization**: Refactor into modular structure
2. **Batch Operations**: Support bulk task updates
3. **Analytics Tools**: Add project analytics and insights
4. **Team Tools**: Inter-agent communication tools
5. **Learning Tools**: Capture and apply learned patterns