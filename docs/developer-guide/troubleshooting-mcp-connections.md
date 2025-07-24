# Troubleshooting MCP Connection Issues

## Problem: Claude Code Loses MCP Connection After Interruption

When interrupting Claude Code during an MCP call, the connection to Marcus can be permanently lost, requiring a restart of Claude Code.

## Root Cause

The issue stems from how MCP stdio connections work:

1. **No Session IDs**: MCP connections don't have session identifiers - they're just stdio pipes
2. **Process-Based**: Communication happens through stdin/stdout of a subprocess
3. **No Reconnection Protocol**: Once pipes are broken, there's no way to reconnect to the same process

When you interrupt Claude during an MCP operation:
- The stdio pipes (file descriptors) get severed
- Claude still references the old, broken pipes
- Marcus server process might still be running but unreachable
- Claude can't establish a new connection because it's still trying to use the old pipes

## Technical Details

```
Initial Connection:
Claude → spawns → Marcus subprocess (PID 12345)
     ↓                    ↓
Creates pipes:      stdin/stdout
fd:3 (write)  ←→   fd:0 (read)
fd:4 (read)   ←→   fd:1 (write)

After Interruption:
Claude → broken pipes → Marcus (still running)
fd:3 ❌              PID 12345
fd:4 ❌              (orphaned)

Claude tries to reconnect:
Still using fd:3,4 → Error: Broken pipe
```

## Workarounds

### 1. Avoid Interrupting During MCP Calls
- Wait for operations to complete
- Look for the spinner indicator

### 2. Increase Cleanup Timeouts
We've increased the cleanup timeout from 0.5s to 5.0s in `nlp_tools.py` to reduce the chance of leaving connections in a bad state.

### 3. Use Shorter Operations
- Break large tasks into smaller chunks
- This reduces the need to interrupt

## Future Solutions

### Option 1: Session Management Layer
Add session IDs to track and recover connections:
```python
class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, agent_id):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "agent_id": agent_id,
            "created_at": datetime.now(),
            "process": None
        }
        return session_id
```

### Option 2: Connection Pool
Maintain a pool of Marcus processes that can be reused:
```python
class MarcusConnectionPool:
    def __init__(self, size=3):
        self.pool = []
        self.in_use = set()

    async def get_connection(self):
        # Return available connection or create new one
        pass
```

### Option 3: HTTP/WebSocket Transport
Switch from stdio to a more robust transport that supports reconnection:
- WebSocket with automatic reconnection
- HTTP with session cookies
- gRPC with connection management

## Related Issues

- Aggressive cleanup timeouts (fixed in commit)
- Lack of session persistence in MCP protocol
- No built-in reconnection mechanism in stdio transport

## Best Practices

1. **Save Work Frequently**: Commit before long operations
2. **Monitor Connections**: Check Marcus logs for connection state
3. **Report Issues**: File at https://github.com/anthropics/claude-code/issues

## Debug Commands

```bash
# Check if Marcus process is still running
ps aux | grep marcus_mcp

# Check for orphaned Marcus processes
lsof | grep marcus | grep PIPE

# Clean up orphaned processes
pkill -f marcus_mcp
```
