#!/bin/bash
# Quick test script for agent setup

echo "=== Testing Claude Agent Setup with Marcus ==="

# Check if Marcus is running
echo -n "Checking Marcus... "
if curl -s http://localhost:8765/health > /dev/null; then
    echo "✓ Running"
else
    echo "✗ Not running!"
    echo "Please start Marcus first: cd /Users/lwgray/dev/marcus && python marcus_mcp_server.py"
    exit 1
fi

# Setup test repository
TEST_REPO="/tmp/test-agent-repo"
WORKSPACE="/tmp/test-agent-workspace"

echo -e "\n1. Creating test repository at $TEST_REPO"
rm -rf $TEST_REPO
mkdir -p $TEST_REPO
cd $TEST_REPO
git init
git config user.email "test@example.com"
git config user.name "Test User"
echo "# Test Project" > README.md
echo "def hello():\n    print('Hello')" > main.py
git add .
git commit -m "Initial commit"

# Setup worktrees
echo -e "\n2. Setting up worktrees at $WORKSPACE"
cd /Users/lwgray/dev/marcus/experiments
python scripts/setup_worktrees.py \
    --source-repo $TEST_REPO \
    --workspace-dir $WORKSPACE \
    --num-agents 2

# Configure agents
echo -e "\n3. Configuring agents with CLAUDE.md"
python scripts/setup_claude_agent.py --all \
    $WORKSPACE \
    /Users/lwgray/dev/marcus/marcus_mcp_server.py

echo -e "\n=== Setup Complete! ==="
echo -e "\nTo start agents:"
echo "  Terminal 1: cd $WORKSPACE/agent1 && claude"
echo "  Terminal 2: cd $WORKSPACE/agent2 && claude"
echo -e "\nThen type 'start work' in each Claude instance"
echo -e "\nMonitor progress at: http://localhost:8765"