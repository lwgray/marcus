# Debugging MCP Connection Interruptions

## Overview

When Claude Code is interrupted during an MCP call, it can leave the connection in a broken state. This guide explains how to debug these issues by logging all JSON-RPC messages between Claude and Marcus.

## Enabling MCP Debug Mode

### 1. Set Environment Variable

Before starting Claude Code, set the `MCP_DEBUG` environment variable:

```bash
export MCP_DEBUG=1
claude
```

Or run it directly:
```bash
MCP_DEBUG=1 claude
```

### 2. Debug Logs Location

When debug mode is enabled, Marcus will create detailed logs in:
```
/Users/lwgray/dev/marcus/logs/mcp_debug/
```

Three log files are created for each session:
- `mcp_read_YYYYMMDD_HHMMSS.log` - Messages FROM Claude TO Marcus
- `mcp_write_YYYYMMDD_HHMMSS.log` - Messages FROM Marcus TO Claude
- `mcp_combined_YYYYMMDD_HHMMSS.log` - All messages in chronological order

## Experiment: Debugging an Interruption

### Step 1: Start with Debug Mode

```bash
# Start Claude with debugging enabled
MCP_DEBUG=1 claude

# You'll see in the Marcus startup logs:
🔍 MCP Debug logging enabled:
   📖 Read log: /Users/lwgray/dev/marcus/logs/mcp_debug/mcp_read_20250724_083000.log
   ✍️  Write log: /Users/lwgray/dev/marcus/logs/mcp_debug/mcp_write_20250724_083000.log
   📊 Combined log: /Users/lwgray/dev/marcus/logs/mcp_debug/mcp_combined_20250724_083000.log
```

### Step 2: Perform Normal Operations

Use Marcus tools normally. Each JSON-RPC message will be logged.

### Step 3: Interrupt During an Operation

When you see a long-running operation (like `create_project`), interrupt it with Ctrl+C.

### Step 4: Analyze the Logs

Open the combined log to see what happened:

```bash
# View the last messages before interruption
tail -50 /Users/lwgray/dev/marcus/logs/mcp_debug/mcp_combined_*.log
```

Look for:
1. **Incomplete JSON messages** - Partial data that got cut off
2. **Missing response** - Request without corresponding response
3. **Error messages** - Any errors during read/write operations

## What to Look For

### Healthy Communication Pattern
```json
[write] {
  "jsonrpc": "2.0",
  "id": 1,
  "method": "ping",
  "params": {"echo": "test"}
}

[read] {
  "jsonrpc": "2.0",
  "id": 1,
  "result": {"echo": "test", "timestamp": "..."}
}
```

### Interrupted Communication Pattern
```json
[write] {
  "jsonrpc": "2.0",
  "id": 2,
  "method": "create_project",
  "params": {...}
}

[read] {
  "jsonrpc": "2.0",
  "id": 2,
  "res[INTERRUPTED]

[write] {
  "jsonrpc": "2.0",
  "id": 3,
  "method": "ping",
  "params": {}
}

[read_error] {
  "error": "JSON parse error: Unexpected token",
  "buffer": "ult\":{...}}\n{\"jsonrpc\":\"2.0\",\"error\":..."
}
```

## Common Issues Found

### 1. Partial Message in Buffer
When interrupted, a partial JSON message remains in the stdio buffer. The next message gets appended, creating invalid JSON.

### 2. Lost Message Boundaries
JSON-RPC over stdio uses newline delimiters. An interruption can break this, causing message boundaries to be lost.

### 3. No Recovery Mechanism
Once the stream is corrupted, there's no protocol to clear the buffer and resynchronize.

## Temporary Workarounds

1. **Wait for Operations**: Don't interrupt during MCP calls
2. **Quick Recovery**: If interrupted, restart Claude Code immediately
3. **Monitor Logs**: Use debug mode to understand when corruption happens

## Long-term Solutions

1. **Message Framing**: Implement length-prefixed messages
2. **Stream Recovery**: Add synchronization markers
3. **Alternative Transport**: Use WebSocket or HTTP instead of stdio

## Disable Debug Mode

Remember to disable debug mode for normal use:
```bash
unset MCP_DEBUG
```

Debug logs can grow large quickly, so clean them up periodically:
```bash
rm -rf /Users/lwgray/dev/marcus/logs/mcp_debug/*
```
