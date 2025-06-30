# How to Start Marcus MCP Server

## Current Status
✅ Marcus initialization test passed
✅ Configuration loading works
✅ All fixes applied successfully

## Steps to Connect Marcus via MCP

### 1. Start Marcus MCP Server
In a terminal, run:
```bash
cd /Users/lwgray/dev/marcus
python marcus.py
```

You should see:
```
Marcus MCP Server Running
Kanban Provider: PLANKA
Logs: logs/conversations/
==================================================
```

**Leave this terminal running** - Marcus is now waiting for MCP connections.

### 2. Connect via Your MCP Client

Your MCP client should be configured to connect to Marcus. If you're using Claude Desktop, the configuration should look like:

```json
{
  "mcpServers": {
    "marcus": {
      "command": "python",
      "args": ["/Users/lwgray/dev/marcus/marcus.py"],
      "env": {
        "KANBAN_PROVIDER": "planka",
        "PLANKA_BASE_URL": "http://localhost:3333",
        "PLANKA_AGENT_EMAIL": "demo@demo.demo",
        "PLANKA_AGENT_PASSWORD": "demo"
      }
    }
  }
}
```

### 3. Test the Fixed Tools

Once connected, try:

1. **get_project_status** - should return project metrics
2. **request_next_task** with agent_id - should work without JSON errors

## Troubleshooting

If connection fails:
1. Make sure Planka is running on http://localhost:3333
2. Check that Marcus terminal shows "Marcus MCP Server Running"
3. Verify your MCP client configuration matches above
4. Restart both Marcus and your MCP client if needed

## What Was Fixed

- ✅ RiskLevel JSON serialization errors
- ✅ "Not initialized" errors in get_project_status
- ✅ Automatic configuration loading from config_marcus.json
- ✅ Environment variable setup for Planka connection