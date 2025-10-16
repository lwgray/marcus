# Active Project Management Overview

This section contains comprehensive documentation about active project selection, timing, and state management in Marcus.

## Key Documents

### [Active Project Selection Reference](active-project-selection-reference)
Complete technical reference for when and how active projects are chosen in Marcus, including:
- System startup flow
- Project creation flow with auto-select
- Manual project selection
- Project sync operations with preservation
- Persistence layer architecture
- Edge cases and failure modes
- Complete state machine

### [Active Project Timing Analysis](active-project-timing-analysis)
Analysis of active project selection bug and its fix, including:
- Current flow with fixes applied
- Problem hypothesis and investigation
- Root cause analysis
- Fixes implemented
- Expected behavior after fix

## Quick Reference

### Active Project Selection Triggers

Active project selection in Marcus happens through **5 primary triggers**:

| Trigger | File | Function | When | Auto/Manual |
|---------|------|----------|------|-------------|
| 1. Server Startup | `server.py:446-586` | `initialize()` | Once at startup | Auto |
| 2. Project Creation | `nlp.py:369-394` | `create_project()` | After successful create | Auto |
| 3. Manual Selection | `project_management.py:475-681` | `select_project()` | User/agent request | Manual |
| 4. Project Sync | `project_management.py:458-643` | `sync_projects()` | After provider sync | Auto (preserve) |
| 5. Project Deletion | `project_registry.py:246-252` | `delete_project()` | When active deleted | Auto (fallback) |

## Key Findings

### Active Project Persistence
- Active project ID stored in `persistence["projects"]["active_project"]`
- Loaded at server startup and restored after restarts
- Synchronized across registry, project manager, and persistence layer

### Project Creation Auto-Select
When a new project is created:
1. Project is created in provider (e.g., Planka)
2. `discover_planka_projects(preserve_active=False)` syncs to registry
3. `switch_project(new_project_id)` switches to the new project
4. Any subsequent syncs use `preserve_active=True` to keep the new project active

### Sync Preservation Logic
- Before sync: Save current active_project_id
- During sync: Add/update projects in registry
- After sync: Restore previously active project (if it still exists)
- If active project deleted during sync: Fallback to first available

## State Machine Summary

```
NO ACTIVE PROJECT
    ├─ create_project (auto-select) → ACTIVE PROJECT SET
    ├─ select_project (manual) → ACTIVE PROJECT SET
    └─ add_project (first project) → ACTIVE PROJECT SET

ACTIVE PROJECT SET
    ├─ select another → Switch to new project
    ├─ create new → Switch to new project
    ├─ sync projects → Preserve active
    ├─ delete active → Fallback to first
    └─ server restart → Restore from persistence
```

## Timing Characteristics

| Operation | Typical Duration |
|-----------|-----------------|
| Registry lookup | < 1ms (in-memory cache) |
| switch_project() | 10-50ms (context creation) |
| get_kanban_client() | 5-20ms (connection reuse) |
| refresh_project_state() | 100-500ms (load tasks, wire deps) |
| Persistence write | 5-50ms (file I/O) |
| **TOTAL** | 120-620ms |

## Bug Fix Summary

### Problem
After project creation, the newly created project would not remain active. Subsequent sync operations were restoring the previously active project.

### Root Cause
Three locations were calling `discover_planka_projects` without the `preserve_active` parameter:
1. `server.py:461` - Startup sync during server initialization
2. `project_management.py:43` - In `list_projects` with `force_sync=True`
3. `project_management.py:493` - In `select_project` during read-through cache sync

### Solution
All three locations now pass `preserve_active=True` to maintain the current active project during sync operations.

## Related Documentation

- [Project Management Systems](index) - Overview of all project management systems
- [Kanban Integration](04-kanban-integration) - How Marcus integrates with Kanban providers
- [Natural Language Project Creation](38-natural-language-project-creation) - How projects are created from descriptions
