# Claude Code MCP Setup for Marcus

## Security Considerations

The Marcus includes security boundaries to prevent autonomous agents from accessing its source code. When setting up the MCP server, it's important to configure it properly to maintain these security boundaries.

## Recommended Setup

### Option 1: Run from Marcus Directory (Secure)

```bash
claude mcp add pm-agent /path/to/your/python -m src.pm_agent_mvp_fixed
```

This runs the Marcus from its installation directory WITHOUT giving the agent access to it. The WorkspaceManager automatically protects the Marcus directory.

### Option 2: Run with Explicit Working Directory (Client Workspace)

If you want to set a specific working directory for the agent:

```bash
# Create a client workspace
mkdir -p ~/pm-agent-workspace

# Add MCP server with client workspace as working directory
claude mcp add pm-agent -d ~/pm-agent-workspace -- /path/to/python /path/to/pm-agent/src/pm_agent_mvp_fixed.py
```

## Finding Your Python Path

### For Conda Environments
```bash
conda activate your-env
which python
# Example output: /home/user/anaconda3/envs/pm-agent/bin/python
```

### For Virtualenv
```bash
source venv/bin/activate
which python
# Example output: /home/user/projects/pm-agent/venv/bin/python
```

### For Pipenv
```bash
cd /path/to/pm-agent
pipenv --venv
# Example output: /home/user/.local/share/virtualenvs/pm-agent-x7d8s9f/
# Use the Python binary in that directory's bin folder
```

### For System Python
```bash
which python3
# Example output: /usr/bin/python3
```

## What Each Flag Does

- `-s user`: Runs the server as the current user (default)
- `-d <directory>`: Sets the working directory for the MCP server
- `--`: Separates MCP flags from the command

## Security Features

1. **Automatic Marcus Protection**: The WorkspaceManager automatically detects where Marcus is installed and adds it to forbidden paths.

2. **Workspace Isolation**: Each agent gets assigned a workspace and cannot access:
   - Marcus source code
   - Other agents' workspaces
   - System directories

3. **Path Validation**: All file operations are validated against forbidden paths.

## Verifying Security

After setting up, you can verify security is working:

1. Use the ping tool to check the Marcus is running:
   ```
   Use the pm-agent ping tool
   ```

2. Register as an agent and request a task:
   ```
   Use pm-agent register_agent with agent_id "test-01", name "Test Agent", role "Developer"
   Then use pm-agent request_next_task with agent_id "test-01"
   ```

3. Check the task assignment includes forbidden paths that prevent access to Marcus.

## Troubleshooting

### "No module named src"
Make sure you're running from the Marcus directory or using the full path to the script:
```bash
# If running from Marcus directory
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed

# Or use full path
claude mcp add pm-agent python3 /path/to/pm-agent/src/pm_agent_mvp_fixed.py
```

### "Board ID not set"
Ensure `config_pm_agent.json` exists in the Marcus directory with:
```json
{
  "project_id": "your-project-id",
  "board_id": "your-board-id"
}
```

### Agent can access Marcus files
This should not happen with the current security implementation. If it does:
1. Check WorkspaceManager is initialized properly
2. Verify the pm_agent_root detection is working
3. Report as a security issue

## Docker Alternative

You can also run Marcus in Docker for additional isolation:

```bash
# Build the image
cd /path/to/pm-agent
docker build -t pm-agent:latest .

# Run with MCP
claude mcp add pm-agent-docker docker run -i --rm -v $(pwd)/config_pm_agent.json:/app/config_pm_agent.json pm-agent:latest
```

## Best Practices

1. **Don't use `-d /path/to/pm-agent`**: This would set the working directory to Marcus itself
2. **Use separate workspaces**: Create dedicated directories for agent work
3. **Monitor logs**: Check Marcus logs for security violations
4. **Test isolation**: Regularly verify agents cannot access forbidden paths

## Examples for Different Setups

### Conda Environment
```bash
# Activate your environment first
conda activate pm-agent-env

# Find Python path
which python
# Output: /home/user/anaconda3/envs/pm-agent-env/bin/python

# Add to Claude Code
claude mcp add pm-agent /home/user/anaconda3/envs/pm-agent-env/bin/python -m src.pm_agent_mvp_fixed
```

### Pipenv
```bash
# From Marcus directory
cd /path/to/pm-agent

# Add using pipenv
claude mcp add pm-agent pipenv run python -m src.pm_agent_mvp_fixed
```

### Virtualenv
```bash
# Create and activate virtualenv
cd /path/to/pm-agent
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Add to Claude Code
claude mcp add pm-agent ./venv/bin/python -m src.pm_agent_mvp_fixed
```

### System Python
```bash
# Simple setup with system Python
claude mcp add pm-agent python3 -m src.pm_agent_mvp_fixed
```

## Understanding the Security Model

Even though the Marcus runs from its own directory, it's still secure because:

1. **WorkspaceManager** detects its own location at startup
2. Adds its directory to a forbidden paths list
3. Intercepts all file operations from agents
4. Blocks access to forbidden paths
5. Assigns safe workspaces for agent work

This means the `-d` flag is more about where the agent should work, not about security. The security is enforced at the application level, not by the working directory.