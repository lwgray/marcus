# Step-by-Step Instructions for Testing Marcus UI with Agents

## Current Status
- ✅ Marcus MCP server is running
- ✅ UI server is running with fixes to recognize agents
- ✅ Two test agents have been started and are waiting for MCP connections
- ✅ UI is accessible at http://localhost:8080

## Steps to Complete the Test

### Step 1: Open the UI
1. Open your web browser
2. Navigate to http://localhost:8080
3. You should see the Marcus Visualization interface with:
   - A sidebar on the left with filters
   - A main visualization area in the center
   - Metrics panel on the right
   - Event log at the bottom

### Step 2: Connect Agent 1
1. Open a new terminal window
2. Navigate to agent1's directory:
   ```bash
   cd /tmp/marcus-agents/agent1
   ```
3. Start Claude Code with the MCP connection:
   ```bash
   claude code
   ```
4. In the Claude Code interface, type `/mcp`
5. When the MCP connection dialog appears, connect to `marcus_agent1`
6. Once connected, type "start work" to begin the agent's autonomous workflow

### Step 3: Connect Agent 2
1. Open another new terminal window
2. Navigate to agent2's directory:
   ```bash
   cd /tmp/marcus-agents/agent2
   ```
3. Start Claude Code with the MCP connection:
   ```bash
   claude code
   ```
4. In the Claude Code interface, type `/mcp`
5. When the MCP connection dialog appears, connect to `marcus_agent2`
6. Once connected, type "start work" to begin the agent's autonomous workflow

### Step 4: Monitor the UI
Once both agents are connected and working, you should see in the UI:

1. **Network Visualization**:
   - "agent1" and "agent2" nodes appear (blue worker nodes)
   - "marcus" node in the center (purple)
   - "kanban_board" node (green)
   - Lines showing communication flow between nodes
   - Animated edges when messages are sent

2. **Metrics Panel** (right side):
   - Active Workers count should show "2"
   - Tasks in Progress will update as agents work
   - Decisions Made counter increases as Marcus makes decisions
   - Average Confidence percentage

3. **Event Log** (bottom):
   - Real-time messages showing:
     - Agent registrations
     - Task requests
     - Progress updates
     - Marcus decisions

### Step 5: Verify Agent Activity
To confirm agents are working properly:

1. Check agent logs:
   ```bash
   # In one terminal
   tail -f /tmp/marcus-agents/agent1/agent1.log
   
   # In another terminal
   tail -f /tmp/marcus-agents/agent2/agent2.log
   ```

2. Check Marcus server logs:
   ```bash
   tail -f /Users/lwgray/dev/marcus/logs/conversations/realtime_*.jsonl | grep -E "agent1|agent2"
   ```

3. Check UI server logs:
   ```bash
   tail -f /Users/lwgray/dev/marcus/ui_server_fixed2.log
   ```

### Expected Behavior
- Agents will register themselves with Marcus
- They'll request tasks from the Planka board
- Marcus will assign tasks based on agent skills
- Agents will report progress at 25%, 50%, 75%, and completion
- All this activity should be visible in real-time in the UI

### Troubleshooting

**If agents don't appear in the UI:**
1. Refresh the browser page
2. Check that agents successfully connected via MCP
3. Verify Marcus server is still running
4. Check for errors in the UI server log

**If agents aren't getting tasks:**
1. Verify there are tasks in the Planka board
2. Check Marcus server logs for task assignment decisions
3. Ensure agents are properly registered

**To restart everything:**
```bash
# Stop all processes
pkill -f "claude code"
pkill -f "python.*ui_server"
pkill -f "python.*marcus_mcp_server"

# Restart Marcus server
cd /Users/lwgray/dev/marcus
python marcus_mcp_server.py &

# Restart UI server
python run_ui_server.py &

# Restart agents
./experiments/restart_test_agents.sh
```

Then repeat steps 2-4 to reconnect the agents.