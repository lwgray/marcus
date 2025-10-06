# Hierarchical Task Decomposition

## Overview

Hierarchical Task Decomposition is Marcus's system for intelligently breaking down large, complex tasks into smaller, manageable subtasks that can be worked on autonomously. This system enables better parallelization, clearer interfaces, and improved coordination while maintaining Marcus's core values of guided autonomy and context-rich task management.

## The Problem

In real-world software development, tasks vary dramatically in size and complexity. A task like "Build user management system" might be appropriate for a project plan, but it's too large and ambiguous for a single agent to work on effectively. Breaking it down manually is time-consuming and requires deep technical understanding.

### Challenges with Large Tasks

**Ambiguity**: Large tasks contain multiple components that need clear interfaces
```
Task: "Build authentication system"
Questions: What about password reset? 2FA? Social login? Session management?
```

**Integration Risk**: Multiple components need to work together seamlessly
```
Problem: Agent 1 builds API with JWT, Agent 2 expects sessions
Result: Integration failure, rework required
```

**Coordination Overhead**: Agents need to understand how their work fits together
```
Without decomposition: "Build auth" → unclear scope, duplicate work, integration issues
With decomposition: "Create User model" → "Build login API" → "Add session management"
```

**Progress Tracking**: Hard to measure completion on monolithic tasks
```
Task: "Build authentication" - 50% complete
What does 50% mean? Which parts are done? What's left?
```

## The Solution

Marcus uses **AI-powered hierarchical task decomposition** to automatically break large tasks into well-defined subtasks with clear interfaces, dependencies, and shared conventions.

### Key Principles

**1. Intelligent Decomposition**

Marcus uses heuristics and AI analysis to decide which tasks benefit from decomposition:

✅ **Decompose when**:
- Task estimated > 4 hours
- Multiple distinct components (API + DB + UI)
- Clear sequential phases
- Epic-level features

❌ **Keep intact when**:
- Bug fixes (focused scope)
- Small enhancements (< 3 hours)
- Refactoring tasks (atomic changes)
- Deployment tasks (coordinated execution)

**2. Clear Interfaces**

Every subtask defines what it provides and what it requires:

```python
Subtask("Create User model")
  provides: "User model with email validation, password hashing"
  requires: None  # Foundation task
  file_artifacts: ["src/models/user.py"]

Subtask("Build login endpoint")
  provides: "POST /api/login returning {token, user}"
  requires: "User model from subtask 1"
  file_artifacts: ["src/api/auth/login.py"]

Subtask("Add session management")
  provides: "Session tracking and refresh tokens"
  requires: "Login endpoint from subtask 2"
  file_artifacts: ["src/api/auth/sessions.py"]
```

**3. Shared Conventions**

All subtasks in a decomposition share common patterns to avoid integration issues:

```python
shared_conventions = {
    "base_path": "src/api/auth/",
    "response_format": {
        "success": {"status": "ok", "data": {...}},
        "error": {"status": "error", "message": "..."}
    },
    "authentication": "JWT tokens in Authorization header",
    "naming_convention": "snake_case for endpoints, camelCase for JSON"
}
```

**4. Automatic Integration Subtask**

Every decomposition automatically includes a final integration subtask that:
- Verifies all components work together
- Runs end-to-end tests
- Creates consolidated documentation
- Validates all promised interfaces

**5. Parent Auto-Completion**

When all subtasks complete, the parent task automatically:
- Moves to "Done" status
- Updates progress to 100%
- Adds completion comment with subtask summary
- Triggers dependent tasks

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│           Hierarchical Task Decomposition System             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │  Decomposer      │  │  SubtaskManager   │               │
│  │                  │  │                   │               │
│  │ • should_decomp  │  │ • Track subtasks  │               │
│  │ • AI breakdown   │  │ • Manage state   │               │
│  │ • Conventions    │  │ • Persistence    │               │
│  │ • Integration    │  │ • Completion     │               │
│  └──────────────────┘  └──────────────────┘               │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      │                                      │
│  ┌───────────────────┼─────────────────────────────────┐   │
│  │                   │                                  │   │
│  │  Subtask Assignment & Coordination                  │   │
│  │                   │                                  │   │
│  │  • Dependency resolution    • Context enrichment    │   │
│  │  • Task conversion          • Progress tracking     │   │
│  │  • Parent updates           • Integration checks    │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Integration

```
┌─────────────────────────────────────────────────┐
│         Task Assignment with Subtasks            │
├─────────────────────────────────────────────────┤
│                                                  │
│  Agent: request_next_task()                      │
│         │                                        │
│         ▼                                        │
│  Check SubtaskManager for available subtasks     │
│         │                                        │
│    ┌────┴────┐                                   │
│    │ Found?  │                                   │
│    ▼         ▼                                   │
│  Yes        No                                   │
│   │          │                                   │
│   │          ▼                                   │
│   │    Regular task assignment                   │
│   │          │                                   │
│   ▼          │                                   │
│  Check dependencies satisfied                    │
│   │          │                                   │
│   ▼          │                                   │
│  Convert Subtask → Task                          │
│   │          │                                   │
│   └────┬─────┘                                   │
│        │                                         │
│        ▼                                         │
│  Assign with enhanced context                    │
│        │                                         │
│        ▼                                         │
│  Agent works on subtask                          │
│        │                                         │
│        ▼                                         │
│  Reports completion                              │
│        │                                         │
│        ▼                                         │
│  Update subtask status                           │
│        │                                         │
│        ▼                                         │
│  Update parent progress                          │
│        │                                         │
│        ▼                                         │
│  Check if all subtasks done                      │
│        │                                         │
│    ┌───┴────┐                                    │
│    │  Done? │                                    │
│    ▼        ▼                                    │
│  Yes       No                                    │
│   │         │                                    │
│   ▼         └─→ Continue                         │
│  Auto-complete parent                            │
│   │                                              │
│   ▼                                              │
│  Trigger dependent tasks                         │
│                                                  │
└─────────────────────────────────────────────────┘
```

## How It Works

### 1. Decomposition Decision

When a task is created, Marcus evaluates whether it should be decomposed:

```python
def should_decompose(task: Task) -> bool:
    # Size heuristic
    if task.estimated_hours >= 4.0:
        return True

    # Complexity heuristic
    indicators = ["api", "database", "model", "ui", "frontend", "backend"]
    indicator_count = sum(1 for i in indicators if i in task.description.lower())
    if indicator_count >= 3:
        return True

    # Type heuristic - skip certain types
    skip_types = ["bugfix", "hotfix", "refactor", "deploy"]
    if any(t in task.labels for t in skip_types):
        return False

    return False
```

### 2. AI-Powered Breakdown

If decomposition is warranted, Marcus uses AI to create subtasks:

```python
decomposition = await decompose_task(
    task,
    ai_engine,
    project_context={
        "labels": task.labels,
        "existing_tasks": [t.name for t in project_tasks],
        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "React"]
    }
)
```

**AI Analysis Includes**:
- Component identification (API, DB, UI, etc.)
- Sequential vs parallel opportunities
- Interface design between components
- File artifact organization
- Time estimation per subtask
- Dependency relationships

### 3. Subtask Generation

AI generates structured subtasks with complete metadata:

```python
{
    "success": True,
    "subtasks": [
        {
            "id": "task_123_sub_1",
            "name": "Create User database model",
            "description": "Implement User model with fields: id, email, password_hash, created_at...",
            "estimated_hours": 2.0,
            "dependencies": [],
            "file_artifacts": ["src/models/user.py"],
            "provides": "User model with email validation and password hashing",
            "requires": None,
            "order": 1
        },
        {
            "id": "task_123_sub_2",
            "name": "Build authentication endpoints",
            "description": "Implement POST /api/login and POST /api/register endpoints...",
            "estimated_hours": 2.5,
            "dependencies": ["task_123_sub_1"],
            "file_artifacts": ["src/api/auth/login.py", "src/api/auth/register.py"],
            "provides": "POST /api/login, POST /api/register with JWT token response",
            "requires": "User model from subtask 1",
            "order": 2
        },
        {
            "id": "task_123_sub_integration",
            "name": "Integration testing and validation",
            "description": "Verify all auth components work together, run e2e tests...",
            "estimated_hours": 1.0,
            "dependencies": ["task_123_sub_1", "task_123_sub_2"],
            "file_artifacts": ["docs/integration_report.md", "tests/integration/test_auth.py"],
            "provides": "Validated, integrated authentication system",
            "requires": "All auth components",
            "order": 99  # Integration always last
        }
    ],
    "shared_conventions": {
        "base_path": "src/api/auth/",
        "response_format": {"success": {...}, "error": {...}},
        "authentication": "JWT tokens",
        "error_handling": "Custom AuthException with HTTP status codes"
    }
}
```

### 4. Subtask Assignment

When agents request work, subtasks are prioritized:

```python
async def find_optimal_task_for_agent(agent_id: str, state: Any) -> Optional[Task]:
    # Check for available subtasks first
    if state.subtask_manager:
        available_subtask = await find_available_subtask(
            state.subtask_manager,
            agent_id,
            state.project_tasks
        )

        if available_subtask:
            # Convert subtask to Task for assignment
            task = convert_subtask_to_task(available_subtask, state.subtask_manager)
            return task

    # Fall back to regular task assignment
    return await find_optimal_task_original(agent_id, state)
```

### 5. Enhanced Context

Agents receive rich context about their subtask's role:

```python
{
    "is_subtask": True,
    "subtask_info": {
        "name": "Build authentication endpoints",
        "provides": "POST /api/login, POST /api/register with JWT tokens",
        "requires": "User model from subtask 1",
        "file_artifacts": ["src/api/auth/login.py", "src/api/auth/register.py"]
    },
    "parent_task": {
        "id": "task_123",
        "name": "Build user authentication system",
        "description": "Complete auth system with login, registration, and sessions"
    },
    "shared_conventions": {
        "base_path": "src/api/auth/",
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
        {"name": "Add session management", "status": "todo"},
        {"name": "Integration testing", "status": "todo"}
    ]
}
```

### 6. Progress Tracking

As subtasks complete, parent progress updates automatically:

```python
# When subtask completes
await report_task_progress(agent_id, "task_123_sub_2", status="completed", ...)

# System automatically:
# 1. Updates subtask status
state.subtask_manager.update_subtask_status("task_123_sub_2", TaskStatus.DONE, agent_id)

# 2. Calculates parent completion
completed = sum(1 for s in subtasks if s.status == TaskStatus.DONE)
progress = int((completed / len(subtasks)) * 100)

# 3. Updates parent task
await kanban_client.update_task_progress("task_123", progress)

# 4. Checks for auto-completion
if all(s.status == TaskStatus.DONE for s in subtasks):
    await kanban_client.move_task_to_done("task_123")
```

## Benefits

### For Agents

**Clearer Scope**: Work on well-defined components instead of vague epics
```
Before: "Build authentication system" (unclear what's included)
After: "Build login endpoint returning JWT tokens" (specific deliverable)
```

**Better Context**: Understand how your work fits into the larger system
```
Context shows:
- What you can use from completed subtasks
- What future subtasks will depend on your work
- Shared patterns to follow for consistency
```

**Reduced Integration Risk**: Shared conventions prevent mismatch
```
All subtasks follow same:
- File structure
- Response formats
- Error handling
- Naming conventions
```

### For Project Management

**Accurate Progress**: Real-time visibility into feature completion
```
Parent: "Build authentication" - 66% complete
  ✓ Create User model (done)
  ✓ Build login endpoint (done)
  ⧗ Add session management (in progress)
  ○ Integration testing (todo)
```

**Better Parallelization**: Independent subtasks can run simultaneously
```
Sequential: User model → Login → Register → Sessions (8 hours serial)
Parallel: User model → [Login + Register + Sessions] (5 hours with 3 agents)
```

**Easier Recovery**: Failed subtasks can be reassigned without losing context
```
If agent fails during "Add session management":
- Other subtasks remain complete
- New agent gets same context and conventions
- No need to restart entire feature
```

### For System Intelligence

**Learning Patterns**: Marcus learns effective decomposition strategies
```
Memory System records:
- Which decompositions worked well
- Common subtask patterns for feature types
- Optimal subtask sizes and dependencies
- Integration task effectiveness
```

**Improved Estimates**: Better time predictions from subtask history
```
"Authentication system" historically breaks down to:
- User model: 1.5-2.5 hours
- Login endpoints: 2-3 hours
- Session management: 1.5-2 hours
- Integration: 0.5-1 hour
Total: 5.5-8.5 hours
```

## Comparison with Other Approaches

### vs. Manual Task Breakdown

**Manual**:
- Time-consuming upfront planning
- Requires deep technical knowledge
- Hard to maintain consistency
- Doesn't adapt to project changes

**Marcus Hierarchical**:
- Automated AI-powered breakdown
- Learns from project patterns
- Enforces shared conventions
- Adapts to new information

### vs. Flat Task Lists

**Flat**:
- All tasks at same level
- Unclear relationships
- Hard to track feature completion
- Integration happens implicitly

**Marcus Hierarchical**:
- Parent-child relationships clear
- Explicit interfaces defined
- Feature progress tracked automatically
- Integration tested explicitly

### vs. Epic/Story/Task Hierarchy

**Traditional Agile**:
- Manual story pointing
- Subjective estimates
- Human-defined dependencies
- Stories often too large for one sprint

**Marcus Hierarchical**:
- AI-powered decomposition
- Time-based estimates
- Inferred + explicit dependencies
- Subtasks right-sized for agents

## Key Takeaways

**Hierarchical Task Decomposition enables**:

1. **Intelligent Breakdown** - AI identifies components and interfaces
2. **Clear Contracts** - Subtasks define provides/requires explicitly
3. **Shared Conventions** - Consistent patterns across components
4. **Automatic Integration** - Final validation subtask ensures cohesion
5. **Better Parallelization** - Independent subtasks run simultaneously
6. **Accurate Tracking** - Parent progress reflects subtask completion
7. **Easier Recovery** - Failed subtasks don't invalidate entire features

**This system embodies Marcus's core values**:
- **Context Compounds** - Rich subtask context enables autonomy
- **Guided Autonomy** - Clear interfaces with implementation freedom
- **Relentless Focus** - One subtask, complete → request next
- **Fail Forward** - Subtask failures don't cascade to entire features

## Next Steps

- **[Guide: Using Hierarchical Task Decomposition](../guides/project-management/hierarchical-task-decomposition.md)** - Practical usage
- **[System: Task Decomposition System](../systems/project-management/54-hierarchical-task-decomposition.md)** - Technical details
- **[Integration Guide](../../task-decomposition-integration.md)** - Developer integration

---

*Hierarchical Task Decomposition transforms large, ambiguous features into manageable, well-defined subtasks with clear interfaces—enabling autonomous agents to collaborate effectively on complex software projects.*
