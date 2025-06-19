# Testing PM Agent MCP Connection

After running:
```bash
claude mcp add pm-agent "/Users/lwgray/opt/anaconda3/envs/pm-agent/bin/python" "/Users/lwgray/dev/pm-agent/pm_agent_mcp_server_v2.py"
```

1. Restart Claude (completely quit and reopen)

2. In a new Claude conversation, you should be able to use these PM Agent tools:
   - `ping` - Test connection
   - `register_agent` - Register as a worker
   - `request_next_task` - Get a task assignment
   - `report_task_progress` - Report progress
   - `get_project_status` - View project status

3. Test with:
   ```
   Use the pm-agent ping tool to test the connection
   ```

The PM Agent should respond with the echo message and current status.