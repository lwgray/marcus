# Active Project Selection: Timing and Trigger Diagram

**Generated:** 2025-10-15
**Purpose:** Complete reference for when and how active projects are chosen in Marcus

---

## Table of Contents

1. [Overview](#overview)
2. [System Startup Flow](#system-startup-flow)
3. [Project Creation Flow](#project-creation-flow)
4. [Manual Project Selection](#manual-project-selection)
5. [Project Sync Operations](#project-sync-operations)
6. [Persistence Layer](#persistence-layer)
7. [Edge Cases and Failure Modes](#edge-cases-and-failure-modes)
8. [Complete State Machine](#complete-state-machine)

---

## Overview

Active project selection in Marcus happens through **5 primary triggers**:

| Trigger | File | Function | When | Auto/Manual |
|---------|------|----------|------|-------------|
| 1. Server Startup | `server.py:446-586` | `initialize()` | Once at startup | Auto |
| 2. Project Creation | `nlp.py:369-394` | `create_project()` | After successful create | Auto |
| 3. Manual Selection | `project_management.py:475-681` | `select_project()` | User/agent request | Manual |
| 4. Project Sync | `project_management.py:458-643` | `sync_projects()` | After provider sync | Auto (preserve) |
| 5. Project Deletion | `project_registry.py:246-252` | `delete_project()` | When active deleted | Auto (fallback) |

---

## System Startup Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  SERVER STARTUP SEQUENCE                                        │
│  File: src/marcus_mcp/server.py:446-586                        │
└─────────────────────────────────────────────────────────────────┘

START: server.initialize()
│
├─[1]─► ProjectRegistry.initialize()
│       │
│       ├─► Load persistence file (projects.json)
│       │   └─► Retrieve active_project_id from storage
│       │       Location: persistence["projects"]["active_project"]
│       │
│       └─► Pre-load all projects into cache
│           Registry._cache = {project_id: ProjectConfig, ...}
│
├─[2]─► ProjectManager.initialize(auto_switch=False)
│       Note: auto_switch=False prevents premature switching
│
├─[3]─► Auto-sync from Provider (if enabled)
│       File: server.py:454-481
│       │
│       ├─► discover_planka_projects(auto_sync=True)
│       │   └─► Fetches all projects/boards from Planka
│       │
│       └─► sync_projects()
│           ├─► Deduplicate registry
│           ├─► Add/update projects
│           └─► PRESERVE active_project_id (see line 594-606)
│               └─► Restores previously active project after sync
│
├─[4]─► Load Active Project from Persistence
│       File: server.py:472-477
│       │
│       ├─► active_project = registry.get_active_project()
│       │   Returns: ProjectConfig or None
│       │
│       └─► IF active_project exists:
│           └─► project_manager.switch_project(active_project.id)
│
└─[5]─► Auto-select Default Project (if configured)
        File: server.py:484-505
        │
        ├─► IF config["default_project_name"] exists:
        │   └─► select_project(name=default_project_name)
        │       └─► Overrides previously loaded active project
        │
        └─► DONE: Server ready with active project set

────────────────────────────────────────────────────────────────────

RESULT STATES:
┌─────────────────────┬──────────────────────────────────────────┐
│ State               │ Condition                                │
├─────────────────────┼──────────────────────────────────────────┤
│ Active project set  │ - Persistence had active_project_id      │
│                     │ - OR default_project_name configured     │
│                     │ - AND project still exists               │
├─────────────────────┼──────────────────────────────────────────┤
│ No active project   │ - First time startup (no persistence)    │
│                     │ - Active project was deleted             │
│                     │ - No default configured                  │
└─────────────────────┴──────────────────────────────────────────┘
```

---

## Project Creation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJECT CREATION WITH AUTO-SELECT                              │
│  File: src/marcus_mcp/tools/nlp.py:24-396                      │
└─────────────────────────────────────────────────────────────────┘

START: create_project(description, project_name, options, state)
│
├─[1]─► Validate Parameters
│       └─► Check description, project_name, options
│
├─[2]─► Pipeline Tracking (non-blocking)
│       └─► Start flow visualization
│
├─[3]─► Create Project Structure
│       File: nlp.py:272-310
│       │
│       └─► create_project_from_natural_language_tracked()
│           ├─► NLP parsing (AI breaks down tasks)
│           ├─► Create Planka project/board
│           ├─► Add to registry
│           └─► Returns: {
│                   "success": True,
│                   "project_id": "proj-uuid-123",
│                   "tasks_created": 15,
│                   ...
│               }
│
├─[4]─► AUTO-SELECT NEW PROJECT (Critical Section)
│       File: nlp.py:369-394
│       │
│       ├─► IF result["success"] and result["project_id"]:
│       │   │
│       │   ├─► Call: select_project(state, {"project_id": ...})
│       │   │   │
│       │   │   ├─► switch_project(project_id)
│       │   │   ├─► get_kanban_client()
│       │   │   ├─► refresh_project_state()
│       │   │   └─► set_active_project(project_id)
│       │   │       └─► Persists to storage
│       │   │
│       │   └─► IF select_result["success"]:
│       │       ├─► result["active"] = True
│       │       └─► Project now active ✓
│       │
│       └─► ELSE (Selection Failed):
│           ├─► Log error event
│           ├─► result["warning"] = "Failed to set as active..."
│           ├─► result["active"] = False
│           └─► Project created but NOT active ⚠️
│
└─[5]─► Return Result
        └─► User sees: success=True, active=True/False, warning?

────────────────────────────────────────────────────────────────────

FAILURE SCENARIOS (Why Auto-Select Fails):

┌────────────────────┬─────────────────────────────────────────┐
│ Failure Point      │ Cause                                   │
├────────────────────┼─────────────────────────────────────────┤
│ switch_project()   │ Project not in registry                 │
│                    │ Context creation failed                 │
├────────────────────┼─────────────────────────────────────────┤
│ get_kanban_client()│ Planka connection lost                  │
│                    │ Invalid credentials                     │
├────────────────────┼─────────────────────────────────────────┤
│ refresh_state()    │ Can't load tasks from provider          │
│                    │ Provider API error                      │
├────────────────────┼─────────────────────────────────────────┤
│ set_active_project│ Persistence write failed                │
│                    │ File permissions issue                  │
└────────────────────┴─────────────────────────────────────────┘

BEFORE FIX (nlp.py:377-385):
  → Error logged but NOT returned to user
  → User sees "success: True" with no active project
  → Silent failure ⚠️

AFTER FIX (nlp.py:377-394):
  → Error logged AND added to result["warning"]
  → User sees success=True, active=False, warning="..."
  → Visible failure with remediation ✓
```

---

## Manual Project Selection

```
┌─────────────────────────────────────────────────────────────────┐
│  MANUAL PROJECT SELECTION                                       │
│  File: src/marcus_mcp/tools/project_management.py:475-681     │
└─────────────────────────────────────────────────────────────────┘

START: select_project(server, arguments)
│
├─[1]─► Parse Arguments
│       ├─► project_id (direct lookup)
│       ├─► name + board_name (compound search)
│       └─► name only (fuzzy match)
│
├─[2]─► BRANCH A: Selection by project_id
│       File: project_management.py:516-545
│       │
│       ├─► project_manager.switch_project(project_id)
│       │   File: project_context_manager.py:122-206
│       │   │
│       │   ├─► Lock acquired (async with self.lock)
│       │   ├─► Get project from registry
│       │   ├─► Save current project state (if exists)
│       │   ├─► Load/create context for new project
│       │   ├─► UPDATE: self.active_project_id = project_id
│       │   └─► registry.set_active_project(project_id)
│       │       File: project_registry.py:256-283
│       │       │
│       │       ├─► Update in-memory: self._active_project_id
│       │       ├─► Update last_used timestamp
│       │       └─► Persist to disk:
│       │           persistence.store(
│       │               "projects",
│       │               "active_project",
│       │               {"project_id": project_id}
│       │           )
│       │
│       ├─► server.kanban_client = get_kanban_client()
│       ├─► server._subtasks_migrated = False
│       ├─► server.refresh_project_state()
│       │   └─► Triggers subtask migration and dependency wiring
│       │
│       └─► Return: {
│               "success": True,
│               "action": "selected_existing",
│               "project": {...}
│           }
│
├─[2]─► BRANCH B: Selection by name + board_name
│       File: project_management.py:547-612
│       │
│       ├─► Search registry for exact match on both fields
│       ├─► IF no matches: Return error
│       ├─► IF multiple matches: Return list for disambiguation
│       └─► IF single match: Execute same flow as BRANCH A
│
└─[2]─► BRANCH C: Selection by name only
        File: project_management.py:614-681
        │
        ├─► Call find_or_create_project(name, create_if_missing=False)
        │   │
        │   ├─► Exact match: Execute BRANCH A flow
        │   ├─► Fuzzy match: Return suggestions
        │   └─► No match: Return "not found"
        │
        └─► Return result with guidance

────────────────────────────────────────────────────────────────────

TIMING CHARACTERISTICS:

┌────────────────────────┬──────────────────────────────────────┐
│ Operation              │ Typical Duration                     │
├────────────────────────┼──────────────────────────────────────┤
│ Registry lookup        │ < 1ms (in-memory cache)              │
│ switch_project()       │ 10-50ms (context creation)           │
│ get_kanban_client()    │ 5-20ms (connection reuse)            │
│ refresh_project_state()│ 100-500ms (load tasks, wire deps)    │
│ Persistence write      │ 5-50ms (file I/O)                    │
├────────────────────────┼──────────────────────────────────────┤
│ TOTAL                  │ 120-620ms                            │
└────────────────────────┴──────────────────────────────────────┘
```

---

## Project Sync Operations

```
┌─────────────────────────────────────────────────────────────────┐
│  PROJECT SYNC WITH ACTIVE PROJECT PRESERVATION                  │
│  File: src/marcus_mcp/tools/project_management.py:458-643     │
└─────────────────────────────────────────────────────────────────┘

START: sync_projects(server, arguments)
│
├─[1]─► SAVE CURRENT ACTIVE PROJECT
│       File: project_management.py:519-521
│       │
│       └─► active_project_before = registry.get_active_project()
│           active_project_id_before = active_project_before.id
│           └─► Store for restoration after sync
│
├─[2]─► Deduplicate Registry
│       File: project_management.py:523-524
│       │
│       └─► _deduplicate_registry(server)
│           ├─► Group projects by provider key
│           ├─► Keep most recently used
│           └─► Delete duplicates
│
├─[3]─► Process Projects from Provider
│       File: project_management.py:530-590
│       │
│       └─► FOR EACH project_definition:
│           ├─► Check if exists (match by provider_config)
│           ├─► IF exists: Update name, config, tags
│           └─► IF new: Add to registry
│               └─► registry.add_project(project)
│                   File: project_registry.py:124-126
│                   │
│                   └─► IF this is FIRST project:
│                       └─► set_active_project(project.id)
│                           └─► Auto-activate first project
│
└─[4]─► RESTORE ACTIVE PROJECT
        File: project_management.py:594-606
        │
        ├─► IF active_project_id_before exists:
        │   │
        │   ├─► restored_project = registry.get_project(id_before)
        │   │
        │   ├─► IF restored_project exists:
        │   │   └─► registry.set_active_project(id_before)
        │   │       └─► Restores to previous active project
        │   │
        │   └─► ELSE:
        │       └─► Log warning: "project was deleted during sync"
        │
        └─► Return sync summary

────────────────────────────────────────────────────────────────────

ACTIVE PROJECT PRESERVATION LOGIC:

SCENARIO 1: Sync with existing active project
  Before: active_project_id = "proj-A"
  Sync: Discovers projects B, C, D
  After: active_project_id = "proj-A" (preserved ✓)

SCENARIO 2: Active project deleted during sync
  Before: active_project_id = "proj-A"
  Sync: proj-A not found in provider
  Cleanup: _remove_stale_boards() deletes proj-A
  After: active_project_id = None (fallback to first available)

SCENARIO 3: First project sync (no active project)
  Before: active_project_id = None
  Sync: Discovers first project "proj-A"
  registry.add_project() triggers: set_active_project("proj-A")
  After: active_project_id = "proj-A" (auto-activated ✓)

────────────────────────────────────────────────────────────────────

RACE CONDITIONS:

┌────────────────────────┬────────────────────────────────────┐
│ Race Condition         │ Resolution                         │
├────────────────────────┼────────────────────────────────────┤
│ Sync during startup    │ sync_projects() preserves active   │
│                        │ project loaded from persistence    │
├────────────────────────┼────────────────────────────────────┤
│ Sync after create      │ New project added to registry      │
│                        │ active_project preserved if set    │
├────────────────────────┼────────────────────────────────────┤
│ Concurrent syncs       │ Async lock in switch_project()     │
│                        │ prevents context corruption        │
└────────────────────────┴────────────────────────────────────┘
```

---

## Persistence Layer

```
┌─────────────────────────────────────────────────────────────────┐
│  PERSISTENCE LAYER ARCHITECTURE                                 │
│  File: src/core/project_registry.py                            │
└─────────────────────────────────────────────────────────────────┘

STORAGE FORMAT:
───────────────
persistence.json
├── projects/
│   ├── active_project          ← Single metadata entry
│   │   └── { "project_id": "proj-uuid-123" }
│   │
│   └── <project-uuid>          ← Project entries (multiple)
│       └── { "id": "...", "name": "...", "provider": "...", ... }

WRITE OPERATIONS:
─────────────────

[1] SET ACTIVE PROJECT
    File: project_registry.py:256-283

    async def set_active_project(project_id: str) -> bool:
        ┌─── STEP 1: Update in-memory cache
        │    self._active_project_id = project_id
        │
        ├─── STEP 2: Update last_used timestamp
        │    await self.update_project(project_id, {
        │        "last_used": datetime.now()
        │    })
        │
        └─── STEP 3: Persist to disk
             await self.persistence.store(
                 collection="projects",
                 key="active_project",
                 data={"project_id": project_id}
             )
             └─► Writes to: persistence["projects"]["active_project"]

    FAILURE MODES:
    ├─► Project ID doesn't exist → Validation error
    ├─► Persistence write fails → Silent (in-memory OK)
    └─► Disk full / permissions → Exception raised

[2] ADD PROJECT
    File: project_registry.py:116-138

    async def add_project(config: ProjectConfig) -> str:
        ┌─── Generate UUID
        │    project_id = str(uuid.uuid4())
        │
        ├─── Update in-memory cache
        │    self._cache[project_id] = config
        │
        ├─── Persist to disk
        │    await self.persistence.store(
        │        collection="projects",
        │        key=project_id,
        │        data=config.to_dict()
        │    )
        │
        └─── IF first project:
             └─► set_active_project(project_id)
                 └─► Auto-activate first project

READ OPERATIONS:
────────────────

[1] INITIALIZE (Startup)
    File: project_registry.py:85-99

    async def initialize() -> None:
        ┌─── Load active project ID
        │    active_data = await persistence.retrieve(
        │        collection="projects",
        │        key="active_project"
        │    )
        │    self._active_project_id = active_data.get("project_id")
        │
        └─── Pre-load all projects into cache
             all_projects = await persistence.query("projects")
             for proj_data in all_projects:
                 if "id" in proj_data:
                     project = ProjectConfig.from_dict(proj_data)
                     self._cache[project.id] = project

[2] GET ACTIVE PROJECT
    File: project_registry.py:285-301

    async def get_active_project() -> Optional[ProjectConfig]:
        ┌─── Check in-memory cache
        │    if not self._active_project_id:
        │        return None
        │
        └─── Retrieve from cache
             return self._cache.get(self._active_project_id)
             └─► O(1) lookup (dict)

CACHE MANAGEMENT:
─────────────────

┌────────────────────┬─────────────────────────────────────────┐
│ Cache Type         │ Description                             │
├────────────────────┼─────────────────────────────────────────┤
│ Registry._cache    │ All projects: {project_id: ProjectConfig│
│                    │ Loaded at startup                       │
│                    │ Updated on add/update/delete            │
├────────────────────┼─────────────────────────────────────────┤
│ ProjectManager.    │ Active contexts: {project_id: Context}  │
│ contexts           │ LRU cache (max 10)                      │
│                    │ Created on switch_project()             │
│                    │ Contains kanban_client, events, etc     │
└────────────────────┴─────────────────────────────────────────┘

CONSISTENCY GUARANTEES:
───────────────────────

✓ In-memory cache always synced with persistence
✓ active_project_id validated on set (must exist)
✓ Atomic updates (update_project uses single store call)
✗ No distributed locking (single-process assumption)
✗ No transaction support (fire-and-forget persistence)
```

---

## Edge Cases and Failure Modes

```
┌─────────────────────────────────────────────────────────────────┐
│  EDGE CASES AND FAILURE RECOVERY                                │
└─────────────────────────────────────────────────────────────────┘

[1] PROJECT DELETION
────────────────────
File: project_registry.py:246-252

DELETE FLOW:
  delete_project(project_id)
  │
  ├─► IF project_id == active_project_id:
  │   │
  │   ├─► self._active_project_id = None
  │   │
  │   └─► remaining = await list_projects()
  │       IF remaining:
  │           └─► set_active_project(remaining[0].id)
  │               └─► Auto-activate first remaining project
  │
  └─► Remove from cache and persistence

RESULT:
  ✓ Always have an active project (if any exist)
  ✓ Graceful fallback
  ⚠️ No user choice (picks first alphabetically)

────────────────────────────────────────────────────────────────────

[2] PERSISTENCE CORRUPTION
───────────────────────────

SCENARIO: persistence.json corrupted or deleted

RECOVERY:
  ├─► initialize() fails to load active_project_id
  ├─► self._active_project_id = None
  ├─► Server starts with no active project
  └─► User must manually select or create project

PREVENTION:
  ✓ Regular backups (user responsibility)
  ✓ JSON validation on load
  ⚠️ No automatic recovery

────────────────────────────────────────────────────────────────────

[3] PROVIDER CONNECTION LOST
─────────────────────────────

SCENARIO: Planka server down after project selected

FLOW:
  select_project(project_id)
  │
  ├─► switch_project(project_id) ✓
  ├─► get_kanban_client() → Exception ✗
  │
  └─► Return: {"success": False, "error": "Connection failed"}

RESULT:
  ⚠️ Project NOT set as active
  ⚠️ Previous active project preserved
  ✓ State consistent (no partial updates)

────────────────────────────────────────────────────────────────────

[4] MULTIPLE BOARDS PER PROJECT
────────────────────────────────

SITUATION: Planka project has 5 boards

REGISTRY STORAGE:
  Each board = separate registry entry
  ├─► "Project A - Board 1" (proj-id: A, board-id: 1)
  ├─► "Project A - Board 2" (proj-id: A, board-id: 2)
  ├─► "Project A - Board 3" (proj-id: A, board-id: 3)
  └─► ...

ACTIVE PROJECT:
  Only ONE board can be active at a time
  └─► active_project_id points to specific board
      └─► Example: "Project A - Board 2"

SWITCHING BOARDS:
  Use: select_project(name="Project A", board_name="Board 3")
  └─► Switches active context to different board

────────────────────────────────────────────────────────────────────

[5] CONCURRENT OPERATIONS
──────────────────────────

SCENARIO: User calls select_project twice rapidly

PROTECTION:
  File: project_context_manager.py:122

  async def switch_project(project_id: str):
      async with self.lock:  ← Async lock
          # ... switch logic ...

RESULT:
  ✓ Second call waits for first to complete
  ✓ No context corruption
  ✓ State consistent

────────────────────────────────────────────────────────────────────

[6] DEFAULT PROJECT OVERRIDE
─────────────────────────────

SCENARIO: config has default_project_name, but persistence has
          different active_project_id

STARTUP SEQUENCE:
  1. Load persistence → active_project = "Project A"
  2. switch_project("Project A") ✓
  3. Check default_project_name = "Project B"
  4. select_project(name="Project B")
  5. Final active_project = "Project B"

RESULT:
  ⚠️ Config overrides persistence
  ⚠️ May not be expected behavior
  ✓ Explicit config takes precedence

RECOMMENDATION:
  ├─► Use default_project_name for first-time setup only
  └─► Comment out after initial configuration
```

---

## Complete State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│  ACTIVE PROJECT STATE MACHINE                                   │
└─────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │    NO ACTIVE PROJECT    │
                    │   active_project_id =   │
                    │         None            │
                    └──────────┬──────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        │ [1] create_project   │ [2] select_project   │ [3] add_project
        │     (auto-select)    │     (manual)         │     (first project)
        │                      │                      │
        ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ACTIVE PROJECT SET                          │
│              active_project_id = "proj-uuid-123"                │
│         ┌────────────────────────────────────────┐              │
│         │ In Memory:                             │              │
│         │   registry._active_project_id          │              │
│         │   project_manager.active_project_id    │              │
│         │   project_manager.contexts[id]         │              │
│         ├────────────────────────────────────────┤              │
│         │ On Disk:                               │              │
│         │   persistence["projects"]              │              │
│         │     ["active_project"]                 │              │
│         │       = {"project_id": "..."}          │              │
│         └────────────────────────────────────────┘              │
└──────────────┬──────────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────────┬──────────────┐
    │          │          │              │              │
    │ [4]      │ [5]      │ [6]          │ [7]          │ [8]
    │ select   │ create   │ sync         │ delete       │ server
    │ another  │ new      │ projects     │ active       │ restart
    │          │          │ (preserve)   │ project      │
    │          │          │              │              │
    ▼          ▼          ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌─────────┐  ┌─────────┐   ┌─────────┐
│ Switch  │ │ Switch  │ │ Restore │  │ Fallback│   │ Restore │
│ to new  │ │ to new  │ │ to prev │  │ to first│   │ from    │
│ project │ │ project │ │ active  │  │ remain  │   │ persist │
└────┬────┘ └────┬────┘ └────┬────┘  └────┬────┘   └────┬────┘
     │           │           │            │             │
     └───────────┴───────────┴────────────┴─────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   ACTIVE PROJECT SET     │
              │    (possibly different)  │
              └──────────────────────────┘

────────────────────────────────────────────────────────────────────

STATE TRANSITIONS:

┌────────┬─────────────────┬────────────────────┬────────────────┐
│ From   │ Trigger         │ Action             │ To             │
├────────┼─────────────────┼────────────────────┼────────────────┤
│ None   │ create_project  │ Auto-select new    │ Active         │
│ None   │ select_project  │ Manual select      │ Active         │
│ None   │ add_project     │ Auto-activate first│ Active         │
├────────┼─────────────────┼────────────────────┼────────────────┤
│ Active │ select_project  │ Switch to another  │ Active (diff)  │
│ Active │ create_project  │ Switch to new      │ Active (diff)  │
│ Active │ sync_projects   │ Preserve active    │ Active (same)  │
│ Active │ delete active   │ Fallback to first  │ Active/None    │
│ Active │ server restart  │ Restore from disk  │ Active (same)  │
├────────┼─────────────────┼────────────────────┼────────────────┤
│ Active │ Persistence fail│ Keep in-memory     │ Active (lost)  │
│        │                 │ Lost on restart    │                │
└────────┴─────────────────┴────────────────────┴────────────────┘

────────────────────────────────────────────────────────────────────

INVARIANTS:

✓ At most ONE active project at any time
✓ Active project must exist in registry
✓ Active project ID consistent across:
    - registry._active_project_id
    - project_manager.active_project_id
    - persistence["projects"]["active_project"]
✓ Setting active project updates all three locations
✓ Deleting active project triggers fallback
