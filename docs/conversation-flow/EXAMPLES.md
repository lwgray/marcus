
# Example Conversations

## 1. Worker Registration

**Worker → PM Agent:**
```
{
  "action": "register_agent",
  "agent_id": "claude-backend-001",
  "name": "Claude Backend Dev",
  "role": "Backend Developer",
  "skills": ["python", "api", "database", "testing"]
}
```

**PM Agent Thinking:**
- New agent registration request
- Validating skills against project needs
- Checking for duplicate registration
- Adding to available worker pool

**PM Agent → Worker:**
```
{
  "success": true,
  "message": "Welcome Claude Backend Dev! You're registered and ready to receive tasks.",
  "agent_id": "claude-backend-001"
}
```

## 2. Task Request & Assignment

**Worker → PM Agent:**
```
{
  "action": "request_next_task",
  "agent_id": "claude-backend-001"
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "get_available_tasks",
  "filters": {
    "status": ["Backlog", "Ready"],
    "assigned_to": null
  }
}
```

**Kanban Board → PM Agent:**
```
{
  "tasks": [
    {
      "id": "task-123",
      "title": "Implement user authentication",
      "priority": "High",
      "labels": ["backend", "security"],
      "estimated_hours": 8
    },
    {
      "id": "task-124", 
      "title": "Create API documentation",
      "priority": "Medium",
      "labels": ["documentation"],
      "estimated_hours": 4
    }
  ]
}
```

**PM Agent Thinking:**
- Analyzing 2 available tasks
- Task-123: High priority, matches skills (backend, security)
- Task-124: Medium priority, partial match
- Decision: Assign task-123 due to priority and skill match

**PM Agent → Kanban Board:**
```
{
  "action": "assign_task",
  "task_id": "task-123",
  "agent_id": "claude-backend-001",
  "updates": {
    "assigned_to": "claude-backend-001",
    "status": "In Progress",
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```

**PM Agent → Worker:**
```
{
  "has_task": true,
  "task": {
    "id": "task-123",
    "title": "Implement user authentication",
    "description": "Create secure login system with JWT tokens",
    "priority": "High",
    "estimated_hours": 8,
    "instructions": "1. Set up user model\n2. Implement JWT auth\n3. Create login/logout endpoints\n4. Add password hashing\n5. Write tests"
  }
}
```

## 3. Progress Update

**Worker → PM Agent:**
```
{
  "action": "report_task_progress",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "status": "in_progress",
  "progress": 50,
  "message": "User model and JWT implementation complete. Working on endpoints."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "update_task",
  "task_id": "task-123",
  "updates": {
    "progress": 50,
    "last_updated": "2024-01-15T14:30:00Z"
  },
  "comment": "Progress: 50% - User model and JWT implementation complete. Working on endpoints."
}
```

## 4. Blocker Report

**Worker → PM Agent:**
```
{
  "action": "report_blocker",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "blocker_description": "Missing OAuth provider credentials for social login",
  "severity": "medium"
}
```

**PM Agent Thinking:**
- Blocker type: External dependency
- Severity: Medium (can work around)
- Analyzing possible solutions

**PM Agent → Kanban Board:**
```
{
  "action": "add_comment",
  "task_id": "task-123",
  "comment": "BLOCKER: Missing OAuth provider credentials\nSeverity: Medium\nAssigned agent blocked on external dependency"
}
```

**PM Agent → Worker:**
```
{
  "success": true,
  "suggestions": [
    "Implement local authentication first, add OAuth later",
    "Use mock OAuth provider for development",
    "Request credentials from DevOps team via separate task"
  ],
  "escalated": false
}
```

## 5. Task Completion

**Worker → PM Agent:**
```
{
  "action": "report_task_progress",
  "agent_id": "claude-backend-001",
  "task_id": "task-123",
  "status": "completed",
  "progress": 100,
  "message": "Authentication system complete. All tests passing, documentation updated."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "move_card",
  "task_id": "task-123",
  "to_list": "Done",
  "comment": "Completed by claude-backend-001. All tests passing."
}
```

**PM Agent → Kanban Board:**
```
{
  "action": "get_project_metrics"
}
```

**Kanban Board → PM Agent:**
```
{
  "metrics": {
    "total_tasks": 25,
    "completed": 11,
    "in_progress": 4,
    "completion_rate": "44%",
    "velocity": "2.8 tasks/day"
  }
}
```

**PM Agent → Worker:**
```
{
  "success": true,
  "message": "Excellent work! Task completed successfully. Ready for next assignment?"
}
```
