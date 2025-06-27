# Marcus UI Status and Issues

## Current Situation

Marcus has a visualization UI component (`src/visualization/ui_server.py`) but it's currently not working due to initialization issues.

## The UI Components

### 1. **UI Server** (`src/visualization/ui_server.py`)
- Runs on port 8080 (not 8765 as previously thought)
- Provides real-time visualization of:
  - Agent conversations
  - Decision-making processes
  - Knowledge graph
  - System metrics
- Uses Socket.IO for real-time updates
- Has a web interface with Jinja2 templates

### 2. **Related Components**
- `conversation_stream.py` - Processes conversation events
- `decision_visualizer.py` - Visualizes decision-making
- `knowledge_graph.py` - Builds knowledge graphs
- `health_monitor.py` - Monitors system health

## Current Issues

### 1. **Initialization Error**
```
TypeError: object NoneType can't be used in 'await' expression
```
- Location: `health_monitor.start_monitoring(health_update_callback)`
- The `start_monitoring` method returns `None` instead of an awaitable

### 2. **Missing Dependencies**
The UI requires several packages that might not be installed:
- `aiohttp` - Async HTTP server
- `aiohttp-cors` - CORS support
- `python-socketio` - Socket.IO server
- `jinja2` - Template engine

### 3. **Missing Templates**
The UI expects templates in `src/visualization/templates/` but this directory might not exist or have the required `index.html`.

### 4. **Health Monitor Issues**
The health monitor's `start_monitoring` method needs to be async but isn't properly implemented.

## How Marcus Actually Works Without UI

Marcus is an MCP (Model Context Protocol) server that:
1. Runs as a stdio server (communicates via stdin/stdout)
2. Is accessed through Claude's MCP interface
3. Doesn't need a web UI to function

The experiments work by:
1. Claude agents connect to Marcus via MCP
2. Marcus coordinates tasks through the MCP protocol
3. No web UI is needed for basic operation

## Fixing the UI

To fix the UI server, we need to:

### 1. **Install Dependencies**
```bash
pip install aiohttp aiohttp-cors python-socketio jinja2
```

### 2. **Fix the Health Monitor**
The `start_monitoring` method needs to be properly async.

### 3. **Create Missing Templates**
Need to create `src/visualization/templates/index.html`

### 4. **Fix Initialization**
The server initialization needs to handle missing components gracefully.

## Workaround for Experiments

Since the UI is broken, monitor experiments by:

1. **Watch Marcus MCP logs** in the terminal where it's running
2. **Check git branches** for agent commits:
   ```bash
   git log --oneline --graph --all
   ```
3. **Use the Kanban board directly** (GitHub Projects, Linear, or Planka)
4. **Watch agent terminals** to see their progress

## Alternative Monitoring

### 1. **Simple Log Monitor**
```bash
# Watch Marcus logs
tail -f marcus.log | grep -E "task|agent|complete"
```

### 2. **Git Activity Monitor**
```bash
# Watch for new commits
watch -n 5 'git log --oneline --all --since="1 hour ago"'
```

### 3. **Direct MCP Queries**
Use Claude to query Marcus directly:
```
/mcp
# Connect to marcus
# Then use: marcus.get_project_status()
```

## Summary

- Marcus UI exists but is currently broken
- The UI runs on port 8080, not 8765
- Marcus works fine without the UI through MCP
- Experiments can be monitored through logs and git
- The UI can be fixed but isn't required for experiments