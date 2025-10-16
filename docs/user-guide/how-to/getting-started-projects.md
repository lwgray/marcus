# Getting Started with Multi-Project Management

Marcus supports working with multiple projects simultaneously, allowing you to organize different initiatives, track separate codebases, or manage various client work in isolated contexts.

## Understanding Projects in Marcus

A **project** in Marcus represents an isolated workspace with:
- Its own kanban board and tasks
- Dedicated provider configuration (Planka, GitHub Projects, or Linear)
- Independent task history and analytics
- Separate team assignments and workflows

## Quick Start Guide

### Scenario 1: Starting Fresh (No Existing Projects)

When you first use Marcus, simply create a project using natural language:

```python
# Using the create_project MCP tool
create_project(
    description="Build a REST API for user authentication with JWT tokens",
    project_name="UserAuthAPI",
    options={
        "complexity": "standard",
        "deployment": "production"
    }
)
```

**What happens:**
1. Marcus searches for existing projects named "UserAuthAPI"
2. Finds none, so creates a new Planka project automatically
3. Registers the project in Marcus's ProjectRegistry
4. Switches to that project context
5. Creates tasks based on your description

### Scenario 2: Working on an Existing Project

If you've already created a project and want to add more features:

#### Option A: Auto-Discovery (Recommended)

Simply use the same project name - Marcus will find it automatically:

```python
create_project(
    description="Add password reset functionality",
    project_name="UserAuthAPI"  # Same name as before
)
```

**What happens:**
1. Marcus searches for projects named "UserAuthAPI"
2. Finds exact match
3. Automatically switches to that project
4. Adds new tasks to the existing board

#### Option B: Explicit Project Selection

For maximum control, specify the exact project ID:

```python
# First, list your projects to get the ID
list_projects()

# Then create with explicit project_id
create_project(
    description="Add password reset functionality",
    project_name="UserAuthAPI",
    options={"project_id": "abc123xyz"}  # Exact project to use
)
```

### Scenario 3: Creating a New Project When Similar Ones Exist

Sometimes you want a fresh project even though similar ones exist (e.g., "UserAuthAPI-v2"):

```python
create_project(
    description="Build OAuth 2.0 authentication system",
    project_name="UserAuthAPI-v2",
    options={"mode": "new_project"}  # Force new creation
)
```

**What happens:**
1. Marcus skips searching for existing projects
2. Creates a brand new project even if "UserAuthAPI" exists
3. Registers it as a separate project
4. Switches to the new project context

### Scenario 4: Working on Existing Projects Without Creating Tasks

**Two Workflows:**

#### Workflow A: Work on Existing Project (List → Select)

```python
# Step 1: List available projects
projects = list_projects()

# Step 2: Select a project to work on (NO task creation)
result = select_project(name="UserAuthAPI - Main Board")

# Result:
{
    "success": True,
    "action": "selected_existing",
    "project": {
        "id": "proj-123",
        "name": "UserAuthAPI",
        "provider": "planka",
        "task_count": 15  # Existing tasks ready to work on
    },
    "message": "Selected project 'UserAuthAPI' - ready to work"
}

# Step 3: Now request tasks from this project
task = request_next_task(agent_id="my-agent")
```

**Alternative: Select by ID (most reliable)**
```python
result = select_project(project_id="proj-123")
```

#### Workflow B: Create New Project (Just Create)

```python
# No list/select needed - just create
create_project(
    description="Build a REST API for user authentication",
    project_name="UserAuthAPI"
)
```

**Why use `select_project`?**
- ✅ Work on existing backlogs
- ✅ No task creation
- ✅ Clear intent (selection vs creation)
- ✅ Includes fuzzy matching and suggestions

### Scenario 5: Auto-Selecting Projects at Startup (Multi-Agent Deployments)

**For teams running 50+ agents:** Configure a default project in `config_marcus.json` to auto-select on startup:

```json
{
  "default_project_name": "MainProject",
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "user@example.com",
    "password": "password"  # pragma: allowlist secret
  },
  "ai": {...}
}
```

**What happens:**
1. Marcus starts
2. Auto-runs `select_project(name="MainProject")`
3. All agents immediately have the right project context
4. No manual selection needed

**Benefits:**
- ✅ One config for all agents
- ✅ Consistent project context
- ✅ Optional (won't break existing setups)
- ✅ Clean separation: settings vs runtime state

### Scenario 6: Syncing Projects from Planka to Marcus

**Problem:** You have existing projects in Planka that don't appear in Marcus's registry.

When Marcus's project list gets out of sync with your Planka board, use the `sync_projects` tool to import them:

```python
# First, get your Planka project info (manually from Planka UI)
# Then sync them into Marcus:
sync_projects(
    projects=[
        {
            "name": "1st Project",
            "provider": "planka",
            "config": {
                "project_id": "1234567890",
                "board_id": "9876543210"
            },
            "tags": ["production"]
        },
        {
            "name": "Backend API",
            "provider": "planka",
            "config": {
                "project_id": "0987654321",
                "board_id": "1234567890"
            }
        }
    ]
)
```

**Response:**
```json
{
    "success": true,
    "summary": {
        "added": 2,
        "updated": 0,
        "skipped": 0
    },
    "details": {
        "added": [
            {"id": "proj-new-1", "name": "1st Project"},
            {"id": "proj-new-2", "name": "Backend API"}
        ],
        "updated": [],
        "skipped": []
    }
}
```

**What happens:**
1. Marcus checks each project against its registry
2. **New projects** are added to the registry
3. **Existing projects** get their configs updated
4. **Invalid entries** (missing name) are skipped
5. All projects become available in `list_projects()`

**When to use:**
- ✅ Marcus says "project not found" but it exists in Planka
- ✅ After manually creating projects in Planka UI
- ✅ Setting up Marcus with existing Planka boards
- ✅ Recovering from registry corruption

**Automatic Synchronization:**

Marcus automatically synchronizes projects from your Kanban provider on startup. This means:

- New boards in Planka/GitHub appear automatically in Marcus
- Project metadata stays up-to-date
- No manual sync needed in most cases

If `select_project` can't find a project, you can manually sync:

```python
# Force a sync to check for new projects
sync_projects()
```

### Scenario 7: Handling Fuzzy Matches

If Marcus finds similar (but not exact) project names, it will ask for clarification:

```python
# You type a lowercase version
create_project(
    description="Update user profiles",
    project_name="userauthapi"  # lowercase
)
```

**Marcus responds:**
```json
{
    "success": false,
    "action": "found_similar",
    "message": "Found similar projects",
    "matches": [
        {"id": "abc123", "name": "UserAuthAPI", "similarity": 0.9},
        {"id": "xyz789", "name": "UserAuthAPI-v2", "similarity": 0.8}
    ],
    "hint": "To proceed: specify project_id in options or set mode='new_project' to create new"
}
```

**To resolve, use one of these:**

```python
# Option 1: Use the suggested project
create_project(
    description="Update user profiles",
    project_name="userauthapi",
    options={"project_id": "abc123"}  # Use the first match
)

# Option 2: Create new anyway
create_project(
    description="Update user profiles",
    project_name="userauthapi",
    options={"mode": "new_project"}
)
```

## Common Workflows

### 1. Connecting to an Existing Planka Project

If you have a Planka board that's already set up:

```python
add_project(
    name="ExistingProject",
    provider="planka",
    config={
        "project_id": "your-planka-project-id",
        "board_id": "your-planka-board-id"
    },
    make_active=True  # Switch to it immediately
)
```

### 2. Switching Between Projects

```python
# See all your projects
projects = list_projects()

# Switch to a specific one
switch_project(project_id="abc123")

# Check which project is currently active
get_current_project()
```

### 3. Managing Multiple Clients

Organize client work with tags:

```python
# Create client projects with tags
create_project(
    description="E-commerce platform for Client A",
    project_name="ClientA-Shop",
    options={"tags": ["client-a", "ecommerce"]}
)

create_project(
    description="Mobile app for Client B",
    project_name="ClientB-App",
    options={"tags": ["client-b", "mobile"]}
)

# List projects by client
list_projects(filter_tags=["client-a"])
```

## Decision Tree: Which Project Workflow?

Use this flowchart to decide how to create/use projects:

```
Do you have an existing project in Marcus?
├─ NO → Use create_project with any name
│        Marcus will create and register a new project
│
├─ YES → Do you know the exact project ID?
   │
   ├─ YES → Use options.project_id="<id>"
   │         Marcus will use that specific project
   │
   └─ NO → Do you want to use the existing project?
      │
      ├─ YES → Use the same project_name
      │         Marcus will find and use it
      │
      └─ NO (want new project) → Use options.mode="new_project"
                                   Marcus will create a fresh project
```

## Best Practices

### 1. Use Descriptive Project Names

✅ **Good:**
- `CustomerPortal-Frontend`
- `PaymentService-API`
- `MobileApp-iOS-v2`

❌ **Avoid:**
- `Project1`
- `Test`
- `MyProject`

### 2. Leverage Tags for Organization

```python
# Use consistent tag naming
options={
    "tags": [
        "team:backend",
        "priority:high",
        "client:acme-corp",
        "status:active"
    ]
}
```

### 3. Keep Project Names Consistent

When adding features to existing projects, use the **exact same name**:

```python
# Initial creation
create_project(description="...", project_name="UserDashboard")

# Later additions - use same name
create_project(description="Add charts", project_name="UserDashboard")
create_project(description="Add exports", project_name="UserDashboard")
```

### 4. Force New Projects for Major Versions

When starting a significant rewrite or new version:

```python
create_project(
    description="Complete rewrite with React",
    project_name="UserDashboard-v2",
    options={"mode": "new_project"}
)
```

## Understanding Project Providers

Marcus supports multiple kanban providers:

### Planka (Default)
- Self-hosted kanban board
- Full control over data
- Free and open source

```python
options={"provider": "planka"}  # Default, no need to specify
```

### GitHub Projects (Coming Soon)
- Integrated with GitHub repositories
- Issue tracking + project boards
- Native GitHub integration

```python
options={"provider": "github"}  # Not yet implemented
```

### Linear (Coming Soon)
- Modern issue tracking
- Advanced workflow automation
- Team collaboration features

```python
options={"provider": "linear"}  # Not yet implemented
```

## Troubleshooting

### "No project/board IDs found" Error

**Cause:** Marcus couldn't connect to your kanban provider.

**Solution:**
1. Check your `.env` file has correct Planka credentials
2. Verify Planka server is running
3. Test connection: `add_project(...)` with explicit IDs

### "Found similar projects" Message

**Cause:** You used a slightly different name than an existing project.

**Solutions:**
- Use the suggested project ID: `options={"project_id": "abc123"}`
- Force new creation: `options={"mode": "new_project"}`
- Use exact name from the suggestions

### Can't Find My Project

**Check:**
1. List all projects: `list_projects()`
2. Search by provider: `list_projects(provider="planka")`
3. Filter by tags: `list_projects(filter_tags=["my-tag"])`

## Next Steps

- [Managing Projects](managing-projects.md) - Advanced project management
- [Project Tools Reference](../reference/project-tools-reference.md) - Complete API docs
- [Creating Projects with AI](creating-projects.md) - Detailed AI capabilities

## Need Help?

If you encounter issues:
1. Check the [FAQ](../faq.md)
2. Review [Troubleshooting Guide](../troubleshooting.md)
3. Report issues at [GitHub](https://github.com/lwgray/marcus/issues)
