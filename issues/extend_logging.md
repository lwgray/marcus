# Extending Marcus Logging to MCP Server

## Overview

Welcome to the team! This document outlines how to properly integrate the Marcus logging system into the MCP (Model Context Protocol) server. Currently, the MCP server is not utilizing our comprehensive logging infrastructure, which means we're missing valuable data for debugging, performance analysis, and system evaluation.

## Background

Marcus has two primary logging systems:
1. **ConversationLogger** - A structured logging system for tracking all conversations and decisions
2. **Agent Events Logger** - A lightweight event logger for visualization

The MCP server currently only writes to basic realtime logs (`logs/conversations/realtime_*.jsonl`), missing the rich context and structure our logging system provides.

## Your Task

Integrate the existing logging infrastructure into the MCP server to capture all tool interactions, decisions, and system events according to the Marcus logging patterns.

## Implementation Steps

### Step 1: Initialize Logging in MCP Server

In `src/marcus_mcp/server.py`, add the ConversationLogger initialization:

```python
# Add imports at the top
from src.logging.conversation_logger import ConversationLogger
from src.logging.agent_events import log_agent_event

# In MarcusServer.__init__, after line 88 (realtime_log creation):
# Initialize conversation logger
self.conversation_logger = ConversationLogger(
    log_dir=log_dir / "structured",
    max_bytes=10 * 1024 * 1024,  # 10MB per file
    backup_count=10
)
```

### Step 2: Create MCP-Specific Logging Wrapper

Create a new file `src/marcus_mcp/logging_integration.py`:

```python
"""
MCP Server Logging Integration

Provides structured logging for MCP tool calls following Marcus patterns.
"""

from typing import Any, Dict, Optional
from datetime import datetime
from src.logging.conversation_logger import ConversationLogger, ConversationType
from src.logging.agent_events import log_agent_event, log_thinking


class MCPLoggingIntegration:
    """Integrates MCP server operations with Marcus logging system."""

    def __init__(self, conversation_logger: ConversationLogger):
        self.logger = conversation_logger

    def log_tool_request(self, tool_name: str, arguments: Dict[str, Any],
                        client_id: str = "mcp_client") -> None:
        """Log incoming tool request from MCP client."""
        # Log as worker-to-pm communication
        self.logger.log_worker_message(
            worker_id=client_id,
            direction="to_pm",
            message=f"Tool request: {tool_name}",
            metadata={
                "tool": tool_name,
                "arguments": arguments,
                "timestamp": datetime.now().isoformat()
            }
        )

        # Log event for visualization
        log_agent_event("mcp_tool_request", {
            "tool": tool_name,
            "client": client_id,
            "has_arguments": bool(arguments)
        })

    def log_tool_processing(self, tool_name: str, processing_step: str,
                           details: Optional[Dict[str, Any]] = None) -> None:
        """Log internal processing steps."""
        log_thinking(
            agent="marcus",
            thought=f"Processing {tool_name}: {processing_step}",
            context=details or {}
        )

    def log_tool_response(self, tool_name: str, success: bool,
                         result: Optional[Dict[str, Any]] = None,
                         error: Optional[str] = None,
                         client_id: str = "mcp_client") -> None:
        """Log tool response being sent back to client."""
        # Log response
        self.logger.log_worker_message(
            worker_id=client_id,
            direction="from_pm",
            message=f"Tool response: {tool_name} - {'success' if success else 'failed'}",
            metadata={
                "tool": tool_name,
                "success": success,
                "has_result": result is not None,
                "error": error
            }
        )

        # Log completion event
        log_agent_event("mcp_tool_complete", {
            "tool": tool_name,
            "success": success,
            "duration_ms": None  # Will be calculated from request timestamp
        })
```

### Step 3: Integrate Logging into Tool Handlers

Modify `src/marcus_mcp/handlers.py` to use the logging integration:

```python
# In handle_tool_call function, add at the beginning:
if hasattr(state, 'mcp_logger'):
    state.mcp_logger.log_tool_request(name, arguments)

# Before each tool execution:
if hasattr(state, 'mcp_logger'):
    state.mcp_logger.log_tool_processing(name, "validating_arguments")

# After successful execution:
if hasattr(state, 'mcp_logger'):
    state.mcp_logger.log_tool_response(name, True, result)

# In exception handler:
if hasattr(state, 'mcp_logger'):
    state.mcp_logger.log_tool_response(name, False, error=str(e))
```

### Step 4: Add Specific Logging for Key Tools

For `create_project` in `src/marcus_mcp/tools/nlp.py`:

```python
# Log project creation decision
if hasattr(state, 'conversation_logger'):
    state.conversation_logger.log_pm_decision(
        decision=f"Create project: {project_name}",
        rationale=f"Natural language request with {len(description)} char description",
        confidence_score=0.95,
        decision_factors={
            "complexity": options.get("complexity", "standard"),
            "deployment": options.get("deployment", "none"),
            "description_length": len(description)
        }
    )

# Log task creation progress
if hasattr(state, 'conversation_logger'):
    state.conversation_logger.log_kanban_interaction(
        action="create_tasks",
        direction="to_kanban",
        data={
            "project_name": project_name,
            "task_count": len(tasks),
            "total_estimated_hours": sum(t.estimated_hours for t in tasks)
        }
    )
```

### Step 5: Add Performance Metrics Logging

For operations that take significant time (like create_project):

```python
# At start of operation:
start_time = datetime.now()

# At end of operation:
duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

if hasattr(state, 'conversation_logger'):
    state.conversation_logger.log_system_state(
        active_workers=len(state.agent_status),
        tasks_in_progress=len([t for t in state.agent_tasks.values() if t.status == "in_progress"]),
        tasks_completed=result.get("tasks_created", 0),
        tasks_blocked=0,
        system_metrics={
            "operation": "create_project",
            "duration_ms": duration_ms,
            "tasks_created": result.get("tasks_created", 0)
        }
    )
```

### Step 6: Clean Up Existing Debug Logs

Remove or convert the ad-hoc logging statements we added:
- Remove direct `state.log_event()` calls that duplicate structured logging
- Keep only essential realtime logs for backward compatibility
- Ensure no print statements remain that could corrupt MCP protocol

## Testing Your Implementation

1. **Unit Tests**: Create tests in `tests/unit/marcus_mcp/test_logging_integration.py`
2. **Integration Tests**: Test with actual MCP client in `tests/integration/`
3. **Manual Testing**:
   - Start MCP server
   - Use Claude or another MCP client to call tools
   - Verify logs appear in `logs/conversations/structured/`
   - Check visualization pipeline receives events

## Validation Checklist

- [ ] ConversationLogger properly initialized in MCP server
- [ ] All tool requests/responses logged with proper conversation types
- [ ] Decision logging implemented for key operations
- [ ] Performance metrics captured for slow operations
- [ ] Agent events logged for visualization
- [ ] No print statements to stdout (MCP protocol corruption)
- [ ] Error handling logs failures without breaking operations
- [ ] Log files properly rotated and organized

## Expected Outcomes

After implementation, you should see:

1. **Structured conversation logs** in `logs/conversations/structured/conversations_*.jsonl`
2. **Decision logs** with rationale for all major operations
3. **Agent event logs** feeding the visualization pipeline
4. **Performance metrics** for all tool operations
5. **Complete audit trail** of all MCP interactions

## Common Pitfalls to Avoid

1. **Don't log to stdout** - This corrupts MCP protocol
2. **Don't block on logging** - Use async where possible
3. **Don't lose context** - Ensure client_id/agent_id is tracked
4. **Don't skip error logging** - Failures are important data
5. **Don't forget metadata** - Rich context enables analysis

## Questions?

If you have questions about:
- The logging system architecture → See `/docs/systems/02-logging-system.md`
- ConversationLogger API → Check docstrings in `src/logging/conversation_logger.py`
- MCP protocol → Review MCP library documentation
- Marcus architecture → See `/docs/systems/` directory

Good luck! This enhancement will significantly improve our ability to debug issues, analyze performance, and understand system behavior.
