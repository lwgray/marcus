# Claude Desktop Setup for Marcus

## Overview

Claude Desktop uses a different configuration format than Claude Code. This guide shows how to set up Marcus as an MCP server in Claude Desktop.

## Prerequisites

1. **Marcus installed and working**:
   ```bash
   cd /path/to/pm-agent
   python -m src.pm_agent_mvp_fixed
   # Should see "Marcus MVP is ready!" message
   ```

2. **Planka running** (for kanban board):
   ```bash
   cd /path/to/kanban-mcp
   npm run up
   ```

3. **Configuration file exists**:
   ```bash
   cat /path/to/pm-agent/config_pm_agent.json
   # Should show project_id and board_id
   ```

## Configuration Steps

### 1. Open Claude Desktop Configuration

1. Open Claude Desktop
2. Go to Settings (⌘+, on Mac, Ctrl+, on Windows/Linux)
3. Navigate to "Developer" section
4. Click "Edit Config" under MCP Servers

### 2. Add Marcus Configuration

Add this to your config file:

**Location of config file:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/path/to/your/python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/path/to/pm-agent",
      "env": {
        "PYTHONPATH": "/path/to/pm-agent"
      }
    }
  }
}
```

Replace the paths with your actual paths:
- `/path/to/your/python`: Your Python executable
- `/path/to/pm-agent`: Where you cloned/installed Marcus

### Alternative Configurations

#### Using System Python
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "python3",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/path/to/pm-agent"
    }
  }
}
```

#### Using Conda Environment
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/home/user/anaconda3/envs/pm-agent/bin/python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/path/to/pm-agent"
    }
  }
}
```

#### Using Pipenv
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "pipenv",
      "args": ["run", "python", "-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/path/to/pm-agent"
    }
  }
}
```

#### Using Start Script (with Task Master defaults)
```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/path/to/your/python",
      "args": ["start_pm_agent_task_master.py"],
      "cwd": "/path/to/pm-agent"
    }
  }
}
```

### 3. Restart Claude Desktop

After saving the configuration:
1. Quit Claude Desktop completely (⌘+Q on Mac, Alt+F4 on Windows)
2. Restart Claude Desktop
3. The Marcus server should connect automatically

## Finding Your Python Path

### For Different Environments

**Conda:**
```bash
conda activate your-env
which python
# Example: /home/user/anaconda3/envs/pm-agent/bin/python
```

**Virtualenv:**
```bash
source venv/bin/activate
which python
# Example: /home/user/project/venv/bin/python
```

**Pipenv:**
```bash
cd /path/to/pm-agent
pipenv --venv
# Returns: /home/user/.local/share/virtualenvs/pm-agent-x7d8/
# Use: /home/user/.local/share/virtualenvs/pm-agent-x7d8/bin/python
```

**System Python:**
```bash
which python3
# Example: /usr/bin/python3
```

**Windows:**
```bash
where python
# Example: C:\Users\Username\AppData\Local\Programs\Python\Python39\python.exe
```

## Verifying the Setup

### Check Connection
In a new Claude Desktop conversation, ask:
```
Can you use the pm-agent ping tool to check if the Marcus is running?
```

You should see:
- Status: online
- Service: Marcus MVP
- Health: healthy

### Available Tools

Once connected, Claude Desktop has access to these Marcus tools:

1. **`ping`** - Check Marcus health
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

1. **Working Directory**: Set to Marcus directory for module imports
2. **File Access**: Claude Desktop has its own file access controls
3. **Workspace Protection**: Marcus's WorkspaceManager still protects source files

The security boundaries work differently:
- Claude Desktop doesn't have direct file system access like Claude Code
- Marcus tools return sanitized data
- Workspace paths in task assignments are informational

## Troubleshooting

### "MCP Server failed to start"
1. Check Python path is correct
2. Verify Marcus works standalone:
   ```bash
   cd /path/to/pm-agent
   /path/to/your/python -m src.pm_agent_mvp_fixed
   ```
3. Check logs in Claude Desktop developer console

### "No module named src"
1. Ensure `cwd` is set to Marcus directory
2. Add `PYTHONPATH` to env if needed
3. Try absolute path: `"args": ["/path/to/pm-agent/src/pm_agent_mvp_fixed.py"]`

### "Board ID not set"
1. Check `config_pm_agent.json` exists in Marcus directory
2. Verify Planka is running
3. Use diagnostic tools to test configuration:
   ```bash
   python /path/to/pm-agent/tests/diagnostics/test_board_id.py
   ```

### Tools not appearing
1. Restart Claude Desktop completely
2. Check MCP server status in developer settings
3. Verify no syntax errors in config JSON (use a JSON validator)

### Windows-specific issues
1. Use forward slashes in paths: `C:/Users/Name/pm-agent`
2. Or escape backslashes: `C:\\Users\\Name\\pm-agent`
3. Try short path names if spaces cause issues

## Environment Variables

Marcus reads from `.env` file in its directory:

```bash
# /path/to/pm-agent/.env
PLANKA_BASE_URL=http://localhost:3333
PLANKA_AGENT_EMAIL=demo@demo.demo
PLANKA_AGENT_PASSWORD=demo
ANTHROPIC_API_KEY=your-api-key-here
```

## Best Practices

1. **Test Standalone First**: Always verify Marcus works in terminal before adding to Claude Desktop
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