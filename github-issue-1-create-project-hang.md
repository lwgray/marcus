# create_project MCP tool doesn't send response back, causing client connection to hang

## Problem Description

When using the `create_project` MCP tool through Claude Code, the tool successfully creates the project and task cards in Planka, but fails to send a response back to the client. This leaves Claude Code waiting indefinitely for a response, effectively hanging the connection.

## Steps to Reproduce

1. Start Marcus MCP server (`marcus start`)
2. Connect Claude Code to Marcus
3. Call the `create_project` tool to create a new project
4. Observe that:
   - The project and tasks ARE created successfully in Planka
   - Claude Code never receives a response and appears to hang
   - The Claude Code instance must be interrupted

## Expected Behavior

- The `create_project` tool should complete the project creation AND send a proper JSON-RPC response back to the client
- Claude Code should receive the response and be able to continue with other operations

## Actual Behavior

- Project creation completes successfully on the backend
- No response is sent back to the client
- Claude Code hangs waiting for a response
- The connection becomes unusable:
  - Pinging Marcus from the same Claude Code instance fails
  - A new Claude Code instance can successfully ping Marcus

## Technical Analysis

### Root Cause
The issue appears to be related to stdout interference with the JSON-RPC protocol. When Marcus starts, it outputs significant diagnostic information to stdout:

```
🚀 Starting Marcus MCP Server...
==================================================
🏗️  Provider: planka
🔧 Initializing server components...
[... more startup output ...]
```

In JSON-RPC over stdio (which MCP uses):
- **stdin**: Server receives requests
- **stdout**: Server sends responses (MUST be clean JSON-RPC only)
- **stderr**: For logging/debugging

Any non-JSON-RPC output to stdout corrupts the communication channel.

### Likely Issues

1. **Startup logging to stdout**: The server startup messages shown above
2. **Progress messages during project creation**: The tool might be printing status updates
3. **Board creation output**: Possible "Board: [details]" output mentioned in code analysis

### Affected Code Areas

- `/Users/lwgray/dev/marcus/src/marcus_mcp/tools/nlp.py` - create_project implementation
- `/Users/lwgray/dev/marcus/src/marcus_mcp/handlers.py` - MCP response handling
- `/Users/lwgray/dev/marcus/src/integrations/pipeline_tracked_nlp.py` - Project creation pipeline
- Server startup code that prints diagnostic information

## Proposed Solution

### 1. Immediate Fix - Redirect All Output
- Ensure ALL print statements and logging go to stderr, not stdout
- Add stdout capture/suppression around project creation
- Validate JSON-RPC response format before sending

### 2. Code Changes Needed

```python
# In create_project function
import sys
from io import StringIO

async def create_project(...):
    # Capture any stdout to prevent interference
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        # ... existing project creation logic ...
        result = await pipeline.create_project_from_natural_language(...)

        # Ensure clean response
        return {
            "success": True,
            "project": {...},
            "message": "Project created successfully"
        }
    finally:
        # Restore stdout
        sys.stdout = old_stdout
```

### 3. Server-wide Changes
- Move ALL startup logging to stderr or log files
- Add a logging configuration that enforces stderr for console output
- Add JSON-RPC response validation before sending

### 4. Testing Strategy
- Unit test to verify no stdout pollution during tool execution
- Integration test with actual MCP client to verify response delivery
- Add stdout monitoring in tests to catch any print statements

## Impact

- **Severity**: High - Makes the tool unusable through MCP
- **Users Affected**: Anyone using create_project through Claude Code or other MCP clients
- **Workaround**: None - must restart Claude Code instance after each use

## Related Issues

- MCP protocol specification requires clean stdout for JSON-RPC
- Similar issues may affect other long-running MCP tools if they print to stdout

## Additional Context

The issue manifests as a hung connection rather than an error, making it particularly problematic for users who may not realize the operation actually succeeded on the backend.
