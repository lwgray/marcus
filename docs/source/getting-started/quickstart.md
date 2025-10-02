# Quickstart Guide

Get Marcus up and running in 5 minutes.

## Prerequisites

- **Docker** (for running Marcus)
- **GitHub Account** with a [personal access token](https://github.com/settings/tokens) (needs `project` scope)
- **Claude Code** or another MCP-compatible AI agent
- **AI API Key** (Anthropic, OpenAI, or local Ollama)

## Quick Install

### 1. Run Marcus with Docker

```bash
# Quick start with environment variables
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=your_github_token \
  -e ANTHROPIC_API_KEY=your_api_key \
  marcus/marcus:latest

# Or build from source
git clone https://github.com/lwgray/marcus.git
cd marcus
cp config_marcus.example.json config_marcus.json
# Edit config_marcus.json with your settings
docker build -t marcus .
docker run -p 4298:4298 -v $(pwd)/config_marcus.json:/app/config_marcus.json marcus
```

### 2. Connect Your AI Agent

For Claude Code:
```bash
# Add Marcus MCP server
claude mcp add http://localhost:4298/marcus

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
"Create a project for a todo app with Marcus and start working"
```

The agent will automatically:
1. Register with Marcus
2. Create a GitHub project board from your description
3. Request and work on tasks continuously
4. Report progress as it goes
5. Keep working until all tasks are done

## What You'll See

When your agent starts working with Marcus:

- ✅ Agent registers itself ("Agent claude-1 registered")
- ✅ Project created on GitHub with structured tasks
- ✅ Agent continuously pulling and completing tasks
- ✅ Progress updates: "25% complete", "50% complete", etc.
- ✅ Tasks moving through board columns: TODO → IN PROGRESS → DONE
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
# simple_agent.py
import asyncio
from src.worker.client import WorkerMCPClient

async def main():
    client = WorkerMCPClient()

    # Connect to Marcus MCP server
    async with client.connect_to_marcus() as session:
        # Register agent with skills
        await client.register_agent(
            agent_id="my-agent-1",
            name="Backend Developer",
            role="Developer",
            skills=["python", "javascript", "testing"]
        )

        # Work loop
        while True:
            # Request next task
            task_result = await client.request_next_task("my-agent-1")

            if task_result.get('task'):
                task = task_result['task']
                print(f"Working on: {task['title']}")

                # Report progress milestones
                await client.report_task_progress(
                    agent_id="my-agent-1",
                    task_id=task['id'],
                    status="in_progress",
                    progress=50
                )

                # Do the work (your implementation here)
                # ...

                # Report completion
                await client.report_task_progress(
                    agent_id="my-agent-1",
                    task_id=task['id'],
                    status="completed",
                    progress=100
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

### AI Provider Errors
- Verify API key is correct
- Check API key has sufficient credits
- Try switching to local LLM: [Setup Guide](setup-local-llm.md)

## Next Steps

Now that Marcus is running:

1. **Learn Core Concepts** → [Core Concepts](core-concepts.md)
2. **Understand Agent Workflows** → [Agent Workflows](../guides/agent-workflows/)
3. **Explore Project Management** → [Project Management](../guides/project-management/)
4. **Build Advanced Agents** → [API Reference](../api/)
5. **Customize Configuration** → Check `config_marcus.json` options

## Quick Commands Reference

```bash
# Start Marcus with Docker
docker run -p 4298:4298 \
  -e GITHUB_TOKEN=your_token \
  -e ANTHROPIC_API_KEY=your_key \
  marcus/marcus:latest

# Stop Marcus
docker stop $(docker ps -q --filter ancestor=marcus/marcus)

# View Marcus logs
docker logs -f $(docker ps -q --filter ancestor=marcus/marcus)

# Build from source
git clone https://github.com/lwgray/marcus.git
cd marcus
docker build -t marcus .

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
