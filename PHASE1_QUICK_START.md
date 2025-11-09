# Phase 1 Post-Project Analysis - Quick Start Guide

## What is Phase 1?

A complete system for storing, aggregating, and querying project execution history to answer: **"Did we build what we said we would build?"**

## Core Components

```
┌─────────────────────────────────────────────────────────┐
│                   Agent / MCP Client                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │    MCP Tool: query_project_history     │
        │  (src/marcus_mcp/tools/history.py)     │
        └────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │   ProjectHistoryQuery API              │
        │   (src/analysis/query_api.py)          │
        │  - 20+ query methods                   │
        │  - Filtering & pagination              │
        └────────────────────────────────────────┘
                          │
                          ▼
        ┌────────────────────────────────────────┐
        │  ProjectHistoryAggregator              │
        │  (src/analysis/aggregator.py)          │
        │  - Unifies 5 data sources              │
        │  - 60s cache                           │
        └────────────────────────────────────────┘
                          │
        ┌─────────┬──────────┬─────────┬─────────┐
        │         │          │         │         │
        ▼         ▼          ▼         ▼         ▼
    Decisions Artifacts Conversations Outcomes Profiles
    (SQLite)  (SQLite)    (JSONL)      (JSON)   (JSON)
```

## File Locations

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Data Models | `src/core/project_history.py` | 853 | Decision, ArtifactMetadata, ProjectSnapshot |
| Persistence | `src/core/persistence.py` | ~150 | SQLite backend |
| Aggregation | `src/analysis/aggregator.py` | 847 | Unify multiple data sources |
| Query API | `src/analysis/query_api.py` | 597 | Query interface |
| MCP Tool | `src/marcus_mcp/tools/history.py` | 498 | Agent-facing API |

## Key Data Files

```
data/
├── marcus.db                          # SQLite: decisions, artifacts
└── project_history/
    └── {project_id}/
        ├── snapshot.json              # Project completion state
        ├── decisions.json             # File backup
        └── artifacts.json             # File backup

logs/
└── conversations/
    └── conversations_*.jsonl          # Task instructions, metadata

data/marcus_state/
├── task_outcomes.json                 # TaskOutcome from Memory
└── agent_profiles.json                # AgentProfile from Memory
```

## How to Use Phase 1

### Option 1: Via MCP Tool (Agents)

```python
# In agent code via MCP
await query_project_history(
    project_id="my-project-123",
    query_type="summary",
    state=state
)

# Response:
# {
#     "success": True,
#     "data": {
#         "project_name": "...",
#         "total_tasks": 10,
#         "completed_tasks": 8,
#         ...
#     }
# }
```

### Option 2: Direct Python API

```python
from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery

aggregator = ProjectHistoryAggregator()
query = ProjectHistoryQuery(aggregator)

# Get project summary
summary = await query.get_project_summary(project_id)

# Find completed tasks
completed = await query.find_tasks_by_status(project_id, "completed")

# Analyze agent performance
metrics = await query.get_agent_performance_metrics(project_id, agent_id)
```

### Option 3: Example Script

```bash
python examples/query_project_history_example.py <project_id>
```

Shows all 10 query types with output.

## Available Query Types

### Project Queries
- `get_project_summary()` - High-level statistics
- `get_project_history()` - Complete unified history

### Task Queries
- `find_tasks_by_status(project_id, status)` - Filter by status
- `find_tasks_by_agent(project_id, agent_id)` - Filter by agent
- `find_tasks_in_timerange(project_id, start, end)` - Filter by time
- `find_blocked_tasks(project_id)` - Find problematic tasks
- `get_task_dependency_chain(project_id, task_id)` - Dependency graph

### Decision Queries
- `find_decisions_by_task(project_id, task_id)` - Decisions in a task
- `find_decisions_by_agent(project_id, agent_id)` - Decisions by agent
- `find_decisions_affecting_task(project_id, task_id)` - Impact analysis

### Artifact Queries
- `find_artifacts_by_task(project_id, task_id)` - Output of task
- `find_artifacts_by_type(project_id, type)` - Specification, design, etc.
- `find_artifacts_by_agent(project_id, agent_id)` - Work product by agent

### Agent Queries
- `get_agent_history(project_id, agent_id)` - Complete agent record
- `get_agent_performance_metrics(project_id, agent_id)` - KPIs

### Timeline Queries
- `search_timeline(project_id, event_type, agent_id, task_id, start_time, end_time)`

### Conversation Queries
- `search_conversations(project_id, keyword, agent_id, task_id)`

## Data Models

### Decision
What decision did agent make, why, and what's the impact?

```python
@dataclass
class Decision:
    decision_id: str              # Unique ID
    task_id: str                  # Where decided
    agent_id: str                 # Who decided
    timestamp: datetime            # When (UTC, timezone-aware)
    what: str                      # The choice
    why: str                       # Rationale
    impact: str                    # Downstream effects
    affected_tasks: list[str]      # Which tasks affected
    confidence: float              # 0.0-1.0
```

### ArtifactMetadata
What file was produced, by whom, from which task?

```python
@dataclass
class ArtifactMetadata:
    artifact_id: str               # Unique ID
    task_id: str                   # Source task
    agent_id: str                  # Creator
    timestamp: datetime             # When created
    filename: str                  # File name
    artifact_type: str             # Type: specification, design, api, etc.
    relative_path: str             # Relative to project root
    absolute_path: str             # Full path
    description: str               # What it is
    file_size_bytes: int           # Size
    sha256_hash: Optional[str]      # For integrity
    referenced_by_tasks: list[str]  # Consumers
```

### ProjectSnapshot
Final state of project.

```python
@dataclass
class ProjectSnapshot:
    project_id: str
    project_name: str
    snapshot_timestamp: datetime
    completion_status: str         # completed, abandoned, stalled

    # Statistics
    total_tasks: int
    completed_tasks: int
    completion_rate: float

    # Timing
    project_started: datetime
    project_completed: Optional[datetime]
    total_duration_hours: float

    # Team
    total_agents: int
    agent_summary: list[dict]

    # Quality
    team_velocity: float
    risk_level: str

    # Outcome
    application_works: Optional[bool]
    deployment_status: Optional[str]
    user_satisfaction: Optional[str]
```

## Critical Design Decisions

### 1. Conversation Logs are Authoritative
Task ID extraction uses conversation metadata, not Decision.project_id.
This ensures single source of truth.

**Why:** Prevents data inconsistencies if metadata diverges.

### 2. Pagination Capped at 10,000
Large result sets are capped to prevent memory exhaustion.

**Why:** Safety first; optimization possible in Phase 2.

### 3. 60-Second Cache
ProjectHistory is cached per-project for 60 seconds.

**Why:** Reduces I/O; ensures freshness; mirrors Cato pattern.

### 4. Hybrid Storage
- SQLite for decisions/artifacts (scalable, paginated)
- Files for snapshots (human-readable, archival)

**Why:** Different access patterns require different storage.

## Pagination

All queries support pagination via MCP tool:

```python
await query_project_history(
    project_id="proj-123",
    query_type="decisions",
    limit=100,          # Max 10000
    offset=200,         # Skip first 200
)
```

Returns:
```python
{
    "success": True,
    "data": [...],      # 100 decision dicts
    "count": 100
}
```

## Common Patterns

### Get all decisions from a task
```python
decisions = await query.find_decisions_by_task(project_id, task_id)
for decision in decisions:
    print(f"{decision.what} - {decision.why}")
```

### Find what agent did
```python
metrics = await query.get_agent_performance_metrics(project_id, agent_id)
print(f"Tasks completed: {metrics['tasks_completed']}")
print(f"Decisions made: {metrics['decisions_made']}")
print(f"Artifacts produced: {metrics['artifacts_produced']}")
```

### Analyze dependencies
```python
deps = await query.get_task_dependency_chain(project_id, task_id)
print(f"Task depends on {len(deps)} other tasks")
for dep_task in deps:
    print(f"  - {dep_task.name}")
```

### Search conversations
```python
messages = await query.search_conversations(
    project_id,
    keyword="API"
)
print(f"Found {len(messages)} messages mentioning API")
```

## Testing

### Run unit tests
```bash
pytest tests/unit/core/test_project_history.py
pytest tests/unit/core/test_project_history_sqlite.py
pytest tests/unit/analysis/test_query_api.py
```

### Test with real project data
```bash
python examples/query_project_history_example.py <project_id>
```

## Performance Considerations

**Current Performance (Phase 1):**
- Aggregation: ~1-2 seconds (includes conversation log parsing)
- Queries: <100ms (in-memory filtering)
- Cache hit: <10ms

**Bottlenecks for Phase 2:**
- Conversation log parsing (scans all files for project ID)
- Full ProjectHistory in memory (can be large)
- Client-side filtering with 10k limit

## Next Steps (Phase 2)

Phase 1 is the data foundation. Phase 2 adds AI-powered analysis:

1. Requirement Fidelity: Compare specs → instructions
2. Instruction Quality: Score clarity of task instructions
3. Root Cause Analysis: Analyze why tasks failed
4. Decision Impact: Link decisions to outcomes
5. Multi-Project Analysis: Find meta-patterns

**Phase 2 Strategy:**
- Create ProjectAnalysisQuery extending ProjectHistoryQuery
- Add AI analysis methods
- Populate TaskHistory analysis fields
- Don't modify Phase 1 data layer
- Build analysis layer on top

## Resources

- **Full Analysis:** `PHASE1_ARCHITECTURE_ANALYSIS.md` (1110 lines)
- **Summary:** `PHASE1_SUMMARY.txt`
- **Example:** `examples/query_project_history_example.py`
- **Test Examples:** `tests/unit/analysis/test_query_api.py`

## Debugging Tips

### Check data exists
```python
aggregator = ProjectHistoryAggregator()
history = await aggregator.aggregate_project("project-id")
print(f"Found {len(history.tasks)} tasks")
print(f"Found {len(history.decisions)} decisions")
print(f"Found {len(history.artifacts)} artifacts")
```

### Verify conversation logs
```bash
ls -la logs/conversations/
cat logs/conversations/conversations_*.jsonl | grep "project_id"
```

### Check SQLite database
```bash
sqlite3 data/marcus.db
.tables                           # Show tables
SELECT COUNT(*) FROM persistence WHERE collection='decisions';
.schema persistence               # Show schema
```

### Enable logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## FAQ

**Q: Why use conversation logs for task mapping?**
A: They're the authoritative source. Decision.project_id is only for validation.

**Q: What if I have 10,000+ decisions?**
A: Use pagination (limit/offset). Phase 2 can optimize with SQL offset.

**Q: How often is cache updated?**
A: Every 60 seconds, or on manual refresh. No cache invalidation on updates.

**Q: Can I use Phase 1 without Kanban?**
A: Yes, Kanban integration is optional. All other data sources are always available.

**Q: What happens if conversation logs are incomplete?**
A: Tasks without conversation metadata won't be included. Phase 2 should validate data quality.

---

**Ready to build Phase 2?** Read `PHASE1_ARCHITECTURE_ANALYSIS.md` sections 2-6 first.
