# PM Agent Quick Start Guide

This guide will help you get the PM Agent system up and running with visualization.

## Prerequisites

1. Python 3.8+
2. Node.js 16+
3. One of the following kanban providers set up:
   - **Planka**: Local MCP server running
   - **Linear**: API key and team ID
   - **GitHub Projects**: Personal access token with project permissions

## Environment Setup

### 1. Create `.env` file

```bash
# For Planka (default)
KANBAN_PROVIDER=planka
PLANKA_PROJECT_NAME="Task Master Test"

# For Linear
KANBAN_PROVIDER=linear
LINEAR_API_KEY=your_api_key_here
LINEAR_TEAM_ID=your_team_id_here
LINEAR_PROJECT_ID=your_project_id_here  # Optional

# For GitHub Projects
KANBAN_PROVIDER=github
GITHUB_TOKEN=your_token_here
GITHUB_OWNER=your_username_or_org
GITHUB_REPO=your_repo_name
GITHUB_PROJECT_NUMBER=1
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install visualization dependencies

```bash
cd visualization-ui
npm install
cd ..
```

## Quick Start

### Option 1: Automated Demo (Recommended)

```bash
python start_demo.py
```

This will:
1. Let you choose your kanban provider
2. Check environment configuration
3. Start PM Agent MCP server
4. Launch mock Claude workers
5. Start the visualization UI
6. Open terminals for each service

### Option 2: Manual Start

#### 1. Start PM Agent MCP Server

```bash
# Terminal 1
export KANBAN_PROVIDER=planka  # or linear, github
python pm_agent_mcp_server_unified.py
```

#### 2. Start Mock Workers

```bash
# Terminal 2
python mock_claude_worker.py --name worker_1 --skills "backend,api,database"

# Terminal 3
python mock_claude_worker.py --name worker_2 --skills "frontend,ui,testing"
```

#### 3. Start Visualization

```bash
# Terminal 4
cd visualization-ui
npm run dev
```

#### 4. Open Browser

Navigate to http://localhost:4298

## What You'll See

1. **Visualization Canvas**: Shows PM Agent, Workers, and Kanban Board as connected nodes
2. **Real-time Updates**: Watch as workers register, request tasks, and report progress
3. **Data Flow**: See messages flowing between components
4. **Task Progress**: Visual indicators of task status and worker activity

## Logs

All conversations are logged to:
- `logs/conversations/` - Structured JSON logs for visualization
- `logs/raw/` - Raw text logs for debugging

## Sample Tasks

Create these tasks in your kanban board for the demo:

1. **High Priority**: "Implement user authentication"
   - Add to backlog/todo column
   - Set high priority label/field

2. **Medium Priority**: "Create REST API endpoints"
   - Add to backlog/todo column
   - Set medium priority label/field

3. **Low Priority**: "Write unit tests"
   - Add to backlog/todo column
   - Set low priority label/field

## Troubleshooting

### "No tasks available"
- Ensure tasks are in the backlog/todo column
- Check tasks are unassigned
- Verify kanban connection in logs

### Visualization not updating
- Check WebSocket connection (port 4299)
- Verify PM Agent is running with logging enabled
- Check browser console for errors

### Workers not connecting
- Ensure PM Agent MCP server is running first
- Check Python path includes project root
- Verify no port conflicts

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Workers │────▶│    PM Agent     │────▶│  Kanban Board   │
│  (Mock Agents)  │◀────│  (MCP Server)   │◀────│(Planka/Linear/  │
└─────────────────┘     └─────────────────┘     │    GitHub)      │
         │                       │                └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
              ┌──────▼──────┐
              │ Structured  │
              │    Logs     │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │Visualization│
              │     UI      │
              │  (Vue.js)   │
              └─────────────┘
```

## Next Steps

1. **Customize Workers**: Edit `mock_claude_worker.py` to simulate different behaviors
2. **Add More Providers**: Extend `KanbanInterface` for other project management tools
3. **Enhance Visualization**: Modify Vue components in `visualization-ui/src/`
4. **Real Claude Integration**: Replace mock workers with actual Claude Desktop/API calls

## Stopping the Demo

Press `Ctrl+C` in the terminal running `start_demo.py` to stop all services.

For manual setup, stop each service with `Ctrl+C` in its respective terminal.