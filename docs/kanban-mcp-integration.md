# Kanban MCP Integration

## Understanding kanban-mcp

The kanban-mcp is a Model Context Protocol (MCP) server that provides programmatic access to Planka boards. It's important to understand:

### Key Concepts

1. **It's NOT a traditional server**
   - Doesn't run continuously in the background
   - Communicates via stdio (stdin/stdout)
   - Starts automatically when Python scripts connect

2. **How it works**
   ```python
   # When you do this:
   async with stdio_client(server_params) as (read, write):
       async with ClientSession(read, write) as session:
           # kanban-mcp starts automatically here
           await session.initialize()
   ```

3. **No manual management needed**
   - Don't use `./kanban start` scripts
   - Don't worry about starting/stopping
   - Just run your Python scripts

## Available Tools

The kanban-mcp provides 8 tools:

### 1. Project & Board Manager
```python
await session.call_tool("mcp_kanban_project_board_manager", {
    "action": "get_boards",
    "projectId": "123"
})
```

### 2. List Manager
```python
await session.call_tool("mcp_kanban_list_manager", {
    "action": "create",
    "boardId": "456",
    "name": "To Do",
    "position": 1
})
```

### 3. Card Manager
```python
await session.call_tool("mcp_kanban_card_manager", {
    "action": "create",
    "listId": "789",
    "name": "New Task",
    "description": "Task details"
})
```

### 4. Task Manager
```python
await session.call_tool("mcp_kanban_task_manager", {
    "action": "create",
    "cardId": "abc",
    "name": "Subtask 1"
})
```

### 5. Label Manager
```python
await session.call_tool("mcp_kanban_label_manager", {
    "action": "create",
    "boardId": "456",
    "name": "Bug",
    "color": "berry-red"
})
```

### 6. Comment Manager
```python
await session.call_tool("mcp_kanban_comment_manager", {
    "action": "create",
    "cardId": "abc",
    "text": "Progress update"
})
```

### 7. Stopwatch (Time Tracking)
```python
await session.call_tool("mcp_kanban_stopwatch", {
    "action": "start",
    "id": "card_id"
})
```

### 8. Membership Manager
```python
await session.call_tool("mcp_kanban_membership_manager", {
    "action": "get_all",
    "boardId": "456"
})
```

## Connection Pattern

Always use this pattern:

```python
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Connect
server_params = StdioServerParameters(
    command="node",
    args=["../kanban-mcp/dist/index.js"],
    env=os.environ.copy()
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # Now use session.call_tool()
```

## Troubleshooting

### Connection Issues
- Ensure kanban-mcp is installed at `../kanban-mcp`
- Check Planka is running at configured URL
- Verify credentials are correct

### Common Errors
- `JSONDecodeError`: Response format changed, check tool parameters
- `TimeoutError`: Planka not accessible or credentials wrong
- `FileNotFoundError`: kanban-mcp not installed at expected path