# Running Marcus Experiments - Current Status

## The Challenge

Claude agents need to:
1. Start in interactive mode (to work continuously)
2. Read their CLAUDE.md file
3. Connect to Marcus MCP
4. Respond to "start work" command
5. Work autonomously until no tasks remain

## Current Approach

### 1. Setup Phase (Automated)
```bash
# This part works well
python scripts/run_real_agents.py \
  --source-repo /path/to/repo \
  --workspace /tmp/agents \
  --marcus-server /path/to/marcus_mcp_server.py \
  --agents 2
```

This successfully:
- ✅ Creates git worktrees for each agent
- ✅ Creates CLAUDE.md with instructions
- ✅ Configures Marcus MCP servers
- ❌ But agents exit immediately when using `claude -p "start work"`

### 2. Manual Agent Launch (Working)

After setup, manually start each agent:

**Terminal 1:**
```bash
cd /tmp/agents/agent1
claude
# Wait for Claude to start
# Type: start work
```

**Terminal 2:**
```bash
cd /tmp/agents/agent2  
claude
# Wait for Claude to start
# Type: start work
```

## Why Automation Is Tricky

1. `claude -p "start work"` - Runs in print mode, outputs response, exits
2. `claude` alone - Starts interactive mode but needs manual "start work"
3. Piping doesn't work as expected with interactive programs

## Workarounds

### Option 1: Using tmux (Semi-Automated)
```bash
#!/bin/bash
# launch_agents_tmux.sh

tmux new-session -d -s agents

# Agent 1
tmux send-keys -t agents "cd /tmp/agents/agent1 && claude" C-m
sleep 5
tmux send-keys -t agents "start work" C-m

# Agent 2  
tmux split-window -t agents
tmux send-keys -t agents "cd /tmp/agents/agent2 && claude" C-m
sleep 5
tmux send-keys -t agents "start work" C-m

tmux attach -t agents
```

### Option 2: Using expect (Fully Automated)
```expect
#!/usr/bin/expect
# launch_agent.exp

spawn claude
expect "Claude"
send "start work\r"
interact
```

### Option 3: Modified CLAUDE.md (Self-Starting)
Instead of waiting for "start work", make CLAUDE.md more directive:
```markdown
# IMPORTANT: Start Working Immediately

As soon as you read this, immediately:
1. Connect to Marcus MCP using /mcp
2. Begin the autonomous workflow
[rest of instructions...]
```

## Current Recommendation

For now, use the semi-manual approach:

1. **Run setup script** to prepare everything:
   ```bash
   python scripts/run_real_agents.py --setup-only [args...]
   ```

2. **Launch agents manually** in separate terminals:
   ```bash
   cd /tmp/agents/agent1 && claude
   # Type: start work
   ```

3. **Monitor progress** at http://localhost:8765

## Future Improvements

1. Investigate Claude API for programmatic control
2. Create expect scripts for full automation
3. Modify Claude to support batch mode
4. Use process automation tools

## Testing

To test with 2 agents on a simple project:
```bash
# Terminal 1: Marcus
cd /Users/lwgray/dev/marcus
python marcus_mcp_server.py

# Terminal 2: Setup
cd /Users/lwgray/dev/marcus/experiments
./test_agent_setup.sh

# Terminal 3 & 4: Launch agents manually
# Follow instructions from setup script
```