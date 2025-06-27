#!/bin/bash
# Launch a Claude agent with "start work" piped in

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <agent_id> <worktree_path>"
    exit 1
fi

AGENT_ID=$1
WORKTREE_PATH=$2

echo "Launching Claude agent $AGENT_ID in $WORKTREE_PATH"

# Change to worktree
cd "$WORKTREE_PATH"

# Launch Claude with "start work" piped in
echo "start work" | claude