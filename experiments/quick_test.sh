#!/bin/bash
# Quick test script for Marcus experiments

echo "Setting up test environment for Marcus..."

# 1. Create a test project if it doesn't exist
TEST_PROJECT="/tmp/test-project"
WORKSPACE="/tmp/marcus-agents"

if [ ! -d "$TEST_PROJECT" ]; then
    echo "Creating test project..."
    mkdir -p "$TEST_PROJECT"
    cd "$TEST_PROJECT"
    git init
    git config user.email "test@example.com"
    git config user.name "Test User"
    git config commit.gpgsign false
    
    # Create some initial files
    echo "# Test Project" > README.md
    echo "def main():\n    print('Hello World')" > main.py
    echo "# TODO: Add tests" > test_main.py
    
    git add .
    git commit -m "Initial commit"
fi

# 2. Clean workspace and branches
echo "Cleaning workspace..."
rm -rf "$WORKSPACE"

# Clean up git branches if they exist
if [ -d "$TEST_PROJECT/.git" ]; then
    cd "$TEST_PROJECT"
    git branch -D agent1-work agent2-work 2>/dev/null || true
    git worktree prune
    cd - > /dev/null
fi

# 3. Run the experiment setup
echo "Starting experiment with 2 agents..."
cd /Users/lwgray/dev/marcus/experiments

python scripts/run_real_agents.py \
  --source-repo "$TEST_PROJECT" \
  --workspace "$WORKSPACE" \
  --marcus-server /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  --agents 2

echo -e "\n=== Setup Complete ==="
echo "Now manually start agents:"
echo "  Terminal 1: cd $WORKSPACE/agent1 && claude"
echo "  Terminal 2: cd $WORKSPACE/agent2 && claude"
echo "Then type 'start work' in each"