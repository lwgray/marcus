# PM Agent Configuration Guide

This guide covers all configuration options for PM Agent, including project selection, board management, and advanced settings.

## Configuration Methods

### 1. Configuration File (Recommended)
PM Agent uses `config_pm_agent.json` for persistent configuration.

```json
{
  "project_id": "1533678301472621705",
  "board_id": "1533822098756076745",
  "project_name": "Task Master Test",
  "auto_find_board": true,
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"
  }
}
```

### 2. Environment Variables
Override configuration with environment variables:

```bash
export PM_AGENT_PROJECT_ID="1533678301472621705"
export PM_AGENT_BOARD_ID="1533822098756076745"
export PLANKA_BASE_URL="http://localhost:3333"
export PLANKA_AGENT_EMAIL="demo@demo.demo"
export PLANKA_AGENT_PASSWORD="demo"
export ANTHROPIC_API_KEY="your-api-key"
```

### 3. Programmatic Configuration
Configure PM Agent in code:

```python
from pm_agent_mvp_fixed import PMAgentMVP

agent = PMAgentMVP()
agent.kanban_client.project_id = "your-project-id"
agent.kanban_client.board_id = "your-board-id"
```

## Project and Board Configuration

### Finding Your Project ID

#### Method 1: Using Kanban MCP Tools
```bash
python -c "
import asyncio
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

async def list_projects():
    client = MCPKanbanClient()
    async with client.connect() as conn:
        result = await conn.call_tool('mcp_kanban_project_board_manager', {
            'action': 'get_projects'
        })
        print(result)

asyncio.run(list_projects())
"
```

#### Method 2: From Planka URL
When viewing a project in Planka, the URL contains the project ID:
```
http://localhost:3333/projects/1533678301472621705/boards/...
                              ^^^^^^^^^^^^^^^^^^^^
                              This is your project ID
```

### Selecting a Board

#### Automatic Board Selection
```bash
# This script lists boards and saves selection
python select_task_master_board.py
```

#### Manual Board Selection
1. List boards in your project:
```python
# list_boards.py
import asyncio
import json
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

async def list_boards():
    client = MCPKanbanClient()
    client.project_id = "your-project-id"
    
    async with client.connect() as conn:
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "get_boards",
            "projectId": client.project_id
        })
        
        boards = json.loads(result.content[0].text)
        for board in boards:
            print(f"Board: {board['name']}")
            print(f"  ID: {board['id']}")
            print(f"  Cards: {board.get('cardCount', 0)}")
            print()

asyncio.run(list_boards())
```

2. Update config_pm_agent.json with chosen board ID

### Creating a New Board
```python
# create_board.py
import asyncio
import json
from datetime import datetime
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

async def create_board():
    client = MCPKanbanClient()
    client.project_id = "your-project-id"
    
    board_name = f"Dev Sprint - {datetime.now().strftime('%Y-%m-%d')}"
    
    async with client.connect() as conn:
        result = await conn.call_tool("mcp_kanban_project_board_manager", {
            "action": "create_board",
            "projectId": client.project_id,
            "name": board_name,
            "position": 1
        })
        
        board = json.loads(result.content[0].text)
        print(f"Created board: {board['name']}")
        print(f"Board ID: {board['id']}")
        
        # Save to config
        config = {
            "project_id": client.project_id,
            "board_id": board['id'],
            "project_name": "Your Project",
            "auto_find_board": False
        }
        
        with open("config_pm_agent.json", "w") as f:
            json.dump(config, f, indent=2)

asyncio.run(create_board())
```

## Advanced Configuration

### AI Engine Settings
Configure the AI engine in `src/config/settings.py`:

```python
class Settings:
    # AI Model Configuration
    ai_model: str = "claude-3-opus-20240229"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 4096
    
    # Task Analysis Settings
    task_analysis_prompt_template: str = "..."
    blocker_resolution_prompt_template: str = "..."
```

### Worker Agent Settings
Configure worker agent behavior:

```python
# In pm_agent_mvp_fixed.py or via configuration
class PMAgentMVP:
    def __init__(self):
        # Worker settings
        self.max_concurrent_workers = 10
        self.task_timeout_hours = 24
        self.worker_idle_timeout_minutes = 30
        self.default_worker_capacity = 40  # hours/week
```

### Kanban MCP Connection Settings
```python
# Connection timeouts and retries
class MCPKanbanClient:
    def __init__(self):
        self.connection_timeout = 30  # seconds
        self.retry_attempts = 3
        self.retry_delay = 2  # seconds
```

## Multi-Project Configuration

### Managing Multiple Projects
Create separate configuration files for each project:

```bash
# Project configurations
config_project_web.json
config_project_api.json
config_project_mobile.json

# Start PM Agent with specific config
python -m src.enhancements.configurable_pm_agent --config config_project_web.json
```

### Project Switching Script
```python
# switch_project.py
import json
import sys

def switch_project(project_name):
    configs = {
        "web": {
            "project_id": "123",
            "board_id": "456",
            "project_name": "Web Application"
        },
        "api": {
            "project_id": "789",
            "board_id": "012",
            "project_name": "API Backend"
        }
    }
    
    if project_name not in configs:
        print(f"Unknown project: {project_name}")
        print(f"Available: {', '.join(configs.keys())}")
        return
    
    config = configs[project_name]
    config["planka"] = {
        "base_url": "http://localhost:3333",
        "email": "demo@demo.demo",
        "password": "demo"
    }
    
    with open("config_pm_agent.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"Switched to project: {config['project_name']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python switch_project.py <project_name>")
    else:
        switch_project(sys.argv[1])
```

## Configuration Best Practices

### 1. Security
- Never commit credentials to git
- Use environment variables for sensitive data
- Rotate API keys regularly

### 2. Project Organization
- One board per sprint/phase
- Clear project naming conventions
- Archive completed boards

### 3. Performance
- Limit board size (< 100 active cards)
- Use specific project/board IDs (not auto-find)
- Configure appropriate timeouts

### 4. Development vs Production
```python
# config_dev.json
{
  "project_id": "dev-project-id",
  "board_id": "dev-board-id",
  "debug": true,
  "log_level": "DEBUG"
}

# config_prod.json
{
  "project_id": "prod-project-id",
  "board_id": "prod-board-id",
  "debug": false,
  "log_level": "INFO"
}
```

## Validation Script
```python
# validate_config.py
import json
import asyncio
from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient

async def validate_config():
    try:
        with open("config_pm_agent.json", "r") as f:
            config = json.load(f)
        
        print("✓ Config file loaded")
        
        client = MCPKanbanClient()
        client.project_id = config.get("project_id")
        client.board_id = config.get("board_id")
        
        async with client.connect() as conn:
            # Verify project exists
            result = await conn.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_project",
                "projectId": client.project_id
            })
            print(f"✓ Project verified: {client.project_id}")
            
            # Verify board exists
            if client.board_id:
                result = await conn.call_tool("mcp_kanban_project_board_manager", {
                    "action": "get_board",
                    "boardId": client.board_id
                })
                print(f"✓ Board verified: {client.board_id}")
        
        print("\n✅ Configuration is valid!")
        
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")

asyncio.run(validate_config())
```