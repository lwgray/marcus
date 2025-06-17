# PM Agent Setup Guide

## Quick Start

PM Agent can be used with both Claude Desktop and Claude Code. Choose based on your needs:

- **Claude Desktop**: For project management, planning, and coordination
- **Claude Code**: For actual development work with file system access

## Claude Desktop Setup

### 1. Edit Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pm-agent": {
      "command": "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
      "args": ["-m", "src.pm_agent_mvp_fixed"],
      "cwd": "/Users/lwgray/dev/pm-agent"
    }
  }
}
```

### 2. Restart Claude Desktop

Quit and restart Claude Desktop for changes to take effect.

### 3. Verify

Ask Claude: "Can you use the pm-agent ping tool?"

## Claude Code Setup

### 1. Add MCP Server

Run in terminal:

```bash
claude mcp add pm-agent /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python -m src.pm_agent_mvp_fixed
```

### 2. Verify

In Claude Code, ask to use the pm-agent ping tool.

## Prerequisites for Both

1. **Install PM Agent**:
   ```bash
   cd /Users/lwgray/dev/pm-agent
   pip install -r requirements.txt
   ```

2. **Configure PM Agent**:
   Create `config_pm_agent.json`:
   ```json
   {
     "project_id": "your-project-id",
     "board_id": "your-board-id"
   }
   ```

3. **Start Planka**:
   ```bash
   cd /Users/lwgray/dev/kanban-mcp
   npm run up
   ```

## Security Notes

- **Claude Desktop**: Sandboxed environment, limited file access
- **Claude Code**: Full file access with WorkspaceManager protection

PM Agent automatically protects its source code from modification by agents in both environments.

## Available Tools

Both environments get access to:
- `ping` - Health check
- `register_agent` - Register as agent
- `request_next_task` - Get tasks
- `report_task_progress` - Update progress
- `report_blocker` - Report issues
- `get_project_status` - View stats
- `get_agent_status` - Check status
- `list_registered_agents` - List agents

## Troubleshooting

### Python Not Found
Use full path to Python:
- Conda: `/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python`
- System: `/usr/bin/python3` or `python3`

### Module Not Found
Ensure running from PM Agent directory or set PYTHONPATH.

### Board ID Not Set
Check `config_pm_agent.json` exists with valid IDs.

## Full Documentation

- [Claude Desktop Setup](docs/CLAUDE_DESKTOP_SETUP.md)
- [Claude Code Setup](docs/CLAUDE_CODE_SETUP.md)
- [Security Model](docs/claude-code-setup.md)