# Quick Start Guide - Marcus Visualization Dashboard

## 🎯 Goal
Visualize your Marcus multi-agent system in action with live data or demonstration data.

## 📋 Prerequisites
- Marcus installed and working
- Node.js 18+ installed
- Python dependencies installed

## 🚀 5-Minute Quick Start

### Step 1: Start the Backend Server

Open a terminal in Marcus root directory:

```bash
# Make sure you're in Marcus root (not viz_backend)
cd /path/to/marcus

# Start the backend (it will find an available port automatically)
python -m viz_backend.run_server
```

You'll see:
```
🚀 Starting Marcus Viz Backend on http://localhost:4300
📊 API Documentation: http://localhost:4300/docs
✅ Health Check: http://localhost:4300/health

💡 Update your frontend .env to: VITE_API_URL=http://localhost:4300
```

**Keep this terminal open!** The server needs to stay running.

### Step 2: Start the Frontend Dashboard

Open a **NEW terminal** and navigate to the dashboard:

```bash
cd /path/to/marcus/viz-dashboard

# First time only: install dependencies
npm install

# Start the dashboard
npm run dev
```

The dashboard will open at: **http://localhost:5173**

### Step 3: View Your Data

The dashboard opens automatically in your browser. You'll see:

**Header Controls:**
- **🔵 Mock Data** button - Currently showing demonstration data
- **🔄 Refresh** button - Reload data from backend

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
3. Dashboard loads your actual data from:
   - Tasks from `data/marcus_state/projects.json`
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

As your agents work:
1. Click **🔄 Refresh** button to reload latest data
2. See updated task statuses, new messages, etc.

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

### "Failed to fetch data from API"
**Problem**: Backend server not running or wrong port

**Solution**:
1. Check backend terminal is still running
2. Look for the port number it shows (e.g., 4300)
3. Create `viz-dashboard/.env`:
   ```
   VITE_API_URL=http://localhost:4300
   ```
4. Restart frontend: `Ctrl+C` then `npm run dev`

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
**Solution**: Click **🔄 Refresh** button to reload

### Port 4300 already in use
**No problem!** The backend auto-finds the next available port (4301, 4302, etc.)
Just update your `.env` to match what the backend shows.

## 💡 Tips

1. **Start with Mock Data**: Explore features with demonstration data first
2. **Generate Sample Data**: Use Marcus CLI to create realistic scenarios
3. **Use Refresh**: After agents complete tasks, refresh to see updates
4. **Try Playback**: Use the timeline controls to "replay" project execution
5. **Compare Modes**: Toggle between Live and Mock to see the difference

## 🔗 Useful URLs

Once everything is running:
- **Dashboard**: http://localhost:5173
- **API Health**: http://localhost:4300/health
- **API Docs**: http://localhost:4300/docs
- **All Data**: http://localhost:4300/api/data

## 📝 Summary

**To see live data:**
1. ✅ Start backend: `python -m viz_backend.run_server`
2. ✅ Start frontend: `cd viz-dashboard && npm run dev`
3. ✅ Generate data: Run Marcus projects with agents
4. ✅ Switch mode: Click **🔵 Mock Data** → **🟢 Live Data**
5. ✅ Explore: Use the three visualization views
6. ✅ Refresh: Click **🔄** to see latest updates

**That's it!** You're now visualizing Marcus multi-agent parallelization! 🎉
