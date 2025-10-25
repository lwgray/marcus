# Examples

Working code examples demonstrating Marcus functionality and common patterns.

## Examples Overview

| Example | Purpose | Complexity |
|---------|---------|------------|
| `autonomous_agent_workflow.py` | Complete agent lifecycle | ⭐⭐⭐ Advanced |
| `agent_select_project.py` | Project selection pattern | ⭐⭐ Intermediate |
| `task_decomposition_demo.py` | Task breakdown strategies | ⭐⭐ Intermediate |
| `inspector_demo.py` | Inspector tool usage | ⭐ Beginner |
| `demo_http_connection.py` | HTTP transport integration | ⭐ Beginner |
| `demo_stdio_connection.py` | Stdio transport integration | ⭐ Beginner |

## Quick Start

### Running Examples

All examples can be run directly:

```bash
# Run autonomous agent workflow
python autonomous_agent_workflow.py

# Run with custom configuration
python autonomous_agent_workflow.py --config my_config.yaml

# Run in verbose mode
python autonomous_agent_workflow.py --verbose
```

### Prerequisites

```bash
# Install dependencies
pip install -r ../../requirements.txt

# Ensure Marcus MCP server is running
# Set environment variables
export KANBAN_URL="your_kanban_url"
export KANBAN_TOKEN="your_token"
```

## Detailed Example Documentation

### autonomous_agent_workflow.py ⭐⭐⭐

Demonstrates the complete lifecycle of an autonomous agent working with Marcus.

**What It Shows**:
- Agent registration
- Task requesting loop
- Task execution
- Progress reporting
- Blocker handling
- Completion workflow

**Code Structure**:
```python
async def main():
    # 1. Register agent
    agent_id = await register_agent(
        name="Backend Developer",
        capabilities=["python", "fastapi", "postgres"]
    )

    # 2. Work loop
    while True:
        # Request task
        task = await request_next_task(agent_id)

        if task is None:
            break  # No more work

        # Execute task
        try:
            await execute_task(task)
            await report_progress(task.id, status="completed")
        except Exception as e:
            await report_blocker(task.id, error=str(e))
```

**Key Concepts**:
- Autonomous agent pattern
- Task lifecycle management
- Error recovery
- Progress reporting milestones

**Usage**:
```bash
# Basic run
python autonomous_agent_workflow.py

# With specific agent type
python autonomous_agent_workflow.py --role backend

# With custom capabilities
python autonomous_agent_workflow.py --skills "python,fastapi,postgres"

# Dry run (no actual task execution)
python autonomous_agent_workflow.py --dry-run
```

**Expected Output**:
```
=== AUTONOMOUS AGENT WORKFLOW ===

[1/6] Registering agent...
  ✓ Registered as: agent_backend_001

[2/6] Entering work loop...
  → Requesting next task...
  ✓ Received: task_5 - Implement authentication

[3/6] Executing task_5...
  ✓ Progress: 25% - Created auth models
  ✓ Progress: 50% - Implemented JWT logic
  ✓ Progress: 75% - Added tests
  ✓ Progress: 100% - Task complete

[4/6] Requesting next task...
  → No more tasks available

[5/6] Reporting completion...
  ✓ All assigned tasks completed

✅ Workflow complete!
   Tasks completed: 3
   Blockers encountered: 0
   Total time: 15m 32s
```

**When to Use**:
- Learning agent patterns
- Implementing new agent types
- Testing agent workflows
- Understanding Marcus orchestration

---

### agent_select_project.py ⭐⭐

Shows how agents discover and select projects to work on.

**What It Shows**:
- Project listing and filtering
- Project selection logic
- Skill matching
- Workload balancing

**Code Structure**:
```python
async def select_project(agent_capabilities):
    # 1. List available projects
    projects = await list_projects()

    # 2. Filter by capabilities
    suitable = [
        p for p in projects
        if match_capabilities(p.requirements, agent_capabilities)
    ]

    # 3. Select best match
    selected = rank_projects(suitable, agent_capabilities)

    return selected[0] if selected else None
```

**Key Concepts**:
- Project discovery
- Capability matching
- Priority ranking
- Workload distribution

**Usage**:
```bash
# List available projects
python agent_select_project.py --list

# Select project with specific skills
python agent_select_project.py --skills "react,typescript"

# Show selection logic
python agent_select_project.py --explain

# Select and start work
python agent_select_project.py --auto-start
```

**When to Use**:
- Building project selection logic
- Implementing capability matching
- Optimizing agent allocation
- Understanding project discovery

---

### task_decomposition_demo.py ⭐⭐

Demonstrates different strategies for breaking down complex tasks into subtasks.

**What It Shows**:
- Decomposition strategies
- Dependency identification
- Effort estimation
- Parallelization opportunities

**Decomposition Strategies**:
1. **Sequential**: Break into steps (A → B → C)
2. **Parallel**: Independent subtasks (A, B, C)
3. **Hierarchical**: Nested breakdown (A → [A1, A2], B → [B1, B2])
4. **Feature-based**: By functionality (Auth, API, UI)

**Code Structure**:
```python
def decompose_task(task, strategy="auto"):
    if strategy == "sequential":
        return create_sequential_subtasks(task)
    elif strategy == "parallel":
        return create_parallel_subtasks(task)
    elif strategy == "hierarchical":
        return create_hierarchical_subtasks(task)
    else:
        return auto_decompose(task)  # AI-powered
```

**Usage**:
```bash
# Auto decomposition
python task_decomposition_demo.py --task "Build REST API"

# Specific strategy
python task_decomposition_demo.py --task "Build REST API" --strategy parallel

# Show dependency graph
python task_decomposition_demo.py --task "Build REST API" --show-deps

# Estimate effort
python task_decomposition_demo.py --task "Build REST API" --estimate
```

**Output Example**:
```
=== TASK DECOMPOSITION ===
Original: Build REST API
Strategy: hierarchical

DECOMPOSITION:
1. Backend Setup (Sequential)
   1.1. Initialize project structure
   1.2. Configure database
   1.3. Setup testing framework

2. Core Features (Parallel)
   2.1. Authentication endpoints
   2.2. User management
   2.3. Data models

3. Integration (Sequential)
   3.1. Connect components
   3.2. End-to-end tests
   3.3. Documentation

ANALYSIS:
  Total subtasks: 9
  Parallelizable: 3 (33%)
  Critical path: 1 → 1.1 → 1.2 → 1.3 → 2.* → 3 → 3.1 → 3.2 → 3.3
  Estimated time: 6-8 hours
  Recommended agents: 3
```

**When to Use**:
- Designing task breakdown logic
- Optimizing parallelization
- Understanding decomposition strategies
- Improving project planning

---

### inspector_demo.py ⭐

Basic demonstration of Marcus Inspector tool for debugging.

**What It Shows**:
- Inspector initialization
- State inspection
- Real-time monitoring
- Debugging utilities

**Code Structure**:
```python
from marcus.inspector import Inspector

async def demo():
    inspector = Inspector()

    # Inspect agent state
    state = await inspector.inspect_agent(agent_id)

    # Monitor board
    await inspector.monitor_board(board_id, interval=5)

    # Check task status
    task_info = await inspector.inspect_task(task_id)
```

**Usage**:
```bash
# Inspect specific agent
python inspector_demo.py --agent agent_001

# Monitor board
python inspector_demo.py --board 12345 --monitor

# Check task details
python inspector_demo.py --task task_42

# Full system inspection
python inspector_demo.py --full
```

**When to Use**:
- Learning Inspector API
- Debugging agent behavior
- Monitoring system state
- Building custom tools

---

### demo_http_connection.py ⭐

Demonstrates HTTP transport integration with Marcus MCP.

**What It Shows**:
- HTTP client setup
- Request/response handling
- Error handling
- Authentication

**Code Structure**:
```python
import httpx
from marcus.transports import HTTPTransport

async def demo():
    # Initialize HTTP transport
    transport = HTTPTransport(
        url="http://localhost:3000",
        auth_token="your_token"
    )

    # Make requests
    response = await transport.call_tool(
        "request_next_task",
        {"agent_id": "agent_001"}
    )

    return response
```

**Usage**:
```bash
# Basic HTTP demo
python demo_http_connection.py

# Custom URL
python demo_http_connection.py --url http://localhost:8000

# With authentication
python demo_http_connection.py --token your_token

# Verbose logging
python demo_http_connection.py --verbose
```

**When to Use**:
- Integrating HTTP clients
- Testing HTTP transport
- Understanding MCP over HTTP
- Building web integrations

---

### demo_stdio_connection.py ⭐

Demonstrates Stdio transport integration with Marcus MCP.

**What It Shows**:
- Stdio transport setup
- Process communication
- Input/output handling
- Process lifecycle

**Code Structure**:
```python
from marcus.transports import StdioTransport

async def demo():
    # Initialize Stdio transport
    transport = StdioTransport(
        command=["python", "-m", "marcus.server"],
        cwd="/path/to/marcus"
    )

    # Communicate via stdin/stdout
    response = await transport.call_tool(
        "request_next_task",
        {"agent_id": "agent_001"}
    )

    return response
```

**Usage**:
```bash
# Basic stdio demo
python demo_stdio_connection.py

# Custom command
python demo_stdio_connection.py --command "python -m my_server"

# Custom working directory
python demo_stdio_connection.py --cwd /path/to/dir

# Debug mode
python demo_stdio_connection.py --debug
```

**When to Use**:
- Integrating stdio clients
- Testing stdio transport
- Understanding MCP over stdio
- Building CLI integrations

## Common Patterns

### Pattern 1: Agent Registration and Work Loop

```python
# From autonomous_agent_workflow.py
async def agent_lifecycle():
    # Register
    agent_id = await register_agent(name="Developer", skills=["python"])

    # Work loop
    while True:
        task = await request_next_task(agent_id)
        if not task:
            break

        await execute_task(task)
        await report_progress(task.id, "completed")
```

**Use for**: Building autonomous agents

---

### Pattern 2: Project Selection

```python
# From agent_select_project.py
async def select_best_project(agent_capabilities):
    projects = await list_projects()

    scored = [
        (p, score_match(p, agent_capabilities))
        for p in projects
    ]

    best = max(scored, key=lambda x: x[1])
    return best[0]
```

**Use for**: Project allocation logic

---

### Pattern 3: Task Decomposition

```python
# From task_decomposition_demo.py
def decompose_hierarchical(task):
    subtasks = []

    for phase in ["setup", "implementation", "testing"]:
        phase_tasks = analyze_phase(task, phase)
        subtasks.extend(phase_tasks)

    return subtasks
```

**Use for**: Breaking down complex tasks

---

### Pattern 4: Transport Initialization

```python
# From demo_http_connection.py and demo_stdio_connection.py
async def init_transport(transport_type="http"):
    if transport_type == "http":
        return HTTPTransport(url=MCP_URL, auth=AUTH_TOKEN)
    else:
        return StdioTransport(command=["python", "-m", "marcus.server"])
```

**Use for**: Flexible transport selection

## Customization

### Modifying Examples

All examples accept configuration:

```python
# At the top of any example file
CONFIG = {
    "agent_name": "My Agent",
    "capabilities": ["python", "javascript"],
    "verbose": True,
    "dry_run": False,
}
```

### Creating New Examples

Template for new examples:

```python
#!/usr/bin/env python3
"""
Example: [Your Example Name]

Demonstrates: [What it shows]

Usage:
    python your_example.py [options]
"""
import asyncio
from marcus import MarcusClient

async def main():
    """Main demonstration function."""
    # Your example code here
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

## Learning Path

### Beginner Path
1. Start with `inspector_demo.py`
2. Try `demo_http_connection.py`
3. Experiment with `demo_stdio_connection.py`
4. Understand transport basics

### Intermediate Path
1. Study `task_decomposition_demo.py`
2. Explore `agent_select_project.py`
3. Understand task and project management
4. Build custom selection logic

### Advanced Path
1. Master `autonomous_agent_workflow.py`
2. Implement custom agent types
3. Build full agent systems
4. Contribute new examples

## Troubleshooting

### Import Errors
```bash
# Ensure Marcus is in PYTHONPATH
export PYTHONPATH="/Users/lwgray/dev/marcus:$PYTHONPATH"
```

### Connection Errors
- Verify MCP server is running
- Check URL and credentials
- Review error logs

### Example Crashes
- Check prerequisites are met
- Verify environment variables
- Run with `--verbose` for details
- Review example-specific documentation

## Contributing Examples

When adding new examples:
1. Follow the template structure
2. Include comprehensive docstrings
3. Add to this README
4. Test thoroughly
5. Document prerequisites

## Requirements

- Python 3.8+
- Marcus MCP server
- Dependencies: See main requirements.txt
- For HTTP examples: Running HTTP server
- For Stdio examples: Marcus server installation

## Support

For example-related questions:
- Review example docstrings
- Check specific example comments
- Run with `--help` flag
- See main dev-tools/README.md
