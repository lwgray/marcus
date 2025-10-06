# Task Decomposition Integration Guide

This document explains how to integrate hierarchical task decomposition into Marcus.

## Overview

The task decomposition system allows large tasks to be automatically broken down into smaller subtasks that can be worked on independently or sequentially. Each subtask has clear interfaces, dependencies, and file artifacts.

## Architecture

```
┌─────────────────────────────────────────────┐
│         Task Assignment Flow                 │
├─────────────────────────────────────────────┤
│                                              │
│  request_next_task()                         │
│         │                                    │
│         ▼                                    │
│  Check for decomposed tasks                  │
│         │                                    │
│    ┌────┴────┐                               │
│    │ Yes     │ No                            │
│    ▼         ▼                               │
│  Serve    Regular                            │
│  Subtask   Task                              │
│    │         │                               │
│    └────┬────┘                               │
│         │                                    │
│         ▼                                    │
│   Assign to Agent                            │
└─────────────────────────────────────────────┘
```

## Integration Steps

### 1. Add SubtaskManager to MarcusServer

In `src/marcus_mcp/server.py`, add the subtask manager to server initialization:

```python
from src.marcus_mcp.coordinator import SubtaskManager

class MarcusServer:
    def __init__(self):
        # ... existing initialization ...

        # Add subtask manager
        self.subtask_manager = SubtaskManager()
```

### 2. Integrate with Task Assignment

Modify `find_optimal_task_for_agent` in `src/marcus_mcp/tools/task.py`:

```python
from src.marcus_mcp.coordinator.task_assignment_integration import (
    find_optimal_task_with_subtasks
)

async def find_optimal_task_for_agent(
    agent_id: str, state: Any
) -> Optional[Task]:
    """Find optimal task, checking subtasks first."""

    # Use integrated finder that checks subtasks
    return await find_optimal_task_with_subtasks(
        agent_id,
        state,
        fallback_task_finder=_find_optimal_task_basic_logic,
    )
```

### 3. Handle Subtask Completion

Modify `report_task_progress` to handle subtask completion:

```python
from src.marcus_mcp.coordinator.subtask_assignment import (
    check_and_complete_parent_task,
    update_subtask_progress_in_parent,
)

async def report_task_progress(
    agent_id: str, task_id: str, status: str,
    progress: int, message: str, state: Any
) -> Dict[str, Any]:
    # ... existing logic ...

    if status == "completed":
        # Check if this is a subtask
        if (hasattr(state, "subtask_manager") and
            state.subtask_manager and
            task_id in state.subtask_manager.subtasks):

            # Update subtask status
            state.subtask_manager.update_subtask_status(
                task_id, TaskStatus.DONE, agent_id
            )

            # Get parent task ID
            subtask = state.subtask_manager.subtasks[task_id]
            parent_task_id = subtask.parent_task_id

            # Update parent progress
            await update_subtask_progress_in_parent(
                parent_task_id,
                task_id,
                state.subtask_manager,
                state.kanban_client,
            )

            # Check if parent is complete
            await check_and_complete_parent_task(
                parent_task_id,
                state.subtask_manager,
                state.kanban_client,
            )

    # ... rest of existing logic ...
```

### 4. Automatic Task Decomposition

When creating tasks, optionally decompose large ones:

```python
from src.marcus_mcp.coordinator import should_decompose, decompose_task

async def create_task_with_decomposition(
    task_data: Dict[str, Any],
    state: Any,
) -> Task:
    # Create the parent task
    task = await state.kanban_client.create_task(task_data)

    # Check if it should be decomposed
    if should_decompose(task):
        # Decompose using AI
        decomposition = await decompose_task(
            task,
            state.ai_engine,
            project_context={
                "labels": task.labels,
                "existing_tasks": [t.name for t in state.project_tasks],
            },
        )

        if decomposition["success"]:
            # Store subtasks
            from src.marcus_mcp.coordinator import SubtaskMetadata

            metadata = SubtaskMetadata(
                shared_conventions=decomposition["shared_conventions"],
                decomposed_by="ai",
            )

            state.subtask_manager.add_subtasks(
                task.id,
                decomposition["subtasks"],
                metadata,
            )

            logger.info(
                f"Decomposed task {task.name} into "
                f"{len(decomposition['subtasks'])} subtasks"
            )

    return task
```

## Features

### Automatic Integration Subtask

Every decomposed task automatically gets a final integration subtask that:
- Verifies all components work together
- Runs integration tests
- Creates consolidated documentation
- Validates all file outputs

### Shared Conventions

All subtasks share conventions to avoid integration issues:
- **Base path**: Common directory for outputs
- **File structure**: Standard organization pattern
- **Response format**: Consistent API formats
- **Naming conventions**: Unified naming across files

### Parent Task Auto-Completion

When all subtasks complete:
1. Parent task automatically moves to "Done"
2. Progress reaches 100%
3. Completion comment added with subtask list
4. Triggers any dependent tasks

## Context for Subtasks

Agents working on subtasks get enhanced context via `get_task_context`:

```python
{
  "is_subtask": true,
  "subtask_info": {
    "name": "Build login endpoint",
    "description": "...",
    "file_artifacts": ["src/api/auth/login.py"],
    "provides": "POST /api/login returning {token, user}",
    "requires": "User model from subtask 1"
  },
  "parent_task": {
    "id": "task-123",
    "name": "Build authentication system",
    "description": "...",
    "labels": ["backend", "security"]
  },
  "shared_conventions": {
    "base_path": "src/api/",
    "response_format": {...}
  },
  "dependency_artifacts": {
    "task-123_sub_1": {
      "name": "Create User model",
      "provides": "User model with email validation",
      "file_artifacts": ["src/models/user.py"],
      "status": "done"
    }
  },
  "sibling_subtasks": [...]
}
```

## Best Practices

### When to Decompose

✅ **Do decompose:**
- Tasks estimated > 4 hours
- Tasks with multiple components (API + DB + UI)
- Tasks with clear sequential phases
- Epic-level features

❌ **Don't decompose:**
- Bug fixes
- Small enhancements (< 3 hours)
- Refactoring tasks
- Deployment tasks
- Research/exploration work

### Decomposition Quality

Good decompositions have:
- **Clear interfaces**: Each subtask has well-defined inputs/outputs
- **Minimal coupling**: Subtasks can be tested independently
- **Sequential when needed**: Don't parallelize tightly coupled work
- **File ownership**: Each subtask primarily works on its own files

### Integration Testing

Always include integration testing in the final subtask:
- End-to-end workflow validation
- Interface compatibility checks
- Consolidated documentation
- Performance benchmarks (if applicable)

## Example

### Original Task
```
Task: Build user management API
Estimated: 8 hours
Description: Create REST API for user management with CRUD operations
```

### Decomposed Subtasks

1. **Create User model** (2h)
   - File: `src/models/user.py`
   - Provides: User model with email validation
   - Dependencies: None

2. **Build authentication** (2.5h)
   - Files: `src/api/auth/login.py`, `src/api/auth/register.py`
   - Provides: POST /api/login, POST /api/register
   - Dependencies: Subtask 1

3. **CRUD endpoints** (2.5h)
   - Files: `src/api/users/*.py`
   - Provides: GET/PUT/DELETE /api/users
   - Dependencies: Subtasks 1, 2

4. **Integration & validation** (1h) *[AUTO-GENERATED]*
   - Files: `docs/integration_report.md`, `tests/integration/test_users.py`
   - Provides: Validated, integrated solution
   - Dependencies: All previous subtasks

## Monitoring

Track decomposition effectiveness:
- Average time per subtask vs. estimates
- Parent completion rate
- Integration subtask failure rate
- Agent satisfaction with subtask clarity

## Troubleshooting

### Subtasks not being assigned

Check:
1. `subtask_manager` is initialized in server
2. Parent task is in TODO status
3. Dependencies are satisfied
4. Subtask not already assigned

### Parent not auto-completing

Check:
1. All subtasks show status=DONE
2. `check_and_complete_parent_task` is called
3. Kanban client has update permissions

### Context missing for subtasks

Check:
1. `get_task_context` enhanced version is active
2. SubtaskManager has the subtask tracked
3. Parent task exists in project_tasks
