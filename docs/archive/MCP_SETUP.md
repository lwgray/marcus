# MCP Server Setup Guide

This guide explains how to set up the PM Agent system with different kanban providers using their respective MCP servers.

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Workers │────▶│    PM Agent     │────▶│  Kanban MCP     │
│  (Agents/AI)    │◀────│  (MCP Server)   │◀────│    Servers      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                         │
                                │                   ┌─────┴─────┐
                                │                   │           │
                                │              ┌────▼───┐ ┌────▼───┐
                                │              │ Linear │ │ GitHub │
                                │              │  MCP   │ │  MCP   │
                                │              └────┬───┘ └────┬───┘
                                │                   │           │
                                │              ┌────▼───┐ ┌────▼───┐
                                │              │ Linear │ │ GitHub │
                                │              │  API   │ │  API   │
                                │              └────────┘ └────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Planka MCP     │
                        │  (Direct)       │
                        └─────────────────┘
```

## Provider Setup

### 1. Planka (Default)

Planka uses a direct MCP integration through the existing kanban-mcp server.

**Requirements:**
- Planka instance running
- kanban-mcp server configured

**Configuration:**
```bash
# .env
KANBAN_PROVIDER=planka
PLANKA_PROJECT_NAME="Task Master Test"
```

**MCP Server Setup:**
The Planka MCP server should already be configured in your Claude Desktop or VS Code.

### 2. Linear

Linear uses the [@cosmix/linear-mcp](https://glama.ai/mcp/servers/@cosmix/linear-mcp) server.

**Requirements:**
- Linear account with API access
- Linear API key
- Team ID and optional Project ID

**Installation:**
```bash
# Clone Linear MCP server
git clone https://github.com/cosmix/linear-mcp.git
cd linear-mcp

# Install dependencies
bun install
bun run build
```

**Configuration:**
```bash
# .env
KANBAN_PROVIDER=linear
LINEAR_API_KEY=your_api_key_here
LINEAR_TEAM_ID=your_team_id_here
LINEAR_PROJECT_ID=your_project_id_here  # Optional
```

**MCP Configuration (Claude Desktop):**
```json
{
  "mcpServers": {
    "linear": {
      "command": "node",
      "args": ["/absolute/path/to/linear-mcp/build/index.js"],
      "env": {
        "LINEAR_API_KEY": "your_api_key"
      }
    }
  }
}
```

### 3. GitHub Projects

GitHub uses the official [github-mcp-server](https://github.com/github/github-mcp-server).

**Requirements:**
- GitHub account
- Personal Access Token with appropriate permissions
- Repository with Projects enabled

**Installation (Docker):**
```bash
# Pull the Docker image
docker pull ghcr.io/github/github-mcp-server
```

**Configuration:**
```bash
# .env
KANBAN_PROVIDER=github
GITHUB_TOKEN=your_token_here
GITHUB_OWNER=your_username_or_org
GITHUB_REPO=your_repo_name
GITHUB_PROJECT_NUMBER=1
```

**MCP Configuration (Claude Desktop):**
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Running PM Agent with MCP Servers

### Step 1: Start the Kanban MCP Server

Depending on your chosen provider, ensure the appropriate MCP server is running:

- **Planka**: Start the kanban-mcp server
- **Linear**: The Linear MCP server will be started by your MCP host
- **GitHub**: The GitHub MCP server will be started by Docker

### Step 2: Start PM Agent

```bash
# Set the provider
export KANBAN_PROVIDER=linear  # or github, planka

# Run PM Agent
python pm_agent_mcp_server_unified.py
```

### Step 3: Start Mock Workers (for testing)

```bash
python mock_claude_worker.py --name worker_1
```

## Tool Mapping

### Linear MCP Tools
- `linear.create_issue` → Create new task
- `linear.update_issue` → Update task details
- `linear.get_issue` → Get task by ID
- `linear.search_issues` → Search for tasks
- `linear.create_comment` → Add comment to task
- `linear.get_teams` → Get team information

### GitHub MCP Tools
- `github.create_issue` → Create new task
- `github.update_issue` → Update task details
- `github.get_issue` → Get task by ID
- `github.list_issues` → List repository issues
- `github.search_issues` → Search for tasks
- `github.add_issue_comment` → Add comment to task

## Troubleshooting

### MCP Server Connection Issues

1. **Check MCP server is running:**
   - For Linear: Check the process is running
   - For GitHub: Check Docker container is running
   - For Planka: Check kanban-mcp server logs

2. **Verify API credentials:**
   - Linear: Test API key at https://linear.app/settings/api
   - GitHub: Test token with `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`

3. **Check environment variables:**
   ```bash
   echo $KANBAN_PROVIDER
   echo $LINEAR_API_KEY  # or GITHUB_TOKEN
   ```

### Task Sync Issues

1. **Linear:**
   - Ensure tasks are in correct team
   - Check project filters if using project_id
   - Verify issue states match expected values

2. **GitHub:**
   - Ensure issues are in the specified repository
   - Check label configuration for priority/status
   - Verify project board setup

## Advanced Configuration

### Custom MCP Tool Caller

To implement a real MCP client connection, update the `_mcp_function_caller` method in `pm_agent_mcp_server_unified.py`:

```python
async def _mcp_function_caller(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
    """Function to call MCP tools for kanban integrations"""
    
    # Example using hypothetical MCP client library
    if self.provider == 'linear':
        client = MCPClient("linear")
        return await client.call_tool(tool_name, arguments)
    # ... etc
```

### Multiple Providers

You can run multiple PM Agent instances with different providers:

```bash
# Terminal 1 - Linear
KANBAN_PROVIDER=linear python pm_agent_mcp_server_unified.py

# Terminal 2 - GitHub  
KANBAN_PROVIDER=github python pm_agent_mcp_server_unified.py
```

## Next Steps

1. Choose your preferred kanban provider
2. Set up the corresponding MCP server
3. Configure environment variables
4. Start the PM Agent system
5. Monitor the visualization UI at http://localhost:4298

For production use, consider:
- Implementing proper MCP client connections
- Adding authentication/authorization
- Setting up monitoring and logging
- Configuring rate limiting for API calls