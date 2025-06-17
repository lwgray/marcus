# Claude Desktop Setup for PM Agent

## Overview

Claude Desktop uses a different configuration format than Claude Code. This guide shows how to set up PM Agent as an MCP server in Claude Desktop.

## Prerequisites

1. **PM Agent installed and working**:
   ```bash
   cd /Users/lwgray/dev/pm-agent
   python -m src.pm_agent_mvp_fixed
   # Should see "PM Agent MVP is ready!" message
   ```

2. **Planka running** (for kanban board):
   ```bash
   cd /Users/lwgray/dev/kanban-mcp
   npm run up
   ```

3. **Configuration file exists**:
   ```bash
   cat /Users/lwgray/dev/pm-agent/config_pm_agent.json
   # Should show project_id and board_id
   ```

## Configuration Steps

### 1. Open Claude Desktop Configuration

1. Open Claude Desktop
2. Go to Settings (⌘+, on Mac)
3. Navigate to "Developer" section
4. Click "Edit Config" under MCP Servers

### 2. Add PM Agent Configuration

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/lwgray/dev/pm-agent",
      "env": {
        "PYTHONPATH": "/Users/lwgray/dev/pm-agent"
      }
    }
  }
}
```

### Alternative Configurations

#### Using System Python
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/lwgray/dev/pm-agent"
    }
  }
}
```

#### Using Start Script (with Task Master defaults)
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
      "args": ["start_pm_agent_task_master.py"],
      "cwd": "/Users/lwgray/dev/pm-agent"
    }
  }
}
```

### 3. Restart Claude Desktop

After saving the configuration:
1. Quit Claude Desktop completely (⌘+Q)
2. Restart Claude Desktop
3. The PM Agent server should connect automatically

## Verifying the Setup

### Check Connection
In a new Claude Desktop conversation, ask:
```
Can you use the pm-agent ping tool to check if the PM Agent is running?
```

You should see:
- Status: online
- Service: PM Agent MVP
- Health: healthy

### Available Tools

Once connected, Claude Desktop has access to these PM Agent tools:

1. **`ping`** - Check PM Agent health
2. **`register_agent`** - Register as a worker agent
3. **`request_next_task`** - Get task assignment
4. **`report_task_progress`** - Update task progress
5. **`report_blocker`** - Report blockers
6. **`get_project_status`** - View project stats
7. **`get_agent_status`** - Check agent info
8. **`list_registered_agents`** - List all agents

## Example Usage

### 1. Register as an Agent
```
Use the pm-agent register_agent tool with:
- agent_id: "claude-desktop-01"
- name: "Claude Desktop Agent"
- role: "AI Assistant"
- skills: ["planning", "code-review", "documentation"]
```

### 2. Request a Task
```
Use the pm-agent request_next_task tool with agent_id "claude-desktop-01"
```

### 3. Report Progress
```
Use the pm-agent report_task_progress tool with:
- agent_id: "claude-desktop-01"
- task_id: [from previous step]
- status: "in_progress"
- progress: 50
- message: "Completed initial analysis"
```

## Security in Claude Desktop

Claude Desktop runs MCP servers with different security constraints than Claude Code:

1. **Working Directory**: Set to PM Agent directory for module imports
2. **File Access**: Claude Desktop has its own file access controls
3. **Workspace Protection**: PM Agent's WorkspaceManager still protects source files

The security boundaries work differently:
- Claude Desktop doesn't have direct file system access like Claude Code
- PM Agent tools return sanitized data
- Workspace paths in task assignments are informational

## Troubleshooting

### "MCP Server failed to start"
1. Check Python path is correct: `which python` or `which python3`
2. Verify PM Agent works standalone
3. Check logs in Claude Desktop developer console

### "No module named src"
1. Ensure `cwd` is set to PM Agent directory
2. Add `PYTHONPATH` to env if needed
3. Try absolute import: `"args": ["/Users/lwgray/dev/pm-agent/src/pm_agent_mvp_fixed.py"]`

### "Board ID not set"
1. Check `config_pm_agent.json` exists in PM Agent directory
2. Verify Planka is running
3. Use diagnostic tools to test configuration

### Tools not appearing
1. Restart Claude Desktop completely
2. Check MCP server status in developer settings
3. Verify no syntax errors in config JSON

## Environment Variables

PM Agent reads from `.env` file in its directory:

```bash
# /Users/lwgray/dev/pm-agent/.env
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo
ANTHROPIC_API_KEY=your-api-key-here
```

## Best Practices

1. **Test Standalone First**: Always verify PM Agent works in terminal before adding to Claude Desktop
2. **Use Absolute Paths**: Avoid path resolution issues
3. **Check Logs**: Enable developer mode to see MCP communication
4. **One Agent Per Session**: Register once per Claude Desktop conversation

## Differences from Claude Code

| Feature | Claude Desktop | Claude Code |
|---------|---------------|-------------|
| File Access | Limited, controlled | Full, with MCP tools |
| Working Directory | Informational only | Actual file system access |
| Security Model | Sandbox-based | Path validation-based |
| Use Case | Planning & coordination | Actual development work |

Claude Desktop is ideal for:
- Project planning and task management
- Reviewing project status
- Coordinating work assignments
- Getting AI assistance on blockers

Claude Code is ideal for:
- Actually implementing tasks
- Writing and editing code
- Running tests and builds
- File system operations