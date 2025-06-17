# PM Agent API Reference

This document provides a comprehensive reference for the PM Agent MCP (Model Context Protocol) API, including all available tools, their parameters, and expected responses.

## Table of Contents

- [Overview](#overview)
- [MCP Tools](#mcp-tools)
  - [register_agent](#register_agent)
  - [request_next_task](#request_next_task)
  - [report_task_progress](#report_task_progress)
  - [report_blocker](#report_blocker)
  - [get_project_status](#get_project_status)
  - [get_agent_status](#get_agent_status)
  - [list_registered_agents](#list_registered_agents)
  - [ping](#ping)
- [Core Classes](#core-classes)
  - [Task](#task)
  - [WorkerStatus](#workerstatus)
  - [TaskAssignment](#taskassignment)
  - [ProjectState](#projectstate)
- [Integration Classes](#integration-classes)
  - [SimpleMCPKanbanClient](#simplemcpkanbanclient)
  - [AIAnalysisEngine](#aianalysisengine)
  - [WorkspaceManager](#workspacemanager)

## Overview

PM Agent provides an MCP server that autonomous agents can connect to for project management capabilities. The API follows the Model Context Protocol standard for tool invocation.

### Connection Example

```python
# For Claude Desktop/Code
{
  "mcpServers": {
    "pm-agent": {
      "command": "python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/path/to/pm-agent"
    }
  }
}
```

## MCP Tools

### register_agent

Register a new agent with the PM system.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_id | string | Yes | Unique identifier for the agent |
| name | string | Yes | Display name of the agent |
| role | string | Yes | Agent's role (e.g., "Backend Developer") |
| skills | array[string] | No | List of agent's technical skills |

#### Example Request

```json
{
  "agent_id": "agent-001",
  "name": "Alice Smith",
  "role": "Backend Developer",
  "skills": ["Python", "Django", "PostgreSQL"]
}
```

#### Example Response

```json
{
  "success": true,
  "message": "Agent agent-001 registered successfully",
  "agent_data": {
    "id": "agent-001",
    "name": "Alice Smith",
    "role": "Backend Developer",
    "skills": ["Python", "Django", "PostgreSQL"]
  }
}
```

### request_next_task

Request the next optimal task assignment for an agent.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_id | string | Yes | ID of the agent requesting a task |

#### Example Request

```json
{
  "agent_id": "agent-001"
}
```

#### Example Response

```json
{
  "has_task": true,
  "assignment": {
    "task_id": "card-123",
    "task_name": "Implement user authentication",
    "description": "Add JWT-based authentication to the API",
    "instructions": "## Task Assignment for Alice Smith\n\n**Task:** Implement user authentication...",
    "priority": "high",
    "estimated_hours": 8.0,
    "due_date": "2024-12-25T00:00:00",
    "workspace_path": "/home/project",
    "forbidden_paths": ["/usr/lib/python3", "/home/project/pm-agent"]
  }
}
```

### report_task_progress

Report progress on an assigned task.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_id | string | Yes | ID of the reporting agent |
| task_id | string | Yes | ID of the task being updated |
| status | string | Yes | Task status: "in_progress", "completed", or "blocked" |
| progress | integer | No | Completion percentage (0-100) |
| message | string | No | Progress update message |

#### Example Request

```json
{
  "agent_id": "agent-001",
  "task_id": "card-123",
  "status": "in_progress",
  "progress": 50,
  "message": "Completed authentication middleware"
}
```

#### Example Response

```json
{
  "acknowledged": true,
  "status": "progress_recorded",
  "message": "Progress updated for task card-123"
}
```

### report_blocker

Report a blocker preventing task completion.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_id | string | Yes | ID of the agent reporting the blocker |
| task_id | string | Yes | ID of the blocked task |
| blocker_description | string | Yes | Detailed description of the blocker |
| severity | string | No | Severity: "low", "medium", or "high" (default: "medium") |

#### Example Request

```json
{
  "agent_id": "agent-001",
  "task_id": "card-123",
  "blocker_description": "Cannot connect to authentication database",
  "severity": "high"
}
```

#### Example Response

```json
{
  "success": true,
  "message": "Blocker reported successfully",
  "resolution_suggestion": "1. Check database server status\n2. Verify connection credentials\n3. Check network connectivity\n4. Review firewall rules"
}
```

### get_project_status

Get current project status and metrics.

#### Parameters

None required.

#### Example Response

```json
{
  "success": true,
  "project_status": {
    "total_cards": 45,
    "completion_percentage": 67,
    "in_progress_count": 8,
    "done_count": 30,
    "urgent_count": 2,
    "bug_count": 5
  },
  "board_info": {
    "board_id": "board-456",
    "project_id": "project-789"
  }
}
```

### get_agent_status

Get status information for a specific agent.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| agent_id | string | Yes | ID of the agent to query |

#### Example Request

```json
{
  "agent_id": "agent-001"
}
```

#### Example Response

```json
{
  "found": true,
  "agent_info": {
    "id": "agent-001",
    "name": "Alice Smith",
    "role": "Backend Developer",
    "skills": ["Python", "Django", "PostgreSQL"],
    "completed_tasks": 15,
    "current_task": {
      "task_id": "card-123",
      "task_name": "Implement user authentication",
      "assigned_at": "2024-12-20T10:30:00"
    }
  }
}
```

### list_registered_agents

List all registered agents and their current status.

#### Parameters

None required.

#### Example Response

```json
{
  "success": true,
  "agent_count": 3,
  "agents": [
    {
      "id": "agent-001",
      "name": "Alice Smith",
      "role": "Backend Developer",
      "skills": ["Python", "Django"],
      "completed_tasks": 15,
      "has_current_task": true,
      "current_task_id": "card-123"
    },
    {
      "id": "agent-002",
      "name": "Bob Jones",
      "role": "Frontend Developer",
      "skills": ["React", "TypeScript"],
      "completed_tasks": 12,
      "has_current_task": false,
      "current_task_id": null
    }
  ]
}
```

### ping

Health check endpoint for PM Agent.

#### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| echo | string | No | Optional message to echo back |

#### Example Request

```json
{
  "echo": "hello"
}
```

#### Example Response

```json
{
  "success": true,
  "pong": true,
  "status": "online",
  "service": "PM Agent MVP",
  "timestamp": "2024-12-20T15:30:00",
  "version": "1.0.0",
  "uptime": "2h 15m 30s",
  "echo": "hello",
  "echo_received": true,
  "health": {
    "status": "healthy",
    "ai_engine": "available",
    "memory_usage": {
      "rss_mb": 125.5,
      "percent": 2.3
    }
  },
  "capabilities": {
    "agent_registration": true,
    "task_assignment": true,
    "progress_tracking": true,
    "blocker_resolution": true,
    "ai_assistance": true
  },
  "workload": {
    "registered_agents": 3,
    "active_assignments": 2,
    "total_completed_tasks": 45,
    "agents_available": 1
  }
}
```

## Core Classes

### Task

Represents a work item in the project management system.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| id | string | Unique identifier for the task |
| name | string | Short descriptive name |
| description | string | Detailed description |
| status | TaskStatus | Current state (TODO, IN_PROGRESS, DONE, BLOCKED) |
| priority | Priority | Urgency level (LOW, MEDIUM, HIGH, URGENT) |
| assigned_to | string? | ID of assigned worker |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Last modification timestamp |
| due_date | datetime? | Target completion date |
| estimated_hours | float | Estimated time to complete |
| actual_hours | float | Actual time spent |
| dependencies | list[string] | Task IDs that must complete first |
| labels | list[string] | Tags for categorization |

### WorkerStatus

Represents the current state and capabilities of a worker agent.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| worker_id | string | Unique identifier |
| name | string | Display name |
| role | string | Job role/specialization |
| email | string? | Contact email |
| current_tasks | list[Task] | Currently assigned tasks |
| completed_tasks_count | int | Total completed tasks |
| capacity | int | Max hours per week |
| skills | list[string] | Technical competencies |
| availability | dict[str, bool] | Days available |
| performance_score | float | Performance rating (0.0-2.0) |

### TaskAssignment

Represents a task assignment to a specific worker.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| task_id | string | Task identifier |
| task_name | string | Task name |
| description | string | What needs to be done |
| instructions | string | Detailed instructions |
| estimated_hours | float | Expected time |
| priority | Priority | Task urgency |
| dependencies | list[string] | Other required tasks |
| assigned_to | string | Worker ID |
| assigned_at | datetime | Assignment timestamp |
| due_date | datetime? | Target completion |
| workspace_path | string? | Working directory |
| forbidden_paths | list[string] | Restricted paths |

### ProjectState

Enumeration of possible project states.

- `HEALTHY` - Project on track
- `AT_RISK` - Potential issues identified  
- `CRITICAL` - Immediate action required

## Integration Classes

### SimpleMCPKanbanClient

Simple MCP Kanban client for reliable task management.

#### Key Methods

##### get_available_tasks()
```python
async def get_available_tasks() -> List[Task]
```
Retrieves all unassigned tasks from the kanban board.

##### assign_task()
```python
async def assign_task(task_id: str, agent_id: str) -> None
```
Assigns a task to an agent and moves it to "In Progress".

##### get_board_summary()
```python
async def get_board_summary() -> Dict[str, Any]
```
Gets summary statistics for the kanban board.

### AIAnalysisEngine

AI-powered analysis and decision engine using Claude API.

#### Key Methods

##### match_task_to_agent()
```python
async def match_task_to_agent(
    available_tasks: List[Task], 
    agent: WorkerStatus,
    project_state: ProjectState
) -> Optional[Task]
```
Finds the optimal task for an agent using AI analysis.

##### generate_task_instructions()
```python
async def generate_task_instructions(
    task: Task, 
    agent: Optional[WorkerStatus] = None
) -> str
```
Generates detailed, context-aware task instructions.

##### analyze_blocker()
```python
async def analyze_blocker(
    task_id: str,
    description: str,
    severity: str
) -> Dict[str, Any]
```
Analyzes blockers and suggests resolution steps.

### WorkspaceManager

Manages workspace isolation and security boundaries.

#### Key Methods

##### assign_agent_workspace()
```python
def assign_agent_workspace(
    agent_id: str, 
    workspace_path: Optional[str] = None
) -> WorkspaceConfig
```
Assigns a secure workspace to an agent.

##### validate_path()
```python
def validate_path(path: str) -> str
```
Validates that a path is allowed (not in forbidden paths).

##### get_task_assignment_data()
```python
def get_task_assignment_data(agent_id: str) -> Dict[str, Any]
```
Gets workspace data to include in task assignments.

## Error Handling

All MCP tools return structured error responses when failures occur:

```json
{
  "success": false,
  "error": "Detailed error message",
  "tool": "tool_name",
  "arguments": {...}
}
```

Common error scenarios:
- Agent not registered
- Board ID not configured
- Task not found
- AI service unavailable (falls back to rule-based logic)
- Workspace security violations

## Best Practices

1. **Agent Registration**: Always register agents before requesting tasks
2. **Progress Reporting**: Report progress at 25%, 50%, 75%, and completion
3. **Blocker Reporting**: Include detailed descriptions and accurate severity
4. **Task Completion**: Always report "completed" status when done
5. **Error Handling**: Check response success/error fields
6. **Workspace Security**: Respect forbidden paths in task assignments

## Environment Variables

Required environment variables:

```bash
# For AI features (optional - falls back if not set)
ANTHROPIC_API_KEY=your-api-key

# Planka configuration (loaded from .env)
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo  
PLANKA_AGENT_PASSWORD=demo
```

## Configuration Files

### config_pm_agent.json
```json
{
  "project_id": "your-project-id",
  "board_id": "your-board-id",
  "project_name": "Your Project",
  "auto_find_board": false
}
```

### Workspace Configuration
```json
{
  "project": {
    "workspaces": {
      "main": "/path/to/project",
      "agents": {
        "agent-001": "/path/to/agent1/workspace"
      }
    }
  },
  "security": {
    "additional_forbidden_paths": ["/sensitive/data"]
  }
}
```