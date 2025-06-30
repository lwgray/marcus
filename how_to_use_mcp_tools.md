# How to Use Marcus MCP Tools

## The Issue
The create_project MCP tool appears to timeout, but testing shows the actual function works fine (completes in ~7 seconds). The issue is with how the MCP server and client communicate.

## How MCP Works
1. **Server**: `marcus.py` runs as an MCP server that listens for tool requests
2. **Client**: Your MCP client (e.g., Claude Desktop) connects to the server
3. **Communication**: Uses stdio (standard input/output) for communication

## Correct Setup

### 1. Start Marcus MCP Server
```bash
# In a terminal, start the server:
python marcus.py
```

This will show:
```
Marcus MCP Server Running
Kanban Provider: KANBAN_MCP
Logs: logs/conversations/
==================================================
```

The server then waits for MCP client connections.

### 2. Configure Your MCP Client

For Claude Desktop, add to your MCP settings:
```json
{
  "marcus": {
    "command": "python",
    "args": ["/path/to/marcus.py"],
    "env": {
      "PLANKA_BASE_URL": "http://localhost:3333",
      "PLANKA_AGENT_EMAIL": "demo@demo.demo",
      "PLANKA_AGENT_PASSWORD": "demo"
    }
  }
}
```

### 3. Use the Tools

In your MCP client, you can then use:
```
create_project(
  description="Your project description",
  project_name="Project Name",
  options={}
)
```

## Why It Times Out

1. **No Server Running**: If marcus.py isn't running, the tool can't connect
2. **Wrong Usage**: Running `python marcus.py` again tries to start a new server, not connect to existing one
3. **MCP Client Timeout**: Default timeout may be too short for complex projects

## Alternative: Direct Python Usage

Since the function works fine directly, you can bypass MCP:

```python
# create_project_direct.py
import asyncio
from src.integrations.mcp_natural_language_tools import create_project_from_natural_language
from src.integrations.kanban_client_with_create import KanbanClientWithCreate
from src.ai.core.ai_engine import MarcusAIEngine

class SimpleState:
    def __init__(self):
        self.kanban_client = KanbanClientWithCreate()
        self.ai_engine = MarcusAIEngine()
        self.project_tasks = []
    
    async def refresh_project_state(self):
        self.project_tasks = await self.kanban_client.get_all_tasks()

async def create_project(description, name):
    state = SimpleState()
    return await create_project_from_natural_language(
        description=description,
        project_name=name,
        state=state
    )

# Use it
result = asyncio.run(create_project(
    "Your project description",
    "Project Name"
))
```

## Recommendations

1. **For Quick Tasks**: Use direct Python scripts (like create_recipe_project_simple.py)
2. **For MCP Integration**: Ensure marcus.py is running as a server first
3. **For Testing**: Use the direct function calls to bypass MCP overhead
4. **For Production**: Consider implementing progress updates to avoid timeout issues