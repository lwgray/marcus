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

### Scenario 4: Handling Fuzzy Matches

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
