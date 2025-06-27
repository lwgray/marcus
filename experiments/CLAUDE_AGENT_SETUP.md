# Setting Up Claude Agents with Marcus

Since Claude reads from `CLAUDE.md` files and responds to "start work", here's the correct way to set up agents:

## Quick Setup (2 Agents)

### 1. Create Test Repository
```bash
mkdir -p /tmp/test-project
cd /tmp/test-project
git init
echo "# Test" > README.md
git add . && git commit -m "Initial"
```

### 2. Setup Worktrees
```bash
cd /Users/lwgray/dev/marcus/experiments
python scripts/setup_worktrees.py \
  --source-repo /tmp/test-project \
  --workspace-dir /tmp/agent-workspace \
  --num-agents 2
```

### 3. Configure Agents
```bash
python scripts/setup_claude_agent.py --all \
  /tmp/agent-workspace \
  /Users/lwgray/dev/marcus/marcus_mcp_server.py \
  prompts/marcus_agent.md
```

This creates `CLAUDE.md` in each worktree with the agent instructions.

### 4. Start Agents Manually

**Terminal 1:**
```bash
cd /tmp/agent-workspace/agent1
claude
# Once Claude starts, type: start work
```

**Terminal 2:**
```bash
cd /tmp/agent-workspace/agent2
claude
# Once Claude starts, type: start work
```

## What Happens

1. Each agent reads their `CLAUDE.md` file
2. When you type "start work", they:
   - Connect to Marcus MCP (`/mcp` command)
   - Register with Marcus
   - Start requesting and working on tasks
   - Work autonomously until no tasks remain

## Automated Launch (Experimental)

For multiple agents, you can use tmux:

```bash
#!/bin/bash
# launch_agents_tmux.sh

WORKSPACE="/tmp/agent-workspace"
NUM_AGENTS=2

# Create tmux session
tmux new-session -d -s marcus-agents

# Launch each agent in a pane
for i in $(seq 1 $NUM_AGENTS); do
    if [ $i -eq 1 ]; then
        # First pane
        tmux send-keys -t marcus-agents "cd $WORKSPACE/agent$i && claude" C-m
    else
        # Split and create new pane
        tmux split-window -t marcus-agents
        tmux send-keys -t marcus-agents "cd $WORKSPACE/agent$i && claude" C-m
    fi
    
    # Wait for Claude to start
    sleep 3
    
    # Send "start work" command
    tmux send-keys -t marcus-agents "start work" C-m
done

# Arrange panes
tmux select-layout -t marcus-agents tiled

# Attach to session
tmux attach -t marcus-agents
```

## Directory Structure After Setup

```
/tmp/agent-workspace/
├── agent1/
│   ├── CLAUDE.md       # Agent 1's instructions
│   ├── .git            # Worktree git info
│   └── [project files]
└── agent2/
    ├── CLAUDE.md       # Agent 2's instructions
    ├── .git            # Worktree git info
    └── [project files]
```

## Each CLAUDE.md Contains

1. Auto-start trigger for "start work"
2. Agent identity (ID, branch, worktree)
3. MCP connection instructions
4. Full Marcus workflow
5. Task execution guidelines

## Troubleshooting

### MCP Not Connecting
```bash
# List configured MCP servers
claude mcp list

# Remove old configs
claude mcp remove marcus_agent1

# Re-add
claude mcp add marcus_agent1 -- python /path/to/marcus_mcp_server.py
```

### Agent Not Starting
1. Check CLAUDE.md exists in worktree
2. Verify Marcus is running (http://localhost:8765)
3. Check MCP server is configured
4. Try manual MCP connection: `/mcp` in Claude

### Multiple Agents Conflict
Each agent should:
- Work in separate worktree
- Have unique agent ID
- Use different git branch
- Connect to Marcus with unique name

## Next Steps

1. Start with 2 agents for testing
2. Create tasks in Marcus UI
3. Launch agents and type "start work"
4. Monitor progress in Marcus UI
5. Check git branches for commits