# Complete Guide to Running Marcus Experiments with Real Claude Agents

This guide provides step-by-step instructions for running experiments with real Claude agents coordinated through Marcus MCP.

## Prerequisites

1. **Marcus Repository** cloned at `/Users/lwgray/dev/marcus`
2. **Kanban MCP** installed and ready
3. **Claude CLI** installed and working
4. **Git** configured on your system
5. **Python 3.8+** with required packages

## Step 1: Start Marcus MCP Server

Marcus coordinates all agents through the MCP interface.

```bash
# Terminal 1
cd /Users/lwgray/dev/marcus
python marcus_mcp_server.py
```

Expected output:
```
Starting Marcus MCP Server...
```

## Step 1b: Start Marcus Visualization UI (Optional but Recommended)

Marcus has a web UI for real-time visualization:

```bash
# Terminal 1b
cd /Users/lwgray/dev/marcus
python run_ui_server.py
```

Expected output:
```
============================================================
Marcus Visualization UI Server
============================================================

Starting server on http://localhost:8080

Features:
- Real-time agent conversation monitoring
- Decision visualization
- Knowledge graph
- System health metrics

Note: This UI is optional. Marcus works through MCP without it.

Press Ctrl+C to stop
============================================================
```

## Step 2: Start Kanban MCP Server

Marcus needs the Kanban board backend for task storage.

```bash
# Terminal 2
cd /Users/lwgray/dev/kanban-mcp
npm start
```

Expected output:
```
Kanban MCP server started...
```

## Step 3: Verify Marcus is Running

Open your browser and navigate to: **http://localhost:8080**

You should see the Marcus Visualization UI. If not, check troubleshooting section below.

Note: The UI is optional - Marcus works through MCP even without the web UI.

## Step 4: Create Tasks in Marcus

Before agents can work, they need tasks. In the Marcus UI:

1. Click "Create Task" or use the appropriate button
2. Add several tasks with descriptions like:
   - "Fix the bug in authentication module"
   - "Add unit tests for user service"
   - "Implement password reset feature"
   - "Optimize database queries"

## Step 5: Prepare a Test Repository

Create a repository for agents to work on:

```bash
# Terminal 3
mkdir -p /tmp/test-project
cd /tmp/test-project
git init
git config user.email "test@example.com"
git config user.name "Test User"

# Create some initial files
echo "# Test Project" > README.md
echo "def main():\n    print('Hello World')" > main.py
echo "# TODO: Add tests" > test_main.py

git add .
git commit -m "Initial commit"
```

## Step 6: Set Up Agent Worktrees

This creates isolated git worktrees for each agent:

```bash
# Still in Terminal 3
cd /Users/lwgray/dev/marcus/experiments

python scripts/run_real_agents.py \
  --source-repo /tmp/test-project \
  --workspace /tmp/agent-workspace \
  --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  --agents 2
```

**When you see "All agents have terminated"**, type `y` to keep worktrees for inspection.

This process:
- Creates `/tmp/agent-workspace/agent1` and `/tmp/agent-workspace/agent2`
- Sets up git branches `agent1-work` and `agent2-work`
- Creates `CLAUDE.md` in each worktree with agent instructions
- Configures MCP servers `marcus_agent1` and `marcus_agent2`

## Step 7: Launch Agents Manually

Now start each agent in its own terminal:

### Agent 1
```bash
# Terminal 4
cd /tmp/agent-workspace/agent1
claude
```

Wait for Claude to start, then type:
```
start work
```

### Agent 2
```bash
# Terminal 5
cd /tmp/agent-workspace/agent2
claude
```

Wait for Claude to start, then type:
```
start work
```

## Step 8: What Happens Next

Each agent will:

1. Read their `CLAUDE.md` file with instructions
2. Connect to Marcus MCP using `/mcp` command
3. Register with Marcus as an agent
4. Request their first task
5. Work on the task autonomously
6. Report progress (25%, 50%, 75%, 100%)
7. Commit changes to their branch
8. Request next task
9. Continue until no tasks remain

## Step 9: Monitor Progress

1. **Marcus UI** (http://localhost:8765):
   - See active agents
   - Watch task assignments
   - View progress reports
   - Check completion rates

2. **Agent Terminals**:
   - See real-time agent actions
   - Watch MCP tool calls
   - View any errors or blockers

3. **Git Repository**:
   ```bash
   cd /tmp/test-project
   git branch -a
   git log --oneline --graph --all
   ```

## Step 10: Collect Results

After agents complete their work:

1. **Check commits**:
   ```bash
   git log agent1-work
   git log agent2-work
   ```

2. **Review changes**:
   ```bash
   git diff main..agent1-work
   git diff main..agent2-work
   ```

3. **Export metrics** from Marcus UI

## Troubleshooting

### Marcus UI Not Loading (Port 8080)

1. **Check if Marcus is actually running**:
   ```bash
   ps aux | grep marcus_mcp_server
   ```

2. **Check if UI server is running**:
   ```bash
   ps aux | grep ui_server
   ```

3. **Check if port is in use**:
   ```bash
   lsof -i :8080
   ```

3. **Check Marcus logs** in Terminal 1 for errors

4. **Try curl to test**:
   ```bash
   curl http://localhost:8080
   ```

5. **Check firewall settings**:
   ```bash
   sudo pfctl -s rules | grep 8080
   ```

### Agents Not Starting

1. **Verify MCP servers are configured**:
   ```bash
   claude mcp list
   ```

2. **Check CLAUDE.md exists**:
   ```bash
   ls -la /tmp/agent-workspace/agent1/CLAUDE.md
   ```

3. **Try manual MCP connection** in Claude:
   ```
   /mcp
   ```

### No Tasks Available

1. Ensure tasks were created in Marcus UI
2. Check Marcus server logs
3. Verify Kanban MCP is running

## Quick Test Script

For repeated testing, use this script:

```bash
#!/bin/bash
# quick_test.sh

# Check Marcus
if ! curl -s http://localhost:8765 > /dev/null; then
    echo "ERROR: Marcus not running on port 8765"
    echo "Start with: cd /Users/lwgray/dev/marcus && python marcus_mcp_server.py"
    exit 1
fi

# Setup
echo "Setting up test environment..."
rm -rf /tmp/test-project /tmp/agent-workspace
mkdir -p /tmp/test-project
cd /tmp/test-project
git init -q
git config user.email "test@example.com"
git config user.name "Test"
echo "# Test" > README.md
git add . && git commit -q -m "Initial"

# Create worktrees
cd /Users/lwgray/dev/marcus/experiments
python scripts/run_real_agents.py \
  --source-repo /tmp/test-project \
  --workspace /tmp/agent-workspace \
  --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  --agents 2

echo -e "\n=== Setup Complete ==="
echo "Now manually start agents:"
echo "  Terminal 1: cd /tmp/agent-workspace/agent1 && claude"
echo "  Terminal 2: cd /tmp/agent-workspace/agent2 && claude"
echo "Then type 'start work' in each"
```

## Summary

1. Start Marcus and Kanban MCP servers
2. Create tasks in Marcus UI
3. Set up a test repository
4. Run setup script to create agent worktrees
5. Manually launch each agent with Claude
6. Type "start work" to begin
7. Monitor progress in Marcus UI
8. Collect results from git branches

The manual launch approach gives you full visibility into agent behavior, which is ideal for experiments and debugging.