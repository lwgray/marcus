#!/bin/bash

# Simple restart for agents

echo "Restarting agents..."

# Kill any existing agent processes
pkill -f "claude code" || true
sleep 2

# Start agent1
echo "Starting agent1..."
(cd agent1 && nohup claude code "$(cat ../prompts/marcus_agent_prompt.txt)" > ../agent1_restart.log 2>&1 &)
echo "Agent1 started"

# Start agent2  
echo "Starting agent2..."
(cd agent2 && nohup claude code "$(cat ../prompts/marcus_agent_prompt.txt)" > ../agent2_restart.log 2>&1 &)
echo "Agent2 started"

echo ""
echo "Both agents restarted!"
echo "Monitor UI at http://localhost:8080"
echo ""
echo "Watch logs:"
echo "  tail -f experiments/agent1_restart.log" 
echo "  tail -f experiments/agent2_restart.log"