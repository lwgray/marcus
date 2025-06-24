# Starting PM Agent MCP Server

Quick guide to get PM Agent up and running.

## Prerequisites

1. **Python 3.8+**
2. **Environment variables** (create `.env` file):
   ```bash
   # Required
   ANTHROPIC_API_KEY=your-api-key-here
   
   # Kanban Provider (choose one)
   KANBAN_PROVIDER=planka  # or github, linear
   
   # Provider-specific settings
   # For Planka:
   PLANKA_SERVER_URL=http://localhost:3000
   PLANKA_EMAIL=demo@demo.demo
   PLANKA_PASSWORD=demo-password
   
   # For GitHub:
   GITHUB_TOKEN=your-github-token
   GITHUB_OWNER=your-username
   GITHUB_REPO=your-repo
   GITHUB_PROJECT_NUMBER=1
   
   # For Linear:
   LINEAR_API_KEY=your-linear-api-key
   LINEAR_TEAM_ID=your-team-id
   ```

## Quick Start

### Option 1: Direct Python
```bash
# Install dependencies
pip install -r requirements.txt

# Start PM Agent
python -m pm_agent_mcp_server_v2

# Server runs on http://localhost:3100
```

### Option 2: Docker Compose (Recommended)
```bash
# Start with local Planka board
docker-compose up -d

# Or use external kanban provider
docker-compose -f docker-compose.remote.yml up -d
```

### Option 3: Using VS Code
1. Open project in VS Code
2. Press `F5` or go to Run → Start Debugging
3. Select "Python: PM Agent MCP Server"

## Verify It's Running

```bash
# Check server health
curl http://localhost:3100/health

# Expected response:
{
  "status": "healthy",
  "uptime": "0h 0m 15s",
  "registered_agents": 0,
  "kanban_provider": "planka"
}
```

## Connecting Worker Agents

Worker agents connect via MCP protocol:

```python
# Example worker agent connection
mcp add server pm-agent http://localhost:3100

# Available tools:
- register_agent
- request_next_task
- report_task_progress
- report_blocker
- get_project_status
- get_agent_status
```

## Configuration Files

### Main Configuration
`config_pm_agent.json`:
```json
{
  "pm_agent": {
    "server_port": 3100,
    "kanban_provider": "planka",
    "enable_ai": true,
    "task_refresh_interval": 30
  }
}
```

### Provider Configurations
- Planka: `config/kanban_planka.json`
- GitHub: `config/kanban_github.json`
- Linear: `config/kanban_linear.json`

## Monitoring

### Logs
```bash
# View real-time logs
docker-compose logs -f pm-agent

# Or if running directly
# Logs appear in console
```

### Visualization Dashboard
```bash
# Start with visualization
docker-compose -f docker-compose.viz.yml up -d

# Access dashboard at http://localhost:8080
```

## Common Issues

### Port Already in Use
```bash
# Change port in config_pm_agent.json
"server_port": 3101
```

### Anthropic API Key Missing
```bash
export ANTHROPIC_API_KEY=your-key-here
# Or add to .env file
```

### Can't Connect to Kanban
- Check provider credentials
- Verify network connectivity
- Ensure kanban service is running

### Worker Can't Find Tasks
- Ensure tasks exist in TODO column
- Check task labels match worker skills
- Verify PM Agent has kanban access

## Stopping PM Agent

### Docker
```bash
docker-compose down
```

### Direct Python
Press `Ctrl+C` in terminal

## Development Mode

For development with auto-reload:
```bash
# Install development dependencies
pip install watchdog

# Run with auto-reload
python -m watchdog.tricks.shell_command \
  --patterns="*.py" \
  --recursive \
  --command="python -m pm_agent_mcp_server_v2" \
  src/
```

## Next Steps

1. **Register a worker agent** using the MCP tools
2. **Create tasks** in your kanban board's TODO column
3. **Monitor progress** via logs or visualization dashboard
4. **Check project status** using the get_project_status tool

For detailed documentation, see:
- [AI Engine Guide](AI_ENGINE_COMPREHENSIVE_GUIDE.md)
- [System Architecture](PM_AGENT_SYSTEM_ARCHITECTURE.md)
- [API Reference](../src/README.md)