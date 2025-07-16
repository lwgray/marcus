# Issue: MCP Server Not Using Marcus Logging Infrastructure

## Problem Description

The MCP (Model Context Protocol) server is not utilizing the comprehensive Marcus logging system, resulting in:
- Loss of valuable debugging information
- No structured conversation tracking for MCP interactions
- Missing performance metrics and decision rationale
- Incomplete audit trail for system evaluation

Currently, the MCP server only writes basic events to `realtime_*.jsonl` files, missing the rich context and analysis capabilities of our ConversationLogger and Agent Events systems.

## Current State

### What's Working
- Basic event logging to realtime logs via `log_event()`
- Pipeline visualization events for create_project
- Minimal request/response tracking

### What's Missing
- Structured conversation logging with proper categorization
- Decision tracking with rationale and confidence scores
- Performance metrics for tool operations
- Integration with visualization pipeline
- Proper error context and recovery tracking

## Impact

This affects:
1. **Debugging**: Hard to trace issues through MCP interactions
2. **Performance Analysis**: No metrics on tool execution times
3. **Quality Assurance**: Can't evaluate decision-making patterns
4. **Agent Development**: Missing data for agent behavior analysis
5. **System Monitoring**: Incomplete picture of system health

## Proposed Solution

Integrate the existing Marcus logging infrastructure into the MCP server following the patterns documented in `/docs/systems/02-logging-system.md`.

### High-Level Changes

1. Initialize ConversationLogger in MCP server
2. Create MCPLoggingIntegration wrapper class
3. Log all tool requests/responses as conversations
4. Track decisions with rationale for major operations
5. Capture performance metrics
6. Ensure agent events feed visualization pipeline

### Implementation Guide

A detailed implementation guide has been created at `/issues/extend_logging.md` for the engineer assigned to this task.

## Acceptance Criteria

- [ ] ConversationLogger initialized and configured in MCP server
- [ ] All MCP tool calls logged with:
  - [ ] Request details (tool name, arguments, client ID)
  - [ ] Processing steps (internal thinking)
  - [ ] Response details (success/failure, results, errors)
- [ ] Decision logging for:
  - [ ] create_project (with rationale for task generation)
  - [ ] request_next_task (with assignment reasoning)
  - [ ] report_blocker (with resolution strategy)
- [ ] Performance metrics captured:
  - [ ] Tool execution duration
  - [ ] Task creation counts
  - [ ] System resource usage
- [ ] Agent events properly formatted for visualization
- [ ] No stdout pollution (MCP protocol integrity maintained)
- [ ] Error scenarios properly logged without breaking operations
- [ ] Unit and integration tests for logging integration

## Technical Considerations

1. **Async Operations**: Logging should not block MCP responses
2. **Protocol Integrity**: No print statements to stdout
3. **Error Resilience**: Logging failures shouldn't break tools
4. **Performance**: Minimal overhead on tool execution
5. **Storage**: Proper log rotation to manage disk usage

## Testing Plan

1. **Unit Tests**: Mock logging and verify correct calls
2. **Integration Tests**: Full MCP server with logging enabled
3. **Performance Tests**: Measure logging overhead
4. **Manual Testing**: Use Claude/MCP client to verify logs
5. **Visualization Testing**: Confirm events appear in UI

## Dependencies

- Existing ConversationLogger (`src/logging/conversation_logger.py`)
- Agent Events logger (`src/logging/agent_events.py`)
- No new external dependencies required

## Estimated Effort

- Implementation: 2-3 days
- Testing: 1 day
- Documentation updates: 0.5 days
- Total: ~4 days

## Priority

**High** - This is critical for:
- Debugging the recent MCP response hanging issues
- Understanding agent behavior patterns
- Evaluating system performance
- Supporting future AI training on decision data

## Related Issues

- #[previous issue number] - MCP Response Hanging (root cause analysis needed better logging)
- #[future issue] - Agent Decision Analysis Dashboard (requires this logging data)

## Additional Context

Recent debugging of MCP response hanging issues highlighted the lack of proper logging. We added ad-hoc debug statements but need a systematic approach using our existing infrastructure.

Example of what we're missing:
```json
{
  "timestamp": "2024-01-15T10:30:45.123Z",
  "conversation_type": "worker_to_pm",
  "participant_id": "claude-mcp-client",
  "message": "create_project request",
  "metadata": {
    "tool": "create_project",
    "project_name": "Todo App",
    "complexity": "prototype",
    "estimated_tasks": 15
  },
  "decision": {
    "action": "approve_project_creation",
    "rationale": "Valid project scope with clear requirements",
    "confidence": 0.92,
    "alternatives_considered": []
  },
  "performance": {
    "duration_ms": 15234,
    "tasks_created": 15,
    "ai_tokens_used": 1847
  }
}
```

## Labels

- `enhancement`
- `logging`
- `mcp-server`
- `high-priority`
- `good-first-issue` (with the detailed guide)
