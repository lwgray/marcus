# Marcus Visualization Dashboard - Setup Guide

Complete guide for setting up and running the Marcus visualization dashboard with live or mock data.

## Architecture Overview

```
┌─────────────────────┐
│   viz-dashboard     │  React/TypeScript Frontend
│   (Port 5173)       │  Network Graph, Swim Lanes, Conversations
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   viz_backend       │  FastAPI Backend
│   (Port 8000)       │  Data transformation & API
└──────────┬──────────┘
           │ File I/O
           ▼
┌─────────────────────┐
│  Marcus Data Layer  │  Persistence, Logs, Experiments
│  - data/            │  • projects.json (tasks)
│  - logs/            │  • conversations/*.jsonl
│  - mlruns/          │  • agent_events/*.jsonl
└─────────────────────┘
```

## Prerequisites

- **Node.js**: 18+ with npm
- **Python**: 3.9+ with pip
- **Marcus**: Running instance with data (or use mock mode)

## Quick Start (5 minutes)

### 1. Install Frontend Dependencies
```bash
cd viz-dashboard
npm install
```

### 2. Install Backend Dependencies
```bash
cd ../viz_backend
pip install -r requirements.txt
```

### 3. Start Backend Server
```bash
# From viz_backend directory
python run_server.py

# Server starts on http://localhost:8000
```

### 4. Start Frontend Development Server
```bash
# From viz-dashboard directory (new terminal)
npm run dev

# Dashboard opens at http://localhost:5173
```

### 5. Choose Data Mode

The dashboard has two modes:

**Mock Mode** (default):
- Uses generated demonstration data
- Works immediately without Marcus data
- Shows 5 agents, 10 tasks, 50+ messages

**Live Mode**:
- Fetches real data from Marcus backend
- Requires Marcus to have run projects
- Shows actual agent work and communication

Toggle between modes using the button in the header: `🔵 Mock Data` / `🟢 Live Data`

## Configuration

### Frontend (.env)

Create `viz-dashboard/.env`:
```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# Default data mode: 'mock' or 'live'
VITE_DATA_MODE=mock
```

### Backend (Auto-detection)

The backend automatically detects Marcus root and finds data sources:
- `data/marcus_state/projects.json` - Task data
- `logs/conversations/*.jsonl` - Conversation logs
- `logs/agent_events/*.jsonl` - Event logs
- `mlruns/` - Experiment tracking

No configuration needed unless using custom paths.

## Using Live Data

### Step 1: Generate Marcus Data

Run a Marcus project to generate data:

```bash
# From Marcus root
./marcus

# In Marcus, create and run a project
> create_project "Test Viz Project"
> register_agent my_agent "Developer" python,api
> request_next_task my_agent
# ... work on tasks ...
```

This creates:
- Tasks in `data/marcus_state/projects.json`
- Messages in `logs/conversations/conversations_YYYYMMDD.jsonl`
- Events in `logs/agent_events/agent_events_YYYYMMDD.jsonl`

### Step 2: Start Backend with Live Data

```bash
cd viz_backend
python run_server.py
```

Verify data is loading:
```bash
curl http://localhost:8000/api/tasks
# Should return JSON with tasks
```

### Step 3: Switch Dashboard to Live Mode

1. Open dashboard at `http://localhost:5173`
2. Click `🔵 Mock Data` button in header
3. Switches to `🟢 Live Data` and fetches from backend
4. Use `🔄 Refresh` button to reload live data

### Step 4: Explore Your Data

- **Network Graph**: See task dependencies and relationships
- **Swim Lanes**: Watch agent timeline and parallelization
- **Conversations**: Read actual Marcus ↔ Agent messages
- **Metrics Panel**: View autonomy scores, speedup factor

## Data Mapping

### What Gets Visualized

| Marcus Source | Visualization | Features |
|--------------|---------------|----------|
| `projects.json` tasks | Network nodes, Swim lane bars | Status, dependencies, progress |
| `conversations/*.jsonl` | Conversation threads | Message types, response times |
| `agent_events/*.jsonl` | Timeline markers | Agent actions, state changes |
| `mlruns/` experiments | Agent profiles | Skills, roles, autonomy |
| Task assignments | Current work | Active tasks per agent |

### Calculated Metrics

The dashboard calculates:
- **Speedup Factor**: Multi-agent vs sequential execution time
- **Autonomy Scores**: Based on questions/blockers per task
- **Parallelization Level**: Max concurrent tasks
- **Completion Rates**: Tasks done / total tasks
- **Response Times**: Marcus reply speed to questions

## Troubleshooting

### Backend Issues

**Problem**: `ImportError: No module named 'viz_backend'`
```bash
# Ensure you're in Marcus root
cd /path/to/marcus

# Install from Marcus root
pip install -r viz_backend/requirements.txt
```

**Problem**: `No data returned from /api/tasks`
```bash
# Check if Marcus data exists
ls data/marcus_state/projects.json
ls logs/conversations/
ls logs/agent_events/

# If empty, run a Marcus project first
```

**Problem**: `CORS error in browser console`
```bash
# Check backend is running on port 8000
curl http://localhost:8000/health

# Verify frontend URL is in allowed origins (api.py)
# Default: localhost:3000, localhost:5173
```

### Frontend Issues

**Problem**: `Failed to fetch data from API`
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check API URL in .env
echo $VITE_API_URL  # Should be http://localhost:8000

# 3. Try mock mode first
# Click "🟢 Live Data" to switch to "🔵 Mock Data"
```

**Problem**: `npm install` fails
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

**Problem**: Dashboard shows but graphs don't render
```bash
# Check browser console for errors
# Common issue: D3.js version conflict

# Reinstall
npm install d3@7
```

### Data Quality Issues

**Problem**: No agents showing in live mode
- **Cause**: No tasks assigned to agents
- **Fix**: Run `request_next_task <agent_id>` in Marcus to assign work

**Problem**: No messages in conversation view
- **Cause**: Marcus not logging conversations
- **Fix**: Check `logs/conversations/` exists and has `.jsonl` files with content

**Problem**: Incorrect task statuses
- **Cause**: Stale data in persistence
- **Fix**: Click `🔄 Refresh` button or restart backend

## Advanced Usage

### Custom Backend Port

```bash
# In viz_backend/run_server.py, change:
uvicorn.run(app, host="0.0.0.0", port=9000)  # Custom port

# Update frontend .env:
VITE_API_URL=http://localhost:9000
```

### Filter by Project

```bash
# Backend API supports project filtering
curl "http://localhost:8000/api/data?project_id=my-project-123"

# Frontend: Will be added in next version
```

### Export Data

```bash
# Save current state to JSON
curl http://localhost:8000/api/data > marcus_snapshot.json

# Load in dashboard (future feature)
```

### Real-time Updates

Currently uses manual refresh. WebSocket support coming soon:
- Auto-refresh every N seconds
- Live agent status changes
- Real-time message streaming

## Development

### Adding Custom Visualizations

1. Create component in `viz-dashboard/src/components/`
2. Access data from store: `useVisualizationStore()`
3. Add to `App.tsx` as new layer
4. Style in component CSS file

Example:
```typescript
import { useVisualizationStore } from '../store/visualizationStore';

function MyCustomView() {
  const data = useVisualizationStore((state) => state.data);
  const tasks = data.tasks;

  return (
    <div>
      <h2>Custom View</h2>
      {tasks.map(task => <div key={task.id}>{task.name}</div>)}
    </div>
  );
}
```

### Adding Backend Endpoints

1. Add function to `viz_backend/api.py`:
```python
@app.get("/api/custom")
async def get_custom_data():
    # Your logic
    return {"data": "..."}
```

2. Add service function to `viz-dashboard/src/services/dataService.ts`:
```typescript
export async function fetchCustomData() {
  const response = await fetch(`${API_BASE_URL}/api/custom`);
  return await response.json();
}
```

3. Use in component:
```typescript
import { fetchCustomData } from '../services/dataService';

// In component
const data = await fetchCustomData();
```

## Performance Tips

### Backend Optimization

- **Caching**: Data is loaded fresh on each request. Add caching for large datasets.
- **Pagination**: API returns all data. Add `limit` and `offset` for large projects.
- **Filtering**: Use `project_id` parameter to load only relevant data.

### Frontend Optimization

- **Large graphs**: Network graph slows with 100+ nodes. Consider filtering.
- **Playback speed**: Use slower speed (0.5x) for large timelines.
- **Message filtering**: Filter by agent or task to reduce rendered messages.

## Production Deployment

### Backend (Docker)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY viz_backend/ ./viz_backend/
COPY data/ ./data/
COPY logs/ ./logs/
RUN pip install -r viz_backend/requirements.txt
CMD ["python", "viz_backend/run_server.py"]
```

### Frontend (Static Build)

```bash
# Build for production
cd viz-dashboard
npm run build

# Serve with nginx, Apache, or static host
# Output in viz-dashboard/dist/
```

### Environment Variables

Production `.env`:
```bash
VITE_API_URL=https://api.yourdomain.com
VITE_DATA_MODE=live
```

## Next Steps

1. **Explore Mock Data**: Understand features with demonstration data
2. **Run Marcus Projects**: Generate real data to visualize
3. **Switch to Live Mode**: See actual agent work patterns
4. **Analyze Metrics**: Study parallelization and autonomy
5. **Export Insights**: Use findings to optimize Marcus configuration

## Support

- **Issues**: Report at GitHub repository
- **Docs**: See `viz_backend/README.md` and `viz-dashboard/README.md`
- **Examples**: Check `examples/` directory in Marcus root

## License

Part of the Marcus project. See root LICENSE file.
