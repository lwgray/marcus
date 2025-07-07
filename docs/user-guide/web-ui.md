# Marcus Web UI Dashboard

Marcus includes an integrated web UI dashboard for monitoring projects, managing agents, and tracking costs in real-time.

## Starting Marcus

### Quick Start

```bash
# Start Marcus (web UI enabled by default)
./marcus
```

The web UI will be available at: http://localhost:5000

### Command Line Options

```bash
# Start on custom port
./marcus --port 8080

# Start without web UI (MCP server only)
./marcus --no-web

# View all options
./marcus --help
```

## Features

### 1. Real-Time Cost Tracking

The web UI now tracks actual AI token usage instead of naive hourly estimates:

- **Total Tokens Used**: Exact count of input/output tokens
- **Actual Cost**: Based on real token consumption ($0.03/1K tokens)
- **Current Burn Rate**: Tokens consumed per hour
- **Cost Projections**: Estimated total cost based on current usage
- **Variance Analysis**: Compare actual vs naive estimates

### 2. Project Management

- Create projects from natural language descriptions
- Use pre-defined sample projects for quick testing
- Monitor project progress in real-time
- View AI-analyzed requirements and task breakdowns

### 3. Agent Management

- Register and monitor coding agents
- View agent status and current assignments
- Trigger task requests and updates
- Track agent performance metrics

### 4. Pipeline Monitoring

- Live pipeline execution monitoring
- Health status tracking
- System metrics and alerts
- Flow visualization

## Configuration

To disable the web UI by default, add to `marcus.config.json`:

```json
{
  "advanced": {
    "web_ui_enabled": false,
    "web_ui_port": 5000
  }
}
```

## API Endpoints

The web UI exposes several REST APIs:

### Cost Tracking
- `GET /api/costs/project/{project_id}` - Get project cost details
- `GET /api/costs/summary` - Get all projects cost summary
- `GET /api/costs/live-feed` - Live token usage feed

### Project Management
- `POST /api/projects/create` - Create new project
- `GET /api/projects/list` - List all projects
- `POST /api/projects/{id}/workflow/start` - Start project workflow

### Agent Management
- `POST /api/agents/register` - Register new agent
- `GET /api/agents/list` - List all agents
- `GET /api/agents/{id}/status` - Get agent status

## Security Considerations

The web UI binds to all interfaces (0.0.0.0) by default. For production:

1. Use a reverse proxy (nginx, Apache)
2. Enable authentication
3. Use HTTPS
4. Restrict to localhost only:
   ```bash
   python marcus.py --with-web --web-host 127.0.0.1
   ```

## Troubleshooting

### Port Already in Use
```bash
# Kill existing processes
pkill -f "python.*src.api.app"

# Or use a different port
python marcus.py --with-web --web-port 8080
```

### Vue.js Errors
The dashboard uses Vue.js 3. If you see template errors:
1. Clear browser cache
2. Reload the page
3. Check browser console for details

### No Cost Data Showing
Cost tracking only shows data when AI calls are made:
1. Create a project
2. Start the workflow
3. Register agents
4. Have agents request tasks

This will trigger AI API calls that consume tokens.