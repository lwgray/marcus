# Quickstart Guide

Get Marcus up and running in 5 minutes.

## Prerequisites

- **Python 3.10+** (Python 3.11+ recommended)
- **Docker & Docker Compose** (for Kanban server)
- **Git** (for version control)
- **AI Provider Access** (Anthropic, OpenAI, or local Ollama)

## Quick Install

### 1. Clone the Repository

```bash
git clone https://github.com/lwgray/marcus.git
cd marcus
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Marcus
pip install -e .
```

### 3. Start Kanban Server

Marcus uses a Kanban board for task management. Start Planka (recommended):

```bash
# Start Planka with Docker Compose
docker-compose up -d planka
```

Wait ~30 seconds for Planka to start, then access it at `http://localhost:3333`

**Default credentials**:
- Email: `demo@demo.demo`
- Password: `demo`

### 4. Configure Marcus

Create your configuration file:

```bash
cp config_marcus.example.json config_marcus.json
```

Edit `config_marcus.json`:

```json
{
  "project_id": "",
  "board_id": "",
  "project_name": "My First Project",
  "auto_find_board": true,
  "kanban": {
    "provider": "planka"
  },
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"
  },
  "ai": {
    "provider": "anthropic",
    "enabled": true,
    "anthropic_api_key": "YOUR_ANTHROPIC_API_KEY",
    "model": "claude-3-5-sonnet-20241022"
  },
  "features": {
    "events": true,
    "context": true,
    "memory": true,
    "visibility": false
  }
}
```

**AI Provider Options**:
- **Anthropic** (recommended): Set `provider: "anthropic"` and add your API key
- **OpenAI**: Set `provider: "openai"` and add your API key
- **Local (Ollama)**: See [Local LLM Setup](setup-local-llm.md)

### 5. Start Marcus

```bash
python -m marcus_mcp
```

You should see:
```
Marcus MCP Server starting...
Connected to Planka at http://localhost:3333
Waiting for agent connections...
```

## Your First Project

### Option 1: Natural Language (Recommended)

Marcus can create projects from natural language descriptions:

```bash
# In a new terminal, with Marcus MCP tools available:
# Use the create_project tool with a description:

{
  "tool": "create_project",
  "arguments": {
    "description": "Build a simple todo app with a React frontend and Python FastAPI backend. Include user authentication, CRUD operations for todos, and deployment to Docker."
  }
}
```

Marcus will:
1. Parse your description using NLP
2. Extract requirements, constraints, and objectives
3. Generate intelligent task breakdown
4. Infer dependencies automatically
5. Create organized project on Kanban board

### Option 2: Use Claude Desktop

If using Claude Desktop with MCP:

1. Add Marcus to your Claude Desktop config
2. Chat naturally: "Create a project to build a REST API for a blog platform"
3. Marcus creates the structured project automatically

### Option 3: Manual Project Creation

Create a project manually in Planka:
1. Go to `http://localhost:3333`
2. Create a new board
3. Add lists: "Planning", "Development", "Testing", "Deployment"
4. Create task cards in each list
5. Marcus will detect and manage them

## Connect an Agent

Agents are AI workers that complete tasks. Here's a simple agent:

```python
# simple_agent.py
import asyncio
from marcus_mcp import MarcusClient

async def main():
    client = MarcusClient()

    # Register agent
    await client.register_agent(
        agent_id="my-agent-1",
        capabilities=["python", "javascript", "testing"]
    )

    # Work loop
    while True:
        # Request task
        task = await client.request_next_task("my-agent-1")

        if task:
            print(f"Working on: {task['name']}")

            # Get context if needed
            if task.get('dependencies'):
                context = await client.get_task_context(task['id'])
                print(f"Context: {context}")

            # Do the work (your implementation here)
            # ...

            # Report progress
            await client.report_task_progress(
                task['id'],
                "my-agent-1",
                progress=100,
                details="Task completed successfully"
            )
        else:
            print("No tasks available, waiting...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
```

Run the agent:
```bash
python simple_agent.py
```

## Verify Everything Works

### Check Project Status

```python
from marcus_mcp import MarcusClient

client = MarcusClient()
status = await client.get_project_status()
print(status)
```

You should see:
- Project name and health metrics
- Task breakdown by phase
- Agent assignments
- Completion predictions

### Check Agent Status

```python
agent_status = await client.get_agent_status("my-agent-1")
print(agent_status)
```

You should see:
- Agent capabilities
- Current assignment
- Performance metrics
- Health status

### Test Connectivity

```python
pong = await client.ping()
print(pong)  # Should return system health info
```

## Common Issues

### Planka Won't Start
```bash
# Check if port 3333 is in use
lsof -i :3333

# Stop and restart
docker-compose down
docker-compose up -d planka
```

### Can't Connect to Marcus
- Verify Marcus is running: `ps aux | grep marcus`
- Check configuration in `config_marcus.json`
- Ensure Planka is accessible: `curl http://localhost:3333`

### AI Provider Errors
- Verify API key is correct
- Check API key has sufficient credits
- Try switching to local LLM: [Setup Guide](setup-local-llm.md)

### Agent Can't Find Tasks
- Verify agent is registered: Check agent list in Planka
- Ensure tasks exist in "Planning" or "Development" lists
- Check task dependencies are met

## Next Steps

Now that Marcus is running:

1. **Learn Core Concepts** → [Core Concepts](core-concepts.md)
2. **Understand Agent Workflows** → [Agent Workflows](../guides/agent-workflows/)
3. **Explore Project Management** → [Project Management](../guides/project-management/)
4. **Build Advanced Agents** → [API Reference](../api/)
5. **Customize Configuration** → Check `config_marcus.json` options

## Quick Commands Reference

```bash
# Start Marcus
python -m marcus_mcp

# Start Planka
docker-compose up -d planka

# Stop everything
docker-compose down
pkill -f marcus_mcp

# View logs
tail -f logs/marcus.log

# Run tests
pytest tests/

# Check health
curl http://localhost:3333/health
```

## Development Mode

For development and testing:

```bash
# Enable all features
export MARCUS_FEATURES_MEMORY=true
export MARCUS_FEATURES_VISIBILITY=true

# Use verbose logging
export MARCUS_LOG_LEVEL=DEBUG

# Start Marcus
python -m marcus_mcp
```

## Getting Help

- **Documentation**: [Full docs](../README.md)
- **Examples**: Check `examples/` directory
- **Issues**: [GitHub Issues](https://github.com/lwgray/marcus/issues)
- **Discussions**: [GitHub Discussions](https://github.com/lwgray/marcus/discussions)

---

**Congratulations!** You have Marcus running. Explore the documentation to learn about its powerful intelligent coordination capabilities.

---

*Ready to learn more? Check out [Core Concepts](core-concepts.md) →*
