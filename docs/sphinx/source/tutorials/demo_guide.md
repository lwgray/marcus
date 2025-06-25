# Marcus Demo Guide

This guide explains how to run demonstrations of Marcus with mock Claude workers, showing the detailed conversation and decision-making process between Workers, Marcus, and the Kanban Board.

## Available Demo Scripts

### 1. **Basic Mock Worker** (`scripts/mock_claude_worker.py`)
- Simple worker simulation
- Minimal output
- Good for testing basic functionality

### 2. **Verbose Mock Worker** (`scripts/mock_claude_worker_verbose.py`)
- Detailed conversation logging
- Shows worker "thinking" process
- Rich terminal output with colors
- Personality traits for realistic behavior

### 3. **Test Conversation** (`scripts/test_conversation.py`)
- Simple test to verify conversation flow
- No external dependencies
- Good for understanding the communication pattern

### 4. **Full Demo Runner** (`scripts/run_verbose_demo.py`)
- Orchestrates Marcus + Workers
- Optional screen recording
- Multiple demo presets

### 5. **Full Conversation Test** (`scripts/test_full_conversation.py`)
- Shows complete three-way conversation
- Worker ↔ Marcus ↔ Kanban Board
- Demonstrates all interaction patterns
- No external dependencies needed

### 6. **Conversation Flow Visualizer** (`scripts/visualize_conversation_flow.py`)
- Generates Mermaid diagrams
- Creates conversation examples
- Documents communication patterns

## Quick Start

### Test Basic Conversation
```bash
python scripts/test_conversation.py
```

This shows a simulated conversation between Marcus and a worker without needing the full system running.

### Run Single Verbose Worker
```bash
# Make sure Marcus is running first
python pm_agent_mcp_server.py

# In another terminal, run a worker
python scripts/mock_claude_worker_verbose.py
# Select worker 1, 2, or 3
```

### Run Full Demo with Recording

#### Prerequisites
1. **Planka running**: `docker-compose up -d`
2. **FFmpeg installed** (optional, for recording):
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`
3. **Python packages**: `pip install mcp rich requests`

#### Run Demo
```bash
python scripts/run_verbose_demo.py
```

Demo options:
- **Quick Demo**: 1 worker, 2 minutes
- **Standard Demo**: 2 workers, 5 minutes  
- **Full Demo**: 3 workers, 10 minutes
- **Custom**: Choose your own settings

## What You'll See

### Three-Way Conversation Flow

The system shows conversations between three components:

1. **Worker ↔ Marcus**
   - Workers request tasks and report progress
   - Marcus assigns tasks and provides guidance
   
2. **Marcus ↔ Kanban Board**  
   - PM queries available tasks and board state
   - PM updates task assignments and progress
   - Kanban returns task data and metrics

3. **Internal Processing**
   - Marcus thinking and decision logic
   - Kanban board processing operations

### Marcus Output
```
🧠 Marcus thinking: New agent wants to register: Claude Backend Dev
📋 PM Decision: Register Claude Backend Dev
   Reason: Skills match project requirements

🧠 Marcus thinking: Finding optimal task for agent
   Agent: claude-backend-001
   Skills: python, api, database, testing
   Available tasks: 5

📋 PM Decision: Assign task 'Implement user authentication' to claude-backend-001
   Reason: Best match for agent skills, Priority: high, Estimated: 4h
```

### Worker Output
```
💭 Claude Backend Dev thinking: Time to register with Marcus
📤 Claude Backend Dev → Marcus: Hello Marcus! I'm Claude Backend Dev...
📥 Marcus → Claude Backend Dev: Welcome! You're registered...

💭 Claude Backend Dev thinking: Let me check if there's any work for me
🔧 Claude Backend Dev action: Starting work on task
   'Implement user authentication'
```

### Kanban Board Interactions
```
🔌 Marcus → Kanban Board:
   Action: Get available tasks
   Criteria: Unassigned, in Backlog or Ready

🤔 Kanban processing: Searching for available tasks
   1. Scanning Backlog column
   2. Filtering unassigned tasks
   3. Sorting by priority

📋 Kanban Board → Marcus:
   Found: 3 available tasks
   • Implement user authentication (High priority)
   • Create API documentation (Medium priority)
```

### Conversation Flow
1. **Worker Registration**
   - Worker introduces itself with skills
   - Marcus evaluates and accepts
   
2. **Task Assignment**
   - Worker requests work
   - Marcus analyzes available tasks
   - Marcus assigns best match
   
3. **Progress Updates**
   - Worker reports progress at 25%, 50%, 75%, 100%
   - Marcus acknowledges and tracks
   
4. **Blocker Handling** (10% chance)
   - Worker reports blocker
   - Marcus provides solutions
   - Worker attempts resolution

## Screen Recording

### Automatic Recording (FFmpeg)
The demo scripts can automatically record your screen if FFmpeg is installed:
- Records full screen or specific window
- Saves to `recordings/` directory
- MP4 format with good compression

### Manual Recording Options
1. **macOS**: QuickTime Player → File → New Screen Recording
2. **Windows**: Windows + G (Game Bar)
3. **Linux**: OBS Studio or SimpleScreenRecorder
4. **Cross-platform**: OBS Studio (recommended for best quality)

### Recording Planka Board
To focus recording on Planka:
1. Open Planka in a browser window
2. Size the window to show all columns
3. Start recording before running workers
4. The board will show tasks moving through columns as workers process them

## Customizing the Demo

### Modify Worker Personalities
Edit `mock_claude_worker_verbose.py`:
```python
self.personality = {
    "thoroughness": 0.9,      # How detailed in work
    "communication": 0.8,     # How verbose in updates
    "problem_solving": 0.85,  # Ability to resolve blockers
    "blocker_tendency": 0.1   # Chance of hitting blockers
}
```

### Add Custom Tasks
Before running the demo, add tasks to your Planka board:
1. Create tasks in the Backlog column
2. Set priorities (High, Medium, Low)
3. Add labels for agent types (backend, frontend, etc.)
4. Workers will automatically pick up matching tasks

### Adjust Timing
In `mock_claude_worker_verbose.py`:
```python
# Change work speed (default: 2 seconds = 1 hour)
work_time = (estimated_hours * 0.25 * self.work_speed * 2)
```

## Troubleshooting

### Marcus Not Receiving Messages
- Check that Marcus is running: `ps aux | grep pm_agent`
- Verify MCP connection in logs
- Ensure Planka is accessible

### Workers Not Finding Tasks
- Verify tasks exist in Planka Backlog
- Check task labels match worker skills
- Ensure Marcus has board access

### Recording Issues
- **macOS**: Grant terminal permission for screen recording
- **FFmpeg errors**: Check device index with `ffmpeg -f avfoundation -list_devices true -i ""`
- **No video**: Try different screen index (0, 1, 2)

## Best Practices for Demos

1. **Prepare the Board**
   - Clear completed tasks
   - Add 5-10 demo tasks
   - Vary priorities and complexities

2. **Choose Demo Length**
   - Quick demo (2 min) for overview
   - Standard (5 min) for full workflow
   - Extended (10+ min) for multiple cycles

3. **Monitor Both Sides**
   - Keep Planka visible
   - Watch terminal output
   - Note conversation patterns

4. **Save Artifacts**
   - Recording videos
   - Console logs
   - `pm_agent_conversation.log`

## Example Demo Scenarios

### Scenario 1: Single Developer
```bash
# Add 3-5 backend tasks to Planka
# Run 1 backend worker for 5 minutes
# Shows focused task completion
```

### Scenario 2: Team Collaboration
```bash
# Add mixed tasks (backend, frontend, testing)
# Run all 3 workers for 10 minutes
# Shows task distribution and parallel work
```

### Scenario 3: Blocker Resolution
```bash
# Increase blocker_tendency to 0.3
# Run workers to see blocker handling
# Shows Marcus problem-solving
```

## Next Steps

After running demos, you can:
1. Analyze conversation logs for improvement
2. Test with real AI workers (Claude, GPT-4)
3. Customize Marcus decision logic
4. Add more sophisticated task routing

The demo system provides a foundation for testing and showcasing Marcus's autonomous project management capabilities!