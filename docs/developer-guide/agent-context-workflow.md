# Agent Context and Decision Workflow Guide

## Overview

Marcus enables autonomous agents to work independently while sharing context through a centralized PM system. This guide explains how to configure agents to use the context and decision logging tools effectively.

## Key Tools for Context Sharing

### 1. `get_task_context`
Retrieves full context for a task including:
- Previous architectural decisions
- Implementation details from dependencies
- API endpoints and data models created
- Patterns established by other agents

### 2. `log_decision`
Records architectural decisions that affect other tasks:
- Technical choices (database, frameworks, patterns)
- API contracts and data schemas
- Security decisions
- Naming conventions

## Agent System Prompt Configuration

### Required Tool Access

Agents need these tools in their allowed list:
```
- register_agent
- request_next_task
- report_task_progress
- report_blocker
- get_project_status
- get_agent_status
- log_decision        # For recording decisions
- get_task_context    # For reading context
```

### System Prompt Sections

#### 1. Context Awareness Section
```
WHEN TO USE get_task_context:
- Your task has dependencies listed: Always check what those tasks built
- Task description mentions "integrate with", "extend", "based on"
- You need to understand existing patterns
- Task seems to build on previous work

Example triggers:
- "Add user profile management" → get_task_context on user/auth tasks
- Dependencies: ["task-123"] → Always get_task_context("task-123")
```

#### 2. Decision Logging Section
```
WHEN TO USE log_decision:
- Choosing between technical approaches
- Defining API contracts or data schemas
- Making security decisions
- Selecting libraries or frameworks
- Establishing patterns others should follow

Format: "I chose X because Y. This affects Z."
```

## Workflow Examples

### Example 1: Backend API Development

```python
# Agent A: Authentication Task
async def agent_a_workflow():
    # 1. Get task with no dependencies
    task = await request_next_task("agent-a")
    # Task: "Design Authentication System"

    # 2. Make architectural decisions
    await log_decision(
        "agent-a",
        "task-001",
        "I chose JWT with RS256 because it allows stateless auth across microservices. This affects all API endpoints."
    )

    # 3. Complete with implementation details
    await report_task_progress(
        "agent-a",
        "task-001",
        "completed",
        100,
        "Implemented auth: POST /api/auth/login returns {token, refreshToken}"
    )

# Agent B: User Profile Task
async def agent_b_workflow():
    # 1. Get task with dependencies
    task = await request_next_task("agent-b")
    # Task: "Create User Profile API"
    # Dependencies: ["task-001"]

    # 2. Check context from dependencies
    context = await get_task_context("task-001")
    # Discovers: JWT with RS256, Redis for keys

    # 3. Make compatible decisions
    await log_decision(
        "agent-b",
        "task-002",
        "I'm using the JWT validation from auth module. This affects all user endpoints."
    )

    # 4. Build on previous work
    await report_task_progress(
        "agent-b",
        "task-002",
        "completed",
        100,
        "Implemented user API: GET /api/users/profile (requires JWT)"
    )
```

### Example 2: Frontend Integration

```python
# Agent C: Frontend Task
async def agent_c_workflow():
    # 1. Get frontend task
    task = await request_next_task("agent-c")
    # Task: "Create User Dashboard"
    # Dependencies: ["task-001", "task-002"]

    # 2. Get context from multiple dependencies
    auth_context = await get_task_context("task-001")
    user_context = await get_task_context("task-002")

    # 3. Understand the full API surface
    # From context learns:
    # - POST /api/auth/login for authentication
    # - GET /api/users/profile for user data
    # - Needs to handle JWT tokens

    # 4. Make frontend decisions
    await log_decision(
        "agent-c",
        "task-003",
        "I'm storing JWT in httpOnly cookies because of XSS concerns. This affects all frontend API calls."
    )
```

## Best Practices

### 1. Always Check Dependencies
```python
if task.dependencies:
    for dep_id in task.dependencies:
        context = await get_task_context(dep_id)
        # Review decisions and implementations
```

### 2. Log Decisions with Impact
```python
# GOOD - Explains impact
await log_decision(
    agent_id,
    task_id,
    "I chose PostgreSQL over MongoDB because we need ACID transactions. This affects all data models which must be relational."
)

# BAD - No impact explained
await log_decision(
    agent_id,
    task_id,
    "Using PostgreSQL"
)
```

### 3. Build on Existing Patterns
When context shows existing patterns:
- Follow the same naming conventions
- Use the same authentication approach
- Match API response formats
- Reuse established libraries

### 4. Document Integration Points
In progress reports, clearly state:
- What existing APIs you're using
- What new APIs you're creating
- Expected request/response formats
- Authentication requirements

## Common Patterns

### API Endpoint Consistency
If context shows:
```
GET /api/users returns {items: [...], total: 10}
```

You should create:
```
GET /api/products returns {items: [...], total: 20}
```

### Authentication Pattern
If context shows JWT with Bearer tokens:
```
Authorization: Bearer <token>
```

All your endpoints should follow the same pattern.

### Error Response Format
If context shows:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token has expired"
  }
}
```

Match this format in your implementations.

## Debugging Context Issues

### 1. Context Not Found
```python
context = await get_task_context("task-123")
if not context["success"]:
    # Task might not exist or context system not enabled
    # Proceed with reasonable defaults
```

### 2. Understanding Complex Dependencies
```python
# Get your task's context to see all dependencies
my_context = await get_task_context(current_task_id)
# This shows decisions from ALL dependencies
```

### 3. Tracing Decision Impact
When making decisions, always include:
- What you chose
- Why you chose it
- What tasks/components it affects

This helps future agents understand the rationale.

## Summary

The context and decision system enables:
1. **Autonomous agents** working independently
2. **Shared understanding** through Marcus
3. **Consistent patterns** across the project
4. **Clear documentation** of architectural choices

Configure agents with both `get_task_context` and `log_decision` tools to participate fully in this collaborative workflow.
