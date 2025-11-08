# Phase 1: Data Persistence & Aggregation Layer

## Overview

Phase 1 builds the foundation for post-project analysis by:
1. Persisting currently ephemeral data (decisions, artifact metadata, project snapshots)
2. Creating a unified aggregator that indexes all data sources
3. Providing a clean query API for historical project data
4. **Zero duplication** - only persist what doesn't already exist

**Duration:** 3-5 days
**Dependencies:** None
**Deliverable:** Historical project data query API with comprehensive test coverage

## Problem Statement

### Current State

MARCUS already captures rich execution data:

**Persistent Sources:**
- `logs/conversations/{timestamp}.jsonl` - All worker↔PM interactions
  - **CRITICAL**: Task assignment conversations include full instructions given to agents
  - See `task.py:806-816` and `task.py:860-872` - Instructions logged in metadata
- `logs/agent_events/{timestamp}.jsonl` - Agent lifecycle events
- `data/marcus_state/projects.json` - Project registry
- `data/marcus_state/subtasks.json` - Task decomposition records
- Memory system backend - TaskOutcomes, AgentProfiles, TaskPatterns
- MLflow runs - If experiment tracking is enabled
- Kanban board state - Via provider APIs (Planka/GitHub/Linear)
- Project workspace - Artifact files (`docs/design/*.md`, etc.)

**Ephemeral Sources (LOST after session ends):**
- `state.context.decisions` - Dict of architectural decisions
- `state.task_artifacts` - Dict of artifact metadata (files exist, metadata doesn't)
- `state.project_state` - Final project metrics (velocity, completion %, risk level)

### Gap Analysis

| **Data Type** | **Currently Persisted?** | **Queryable After Session?** | **Action Needed** |
|--------------|-------------------------|------------------------------|-------------------|
| Conversation logs | ✅ File | ✅ Yes | Index only |
| Agent events | ✅ File | ✅ Yes | Index only |
| Task outcomes | ✅ Memory backend | ✅ Yes | Index only |
| Agent profiles | ✅ Memory backend | ✅ Yes | Index only |
| Decisions | ⚠️ Kanban comments only | ⚠️ Hard to query | **Persist registry** |
| Artifact metadata | ❌ Memory only | ❌ No | **Persist registry** |
| Project snapshots | ❌ Memory only | ❌ No | **Persist snapshots** |
| Task descriptions | ✅ Kanban | ✅ Yes | Index only |
| Dependencies | ✅ Kanban | ✅ Yes | Index only |

**Key Insight:** We're not missing much data - we just need to:
1. Persist the 3 ephemeral registries
2. Build an aggregator to unify existing sources
3. Create a query API

## Detailed Design

### 1. Persistent Storage Schema

#### 1.1 Decisions Registry

**File:** `data/project_history/{project_id}/decisions.json`

**Purpose:** Index all architectural decisions with full context (Kanban comments exist but aren't indexed)

**Schema:**
```json
{
  "project_id": "marcus_proj_123",
  "project_name": "Task Management API",
  "decisions": [
    {
      "decision_id": "dec_uuid_001",
      "task_id": "task_user-login_implement",
      "agent_id": "agent_worker_1",
      "timestamp": "2025-11-05T14:32:00Z",
      "what": "Use JWT tokens for authentication",
      "why": "Stateless auth reduces server memory, scales horizontally",
      "impact": "All API endpoints must validate JWT, user sessions stored client-side",
      "affected_tasks": ["task_api-auth_implement", "task_logout_implement"],
      "confidence": 0.85,
      "kanban_comment_url": "https://planka.example.com/cards/123#comment-456"
    }
  ],
  "metadata": {
    "last_updated": "2025-11-05T16:00:00Z",
    "total_decisions": 12
  }
}
```

**Rationale:**
- `decision_id` - Unique identifier for referencing
- `affected_tasks` - Pre-computed to avoid traversing dependency graph
- `kanban_comment_url` - Link to original source for verification
- `confidence` - How certain was the agent? (useful for risk analysis)

#### 1.2 Artifacts Registry

**File:** `data/project_history/{project_id}/artifacts.json`

**Purpose:** Index artifact metadata (files already exist in workspace)

**Schema:**
```json
{
  "project_id": "marcus_proj_123",
  "project_name": "Task Management API",
  "project_root": "/Users/username/projects/task-management-api",
  "artifacts": [
    {
      "artifact_id": "art_uuid_001",
      "task_id": "task_user-auth_design",
      "agent_id": "agent_designer_1",
      "timestamp": "2025-11-05T13:15:00Z",
      "filename": "user_authentication_design.md",
      "artifact_type": "design",
      "relative_path": "docs/design/user_authentication_design.md",
      "absolute_path": "/Users/username/projects/task-management-api/docs/design/user_authentication_design.md",
      "description": "Authentication flow design with JWT strategy",
      "file_size_bytes": 4096,
      "sha256_hash": "abc123...",
      "kanban_comment_url": "https://planka.example.com/cards/120#comment-450",
      "referenced_by_tasks": ["task_user-login_implement", "task_api-auth_implement"]
    }
  ],
  "metadata": {
    "last_updated": "2025-11-05T16:00:00Z",
    "total_artifacts": 28,
    "total_size_mb": 1.2
  }
}
```

**Rationale:**
- `sha256_hash` - Detect if file was modified post-project
- `referenced_by_tasks` - Pre-computed from context system
- Both relative and absolute paths for portability
- File size tracking for cleanup analysis

#### 1.3 Project Completion Snapshot

**File:** `data/project_history/{project_id}/snapshot.json`

**Purpose:** Capture final project state at completion

**Schema:**
```json
{
  "project_id": "marcus_proj_123",
  "project_name": "Task Management API",
  "snapshot_timestamp": "2025-11-05T18:00:00Z",
  "completion_status": "completed",  // or "abandoned", "stalled"

  "task_statistics": {
    "total_tasks": 24,
    "completed": 22,
    "in_progress": 0,
    "blocked": 2,
    "completion_rate": 0.917
  },

  "timing": {
    "project_started": "2025-11-01T09:00:00Z",
    "project_completed": "2025-11-05T18:00:00Z",
    "total_duration_hours": 105,
    "estimated_hours": 80,
    "actual_hours": 92,
    "estimation_accuracy": 0.870
  },

  "team": {
    "total_agents": 5,
    "agents": [
      {
        "agent_id": "agent_worker_1",
        "tasks_completed": 8,
        "tasks_blocked": 1,
        "success_rate": 0.889,
        "total_hours": 32
      }
    ]
  },

  "quality_metrics": {
    "team_velocity": 4.2,  // tasks per day
    "risk_level": "medium",
    "average_task_duration": 3.83,  // hours
    "blockage_rate": 0.083
  },

  "technology_stack": {
    "languages": ["Python", "TypeScript"],
    "frameworks": ["FastAPI", "React"],
    "tools": ["PostgreSQL", "Redis"]
  },

  "outcome": {
    "application_works": null,  // To be filled by user/tests
    "deployment_status": null,
    "user_satisfaction": null,
    "notes": ""
  }
}
```

**Rationale:**
- Comprehensive metrics for trend analysis
- `outcome` section for user feedback
- Technology stack for pattern analysis (e.g., "React projects have lower success rates")
- Both estimated and actual for accuracy tracking

### 2. Persistence Triggers

**When do we persist?**

#### 2.1 Incremental (Real-Time)

**Decisions:**
```python
# In src/marcus_mcp/tools/context.py:log_decision()
async def log_decision(...):
    # ... existing code ...

    # NEW: Persist decision immediately
    await state.project_history.append_decision(
        project_id=state.current_project_id,
        decision=logged_decision
    )
```

**Artifacts:**
```python
# In src/marcus_mcp/tools/attachment.py:log_artifact()
async def log_artifact(...):
    # ... existing code ...

    # NEW: Persist artifact metadata immediately
    await state.project_history.append_artifact(
        project_id=state.current_project_id,
        artifact=artifact_metadata
    )
```

**Rationale:** Incremental persistence prevents data loss if session crashes

#### 2.2 Batch (Project Completion)

**Snapshot:**
```python
# In src/marcus_mcp/tools/project.py or coordinator
async def finalize_project(project_id: str):
    """Called when all tasks completed or project abandoned."""

    # Capture final snapshot
    snapshot = await state.project_history.create_snapshot(
        project_id=project_id,
        project_state=state.project_state,
        agent_status=state.agent_status
    )

    # Trigger analysis (Phase 2)
    await trigger_post_project_analysis(project_id)
```

**Rationale:** Snapshot only meaningful at completion, so batch makes sense

### 3. Aggregator Architecture

#### 3.1 Data Sources

The aggregator unifies **existing** data sources + **new** persistent registries:

```python
class ProjectHistoryAggregator:
    """
    Unified aggregator for historical project data.

    Indexes and denormalizes data from:
    - Conversation logs (existing)
    - Agent events (existing)
    - Memory system (existing)
    - Kanban board (existing)
    - Decisions registry (NEW)
    - Artifacts registry (NEW)
    - Project snapshots (NEW)
    """

    def __init__(self, marcus_root: Path):
        self.marcus_root = marcus_root
        self.history_dir = marcus_root / "data" / "project_history"
        self.logs_dir = marcus_root / "logs"
        self.state_dir = marcus_root / "data" / "marcus_state"
```

#### 3.2 Core Aggregation Method

```python
async def aggregate_project(
    self,
    project_id: str,
    include_conversations: bool = True,
    include_kanban: bool = True
) -> ProjectHistory:
    """
    Aggregate all historical data for a project.

    Returns
    -------
    ProjectHistory
        Unified data structure with all project execution data
    """

    # Load new persistent registries
    decisions = await self._load_decisions(project_id)
    artifacts = await self._load_artifacts(project_id)
    snapshot = await self._load_snapshot(project_id)

    # Load existing data sources
    conversations = await self._load_conversations(project_id) if include_conversations else []
    events = await self._load_agent_events(project_id)
    outcomes = await self._load_task_outcomes(project_id)  # From Memory system

    # Optional: Load from Kanban (may be slow)
    kanban_tasks = await self._load_kanban_tasks(project_id) if include_kanban else []

    # Denormalize and cross-reference
    return ProjectHistory(
        project_id=project_id,
        snapshot=snapshot,
        tasks=self._build_task_histories(outcomes, kanban_tasks, decisions, artifacts),
        agents=self._build_agent_histories(events, outcomes),
        timeline=self._build_timeline(conversations, events, decisions, artifacts),
        decisions=decisions,
        artifacts=artifacts
    )
```

#### 3.3 Data Model

```python
@dataclass
class TaskHistory:
    """Complete history for a single task."""

    # Basic info (from Kanban/Memory)
    task_id: str
    name: str
    description: str
    status: str
    estimated_hours: float
    actual_hours: float

    # Execution (from agent events + conversations)
    assigned_to: str
    started_at: datetime
    completed_at: datetime
    outcome: TaskOutcome  # From Memory system

    # Instructions (CRITICAL - from conversation logs)
    instructions_received: str  # Full instructions from task assignment
    # Extracted from conversation_logger.log_worker_message() at task.py:806-816
    # Contains: base instructions + context + dependencies + predictions

    # Context (from context system)
    dependencies: list[str]
    context_received: dict[str, Any]  # What context was provided

    # Decisions (from decisions registry)
    decisions_made: list[Decision]
    decisions_consumed: list[Decision]  # From dependencies

    # Artifacts (from artifacts registry)
    artifacts_produced: list[Artifact]
    artifacts_consumed: list[Artifact]  # From dependencies

    # Communication (from conversation logs)
    conversations: list[Message]
    blockers_reported: list[Blocker]

    # Analysis (Phase 2 will populate)
    requirement_fidelity: Optional[float] = None
    instruction_quality: Optional[float] = None
    failure_causes: list[str] = field(default_factory=list)


@dataclass
class ProjectHistory:
    """Complete aggregated history for a project."""

    project_id: str
    snapshot: ProjectSnapshot
    tasks: list[TaskHistory]
    agents: list[AgentHistory]
    timeline: list[TimelineEvent]
    decisions: list[Decision]
    artifacts: list[Artifact]

    # Computed properties
    @property
    def task_by_id(self) -> dict[str, TaskHistory]:
        return {t.task_id: t for t in self.tasks}

    @property
    def decision_impact_graph(self) -> Dict[str, list[str]]:
        """Map decision_id -> affected_task_ids."""
        graph = {}
        for decision in self.decisions:
            graph[decision.decision_id] = decision.affected_tasks
        return graph
```

### 4. Query API

#### 4.1 High-Level Interface

```python
class ProjectHistoryQuery:
    """
    Query interface for historical project data.

    Examples:
        # Get full project history
        history = await query.get_project_history("marcus_proj_123")

        # Get task execution trace
        task = await query.get_task_history("marcus_proj_123", "task_login_implement")

        # Find decisions affecting a task
        decisions = await query.get_decisions_affecting_task("task_login_implement")

        # Get artifacts produced by task
        artifacts = await query.get_artifacts_for_task("task_user-auth_design")
    """

    def __init__(self, aggregator: ProjectHistoryAggregator):
        self.aggregator = aggregator

    async def get_project_history(
        self,
        project_id: str,
        include_conversations: bool = False  # Can be large
    ) -> ProjectHistory:
        """Get complete project history."""
        return await self.aggregator.aggregate_project(
            project_id,
            include_conversations=include_conversations
        )

    async def get_task_history(
        self,
        project_id: str,
        task_id: str
    ) -> TaskHistory:
        """Get complete history for a single task."""
        project = await self.get_project_history(project_id)
        return project.task_by_id[task_id]

    async def get_decisions_affecting_task(
        self,
        project_id: str,
        task_id: str
    ) -> list[Decision]:
        """Get all decisions that affected this task."""
        project = await self.get_project_history(project_id)

        # Direct decisions on this task
        direct = [d for d in project.decisions if d.task_id == task_id]

        # Decisions from dependencies
        task = project.task_by_id[task_id]
        dependency_decisions = []
        for dep_id in task.dependencies:
            dep_decisions = [d for d in project.decisions if d.task_id == dep_id]
            dependency_decisions.extend(dep_decisions)

        return direct + dependency_decisions

    async def trace_decision_impact(
        self,
        project_id: str,
        decision_id: str
    ) -> Dict[str, Any]:
        """
        Trace the full impact of a decision.

        Returns tasks affected, their outcomes, and downstream cascade.
        """
        project = await self.get_project_history(project_id)
        decision = next(d for d in project.decisions if d.decision_id == decision_id)

        affected_tasks = [project.task_by_id[tid] for tid in decision.affected_tasks]

        return {
            "decision": decision,
            "directly_affected": affected_tasks,
            "cascade_depth": self._calculate_cascade_depth(project, decision),
            "success_rate": sum(1 for t in affected_tasks if t.outcome.success) / len(affected_tasks),
            "blockers_caused": [t.blockers_reported for t in affected_tasks]
        }
```

#### 4.2 Search & Filter

```python
class ProjectSearch:
    """Advanced search and filtering."""

    async def find_projects(
        self,
        status: Optional[str] = None,  # "completed", "abandoned", "stalled"
        date_range: Optional[tuple[datetime, datetime]] = None,
        technology: Optional[str] = None,  # e.g., "FastAPI", "React"
        min_completion_rate: Optional[float] = None
    ) -> list[ProjectSnapshot]:
        """Search projects by criteria."""
        pass

    async def find_failed_tasks(
        self,
        project_id: str,
        task_type: Optional[str] = None  # "design", "implement", "test"
    ) -> list[TaskHistory]:
        """Find all failed tasks in a project."""
        pass

    async def find_blocking_decisions(
        self,
        project_id: str
    ) -> list[Decision]:
        """Find decisions that led to blockers in downstream tasks."""
        pass
```

### 5. Implementation Sequence

#### Step 1: Create Storage Schema (Day 1)

1. **Define data structures** - Pydantic models for decisions, artifacts, snapshots
2. **Create file I/O** - JSON serialization with atomic writes
3. **Write unit tests** - Test serialization, deserialization, schema validation

**Files to create:**
- `src/core/project_history.py` - Data models and persistence
- `tests/unit/core/test_project_history.py` - Unit tests

#### Step 2: Add Persistence Hooks (Day 1-2)

1. **Modify `log_decision()`** - Add `await state.project_history.append_decision()`
2. **Modify `log_artifact()`** - Add `await state.project_history.append_artifact()`
3. **Add `finalize_project()`** - Create snapshot on completion
4. **Write integration tests** - Verify persistence happens correctly

**Files to modify:**
- `src/marcus_mcp/tools/context.py`
- `src/marcus_mcp/tools/attachment.py`
- Add new: `src/marcus_mcp/tools/project_lifecycle.py`

**Tests:**
- `tests/integration/mcp/test_decision_persistence.py`
- `tests/integration/mcp/test_artifact_persistence.py`

#### Step 3: Build Aggregator (Day 2-3)

1. **Create `ProjectHistoryAggregator`** - Load and denormalize data sources
2. **Implement `aggregate_project()`** - Main aggregation method
3. **Add caching** - Cache aggregated data (60s TTL like Cato)
4. **Write tests** - Test with mock data and real project files

**Files to create:**
- `src/analysis/aggregator.py` - Aggregator implementation
- `tests/unit/analysis/test_aggregator.py` - Unit tests
- `tests/integration/analysis/test_aggregator_e2e.py` - End-to-end tests

#### Step 4: Build Query API (Day 3-4)

1. **Create `ProjectHistoryQuery`** - High-level query interface
2. **Implement core methods** - `get_project_history()`, `get_task_history()`, etc.
3. **Add search/filter** - `ProjectSearch` class
4. **Write tests** - Test all query methods

**Files to create:**
- `src/analysis/query.py` - Query API
- `tests/unit/analysis/test_query.py` - Unit tests

#### Step 5: Integration & Documentation (Day 4-5)

1. **Add MCP tool** - `get_project_history` tool for agents/users
2. **Write documentation** - Usage guide, examples, API reference
3. **Run integration tests** - End-to-end test with real project
4. **Update CLAUDE.md** - Document new tools and patterns

**Files to create/modify:**
- `src/marcus_mcp/tools/history.py` - MCP tool for querying history
- `docs/analysis/PROJECT_HISTORY.md` - User guide
- `docs/api/PROJECT_HISTORY_API.md` - API reference

### 6. Testing Strategy

#### 6.1 Unit Tests

**Coverage targets:** 80%+

**Test categories:**
```python
# Test data models
def test_decision_serialization()
def test_artifact_registry_schema()
def test_snapshot_validation()

# Test persistence
def test_append_decision()
def test_append_artifact()
def test_create_snapshot()
def test_atomic_writes()
def test_concurrent_writes()

# Test aggregation
def test_aggregate_decisions()
def test_aggregate_artifacts()
def test_cross_reference_tasks()
def test_build_timeline()

# Test queries
def test_get_task_history()
def test_trace_decision_impact()
def test_find_failed_tasks()
```

#### 6.2 Integration Tests

```python
# End-to-end persistence
async def test_decision_persists_on_log():
    """Verify decision logged via MCP tool persists to file."""

async def test_artifact_persists_on_log():
    """Verify artifact logged via MCP tool persists to file."""

async def test_snapshot_created_on_completion():
    """Verify snapshot created when project completes."""

# End-to-end aggregation
async def test_aggregate_real_project():
    """Load real project data and aggregate."""

# End-to-end querying
async def test_query_historical_project():
    """Query a completed project and verify data."""
```

#### 6.3 Performance Tests

```python
async def test_aggregation_performance():
    """Aggregation should complete in < 500ms for typical project."""

async def test_large_project_aggregation():
    """Test with project having 100+ tasks."""

async def test_concurrent_queries():
    """Multiple concurrent queries shouldn't degrade performance."""
```

### 7. File Structure

```
marcus/
├── src/
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── aggregator.py          # ProjectHistoryAggregator
│   │   ├── query.py                # ProjectHistoryQuery, ProjectSearch
│   │   └── models.py               # TaskHistory, ProjectHistory, etc.
│   ├── core/
│   │   └── project_history.py      # Persistence layer
│   └── marcus_mcp/
│       └── tools/
│           ├── context.py          # Modified: add persistence
│           ├── attachment.py       # Modified: add persistence
│           ├── project_lifecycle.py # New: project finalization
│           └── history.py          # New: MCP query tool
├── data/
│   └── project_history/
│       └── {project_id}/
│           ├── decisions.json
│           ├── artifacts.json
│           └── snapshot.json
├── tests/
│   ├── unit/
│   │   ├── analysis/
│   │   │   ├── test_aggregator.py
│   │   │   ├── test_query.py
│   │   │   └── test_models.py
│   │   └── core/
│   │       └── test_project_history.py
│   └── integration/
│       ├── analysis/
│       │   └── test_aggregator_e2e.py
│       └── mcp/
│           ├── test_decision_persistence.py
│           └── test_artifact_persistence.py
└── docs/
    ├── analysis/
    │   └── PROJECT_HISTORY.md
    └── api/
        └── PROJECT_HISTORY_API.md
```

### 8. Risk Mitigation

| **Risk** | **Mitigation** |
|----------|---------------|
| File corruption | Atomic writes, validation on load, backups |
| Concurrent writes | File locking, append-only pattern for incremental data |
| Large file sizes | Pagination for queries, compression for old projects |
| Schema changes | Versioning in JSON (`"schema_version": "1.0"`), migration scripts |
| Performance degradation | Caching, indexing, lazy loading of conversations |
| Data loss | Incremental persistence, redundant storage (Kanban comments) |

### 9. Success Criteria

Phase 1 is complete when:

✅ Decisions persisted incrementally to `decisions.json` on `log_decision()`
✅ Artifact metadata persisted incrementally to `artifacts.json` on `log_artifact()`
✅ Project snapshots created on project completion
✅ Aggregator can load and denormalize all data sources
✅ Query API provides access to historical project data
✅ 80%+ test coverage for all new code
✅ Mypy strict mode compliance
✅ Documentation complete (user guide + API reference)
✅ Integration test with real project passes

### 10. Future Enhancements (Out of Scope for Phase 1)

- **Database backend** - Replace file-based storage with SQLite/PostgreSQL for complex queries
- **Compression** - Compress old project histories to save space
- **Incremental aggregation** - Update aggregated cache on each new event
- **Real-time streaming** - WebSocket API for live project monitoring
- **Multi-project analysis** - Cross-project pattern detection
- **Data retention policies** - Auto-cleanup of old projects

These will be considered in Phase 2 or Phase 3 as needed.

## Next Steps

After Phase 1 completion:
1. **Review deliverables** - Ensure all success criteria met
2. **User acceptance testing** - Query real project data, verify accuracy
3. **Proceed to Phase 2** - Build LLM analysis engine on top of this foundation
