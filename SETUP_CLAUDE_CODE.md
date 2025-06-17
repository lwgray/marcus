# Setting Up PM Agent with Claude Code

## Quick Setup (Recommended)

Run this command to add PM Agent to Claude Code:

```bash
claude mcp add pm-agent /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python -m src.pm_agent_mvp_fixed
```

This setup:
- ✅ Runs PM Agent from its directory
- ✅ Maintains security boundaries
- ✅ Protects PM Agent source code from agents

## Alternative Setups

### With Separate Client Workspace

If you want agents to work in a specific directory:

```bash
# Create workspace
mkdir -p ~/agent-workspace

# Add PM Agent with workspace
claude mcp add pm-agent -d ~/agent-workspace -- /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python /Users/lwgray/dev/pm-agent/src/pm_agent_mvp_fixed.py
```

### Using System Python

If you don't have conda:

```bash
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

## What NOT to Do

❌ **Don't set working directory to PM Agent:**
```bash
# BAD - gives agent access to PM Agent source
claude mcp add pm-agent -d /Users/lwgray/dev/pm-agent -- python -m src.pm_agent_mvp_fixed
```

## Verify Security

After setup, test that security is working:

1. Ask Claude to use the PM Agent ping tool
2. Register as an agent and request a task
3. Try to access PM Agent files (should be blocked)

## How Security Works

1. **WorkspaceManager** automatically detects PM Agent location
2. Adds PM Agent directory to forbidden paths
3. Validates all file operations
4. Assigns safe workspaces to agents

Even if you run from PM Agent directory, the security system prevents agents from modifying PM Agent files.