#!/bin/bash

# Restart test agents in /tmp/marcus-agents

echo "Restarting test agents..."

# Kill any existing agent processes
echo "Stopping existing agents..."
pkill -f "claude code" || true
sleep 2

# Navigate to the workspace
cd /tmp/marcus-agents

# Start agent1
echo "Starting agent1..."
cd agent1
nohup claude code "$(cat /Users/lwgray/dev/marcus/experiments/prompts/marcus_agent.md)" > agent1.log 2>&1 &
AGENT1_PID=$!
echo "Agent1 started with PID: $AGENT1_PID"
cd ..

# Start agent2  
echo "Starting agent2..."
cd agent2
nohup claude code "$(cat /Users/lwgray/dev/marcus/experiments/prompts/marcus_agent.md)" > agent2.log 2>&1 &
AGENT2_PID=$!
echo "Agent2 started with PID: $AGENT2_PID"
cd ..

echo ""
echo "Both agents restarted!"
echo ""
echo "Monitor the UI at http://localhost:8080 to see agent activity"
echo ""
echo "Check agent logs:"
echo "  tail -f /tmp/marcus-agents/agent1/agent1.log"
echo "  tail -f /tmp/marcus-agents/agent2/agent2.log"
echo ""
echo "To stop agents: pkill -f 'claude code'"