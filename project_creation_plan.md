# REVISED Plan: Integrate create_project with Multi-Project System

## Context & Analysis

### Redundancy Confirmed: YES ✅
- **`add_project`**: Manually registers project configs → intended for existing Planka/GitHub/Linear projects
- **`create_project`**: NLP-based creation → auto-creates Planka project/board BUT doesn't register in ProjectRegistry
- **Problem**: `create_project` works in single-project mode, bypasses multi-project infrastructure

### Key User Requirements
1. **"Users working on existing projects shouldn't have to create new ones"**
2. **"Users need a workflow to choose/connect to a specific existing project"** ← CRITICAL MISSING PIECE

---

## USER WORKFLOW: Connecting to Existing Projects

### Scenario 1: User Has Existing Planka/GitHub/Linear Project

**Current Problem**: No clear workflow to "connect Marcus to my existing project board"

**New Workflow**:

```
USER INTENT: "I want Marcus to help with my existing project"

Step 1: User discovers their project
┌────────────────────────────────────────────────────────┐
│ Agent: "What projects exist?"                          │
│ Tool: list_projects()                                  │
│ Response: []  (empty - first time user)                │
└────────────────────────────────────────────────────────┘
    ↓
Step 2: User connects to existing Planka/GitHub project
┌────────────────────────────────────────────────────────┐
│ Agent: "Add my Planka project to Marcus"               │
│ Tool: add_project(                                     │
│   name="E-commerce Platform",                          │
│   provider="planka",                                   │
│   config={                                             │
│     "project_id": "1234567890",  ← Existing Planka ID │
│     "board_id": "9876543210"     ← Existing Board ID  │
│   }                                                     │
│ )                                                       │
│                                                         │
│ Response: {                                            │
│   "success": true,                                     │
│   "project": {                                         │
│     "id": "uuid-abc-123",        ← Marcus internal ID │
│     "name": "E-commerce Platform",                     │
│     "provider": "planka",                              │
│     "is_active": true,                                 │
│     "task_count": 47             ← Tasks from board   │
│   },                                                    │
│   "message": "Connected to existing project"          │
│ }                                                       │
└────────────────────────────────────────────────────────┘
    ↓
Step 3: User works on the project
┌────────────────────────────────────────────────────────┐
│ Agent: "What should I work on?"                        │
│ Tool: request_next_task()                              │
│ → Uses active project (E-commerce Platform)            │
│ → Returns tasks from existing Planka board             │
└────────────────────────────────────────────────────────┘
```

### Scenario 2: User Wants to ADD Features to Existing Project

```
USER INTENT: "Add authentication to my existing project"

Step 1: Verify active project
┌────────────────────────────────────────────────────────┐
│ Agent: "Which project am I working on?"                │
│ Tool: get_current_project()                            │
│ Response: {                                            │
│   "project": {                                         │
│     "id": "uuid-abc-123",                              │
│     "name": "E-commerce Platform",                     │
│     "provider": "planka",                              │
│     "task_count": 47                                   │
│   }                                                     │
│ }                                                       │
└────────────────────────────────────────────────────────┘
    ↓
Step 2: Add tasks to existing project using create_project
┌────────────────────────────────────────────────────────┐
│ Agent: "Add authentication feature"                    │
│ Tool: create_project(                                  │
│   description="Add OAuth2 authentication...",          │
│   project_name="E-commerce Platform",                  │
│   options={                                            │
│     "project_id": "uuid-abc-123",  ← Use existing!    │
│     "mode": "add_feature"           ← NEW option      │
│   }                                                     │
│ )                                                       │
│                                                         │
│ Response: {                                            │
│   "success": true,                                     │
│   "action": "tasks_added",                             │
│   "project": {                                         │
│     "id": "uuid-abc-123",                              │
│     "name": "E-commerce Platform",                     │
│     "task_count": 52  ← 47 + 5 new auth tasks         │
│   },                                                    │
│   "tasks_created": 5,                                  │
│   "new_tasks": [...]                                   │
│ }                                                       │
└────────────────────────────────────────────────────────┘
```

### Scenario 3: New User, No Projects Yet

```
USER INTENT: "Create a new project from scratch"

Step 1: Check for projects
┌────────────────────────────────────────────────────────┐
│ Agent: "Start new project"                             │
│ Tool: list_projects()                                  │
│ Response: [] (empty)                                   │
└────────────────────────────────────────────────────────┘
    ↓
Step 2: Create new project
┌────────────────────────────────────────────────────────┐
│ Agent: "Create task management app"                    │
│ Tool: create_project(                                  │
│   description="Build a web app for task management",   │
│   project_name="TaskMaster",                           │
│   options={                                            │
│     "complexity": "standard",                          │
│     "provider": "planka"                               │
│     # NO project_id = creates new                     │
│   }                                                     │
│ )                                                       │
│                                                         │
│ → Marcus auto-creates Planka project/board            │
│ → Registers in ProjectRegistry                        │
│ → Generates tasks                                      │
│ → Sets as active project                              │
│                                                         │
│ Response: {                                            │
│   "success": true,                                     │
│   "action": "project_created",                         │
│   "project": {                                         │
│     "id": "uuid-xyz-789",                              │
│     "name": "TaskMaster",                              │
│     "provider": "planka",                              │
│     "is_new": true,                                    │
│     "planka_url": "http://localhost:3333/..."         │
│   },                                                    │
│   "tasks_created": 15                                  │
│ }                                                       │
└────────────────────────────────────────────────────────┘
```

---

## NEW: Onboarding Flow Documentation

### Decision Tree for Users

```
┌─────────────────────────────────────────┐
│ "What do you want to do with Marcus?"  │
└─────────────────────────────────────────┘
            │
            ├─────────────────────────────────────────┐
            ↓                                         ↓
┌──────────────────────────────┐    ┌────────────────────────────┐
│ "Work on existing project"   │    │ "Create new project"       │
└──────────────────────────────┘    └────────────────────────────┘
            │                                         │
            ↓                                         ↓
┌──────────────────────────────┐    ┌────────────────────────────┐
│ Is project in Marcus?        │    │ Do you have existing       │
│                              │    │ Planka/GitHub board?       │
│ Call: list_projects()        │    └────────────────────────────┘
└──────────────────────────────┘                │
            │                                    ├──── YES ───┐
            ├─── YES ───┐                       ↓             ↓
            ↓            ↓            ┌──────────────┐  ┌─────────────┐
    ┌──────────┐  ┌──────────┐      │ Use:         │  │ Use:        │
    │ Use:     │  │ Use:     │      │ add_project  │  │ create_     │
    │ switch_  │  │ add_     │      │ (connect to  │  │ project     │
    │ project  │  │ project  │      │  existing)   │  │ (auto-      │
    │          │  │          │      └──────────────┘  │  create)    │
    └──────────┘  └──────────┘                        └─────────────┘
```

---

## Enhanced create_project Behavior

### New Mode: "add_feature" vs "new_project"

```python
options = {
    "project_id": "uuid-123",     # If provided, USE THIS PROJECT
    "mode": "add_feature",         # NEW: add_feature | new_project | auto

    # mode="add_feature" behavior:
    #   - Requires project_id
    #   - Adds tasks to existing board
    #   - Respects existing task structure
    #   - No new Planka project/board creation

    # mode="new_project" behavior:
    #   - Ignores project_id (or creates new with suffix)
    #   - Creates new Planka project/board
    #   - Registers in ProjectRegistry

    # mode="auto" (default):
    #   - If project_id provided → add_feature
    #   - Else → new_project
}
```

---

## PHASE 0: Discovery & Onboarding Workflow (NEW)

### 0.1 Create "Getting Started with Projects" Guide

**File**: `docs/source/guides/project-management/getting-started-projects.md` (NEW)

```markdown
# Getting Started with Projects in Marcus

This guide helps you decide how to set up your first project with Marcus.

## I Have an Existing Planka/GitHub Project

If you already have a project board with tasks, connect Marcus to it:

### Step 1: Find Your Project IDs

**For Planka**:
- Project ID: Found in URL or Planka settings
- Board ID: Found in URL or board settings

**For GitHub**:
- Owner: Your GitHub username/org
- Repo: Repository name
- Project Number: In project URL

**For Linear**:
- Team ID: From Linear settings
- Project ID: From project URL

### Step 2: Add Project to Marcus

```python
result = await add_project(
    name="My Existing Project",
    provider="planka",  # or "github", "linear"
    config={
        "project_id": "1234567890",  # Your Planka project ID
        "board_id": "9876543210"     # Your Planka board ID
    },
    make_active=True
)
```

Marcus will:
- Connect to your existing board
- Import all tasks
- Make it the active project
- Ready for agents to request tasks

### Step 3: Verify Connection

```python
result = await get_current_project()
# Shows: Your project with task count
```

## I'm Starting Fresh

If you don't have a project board yet, let Marcus create one:

```python
result = await create_project(
    description="Build a task management web app",
    project_name="TaskMaster",
    options={
        "complexity": "standard",
        "provider": "planka"
    }
)
```

Marcus will:
- Create Planka project and board
- Generate tasks from your description
- Register project in Marcus
- Set as active project

## I Want to Add Features to Existing Project

Already using Marcus and want to add more tasks:

```python
# First, verify active project
current = await get_current_project()
# Shows: "TaskMaster" with 15 tasks

# Add authentication feature
result = await create_project(
    description="Add OAuth2 authentication with Google and GitHub",
    project_name="TaskMaster",
    options={
        "project_id": current["project"]["id"],  # Use existing!
        "mode": "add_feature"
    }
)

# Result: 5 new tasks added to existing project (now 20 total)
```
```

### 0.2 Add Discovery Tool: find_or_create_project (NEW MCP Tool)

**File**: `src/marcus_mcp/tools/project_management.py` (ADD FUNCTION)

```python
async def find_or_create_project(
    server: Any,
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Smart helper to find existing project or guide creation.

    This tool helps users navigate the "which project?" decision.

    Args:
        project_name: Name to search for
        create_if_missing: Auto-create if not found (default: False)
        provider: Provider for auto-creation (default: "planka")

    Returns:
        Found project, creation guidance, or new project details
    """
    project_name = arguments.get("project_name")
    create_if_missing = arguments.get("create_if_missing", False)
    provider = arguments.get("provider", "planka")

    # Search for existing projects
    projects = await server.project_registry.list_projects()
    exact_matches = [p for p in projects if p.name == project_name]
    fuzzy_matches = [p for p in projects if project_name.lower() in p.name.lower()]

    if exact_matches:
        # Found exact match
        project = exact_matches[0]
        return {
            "action": "found_existing",
            "project": {
                "id": project.id,
                "name": project.name,
                "provider": project.provider,
                "task_count": await get_task_count(server, project.id)
            },
            "next_steps": [
                f"Use project: switch_project(project_id='{project.id}')",
                f"Add tasks: create_project(..., options={{'project_id': '{project.id}'}})"
            ]
        }

    elif fuzzy_matches:
        # Found similar projects
        return {
            "action": "found_similar",
            "matches": [
                {
                    "id": p.id,
                    "name": p.name,
                    "provider": p.provider,
                    "similarity": calculate_similarity(project_name, p.name)
                }
                for p in fuzzy_matches
            ],
            "suggestion": "Did you mean one of these projects?",
            "next_steps": [
                "Use similar: switch_project(project_name='...')",
                f"Create new: create_project(..., project_name='{project_name}')"
            ]
        }

    else:
        # No matches found
        if create_if_missing:
            # Auto-create new project entry (just registration, not full creation)
            return {
                "action": "guide_creation",
                "message": f"No project '{project_name}' found. Ready to create.",
                "options": [
                    {
                        "option": "Create from description",
                        "tool": "create_project",
                        "example": f"create_project(description='...', project_name='{project_name}')"
                    },
                    {
                        "option": "Connect existing Planka/GitHub project",
                        "tool": "add_project",
                        "example": f"add_project(name='{project_name}', provider='planka', config={{...}})"
                    }
                ]
            }
        else:
            return {
                "action": "not_found",
                "message": f"No project named '{project_name}' found in Marcus",
                "total_projects": len(projects),
                "suggestion": "List all projects with: list_projects()",
                "next_steps": [
                    "Create new: create_project(...)",
                    "Connect existing: add_project(...)",
                    "View all: list_projects()"
                ]
            }
```

---

## PHASE 1: Project Selection UX Design (UPDATED)

### Enhanced create_project Workflow

```
Agent calls: create_project("Build a REST API", "MyAPI", options={...})
    ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 1: Check Explicit Instructions                       │
│                                                            │
│ If options.project_id is provided:                        │
│   → SKIP project selection entirely                       │
│   → Use specified project                                 │
│   → Add tasks to that project                             │
│   → Return success                                         │
│                                                            │
│ If options.mode == "new_project":                         │
│   → SKIP project selection                                │
│   → Force create new project                              │
│   → Auto-create Planka/GitHub board                       │
│   → Register in ProjectRegistry                           │
│   → Return success                                         │
│                                                            │
│ Otherwise → Continue to Step 2                            │
└────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 2: Search for Existing Projects                      │
│                                                            │
│ Query ProjectRegistry for:                                │
│   • Exact name match: "MyAPI"                             │
│   • Fuzzy matches: "MyAPI-Dev", "MyAPI-v2"                │
│   • Same provider + recent activity                       │
│                                                            │
│ Cases:                                                     │
│   0 matches → Create new (Step 3a)                       │
│   1 match → Prompt confirmation (Step 3b)                 │
│   2+ matches → Show selection (Step 3c)                   │
└────────────────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────────────────┐
│ STEP 3a: No Matches - Create New Project                  │
│                                                            │
│ Actions:                                                   │
│   1. Create ProjectConfig                                 │
│   2. Auto-setup Planka/GitHub project & board             │
│   3. Register in ProjectRegistry                          │
│   4. Switch to new project                                │
│   5. Generate tasks via NLP                               │
│   6. Create tasks on board                                │
│                                                            │
│ Return: {                                                  │
│   "success": true,                                         │
│   "action": "project_created",                            │
│   "project": {...},                                        │
│   "tasks_created": 15                                      │
│ }                                                           │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ STEP 3b: One Match - Prompt for Reuse                     │
│                                                            │
│ Return: {                                                  │
│   "action": "confirm_reuse",                               │
│   "found_project": {                                       │
│     "id": "abc-123",                                       │
│     "name": "MyAPI",                                       │
│     "task_count": 12,                                      │
│     "last_used": "2 hours ago"                             │
│   },                                                        │
│   "recommendation": "Add tasks to existing project",      │
│   "next_steps": {                                          │
│     "add_to_existing": {                                  │
│       "tool": "create_project",                           │
│       "params": {                                          │
│         "description": "...",                              │
│         "project_name": "MyAPI",                           │
│         "options": {"project_id": "abc-123"}              │
│       }                                                     │
│     },                                                      │
│     "create_new_instead": {                               │
│       "tool": "create_project",                           │
│       "params": {                                          │
│         "project_name": "MyAPI-2",                         │
│         "options": {"mode": "new_project"}                │
│       }                                                     │
│     }                                                       │
│   }                                                         │
│ }                                                           │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ STEP 3c: Multiple Matches - Selection Required            │
│                                                            │
│ Return: {                                                  │
│   "action": "select_project",                              │
│   "matches": [                                             │
│     {id: "abc", name: "MyAPI", tasks: 12, provider: "planka"},
│     {id: "def", name: "MyAPI-Dev", tasks: 8, provider: "planka"},
│     {id: "ghi", name: "MyAPI-Prod", tasks: 25, provider: "github"}
│   ],                                                        │
│   "message": "Multiple projects found. Specify project_id",│
│   "next_steps": "Use project_id in options to select one" │
│ }                                                           │
└────────────────────────────────────────────────────────────┘
```

---

## PHASE 2: Code Implementation (UPDATED)

### 2.0 Add find_or_create_project Tool (NEW)

**File**: `src/marcus_mcp/tools/project_management.py`
- Add `find_or_create_project` function (documented above)

**File**: `src/marcus_mcp/server.py`
- Register `find_or_create_project` as MCP tool

### 2.1 Create Project Auto-Setup Module

**File**: `src/integrations/project_auto_setup.py` (NEW)

```python
"""
Provider-agnostic project auto-setup for create_project.
"""

class ProjectAutoSetup:
    async def setup_new_project(
        provider: str,
        project_name: str,
        options: Dict[str, Any]
    ) -> ProjectConfig:
        """Dispatch to provider-specific setup"""

    async def setup_planka_project(...) -> ProjectConfig
    async def setup_github_project(...) -> ProjectConfig
    async def setup_linear_project(...) -> ProjectConfig
```

### 2.2 Update MCP Tool Layer

**File**: `src/marcus_mcp/tools/nlp.py::create_project` (MODIFY)

```python
async def create_project(...) -> Dict[str, Any]:
    # STEP 1: Check explicit instructions
    project_id = options.get("project_id") if options else None
    mode = options.get("mode", "auto") if options else "auto"

    if project_id:
        # User specified project - use it directly
        project = await state.project_registry.get_project(project_id)
        if not project:
            return {"error": f"Project {project_id} not found"}

        # Switch to this project
        await state.project_manager.switch_project(project_id)

        # Add tasks to existing project
        result = await create_project_from_natural_language_tracked(
            description=description,
            project_name=project_name,
            state=state,
            options=options,
            flow_id=flow_id,
            existing_project=project  # NEW parameter
        )

        result["action"] = "tasks_added_to_existing"
        return result

    if mode == "new_project":
        # Force create new - skip search
        # ... create new project logic
        return result

    # STEP 2: Search for existing projects (auto mode)
    existing = await state.project_registry.list_projects()
    exact_matches = [p for p in existing if p.name == project_name]

    if len(exact_matches) == 1:
        # Return confirmation prompt
        return {
            "action": "confirm_reuse",
            "found_project": {...},
            "next_steps": {...}
        }

    elif len(exact_matches) > 1:
        # Return selection menu
        return {
            "action": "select_project",
            "matches": [...],
            "next_steps": {...}
        }

    # STEP 3: No matches - create new project
    from src.integrations.project_auto_setup import ProjectAutoSetup

    auto_setup = ProjectAutoSetup()
    project_config = await auto_setup.setup_new_project(
        provider=options.get("provider", "planka"),
        project_name=project_name,
        options=options
    )

    # Register in ProjectRegistry
    project_id = await state.project_registry.add_project(project_config)
    await state.project_manager.switch_project(project_id)

    # Create tasks
    result = await create_project_from_natural_language_tracked(...)
    result["action"] = "project_created"
    result["project"]["is_new"] = True

    return result
```

### 2.3 Update NLP Tools Layer

**File**: `src/integrations/nlp_tools.py` (MODIFY)

```python
async def create_project_from_natural_language(
    description: str,
    project_name: str,
    state: Any,
    existing_project: Optional[ProjectConfig] = None,  # NEW
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    If existing_project provided:
      - Don't create new Planka project/board
      - Add tasks to existing board
      - Return with action="tasks_added"

    Otherwise:
      - Assume auto-setup was done in MCP layer
      - Create tasks on newly created board
      - Return with action="project_created"
    """

    is_adding_to_existing = existing_project is not None

    # Skip Planka auto-creation if adding to existing
    if not is_adding_to_existing:
        # Auto-create logic (existing code)
        if not state.kanban_client.project_id or not state.kanban_client.board_id:
            # ... existing auto-setup code
            pass

    # Generate tasks (same for both cases)
    tasks = await self.process_natural_language(...)

    # Create tasks on board
    created_tasks = await self.create_tasks_on_board(tasks)

    return {
        "success": True,
        "action": "tasks_added" if is_adding_to_existing else "project_created",
        "project": {
            "id": existing_project.id if existing_project else new_project_id,
            "name": project_name,
            "is_new": not is_adding_to_existing
        },
        "tasks_created": len(created_tasks),
        "tasks": created_tasks
    }
```

---

## PHASE 3: Documentation Updates (UPDATED)

### 3.0 Getting Started Guide (NEW - PRIORITY #1)

**File**: `docs/source/guides/project-management/getting-started-projects.md` (NEW)
- Content documented in "PHASE 0: Discovery & Onboarding" above
- This is the FIRST doc users see

### 3.1 Managing Projects Guide (NEW)

**File**: `docs/source/guides/project-management/managing-projects.md` (NEW)

```markdown
# Managing Multiple Projects

## Listing Projects
## Switching Between Projects
## Adding Existing Planka/GitHub Projects
## Removing Projects
## Updating Project Configuration
```

### 3.2 Project Tools Reference (NEW)

**File**: `docs/source/guides/project-management/project-tools-reference.md` (NEW)

```markdown
# Project Management Tools Reference

## find_or_create_project (NEW)
Smart helper for discovering or creating projects

## list_projects
## switch_project
## get_current_project
## add_project
## remove_project
## update_project
## create_project (with project selection modes)
```

### 3.3 Update Creating Projects Guide

**File**: `docs/source/guides/project-management/creating-projects.md` (UPDATE)

Add sections:
- **"Using create_project with Existing Projects"**
- **"Project Selection Modes"** (auto, add_feature, new_project)
- **"When to Use add_project vs create_project"**

### 3.4 Update API Documentation

**File**: `docs/source/api/mcp_tools.rst` (UPDATE)

Add under "Project Management Tools":
```rst
.. autofunction:: find_or_create_project
.. autofunction:: list_projects
.. autofunction:: switch_project
.. autofunction:: get_current_project
.. autofunction:: add_project
.. autofunction:: remove_project
.. autofunction:: update_project
```

### 3.5 Update Index Files

**File**: `docs/source/guides/index.rst` (UPDATE)

```rst
Project Management
------------------

.. toctree::
   :maxdepth: 1

   project-management/getting-started-projects     # NEW - First!
   project-management/creating-projects
   project-management/managing-projects            # NEW
   project-management/project-tools-reference      # NEW
   project-management/monitoring-status
   project-management/analyzing-health
```

**File**: `docs/source/index.rst` (UPDATE)

Add to main Guides toctree:
```rst
guides/project-management/getting-started-projects
guides/project-management/managing-projects
guides/project-management/project-tools-reference
```

### 3.6 Cross-Link Documentation

**File**: `docs/source/systems/project-management/16-project-management.md` (UPDATE)

Add at top:
```markdown
> **User Guides**:
> - [Getting Started with Projects](../../guides/project-management/getting-started-projects.md)
> - [Managing Multiple Projects](../../guides/project-management/managing-projects.md)
> - [Project Tools Reference](../../guides/project-management/project-tools-reference.md)
```

---

## PHASE 4: Testing Strategy

### Unit Tests

**File**: `tests/unit/mcp/test_find_or_create_project.py` (NEW)
```python
def test_find_exact_match()
def test_find_fuzzy_matches()
def test_not_found_returns_guidance()
def test_create_if_missing()
```

**File**: `tests/unit/mcp/test_create_project_selection.py` (NEW)
```python
def test_explicit_project_id_skips_search()
def test_mode_new_project_forces_creation()
def test_mode_add_feature_requires_project_id()
def test_no_matches_creates_new()
def test_one_match_returns_confirmation()
def test_multiple_matches_returns_selection()
```

### Integration Tests

**File**: `tests/integration/e2e/test_project_workflows.py` (NEW)
```python
async def test_workflow_connect_existing_planka():
    # add_project with existing IDs
    # request_next_task uses that project

async def test_workflow_create_then_add_features():
    # create_project creates new
    # create_project again with project_id adds tasks

async def test_workflow_find_or_create():
    # find_or_create_project guides user
    # Follow guidance to create/connect
```

---

## PHASE 5: Implementation Order (UPDATED)

```
1. Documentation First ✅
   → Understand user workflows
   → Design decision trees
   → Plan guides structure

2. Create find_or_create_project Tool (NEW - PRIORITY)
   → Helps users navigate "which project?" decision
   → Foundation for good UX
   → File: src/marcus_mcp/tools/project_management.py
   → Register in src/marcus_mcp/server.py

3. Create Project Auto-Setup Module
   → File: src/integrations/project_auto_setup.py
   → Extract Planka auto-creation
   → Add GitHub/Linear stubs

4. Implement Project Selection in create_project
   → Update src/marcus_mcp/tools/nlp.py
   → Add explicit project_id handling
   → Add mode handling (auto/add_feature/new_project)
   → Add search & prompt logic

5. Update NLP Tools for Existing Projects
   → Update src/integrations/nlp_tools.py
   → Accept existing_project parameter
   → Skip auto-creation if adding to existing
   → Return appropriate action in response

6. Write User-Facing Documentation (CRITICAL)
   → getting-started-projects.md (FIRST)
   → managing-projects.md
   → project-tools-reference.md
   → Update creating-projects.md
   → Update mcp_tools.rst
   → Update all index files

7. Write Tests
   → test_find_or_create_project.py
   → test_create_project_selection.py
   → test_project_workflows.py (integration)

8. Update Cross-Links & Polish
   → Add user guide links to systems docs
   → Verify all links work
   → Test full user workflows
```

---

## Key Changes from Previous Plan

✅ **Added PHASE 0**: Discovery & Onboarding workflow
✅ **Added find_or_create_project tool**: Smart helper for "which project?" decision
✅ **Added getting-started-projects.md**: First doc users see - explains workflows
✅ **Enhanced create_project modes**: auto | add_feature | new_project
✅ **Clear workflows for**:
   - Connecting to existing Planka/GitHub project
   - Creating new project from scratch
   - Adding features to existing Marcus project
✅ **Decision tree diagrams**: Visual guide for users
✅ **Explicit project_id handling**: Skip all prompts when user knows what they want

---

## File Changes Summary

**NEW FILES** (8):
- `src/integrations/project_auto_setup.py`
- `src/marcus_mcp/tools/project_discovery.py` (find_or_create_project)
- `docs/source/guides/project-management/getting-started-projects.md` ← CRITICAL
- `docs/source/guides/project-management/managing-projects.md`
- `docs/source/guides/project-management/project-tools-reference.md`
- `tests/unit/mcp/test_find_or_create_project.py`
- `tests/unit/mcp/test_create_project_selection.py`
- `tests/integration/e2e/test_project_workflows.py`

**MODIFIED FILES** (8):
- `src/marcus_mcp/tools/nlp.py` (project selection + modes)
- `src/marcus_mcp/tools/project_management.py` (add find_or_create_project)
- `src/marcus_mcp/server.py` (register new tool)
- `src/integrations/nlp_tools.py` (accept existing_project param)
- `docs/source/guides/project-management/creating-projects.md` (add reuse section)
- `docs/source/api/mcp_tools.rst` (add new tools)
- `docs/source/guides/index.rst` (add new guides)
- `docs/source/index.rst` (add to main toctree)

**UPDATED LINKS** (2):
- `docs/source/systems/project-management/16-project-management.md`
- `docs/source/systems/project-management/34-create-project-tool.md`

---

## Success Criteria

✅ User can discover existing projects: `list_projects()` or `find_or_create_project()`
✅ User can connect to existing Planka board: `add_project()`
✅ User can add tasks to existing project: `create_project(..., options={"project_id": "..."})`
✅ User can force new project: `create_project(..., options={"mode": "new_project"})`
✅ User sees clear guidance when project name is ambiguous
✅ Documentation explains all workflows with examples
✅ Tests cover all user paths (new, existing, ambiguous)
✅ Backward compatible: No options = creates new project (existing behavior)
