# Active Project Selection Timing Analysis

## Current Flow (with our fixes)

```
TIME  | LOCATION                           | ACTION                                      | ACTIVE PROJECT
------|------------------------------------|--------------------------------------------|------------------
T0    | User                               | create_project("Final Test")                | "Second Test"
T1    | nlp.py:285                         | create_project_from_natural_language()      | "Second Test"
T2    | nlp_tools.py:1001                  | Create Planka project/board                | "Second Test"
T3    | nlp_tools.py:1031                  | discover_planka_projects(preserve_active=False) | "Second Test"
T4    | project_management.py:749          | Connect to Planka, fetch projects           | "Second Test"
T5    | project_management.py:815          | sync_projects(preserve_active=False)        | "Second Test"
T6    | project_management.py:1016         | Save active_project_before = "Second Test"  | "Second Test"
T7    | project_management.py:1020-1086    | Add/update projects in registry             | "Second Test"
      |                                    | (including "Final Test")                    |
T8    | project_management.py:1092         | Check preserve_active (FALSE)               | "Second Test"
      |                                    | SKIP restoration (this is correct!)         |
T9    | nlp_tools.py:1081                  | switch_project(marcus_project_id)           | "Final Test" ✓
T10   | nlp.py:375                         | select_project(skip_sync=True)              | "Final Test"
T11   | project_management.py:519          | Check skip_sync (TRUE)                      | "Final Test"
      |                                    | SKIP sync (correct)                         |
T12   | project_management.py:536          | switch_project(project_id) again            | "Final Test" ✓
T13   | nlp.py:396                         | Return result["active"]=True                | "Final Test" ✓
```

## Problem Hypothesis

Looking at the timestamps from list_projects:
- "Second Test Project" last_used: `17:53:29.947043`
- "Final Test" last_used: `17:53:29.942877`

The new project was updated at `.942877` but "Second Test" was updated at `.947043` - **5ms later!**

This suggests something is touching "Second Test" AFTER we switch to "Final Test".

## Possible Causes

### 1. ✅ FOUND IT - startup sync in server.py:461
In `server.py:461`, during server initialization, there's a startup sync:
```python
result = await discover_planka_projects(self, {"auto_sync": True})
```

**This doesn't pass preserve_active parameter!** If this runs AFTER project creation (or gets triggered by MCP operations), it would restore the old active project.

### 2. ❓ list_projects calling discover_planka_projects
In `project_management.py:43`, `list_projects` has `force_sync=True` by default:
```python
if force_sync:
    sync_result = await discover_planka_projects(server, {"auto_sync": True})
```

**This also doesn't pass preserve_active!**

### 3. ❓ Concurrent operations
Could there be async operations happening in parallel that are racing?

## Investigation Steps

1. Check if `list_projects` is being called during or after project creation
2. Check if `refresh_project_state` triggers any syncs
3. Add logging to track all `set_active_project` calls with timestamps
4. Check if `get_project_status` MCP tool triggers a sync

## Root Cause Summary

After analysis, we found TWO locations calling `discover_planka_projects` without `preserve_active`:

1. **`server.py:461`** - Startup sync during server initialization
2. **`project_management.py:43`** - In `list_projects` with `force_sync=True`
3. **`project_management.py:493`** - In `select_project` during read-through cache sync

These sync operations were restoring the previously active project AFTER we switched to the newly created project.

## Fixes Implemented

### Fix 1: server.py:461
```python
# BEFORE
result = await discover_planka_projects(self, {"auto_sync": True})

# AFTER
result = await discover_planka_projects(
    self, {"auto_sync": True, "preserve_active": True}
)
```

### Fix 2: project_management.py:43
```python
# BEFORE
sync_result = await discover_planka_projects(server, {"auto_sync": True})

# AFTER
sync_result = await discover_planka_projects(
    server, {"auto_sync": True, "preserve_active": True}
)
```

### Fix 3: project_management.py:493
```python
# BEFORE
sync_result = await discover_planka_projects(server, {"auto_sync": True})

# AFTER
sync_result = await discover_planka_projects(
    server, {"auto_sync": True, "preserve_active": True}
)
```

## Expected Behavior After Fix

When a new project is created:
1. Project is created in Planka ✓
2. `discover_planka_projects(preserve_active=False)` syncs it to registry ✓
3. `switch_project(new_project_id)` switches to the new project ✓
4. Any subsequent syncs use `preserve_active=True` to keep the new project active ✓

The new project should now remain active after creation.
