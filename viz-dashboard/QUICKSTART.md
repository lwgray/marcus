# Quick Start Guide - Marcus Visualization Dashboard

## 🎯 Goal
Visualize your Marcus multi-agent system in action with live data or demonstration data.

## 📋 Prerequisites
- Marcus installed and working
- Node.js 18+ installed
- Python dependencies installed

## 🚀 2-Minute Quick Start (Automatic - Recommended)

### Single Command to Start Everything

Open a terminal in Marcus root directory:

```bash
# Make sure you're in Marcus root (not viz_backend)
cd /path/to/marcus

# Start both backend AND frontend automatically!
python -m viz_backend.run_server
```

That's it! The server will:
- ✅ Find an available port (4300-4309)
- ✅ Auto-configure the frontend .env file
- ✅ Auto-install npm dependencies (first time only)
- ✅ Auto-start the viz-dashboard
- ✅ Open your browser to http://localhost:5173

You'll see:
```
============================================================
🚀 Starting Marcus Viz Backend on http://localhost:4300
📊 API Documentation: http://localhost:4300/docs
✅ Health Check: http://localhost:4300/health
============================================================
✅ Updated viz-dashboard/.env with VITE_API_URL=http://localhost:4300
🚀 Starting viz-dashboard frontend...
✅ Frontend started successfully
📱 Dashboard should open at: http://localhost:5173
============================================================
🎉 Full stack running:
   Backend:  http://localhost:4300
   Frontend: http://localhost:5173
============================================================

Press Ctrl+C to stop all services
```

**Press Ctrl+C once to stop both services** - no need to manage multiple terminals!

## 🔧 Manual Mode (Advanced)

If you prefer to start services separately:

```bash
# Start ONLY the backend (no frontend auto-start)
python -m viz_backend.run_server --no-frontend
```

Then in another terminal:
```bash
cd /path/to/marcus/viz-dashboard
npm run dev
```

## 📊 Using the Dashboard

The dashboard opens automatically in your browser at http://localhost:5173. You'll see:

**Header Controls:**
- **Project Selector** (Live mode only) - Choose which project to visualize
- **🔵 Mock Data / 🟢 Live Data** button - Toggle between demonstration and real data
- **🔄 Auto (5s) / ⏸️ Manual** button (Live mode only) - Auto-refresh every 5 seconds or manual only
- **🔄 Refresh Now** button - Manually reload data from backend

**Three Visualization Tabs:**
1. **🔗 Network Graph** - Task dependencies as a node graph
2. **📊 Agent Swim Lanes** - Timeline showing agents working in parallel
3. **💬 Conversations** - Messages between Marcus and agents

**Metrics Panel (Right Side):**
- Project overview
- Parallelization speedup (e.g., "5.5x faster than single agent")
- Agent autonomy scores
- Communication metrics

## 🟢 Switching to Live Data

By default, the dashboard shows **mock data** (demonstration data). To see your actual Marcus data:

### Option A: If You Already Have Marcus Data

If you've run Marcus projects before, you already have data! Just:

1. Click the **🔵 Mock Data** button in the header
2. It switches to **🟢 Live Data**
3. Select a project from the dropdown (defaults to most recent)
4. Dashboard auto-refreshes every 5 seconds (toggle with Auto button)
5. Data loaded from:
   - Tasks from `data/marcus_state/subtasks.json`
   - Projects from `data/marcus_state/projects.json`
   - Messages from `logs/conversations/*.jsonl`
   - Events from `logs/agent_events/*.jsonl`

### Option B: Generate Fresh Data

If you don't have data yet, or want fresh data to visualize:

**Open a THIRD terminal** and run Marcus:

```bash
cd /path/to/marcus
./marcus
```

In the Marcus CLI, create a sample project:

```python
# 1. Create a project
> create_project(
    "Test Visualization Project",
    {
        "id": "test-viz-001",
        "name": "Test Visualization Project",
        "description": "Sample project to test the visualization dashboard"
    }
)

# 2. Register an agent
> register_agent(
    agent_id="viz_agent_1",
    name="Visualization Test Agent",
    role="Backend Developer",
    skills=["python", "api", "database"]
)

# 3. Create some tasks manually or request work
> request_next_task("viz_agent_1")

# 4. Report progress (simulate agent working)
> report_task_progress(
    agent_id="viz_agent_1",
    task_id="<task_id_from_step_3>",
    progress=50,
    status="in_progress",
    message="Working on implementation"
)

# 5. Create another agent for parallel work
> register_agent(
    agent_id="viz_agent_2",
    name="Frontend Test Agent",
    role="Frontend Developer",
    skills=["react", "typescript", "ui"]
)

> request_next_task("viz_agent_2")
```

Now you have real Marcus data!

**Switch to live data:**
1. Go back to the dashboard (http://localhost:5173)
2. Click **🔵 Mock Data** → it changes to **🟢 Live Data**
3. See your actual agents and tasks!

## 🔄 Refreshing Live Data

The dashboard now **automatically refreshes** when in Live Data mode!

**Automatic Mode (Recommended):**
- Enabled by default when you switch to Live Data
- Polls for updates every 5 seconds
- Green pulsing **🔄 Auto (5s)** button indicates active
- Dashboard stays current as agents work

**Manual Mode:**
- Click **🔄 Auto (5s)** to switch to **⏸️ Manual** mode
- Click **🔄 Refresh Now** to manually reload
- Use this if you don't want automatic polling

## 📊 What You'll See

### With Mock Data (Default)
- **5 demonstration agents** with different skills
- **10 tasks** showing realistic dependencies
- **50+ messages** showing conversations
- **5.5x parallelization speedup**
- 220 minutes of simulated work

### With Your Live Data
- **Your actual registered agents**
- **Your real project tasks** with current statuses
- **Actual conversations** between Marcus and your agents
- **Real parallelization metrics** from your projects
- **Autonomy scores** showing which agents ask more questions

## 🎮 Exploring the Dashboard

### Network Graph View
- **Nodes** = Tasks (color shows status)
  - 🟦 Blue = TODO
  - 🟨 Yellow = IN_PROGRESS
  - 🟩 Green = DONE
  - 🟥 Red = BLOCKED
- **Edges** = Dependencies (arrows show "depends on")
- **Click a node** to see task details on right
- **Drag to pan**, **scroll to zoom**

### Agent Swim Lanes View
- **Horizontal bars** = Time agents spend on tasks
- **Swim lanes** = One row per agent
- **Timeline** = Project duration
- **Overlapping bars** = Parallelization in action!
- **Click Play** ▶️ to watch timeline animate

### Conversations View
- **Thread view** of all messages
- **Message types**:
  - 📋 Instructions from Marcus
  - ❓ Questions from agents
  - ✅ Status updates
  - 🚫 Blockers
  - 💬 Answers
- **Filter by agent or task**

### Metrics Panel
- **Speedup Factor**: How much faster with multiple agents
- **Task Completion**: Progress statistics
- **Autonomy Scores**:
  - High score = agent works independently
  - Low score = asks many questions
- **Communication Metrics**: Questions, blockers, response times

## 🛠️ Troubleshooting

### Frontend doesn't auto-start
**Problem**: npm not found or Node.js not installed

**Solution**:
1. Install Node.js 18+ from https://nodejs.org
2. Or start manually: `cd viz-dashboard && npm run dev`
3. Or use `--no-frontend` flag and start separately

### "Failed to fetch data from API"
**Problem**: Backend server not running

**Solution**:
1. The .env file is now auto-configured, so this shouldn't happen
2. If it does, check the backend terminal is still running
3. Look for the port number (e.g., 4300)
4. The dashboard should have auto-configured to that port

### "No agents showing in live mode"
**Problem**: No Marcus data exists yet

**Solution**: Either:
- Click **🔵 Mock Data** to see demonstration
- Or generate data using Marcus CLI (see "Generate Fresh Data" above)

### Backend shows "No module named 'viz_backend'"
**Problem**: Running from wrong directory

**Solution**:
```bash
# Must be in Marcus root, not viz_backend folder
cd /path/to/marcus  # (not /path/to/marcus/viz_backend)
python -m viz_backend.run_server
```

### Dashboard shows old data after changes
**Solution**:
1. Auto-refresh should update every 5 seconds automatically
2. Or click **🔄 Refresh Now** to reload immediately
3. Check that auto-refresh is enabled (green **🔄 Auto (5s)** button)

### Port 4300 already in use
**No problem!** The backend auto-finds the next available port (4301, 4302, etc.) and automatically configures the frontend .env file. No manual configuration needed!

## 💡 Tips

1. **One Command to Rule Them All**: Just run `python -m viz_backend.run_server` - everything else is automatic!
2. **Start with Mock Data**: Explore features with demonstration data first
3. **Filter by Project**: Use the project dropdown to focus on specific work
4. **Auto-refresh is Your Friend**: Leave it on to watch agents work in real-time
5. **Generate Sample Data**: Use Marcus CLI to create realistic scenarios
6. **Try Playback**: Use the timeline controls to "replay" project execution
7. **Compare Modes**: Toggle between Live and Mock to see the difference

## 🔗 Useful URLs

Once everything is running:
- **Dashboard**: http://localhost:5173
- **API Health**: http://localhost:4300/health
- **API Docs**: http://localhost:4300/docs
- **All Data**: http://localhost:4300/api/data

## 📝 Summary

**Simplified Workflow:**
1. ✅ Run ONE command: `python -m viz_backend.run_server`
2. ✅ Dashboard opens automatically at http://localhost:5173
3. ✅ Generate data: Run Marcus projects with agents
4. ✅ Switch mode: Click **🔵 Mock Data** → **🟢 Live Data**
5. ✅ Select project: Use dropdown to filter (defaults to most recent)
6. ✅ Watch in real-time: Auto-refresh updates every 5 seconds
7. ✅ Explore: Use the three visualization views

**Press Ctrl+C to stop everything** - both backend and frontend shut down cleanly!

**That's it!** You're now visualizing Marcus multi-agent parallelization! 🎉
