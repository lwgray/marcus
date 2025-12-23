# Testing the MCP Tool Logger

This guide explains how to test the MCP tool logger in different scenarios.

## Overview

The MCP tool logger tracks MCP tool activity (WHAT failed and WHEN) and points operators to diagnostic logs for root cause analysis (WHY).

## Test Levels

### 1. Unit Tests ✅

**Location:** `tests/unit/logging/test_mcp_tool_logger.py`

**Run:**
```bash
python -m pytest tests/unit/logging/test_mcp_tool_logger.py -v
```

**Coverage:** 14 tests covering:
- Success/failure logging
- Log levels (DEBUG for success, WARNING for failures)
- Diagnostic pointers for `request_next_task`
- Integration with conversation logger
- Activity tracking behavior (WHAT/WHEN, not WHY)

### 2. Integration Tests ✅

**Location:** `tests/integration/logging/test_mcp_tool_logger_integration.py`

**Run:**
```bash
python -m pytest tests/integration/logging/test_mcp_tool_logger_integration.py -v
```

**Coverage:** 11 tests covering:
- Real-world failure scenarios
- Log entry creation
- Structured logging format
- End-to-end convenience functions

### 3. Live Testing (Real Marcus System) ✅

**Automated Live Test Script** (Recommended):

```bash
# 1. Start Marcus HTTP server
python -m src.marcus_mcp.server --http

# 2. In another terminal, run live test
python dev-tools/examples/test_mcp_logger_live.py
```

**What it tests:**
- ✅ Scenario 1: No tasks available
- ✅ Scenario 2: Agent already busy
- ✅ Scenario 3: All tasks assigned
- ✅ Scenario 4: Other tool failures (non-request_next_task)

**The script automatically:**
1. Connects to running Marcus HTTP server
2. Authenticates as admin
3. Triggers 4 different failure scenarios
4. Shows you exactly where to look in logs
5. Provides verification commands

**After running, verify:**
```bash
# See all MCP tool failures
grep 'returned failure' logs/conversations/marcus_*.log

# See diagnostic pointers (request_next_task only)
grep 'Diagnostic Report' logs/conversations/marcus_*.log

# See actual diagnostic reports (WHY failures occurred)
grep -A 30 'Diagnostic Report (for operators)' logs/marcus_*.log
```

#### Manual Testing (Alternative)

If you prefer manual testing:

**Setup:**
```bash
# Start Marcus HTTP server
python -m src.marcus_mcp.server --http
```

**Trigger Failures:**

1. **No Tasks Available:**
   - Register agent: `register_agent(agent_id="test-1", ...)`
   - Request task when no project exists → returns `false`

2. **Agent Already Busy:**
   - Assign task to agent
   - Same agent calls `request_next_task` again → returns `false`

3. **All Tasks Assigned:**
   - Create project with 2 tasks
   - Assign both tasks to agents
   - Third agent calls `request_next_task` → returns `false`

**Verify Logs:**
```bash
# Monitor conversation logs (activity tracking)
tail -f logs/conversations/marcus_*.log | grep -A 5 "returned failure"

# Monitor Python logs (diagnostic reports)
tail -f logs/marcus_*.log | grep -A 20 "Diagnostic Report"
```

## What to Look For

### In Conversation Logs (`logs/conversations/marcus_*.log`)

**Success (DEBUG level):**
```json
{
  "event": "pm_thinking",
  "message": "MCP tool 'request_next_task' succeeded",
  "context": {
    "tool_name": "request_next_task",
    "arguments": {"agent_id": "agent_123"},
    "response": {"success": true, "task": {...}}
  }
}
```

**Failure (WARNING level):**
```json
{
  "event": "pm_logger",
  "level": "warning",
  "message": "MCP tool 'request_next_task' returned failure",
  "tool_name": "request_next_task",
  "arguments": {"agent_id": "agent_123"},
  "error": "No suitable tasks available",
  "retry_reason": "All tasks assigned or blocked",
  "response": {...}
}
```

**Diagnostic Pointer (for request_next_task only):**
```json
{
  "event": "pm_thinking",
  "message": "For root cause analysis of request_next_task failure, check Python logs (logs/marcus_*.log) for 'Diagnostic Report' entries near this timestamp",
  "context": {
    "hint": "Diagnostics run automatically when no tasks assignable"
  }
}
```

### In Python Logs (`logs/marcus_*.log`)

**Diagnostic Report (automatic):**
```
INFO - Diagnostic Report (for operators):
=== Task Assignment Diagnostics ===

Total Tasks: 5
TODO Tasks: 3
In Progress: 1
Completed: 1

Filtering Results:
- Started with: 3 TODO tasks
- After dependency filter: 0 tasks
- After skill filter: 0 tasks

Dependency Issues:
- Task "Implement API" blocked by incomplete "Setup Database"
- Task "Write Tests" blocked by incomplete "Implement API"

Recommendation: Review dependency chain for circular dependencies
```

## Verification Checklist

### ✅ Unit Tests Pass
```bash
pytest tests/unit/logging/test_mcp_tool_logger.py -v
# Expected: 14 passed
```

### ✅ Integration Tests Pass
```bash
pytest tests/integration/logging/test_mcp_tool_logger_integration.py -v
# Expected: 11 passed
```

### ✅ Log Files Created
```bash
ls -lh logs/conversations/marcus_*.log
ls -lh logs/marcus_*.log
```

### ✅ Failure Logging Works
1. Trigger a `request_next_task` failure
2. Check conversation logs for WARNING entry
3. Verify diagnostic pointer message appears
4. Check Python logs for "Diagnostic Report" near same timestamp

### ✅ No Categorization Assumptions
1. Create failure with dependency-related keywords
2. Verify log doesn't label it as "dependency_issue"
3. Verify log level stays at WARNING (not CRITICAL)
4. Verify no assumptions made about cause

## Common Testing Scenarios

### Scenario 1: All Tasks Assigned

**Setup:**
```python
# Project with 2 tasks, both assigned
```

**Expected Behavior:**
- `request_next_task` returns `{"success": False, "error": "No suitable tasks..."}`
- Logger creates WARNING entry with full response
- Diagnostic pointer added (for request_next_task)
- Python logs show diagnostic report explaining filtering

**Verify:**
```bash
grep "No suitable tasks" logs/conversations/marcus_*.log
grep "Diagnostic Report" logs/marcus_*.log
```

### Scenario 2: Dependencies Blocking

**Setup:**
```python
# Task A depends on Task B (incomplete)
# Agent requests Task A
```

**Expected Behavior:**
- `request_next_task` returns `{"success": False, ...}`
- Logger records WHAT failed, WHEN
- Does NOT assume it's dependency issue
- Python logs contain actual dependency analysis

**Verify:**
```bash
# Conversation log should NOT say "dependency_issue"
grep "dependency_issue" logs/conversations/marcus_*.log
# (should find nothing)

# Python log SHOULD have dependency analysis
grep "blocked by" logs/marcus_*.log
```

### Scenario 3: Other Tool Failures

**Setup:**
```python
# Call create_project with invalid config
```

**Expected Behavior:**
- Logger creates WARNING entry
- NO diagnostic pointer (only for request_next_task)
- Full response preserved for investigation

**Verify:**
```bash
grep "create_project.*returned failure" logs/conversations/marcus_*.log
# Should NOT contain "Diagnostic Report" reference
```

## Debugging Tips

### No Log Entries Created

**Check:**
```bash
# Verify conversation logger is configured
python -c "from src.logging.conversation_logger import conversation_logger; print(conversation_logger.log_dir)"

# Check log directory exists
ls -la logs/conversations/
```

### Missing Diagnostic Pointer

**Verify:**
- Tool name is exactly "request_next_task" (case-sensitive)
- Check `_log_mcp_tool_failure` in `src/logging/mcp_tool_logger.py:102-108`

### Incorrect Log Levels

**Verify:**
- Successes use `log_pm_thinking()` (DEBUG)
- Failures use `pm_logger.warning()` (WARNING)
- No CRITICAL level usage (categorization removed)

## Performance Testing

### Test High Volume

```python
import time
from src.logging.mcp_tool_logger import log_mcp_tool_response

start = time.time()
for i in range(1000):
    log_mcp_tool_response(
        tool_name="test_tool",
        arguments={"iteration": i},
        response={"success": False, "error": "Test"},
    )
elapsed = time.time() - start

print(f"Logged 1000 failures in {elapsed:.2f}s")
print(f"Average: {elapsed/1000*1000:.2f}ms per log")
```

**Expected:** < 1ms per log entry (structlog is async)

## Maintenance

### Adding New Tools

When adding new MCP tools, no changes needed! The logger automatically handles all tools via the centralized handler dispatch point (`src/marcus_mcp/handlers.py:1416-1420`).

### Changing Log Format

Update structured logging fields in `_log_mcp_tool_failure()`:
```python
context = {
    "tool_name": tool_name,
    "arguments": arguments,
    "error": error_msg,
    "retry_reason": retry_reason,
    "response": response,
    # Add new fields here
}
```

Update tests in:
- `tests/unit/logging/test_mcp_tool_logger.py`
- `tests/integration/logging/test_mcp_tool_logger_integration.py`

## References

- **Implementation:** `src/logging/mcp_tool_logger.py`
- **Integration Point:** `src/marcus_mcp/handlers.py:1416-1420`
- **Diagnostic System:** `src/core/task_diagnostics.py`
- **Unit Tests:** `tests/unit/logging/test_mcp_tool_logger.py`
- **Integration Tests:** `tests/integration/logging/test_mcp_tool_logger_integration.py`
