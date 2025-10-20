# Marcus Visualization Backend

FastAPI backend that serves Marcus data to the visualization dashboard.

## Overview

The viz_backend package reads data from Marcus' persistence layer and logs, transforming it into a format consumable by the viz-dashboard frontend. It provides REST API endpoints for:

- **Tasks**: Load tasks from `data/marcus_state/projects.json`
- **Messages**: Parse conversation logs from `logs/conversations/*.jsonl`
- **Events**: Parse agent events from `logs/agent_events/*.jsonl`
- **Agents**: Infer agent profiles from MLflow experiments, assignments, tasks, and messages
- **Metadata**: Calculate project metrics and timelines

## Installation

```bash
# Install dependencies (if not already installed)
pip install fastapi uvicorn[standard] aiofiles python-dateutil
```

## Running the Server

**IMPORTANT**: The server must be run from the Marcus root directory, not from within viz_backend/

### Method 1: Using the convenience script (Recommended)
```bash
# From anywhere in Marcus
./viz_backend/start_server.sh
```

### Method 2: As a Python module
```bash
# From Marcus root
python -m viz_backend.run_server
```

### Method 3: Direct uvicorn
```bash
# From Marcus root
uvicorn viz_backend.api:app --host 0.0.0.0 --port 4300 --reload
```

The server will:
- Auto-detect an available port (starting from 4300)
- Display helpful startup information
- Show the URL for your frontend .env configuration

Example output:
```
🚀 Starting Marcus Viz Backend on http://localhost:4300
📊 API Documentation: http://localhost:4300/docs
✅ Health Check: http://localhost:4300/health

💡 Update your frontend .env to: VITE_API_URL=http://localhost:4300
```

## Architecture

```
Marcus Root
├── data/
│   ├── marcus_state/
│   │   └── projects.json          # Task data source
│   └── assignments/
│       └── assignments.json        # Agent assignment tracking
├── logs/
│   ├── conversations/
│   │   └── *.jsonl                 # Message data source
│   └── agent_events/
│       └── *.jsonl                 # Event data source
├── mlruns/                         # Experiment tracking (agent profiles)
└── viz_backend/
    ├── data_loader.py              # Data transformation logic
    ├── api.py                      # FastAPI endpoints
    ├── run_server.py               # Server launcher
    └── start_server.sh             # Convenience script
```

## Data Sources Mapped

The MarcusDataLoader integrates multiple Marcus data sources:

### 1. Task Persistence (`data/marcus_state/projects.json`)
- Task definitions with status, priorities, dependencies
- Project metadata and organization
- Task completion tracking

### 2. Conversation Logs (`logs/conversations/*.jsonl`)
- Worker-to-Marcus conversations
- Progress updates and status reports
- Questions, blockers, and resolutions
- Decision tracking

### 3. Agent Events (`logs/agent_events/*.jsonl`)
- Worker registrations
- Task assignments and completions
- System events and state changes

### 4. MLflow Experiments (`mlruns/`)
- Agent profiles with skills and roles
- Performance metrics and scores
- Experiment metadata and artifacts

### 5. Assignment Persistence (`data/assignments/`)
- Current task assignments
- Assignment history and tracking
- Worker allocation data

## API Endpoints

### GET /
Root endpoint with API information and status

### GET /health
Health check endpoint

### GET /api/data
Get all simulation data (tasks, agents, messages, events, metadata)

**Query Parameters:**
- `project_id` (optional): Filter by specific project

**Response:**
```json
{
  "tasks": [...],
  "agents": [...],
  "messages": [...],
  "events": [...],
  "metadata": {...}
}
```

### GET /api/tasks
Get tasks from Marcus persistence

**Query Parameters:**
- `project_id` (optional): Filter by specific project

### GET /api/agents
Get agents inferred from tasks and messages

**Query Parameters:**
- `project_id` (optional): Filter by specific project

### GET /api/messages
Get conversation messages from Marcus logs

### GET /api/events
Get agent events from Marcus logs

### GET /api/metadata
Get project metadata and metrics

**Query Parameters:**
- `project_id` (optional): Calculate for specific project

## Testing the API

```bash
# Health check
curl http://localhost:4300/health

# Get all data
curl http://localhost:4300/api/data

# Get tasks for specific project
curl "http://localhost:4300/api/tasks?project_id=proj-123"

# Get agents
curl http://localhost:4300/api/agents
```

## Interactive API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:4300/docs`
- ReDoc: `http://localhost:4300/redoc`

## CORS Configuration

By default, the API allows requests from:
- `http://localhost:3000` (React default)
- `http://localhost:5173` (Vite default)
- `http://127.0.0.1:3000`
- `http://127.0.0.1:5173`

To add more origins, edit `api.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://your-domain.com"],
    ...
)
```

## Troubleshooting

### ModuleNotFoundError: No module named 'viz_backend'

**Problem**: Running from wrong directory
```bash
# ❌ Wrong - from viz_backend directory
cd viz_backend
python run_server.py  # This will fail

# ✅ Correct - from Marcus root
cd /path/to/marcus
python -m viz_backend.run_server
```

**Solution**: Always run from Marcus root directory using one of:
- `./viz_backend/start_server.sh`
- `python -m viz_backend.run_server`

### No data returned from /api/tasks

**Problem**: Marcus has not generated any data yet

**Solution**: Run a Marcus project first to generate data:
```bash
./marcus
> create_project "Test Project"
> register_agent test_agent "Developer" python,api
> request_next_task test_agent
```

### Port already in use

**Solution**: The server will automatically try ports 4300-4309. If all are in use:
1. Stop other services using those ports
2. Or modify `start_port` in `run_server.py`

### CORS errors in browser console

**Problem**: Frontend running on unexpected port

**Solution**: Add your frontend URL to `allow_origins` in `api.py`

## Development

### Adding New Endpoints

1. Add function to `viz_backend/api.py`:
```python
@app.get("/api/custom")  # type: ignore[misc]
async def get_custom_data() -> Dict[str, Any]:
    # Your logic
    return {"data": "..."}
```

2. Update frontend service if needed

### Testing Changes

The server runs with auto-reload enabled by default. Simply edit files and save - changes will be automatically reloaded.

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Database backend option (SQLite/PostgreSQL)
- [ ] Caching layer for expensive queries
- [ ] Authentication and authorization
- [ ] Rate limiting
- [ ] Prometheus metrics export

## License

Part of the Marcus project. See root LICENSE file.
