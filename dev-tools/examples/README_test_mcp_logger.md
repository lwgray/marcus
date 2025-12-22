# MCP Tool Logger Live Test

Quick guide to testing the MCP tool logger with a real Marcus instance.

## Quick Start

```bash
# Terminal 1: Start Marcus server
python -m src.marcus_mcp.server --http

# Terminal 2: Run live test
python dev-tools/examples/test_mcp_logger_live.py
```

## What Gets Tested

### ✅ Test 1: No Tasks Available
- Registers agent when no tasks exist
- Agent requests task → fails
- **Verifies:** WARNING log + diagnostic pointer

### ✅ Test 2: Agent Already Busy
- Agent requests task twice
- Second request → fails with "already have a task"
- **Verifies:** WARNING log with correct error

### ✅ Test 3: All Tasks Assigned
- Multiple agents request tasks
- Eventually one fails when all assigned
- **Verifies:** WARNING log + diagnostic report

### ✅ Test 4: Other Tool Failure
- Calls non-request_next_task tool with invalid args
- Tool fails
- **Verifies:** WARNING log WITHOUT diagnostic pointer

## Verification Commands

After running the test, check logs:

```bash
# See all MCP tool failures (activity tracking)
grep 'returned failure' logs/conversations/marcus_*.log

# See diagnostic pointers (request_next_task only)
grep 'Diagnostic Report' logs/conversations/marcus_*.log

# See actual diagnostic reports (root cause analysis)
grep -A 30 'Diagnostic Report (for operators)' logs/marcus_*.log

# Verify NO categorization assumptions
grep 'failure_category' logs/conversations/marcus_*.log  # Should be empty
grep 'dependency_issue' logs/conversations/marcus_*.log  # Should be empty
```

## Expected Log Output

### Conversation Log (`logs/conversations/marcus_*.log`)

**For request_next_task failure:**
```json
{
  "level": "warning",
  "event": "pm_logger",
  "message": "MCP tool 'request_next_task' returned failure",
  "tool_name": "request_next_task",
  "arguments": {"agent_id": "test-agent-001"},
  "error": "No suitable tasks available",
  "retry_reason": "All tasks assigned or blocked",
  "response": {...}
}

{
  "event": "pm_thinking",
  "message": "For root cause analysis of request_next_task failure, check Python logs (logs/marcus_*.log) for 'Diagnostic Report' entries near this timestamp"
}
```

**For other tool failures:**
```json
{
  "level": "warning",
  "message": "MCP tool 'get_project_status' returned failure",
  "tool_name": "get_project_status",
  "error": "Project not found"
}
// Note: NO diagnostic pointer for non-request_next_task tools
```

### Python Log (`logs/marcus_*.log`)

**Diagnostic Report (automatic when no tasks assignable):**
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

## What NOT to See

❌ **No categorization labels:**
- No `failure_category` field
- No `dependency_issue` labels
- No CRITICAL log level for "dependency issues"

❌ **No assumptions about cause:**
- Logger records WHAT failed, not WHY
- WHY is in diagnostic reports (Python logs)

## Troubleshooting

### Server Not Running
```
❌ Error: Connection refused

Solution: Start server with:
python -m src.marcus_mcp.server --http
```

### No Failures Logged
```
⚠️  All tests succeeded - no failures to log

Solution: This can happen if:
- Server has tasks available
- Try clearing projects: list_projects() → delete each
- Restart server to clear state
```

### Can't Find Logs
```
Check these locations:
- logs/conversations/marcus_*.log (conversation logs)
- logs/marcus_*.log (Python logs)

If missing, check:
- MARCUS_LOG_DIR environment variable
- config_marcus.json logging configuration
```

## Related Files

- **Test Script:** `dev-tools/examples/test_mcp_logger_live.py`
- **Implementation:** `src/logging/mcp_tool_logger.py`
- **Integration Point:** `src/marcus_mcp/handlers.py:1416-1420`
- **Diagnostics:** `src/core/task_diagnostics.py`
- **Full Guide:** `docs/testing/MCP_TOOL_LOGGER_TESTING.md`

## Quick Test (Inline)

If server is already running, test quickly:

```bash
python -c "
import sys
sys.path.insert(0, '.')
from src.logging.mcp_tool_logger import log_mcp_tool_response

# Simulate failure
log_mcp_tool_response(
    tool_name='request_next_task',
    arguments={'agent_id': 'quick-test'},
    response={
        'success': False,
        'error': 'No suitable tasks',
        'retry_reason': 'Testing logger'
    }
)

print('✅ Log entry created')
print('Check: logs/conversations/marcus_*.log')
"
```
