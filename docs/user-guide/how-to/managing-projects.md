# Managing Projects in Marcus

This guide covers advanced project management workflows, including updating, archiving, and organizing multiple projects.

## Project Management Tools

Marcus provides a complete set of MCP tools for managing projects:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `list_projects()` | View all projects | Daily workflow, finding projects |
| `switch_project()` | Change active project | Moving between different work contexts |
| `get_current_project()` | Check active project | Verify which project you're working on |
| `add_project()` | Register existing board | Connect to pre-existing Planka/GitHub boards |
| `update_project()` | Modify project metadata | Change names, tags, or configuration |
| `remove_project()` | Delete project | Clean up completed or abandoned projects |

## Listing and Searching Projects

### Basic Listing

```python
# Get all projects
all_projects = list_projects()

# Result:
[
    {
        "id": "proj-123",
        "name": "UserAuthAPI",
        "provider": "planka",
        "tags": ["backend", "production"],
        "is_active": True,
        "last_used": "2025-01-15T10:30:00"
    },
    {
        "id": "proj-456",
        "name": "MobileApp",
        "provider": "planka",
        "tags": ["mobile", "ios"],
        "is_active": False,
        "last_used": "2025-01-14T15:20:00"
    }
]
```

### Filtering by Provider

```python
# Only Planka projects
planka_projects = list_projects(provider="planka")

# Only GitHub projects (when available)
github_projects = list_projects(provider="github")
```

### Filtering by Tags

```python
# All backend projects
backend = list_projects(filter_tags=["backend"])

# All high-priority production projects
critical = list_projects(filter_tags=["production", "priority:high"])

# Projects for specific client
client_work = list_projects(filter_tags=["client:acme-corp"])
```

### Advanced Filtering Examples

```python
# Find all active mobile projects
mobile_projects = [
    p for p in list_projects(filter_tags=["mobile"])
    if p["is_active"]
]

# Find projects not used in last 30 days
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=30)
stale_projects = [
    p for p in list_projects()
    if datetime.fromisoformat(p["last_used"]) < cutoff
]

# Find projects by name pattern
api_projects = [
    p for p in list_projects()
    if "API" in p["name"]
]
```

## Switching Between Projects

### By Project ID

```python
# Most reliable method - use exact ID
switch_project(project_id="proj-123")
```

### By Project Name

```python
# If name is unique, you can use it directly
switch_project(project_name="UserAuthAPI")
```

### Verify Switch Success

```python
result = switch_project(project_id="proj-123")

if result["success"]:
    print(f"Switched to: {result['project']['name']}")
    print(f"Tasks available: {result['project']['task_count']}")
else:
    print(f"Error: {result['error']}")
```

## System Behavior: Automatic Project Synchronization

Marcus automatically synchronizes projects from your Kanban provider (Planka, GitHub, etc.) on every startup. This is a transparent system behavior that keeps your project registry up-to-date.

### How It Works

1. **On Startup:** Marcus queries your Kanban provider for all accessible boards/projects
2. **Discovery:** New projects are automatically added to the registry
3. **Updates:** Existing projects have their metadata refreshed (names, board IDs, etc.)
4. **Preservation:** Projects are never automatically deleted from the registry

### What This Means for You

- **No manual registration needed:** New boards appear in `list_projects()` automatically
- **Always current:** Project names and metadata stay synchronized
- **Safe:** Your registry data is preserved even if boards are temporarily unavailable

### Startup Log Example

```
INFO: Auto-syncing projects from Kanban provider...
INFO: Auto-synced projects: 3 added, 5 updated, 0 skipped
INFO: Switching to active project: UserAuthAPI
```

**Note:** Auto-sync runs quickly (typically <1 second) and requires no configuration. It's designed to be invisible during normal operation.

---

## Adding Existing Projects

If you need to manually register a project (e.g., for testing or special configurations), you can do so explicitly:

### Planka Project

```python
add_project(
    name="ExistingPlankBoard",
    provider="planka",
    config={
        "project_id": "planka-proj-id-from-url",
        "board_id": "planka-board-id-from-url"
    },
    tags=["imported", "legacy"],
    make_active=True  # Switch to it immediately
)
```

**Finding Planka IDs:**
1. Open your Planka board in browser
2. Check the URL: `https://planka.example.com/boards/{project_id}/{board_id}`
3. Copy those IDs into the config

### GitHub Project (Coming Soon)

```python
add_project(
    name="MyGitHubRepo",
    provider="github",
    config={
        "repo": "username/repo-name",
        "project_number": 1
    },
    tags=["github", "open-source"]
)
```

## Updating Projects

### Change Project Name

```python
update_project(
    project_id="proj-123",
    name="UserAuthAPI-Refactored"
)
```

### Update Tags

```python
# Add new tags
update_project(
    project_id="proj-123",
    tags=["backend", "production", "auth", "api", "v2"]
)

# Tags completely replace the old list
```

### Update Provider Config

```python
# Change to a different Planka board
update_project(
    project_id="proj-123",
    config={
        "project_id": "new-planka-project",
        "board_id": "new-planka-board"
    }
)
```

### Bulk Updates

```python
# Update multiple projects at once
projects_to_archive = ["proj-123", "proj-456", "proj-789"]

for pid in projects_to_archive:
    update_project(
        project_id=pid,
        tags=["archived", "completed"]
    )
```

## Removing Projects

### Safe Removal (Requires Confirmation)

```python
# This will fail without confirmation
remove_project(project_id="proj-123")
# Error: "confirm parameter must be True"

# Proper way
remove_project(
    project_id="proj-123",
    confirm=True
)
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
```

**Warning:** This only removes the project from Marcus's registry. It does NOT delete the actual Planka/GitHub board. Your data is safe!

## Organizing with Tags

### Tag Naming Conventions

Use prefixes for better organization:

```python
tags=[
    # Team ownership
    "team:backend",
    "team:frontend",
    "team:devops",

    # Priority levels
    "priority:critical",
    "priority:high",
    "priority:low",

    # Project status
    "status:active",
    "status:maintenance",
    "status:archived",

    # Client/customer
    "client:acme-corp",
    "client:big-tech",

    # Technology stack
    "tech:python",
    "tech:react",
    "tech:docker",

    # Environment
    "env:production",
    "env:staging",
    "env:development"
]
```

### Tag-Based Workflows

#### Daily Standup

```python
# Show what you're working on
my_active = list_projects(filter_tags=["team:backend", "status:active"])
for p in my_active:
    print(f"📋 {p['name']} - {p['task_count']} tasks")
```

#### Sprint Planning

```python
# Find high-priority projects needing attention
sprint_candidates = list_projects(filter_tags=["priority:high", "status:active"])
```

#### Client Reporting

```python
# Generate client report
client_projects = list_projects(filter_tags=["client:acme-corp"])

print(f"ACME Corp Projects: {len(client_projects)}")
for p in client_projects:
    current = get_current_project() if p["is_active"] else switch_project(p["id"])
    print(f"  - {p['name']}: {current['task_count']} tasks, "
          f"{current['completed_tasks']} completed")
```

## Advanced Workflows

### Project Templates

Create reusable project structures:

```python
def create_client_project(client_name: str, project_type: str):
    """Template for new client projects"""
    tags = [
        f"client:{client_name.lower().replace(' ', '-')}",
        f"type:{project_type}",
        "status:active",
        "team:assigned"
    ]

    if project_type == "web":
        description = f"Web application for {client_name}"
        tags.append("tech:react")
    elif project_type == "api":
        description = f"REST API for {client_name}"
        tags.append("tech:python")

    return create_project(
        description=description,
        project_name=f"{client_name}-{project_type}",
        options={
            "tags": tags,
            "complexity": "standard",
            "deployment": "production"
        }
    )

# Usage
create_client_project("ACME Corp", "web")
create_client_project("ACME Corp", "api")
```

### Project Archival

```python
def archive_project(project_id: str, reason: str = "completed"):
    """Archive a project with metadata"""
    # Get current project data
    projects = list_projects()
    project = next((p for p in projects if p["id"] == project_id), None)

    if not project:
        return {"error": "Project not found"}

    # Add archive tags
    new_tags = project["tags"] + [
        "archived",
        f"archived:{datetime.now().strftime('%Y-%m')}",
        f"reason:{reason}"
    ]

    # Update project
    update_project(
        project_id=project_id,
        tags=new_tags
    )

    return {"success": True, "message": f"Archived {project['name']}"}

# Usage
archive_project("proj-123", reason="completed")
archive_project("proj-456", reason="cancelled")
```

### Multi-Project Reporting

```python
def generate_portfolio_report():
    """Generate report across all projects"""
    all_projects = list_projects()

    report = {
        "total_projects": len(all_projects),
        "active": len([p for p in all_projects if "status:active" in p["tags"]]),
        "archived": len([p for p in all_projects if "archived" in p["tags"]]),
        "by_team": {},
        "by_client": {}
    }

    for project in all_projects:
        # Count by team
        team_tags = [t for t in project["tags"] if t.startswith("team:")]
        for tag in team_tags:
            team = tag.split(":")[1]
            report["by_team"][team] = report["by_team"].get(team, 0) + 1

        # Count by client
        client_tags = [t for t in project["tags"] if t.startswith("client:")]
        for tag in client_tags:
            client = tag.split(":")[1]
            report["by_client"][client] = report["by_client"].get(client, 0) + 1

    return report

# Usage
report = generate_portfolio_report()
print(f"Managing {report['total_projects']} projects")
print(f"Active: {report['active']}, Archived: {report['archived']}")
```

## Best Practices

### 1. Keep Active Projects Manageable

**Limit active projects to 3-5 at a time:**

```python
active = [p for p in list_projects() if "status:active" in p["tags"]]
if len(active) > 5:
    print("⚠️  Too many active projects! Consider archiving some.")
```

### 2. Regular Cleanup

**Monthly review:**

```python
# Find stale projects (not used in 30 days)
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(days=30)
stale = [
    p for p in list_projects()
    if datetime.fromisoformat(p["last_used"]) < cutoff
    and "archived" not in p["tags"]
]

print(f"Found {len(stale)} stale projects - consider archiving")
```

### 3. Consistent Naming

**Use a naming convention:**

```
[Client]-[Type]-[Component]

Examples:
- AcmeCorp-Web-Frontend
- AcmeCorp-API-Auth
- AcmeCorp-Mobile-iOS
```

### 4. Tag Hierarchy

**Start broad, get specific:**

```python
tags=[
    "production",           # Broad
    "backend",             # Medium
    "service:auth",        # Specific
    "component:jwt",       # Very specific
]
```

## Troubleshooting

### Can't Find Project After Creating

**Check:**
1. Project was registered: `list_projects()`
2. Try searching by tag if you added one
3. Verify provider: `list_projects(provider="planka")`

### Switch Fails with "Project not found"

**Solutions:**
1. List projects to find correct ID
2. Check if project was removed
3. Verify provider connection is working

### Tags Not Filtering Correctly

**Common issues:**
- Tags are case-sensitive: use `"production"` not `"Production"`
- Multiple tags use AND logic (all must match)
- Check for typos in tag names

## Next Steps

- [Getting Started with Projects](getting-started-projects.md) - Basic workflows
- [Project Tools Reference](../reference/project-tools-reference.md) - Complete API docs
- [Advanced AI Features](creating-projects.md) - Using AI for project creation

## Related Documentation

- [Task Management](task-management.md)
- [Team Collaboration](team-collaboration.md)
- [Analytics and Reporting](analytics.md)
