# Quick Start Guide

This guide will get you up and running with PM Agent in 5 minutes.

## Prerequisites

- Python 3.8+
- Node.js 18+
- Docker
- Git

## Step 1: Setup kanban-mcp (includes Planka)

```bash
# Clone and setup kanban-mcp
git clone https://github.com/bradrisse/kanban-mcp.git
cd kanban-mcp
npm install
npm run build

# Start Planka
npm run up
```

This starts Planka at http://localhost:3333
- Login: `demo@demo.demo` / `demo`

## Step 2: Setup PM Agent

```bash
# Clone PM Agent (in parent directory)
cd ..
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Step 3: Verify Setup

```bash
python scripts/utilities/test_setup.py
```

This checks:
- ✓ Python environment
- ✓ Configuration files
- ✓ kanban-mcp installation
- ✓ Planka accessibility

## Step 4: Create Initial Board

```bash
# Option 1: Reset with todo app tasks
python scripts/reset_todo_board_auto.py

# Option 2: Interactive board selection
python scripts/testing/working_select_board_fixed.py
```

## Step 5: Test PM Agent

```bash
# View current board state
python scripts/utilities/quick_board_view.py

# Interactive testing
python scripts/utilities/interactive_test.py

# Run full simulation
python scripts/test_pm_agent_end_to_end.py
```

## Step 6: Start PM Agent Server

For worker agents to connect:

```bash
python start_pm_agent_task_master.py
```

## Important Notes

- **Planka runs via Docker** - Started by `npm run up` in kanban-mcp
- **kanban-mcp is an MCP stdio server** - Starts automatically when Python scripts connect
- **No manual kanban-mcp management needed** - Just run the Python scripts
- **Default board configuration** is in `config_pm_agent.json`

## Stopping Services

```bash
# Stop Planka (from kanban-mcp directory)
cd ../kanban-mcp
npm run down
```

## Next Steps

- Read the [Architecture Guide](architecture.md)
- Learn about [Worker Agents](worker-agents.md)
- See [Configuration Options](configuration.md)
- Understand [Kanban MCP Integration](kanban-mcp-integration.md)