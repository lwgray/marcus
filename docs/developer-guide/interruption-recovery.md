# Interruption Recovery in Marcus MCP

## Overview

Marcus MCP now includes robust interruption recovery mechanisms to handle scenarios where connections are interrupted, particularly during `request_next_task` operations. This guide explains the recovery features and how to use them.

## Problem Addressed

Previously, when Marcus was interrupted during a task request:
- The `tasks_being_assigned` set would retain task IDs that were never cleaned up
- The connection would die and couldn't be reinitiated without restarting Marcus
- Agents would get stuck waiting for responses that never arrived

## Recovery Mechanisms

### 1. Signal Handlers (Server-Side)

Marcus now handles SIGINT (Ctrl+C) and SIGTERM signals gracefully:

```python
# Automatic cleanup on shutdown
- Clears pending task assignments
- Cancels active operations
- Closes log files properly
- Persists final state
```

### 2. Connection State Tracking

The server tracks active operations and cleans them up on disconnect:

```python
# Operations are tracked with identifiers
state._active_operations.add(f"task_assignment_{task_id}")

# Cleaned up automatically on interruption
```

### 3. Client-Side Retry Logic

The worker client implements exponential backoff retry:

```python
@retry_with_backoff(max_attempts=3, initial_delay=2.0)
async def request_next_task(self, agent_id: str) -> Dict[str, Any]:
    # Automatically retries on connection failures
```

Features:
- Exponential backoff with jitter
- Configurable retry attempts
- Automatic reconnection capability

### 4. Enhanced Ping Tool

The ping tool now supports health checks and manual cleanup:

```bash
# Check system health
ping marcus "health"

# Force cleanup of stuck assignments
ping marcus "cleanup"

# Complete reset (use with caution!)
ping marcus "reset"
```

## Usage Examples

### Handling Interruptions

1. **During Normal Operation**: Just press Ctrl+C - Marcus will clean up gracefully
   ```
   ⚠️  Received signal 2, initiating graceful shutdown...
   🧹 Cleaning up active operations...
     Clearing 2 pending task assignments
   ✅ Cleanup completed
   ```

2. **Recovery After Crash**: Use the ping tool to clean up
   ```python
   # From your agent code
   result = await client.session.call_tool("ping", arguments={"echo": "cleanup"})
   ```

3. **Check System Health**:
   ```python
   result = await client.session.call_tool("ping", arguments={"echo": "health"})
   # Returns detailed health information including stuck assignments
   ```

### Client-Side Recovery

The worker client automatically retries failed operations:

```python
# This will retry up to 3 times with exponential backoff
try:
    task = await client.request_next_task("agent-id")
except Exception as e:
    print(f"Failed after retries: {e}")
```

### Manual State Cleanup

If automatic recovery fails, you can manually clean up:

```python
# Connect to Marcus
async with client.connect_to_marcus() as session:
    # Force cleanup
    await session.call_tool("ping", arguments={"echo": "cleanup"})

    # Now safe to continue operations
    await client.request_next_task("agent-id")
```

## Best Practices

1. **Always Use Context Managers**: Ensures proper cleanup
   ```python
   async with client.connect_to_marcus() as session:
       # Your operations here
   ```

2. **Handle Connection Failures Gracefully**: The retry logic will handle transient failures
   ```python
   try:
       result = await client.request_next_task("agent-id")
   except Exception as e:
       # Log and handle appropriately
       logger.error(f"Task request failed: {e}")
   ```

3. **Monitor System Health**: Periodically check health during long-running operations
   ```python
   # Check health every 10 tasks
   if task_count % 10 == 0:
       health = await session.call_tool("ping", arguments={"echo": "health"})
   ```

4. **Use Cleanup Sparingly**: The cleanup command should only be used when necessary
   - After a crash or unexpected termination
   - When health check shows stuck assignments
   - Before starting a fresh agent session

## Troubleshooting

### Connection Won't Restore

1. Check if Marcus is still running: `ps aux | grep marcus`
2. Use ping cleanup: `ping marcus "cleanup"`
3. If still stuck, restart Marcus server

### Tasks Getting Stuck

1. Check health: `ping marcus "health"`
2. Look for tasks in `tasks_being_assigned`
3. Run cleanup: `ping marcus "cleanup"`

### Repeated Connection Failures

1. Check Marcus logs for errors
2. Verify network connectivity
3. Ensure Marcus server is healthy
4. Consider increasing retry delays in client

## Technical Details

### State Cleanup Order

1. Signal received → `_cleanup_on_shutdown()` called
2. Clear `tasks_being_assigned` set
3. Cancel active asyncio operations
4. Stop assignment monitor
5. Close log files
6. Persist final state
7. Force exit

### Retry Configuration

Default retry settings:
- Max attempts: 3
- Initial delay: 1-2 seconds (varies by operation)
- Max delay: 30-60 seconds
- Exponential base: 2.0
- Jitter: Enabled (adds 0-50% random variation)

### Health Information

The health check returns:
- `tasks_being_assigned`: List of task IDs currently being assigned
- `active_agents`: Number of registered agents
- `assigned_tasks`: Number of actively assigned tasks
- `shutdown_pending`: Whether shutdown has been initiated
- `active_operations`: Number of tracked operations
- `assignment_system`: Detailed assignment system health
