#!/bin/bash
# Test real agent launch with piping

echo "=== Testing Real Claude Agents with Marcus ==="

# Create test repo
TEST_REPO="/tmp/real-agent-test"
WORKSPACE="/tmp/real-agent-workspace"

echo "1. Creating test repository..."
rm -rf $TEST_REPO $WORKSPACE
mkdir -p $TEST_REPO
cd $TEST_REPO
git init -q
git config user.email "test@example.com"
git config user.name "Test"
echo "# Test" > README.md
git add . && git commit -q -m "Initial"

echo "2. Setting up worktrees..."
cd /Users/lwgray/dev/marcus/experiments
python scripts/setup_worktrees.py \
    --source-repo $TEST_REPO \
    --workspace-dir $WORKSPACE \
    --num-agents 2 \
    --cleanup

echo "3. Testing agent setup and launch..."
# Try the updated launcher
python scripts/run_real_agents.py \
    --source-repo $TEST_REPO \
    --workspace $WORKSPACE \
    --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
    --agents 2

echo "Done! Check if agents started correctly."