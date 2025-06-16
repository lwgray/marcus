# Getting Started with PM Agent

This guide will help you set up and run PM Agent for the first time.

## Prerequisites

### Required Software
- Python 3.8+
- Node.js 18+
- Docker
- Git

### Optional
- Anthropic API key (for AI features)

## Installation

### 1. Install kanban-mcp (includes Planka)

```bash
# Clone kanban-mcp repository
git clone https://github.com/bradrisse/kanban-mcp.git
cd kanban-mcp

# Install dependencies and build
npm install
npm run build

# Start Planka (runs in Docker)
npm run up
```

Planka will be available at:
- URL: http://localhost:3333
- Login: demo@demo.demo
- Password: demo

### 2. Install PM Agent

```bash
# Go back to parent directory
cd ..

# Clone PM Agent repository
git clone https://github.com/lwgray/pm-agent.git
cd pm-agent

# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure PM Agent

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your ANTHROPIC_API_KEY (optional)
# If not provided, AI features will be disabled
```

### 4. Set Up Kanban MCP
```bash
# Clone kanban-mcp (if not already done)
cd ..
git clone https://github.com/your-repo/kanban-mcp.git
cd kanban-mcp

# Install dependencies
npm install

# Build
npm run build
```

## Starting PM Agent

### Method 1: Quick Start (Task Master Project)
```bash
# From pm-agent directory
python start_pm_agent_task_master.py
```

This will:
- Connect to the Task Master project
- Find or create a board automatically
- Start the MCP server for workers

### Method 2: Custom Configuration
```bash
# First, select your project and board
python select_task_master_board.py

# Then start PM Agent
python -m pm_agent_mvp_fixed
```

### Method 3: With Configuration File
```bash
# Edit config_pm_agent.json with your project/board IDs
# Then run:
python -m src.enhancements.configurable_pm_agent
```

## Verifying PM Agent is Running

You should see output like:
```
🚀 Starting PM Agent MVP...
✅ PM Agent ready to connect to Kanban on demand
🤖 Initializing AI engine...
✅ AI engine ready
🎯 PM Agent MVP is ready!
📋 Available tools:
   - register_agent
   - request_next_task
   - report_task_progress
   - report_blocker
   - get_project_status
   - get_agent_status
   - list_registered_agents
```

## Creating Test Tasks

### Option 1: Use Pre-built Todo App Tasks
```bash
python create_todo_app_tasks_fixed.py
```

### Option 2: Create Tasks Manually in Planka
1. Navigate to http://localhost:3333
2. Open your project board
3. Create cards with:
   - Clear titles
   - Detailed descriptions
   - Appropriate labels (backend, frontend, etc.)

## Testing with a Simple Worker

Create a test worker script:

```python
# test_worker.py
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_worker():
    # Connect to PM Agent
    server_params = StdioServerParameters(
        command="python",
        args=["pm_agent_mvp_fixed.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Register as a worker
            result = await session.call_tool("register_agent", {
                "agent_id": "test_worker_1",
                "name": "Test Worker",
                "role": "Backend Developer",
                "skills": ["python", "fastapi"]
            })
            print("Registration:", result)
            
            # Request a task
            result = await session.call_tool("request_next_task", {
                "agent_id": "test_worker_1"
            })
            print("Task assignment:", result)

if __name__ == "__main__":
    asyncio.run(test_worker())
```

## Stopping PM Agent

### Graceful Shutdown
Press `Ctrl+C` in the terminal where PM Agent is running.

### Force Stop (if needed)
```bash
# Find PM Agent process
ps aux | grep pm_agent

# Kill the process
kill <process_id>
```

## Next Steps

1. [Configure PM Agent](./configuration.md) for your specific project
2. [Build Worker Agents](./worker-agents.md) to automate development
3. [Explore API Reference](./api-reference.md) for all available tools
4. [Set up monitoring](./beyond-mvp.md#monitoring) for production use

## Common Issues

### "No board found"
- Run `python select_task_master_board.py` to create/select a board
- Or create a board manually in Planka

### "Connection refused"
- Ensure Planka is running at http://localhost:3333
- Check credentials in config file

### "No tasks available"
- Create tasks in Planka first
- Ensure tasks are in the "To Do" or "Backlog" list

For more troubleshooting, see [Troubleshooting Guide](./troubleshooting.md).