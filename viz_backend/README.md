# Marcus Visualization Backend

FastAPI backend that serves Marcus data to the visualization dashboard.

## Overview

The viz_backend package reads data from Marcus' persistence layer and logs, transforming it into a format consumable by the viz-dashboard frontend. It provides REST API endpoints for:

- **Tasks**: Load tasks from `data/marcus_state/projects.json`
- **Messages**: Parse conversation logs from `logs/conversations/*.jsonl`
- **Events**: Parse agent events from `logs/agent_events/*.jsonl`
- **Agents**: Infer agent profiles from MLflow experiments, assignments, tasks, and messages
- **Metadata**: Calculate project metrics and timelines

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
    └── run_server.py               # Server launcher
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

## Installation

```bash
# Install dependencies
pip install -r viz_backend/requirements.txt

# Or if requirements are already in project root:
pip install fastapi uvicorn[standard] aiofiles python-dateutil
```

## Running the Server

### Method 1: Direct Python
```bash
python viz_backend/run_server.py
```

### Method 2: Uvicorn Command
```bash
uvicorn viz_backend.api:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: From API Module
```bash
python -m viz_backend.api
```

The server will start on `http://localhost:8000`

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

## Data Transformation

### Task Format
Marcus persistence → Viz format:
```python
{
    "id": str,
    "name": str,
    "description": str,
    "status": "todo" | "in_progress" | "done" | "blocked",
    "priority": "low" | "medium" | "high" | "urgent",
    "assigned_to": str | null,
    "created_at": ISO datetime,
    "updated_at": ISO datetime,
    "estimated_hours": float,
    "actual_hours": float,
    "dependencies": [str],
    "labels": [str],
    "project_id": str,
    "project_name": str,
    "progress": int (0-100)
}
```

### Message Format
Conversation logs → Viz format:
```python
{
    "id": str,
    "timestamp": ISO datetime,
    "from": str,  # agent_id or "marcus"
    "to": str,
    "task_id": str | null,
    "message": str,
    "type": "instruction" | "question" | "answer" | "status_update" | "blocker",
    "parent_message_id": str | null,
    "metadata": {
        "progress": int,
        "blocking": bool,
        "response_time": int (seconds)
    }
}
```

### Agent Format
Inferred from multiple sources:
```python
{
    "id": str,
    "name": str,
    "role": str,
    "skills": [str],
    "current_tasks": [str],
    "completed_tasks_count": int,
    "capacity": int,
    "performance_score": float,
    "autonomy_score": float (0-1)
}
```

## Development

### Adding New Data Sources

1. Add loading method to `MarcusDataLoader`:
```python
def load_new_source(self) -> List[Dict[str, Any]]:
    """Load from new Marcus data source."""
    # Implementation
```

2. Update `load_all_data()` to include new source
3. Add API endpoint in `api.py` if needed
4. Update frontend to consume new data

### Testing the API

```bash
# Health check
curl http://localhost:8000/health

# Get all data
curl http://localhost:8000/api/data

# Get tasks for specific project
curl "http://localhost:8000/api/tasks?project_id=proj-123"

# Get agents
curl http://localhost:8000/api/agents
```

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

### No data returned
- Check that Marcus has generated data in `data/marcus_state/projects.json`
- Verify logs exist in `logs/conversations/` and `logs/agent_events/`
- Run a Marcus project first to generate data

### CORS errors in browser
- Ensure frontend is running on an allowed origin
- Check browser console for specific CORS error
- Add your frontend URL to `allow_origins` in `api.py`

### Import errors
- Ensure you're running from Marcus root directory
- Install all dependencies: `pip install -r viz_backend/requirements.txt`
- Check Python path includes Marcus root

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Database backend option (SQLite/PostgreSQL)
- [ ] Caching layer for expensive queries
- [ ] GraphQL API alternative
- [ ] Authentication and authorization
- [ ] Rate limiting and API keys
- [ ] Prometheus metrics export
- [ ] OpenAPI/Swagger UI improvements
