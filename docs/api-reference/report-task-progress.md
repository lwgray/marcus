# `report_task_progress` MCP Tool Reference

## Overview

The `report_task_progress` tool allows agents to report their progress on assigned tasks to Marcus. This is the primary mechanism for updating task status, tracking completion percentage, and providing visibility into agent activities.

## Function Signature

```python
async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int = 0,
    message: str = ""
) -> Dict[str, Any]
```

## Parameters

### `agent_id` (required)
- **Type:** `str`
- **Description:** Unique identifier of the agent reporting progress
- **Must:** Match a previously registered agent ID
- **Example:** `"calculator-agent"`, `"dev-001"`

### `task_id` (required)
- **Type:** `str`
- **Description:** Unique identifier of the task being updated
- **Must:** Match a task ID from a previous task assignment (from `request_next_task`)
- **Example:** `"task-123"`, `"abc123def456"` <!-- pragma: allowlist secret -->

### `status` (required)
- **Type:** `str`
- **Description:** Current task status
- **Valid Values:**
  - `"in_progress"` - Task is actively being worked on
  - `"completed"` - Task has been fully completed (triggers cleanup)
  - `"blocked"` - Task cannot proceed due to dependencies or issues
  - `"paused"` - Task work has been temporarily suspended
- **Example:** `"in_progress"`

### `progress` (optional)
- **Type:** `int`
- **Default:** `0`
- **Range:** `0` to `100`
- **Description:** Completion percentage
- **Should reflect:** Actual work completed, not time elapsed
- **Best Practice:** Report at milestones (0%, 25%, 50%, 75%, 100%)
- **Example:** `50`

### `message` (optional)
- **Type:** `str`
- **Default:** `""`
- **Description:** Descriptive message about current progress
- **Should include:** Meaningful details about what was accomplished
- **Example:** `"Completed database schema design and validation"`

## Return Value

Returns a `Dict[str, Any]` containing:

```python
{
    "success": True,          # bool - whether the report was processed
    "message": "...",         # str - feedback message
    "task_id": "...",        # str - confirming the updated task
    "status": "...",         # str - confirming the new status
    "progress": 100          # int - confirming the progress percentage
}
```

## What Happens When You Report Progress

### When `status="in_progress"`
1. ✅ Updates task status to IN_PROGRESS in kanban
2. ✅ Updates progress percentage
3. ✅ Renews task lease (prevents timeout/reassignment)
4. ✅ Logs progress update for monitoring
5. ✅ Updates checklist items if applicable

### When `status="completed"`
1. ✅ Updates task status to DONE in kanban
2. ✅ Sets completion timestamp
3. ✅ Records completion in Memory system (for AI learning)
4. ✅ Clears agent's current task assignment
5. ✅ Removes task lease
6. ✅ Increments agent's completed task count
7. ✅ **Makes dependent tasks available for assignment**
8. 🔍 Runs code analysis (for GitHub projects)
9. 📊 Updates project completion metrics

### When `status="blocked"`
1. ⚠️ Updates task status to BLOCKED in kanban
2. ⚠️ Records blocker in Memory system
3. ⚠️ Logs blocker for investigation
4. ℹ️ Task remains assigned to agent
5. 💡 Consider using `report_blocker` tool instead for AI-powered suggestions

### When `status="paused"`
1. ⏸️ Updates task status to PAUSED
2. ℹ️ Task remains assigned to agent
3. 📝 Logs pause message
4. ⏱️ Lease continues (task not released)

## Best Practices

### Report at Key Milestones

```python
# When starting a task
await client.report_task_progress(
    agent_id="dev-001",
    task_id="task-123",
    status="in_progress",
    progress=0,
    message="Started analysis of requirements"
)

# At 25% completion
await client.report_task_progress(
    agent_id="dev-001",
    task_id="task-123",
    status="in_progress",
    progress=25,
    message="Completed database schema design and validation"
)

# At 50% completion
await client.report_task_progress(
    agent_id="dev-001",
    task_id="task-123",
    status="in_progress",
    progress=50,
    message="Implemented core API endpoints with error handling"
)

# At 75% completion
await client.report_task_progress(
    agent_id="dev-001",
    task_id="task-123",
    status="in_progress",
    progress=75,
    message="Added comprehensive test coverage and documentation"
)

# When completing
await client.report_task_progress(
    agent_id="dev-001",
    task_id="task-123",
    status="completed",
    progress=100,
    message="Task completed successfully. All tests passing, deployed to staging."
)
```

### Use Descriptive Messages

❌ **Bad:**
```python
message="Done"
message="Working on it"
message="Almost there"
```

✅ **Good:**
```python
message="Implemented user authentication with JWT tokens and bcrypt password hashing"
message="Created 15 unit tests covering all edge cases, achieved 95% code coverage"
message="Refactored database layer to use connection pooling, improved query performance by 40%"
```

### Progress Should Reflect Work, Not Time

❌ **Bad:**
```python
# After 1 hour of a 4-hour task
progress=25  # Based on time elapsed
```

✅ **Good:**
```python
# After completing 1 of 4 major components
progress=25  # Based on actual work completed
```

## Common Patterns

### Simple Task Workflow

```python
# Start work
await client.report_task_progress(
    agent_id="agent-1",
    task_id="task-456",
    status="in_progress",
    progress=0,
    message="Starting implementation"
)

# Do work...
await asyncio.sleep(5)

# Complete work
await client.report_task_progress(
    agent_id="agent-1",
    task_id="task-456",
    status="completed",
    progress=100,
    message="Implementation complete and tested"
)
```

### Long-Running Task with Milestones

```python
task_id = "task-789"

# Start
await client.report_task_progress(
    agent_id="agent-2",
    task_id=task_id,
    status="in_progress",
    progress=0,
    message="Analyzing requirements"
)

# Milestone 1: Design complete
await client.report_task_progress(
    agent_id="agent-2",
    task_id=task_id,
    status="in_progress",
    progress=25,
    message="Completed system design and architecture diagram"
)

# Milestone 2: Implementation complete
await client.report_task_progress(
    agent_id="agent-2",
    task_id=task_id,
    status="in_progress",
    progress=50,
    message="Implemented all core features with error handling"
)

# Milestone 3: Testing complete
await client.report_task_progress(
    agent_id="agent-2",
    task_id=task_id,
    status="in_progress",
    progress=75,
    message="All tests passing, code coverage at 90%"
)

# Complete
await client.report_task_progress(
    agent_id="agent-2",
    task_id=task_id,
    status="completed",
    progress=100,
    message="Documentation updated, PR merged to main"
)
```

### Handling Blockers

```python
# Option 1: Use report_task_progress with "blocked" status
await client.report_task_progress(
    agent_id="agent-3",
    task_id="task-999",
    status="blocked",
    progress=30,
    message="Cannot proceed: waiting for API credentials from admin"
)

# Option 2 (RECOMMENDED): Use report_blocker for AI-powered suggestions
await client.report_blocker(
    agent_id="agent-3",
    task_id="task-999",
    blocker_description="Cannot access production database - missing credentials",
    severity="high"
)
```

## Errors and Exceptions

### Common Errors

```python
# Invalid status
ValueError: status must be one of: in_progress, completed, blocked, paused

# Invalid progress
ValueError: progress must be between 0 and 100

# Invalid agent_id
RuntimeError: Agent 'unknown-agent' not registered

# Invalid task_id
RuntimeError: Task 'unknown-task' not found

# Task not assigned to agent
RuntimeError: Task 'task-123' is not assigned to agent 'agent-1'
```

## Integration with Other Systems

### Dependency Management
When you report `status="completed"`:
- ✅ Marcus checks for dependent tasks
- ✅ Dependent tasks become available for assignment
- ✅ Other agents can immediately request those tasks via `request_next_task`

### Memory System
Progress reports feed the Memory system:
- 📈 Learns agent performance patterns
- 🎯 Improves task assignment accuracy
- ⏱️ Refines time estimation predictions
- 🚫 Identifies common blockers

### Lease System
Progress reports renew task leases:
- 🔒 Prevents task timeout and reassignment
- ⏰ Extends lease expiration time
- 🔄 Resets abandonment detection

### Monitoring & Visualization
Progress reports enable:
- 📊 Real-time project dashboards
- 📈 Progress charts and metrics
- 🔍 Agent activity tracking
- 📝 Audit logs and history

## See Also

- [`request_next_task`](./request-next-task.md) - Get your next task assignment
- [`report_blocker`](./report-blocker.md) - Report blockers with AI suggestions
- [`check_task_dependencies`](./check-task-dependencies.md) - Check what depends on a task
- [Agent Workflow Guide](../guides/agent-workflows/README.md) - Complete agent lifecycle
