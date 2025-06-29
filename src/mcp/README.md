# Marcus MCP Server - Modular Architecture

This directory contains the reorganized Marcus MCP server with a modular architecture.

## Structure

```
src/mcp/
├── __init__.py          # Package initialization
├── server.py            # Main server class and entry point
├── handlers.py          # Tool registration and routing
├── tools/               # Tool implementations organized by domain
│   ├── __init__.py      # Tool exports
│   ├── agent_tools.py   # Agent management (register, status, list)
│   ├── task_tools.py    # Task operations (request, progress, blockers)
│   ├── project_tools.py # Project monitoring
│   ├── system_tools.py  # System health checks
│   └── nlp_tools.py     # Natural language processing tools
└── README.md            # This file
```

## Benefits

1. **Better Organization**: Tools are grouped by functionality
2. **Easier Maintenance**: Each tool module is focused on a specific domain
3. **Improved Testing**: Modules can be tested independently
4. **Cleaner Code**: Main server file reduced from 1302 lines to ~150 lines
5. **Better Reusability**: Tool functions can be imported and used elsewhere

## Usage

The server can be run using either:

```bash
# Using the new entry point
python marcus_mcp_server_new.py

# Or directly
python -m src.mcp.server
```

## Tool Categories

### Agent Tools (`agent_tools.py`)
- `register_agent`: Register new agents with skills and roles
- `get_agent_status`: Check agent status and current tasks
- `list_registered_agents`: List all registered agents

### Task Tools (`task_tools.py`)
- `request_next_task`: AI-powered optimal task assignment
- `report_task_progress`: Update task progress and status
- `report_blocker`: Report blockers with AI suggestions

### Project Tools (`project_tools.py`)
- `get_project_status`: Get comprehensive project metrics

### System Tools (`system_tools.py`)
- `ping`: Check system connectivity
- `check_assignment_health`: Monitor assignment system health

### NLP Tools (`nlp_tools.py`)
- `create_project`: Create projects from natural language
- `add_feature`: Add features using natural language

## Migration Notes

The modular structure maintains full compatibility with the original implementation.
All tool signatures and behaviors remain unchanged.