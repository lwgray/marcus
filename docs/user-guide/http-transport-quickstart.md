# Marcus HTTP Transport Quick Start

## Default Mode: Agent Tools

When you start Marcus without any special flags, it now defaults to **Agent Mode** with only the essential tools needed to get work done:

```bash
marcus start
```

This gives you access to 10 agent tools:
- `ping` - Check connection
- `register_agent` - Register yourself as an agent
- `request_next_task` - Get your next task
- `report_task_progress` - Update task status
- `report_blocker` - Report when you're stuck
- `get_task_context` - Get full context for a task
- `log_decision` - Document architectural decisions
- `log_artifact` - Save generated artifacts
- `check_task_dependencies` - Check task dependencies
- `get_agent_status` - Check your current status

## Why Agent Mode by Default?

New users typically want to:
1. Connect to Marcus
2. Get a task
3. Start building
4. Report progress

The agent toolset provides exactly what you need for this workflow, without the overhead of project management tools.

## Other Modes

### All Tools Mode
If you need access to all 42+ tools (project management, analytics, etc.):

```bash
marcus start --all-tools
```

### Multi-Endpoint Mode
For role-based tool separation across different ports:

```bash
marcus start --multi
```

This starts:
- Human tools on port 4298 (9 tools)
- Agent tools on port 4299 (10 tools)
- Analytics tools on port 4300 (42 tools)

### Custom Ports
You can customize ports for any mode:

```bash
# Single endpoint with custom port
marcus start --port 5000

# Multi-endpoint with custom ports
marcus start --multi --human-port 5001 --agent-port 5002 --analytics-port 5003
```

## Connecting Claude

For the default agent mode:
```bash
claude mcp add -t http marcus http://localhost:4298/mcp
```

For multi-endpoint mode (connect to specific role):
```bash
# For human/developer tools
claude mcp add -t http marcus-human http://localhost:4298/mcp

# For agent tools
claude mcp add -t http marcus-agent http://localhost:4299/mcp
```
