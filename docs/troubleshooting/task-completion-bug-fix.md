# Task Completion Bug Fix

## Problem

The `examples/calculator_project_workflow.py` script was **not moving tasks from IN_PROGRESS to DONE**.

## Root Cause

**Field Name Mismatch** in `calculator_project_workflow.py:382-383`

The script was using incorrect field names when parsing the task response:

### ❌ **WRONG (Before Fix)**
```python
task = task_data["task"]
task_id = task.get("task_id", "unknown")  # ❌ Field doesn't exist!
task_title = task.get("title", "Untitled Task")  # ❌ Field doesn't exist!
```

### ✅ **CORRECT (After Fix)**
```python
task = task_data["task"]
task_id = task.get("id", "unknown")  # ✅ Correct field name
task_title = task.get("name", "Untitled Task")  # ✅ Correct field name
```

## What Was Happening

1. Agent requests task via `request_next_task`
2. Marcus returns task with structure:
   ```json
   {
     "success": true,
     "task": {
       "id": "abc123",           ← Actual field name
       "name": "Design Addition", ← Actual field name
       "description": "...",
       "priority": "medium"
     }
   }
   ```
3. Script tried to get `task.get("task_id")` → got `"unknown"`
4. Script tried to report progress with `task_id="unknown"`
5. Marcus couldn't find task with ID "unknown" → **task status never updated**
6. Task remained stuck in IN_PROGRESS forever

## Actual Task Response Structure

Based on `src/marcus_mcp/tools/task.py:551-564`:

```python
response: Dict[str, Any] = {
    "success": True,
    "task": {
        "id": optimal_task.id,                    # ← Use "id"
        "name": optimal_task.name,                # ← Use "name"
        "description": optimal_task.description,
        "instructions": instructions,
        "priority": optimal_task.priority.value,
        "implementation_context": previous_implementations,
        "project_id": active_project.id if active_project else None,
        "project_name": active_project.name if active_project else None,
    },
}
```

## How to Verify the Fix Works

Run the test script:
```bash
python test_workflow.py
```

Or run the full calculator workflow:
```bash
python examples/calculator_project_workflow.py
```

You should now see:
- Tasks start with status "TODO"
- Move to "IN_PROGRESS" when agent starts work
- Move to "DONE" when agent reports completion
- Dependent tasks become available after completion

## Lessons Learned

### 1. Always Check API Response Structure
Don't assume field names - verify them in the implementation:
- Check `src/marcus_mcp/tools/task.py` for actual response format
- Use type hints and IDE autocomplete when possible
- Add logging to see actual response data during development

### 2. Use Consistent Field Names
The inconsistency came from different conventions:
- Task model uses: `task.id` and `task.name`
- Some older code used: `task_id` and `title`
- Always reference the source of truth (the MCP tool implementation)

### 3. Test with Real Data
The script worked partially (requested tasks) but failed silently on completion because:
- No error was raised when task ID was "unknown"
- Progress reports just failed silently
- Should add validation or error checking

## Recommended Improvements

### Add Validation to Example Scripts

```python
task = task_data["task"]
task_id = task.get("id")
task_name = task.get("name")

# Validate we got real data
if not task_id or task_id == "unknown":
    raise ValueError(f"Invalid task_id in response: {task}")

if not task_name:
    raise ValueError(f"Missing task name in response: {task}")
```

### Add Debug Logging

```python
logger.log("task_structure", "Full task response", task_data)
logger.log("extracted_fields", f"task_id={task_id}, task_name={task_name}")
```

### Document the Response Format

Create API reference docs showing exact response structures for all MCP tools.
✅ **DONE**: Created `docs/api-reference/report-task-progress.md`

## Related Files

- **Bug Location**: `examples/calculator_project_workflow.py:382-383`
- **Fix Commit**: Updated field names from `task_id`→`id` and `title`→`name`
- **Source of Truth**: `src/marcus_mcp/tools/task.py:551-564`
- **Test Script**: `test_workflow.py`
- **Documentation**: `docs/api-reference/report-task-progress.md`

## Status

✅ **FIXED** - Tasks now properly move from IN_PROGRESS to DONE

The fix has been applied to `examples/calculator_project_workflow.py`.
