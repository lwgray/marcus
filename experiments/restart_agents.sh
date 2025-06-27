#!/bin/bash

# Restart agents to test the UI visualization fixes

echo "Restarting agents to test UI visualization..."

# Kill any existing agent processes
pkill -f "claude code agent1" || true
pkill -f "claude code agent2" || true

# Give processes time to clean up
sleep 2

# Start agent1
echo "Starting agent1..."
cd agent1_worktree
nohup claude code "$(cat ../prompts/marcus_agent_prompt.txt)" > ../logs/agent1_restart.log 2>&1 &
AGENT1_PID=$!
echo "Agent1 started with PID: $AGENT1_PID"
cd ..

# Start agent2  
echo "Starting agent2..."
cd agent2_worktree
nohup claude code "$(cat ../prompts/marcus_agent_prompt.txt)" > ../logs/agent2_restart.log 2>&1 &
AGENT2_PID=$!
echo "Agent2 started with PID: $AGENT2_PID"
cd ..

echo "Both agents restarted!"
echo ""
echo "Monitor the UI at http://localhost:8080 to see agent activity"
echo "Check agent logs:"
echo "  - tail -f logs/agent1_restart.log"
echo "  - tail -f logs/agent2_restart.log"
echo ""
echo "To stop agents: pkill -f 'claude code agent'"