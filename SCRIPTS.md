# PM Agent Scripts Documentation

## Root Directory Scripts

### Core Scripts

- **`main.py`** - Original PM Agent implementation (legacy)
  - Uses the old architecture
  - Kept for reference only
  
- **`pm_agent_mcp_server.py`** - Current PM Agent MCP server
  - The main PM Agent server implementation
  - Uses SimpleMCPKanbanClient
  - Provides MCP tools for autonomous agents
  
- **`start_pm_agent_task_master.py`** - Startup script for Task Master board
  - Initializes PM Agent with specific Task Master configuration
  - Sets up logging and environment

### Source Directory (`src/`)

- **`src/pm_agent_mvp_fixed.py`** - Current MVP implementation
  - Used by pm_agent_mcp_server.py
  - Contains all MCP tool implementations
  - Integrates with SimpleMCPKanbanClient

- **`src/integrations/mcp_kanban_client_simple.py`** - Current Kanban client
  - Simplified client that works reliably
  - Handles the listId requirement fix
  - Used by all current implementations

## Test Scripts

All diagnostic and test scripts have been organized into:

- **`tests/unit/`** - Unit tests
- **`tests/integration/`** - Integration tests  
- **`tests/diagnostics/`** - Diagnostic tools for troubleshooting

See `tests/README.md` for detailed test documentation.

## Running PM Agent

### As MCP Server (Recommended)
```bash
python pm_agent_mcp_server.py
```

### With Task Master Board
```bash
python start_pm_agent_task_master.py
```

## Configuration

PM Agent expects `config_pm_agent.json` in the root directory:
```json
{
  "project_id": "your-project-id",
  "board_id": "your-board-id"
}
```

Get these IDs from your Planka instance or use the diagnostic tools to find them.