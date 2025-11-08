# Phase 1 Quickstart: Project History Queries

Phase 1 provides the data foundation for answering: **"Did we build what we said we would build?"**

You can use Phase 1 independently to query project execution history without needing Phase 2 (AI analysis) or Phase 3 (Cato integration).

## What Phase 1 Gives You

- **Task History**: Find tasks by status, agent, time range, blockers
- **Decision Tracking**: Search architectural decisions and their impact
- **Artifact Tracing**: Find produced artifacts by type, task, or agent
- **Agent Performance**: Calculate completion rates, avg task hours, productivity
- **Timeline Search**: Query events by type, agent, task, or time
- **Conversation Search**: Find messages by keyword, agent, or task
- **Project Summary**: Get high-level statistics and completion metrics

## Quick Usage Examples

### Option 1: MCP Tools (For Claude Code/Agents)

```python
# Get project summary
await mcp__marcus__query_project_history(
    project_id="proj123",
    query_type="summary"
)

# Find completed tasks
await mcp__marcus__query_project_history(
    project_id="proj123",
    query_type="tasks",
    status="completed"
)

# Find blocked tasks
await mcp__marcus__query_project_history(
    project_id="proj123",
    query_type="blocked_tasks"
)

# Get agent performance
await mcp__marcus__query_project_history(
    project_id="proj123",
    query_type="agent_metrics",
    agent_id="agent-456"
)

# Search conversations
await mcp__marcus__query_project_history(
    project_id="proj123",
    query_type="conversations",
    keyword="authentication"
)

# List all projects with history
await mcp__marcus__list_project_history_files()
```

### Option 2: Python API (For Scripts/Notebooks)

```python
from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery

# Initialize
aggregator = ProjectHistoryAggregator()
query = ProjectHistoryQuery(aggregator)

# Get summary
summary = await query.get_project_summary("proj123")
print(f"Completion Rate: {summary['completion_rate']}%")

# Find completed tasks
completed = await query.find_tasks_by_status("proj123", "completed")
print(f"Completed: {len(completed)} tasks")

# Find blocked tasks
blocked = await query.find_blocked_tasks("proj123")
for task in blocked:
    print(f"Blocked: {task.title}")

# Agent performance
metrics = await query.get_agent_performance_metrics("proj123", "agent-456")
print(f"Avg hours per task: {metrics['avg_task_hours']}")

# Search decisions
decisions = await query.find_decisions_by_agent("proj123", "agent-456")

# Find artifacts
specs = await query.find_artifacts_by_type("proj123", "specification")
```

## Available Query Types (MCP)

When using `query_project_history`, these are the available `query_type` values:

1. **`summary`** - Get project summary statistics
   - No additional filters needed

2. **`tasks`** - Find tasks
   - Filters: `status`, `agent_id`, `start_time`, `end_time`

3. **`blocked_tasks`** - Find tasks with blockers
   - No additional filters needed

4. **`task_dependencies`** - Get dependency chain
   - Required: `task_id`

5. **`decisions`** - Find decisions
   - Filters: `task_id`, `agent_id`, `affecting_task_id`

6. **`artifacts`** - Find artifacts
   - Filters: `task_id`, `artifact_type`, `agent_id`

7. **`agent_history`** - Get agent history
   - Required: `agent_id`

8. **`agent_metrics`** - Get agent performance
   - Required: `agent_id`

9. **`timeline`** - Search timeline events
   - Filters: `event_type`, `agent_id`, `task_id`, `start_time`, `end_time`

10. **`conversations`** - Search conversations
    - Filters: `keyword`, `agent_id`, `task_id`

## Finding Your Project ID

```python
# List all projects with history
result = await mcp__marcus__list_project_history_files()

for project in result['projects']:
    print(f"ID: {project['project_id']}")
    print(f"Name: {project['project_name']}")
    print(f"Last Updated: {project['last_updated']}")
```

## Data Sources

Phase 1 automatically aggregates data from:

1. **Conversation Logs** - Agent/human conversations
2. **Agent Events** - Task assignments, progress updates
3. **Memory System** - Stored context and decisions
4. **Project History** - Decisions and artifacts (new in Phase 1)
5. **Kanban Board** - Task states and metadata

## Performance

- **Caching**: 60-second TTL cache (like Cato)
- **Fast Queries**: Most queries complete in <100ms
- **Efficient Storage**: JSONL append-only logs, atomic writes

## Example Use Cases

### 1. Daily Standup Report

```python
# What did we accomplish yesterday?
yesterday = datetime.now(timezone.utc) - timedelta(days=1)
today = datetime.now(timezone.utc)

recent = await query.find_tasks_in_timerange("proj123", yesterday, today)
completed = [t for t in recent if t.status == "completed"]

print(f"Completed yesterday: {len(completed)} tasks")
```

### 2. Sprint Review

```python
# Get sprint summary
summary = await query.get_project_summary("proj123")

print(f"Sprint Velocity:")
print(f"  Completion Rate: {summary['completion_rate']}%")
print(f"  Total Tasks: {summary['total_tasks']}")
print(f"  Completed: {summary['completed_tasks']}")
print(f"  Active Agents: {summary['active_agents']}")
```

### 3. Debugging Blocked Tasks

```python
# Find what's blocking progress
blocked = await query.find_blocked_tasks("proj123")

for task in blocked:
    print(f"\nBlocked: {task.title}")

    # Get dependency chain
    deps = await query.get_task_dependency_chain("proj123", task.task_id)
    print(f"  Waiting on {len(deps)} dependencies")

    # Find related decisions
    decisions = await query.find_decisions_affecting_task("proj123", task.task_id)
    print(f"  Related decisions: {len(decisions)}")
```

### 4. Agent Performance Review

```python
# Analyze agent productivity
history = await query.get_project_history("proj123")

for agent in history.agents:
    metrics = await query.get_agent_performance_metrics("proj123", agent.agent_id)

    print(f"\nAgent: {agent.name}")
    print(f"  Completed: {metrics['tasks_completed']}")
    print(f"  Avg Hours: {metrics['avg_task_hours']}")
    print(f"  Decisions: {metrics['decisions_made']}")
    print(f"  Artifacts: {metrics['artifacts_produced']}")
```

### 5. Architecture Decision Review

```python
# Review all architectural decisions
decisions = await query.find_decisions_by_agent("proj123", "architect-agent")

for decision in decisions:
    print(f"\nDecision: {decision.decision_text}")
    print(f"  Context: {decision.context}")
    print(f"  Affects: {len(decision.affected_tasks)} tasks")
```

## Running the Example

```bash
# Run the comprehensive example
python examples/query_project_history_example.py

# Or use in your own scripts
from src.analysis.query_api import ProjectHistoryQuery
from src.analysis.aggregator import ProjectHistoryAggregator

aggregator = ProjectHistoryAggregator()
query = ProjectHistoryQuery(aggregator)

# Your queries here...
```

## Data Storage Location

Project history is stored in:
```
/path/to/marcus/data/project_history/{project_id}/
├── decisions.jsonl      # Architectural decisions
├── artifacts.jsonl      # Artifact metadata
└── snapshot.json        # Project snapshot
```

## Next Steps

- **Phase 2**: LLM-powered analysis for deeper insights
- **Phase 3**: Cato integration for natural language queries

But Phase 1 works independently - start querying your project history now!
