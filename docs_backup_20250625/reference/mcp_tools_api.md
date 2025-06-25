# PM Agent MCP Tools API Reference

> **Type**: API  
> **Version**: 2.0.0  
> **Last Updated**: 2025-06-25

## Overview

The PM Agent MCP (Model Context Protocol) Tools API provides a comprehensive set of tools for worker agents to interact with the PM Agent system. These tools enable autonomous agents to register themselves, request tasks, report progress, and handle blockers.

## Synopsis

```python
# Basic usage pattern for MCP tools
await mcp_client.call_tool("register_agent", {
    "agent_id": "backend-dev-001",
    "name": "Backend Developer",
    "role": "Backend Developer",
    "skills": ["Python", "Django", "PostgreSQL"]
})
```

## Description

The PM Agent MCP Tools API is designed to facilitate autonomous agent workflows. Worker agents can register with the system, continuously request new tasks, report their progress, and handle blockers with AI-powered suggestions. The API follows a stateless design pattern where each tool call is independent.

## Parameters

### register_agent

Registers a new agent with the PM system.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | Unique identifier for the agent |
| `name` | string | Yes | - | Display name of the agent |
| `role` | string | Yes | - | Agent's role (e.g., 'Backend Developer', 'Frontend Developer') |
| `skills` | array[string] | No | `[]` | List of technical skills and competencies |

#### Parameter Details

##### `agent_id`
The agent ID must be unique across the system. Recommended format is `{role}-{instance}-{number}`, for example: `backend-dev-001`, `frontend-dev-002`.

##### `role`
Standard roles include:
- Backend Developer
- Frontend Developer
- Full Stack Developer
- DevOps Engineer
- QA Engineer
- Data Engineer

##### `skills`
Skills should match task labels for optimal assignment. Common skills:
- Programming languages: Python, JavaScript, TypeScript, Go, Java
- Frameworks: Django, React, Vue, Angular, Express
- Databases: PostgreSQL, MySQL, MongoDB, Redis
- Tools: Docker, Kubernetes, Git, CI/CD

### request_next_task

Requests the next optimal task assignment for an agent.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | ID of the agent requesting a task |

### report_task_progress

Reports progress on an assigned task.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | Agent reporting progress |
| `task_id` | string | Yes | - | ID of the task being updated |
| `status` | string | Yes | - | Task status: `in_progress`, `completed`, `blocked` |
| `progress` | integer | No | `0` | Progress percentage (0-100) |
| `message` | string | No | `""` | Detailed progress message |

#### Parameter Details

##### `status`
- `in_progress`: Task is actively being worked on
- `completed`: Task is finished and ready for review
- `blocked`: Task cannot proceed due to dependencies or issues

##### `progress`
Progress should be reported at key milestones:
- 25%: Initial implementation started
- 50%: Core functionality complete
- 75%: Testing and edge cases handled
- 100%: Fully complete with documentation

### report_blocker

Reports a blocker preventing task completion.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | Agent reporting the blocker |
| `task_id` | string | Yes | - | ID of the blocked task |
| `blocker_description` | string | Yes | - | Detailed description of what's blocking progress |
| `severity` | string | No | `medium` | Blocker severity: `low`, `medium`, `high` |

#### Parameter Details

##### `severity`
- `low`: Minor issue, workaround available
- `medium`: Significant issue, impacts timeline
- `high`: Critical blocker, prevents any progress

### get_project_status

Gets current project status and metrics.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| - | - | - | - | No parameters required |

### get_agent_status

Gets status and current assignment for a specific agent.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `agent_id` | string | Yes | - | Agent to check status for |

### list_registered_agents

Lists all currently registered agents.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| - | - | - | - | No parameters required |

### ping

Checks PM Agent connectivity and status.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `echo` | string | No | `""` | Optional message to echo back |

## Return Values

### Success Response

All tools return a JSON response with at least these fields:

```json
{
  "success": true,
  "message": "Operation completed successfully",
  // Additional tool-specific data
}
```

### Error Response

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

### Tool-Specific Responses

#### register_agent
```json
{
  "success": true,
  "message": "Agent Backend Developer registered successfully",
  "agent_id": "backend-dev-001"
}
```

#### request_next_task
```json
{
  "success": true,
  "task": {
    "id": "task-123",
    "name": "Implement user authentication",
    "description": "Add JWT-based authentication to the API",
    "instructions": "1. Create auth endpoints\n2. Implement JWT tokens\n3. Add middleware",
    "priority": "high",
    "implementation_context": {
      "previous_implementations": ["auth.py", "middleware.py"],
      "patterns_used": ["JWT", "Bearer tokens"]
    }
  }
}
```

#### report_task_progress
```json
{
  "success": true,
  "message": "Progress updated successfully"
}
```

#### report_blocker
```json
{
  "success": true,
  "message": "Blocker reported and suggestions provided",
  "suggestions": "1. Check database connection string\n2. Verify credentials\n3. Test with local database"
}
```

#### get_project_status
```json
{
  "success": true,
  "project": {
    "total_tasks": 50,
    "completed": 20,
    "in_progress": 5,
    "blocked": 2,
    "completion_percentage": 40.0
  },
  "workers": {
    "total": 3,
    "active": 2,
    "available": 1
  },
  "provider": "planka"
}
```

## Examples

### Basic Example
```python
# Register an agent
result = await mcp_client.call_tool("register_agent", {
    "agent_id": "backend-dev-001",
    "name": "Backend Developer",
    "role": "Backend Developer",
    "skills": ["Python", "Django"]
})
```

### Advanced Example
```python
# Complete agent workflow
async def agent_workflow(agent_id, name, role, skills):
    # 1. Register
    await mcp_client.call_tool("register_agent", {
        "agent_id": agent_id,
        "name": name,
        "role": role,
        "skills": skills
    })
    
    # 2. Request task
    task_result = await mcp_client.call_tool("request_next_task", {
        "agent_id": agent_id
    })
    
    if task_result["success"]:
        task = task_result["task"]
        
        # 3. Report progress
        await mcp_client.call_tool("report_task_progress", {
            "agent_id": agent_id,
            "task_id": task["id"],
            "status": "in_progress",
            "progress": 25,
            "message": "Started implementation"
        })
```

### Real-World Example
```python
# Agent with error handling and blocker management
async def robust_agent_workflow(agent_id):
    try:
        # Get next task
        result = await mcp_client.call_tool("request_next_task", {
            "agent_id": agent_id
        })
        
        if not result["success"]:
            print(f"No tasks available: {result.get('message')}")
            return
            
        task = result["task"]
        
        # Start work
        await mcp_client.call_tool("report_task_progress", {
            "agent_id": agent_id,
            "task_id": task["id"],
            "status": "in_progress",
            "progress": 0,
            "message": "Analyzing requirements"
        })
        
        # Simulate work with potential blocker
        try:
            # ... do actual work ...
            pass
        except DatabaseConnectionError as e:
            # Report blocker
            blocker_result = await mcp_client.call_tool("report_blocker", {
                "agent_id": agent_id,
                "task_id": task["id"],
                "blocker_description": str(e),
                "severity": "high"
            })
            
            # Use AI suggestions
            print(f"AI Suggestions: {blocker_result['suggestions']}")
            return
            
        # Complete task
        await mcp_client.call_tool("report_task_progress", {
            "agent_id": agent_id,
            "task_id": task["id"],
            "status": "completed",
            "progress": 100,
            "message": "All tests passing, documentation updated"
        })
        
    except Exception as e:
        print(f"Agent error: {e}")
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `AGENT_NOT_FOUND` | Agent ID not registered | Ensure agent is registered before requesting tasks |
| `TASK_NOT_FOUND` | Task ID doesn't exist | Verify task ID from request_next_task response |
| `INVALID_STATUS` | Invalid task status value | Use only: in_progress, completed, blocked |
| `NO_TASKS_AVAILABLE` | No suitable tasks for agent | Wait and retry, or check agent skills match task requirements |
| `KANBAN_CONNECTION_ERROR` | Cannot connect to kanban provider | Check kanban server status and credentials |

## Notes

- Agents should register only once per session
- Progress should be reported incrementally, not just at completion
- Blockers should include specific error messages for better AI suggestions
- The system uses skill matching to assign optimal tasks
- Tasks are assigned based on priority and agent capabilities

## Performance Considerations

- Tool calls are rate-limited to prevent system overload
- Batch operations are not supported; each tool call is atomic
- Long-running operations may timeout after 30 seconds
- The system caches agent registrations for 24 hours

## Version History

| Version | Changes |
|---------|---------|
| 2.0.0 | Added implementation_context to task assignments |
| 1.5.0 | Added list_registered_agents tool |
| 1.2.0 | Added severity levels to blocker reports |
| 1.1.0 | Added progress percentage to task updates |
| 1.0.0 | Initial release with core tools |

## See Also

- [Configuration Guide](/reference/configuration)
- [System Architecture](/reference/architecture)
- [Worker Agent Guide](/how-to/worker-agents)