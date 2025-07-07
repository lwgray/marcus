# Marcus MCP Server - Modular Architecture

This directory contains the reorganized Marcus MCP server with a modular architecture.

## Structure

```
src/marcus_mcp/
├── __init__.py          # Package initialization
├── server.py            # Main server class and entry point
├── handlers.py          # Tool registration and routing
├── tools/               # Tool implementations organized by domain
│   ├── __init__.py      # Tool exports
│   ├── agent.py         # Agent management (register, status, list)
│   ├── task.py          # Task operations (request, progress, blockers)
│   ├── project.py       # Project monitoring
│   ├── system.py        # System health checks
│   ├── nlp.py           # Natural language processing tools
│   ├── context.py       # Context management
│   └── pipeline.py      # Pipeline enhancement tools
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
python marcus.py

# Or directly
python -m src.mcp.server
```

## Tool Categories

### Agent Tools (`agent.py`)
- `register_agent`: Register new agents with skills and roles
- `get_agent_status`: Check agent status and current tasks
- `list_registered_agents`: List all registered agents

### Task Tools (`task.py`)
- `request_next_task`: AI-powered optimal task assignment
- `report_task_progress`: Update task progress and status
- `report_blocker`: Report blockers with AI suggestions

### Project Tools (`project.py`)
- `get_project_status`: Get comprehensive project metrics

### System Tools (`system.py`)
- `ping`: Check system connectivity
- `check_assignment_health`: Monitor assignment system health

### NLP Tools (`nlp.py`)
- `create_project`: Create projects from natural language
- `add_feature`: Add features using natural language

### Context Tools (`context.py`)
- `log_decision`: Log important decisions and context
- `get_task_context`: Retrieve task-specific context

### Pipeline Tools (`pipeline.py`)
- `start_replay`: Start pipeline replay functionality
- `replay_step_forward`: Step forward in pipeline replay
- `replay_step_backward`: Step backward in pipeline replay
- `start_what_if_analysis`: Start what-if analysis
- `simulate_modification`: Simulate pipeline modifications
- `compare_pipelines`: Compare different pipeline configurations

## Migration Notes

The modular structure maintains full compatibility with the original implementation.
All tool signatures and behaviors remain unchanged.