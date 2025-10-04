# Project Management Tools API Reference

Complete reference for all Marcus MCP project management tools.

## Table of Contents

- [create_project](#create_project)
- [list_projects](#list_projects)
- [switch_project](#switch_project)
- [get_current_project](#get_current_project)
- [add_project](#add_project)
- [update_project](#update_project)
- [remove_project](#remove_project)

---

## create_project

Create a complete project from natural language description with intelligent project discovery.

### Signature

```python
create_project(
    description: str,
    project_name: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | `str` | Yes | Natural language description of what you want to build |
| `project_name` | `str` | Yes | Name for the project (used for discovery) |
| `options` | `Dict[str, Any]` | No | Configuration options (see below) |

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `project_id` | `str` | `None` | Explicit project ID to use (skips discovery) |
| `mode` | `str` | `"auto"` | Creation mode: `"auto"`, `"new_project"`, `"add_feature"` |
| `provider` | `str` | `"planka"` | Kanban provider: `"planka"`, `"github"`, `"linear"` |
| `complexity` | `str` | `"standard"` | Project complexity: `"prototype"`, `"standard"`, `"enterprise"` |
| `deployment` | `str` | `"none"` | Deployment target: `"none"`, `"internal"`, `"production"` |
| `team_size` | `int` | `1` | Team size (1-20) for task estimation |
| `tech_stack` | `List[str]` | `[]` | Technologies to use (e.g., `["React", "Python"]`) |
| `deadline` | `str` | `None` | Project deadline in `YYYY-MM-DD` format |
| `tags` | `List[str]` | `[]` | Tags for project organization |
| `planka_project_name` | `str` | `project_name` | Custom Planka project name |
| `planka_board_name` | `str` | `"Main Board"` | Custom Planka board name |

### Returns

```python
{
    "success": bool,
    "project_id": str,  # Marcus project ID
    "tasks_created": int,
    "board": {
        "project_id": str,  # Provider project ID
        "board_id": str,    # Provider board ID
        "provider": str
    },
    "phases": List[str],  # Project phases identified
    "estimated_duration": str,
    "complexity_score": float
}
```

### Modes

#### `"auto"` (Default)
Intelligent discovery:
1. Checks for exact project name match → uses existing
2. Checks for similar matches → asks for clarification
3. No matches found → creates new project

#### `"new_project"`
Force creation of new project (skips discovery):
- Always creates a fresh project
- Useful for project versions (v2, v3, etc.)

#### `"add_feature"`
Add to existing project:
- Requires `project_id` in options
- Adds tasks to existing board
- Preserves existing project structure

### Examples

#### Basic Project Creation

```python
result = create_project(
    description="Build a REST API for user authentication with JWT tokens",
    project_name="AuthAPI"
)

if result["success"]:
    print(f"Created {result['tasks_created']} tasks")
    print(f"Project ID: {result['project_id']}")
```

#### Use Existing Project

```python
result = create_project(
    description="Add password reset functionality",
    project_name="AuthAPI",  # Will find existing "AuthAPI"
    options={"project_id": "proj-123"}  # Or specify exact ID
)
```

#### Force New Project

```python
result = create_project(
    description="Build OAuth 2.0 authentication",
    project_name="AuthAPI-v2",
    options={"mode": "new_project"}  # Creates new even if similar exists
)
```

#### Advanced Configuration

```python
result = create_project(
    description="E-commerce platform with inventory management",
    project_name="ShopFlow",
    options={
        "complexity": "enterprise",
        "deployment": "production",
        "team_size": 5,
        "tech_stack": ["React", "Node.js", "PostgreSQL", "Redis"],
        "deadline": "2025-06-30",
        "tags": ["ecommerce", "high-priority", "client:acme"],
        "planka_project_name": "ACME Corp - ShopFlow",
        "planka_board_name": "Development Board"
    }
)
```

### Error Responses

#### Similar Projects Found

```python
{
    "success": False,
    "action": "found_similar",
    "message": "Found similar projects",
    "matches": [
        {"id": "proj-123", "name": "AuthAPI", "similarity": 0.9}
    ],
    "hint": "To proceed: specify project_id in options or set mode='new_project'"
}
```

**Resolution:**
```python
# Option 1: Use suggested project
create_project(..., options={"project_id": "proj-123"})

# Option 2: Force new
create_project(..., options={"mode": "new_project"})
```

---

## list_projects

List all projects with optional filtering.

### Signature

```python
list_projects(
    filter_tags: Optional[List[str]] = None,
    provider: Optional[str] = None
) -> List[Dict[str, Any]]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filter_tags` | `List[str]` | No | Filter by tags (AND logic) |
| `provider` | `str` | No | Filter by provider: `"planka"`, `"github"`, `"linear"` |

### Returns

```python
[
    {
        "id": str,              # Project ID
        "name": str,            # Project name
        "provider": str,        # Kanban provider
        "tags": List[str],      # Project tags
        "is_active": bool,      # Currently active?
        "last_used": str,       # ISO datetime
        "task_count": int,      # Number of tasks
        "created_at": str       # ISO datetime
    },
    ...
]
```

### Examples

```python
# All projects
all_projects = list_projects()

# Filter by provider
planka_only = list_projects(provider="planka")

# Filter by tags
backend = list_projects(filter_tags=["backend", "production"])

# Multiple filters
critical = list_projects(
    provider="planka",
    filter_tags=["priority:high", "status:active"]
)
```

---

## switch_project

Switch to a different project context.

### Signature

```python
switch_project(
    project_id: Optional[str] = None,
    project_name: Optional[str] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `str` | * | Exact project ID to switch to |
| `project_name` | `str` | * | Project name (must be unique) |

\* One of `project_id` or `project_name` is required

### Returns

```python
{
    "success": bool,
    "project": {
        "id": str,
        "name": str,
        "provider": str,
        "task_count": int,
        "active_tasks": int,
        "completed_tasks": int
    },
    "message": str
}
```

### Examples

```python
# Switch by ID (most reliable)
result = switch_project(project_id="proj-123")

# Switch by name (if unique)
result = switch_project(project_name="AuthAPI")

# Check result
if result["success"]:
    print(f"Switched to {result['project']['name']}")
    print(f"{result['project']['task_count']} tasks available")
```

---

## get_current_project

Get information about the currently active project.

### Signature

```python
get_current_project() -> Dict[str, Any]
```

### Parameters

None

### Returns

```python
{
    "project": {
        "id": str,
        "name": str,
        "provider": str,
        "tags": List[str],
        "task_count": int,
        "active_tasks": int,
        "completed_tasks": int,
        "last_activity": str,  # ISO datetime
        "provider_config": Dict[str, Any]
    }
}
```

If no project is active:
```python
{
    "project": None,
    "error": "No active project"
}
```

### Examples

```python
current = get_current_project()

if current["project"]:
    proj = current["project"]
    print(f"Working on: {proj['name']}")
    print(f"Tasks: {proj['active_tasks']} active, {proj['completed_tasks']} done")
else:
    print("No active project. Use switch_project() to select one.")
```

---

## add_project

Register an existing kanban board as a Marcus project.

### Signature

```python
add_project(
    name: str,
    provider: str,
    config: Dict[str, Any],
    tags: Optional[List[str]] = None,
    make_active: bool = True
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | `str` | Yes | Display name for the project |
| `provider` | `str` | Yes | Provider type: `"planka"`, `"github"`, `"linear"` |
| `config` | `Dict[str, Any]` | Yes | Provider-specific configuration |
| `tags` | `List[str]` | No | Tags for organization |
| `make_active` | `bool` | No (default: `True`) | Switch to this project immediately |

### Provider Configs

#### Planka

```python
config={
    "project_id": "planka-project-id",
    "board_id": "planka-board-id"
}
```

#### GitHub (Coming Soon)

```python
config={
    "repo": "username/repo-name",
    "project_number": 1
}
```

#### Linear (Coming Soon)

```python
config={
    "team_id": "team-id",
    "project_id": "project-id"
}
```

### Returns

```python
{
    "success": bool,
    "project": {
        "id": str,
        "name": str,
        "provider": str,
        "tags": List[str]
    }
}
```

### Examples

```python
# Add existing Planka board
result = add_project(
    name="Legacy Project",
    provider="planka",
    config={
        "project_id": "abc123",
        "board_id": "xyz789"
    },
    tags=["imported", "legacy", "backend"],
    make_active=True
)

# Add but don't switch
result = add_project(
    name="Archive Board",
    provider="planka",
    config={"project_id": "old-id", "board_id": "old-board"},
    tags=["archived"],
    make_active=False  # Don't switch to it
)
```

---

## update_project

Update project metadata.

### Signature

```python
update_project(
    project_id: str,
    name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `str` | Yes | Project ID to update |
| `name` | `str` | No | New project name |
| `tags` | `List[str]` | No | New tags (replaces existing) |
| `config` | `Dict[str, Any]` | No | New provider config |

### Returns

```python
{
    "success": bool,
    "project": {
        "id": str,
        "name": str,
        "tags": List[str],
        "provider_config": Dict[str, Any]
    }
}
```

### Examples

```python
# Rename project
update_project(
    project_id="proj-123",
    name="AuthAPI-Refactored"
)

# Update tags
update_project(
    project_id="proj-123",
    tags=["backend", "production", "auth", "v2"]
)

# Change Planka board
update_project(
    project_id="proj-123",
    config={
        "project_id": "new-planka-proj",
        "board_id": "new-planka-board"
    }
)

# Update multiple fields
update_project(
    project_id="proj-123",
    name="AuthAPI v2",
    tags=["archived", "completed"],
    config={"archived": True}
)
```

---

## remove_project

Remove a project from Marcus registry.

**Warning:** This only removes the project from Marcus's registry. It does NOT delete the actual Planka/GitHub board!

### Signature

```python
remove_project(
    project_id: str,
    confirm: bool = False
) -> Dict[str, Any]
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | `str` | Yes | Project ID to remove |
| `confirm` | `bool` | Yes | Must be `True` to confirm deletion |

### Returns

```python
{
    "success": bool,
    "message": str,
    "deleted_project_id": str
}
```

### Examples

```python
# This will fail (safety check)
remove_project(project_id="proj-123")
# Error: "confirm parameter must be True"

# Correct usage
result = remove_project(
    project_id="proj-123",
    confirm=True
)

if result["success"]:
    print(f"Removed project: {result['deleted_project_id']}")
```

### Bulk Removal

```python
# Remove all archived projects
archived = list_projects(filter_tags=["archived"])

for project in archived:
    remove_project(
        project_id=project["id"],
        confirm=True
    )
    print(f"Removed: {project['name']}")
```

---

## Error Handling

All tools return a consistent error format:

```python
{
    "success": False,
    "error": str,           # Error message
    "error_type": str,      # Error category
    "details": Dict[str, Any]  # Additional context (optional)
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `"Project not found"` | Invalid project ID | Use `list_projects()` to find correct ID |
| `"Missing required parameter"` | Required param not provided | Check function signature |
| `"Provider not supported"` | Invalid provider name | Use `"planka"`, `"github"`, or `"linear"` |
| `"No active project"` | No project context set | Use `switch_project()` first |
| `"Duplicate project name"` | Name already exists | Use different name or `update_project()` |
| `"Invalid project config"` | Malformed provider config | Check provider config format |

---

## Best Practices

### 1. Always Check Success

```python
result = create_project(...)
if result["success"]:
    # Proceed with result
else:
    # Handle error
    print(f"Error: {result['error']}")
```

### 2. Use Explicit IDs for Critical Operations

```python
# Good - explicit and reliable
switch_project(project_id="proj-123")

# Risky - what if there are multiple "AuthAPI" projects?
switch_project(project_name="AuthAPI")
```

### 3. Filter Results Client-Side for Complex Queries

```python
# Get all projects then filter in Python
all_projects = list_projects()

# Complex filter not supported by API
recent_backend = [
    p for p in all_projects
    if "backend" in p["tags"]
    and datetime.fromisoformat(p["last_used"]) > cutoff
    and p["task_count"] > 10
]
```

### 4. Use Tags Consistently

```python
# Good - consistent naming
tags=["team:backend", "priority:high", "client:acme"]

# Bad - inconsistent
tags=["Backend Team", "HIGH_PRIORITY", "acme-corp"]
```

---

## Related Documentation

- [Getting Started with Projects](../how-to/getting-started-projects.md)
- [Managing Projects](../how-to/managing-projects.md)
- [Creating Projects with AI](../how-to/creating-projects.md)

## Need Help?

- [FAQ](../faq.md)
- [Troubleshooting Guide](../troubleshooting.md)
- [GitHub Issues](https://github.com/lwgray/marcus/issues)
