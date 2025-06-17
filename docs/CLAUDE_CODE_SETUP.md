# Claude Code MCP Setup for PM Agent

## Security Considerations

The PM Agent includes security boundaries to prevent autonomous agents from accessing its source code. When setting up the MCP server, it's important to configure it properly to maintain these security boundaries.

## Recommended Setup

### Option 1: Run from PM Agent Directory (Secure)

```bash
claude mcp add pm-agent /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python -m src.pm_agent_mvp_fixed
```

This runs the PM Agent from its installation directory WITHOUT giving the agent access to it. The WorkspaceManager automatically protects the PM Agent directory.

### Option 2: Run with Explicit Working Directory (Client Workspace)

If you want to set a specific working directory for the agent:

```bash
# Create a client workspace
mkdir -p ~/pm-agent-workspace

# Add MCP server with client workspace as working directory
claude mcp add pm-agent -d ~/pm-agent-workspace -- /Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python /Users/lwgray/dev/pm-agent/src/pm_agent_mvp_fixed.py
```

## What Each Flag Does

- `-s user`: Runs the server as the current user (default)
- `-d <directory>`: Sets the working directory for the MCP server
- `--`: Separates MCP flags from the command

## Security Features

1. **Automatic PM Agent Protection**: The WorkspaceManager automatically detects where PM Agent is installed and adds it to forbidden paths.

2. **Workspace Isolation**: Each agent gets assigned a workspace and cannot access:
   - PM Agent source code
   - Other agents' workspaces
   - System directories

3. **Path Validation**: All file operations are validated against forbidden paths.

## Verifying Security

After setting up, you can verify security is working:

1. Use the ping tool to check the PM Agent is running:
   ```
   Use the pm-agent ping tool
   ```

2. Register as an agent and request a task:
   ```
   Use pm-agent register_agent with agent_id "test-01", name "Test Agent", role "Developer"
   Then use pm-agent request_next_task with agent_id "test-01"
   ```

3. Check the task assignment includes forbidden paths that prevent access to PM Agent.

## Troubleshooting

### "No module named src"
Make sure you're running from the PM Agent directory or using the full path to the script.

### "Board ID not set"
Ensure `config_pm_agent.json` exists in the PM Agent directory with:
```json
{
  "project_id": "your-project-id",
  "board_id": "your-board-id"
}
```

### Agent can access PM Agent files
This should not happen with the current security implementation. If it does:
1. Check WorkspaceManager is initialized properly
2. Verify the pm_agent_root detection is working
3. Report as a security issue

## Docker Alternative

You can also run PM Agent in Docker for additional isolation:

```bash
# Build the image
cd /Users/lwgray/dev/pm-agent
docker build -t pm-agent:latest .

# Run with MCP
claude mcp add pm-agent-docker docker run -i --rm -v $(pwd)/config_pm_agent.json:/app/config_pm_agent.json pm-agent:latest
```

## Best Practices

1. **Don't use `-d /path/to/pm-agent`**: This would set the working directory to PM Agent itself
2. **Use separate workspaces**: Create dedicated directories for agent work
3. **Monitor logs**: Check PM Agent logs for security violations
4. **Test isolation**: Regularly verify agents cannot access forbidden paths