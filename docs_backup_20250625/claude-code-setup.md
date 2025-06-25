# PM Agent Setup for Claude Code

This guide shows how to add PM Agent to Claude Code using the `claude mcp add` command.

## Prerequisites

1. Install Claude Code CLI
2. Ensure PM Agent is set up with a `.env` file containing your Planka credentials
3. Have the pm-agent conda environment activated or Python available

## Adding PM Agent to Claude Code

### Option 1: Using Conda Environment

```bash
claude mcp add pm-agent -s user -- /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python -m src.pm_agent_mvp_fixed
```

### Option 2: Using System Python

```bash
claude mcp add pm-agent -s user -- python3 -m src.pm_agent_mvp_fixed
```

### Option 3: With Working Directory

If you need to specify the working directory:

```bash
claude mcp add pm-agent -s user -- bash -c "cd /Users/lwgray/dev/pm-agent && /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python -m src.pm_agent_mvp_fixed"
```

## Verifying Installation

After adding PM Agent, verify it's installed:

```bash
claude mcp list
```

You should see `pm-agent` in the list of configured MCP servers.

## Using PM Agent in Claude Code

Once added, you can use PM Agent tools in Claude Code:

- `ping` - Check PM Agent status
- `register_agent` - Register as a worker
- `request_next_task` - Get task assignments
- `report_task_progress` - Update progress
- And more...

## Removing PM Agent

If you need to remove PM Agent:

```bash
claude mcp remove pm-agent
```

## Troubleshooting

1. **Python not found**: Use the full path to your Python executable
2. **Module not found**: Ensure you're in the correct directory or set PYTHONPATH
3. **Planka connection errors**: Check your `.env` file has correct credentials

## Alternative: Direct Configuration

If you prefer, you can directly edit the Claude Code configuration instead of using `mcp add`. The config location varies by platform - check Claude Code documentation for details.