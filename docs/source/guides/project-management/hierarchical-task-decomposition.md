# Guide: Using Hierarchical Task Decomposition

## Overview

This guide explains how to use Marcus's Hierarchical Task Decomposition system to break down large tasks into manageable subtasks, assign them to agents, and track progress to completion.

## When to Use Hierarchical Decomposition

### Good Candidates for Decomposition

✅ **Large Features** (> 4 hours estimated)
```
Example: "Build user management API"
→ User model + Authentication + CRUD endpoints + Integration tests
```

✅ **Multi-Component Tasks**
```
Example: "Implement payment processing"
→ Payment gateway integration + Database schema + API endpoints + Receipt generation
```

✅ **Cross-Layer Features**
```
Example: "Add real-time notifications"
→ WebSocket server + Database events + Frontend components + Mobile push
```

✅ **Epic-Level Work**
```
Example: "Social media integration"
→ OAuth setup + Profile sync + Post sharing + Friend imports + Analytics
```

### Poor Candidates for Decomposition

❌ **Bug Fixes**
```
"Fix login redirect bug" - Focused scope, single component
```

❌ **Small Enhancements** (< 3 hours)
```
"Add email validation to signup form" - Atomic change
```

❌ **Refactoring Tasks**
```
"Refactor auth service to use dependency injection" - Keep changes cohesive
```

❌ **Deployment Tasks**
```
"Deploy v2.0 to production" - Coordinated execution required
```

❌ **Research/Exploration**
```
"Research best database for time-series data" - Exploratory work
```

## Decomposition Workflow

### Step 1: Create Parent Task

Create a task for the overall feature as you normally would:

```python
from src.integrations import create_task

task = await create_task(
    name="Build user management API",
    description="""
    Create a complete REST API for user management including:
    - User registration and authentication
    - Profile CRUD operations
    - Role-based permissions
    - Email verification
    - Password reset functionality
    """,
    estimated_hours=8.0,
    labels=["backend", "api", "security"],
    priority="high"
)
```

### Step 2: Automatic Decomposition Check

Marcus automatically evaluates if the task should be decomposed:

```python
from src.marcus_mcp.coordinator import should_decompose

if should_decompose(task):
    logger.info(f"Task {task.name} will be decomposed")
    # Decomposition will happen automatically
else:
    logger.info(f"Task {task.name} will be worked on as-is")
```

**Automatic Triggers**:
- Estimated hours >= 4.0
- Multiple component indicators (3+) in description
- Task type allows decomposition (not bugfix, deploy, etc.)

### Step 3: AI-Powered Breakdown

If decomposition is triggered, Marcus uses AI to create subtasks:

```python
from src.marcus_mcp.coordinator import decompose_task

decomposition = await decompose_task(
    task=task,
    ai_engine=state.ai_engine,
    project_context={
        "labels": task.labels,
        "existing_tasks": [t.name for t in state.project_tasks],
        "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
    }
)
```

**Decomposition Result**:
```python
{
    "success": True,
    "subtasks": [
        {
            "id": "task_123_sub_1",
            "name": "Create User database model",
            "description": "...",
            "estimated_hours": 2.0,
            "dependencies": [],
            "file_artifacts": ["src/models/user.py"],
            "provides": "User model with email validation and password hashing",
            "order": 1
        },
        {
            "id": "task_123_sub_2",
            "name": "Build authentication endpoints",
            "description": "...",
            "estimated_hours": 2.5,
            "dependencies": ["task_123_sub_1"],
            "file_artifacts": ["src/api/auth/login.py", "src/api/auth/register.py"],
            "provides": "POST /api/login, POST /api/register",
            "requires": "User model from subtask 1",
            "order": 2
        },
        # ... more subtasks ...
        {
            "id": "task_123_sub_integration",
            "name": "Integration testing and validation",
            "description": "...",
            "estimated_hours": 1.0,
            "dependencies": ["task_123_sub_1", "task_123_sub_2", ...],
            "file_artifacts": ["tests/integration/test_user_api.py"],
            "provides": "Validated, integrated user management system",
            "order": 99
        }
    ],
    "shared_conventions": {
        "base_path": "src/api/users/",
        "response_format": {
            "success": {"status": "ok", "data": {...}},
            "error": {"status": "error", "message": "..."}
        },
        "authentication": "JWT tokens in Authorization header",
        "naming_convention": "snake_case for endpoints"
    }
}
```

### Step 4: Store Subtasks

Marcus stores the decomposition in the SubtaskManager:

```python
from src.marcus_mcp.coordinator import SubtaskManager, SubtaskMetadata

# Store subtasks
metadata = SubtaskMetadata(
    shared_conventions=decomposition["shared_conventions"],
    decomposed_by="ai"
)

state.subtask_manager.add_subtasks(
    parent_task_id=task.id,
    subtasks=decomposition["subtasks"],
    metadata=metadata
)

logger.info(
    f"Decomposed '{task.name}' into {len(decomposition['subtasks'])} subtasks"
)
```

### Step 5: Subtask Assignment

When agents request work, subtasks are automatically prioritized:

```python
# Agent calls
await request_next_task(agent_id="dev-001")

# Marcus checks subtasks first
available_subtask = await find_available_subtask(
    state.subtask_manager,
    agent_id="dev-001",
    state.project_tasks
)

if available_subtask:
    # Dependencies satisfied, assign this subtask
    task = convert_subtask_to_task(available_subtask, state.subtask_manager)
    return task
```

**Assignment Rules**:
- Subtasks prioritized over regular tasks
- Dependencies must be satisfied (all required subtasks completed)
- Only one agent can work on a subtask at a time
- Integration subtask always assigned last

### Step 6: Agent Receives Enhanced Context

The assigned agent receives rich context about their subtask:

```python
context = await get_task_context(task_id="task_123_sub_2")

{
    "is_subtask": True,
    "subtask_info": {
        "name": "Build authentication endpoints",
        "provides": "POST /api/login, POST /api/register",
        "requires": "User model from subtask 1",
        "file_artifacts": ["src/api/auth/login.py", "src/api/auth/register.py"]
    },
    "parent_task": {
        "id": "task_123",
        "name": "Build user management API",
        "labels": ["backend", "api", "security"]
    },
    "shared_conventions": {
        "base_path": "src/api/users/",
        "response_format": {...},
        "authentication": "JWT tokens"
    },
    "dependency_artifacts": {
        "task_123_sub_1": {
            "name": "Create User database model",
            "provides": "User model with email validation",
            "file_artifacts": ["src/models/user.py"],
            "status": "done"
        }
    },
    "sibling_subtasks": [
        {"name": "Build CRUD endpoints", "status": "todo"},
        {"name": "Add role-based permissions", "status": "todo"},
        {"name": "Integration testing", "status": "todo"}
    ]
}
```

### Step 7: Track Progress

As subtasks complete, parent progress updates automatically:

```python
# Agent reports completion
await report_task_progress(
    agent_id="dev-001",
    task_id="task_123_sub_2",
    status="completed",
    progress=100,
    message="Authentication endpoints implemented with JWT support"
)

# System automatically:
# 1. Updates subtask status
state.subtask_manager.update_subtask_status(
    "task_123_sub_2",
    TaskStatus.DONE,
    "dev-001"
)

# 2. Updates parent progress
completed_count = sum(1 for s in subtasks if s.status == TaskStatus.DONE)
parent_progress = int((completed_count / len(subtasks)) * 100)
await kanban_client.update_task_progress("task_123", parent_progress)

# 3. Adds checklist update on parent task
await kanban_client.add_comment(
    "task_123",
    "✓ Subtask completed: Build authentication endpoints (66% overall)"
)
```

### Step 8: Parent Auto-Completion

When all subtasks finish, parent completes automatically:

```python
# After last subtask completes
if all(s.status == TaskStatus.DONE for s in subtasks):
    # Move parent to Done
    await kanban_client.move_task_to_done("task_123")

    # Add completion summary
    subtask_summary = "\n".join([
        f"✓ {s.name}" for s in subtasks
    ])
    await kanban_client.add_comment(
        "task_123",
        f"All subtasks completed:\n{subtask_summary}"
    )

    logger.info(f"Parent task {task.name} auto-completed")
```

## Best Practices

### Designing Good Decompositions

**1. Clear Interfaces**

Each subtask should have well-defined inputs and outputs:

✅ **Good**:
```python
Subtask("Build login endpoint")
  provides: "POST /api/login accepting {email, password}, returning {token, user}"
  requires: "User model with authenticate() method"
  file_artifacts: ["src/api/auth/login.py"]
```

❌ **Poor**:
```python
Subtask("Work on authentication")
  provides: "Auth stuff"
  requires: "Database"
  file_artifacts: ["src/auth/"]  # Too vague
```

**2. Minimal Coupling**

Subtasks should be as independent as possible:

✅ **Good** - Can test independently:
```python
[
    Subtask("User model with validation"),
    Subtask("Login endpoint"),  # Uses model interface
    Subtask("Registration endpoint"),  # Uses model interface
    Subtask("Password reset endpoint")  # Uses model interface
]
```

❌ **Poor** - Tightly coupled:
```python
[
    Subtask("User model and login endpoint together"),  # Coupled
    Subtask("Registration using login code")  # Unnecessary dependency
]
```

**3. Right-Sized Subtasks**

Aim for 1-3 hours per subtask:

✅ **Good**:
```python
[
    Subtask("User model", 2h),
    Subtask("Login endpoint", 1.5h),
    Subtask("Registration endpoint", 1.5h),
    Subtask("Integration tests", 1h)
]
```

❌ **Poor**:
```python
[
    Subtask("All database models", 8h),  # Too large
    Subtask("Add logging statement", 0.1h)  # Too small
]
```

**4. Sequential When Needed**

Don't force parallelization when components are tightly coupled:

✅ **Good** - Logical sequence:
```python
[
    Subtask("Database schema", order=1, deps=[]),
    Subtask("Data access layer", order=2, deps=["schema"]),
    Subtask("Business logic", order=3, deps=["data_access"]),
    Subtask("API endpoints", order=4, deps=["business_logic"])
]
```

❌ **Poor** - Forced parallelization:
```python
[
    Subtask("Database schema", deps=[]),
    Subtask("API endpoints", deps=[]),  # Needs schema!
    # Will fail at integration
]
```

**5. Always Include Integration**

Explicitly test that components work together:

✅ **Good**:
```python
[
    ...feature subtasks...,
    Subtask("Integration testing and validation",
        deps=["all previous subtasks"],
        description="""
        - Run end-to-end workflow tests
        - Validate all interfaces work together
        - Check error handling across components
        - Create integration documentation
        """,
        order=99  # Always last
    )
]
```

### Working with Subtasks as an Agent

**1. Read the Context**

Always review the enhanced context before starting:

```python
# Check what you're providing
subtask_info["provides"]  # What interfaces you must create

# Check what you can use
for dep_id, artifact in dependency_artifacts.items():
    print(f"Available: {artifact['provides']}")
    print(f"Location: {artifact['file_artifacts']}")

# Follow shared conventions
conventions = shared_conventions
base_path = conventions["base_path"]  # Where to put files
response_format = conventions["response_format"]  # API format
```

**2. Follow Shared Conventions**

Consistency is critical for integration:

```python
# Use the shared response format
@app.post("/api/login")
async def login(credentials: LoginRequest):
    try:
        user = await authenticate(credentials)
        return {
            "status": "ok",  # Convention from shared_conventions
            "data": {
                "token": generate_jwt(user),
                "user": user.to_dict()
            }
        }
    except AuthenticationError as e:
        return {
            "status": "error",  # Convention
            "message": str(e)
        }
```

**3. Create Promised Artifacts**

Deliver exactly what you promised:

```python
# Subtask promises: "POST /api/login returning {token, user}"
# Must implement this interface exactly

# If you change the interface, update the subtask:
await update_subtask_interface(
    subtask_id,
    provides="POST /api/login returning {token, user, expires_at}"
)
```

**4. Report Progress Regularly**

Keep Marcus informed at 25%, 50%, 75%, 100%:

```python
# At 25% - Foundation complete
await report_task_progress(agent_id, subtask_id, status="in_progress",
    progress=25, message="User model loaded, starting endpoint implementation")

# At 50% - Core logic complete
await report_task_progress(agent_id, subtask_id, status="in_progress",
    progress=50, message="Login endpoint implemented, adding validation")

# At 75% - Testing
await report_task_progress(agent_id, subtask_id, status="in_progress",
    progress=75, message="Validation complete, writing tests")

# At 100% - Done
await report_task_progress(agent_id, subtask_id, status="completed",
    progress=100, message="Login endpoint complete with tests")
```

## Monitoring and Debugging

### Check Subtask Status

View all subtasks for a parent task:

```python
subtasks = state.subtask_manager.get_subtasks_for_parent("task_123")

for subtask in subtasks:
    print(f"{subtask.name}:")
    print(f"  Status: {subtask.status}")
    print(f"  Assigned: {subtask.assigned_to or 'Unassigned'}")
    print(f"  Dependencies: {subtask.dependencies}")
    print(f"  Provides: {subtask.provides}")
```

### Monitor Parent Progress

Track overall feature completion:

```python
progress = state.subtask_manager.get_parent_completion_percentage("task_123")
print(f"Feature completion: {progress}%")

# Get breakdown
completed = [s for s in subtasks if s.status == TaskStatus.DONE]
in_progress = [s for s in subtasks if s.status == TaskStatus.IN_PROGRESS]
todo = [s for s in subtasks if s.status == TaskStatus.TODO]

print(f"Completed: {len(completed)}/{len(subtasks)}")
print(f"In Progress: {len(in_progress)}")
print(f"Todo: {len(todo)}")
```

### Verify Dependencies

Ensure subtask dependencies are satisfied:

```python
subtask = state.subtask_manager.subtasks["task_123_sub_3"]

can_start = state.subtask_manager.can_assign_subtask(
    subtask.id,
    state.project_tasks
)

if not can_start:
    missing_deps = [
        dep_id for dep_id in subtask.dependencies
        if state.subtask_manager.subtasks[dep_id].status != TaskStatus.DONE
    ]
    print(f"Cannot start - waiting for: {missing_deps}")
```

### Debug Assignment Issues

If subtasks aren't being assigned:

```python
# Check if subtask manager is initialized
if not hasattr(state, 'subtask_manager') or not state.subtask_manager:
    logger.error("SubtaskManager not initialized!")

# Check parent task status
parent_task = find_task_by_id("task_123")
if parent_task.status != TaskStatus.TODO:
    logger.warning(f"Parent task not in TODO status: {parent_task.status}")

# Check for assignment conflicts
all_assigned = state.assignment_persistence.get_all_assignments()
if subtask.id in all_assigned.values():
    logger.warning(f"Subtask already assigned to {all_assigned[subtask.id]}")
```

## Common Patterns

### Backend Feature Decomposition

```python
# Pattern: API + Database + Business Logic
[
    Subtask("Database schema and models", 2h),
    Subtask("Data access layer", 1.5h, deps=["schema"]),
    Subtask("Business logic services", 2h, deps=["data_access"]),
    Subtask("REST API endpoints", 2h, deps=["services"]),
    Subtask("API tests and documentation", 1h, deps=["api"]),
    Subtask("Integration validation", 0.5h, deps=["tests"])
]
```

### Full-Stack Feature Decomposition

```python
# Pattern: Backend + Frontend + Integration
[
    # Backend
    Subtask("Backend API endpoints", 2.5h),
    Subtask("Backend tests", 1h, deps=["backend_api"]),

    # Frontend
    Subtask("Frontend components", 2h, deps=["backend_api"]),
    Subtask("State management", 1h, deps=["components"]),
    Subtask("Frontend tests", 1h, deps=["state"]),

    # Integration
    Subtask("E2E integration tests", 1.5h, deps=["backend_tests", "frontend_tests"]),
    Subtask("Documentation and deployment", 1h, deps=["integration_tests"])
]
```

### Migration/Refactoring Decomposition

```python
# Pattern: Prepare + Migrate + Validate
[
    Subtask("Create new schema/structure", 2h),
    Subtask("Write migration script", 1.5h, deps=["schema"]),
    Subtask("Test migration on copy", 1h, deps=["script"]),
    Subtask("Run migration", 0.5h, deps=["test"]),
    Subtask("Validate data integrity", 1h, deps=["run"]),
    Subtask("Update dependent code", 2h, deps=["validate"]),
    Subtask("Integration testing", 1h, deps=["update"])
]
```

## Troubleshooting

### Subtasks Not Being Assigned

**Problem**: Agents request tasks but don't get subtasks

**Solutions**:

1. Verify SubtaskManager is initialized:
```python
# In src/marcus_mcp/server.py
self.subtask_manager = SubtaskManager()
```

2. Check parent task status:
```python
# Parent must be in TODO
parent_task.status == TaskStatus.TODO
```

3. Verify dependencies are satisfied:
```python
subtask = state.subtask_manager.subtasks[subtask_id]
for dep_id in subtask.dependencies:
    dep_subtask = state.subtask_manager.subtasks[dep_id]
    assert dep_subtask.status == TaskStatus.DONE
```

### Parent Not Auto-Completing

**Problem**: All subtasks done but parent still in progress

**Solutions**:

1. Ensure completion handler is called:
```python
# In report_task_progress
if status == "completed" and task_id in state.subtask_manager.subtasks:
    await check_and_complete_parent_task(
        parent_task_id,
        state.subtask_manager,
        state.kanban_client
    )
```

2. Verify all subtasks actually completed:
```python
subtasks = state.subtask_manager.get_subtasks_for_parent(parent_id)
incomplete = [s for s in subtasks if s.status != TaskStatus.DONE]
if incomplete:
    logger.warning(f"Incomplete subtasks: {[s.name for s in incomplete]}")
```

### Context Missing for Subtasks

**Problem**: Agents don't receive enhanced subtask context

**Solutions**:

1. Verify get_task_context is using enhanced version:
```python
# Should include subtask-specific logic
if task_id in state.subtask_manager.subtasks:
    context["is_subtask"] = True
    context["subtask_info"] = {...}
```

2. Check SubtaskManager has subtask registered:
```python
if subtask_id not in state.subtask_manager.subtasks:
    logger.error(f"Subtask {subtask_id} not found in manager")
```

## Examples

See the complete working example in `examples/task_decomposition_demo.py`:

```bash
cd /path/to/marcus
python examples/task_decomposition_demo.py
```

This demonstrates:
- Creating a parent task
- Automatic decomposition
- Subtask assignment
- Progress tracking
- Parent auto-completion

## Next Steps

- **[Concept: Hierarchical Task Decomposition](../../concepts/hierarchical-task-decomposition.md)** - Understanding the system
- **[System: Task Decomposition](../../systems/project-management/54-hierarchical-task-decomposition.md)** - Technical architecture
- **[Integration Guide](../../../task-decomposition-integration.md)** - Developer integration instructions

---

*Hierarchical Task Decomposition makes large features manageable by breaking them into well-defined subtasks with clear interfaces and shared conventions.*
