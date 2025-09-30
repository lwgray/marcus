# API Reference Overview

Marcus provides multiple APIs for different use cases:

## MCP (Model Context Protocol) Tools

Marcus implements MCP server tools that AI agents use to coordinate and execute tasks. These tools are the primary interface for agent-to-Marcus communication.

[View MCP Tools Documentation](./README.md)

## Python API

The core Marcus Python API provides programmatic access to all Marcus functionality:

### Core Modules

- **`marcus_mcp.client`** - Client for connecting to Marcus MCP server
- **`marcus_mcp.server`** - MCP server implementation
- **`core.models`** - Data models (Task, Project, Agent, etc.)
- **`core.kanban`** - Kanban board integration
- **`core.memory`** - Memory system (Working, Episodic, Semantic, Procedural)

### Intelligence & AI

- **`ai.intelligence_engine`** - AI-powered decision making
- **`ai.nlp`** - Natural language processing
- **`intelligence.recommendations`** - Task recommendations
- **`intelligence.learning`** - Pattern learning

### Integration

- **`integrations.kanban`** - Kanban board providers (GitHub Projects, etc.)
- **`integrations.github`** - GitHub integration
- **`api.routes`** - REST API endpoints

### Utilities

- **`utils`** - Helper functions
- **`config`** - Configuration management
- **`logging`** - Logging and visualization

## REST API (Future)

Marcus will provide REST API endpoints for web-based integrations and dashboards.

*Coming in future releases*

## Quick Start

### Using MCP Tools

```python
from marcus_mcp import MarcusClient

# Connect to Marcus
client = MarcusClient()

# Register an agent
await client.register_agent(
    agent_id="worker-1",
    capabilities=["python", "testing"]
)

# Get next task
task = await client.request_next_task("worker-1")
```

### Using Python API Directly

```python
from src.core.models import Project, Task
from src.core.kanban import KanbanClient

# Create project
project = Project(name="My Project", description="...")

# Create Kanban client
kanban = KanbanClient(provider="github", config={...})

# Sync tasks
await kanban.sync_tasks(project)
```

## API Documentation

- [MCP Tools Reference](./README.md) - Complete MCP tool documentation
- Core API Reference (Coming soon) - Python API documentation
- REST API Reference (Coming soon) - HTTP endpoints

## See Also

- [Agent Workflows](/guides/agent-workflows/agent-workflow) - How agents use the API
- [Systems Architecture](/systems/README) - Internal system documentation
