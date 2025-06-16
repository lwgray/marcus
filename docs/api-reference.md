# PM Agent API Reference

This document details all MCP tools exposed by PM Agent for worker agents to use.

## Available Tools

### 1. register_agent
Register a new agent with the PM system.

**Parameters:**
```json
{
  "agent_id": "string",      // Unique agent identifier (required)
  "name": "string",          // Agent's display name (required)
  "role": "string",          // Agent's role, e.g., "Backend Developer" (required)
  "skills": ["string"]       // List of agent's skills (optional, default: [])
}
```

**Response:**
```json
{
  "success": true,
  "message": "Agent test_agent_1 registered successfully",
  "agent_data": {
    "id": "test_agent_1",
    "name": "Test Agent",
    "role": "Backend Developer",
    "skills": ["python", "fastapi"]
  }
}
```

**Example:**
```python
result = await session.call_tool("register_agent", {
    "agent_id": "backend_agent_1",
    "name": "Backend Developer Agent",
    "role": "Backend Developer",
    "skills": ["python", "fastapi", "postgresql", "redis"]
})
```

### 2. request_next_task
Request the next optimal task assignment for an agent.

**Parameters:**
```json
{
  "agent_id": "string"       // Agent requesting the task (required)
}
```

**Response (Task Available):**
```json
{
  "has_task": true,
  "assignment": {
    "task_id": "1533846381494535401",
    "task_name": "BACKEND-001: Initialize FastAPI project",
    "description": "Create project structure and setup FastAPI",
    "instructions": "1. Create directory structure\n2. Set up virtual environment\n3. Install dependencies\n4. Create main.py with basic FastAPI app",
    "priority": "high",
    "estimated_hours": 4,
    "due_date": "2024-01-15T10:00:00Z"
  }
}
```

**Response (No Tasks):**
```json
{
  "has_task": false,
  "message": "No tasks available at this time"
}
```

**Example:**
```python
result = await session.call_tool("request_next_task", {
    "agent_id": "backend_agent_1"
})

if result["has_task"]:
    task = result["assignment"]
    print(f"Working on: {task['task_name']}")
```

### 3. report_task_progress
Report progress on a task.

**Parameters:**
```json
{
  "agent_id": "string",      // Agent reporting progress (required)
  "task_id": "string",       // Task being updated (required)
  "status": "string",        // Status: "in_progress", "completed", "blocked" (required)
  "progress": 0-100,         // Progress percentage (optional, default: 0)
  "message": "string"        // Progress message (optional, default: "")
}
```

**Response:**
```json
{
  "acknowledged": true,
  "status": "progress_recorded",
  "message": "Progress updated for task 1533846381494535401"
}
```

**Example:**
```python
# Report progress
await session.call_tool("report_task_progress", {
    "agent_id": "backend_agent_1",
    "task_id": "1533846381494535401",
    "status": "in_progress",
    "progress": 50,
    "message": "Completed project structure and dependencies"
})

# Mark as complete
await session.call_tool("report_task_progress", {
    "agent_id": "backend_agent_1",
    "task_id": "1533846381494535401",
    "status": "completed",
    "progress": 100,
    "message": "FastAPI project initialized successfully"
})
```

### 4. report_blocker
Report a blocker on a task.

**Parameters:**
```json
{
  "agent_id": "string",              // Agent reporting the blocker (required)
  "task_id": "string",               // Blocked task ID (required)
  "blocker_description": "string",   // Description of the blocker (required)
  "severity": "string"               // Severity: "low", "medium", "high" (optional, default: "medium")
}
```

**Response:**
```json
{
  "success": true,
  "message": "Blocker reported successfully",
  "resolution_suggestion": "1. Check if the API endpoint is accessible\n2. Verify authentication credentials\n3. Review API documentation for changes\n4. Contact the API team if issue persists"
}
```

**Example:**
```python
result = await session.call_tool("report_blocker", {
    "agent_id": "frontend_agent_1",
    "task_id": "1533846381704250603",
    "blocker_description": "Cannot connect to backend API - getting 404 errors",
    "severity": "high"
})

print(f"Suggestion: {result['resolution_suggestion']}")
```

### 5. get_project_status
Get current project status and metrics.

**Parameters:**
```json
{}  // No parameters required
```

**Response:**
```json
{
  "success": true,
  "project_status": {
    "total_cards": 25,
    "completion_percentage": 40,
    "in_progress_count": 5,
    "done_count": 10,
    "urgent_count": 2,
    "bug_count": 3
  },
  "board_info": {
    "board_id": "1533822098756076745",
    "project_id": "1533678301472621705"
  }
}
```

**Example:**
```python
status = await session.call_tool("get_project_status", {})
print(f"Project is {status['project_status']['completion_percentage']}% complete")
```

### 6. get_agent_status
Get status and current assignment for an agent.

**Parameters:**
```json
{
  "agent_id": "string"       // Agent to check status for (required)
}
```

**Response (Agent Found):**
```json
{
  "found": true,
  "agent_info": {
    "id": "backend_agent_1",
    "name": "Backend Developer Agent",
    "role": "Backend Developer",
    "skills": ["python", "fastapi"],
    "completed_tasks": 5,
    "current_task": {
      "task_id": "1533846381494535401",
      "task_name": "BACKEND-001: Initialize FastAPI project",
      "assigned_at": "2024-01-10T14:30:00Z"
    }
  }
}
```

**Response (Agent Not Found):**
```json
{
  "found": false,
  "message": "Agent backend_agent_999 not registered"
}
```

**Example:**
```python
status = await session.call_tool("get_agent_status", {
    "agent_id": "backend_agent_1"
})

if status["found"]:
    current = status["agent_info"].get("current_task")
    if current:
        print(f"Currently working on: {current['task_name']}")
```

### 7. list_registered_agents
List all registered agents.

**Parameters:**
```json
{}  // No parameters required
```

**Response:**
```json
{
  "success": true,
  "agent_count": 3,
  "agents": [
    {
      "id": "backend_agent_1",
      "name": "Backend Developer Agent",
      "role": "Backend Developer",
      "skills": ["python", "fastapi"],
      "completed_tasks": 5,
      "has_current_task": true,
      "current_task_id": "1533846381494535401"
    },
    {
      "id": "frontend_agent_1",
      "name": "Frontend Developer Agent",
      "role": "Frontend Developer",
      "skills": ["react", "typescript"],
      "completed_tasks": 3,
      "has_current_task": false,
      "current_task_id": null
    }
  ]
}
```

**Example:**
```python
result = await session.call_tool("list_registered_agents", {})
print(f"Total agents: {result['agent_count']}")
for agent in result['agents']:
    status = "busy" if agent['has_current_task'] else "available"
    print(f"- {agent['name']}: {status}")
```

## Error Responses

All tools may return error responses in this format:

```json
{
  "error": "Error message",
  "tool": "tool_name",
  "arguments": { /* original arguments */ }
}
```

Common errors:
- Agent not registered
- Invalid parameters
- Task not found
- Connection issues

## Usage Guidelines

### 1. Registration
- Always register before requesting tasks
- Use unique agent_id values
- Provide accurate skills for better task matching

### 2. Task Workflow
```python
# Typical worker agent workflow
async def worker_loop(agent_id):
    # 1. Register
    await register_agent(agent_id, name, role, skills)
    
    while True:
        # 2. Request task
        task = await request_next_task(agent_id)
        
        if not task["has_task"]:
            await asyncio.sleep(60)  # Wait before retry
            continue
        
        # 3. Report starting
        await report_task_progress(agent_id, task_id, "in_progress", 0)
        
        # 4. Do work...
        
        # 5. Report progress
        await report_task_progress(agent_id, task_id, "in_progress", 50)
        
        # 6. Handle blockers if needed
        if blocked:
            await report_blocker(agent_id, task_id, description)
        
        # 7. Complete
        await report_task_progress(agent_id, task_id, "completed", 100)
```

### 3. Best Practices
- Report progress regularly (every 15-30 minutes)
- Include meaningful messages with progress reports
- Use appropriate blocker severity levels
- Check agent status before long operations

## Rate Limits

Currently no rate limits are enforced, but recommended guidelines:
- Status checks: Max 1 per minute
- Task requests: Max 1 per 30 seconds
- Progress reports: Max 1 per 5 minutes per task

## Future API Additions

Planned tools for future versions:
- `get_task_clarification` - Ask questions about tasks
- `handoff_task` - Transfer task to another agent
- `request_code_review` - Request review from another agent
- `broadcast_message` - Send message to all agents
- `get_task_dependencies` - Get dependent task information