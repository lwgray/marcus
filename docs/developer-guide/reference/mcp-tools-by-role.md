# MCP Tools Reference by Role

This reference guide categorizes all Marcus MCP tools by the role that uses them. Understanding this separation is crucial for implementing agents and understanding the Marcus architecture.

## Quick Reference Table

| Tool | User/Owner | Marcus PM | Coding Agent |
|------|------------|-----------|--------------|
| `register_agent` | ❌ | ✅ (internal) | ✅ |
| `request_next_task` | ❌ | ❌ | ✅ |
| `report_task_progress` | ❌ | ❌ | ✅ |
| `report_blocker` | ❌ | ❌ | ✅ |
| `get_task_context` | ❌ | ❌ | ✅ |
| `get_agent_status` | ✅ | ✅ | ❌ |
| `list_registered_agents` | ✅ | ✅ | ❌ |
| `get_project_status` | ✅ | ✅ | ❌ |
| `create_project` | ✅ | ✅ | ❌ |
| `add_feature` | ✅ | ✅ | ❌ |
| `pipeline_replay_*` | ✅ | ❌ | ❌ |
| `what_if_*` | ✅ | ❌ | ❌ |
| `pipeline_monitor_*` | ✅ | ❌ | ❌ |
| `pipeline_*` (analysis) | ✅ | ❌ | ❌ |

## Coding Agent Tools (5 Essential Tools)

These are the only tools that coding agents (Claude, Gemini, GPT-4, human developers) should use:

### 1. register_agent
Register with Marcus to join the workforce.

```python
register_agent({
    "agent_id": "backend-dev-001",
    "name": "Backend Developer",
    "role": "Backend Developer",
    "skills": ["python", "fastapi", "postgresql", "redis"]
})
```

**When to use**: Once at startup before requesting any tasks.

### 2. request_next_task
Request the next optimal task assignment.

```python
request_next_task({
    "agent_id": "backend-dev-001"
})

# Returns:
{
    "task": {
        "id": "TASK-123",
        "title": "Implement user authentication",
        "description": "Create JWT-based auth endpoints",
        "labels": ["backend", "api", "security"],
        "priority": "high"
    },
    "instructions": "1. Create /auth/login endpoint\n2. Use bcrypt for passwords\n3. Return JWT token"
}
```

**When to use**: After completing a task or when ready for work.

### 3. report_task_progress
Update progress on current task.

```python
report_task_progress({
    "agent_id": "backend-dev-001",
    "task_id": "TASK-123",
    "status": "in_progress",
    "progress": 50,
    "message": "Completed login endpoint, working on JWT generation"
})
```

**Status values**: `in_progress`, `completed`, `blocked`
**Progress**: 0-100 (percentage)
**When to use**: At 25%, 50%, 75% milestones and completion.

### 4. report_blocker
Report when stuck on a task.

```python
report_blocker({
    "agent_id": "backend-dev-001",
    "task_id": "TASK-123",
    "blocker_description": "Database connection refused - PostgreSQL not accessible",
    "severity": "high"
})
```

**Severity levels**: `low`, `medium`, `high`
**When to use**: Immediately when blocked, don't wait.

### 5. get_task_context
Get context about task dependencies and related decisions.

```python
get_task_context({
    "task_id": "TASK-123"
})

# Returns:
{
    "task": {...},
    "dependencies": ["TASK-100", "TASK-105"],
    "dependent_tasks": ["TASK-150", "TASK-160"],
    "related_decisions": [
        {
            "agent_id": "frontend-dev-002",
            "decision": "Using JWT in Authorization header, not cookies"
        }
    ]
}
```

**When to use**: Before starting work to understand dependencies.

## User/Owner Tools (Observation & Control)

These tools are for project owners, managers, and developers monitoring the system:

### Pipeline Replay Tools

Time-travel debugging to understand what happened:

```python
# Start replay session
pipeline_replay_start({"flow_id": "flow_123"})

# Navigate through execution
pipeline_replay_forward()      # Next step
pipeline_replay_backward()     # Previous step
pipeline_replay_jump({"position": 42})  # Jump to specific position
```

### What-If Analysis Tools

Test alternative scenarios without affecting production:

```python
# Start analysis session
what_if_start({"flow_id": "flow_123"})

# Simulate changes
what_if_simulate({
    "modifications": [
        {
            "parameter_type": "agent_assignment",
            "parameter_name": "assigned_agent",
            "old_value": "junior-dev-001",
            "new_value": "senior-dev-002",
            "description": "Assign to senior developer instead"
        }
    ]
})

# Compare all scenarios
what_if_compare()
```

### Monitoring Tools

Real-time visibility into system health:

```python
# Live dashboard
pipeline_monitor_dashboard()

# Track specific workflow
pipeline_monitor_flow({"flow_id": "flow_123"})

# Risk analysis
pipeline_predict_risk({"flow_id": "flow_123"})

# Get recommendations
pipeline_recommendations({"flow_id": "flow_123"})
```

### Analysis & Reporting Tools

Generate insights and reports:

```python
# Generate report
pipeline_report({
    "flow_id": "flow_123",
    "format": "html"  # or "markdown", "json"
})

# Compare flows
pipeline_compare({
    "flow_ids": ["flow_123", "flow_124", "flow_125"]
})

# Find similar past projects
pipeline_find_similar({
    "flow_id": "flow_123",
    "limit": 5
})
```

### Project Management Tools

High-level project control:

```python
# Create project from description
create_project({
    "description": "Build a REST API for recipe management with user auth",
    "project_name": "Recipe API",
    "options": {
        "team_size": 3,
        "tech_stack": ["python", "fastapi", "postgresql"],
        "deadline": "2024-03-01"
    }
})

# Add features
add_feature({
    "feature_description": "Add social sharing for recipes",
    "integration_point": "parallel"  # or "after_current", "new_phase"
})

# Check project health
get_project_status()

# List all agents
list_registered_agents()

# Check specific agent
get_agent_status({"agent_id": "backend-dev-001"})
```

## Marcus PM Internal Tools

These tools are used internally by Marcus for coordination:

- Pattern learning algorithms
- Task dependency analysis
- Skill matching logic
- Bottleneck detection
- AI-enhanced decision making

**Note**: These are not exposed through MCP as they're implementation details of Marcus's coordination logic.

## Common Patterns

### Coding Agent Work Loop

```python
# 1. Register once
agent = register_agent({...})

# 2. Work loop
while True:
    # Get task
    response = request_next_task({"agent_id": agent_id})
    if not response["task"]:
        break

    task = response["task"]

    # Understand context
    context = get_task_context({"task_id": task["id"]})

    # Work on task
    report_task_progress({
        "agent_id": agent_id,
        "task_id": task["id"],
        "status": "in_progress",
        "progress": 25,
        "message": "Setting up environment"
    })

    # Handle blockers
    if blocked:
        report_blocker({
            "agent_id": agent_id,
            "task_id": task["id"],
            "blocker_description": "Cannot connect to database",
            "severity": "high"
        })

    # Complete
    report_task_progress({
        "agent_id": agent_id,
        "task_id": task["id"],
        "status": "completed",
        "progress": 100,
        "message": "Implemented all endpoints with tests"
    })
```

### User Monitoring Pattern

```python
# Watch project in real-time
dashboard = pipeline_monitor_dashboard()

# Investigate issue
if dashboard["alerts"]:
    # Use replay to understand
    pipeline_replay_start({"flow_id": problem_flow})

    # Test fix
    what_if_start({"flow_id": problem_flow})
    what_if_simulate({...})

    # Get recommendations
    recs = pipeline_recommendations({"flow_id": problem_flow})
```

## Tool Permission Matrix

| Role | Can Plan | Can Execute | Can Monitor | Can Analyze |
|------|----------|-------------|-------------|-------------|
| User/Owner | ✅ | ❌ | ✅ | ✅ |
| Marcus PM | ✅ | ❌ | ✅ | ✅ |
| Coding Agent | ❌ | ✅ | ❌ | ❌ |

## Best Practices

### For Coding Agents

1. **Use only your 5 tools** - Don't try to access monitoring or planning tools
2. **Report progress frequently** - Keep Marcus and users informed
3. **Get context before starting** - Use `get_task_context` to understand dependencies
4. **Report blockers immediately** - Don't wait until deadline

### For Users/Owners

1. **Monitor without interfering** - Use observation tools, not execution tools
2. **Replay before assuming** - Understand what actually happened
3. **Simulate before changing** - Test modifications with what-if analysis
4. **Trust the separation** - Let Marcus coordinate, let agents execute

### For Tool Implementers

1. **Respect role boundaries** - Don't give agents access to user tools
2. **Keep interfaces simple** - Especially for coding agent tools
3. **Make tools discoverable** - Clear naming and documentation
4. **Fail gracefully** - Return helpful errors when tools are misused

## Troubleshooting

### "Tool not found" Error

Check that you're using tools appropriate for your role:
- Coding agents can only use the 5 essential tools
- Users cannot use agent execution tools
- Tools must be called with correct parameters

### "Permission denied" Error

This occurs when trying to use tools outside your role:
- Agents trying to use monitoring tools
- Users trying to directly execute tasks
- Missing authentication/registration

### "No task available" Response

This is normal and means:
- All tasks are assigned or completed
- No tasks match agent's skills
- Project is paused or finished

Simply wait and try again later.
