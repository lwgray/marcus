# MCP Tool Logging System

## Overview

The MCP Tool Logging System provides comprehensive activity tracking for all Marcus MCP (Model Context Protocol) tool operations. It acts as a "table of contents" for MCP tool activity, logging **WHAT failed** and **WHEN**, while pointing operators to detailed diagnostic logs for **WHY** root cause analysis.

This logging system is intentionally simplified to avoid making assumptions about failure causes, instead serving as an index that guides operators to the appropriate diagnostic systems for investigation.

## Purpose and Philosophy

### Design Principle: Activity Tracking, Not Diagnosis

The MCP tool logger follows a clear separation of concerns:

- **Activity Tracker (WHAT/WHEN):** Records that a tool was called and whether it succeeded or failed
- **Diagnostic Systems (WHY):** Provide detailed root cause analysis (e.g., `task_diagnostics.py`)

This separation is crucial because:
1. **MCP responses are intentionally vague** - They don't contain enough context to determine root cause
2. **Agents shouldn't overthink** - Detailed failure analysis in MCP responses causes agents to try alternative strategies instead of following instructions
3. **Diagnostics already exist** - Detailed analysis systems run automatically and log to Python logs

### Target Audience

- **Operators/Developers:** Need to investigate why tools fail to fix code or configuration issues
- **NOT Agents:** Agents receive simple retry instructions, not diagnostic details

## Architecture

### Integration Point

The logger integrates at the centralized MCP handler dispatch point:

```
┌─────────────────────────────────────────────────────────┐
│              MCP Server (src/marcus_mcp/)               │
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │  handlers.py::handle_tool_call()                  │ │
│  │  • Dispatches ALL MCP tool calls                  │ │
│  │  • Returns result to agent                        │ │
│  │  • Logs result via mcp_tool_logger ←────────────┐ │ │
│  └───────────────────────────────────────────────────┘ │ │
│                                                         │ │
│  Tool Functions:                                        │ │
│  • request_next_task()                                  │ │
│  • register_agent()                                     │ │
│  • create_project()                                     │ │
│  • [30+ other tools]                                    │ │
│                                                         │ │
└─────────────────────────────────────────────────────────┘
         │
         ├─── Agent receives simple response
         │    (success/failure + retry instructions)
         │
         └─── Logger captures activity
              │
              ├─── Conversation logs (logs/conversations/)
              │    • WARNING entries for failures
              │    • Full response context
              │    • Diagnostic pointers
              │
              └─── Python logs (logs/marcus_*.log)
                   • Detailed diagnostic reports
                   • Root cause analysis
                   • Automatic when needed
```

### Log Stream Architecture

Marcus uses multiple specialized log streams:

1. **Conversation Logs** (`logs/conversations/marcus_*.log`)
   - Structured JSON logs (structlog)
   - PM decisions, worker messages, MCP tool activity
   - **MCP tool logger writes here**

2. **Python Logs** (`logs/marcus_*.log`)
   - Traditional Python logging
   - Diagnostic reports from `task_diagnostics.py`
   - Dependency analysis, filtering statistics

3. **Agent Event Logs** (`logs/agent_events/*.jsonl`)
   - Lightweight event tracking (JSON Lines)
   - Agent lifecycle events
   - Used by visualization systems

The MCP tool logger bridges streams by recording activity in conversation logs and pointing to diagnostic details in Python logs.

## Implementation

### Core Module: `src/logging/mcp_tool_logger.py`

#### Main Function: `log_mcp_tool_response()`

```python
def log_mcp_tool_response(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """
    Log MCP tool response for activity tracking.

    Records WHAT failed and WHEN. Does not attempt to determine
    WHY failures occurred (root cause analysis is in diagnostic logs).
    """
    success = response.get("success", False)

    if success:
        # DEBUG level - low noise
        conversation_logger.log_pm_thinking(
            f"MCP tool '{tool_name}' succeeded",
            context={
                "tool_name": tool_name,
                "arguments": arguments,
                "response": response,
            },
        )
    else:
        # WARNING level - needs attention
        _log_mcp_tool_failure(tool_name, arguments, response)
```

**Key Design Decisions:**
- **Success = DEBUG level:** Low noise, only for detailed debugging
- **Failure = WARNING level:** Consistent level for all failures
- **No categorization:** Removed aggressive keyword-based classification
- **Full context:** Entire response preserved for investigation

#### Failure Logging: `_log_mcp_tool_failure()`

```python
def _log_mcp_tool_failure(
    tool_name: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    """Log MCP tool failure for activity tracking."""
    error_msg = response.get("error", "Unknown error")
    retry_reason = response.get("retry_reason", "")

    # Log at WARNING level (no categorization)
    conversation_logger.pm_logger.warning(
        f"MCP tool '{tool_name}' returned failure",
        tool_name=tool_name,
        arguments=arguments,
        error=error_msg,
        retry_reason=retry_reason,
        response=response,
    )

    # Special case: request_next_task gets diagnostic pointer
    if tool_name == "request_next_task":
        conversation_logger.log_pm_thinking(
            "For root cause analysis of request_next_task failure, "
            "check Python logs (logs/marcus_*.log) for 'Diagnostic Report' "
            "entries near this timestamp",
            context={"hint": "Diagnostics run automatically when no tasks assignable"},
        )
```

**Key Features:**
- **Consistent WARNING level:** No escalation to CRITICAL based on keywords
- **Diagnostic pointer:** Only for `request_next_task` (most critical tool)
- **No assumptions:** Logs error message as-is without interpretation
- **Full response preserved:** All fields included for operator investigation

### Integration: `src/marcus_mcp/handlers.py`

The logger integrates at the centralized handler dispatch point (line 1414-1420):

```python
# After tool execution
response = [types.TextContent(type="text", text=json.dumps(result, indent=2))]

# Log MCP tool response (especially failures) for diagnostics
if isinstance(result, dict):
    log_mcp_tool_response(
        tool_name=name,
        arguments=arguments,
        response=result,
    )
```

**Benefits of this integration point:**
- ✅ **Automatic coverage:** All 30+ MCP tools logged automatically
- ✅ **Centralized:** Single integration point, easy to maintain
- ✅ **Future-proof:** New tools automatically logged
- ✅ **Post-execution:** Logs actual results, not assumptions

## Logging Behavior

### Success Cases

**Log Entry (DEBUG level):**
```json
{
  "timestamp": "2025-01-15T10:30:45.123Z",
  "event": "pm_thinking",
  "message": "MCP tool 'request_next_task' succeeded",
  "context": {
    "tool_name": "request_next_task",
    "arguments": {"agent_id": "agent_001"},
    "response": {
      "success": true,
      "task": {
        "id": "task_123",
        "name": "Implement API endpoint",
        "description": "...",
        "status": "todo"
      }
    }
  }
}
```

### Failure Cases

#### request_next_task Failure

**Conversation Log (WARNING level):**
```json
{
  "timestamp": "2025-01-15T10:35:22.456Z",
  "level": "warning",
  "event": "pm_logger",
  "message": "MCP tool 'request_next_task' returned failure",
  "tool_name": "request_next_task",
  "arguments": {"agent_id": "agent_002"},
  "error": "No suitable tasks available",
  "retry_reason": "All tasks assigned or blocked",
  "response": {
    "success": false,
    "error": "No suitable tasks available",
    "retry_reason": "All tasks assigned or blocked",
    "retry_after_seconds": 30
  }
}
```

**Diagnostic Pointer (DEBUG level):**
```json
{
  "timestamp": "2025-01-15T10:35:22.457Z",
  "event": "pm_thinking",
  "message": "For root cause analysis of request_next_task failure, check Python logs (logs/marcus_*.log) for 'Diagnostic Report' entries near this timestamp",
  "context": {
    "hint": "Diagnostics run automatically when no tasks assignable"
  }
}
```

**Python Log (Automatic Diagnostic Report):**
```
2025-01-15 10:35:22,450 INFO - Diagnostic Report (for operators):
=== Task Assignment Diagnostics ===

Total Tasks: 5
TODO Tasks: 3
In Progress: 1
Completed: 1

Filtering Results:
- Started with: 3 TODO tasks
- After dependency filter: 0 tasks (blocked by incomplete dependencies)
- After skill filter: 0 tasks
- After assignment filter: 0 tasks

Dependency Chain Analysis:
- Task "Implement API" (task_456) blocked by incomplete "Setup Database" (task_123)
- Task "Write Tests" (task_789) blocked by incomplete "Implement API" (task_456)

Recommendation: Review dependency chain for potential circular dependencies
```

#### Other Tool Failures

**Conversation Log (WARNING level, NO diagnostic pointer):**
```json
{
  "timestamp": "2025-01-15T10:40:10.789Z",
  "level": "warning",
  "event": "pm_logger",
  "message": "MCP tool 'create_project' returned failure",
  "tool_name": "create_project",
  "arguments": {"name": "test-project", "description": "..."},
  "error": "Invalid project configuration",
  "retry_reason": "",
  "response": {
    "success": false,
    "error": "Invalid project configuration"
  }
}
```

Note: No diagnostic pointer for non-`request_next_task` tools.

## Relationship to Diagnostic Systems

### Separation of Concerns

The MCP tool logger is **NOT** a diagnostic system. It is an activity tracker that points to diagnostic systems:

| Aspect | MCP Tool Logger | Diagnostic Systems |
|--------|----------------|-------------------|
| **Purpose** | Activity tracking | Root cause analysis |
| **Answers** | WHAT failed, WHEN | WHY it failed |
| **Location** | `src/logging/mcp_tool_logger.py` | `src/core/task_diagnostics.py` |
| **Log Stream** | Conversation logs | Python logs |
| **Trigger** | Every MCP tool call | Automatic when failures occur |
| **Assumptions** | None | Deep analysis |
| **Audience** | Quick overview | Detailed investigation |

### Diagnostic System: `task_diagnostics.py`

When `request_next_task` cannot find suitable tasks, it automatically runs diagnostics:

```python
# From src/marcus_mcp/tools/task.py (lines 946-989)
if todo_tasks:
    # Tasks exist but can't be assigned - run diagnostics
    logger.warning(f"No tasks assignable but {len(todo_tasks)} TODO tasks exist")

    diagnostic_report = await run_automatic_diagnostics(
        project_tasks=state.project_tasks,
        completed_task_ids=completed_task_ids,
        assigned_task_ids=assigned_task_ids,
    )

    # Format and log for operators
    formatted_report = format_diagnostic_report(diagnostic_report)
    logger.info(f"Diagnostic Report (for operators):\n{formatted_report}")
```

**What Diagnostics Provide:**
- Dependency chain analysis (blocking tasks)
- Task filtering statistics (why tasks were excluded)
- Skill mismatch detection
- Circular dependency detection
- Recommended actions

**Why Separate:**
- Diagnostics run automatically when needed
- Detailed analysis logged to Python logs
- MCP responses stay simple for agents
- Operators get full context in separate stream

## Why Categorization Was Removed

### Original Design (Removed)

The initial implementation attempted to categorize failures:

```python
# REMOVED: Aggressive categorization
def _categorize_failure(response: dict[str, Any]) -> str:
    """Categorize based on keywords."""
    error_msg = response.get("error", "").lower()

    if "dependency" in error_msg or "blocked by" in error_msg:
        return "dependency_issue"  # Assumption!
    if "busy" in error_msg:
        return "agent_busy"
    if "no suitable" in error_msg:
        return "no_suitable_tasks"
    return "unknown"
```

### Problems Discovered

1. **MCP responses lack context:**
   ```python
   # Response says:
   {"error": "No suitable tasks available"}

   # But WHY? Could be:
   # - All tasks assigned
   # - Dependencies blocking
   # - Skill mismatch
   # - Tasks filtered by other criteria
   # - Circular dependencies

   # We can't tell from the response!
   ```

2. **Keyword matching is unreliable:**
   - "Task waiting for dependencies" → Labeled as dependency issue
   - But diagnostic might show: "Actually all tasks are assigned"
   - Keyword doesn't equal root cause

3. **Decision happens elsewhere:**
   ```python
   # From src/core/ai_powered_task_assignment.py
   unblocked_tasks = await self._filter_unblocked_tasks(...)
   if not unblocked_tasks:
       logger.info("No unblocked tasks available")  # Logs here
       return None  # But doesn't pass info back!
   ```

   The filtering logic knows WHY but doesn't include it in the MCP response.

4. **Diagnostics already exist:**
   - `run_automatic_diagnostics()` provides accurate analysis
   - Runs automatically when needed
   - No need to guess from keywords

### Simplified Design (Current)

```python
# CURRENT: No categorization, just facts
def _log_mcp_tool_failure(...):
    """Log the failure as-is, no assumptions."""
    conversation_logger.pm_logger.warning(
        f"MCP tool '{tool_name}' returned failure",
        error=error_msg,  # Log what we know
        # NO failure_category field
    )

    # Point to real diagnostics
    if tool_name == "request_next_task":
        log_pm_thinking("Check Python logs for 'Diagnostic Report'...")
```

**Benefits:**
- ✅ No false assumptions
- ✅ Clear separation: activity tracking vs. diagnostics
- ✅ Points to accurate analysis
- ✅ Simpler, more maintainable

## Usage Patterns

### For Operators

**When investigating MCP tool failures:**

1. **Check conversation logs** for activity overview:
   ```bash
   grep 'returned failure' logs/conversations/marcus_*.log | tail -20
   ```

2. **For request_next_task failures,** check Python logs for diagnostics:
   ```bash
   grep -A 30 'Diagnostic Report' logs/marcus_*.log | tail -50
   ```

3. **Filter by tool:**
   ```bash
   grep 'create_project.*returned failure' logs/conversations/marcus_*.log
   ```

4. **Time-based investigation:**
   ```bash
   # Find failures around 10:35 AM
   grep '10:35:' logs/conversations/marcus_*.log | grep 'returned failure'
   ```

### For Developers

**Adding new MCP tools:**

No changes needed! The logger automatically handles all tools via the centralized dispatch point.

**Changing log format:**

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

**Adding diagnostic pointers for other tools:**

```python
# In _log_mcp_tool_failure()
if tool_name in ["request_next_task", "your_new_tool"]:
    conversation_logger.log_pm_thinking(
        "Check diagnostics at location X...",
        context={"hint": "..."}
    )
```

## Testing

The MCP tool logger has comprehensive test coverage across three levels:

### 1. Unit Tests (14 tests)

**Location:** `tests/unit/logging/test_mcp_tool_logger.py`

**Run:**
```bash
pytest tests/unit/logging/test_mcp_tool_logger.py -v
```

**Coverage:**
- Success/failure logging
- Log levels (DEBUG/WARNING)
- Diagnostic pointers
- Integration with conversation logger
- Activity tracking behavior (WHAT/WHEN, not WHY)
- No categorization assumptions

### 2. Integration Tests (11 tests)

**Location:** `tests/integration/logging/test_mcp_tool_logger_integration.py`

**Run:**
```bash
pytest tests/integration/logging/test_mcp_tool_logger_integration.py -v
```

**Coverage:**
- Real-world failure scenarios
- Log entry creation with real logger
- Structured logging format
- End-to-end convenience functions

### 3. Live System Testing

**Location:** `dev-tools/examples/test_mcp_logger_live.py`

**Run:**
```bash
# Terminal 1: Start Marcus
python -m src.marcus_mcp.server --http

# Terminal 2: Run live test
python dev-tools/examples/test_mcp_logger_live.py
```

**Tests 4 scenarios:**
1. No tasks available
2. Agent already busy
3. All tasks assigned
4. Other tool failures

**Verification:**
```bash
# Activity tracking
grep 'returned failure' logs/conversations/marcus_*.log

# Diagnostic reports
grep -A 30 'Diagnostic Report' logs/marcus_*.log
```

For complete testing guide, see: `docs/testing/MCP_TOOL_LOGGER_TESTING.md`

## Performance Characteristics

### Low Overhead Design

- **Async-friendly:** Uses structlog's async logging
- **Minimal processing:** No complex categorization logic
- **Conditional logging:** DEBUG logs only if enabled
- **Efficient serialization:** JSON serialization by structlog

### Performance Metrics

```python
# Measured performance (1000 log entries)
Average: 0.8ms per log entry
Total overhead: <1% of MCP tool execution time
```

**Why it's fast:**
- Single log write per tool call
- No synchronous I/O blocking
- No expensive analysis or categorization
- Structlog handles async buffering

## Monitoring and Maintenance

### Health Indicators

**Healthy System:**
```bash
# Mostly successes, few failures
grep 'MCP tool' logs/conversations/marcus_*.log | \
    grep -c 'succeeded'
# Example output: 245

grep 'returned failure' logs/conversations/marcus_*.log | wc -l
# Example output: 12
```

**Problem Indicators:**
```bash
# High failure rate for specific tool
grep 'request_next_task.*returned failure' logs/conversations/marcus_*.log | wc -l
# If consistently high: investigate diagnostics

# Unexpected tool failures
grep 'create_project.*returned failure' logs/conversations/marcus_*.log
# If frequent: check project configuration
```

### Log Rotation

Conversation logs use automatic rotation (via structlog configuration):
- Daily rotation
- Compression after 7 days
- Retention: 30 days

**Configuration:** `src/logging/conversation_logger.py`

### Troubleshooting

**No log entries created:**
```bash
# Check logger initialization
python -c "from src.logging.mcp_tool_logger import log_mcp_tool_response; print('OK')"

# Check log directory
ls -la logs/conversations/
```

**Missing diagnostic pointers:**
- Verify tool name is exactly `"request_next_task"` (case-sensitive)
- Check `_log_mcp_tool_failure()` logic at line 102-108

**Wrong log levels:**
- Verify conversation logger configuration
- Check structlog setup in `conversation_logger.py`

## Comparison to Other Monitoring Systems

### vs. Assignment Monitor

| Aspect | MCP Tool Logger | Assignment Monitor |
|--------|----------------|-------------------|
| **Scope** | All MCP tool calls | Task assignments only |
| **Trigger** | Every tool call | Assignment state changes |
| **Purpose** | Activity tracking | Detect assignment reversions |
| **Log Type** | Structured JSON | Specialized alerts |
| **File** | `mcp_tool_logger.py` | `assignment_monitor.py` |

### vs. Error Predictor

| Aspect | MCP Tool Logger | Error Predictor |
|--------|----------------|-----------------|
| **Scope** | Historical activity | Predictive analysis |
| **Timing** | Real-time (during execution) | Proactive (before execution) |
| **Purpose** | Record what happened | Predict what might happen |
| **Method** | Logging | AI pattern analysis |
| **File** | `mcp_tool_logger.py` | `error_predictor.py` |

### vs. Task Diagnostics

| Aspect | MCP Tool Logger | Task Diagnostics |
|--------|----------------|------------------|
| **Scope** | All tools | Task assignment only |
| **Depth** | Activity tracking | Deep analysis |
| **Answers** | WHAT/WHEN | WHY |
| **Trigger** | Every call | Automatic on failures |
| **Log Stream** | Conversation logs | Python logs |
| **File** | `mcp_tool_logger.py` | `task_diagnostics.py` |

**Complementary Design:** These systems work together, each serving a specific purpose.

## Related Documentation

### Implementation
- **Core Module:** `src/logging/mcp_tool_logger.py`
- **Integration:** `src/marcus_mcp/handlers.py` (lines 1414-1420)
- **Diagnostics:** `src/core/task_diagnostics.py`

### Testing
- **Unit Tests:** `tests/unit/logging/test_mcp_tool_logger.py`
- **Integration Tests:** `tests/integration/logging/test_mcp_tool_logger_integration.py`
- **Live Test Script:** `dev-tools/examples/test_mcp_logger_live.py`
- **Testing Guide:** `docs/testing/MCP_TOOL_LOGGER_TESTING.md`

### Related Systems
- **Monitoring Systems:** See `11-monitoring-systems.md`
- **Assignment Monitor:** See `41-assignment-monitor.md`
- **Detection Systems:** See `29-detection-systems.md`

## Future Enhancements

### Potential Improvements

1. **Metrics Collection:**
   - Tool success/failure rates
   - Average response times
   - Most common failure patterns
   - Export to dashboard

2. **Enhanced Diagnostic Linking:**
   - Include diagnostic report IDs in logs
   - Direct links between activity and diagnostics
   - Correlation IDs across log streams

3. **Alert Integration:**
   - Trigger alerts on sustained high failure rates
   - Integrate with monitoring dashboards
   - Webhook notifications for critical tools

4. **Structured Metrics:**
   - Prometheus/OpenTelemetry integration
   - Real-time dashboards
   - Trend analysis

### Non-Goals

- ❌ Root cause analysis (handled by diagnostics)
- ❌ Failure categorization (unreliable from MCP responses)
- ❌ Predictive analysis (handled by error predictor)
- ❌ Assignment tracking (handled by assignment monitor)

The MCP tool logger maintains its focused role as an activity tracker, leaving specialized analysis to purpose-built systems.
