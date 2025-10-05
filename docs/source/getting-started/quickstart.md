# Quickstart Guide

Get Marcus up and running in 5 minutes.

## Prerequisites

- **Docker and Docker Compose** installed and running
- **Claude Code** or another MCP-compatible AI agent
- **AI Model** - Choose one:
  - **FREE:** Local model with Ollama (zero cost, [setup guide](setup-local-llm.md))
  - **Paid:** Anthropic or OpenAI API key

## Setup (Two-Stage Process)

📖 **Complete guide:** [DOCKER_QUICKSTART.md](../../../DOCKER_QUICKSTART.md)

### Stage 1: Start Planka and Postgres

```bash
# Clone the repository
git clone https://github.com/lwgray/marcus.git
cd marcus

# Start Planka first
docker-compose up -d postgres planka
```

Wait 10-15 seconds for Planka to initialize, then open http://localhost:3333

### Stage 2: Configure Planka Board

Login to Planka:
- Email: `demo@demo.demo`
- Password: `demo`  # pragma: allowlist secret

### Stage 2: Configure and Start Marcus

```bash
# Copy and edit the configuration
cp config_marcus.example.json config_marcus.json
```

Edit `config_marcus.json` with:
- Your AI configuration:
  - **For paid API:** Add your Anthropic or OpenAI API key
  - **For free local:** Set `"provider": "local"` and `"local_model": "qwen2.5-coder:7b"` (see [setup guide](setup-local-llm.md))

  {
  "kanban": {
    "provider": "planka"
  },
  "planka": {
    "base_url": "http://localhost:3333",
    "email": "demo@demo.demo",
    "password": "demo"  # pragma: allowlist secret
  },
  "ai": {
    "provider": "local",
    "enabled": true,
    "local_model": "qwen2.5-coder:7b",
    "local_url": "http://localhost:11434/v1",
    "local_key": "none",
    "anthropic_api_key": "",
    "openai_api_key": "",
    "model": "claude-3-sonnet-20240229"
  },
  "features": {
    "events": true,
    "context": true,
    "memory": false,
    "visibility": false
  }
}

```bash
# Start Marcus
docker-compose up -d marcus
```

Marcus is now running at http://localhost:4298/mcp

## 2. Connect Your AI Agent

For Claude Code:
```bash
# Add Marcus MCP server
claude mcp add --transport http marcus http://localhost:4298/mcp

# Marcus provides MCP-compatible endpoints for any agent
```

### 3. Configure Your Agent

Use the Marcus workflow prompt to establish autonomous work patterns:

```bash
# Copy the contents of prompts/Agent_prompt.md as your agent's system prompt
# This gives your agent:
# - Autonomous work loop (register → request → work → report → repeat)
# - Context sharing through artifacts and decisions
# - Progress reporting and error recovery
# - Dependency handling
```

See [docs/agent-workflow.md](../guides/agent-workflows/agent-workflow.md) for all workflow components.

### 4. Start Building

Tell your configured agent:
```
"Create a project for a todo app with Marcus, then register an agent and begin work"
```

The agent will automatically:
1. Create a Planka Project and board from your description
2. Register your ai agent with Marcus
3. Request and work on tasks continuously
4. Report progress as it goes
5. Keep working until all tasks are done

## Essentially You'll See

When your agent starts working with Marcus:

- ✅ Agent registers itself ("Agent claude-1 registered")
- ✅ Project created on Planka with structured tasks
- ✅ Agent continuously pulling and completing tasks
- ✅ Progress updates: "25% complete", "50% complete", etc.
- ✅ At localhost:333 you can see Tasks moving through board columns: TODO → IN PROGRESS → DONE
- ✅ Context flowing between tasks (API specs → implementation → tests)

## Add More Agents (Optional)

Want multiple agents working in parallel? Three options:

### Option A: Multiple Windows (Simplest)
Open a new terminal/Claude window, connect to Marcus, and start another agent. Both agents will pull different tasks from the same board.

### Option B: Claude Subagents
If using Claude, launch subagents with the Task tool. Each subagent automatically registers and works independently.

### Option C: Git Worktrees (Prevents Code Conflicts)
```bash
git worktree add ../project-agent2 -b agent2-branch
# Each agent works in its own directory/branch
# Merge when ready
```

## Build a Custom Agent (Advanced)

If you want to build your own agent programmatically:

```python
"""
Demo script showing how to use WorkerMCPClient with stdio connections.

This demonstrates:
1. Connecting via stdio (spawns separate Marcus instance for isolated testing)

Note: HTTP connections are available via connect_to_marcus_http() but require
      a Marcus server configured for external HTTP access with proper CORS settings.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.client import WorkerMCPClient  # noqa: E402


def pretty_print_result(label: str, result: Any) -> None:
    """Pretty print MCP tool results."""
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        # Extract text from MCP result
        text = result.content[0].text if result.content else str(result)
        try:
            # Try to parse and pretty print JSON
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def demo_stdio_connection() -> None:
    """
    Demo: Connect via stdio (spawns a separate Marcus instance).

    Use this when:
    - You want an isolated testing environment
    - You don't care about sharing state with other Marcus instances
    - You want to test without affecting the main Marcus server
    - You're running automated tests or development workflows

    This is the RECOMMENDED way to test WorkerMCPClient!
    """
    print("\n" + "=" * 60)
    print("DEMO: STDIO Connection (Separate Test Instance)")
    print("=" * 60)

    client = WorkerMCPClient()

    try:
        print("\n📡 Starting separate Marcus instance for testing...")
        async with client.connect_to_marcus() as session:
            # First authenticate as admin to get access to ALL MCP tools
            # Options: "observer", "developer", "agent", "admin"
            print("\n🔐 Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "stdio-worker-1",
                    "client_type": "admin",  # Admin access
                    "role": "admin",
                    "metadata": {"test_mode": True},
                },
            )
            print("✅ Authenticated as admin (full access)")


            # Register agent
            print("\n🔧 Registering test agent...")
            result = await client.register_agent(
                agent_id="stdio-worker-1",
                name="STDIO Test Worker",
                role="Developer",
                skills=["python", "testing"],
            )
            pretty_print_result("✅ Agent registered:", result)

            # Request a task
            print("\n📋 Requesting next task...")
            task = await client.request_next_task("stdio-worker-1")
            pretty_print_result("Task received:", task)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Run the stdio demo."""
    print("\n🚀 WorkerMCPClient Connection Demo")
    print("=" * 60)
    print("\nThis demo shows how to programmatically test Marcus")
    print("by spawning a separate instance via stdio.")
    print("\nNote: This may take 10-15 seconds to initialize...")

    await demo_stdio_connection()

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("\n💡 Tip: For HTTP connections, use connect_to_marcus_http()")
    print("   But you'll need a Marcus server with external HTTP access configured.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

## Verify Everything Works

### Check Agent Status via MCP Tools

Using MCP tools from your agent:
- `get_agent_status` - Check agent capabilities, assignments, and health
- `get_project_status` - View project health, tasks, and predictions
- `ping` - Test Marcus server connectivity

### Monitor on GitHub

Go to your GitHub project board to see:
- Tasks organized by status (TODO, IN PROGRESS, DONE)
- Agent assignments on each task
- Progress updates in task comments
- Dependency relationships between tasks

## Common Issues

### "Connection refused"
Ensure Marcus Docker container is running on port 4298:
```bash
docker ps | grep marcus
```

### "No tasks available"
Agent needs to create a project first using natural language description.

### "Agent not registered"
Agent must call `register_agent` before requesting tasks.

### "GitHub auth failed"
- Check GitHub token has `project` scope permissions
- Verify token is correctly set in environment or config
- Test token: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/user`

### "Failed to create any tasks" (Planka)
**Cause:** Board has no lists/columns to add tasks to.

**Solution:** Open Planka board at http://localhost:3333 and create these lists:
- Backlog
- In Progress
- Blocked
- Done

### "find_target_list failed" (Planka)
**Cause:** Same as above - Marcus can't find a list/column on the board.

**Solution:** Create at least one list on your Planka board before creating projects.

### AI Provider Errors
- **Paid APIs:** Verify API key is correct and has sufficient credits
- **Alternative:** Switch to 100% free local LLM - no API costs ever! [Setup Guide](setup-local-llm.md)

## Next Steps

Now that Marcus is running:

1. **Learn Core Concepts** → [Core Concepts](core-concepts.md)
2. **Understand Agent Workflows** → [Agent Workflows](../guides/agent-workflows/)
3. **Explore Project Management** → [Project Management](../guides/project-management/)
4. **Build Advanced Agents** → [API Reference](../api/)
5. **Customize Configuration** → Check `config_marcus.json` options

## Quick Commands Reference

```bash
# Start services (two-stage)
docker-compose up -d postgres planka  # Stage 1: Start Planka
# Create project/board and lists in Planka
docker-compose up -d marcus           # Stage 2: Start Marcus

# View logs
docker-compose logs -f marcus         # Marcus logs
docker-compose logs -f planka         # Planka logs
docker-compose logs -f                # All logs

# Stop services
docker-compose down                   # Stop all
docker-compose restart marcus         # Restart just Marcus

# Rebuild Marcus (after code changes)
docker-compose build marcus
docker-compose up -d marcus

# Clean slate (removes all data)
docker-compose down -v

# Run tests (development)
pytest tests/
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
