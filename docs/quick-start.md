# Quick Start Guide

This guide will get you up and running with PM Agent in 5 minutes.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Docker (for Planka)
- kanban-mcp installed at `../kanban-mcp`

## Step 1: Start Planka

```bash
# If using Docker
docker run -d \
  --name planka \
  -p 3333:1337 \
  -v planka-data:/app/data \
  ghcr.io/plankanban/planka:latest
```

Default credentials: `demo@demo.demo` / `demo`

## Step 2: Verify Setup

```bash
python scripts/utilities/test_setup.py
```

This checks:
- ✓ Python environment
- ✓ Configuration files
- ✓ kanban-mcp installation
- ✓ Planka accessibility

## Step 3: View the Board

```bash
python scripts/utilities/quick_board_view.py
```

This shows the current state of your project board.

## Step 4: Run Tests

```bash
# Interactive testing
python scripts/utilities/interactive_test.py

# Full workflow simulation
python scripts/test_pm_agent_end_to_end.py
```

## Step 5: Start PM Agent Server

For worker agents to connect:

```bash
python start_pm_agent_task_master.py
```

## Important Notes

- **kanban-mcp starts automatically** - It's an MCP stdio server, not a background service
- **No manual server management needed** - Just run the Python scripts
- **Configuration** is in `config_pm_agent.json`

## Next Steps

- Read the [Architecture Guide](architecture.md)
- Learn about [Worker Agents](worker-agents.md)
- See [Configuration Options](configuration.md)