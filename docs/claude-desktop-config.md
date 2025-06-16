# Claude Desktop MCP Configuration for PM Agent

To use PM Agent with Claude Desktop, add the following configuration to your MCP settings.

## Configuration Steps

1. Open Claude Desktop settings
2. Navigate to the MCP server configuration section
3. Add the PM Agent server configuration

## PM Agent MCP Server Configuration

### Option 1: Using PM Agent Conda Environment (Recommended)

```json
{
  "pm-agent": {
    "command": "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
    "args": ["-m", "src.pm_agent_mvp_fixed"],
    "cwd": "/Users/lwgray/dev/pm-agent",
    "env": {
      "PYTHONPATH": "/Users/lwgray/dev/pm-agent",
      "PLANKA_BASE_URL": "http://localhost:3333",
      "PLANKA_AGENT_EMAIL": "demo@demo.demo",
      "PLANKA_AGENT_PASSWORD": "demo"
    }
  }
}
```

### Option 2: Using python3 Command

```json
{
  "pm-agent": {
    "command": "python3",
    "args": ["-m", "src.pm_agent_mvp_fixed"],
    "cwd": "/Users/lwgray/dev/pm-agent",
    "env": {
      "PYTHONPATH": "/Users/lwgray/dev/pm-agent",
      "PLANKA_BASE_URL": "http://localhost:3333",
      "PLANKA_AGENT_EMAIL": "demo@demo.demo",
      "PLANKA_AGENT_PASSWORD": "demo"
    }
  }
}
```

## Alternative: Using the Start Script

If you prefer using the start script that auto-configures the Task Master project:

```json
{
  "pm-agent": {
    "command": "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python",
    "args": ["start_pm_agent_task_master.py"],
    "cwd": "/Users/lwgray/dev/pm-agent",
    "env": {
      "PYTHONPATH": "/Users/lwgray/dev/pm-agent",
      "PLANKA_BASE_URL": "http://localhost:3333",
      "PLANKA_AGENT_EMAIL": "demo@demo.demo",
      "PLANKA_AGENT_PASSWORD": "demo"
    }
  }
}
```

## Environment Variables

Make sure these environment variables are set:

- `PYTHONPATH`: Path to the PM Agent directory
- `PLANKA_BASE_URL`: URL where Planka is running (default: http://localhost:3333)
- `PLANKA_AGENT_EMAIL`: Planka login email (default: demo@demo.demo)
- `PLANKA_AGENT_PASSWORD`: Planka login password (default: demo)
- `ANTHROPIC_API_KEY`: (Optional) Your Anthropic API key for AI features

## Prerequisites

Before using PM Agent in Claude Desktop:

1. **Install dependencies**:
   ```bash
   cd /Users/lwgray/dev/pm-agent
   pip install -r requirements.txt
   ```

2. **Start Planka** (from kanban-mcp directory):
   ```bash
   cd /Users/lwgray/dev/kanban-mcp
   npm run up
   ```

3. **Verify PM Agent works standalone**:
   ```bash
   cd /Users/lwgray/dev/pm-agent
   python -m src.pm_agent_mvp_fixed
   ```

## Available Tools in Claude Desktop

Once configured, you'll have access to these PM Agent tools:

- `ping` - Check PM Agent health status
- `register_agent` - Register as a worker agent
- `request_next_task` - Get assigned a task
- `report_task_progress` - Update task progress
- `report_blocker` - Report task blockers
- `get_project_status` - View project overview
- `get_agent_status` - Check agent status
- `list_registered_agents` - List all agents

## Troubleshooting

### "spawn python ENOENT" Error
This error means Claude Desktop can't find the Python executable. Solutions:
1. Use the full path to Python: `/Users/lwgray/opt/anaconda3/bin/python`
2. Or use `python3` instead of `python` in the command
3. Find your Python path with: `which python` or `which python3`

### PM Agent won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Ensure Planka is running at http://localhost:3333
- Verify the `cwd` path is correct for your system

### No tasks available
- Create tasks in Planka first
- Ensure tasks are in "To Do" or "Backlog" lists
- Check that board ID is configured correctly

### Connection errors
- Verify kanban-mcp is installed: `/Users/lwgray/dev/kanban-mcp/dist/index.js` should exist
- Check environment variables are set correctly
- Ensure Docker is running (for Planka)

## Example Usage in Claude Desktop

Once configured, you can interact with PM Agent:

```
Human: Can you ping the PM Agent to check if it's running?