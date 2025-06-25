# Marcus Data Models API Reference

> **Type**: API  
> **Version**: 1.0.0  
> **Last Updated**: 2025-06-25

## Overview

Complete reference for all data models used in the Marcus system, including enumerations, dataclasses, and their relationships.

## Synopsis

```python
from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment,
    BlockerReport, ProjectRisk
)

# Create a new task
task = Task(
    id="task-123",
    name="Implement authentication",
    description="Add JWT authentication to API",
    status=TaskStatus.TODO,
    priority=Priority.HIGH,
    assigned_to=None,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    due_date=datetime.now() + timedelta(days=3),
    estimated_hours=8.0,
    dependencies=[],
    labels=["backend", "security"]
)
```

## Description

The Marcus data models provide strongly-typed, validated data structures for representing all aspects of the project management system. These models ensure consistency across the codebase and provide clear contracts for data exchange between components.

## Parameters

### Enumerations

#### TaskStatus

Represents the lifecycle state of a task.

| Value | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `TODO` | string | - | - | Task created but not started |
| `IN_PROGRESS` | string | - | - | Task actively being worked on |
| `DONE` | string | - | - | Task completed successfully |
| `BLOCKED` | string | - | - | Task cannot proceed due to dependencies |

```python
# Usage
status = TaskStatus.IN_PROGRESS
if task.status == TaskStatus.BLOCKED:
    # Handle blocked task
```

#### Priority

Defines task urgency levels for scheduling.

| Value | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `LOW` | string | - | - | Can be deferred without impact |
| `MEDIUM` | string | - | - | Normal priority task |
| `HIGH` | string | - | - | Should be prioritized |
| `URGENT` | string | - | - | Requires immediate attention |

```python
# Priority scoring
priority_weights = {
    Priority.URGENT: 1.0,
    Priority.HIGH: 0.8,
    Priority.MEDIUM: 0.5,
    Priority.LOW: 0.2
}
```

#### RiskLevel

Categorizes risk severity for project health.

| Value | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `LOW` | string | - | - | Minimal impact on timeline |
| `MEDIUM` | string | - | - | Moderate impact, needs attention |
| `HIGH` | string | - | - | Significant impact on project |
| `CRITICAL` | string | - | - | Severe impact, project at risk |

### Data Classes

#### Task

Core work item representation.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `id` | string | Yes | - | Unique task identifier |
| `name` | string | Yes | - | Short descriptive title |
| `description` | string | Yes | - | Detailed task requirements |
| `status` | TaskStatus | Yes | - | Current task state |
| `priority` | Priority | Yes | - | Task urgency level |
| `assigned_to` | Optional[string] | Yes | - | Worker ID if assigned |
| `created_at` | datetime | Yes | - | Creation timestamp |
| `updated_at` | datetime | Yes | - | Last modification time |
| `due_date` | Optional[datetime] | Yes | - | Target completion date |
| `estimated_hours` | float | Yes | - | Time estimate in hours |
| `actual_hours` | float | No | `0.0` | Actual time spent |
| `dependencies` | List[string] | No | `[]` | Prerequisite task IDs |
| `labels` | List[string] | No | `[]` | Skill/category tags |

##### Parameter Details

###### `id`
Must be unique across the system. Common formats:
- Kanban provider ID: `"5f4d3e2c1b0a9876543210"`
- Sequential: `"TASK-001"`, `"TASK-002"`
- UUID: `"550e8400-e29b-41d4-a716-446655440000"`

###### `labels`
Used for skill matching and categorization:
- Technical skills: `["python", "django", "postgresql"]`
- Component areas: `["backend", "frontend", "api"]`
- Features: `["authentication", "payments", "reporting"]`

#### WorkerStatus

Represents an agent's current state and capabilities.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `worker_id` | string | Yes | - | Unique worker identifier |
| `name` | string | Yes | - | Display name |
| `role` | string | Yes | - | Job title/specialization |
| `email` | Optional[string] | Yes | - | Contact email |
| `current_tasks` | List[Task] | Yes | - | Active assignments |
| `completed_tasks_count` | int | Yes | - | Total completed tasks |
| `capacity` | int | Yes | - | Weekly hour capacity |
| `skills` | List[string] | Yes | - | Technical competencies |
| `availability` | Dict[string, bool] | Yes | - | Weekly availability |
| `performance_score` | float | No | `1.0` | Performance metric (0.0-2.0) |

##### Parameter Details

###### `availability`
Dictionary mapping weekdays to availability:
```python
availability = {
    "monday": True,
    "tuesday": True,
    "wednesday": True,
    "thursday": True,
    "friday": True,
    "saturday": False,
    "sunday": False
}
```

###### `performance_score`
- `0.0 - 0.5`: Below expectations
- `0.5 - 1.0`: Meeting expectations
- `1.0 - 1.5`: Exceeding expectations
- `1.5 - 2.0`: Exceptional performance

#### ProjectState

Snapshot of overall project health and progress.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `board_id` | string | Yes | - | Kanban board identifier |
| `project_name` | string | Yes | - | Project display name |
| `total_tasks` | int | Yes | - | Total task count |
| `completed_tasks` | int | Yes | - | Completed task count |
| `in_progress_tasks` | int | Yes | - | Active task count |
| `blocked_tasks` | int | Yes | - | Blocked task count |
| `progress_percent` | float | Yes | - | Completion percentage |
| `overdue_tasks` | List[Task] | Yes | - | Past-due tasks |
| `team_velocity` | float | Yes | - | Tasks/week rate |
| `risk_level` | RiskLevel | Yes | - | Overall risk assessment |
| `last_updated` | datetime | Yes | - | Last refresh time |

#### TaskAssignment

Records task allocation to a worker.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Task identifier |
| `task_name` | string | Yes | - | Task title |
| `description` | string | Yes | - | Task details |
| `instructions` | string | Yes | - | AI-generated guidance |
| `estimated_hours` | float | Yes | - | Time estimate |
| `priority` | Priority | Yes | - | Task urgency |
| `dependencies` | List[string] | Yes | - | Prerequisite tasks |
| `assigned_to` | string | Yes | - | Worker ID |
| `assigned_at` | datetime | Yes | - | Assignment timestamp |
| `due_date` | Optional[datetime] | Yes | - | Target completion |
| `workspace_path` | Optional[string] | No | `None` | Isolated workspace |
| `forbidden_paths` | List[string] | No | `[]` | Restricted paths |

#### BlockerReport

Documents impediments to task progress.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `task_id` | string | Yes | - | Blocked task ID |
| `reporter_id` | string | Yes | - | Reporting worker ID |
| `description` | string | Yes | - | Blocker details |
| `severity` | RiskLevel | Yes | - | Impact severity |
| `reported_at` | datetime | Yes | - | Report timestamp |
| `resolved` | bool | No | `False` | Resolution status |
| `resolution` | Optional[string] | No | `None` | How it was resolved |
| `resolved_at` | Optional[datetime] | No | `None` | Resolution timestamp |

#### ProjectRisk

Identifies potential project threats.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `risk_type` | string | Yes | - | Risk category |
| `description` | string | Yes | - | Risk details |
| `severity` | RiskLevel | Yes | - | Impact level |
| `probability` | float | Yes | - | Likelihood (0.0-1.0) |
| `impact` | string | Yes | - | Potential consequences |
| `mitigation_strategy` | string | Yes | - | Risk reduction plan |
| `identified_at` | datetime | Yes | - | Discovery timestamp |

## Return Values

### Model Creation
```python
# Success
task = Task(id="123", name="Test", ...)
assert task.id == "123"

# Validation error
try:
    task = Task(id=None, ...)  # Missing required field
except TypeError as e:
    print(f"Validation error: {e}")
```

### Model Serialization
```python
# To dictionary
task_dict = {
    "id": task.id,
    "name": task.name,
    "status": task.status.value,
    "priority": task.priority.value,
    # ... other fields
}

# From dictionary
task = Task(**task_dict)
```

## Examples

### Basic Example
```python
# Create a simple task
task = Task(
    id="TASK-001",
    name="Setup development environment",
    description="Install Python, Node.js, and Docker",
    status=TaskStatus.TODO,
    priority=Priority.MEDIUM,
    assigned_to=None,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    due_date=None,
    estimated_hours=2.0
)
```

### Advanced Example
```python
# Complete worker and task assignment flow
from datetime import datetime, timedelta

# Register worker
worker = WorkerStatus(
    worker_id="backend-dev-001",
    name="Alice Smith",
    role="Senior Backend Developer",
    email="alice@company.com",
    current_tasks=[],
    completed_tasks_count=42,
    capacity=40,
    skills=["Python", "Django", "PostgreSQL", "Redis"],
    availability={
        "monday": True, "tuesday": True, "wednesday": True,
        "thursday": True, "friday": True,
        "saturday": False, "sunday": False
    },
    performance_score=1.3
)

# Create high-priority task
task = Task(
    id="TASK-100",
    name="Fix authentication vulnerability",
    description="SQL injection vulnerability in login endpoint",
    status=TaskStatus.TODO,
    priority=Priority.URGENT,
    assigned_to=None,
    created_at=datetime.now(),
    updated_at=datetime.now(),
    due_date=datetime.now() + timedelta(hours=4),
    estimated_hours=3.0,
    dependencies=[],
    labels=["security", "backend", "critical"]
)

# Create assignment
assignment = TaskAssignment(
    task_id=task.id,
    task_name=task.name,
    description=task.description,
    instructions="1. Review auth.py line 45-67\n2. Use parameterized queries\n3. Add input validation",
    estimated_hours=task.estimated_hours,
    priority=task.priority,
    dependencies=task.dependencies,
    assigned_to=worker.worker_id,
    assigned_at=datetime.now(),
    due_date=task.due_date,
    workspace_path="/workspaces/security-fix-001",
    forbidden_paths=["/production", "/secrets"]
)
```

### Real-World Example
```python
# Project health monitoring
def assess_project_health(tasks: List[Task], workers: List[WorkerStatus]) -> ProjectState:
    """Calculate comprehensive project state"""
    
    # Count tasks by status
    status_counts = {
        TaskStatus.TODO: 0,
        TaskStatus.IN_PROGRESS: 0,
        TaskStatus.DONE: 0,
        TaskStatus.BLOCKED: 0
    }
    
    overdue_tasks = []
    now = datetime.now()
    
    for task in tasks:
        status_counts[task.status] += 1
        if task.due_date and task.due_date < now and task.status != TaskStatus.DONE:
            overdue_tasks.append(task)
    
    # Calculate velocity (tasks completed per week)
    completed_this_week = sum(
        1 for w in workers 
        for t in w.current_tasks 
        if t.status == TaskStatus.DONE
    )
    
    # Assess risk level
    risk_level = RiskLevel.LOW
    if len(overdue_tasks) > 5:
        risk_level = RiskLevel.HIGH
    elif status_counts[TaskStatus.BLOCKED] > 3:
        risk_level = RiskLevel.MEDIUM
    
    total_tasks = sum(status_counts.values())
    progress = (status_counts[TaskStatus.DONE] / total_tasks * 100) if total_tasks > 0 else 0
    
    return ProjectState(
        board_id="main-board",
        project_name="E-Commerce Platform",
        total_tasks=total_tasks,
        completed_tasks=status_counts[TaskStatus.DONE],
        in_progress_tasks=status_counts[TaskStatus.IN_PROGRESS],
        blocked_tasks=status_counts[TaskStatus.BLOCKED],
        progress_percent=progress,
        overdue_tasks=overdue_tasks,
        team_velocity=completed_this_week * 4,  # Extrapolate to month
        risk_level=risk_level,
        last_updated=now
    )
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `MISSING_REQUIRED_FIELD` | Required field not provided | Provide all required fields |
| `INVALID_ENUM_VALUE` | Invalid enumeration value | Use valid enum values |
| `TYPE_MISMATCH` | Wrong type for field | Check field type requirements |
| `VALIDATION_ERROR` | Field validation failed | Review validation constraints |

## Notes

- All models are immutable dataclasses by default
- Timestamps should use UTC timezone
- IDs must be unique within their scope
- Lists are initialized as empty if not provided
- Performance scores are normalized to 1.0 baseline

## Relationships

```
Task (1) ← → (0..1) WorkerStatus (via assigned_to)
Task (0..*) → (0..*) Task (via dependencies)
TaskAssignment (1) → (1) Task
TaskAssignment (1) → (1) WorkerStatus
BlockerReport (1) → (1) Task
ProjectRisk (*) → (1) ProjectState
```

## Version History

| Version | Changes |
|---------|---------|
| 1.0.0 | Complete data model documentation |
| 0.9.0 | Added workspace isolation fields |
| 0.8.0 | Added performance metrics |
| 0.7.0 | Initial model definitions |

## See Also

- [MCP Tools API](/reference/mcp_tools_api)
- [System Architecture](/reference/system_architecture)
- [Database Schema](/reference/database_schema)