# Setting Up PM Agent with Claude Code

## Quick Setup (Recommended)

Run this command to add PM Agent to Claude Code:

```bash
claude mcp add pm-agent /path/to/your/python -m src.pm_agent_mvp_fixed
```

Replace `/path/to/your/python` with your Python executable:
- Conda: `~/anaconda3/envs/your-env/bin/python`
- Pipenv: `pipenv run python` (run from PM Agent directory)
- Virtualenv: `./venv/bin/python`
- System: `python3`

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
claude mcp add pm-agent -d ~/agent-workspace -- /path/to/python /path/to/pm-agent/src/pm_agent_mvp_fixed.py
```

### Using System Python

If you're using system Python:

```bash
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

### With Pipenv

If using pipenv from PM Agent directory:

```bash
cd /path/to/pm-agent
claude mcp add pm-agent pipenv run python -m src.pm_agent_mvp_fixed
```

## What NOT to Do

❌ **Don't set working directory to PM Agent:**
```bash
# BAD - gives agent access to PM Agent source
claude mcp add pm-agent -d /path/to/pm-agent -- python -m src.pm_agent_mvp_fixed
```

## Finding Your Python Path

### For Conda
```bash
conda activate your-env
which python
# Example output: /home/user/anaconda3/envs/pm-agent/bin/python
```

### For Virtualenv
```bash
# If using virtualenv
source venv/bin/activate
which python
# Example output: /home/user/projects/pm-agent/venv/bin/python
```

### For Pipenv
```bash
cd /path/to/pm-agent
pipenv --venv
# Example output: /home/user/.local/share/virtualenvs/pm-agent-x7d8s9f/
# Use: /home/user/.local/share/virtualenvs/pm-agent-x7d8s9f/bin/python
```

### For System Python
```bash
which python3
# Example output: /usr/bin/python3
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