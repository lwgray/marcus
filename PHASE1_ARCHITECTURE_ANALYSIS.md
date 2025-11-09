# Phase 1 Post-Project Analysis Implementation - Comprehensive Report

**Document Date:** 2025-11-08
**Marcus Version:** Current develop branch
**Total Phase 1 LOC:** ~2,795 lines across 4 core files

---

## Executive Summary

Phase 1 implements a complete post-project analysis system consisting of:
- **Data Persistence Layer** (SQLite + file-based): Stores decisions, artifacts, and project snapshots
- **Data Aggregation Layer**: Unifies data from conversations, events, memory, and Kanban
- **Query API Layer**: Provides filtering, searching, and analysis capabilities
- **MCP Integration**: Exposes queries to agents via unified MCP tool

The system is designed as a **source-of-truth approach** where:
- Conversation logs are the authoritative source for project-task mapping
- SQLite provides scalable storage with pagination support
- Files are used for archival and export purposes
- Caching (60s TTL) optimizes repeated queries

---

## 1. FILE STRUCTURE & ORGANIZATION

### Core Phase 1 Files

```
/Users/lwgray/dev/marcus/src/
├── core/
│   ├── project_history.py          (853 lines) - Data models & persistence
│   └── persistence.py              - SQLite backend (271-399 lines)
├── analysis/
│   ├── aggregator.py               (847 lines) - Data unification
│   └── query_api.py                (597 lines) - Query interface
└── marcus_mcp/tools/
    └── history.py                  (498 lines) - MCP tool exposure
```

### File Responsibilities

| File | Lines | Primary Responsibility |
|------|-------|------------------------|
| `project_history.py` | 853 | Data models (Decision, ArtifactMetadata, ProjectSnapshot) + SQLite persistence |
| `aggregator.py` | 847 | Unifies multi-source data into unified ProjectHistory |
| `query_api.py` | 597 | High-level query interface for common analysis needs |
| `history.py` (MCP) | 498 | MCP tool wrapper exposing queries to agents |
| `persistence.py` | ~150 | SQLite backend implementation (FilePersistence also available) |

### Test Files Organization

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_project_history.py        - Dataclass serialization tests
│   │   └── test_project_history_sqlite.py - SQLite persistence tests
│   └── analysis/
│       └── test_query_api.py              - Query API filtering tests
└── integration/
    └── (test artifacts integration with workspace)
```

---

## 2. DATA LAYER ANALYSIS

### 2.1 Data Models (project_history.py, lines 22-352)

#### Decision Model
**Location:** `src/core/project_history.py` lines 22-105

```python
@dataclass
class Decision:
    decision_id: str           # Unique ID with timestamp
    task_id: str              # Task where decided
    agent_id: str             # Agent making decision
    timestamp: datetime        # When decided (UTC, timezone-aware)
    what: str                 # The choice made
    why: str                  # Rationale
    impact: str               # Expected downstream impact
    affected_tasks: list[str] # Task IDs that will be affected
    confidence: float         # 0.0-1.0 confidence level
    kanban_comment_url: Optional[str]  # Cross-link to Kanban
    project_id: Optional[str] # For validation/debugging (NOT for filtering)
```

**Key Features:**
- Full round-trip JSON serialization via `to_dict()` / `from_dict()`
- Timezone-aware datetime handling (lines 87-90: handles naive timestamps)
- Supports optional Kanban cross-linking
- Project ID is stored but never used for filtering (design decision)

#### ArtifactMetadata Model
**Location:** `src/core/project_history.py` lines 107-207

```python
@dataclass
class ArtifactMetadata:
    artifact_id: str           # Unique ID
    task_id: str              # Task producing artifact
    agent_id: str             # Agent who created it
    timestamp: datetime        # Creation time
    filename: str             # Artifact filename
    artifact_type: str        # Type: design, specification, api, etc.
    relative_path: str        # Path relative to project root
    absolute_path: str        # Full absolute path
    description: str          # What it contains
    file_size_bytes: int      # File size (0 by default)
    sha256_hash: Optional[str] # For integrity checking
    kanban_comment_url: Optional[str]  # Kanban cross-link
    referenced_by_tasks: list[str]     # Tasks consuming this artifact
    project_id: Optional[str] # For validation/debugging (NOT for filtering)
```

**Key Features:**
- Actual artifact files persist in project workspace
- Metadata only stored in persistence layer
- Supports integrity checking via SHA256 hash
- Tracks artifact consumers for dependency analysis

#### ProjectSnapshot Model
**Location:** `src/core/project_history.py` lines 210-351

**Components:**
- Task Statistics: Total, completed, in_progress, blocked, completion_rate
- Timing: Started, completed, duration, estimation accuracy
- Team: Total agents, per-agent summary
- Quality Metrics: Velocity, risk level, blockage rate, avg task duration
- Technology Stack: Languages, frameworks, tools
- Outcome: Application status, deployment, user satisfaction

### 2.2 SQLite Persistence Implementation

#### Schema
**Location:** `src/core/persistence.py` lines 280-300

```sql
CREATE TABLE IF NOT EXISTS persistence (
    collection TEXT NOT NULL,
    key TEXT NOT NULL,
    data TEXT NOT NULL,
    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (collection, key)
)

CREATE INDEX IF NOT EXISTS idx_stored_at
ON persistence(stored_at)
```

#### Collections Used
- `"decisions"` - Stores Decision objects keyed by decision_id
- `"artifacts"` - Stores ArtifactMetadata keyed by artifact_id
- `"snapshots"` - Stores ProjectSnapshot objects

#### Backend Initialization
**Location:** `src/core/project_history.py` lines 366-391

```python
class ProjectHistoryPersistence:
    def __init__(self, marcus_root: Optional[Path] = None):
        # Auto-detect Marcus root if not provided
        self.db_path = marcus_root / "data" / "marcus.db"
        self._backend = SQLitePersistence(db_path=self.db_path)
```

- Uses **connection pooling** (single reusable backend instance)
- Database located at: `data/marcus.db`
- Automatically creates parent directories

### 2.3 Pagination Implementation

#### Decision Loading
**Location:** `src/core/project_history.py` lines 542-625

```python
async def load_decisions(
    self,
    project_id: str,
    limit: int = 10000,      # Default 10000, max enforced
    offset: int = 0
) -> list[Decision]:
    # 1. Get task IDs from conversations (authoritative source)
    project_task_ids = await self._get_task_ids_from_conversations(project_id)

    # 2. Create filter function for task_id membership
    def task_filter(item: dict[str, Any]) -> bool:
        return item.get("task_id") in project_task_ids

    # 3. Query with filter and pagination
    query_limit = min(limit, 10000)  # Cap at 10000
    all_decisions = await backend.query(
        "decisions",
        filter_func=task_filter,
        limit=query_limit + offset  # Fetch enough for offset
    )

    # 4. Apply offset and limit to results
    paginated_decisions = all_decisions[offset : offset + limit]
```

**Key Design:**
- Conversation logs are authoritative source for project-task mapping
- Project ID field in Decision is never used for filtering (design decision)
- Query limit capped at 10,000 to prevent memory exhaustion
- Offset applied post-query for safety (could be optimized with SQL offset)

#### Artifact Loading
**Location:** `src/core/project_history.py` lines 627-710

Same pagination pattern as decisions.

### 2.4 Conversation Log Access

#### Task ID Extraction
**Location:** `src/core/project_history.py` lines 755-807

```python
async def _get_task_ids_from_conversations(self, project_id: str) -> set[str]:
    conversations_dir = self.marcus_root / "logs" / "conversations"
    task_ids: set[str] = set()

    for log_file in conversations_dir.glob("conversations_*.jsonl"):
        with open(log_file, "r") as f:
            for line in f:
                entry = json.loads(line)
                metadata = entry.get("metadata", {})
                if metadata.get("project_id") == project_id:
                    if "task_id" in metadata:
                        task_ids.add(str(metadata["task_id"]))

    return task_ids
```

**File Location:** `logs/conversations/conversations_*.jsonl`
**Format:** JSONL (one JSON object per line)
**Key Fields:**
- `metadata.project_id` - Project identifier
- `metadata.task_id` - Task identifier
- `conversation_type` - "pm_to_worker" or "worker_to_pm"
- `worker_id` - Agent identifier
- `message` - Conversation content
- `timestamp` - ISO format datetime

---

## 3. AGGREGATION LAYER ANALYSIS

### 3.1 ProjectHistoryAggregator

**Location:** `src/analysis/aggregator.py` lines 218-382

#### Responsibilities
1. Load data from multiple sources
2. Filter by project context
3. Build unified history objects
4. Cache results (60s TTL)

#### Data Sources Unified

| Source | Type | Location | Key Data |
|--------|------|----------|----------|
| Conversation Logs | JSONL | `logs/conversations/` | Messages, task instructions, metadata |
| Agent Events | JSON | `data/marcus_state/` | Task assignments, completions |
| Memory System | JSON | `data/marcus_state/` | TaskOutcomes, AgentProfiles |
| Project History | SQLite | `data/marcus.db` | Decisions, Artifacts, Snapshots |
| Kanban Board | API | Optional | Task status, comments (optional) |

#### Initialization

```python
class ProjectHistoryAggregator:
    def __init__(self, marcus_root: Optional[Path] = None):
        self.marcus_root = marcus_root or Path(__file__).parent.parent.parent
        self.history_persistence = ProjectHistoryPersistence(marcus_root)
        self.logs_dir = marcus_root / "logs"
        self.state_dir = marcus_root / "data" / "marcus_state"

        # Simple in-memory cache (60s TTL)
        self._cache: dict[str, tuple[ProjectHistory, datetime]] = {}
        self._cache_ttl = 60  # seconds
```

#### Core Aggregation Method
**Location:** `src/analysis/aggregator.py` lines 262-382

```python
async def aggregate_project(
    self,
    project_id: str,
    include_conversations: bool = True,
    include_kanban: bool = False,
    decision_limit: int = 10000,
    decision_offset: int = 0,
    artifact_limit: int = 10000,
    artifact_offset: int = 0,
) -> ProjectHistory:
    # 1. Check 60s cache
    # 2. Load decisions (SQLite, paginated)
    # 3. Load artifacts (SQLite, paginated)
    # 4. Load snapshot (file)
    # 5. Load conversations (JSONL, optional)
    # 6. Load events, outcomes, profiles (JSON)

    # 7. Extract task IDs from conversations
    # 8. Filter outcomes & events to project tasks
    # 9. Extract agent IDs from conversations
    # 10. Filter profiles to project agents

    # 11. Build unified structures:
    tasks = self._build_task_histories(...)
    agents = self._build_agent_histories(...)
    timeline = self._build_timeline(...)

    # 12. Cache result and return
```

#### TaskHistory Unification
**Location:** `src/analysis/aggregator.py` lines 54-131 (definition), aggregator methods (construction)

```python
@dataclass
class TaskHistory:
    task_id: str
    name: str
    description: str
    status: str

    # Timing
    estimated_hours: float
    actual_hours: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Assignment
    assigned_to: Optional[str] = None

    # CRITICAL: Instructions from conversations
    instructions_received: Optional[str] = None

    # Context
    dependencies: list[str] = field(default_factory=list)
    context_received: dict[str, Any] = field(default_factory=dict)

    # Decisions & Artifacts
    decisions_made: list[Decision] = field(default_factory=list)
    decisions_consumed: list[Decision] = field(default_factory=list)
    artifacts_produced: list[ArtifactMetadata] = field(default_factory=list)
    artifacts_consumed: list[ArtifactMetadata] = field(default_factory=list)

    # Communication
    conversations: list[Message] = field(default_factory=list)
    blockers_reported: list[dict[str, Any]] = field(default_factory=list)

    # Outcome (from Memory system)
    outcome: Optional[TaskOutcome] = None

    # Phase 2 Fields (populated in Phase 2)
    requirement_fidelity: Optional[float] = None
    instruction_quality: Optional[float] = None
    failure_causes: list[str] = field(default_factory=list)
```

#### ProjectHistory Container
**Location:** `src/analysis/aggregator.py` lines 176-215

```python
@dataclass
class ProjectHistory:
    project_id: str
    snapshot: Optional[ProjectSnapshot]
    tasks: list[TaskHistory]
    agents: list[AgentHistory]
    timeline: list[TimelineEvent]
    decisions: list[Decision]
    artifacts: list[ArtifactMetadata]

    @property
    def task_by_id(self) -> dict[str, TaskHistory]:
        """Map task_id to TaskHistory for quick lookup"""

    @property
    def decision_impact_graph(self) -> dict[str, list[str]]:
        """Map decision_id -> affected_task_ids"""
```

---

## 4. QUERY API LAYER ANALYSIS

### 4.1 ProjectHistoryQuery Interface

**Location:** `src/analysis/query_api.py` lines 26-598

Provides high-level query methods organized by entity type:

#### Task Queries
- `find_tasks_by_status(project_id, status)` - Line 94
- `find_tasks_by_agent(project_id, agent_id)` - Line 115
- `find_tasks_in_timerange(project_id, start_time, end_time)` - Line 136
- `find_blocked_tasks(project_id)` - Line 174
- `get_task_dependency_chain(project_id, task_id)` - Line 191

#### Decision Queries
- `find_decisions_by_task(project_id, task_id)` - Line 239
- `find_decisions_by_agent(project_id, agent_id)` - Line 260
- `find_decisions_affecting_task(project_id, task_id)` - Line 281

#### Artifact Queries
- `find_artifacts_by_task(project_id, task_id)` - Line 304
- `find_artifacts_by_type(project_id, artifact_type)` - Line 325
- `find_artifacts_by_agent(project_id, agent_id)` - Line 346

#### Agent Queries
- `get_agent_history(project_id, agent_id)` - Line 369
- `get_agent_performance_metrics(project_id, agent_id)` - Line 393

#### Timeline Queries
- `search_timeline(project_id, event_type, agent_id, task_id, start_time, end_time)` - Line 443

#### Conversation Queries
- `search_conversations(project_id, keyword, agent_id, task_id)` - Line 496

#### Analysis Helpers
- `get_project_summary(project_id)` - Line 548

### 4.2 Example Usage Pattern

**Location:** `examples/query_project_history_example.py`

```python
aggregator = ProjectHistoryAggregator()
query = ProjectHistoryQuery(aggregator)

# Get summary
summary = await query.get_project_summary(project_id)

# Find completed tasks
completed = await query.find_tasks_by_status(project_id, "completed")

# Analyze agent performance
metrics = await query.get_agent_performance_metrics(project_id, agent_id)

# Search conversations
api_messages = await query.search_conversations(project_id, keyword="API")

# Task dependency analysis
deps = await query.get_task_dependency_chain(project_id, task_id)
```

---

## 5. MCP INTEGRATION

### 5.1 MCP Tool: query_project_history

**Location:** `src/marcus_mcp/tools/history.py` lines 23-280+

#### Unified Query Tool

Exposes all query types via single MCP tool with routing:

```python
async def query_project_history(
    project_id: str,
    query_type: str,  # summary, tasks, blocked_tasks, task_dependencies,
                      # decisions, artifacts, agent_history, agent_metrics,
                      # timeline, conversations
    state: Any,
    **filters: Any
) -> dict[str, Any]:
```

#### Query Type Routing
- `"summary"` - Project summary statistics (line 105)
- `"tasks"` - Tasks with filters: status, agent_id, start_time, end_time (line 109)
- `"blocked_tasks"` - All tasks with blockers (line 157)
- `"task_dependencies"` - Dependency chain for a task (line 165)
- `"decisions"` - Decisions with filters: task_id, agent_id, affecting_task_id (line 180)
- `"artifacts"` - Artifacts with filters: task_id, artifact_type, agent_id (line 213)
- `"agent_history"` - Complete agent history (line 242)
- `"agent_metrics"` - Performance metrics for agent (line 247)
- `"timeline"` - Timeline events with filters (line 256)
- `"conversations"` - Message search with filters (line 268)

#### Pagination Support
- Parameter: `limit` (default: 10000, max: 10000)
- Parameter: `offset` (default: 0)
- Validation: Lines 82-99

#### Response Format
```python
{
    "success": bool,
    "data": [...],          # Query results
    "count": int,          # Number returned
    "error": str           # If success=False
}
```

---

## 6. EXISTING INFRASTRUCTURE

### 6.1 Memory System Integration

**Location:** `src/core/memory.py`

#### TaskOutcome Model
```python
@dataclass
class TaskOutcome:
    task_id: str
    agent_id: str
    task_name: str
    estimated_hours: float
    actual_hours: float
    success: bool
    blockers: List[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    @property
    def estimation_accuracy(self) -> float:
        """Min(est, actual) / Max(est, actual)"""
```

**How It Connects:**
- Aggregator loads outcomes from `data/marcus_state/task_outcomes.json`
- TaskHistory includes outcome reference (line 96 of aggregator.py)
- Used for agent performance metrics (query_api.py line 428)

#### AgentProfile Model
```python
@dataclass
class AgentProfile:
    agent_id: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    blocked_tasks: int
    skill_success_rates: Dict[str, float]
    average_estimation_accuracy: float
    common_blockers: Dict[str, int]

    @property
    def success_rate(self) -> float
    @property
    def blockage_rate(self) -> float
```

**How It Connects:**
- Aggregator loads profiles from `data/marcus_state/`
- AgentHistory includes profile reference (aggregator.py line 144)
- Used for agent analysis

### 6.2 Context System Integration

**Location:** `src/core/context.py`

#### Decision Logging
```python
async def log_decision(
    self,
    agent_id: str,
    task_id: str,
    what: str,
    why: str,
    impact: str
) -> Decision:
    # Creates Decision object
    # Persists to backend if available
    # Publishes DECISION_LOGGED event
```

**Integration Points:**
- Line 237-291 in context.py
- Stores Decision to persistence backend (line 278)
- Emits EventTypes.DECISION_LOGGED event (line 287-288)

### 6.3 Artifact System Integration

**Location:** Not directly in context.py; exposed via MCP tools

**How artifacts are logged:**
- via `mcp__marcus__log_artifact` MCP tool
- Stores metadata in project_history.ArtifactMetadata
- Actual files persist in project workspace

### 6.4 Event System

**Location:** `src/core/events.py`

Events published by Phase 1:
- `EventTypes.DECISION_LOGGED` - When decision is logged
- `EventTypes.IMPLEMENTATION_FOUND` - When implementation context added

---

## 7. TESTING PATTERNS

### 7.1 Unit Tests for Data Models

**Location:** `tests/unit/core/test_project_history.py` (lines 1-200+)

```python
class TestDecision:
    def test_decision_to_dict_serializes_correctly(self)
    def test_decision_from_dict_deserializes_correctly(self)
    def test_decision_roundtrip_preserves_data(self)
    def test_decision_with_minimal_fields(self)

class TestArtifactMetadata:
    def test_artifact_to_dict_serializes_correctly(self)
    # ... similar roundtrip tests
```

**Markers Used:**
- No special markers for simple unit tests
- Test location: `tests/unit/core/`

### 7.2 SQLite Persistence Tests

**Location:** `tests/unit/core/test_project_history_sqlite.py`

```python
@pytest.mark.asyncio
async def test_load_decisions_from_sqlite(self):
    # Setup: Create sample decisions in SQLite
    # Setup: Create conversation logs with project_id
    # Act: Load decisions with pagination
    # Assert: Verify count, content, timezone-aware timestamps

@pytest.mark.asyncio
async def test_load_decisions_timezone_aware(self):
    # Verify timezone handling for loaded decisions
```

**Fixtures:**
- `temp_db: Path` - Temporary SQLite database
- `persistence: ProjectHistoryPersistence` - Mock Marcus root structure
- `sample_decisions` - Pre-populated decisions in SQLite

### 7.3 Query API Tests

**Location:** `tests/unit/analysis/test_query_api.py`

```python
@pytest.fixture
def mock_aggregator():
    aggregator = Mock(spec=ProjectHistoryAggregator)
    aggregator.aggregate_project = AsyncMock()

@pytest.fixture
def sample_project_history():
    # Create complete ProjectHistory with decisions, artifacts, tasks, agents
```

**Test Categories:**
- Task filtering tests
- Decision impact analysis
- Artifact discovery
- Agent performance metrics
- Timeline search
- Conversation search

---

## 8. CODE QUALITY STANDARDS

### 8.1 Type Hints

**Consistent Usage:**
- All function parameters have type hints
- All return types specified
- Use modern syntax: `list[str]`, `dict[str, Any]`, `Optional[T]`
- Example (project_history.py line 542):
  ```python
  async def load_decisions(
      self,
      project_id: str,
      limit: int = 10000,
      offset: int = 0
  ) -> list[Decision]:
  ```

### 8.2 Documentation

**Numpy-style Docstrings:**
- Class docstrings explain purpose and design decisions
- Method docstrings include Parameters and Returns sections
- Notable example (project_history.py lines 542-570):
  ```python
  async def load_decisions(
      self, project_id: str, limit: int = 10000, offset: int = 0
  ) -> list[Decision]:
      """
      Load decisions for a project from SQLite with pagination.

      Filters decisions by task_id, using conversation logs to identify
      project-specific tasks.

      Design Decision: Conversation logs are the authoritative source...

      Parameters
      ----------
      project_id : str
          Project identifier
      limit : int, optional
          Maximum number of decisions (default: 10000)
      offset : int, optional
          Number of decisions to skip (default: 0)

      Returns
      -------
      list[Decision]
          List of decisions (empty if none exist)
      """
  ```

### 8.3 Error Handling

**Marcus Error Framework Usage:**
- `DatabaseError` for database operations (project_history.py line 623)
- `error_context` for rich error context (line 573)
- Pattern:
  ```python
  from src.core.error_framework import DatabaseError, error_context

  with error_context("load_decisions", custom_context={"project_id": project_id}):
      try:
          # operation
      except Exception as e:
          raise DatabaseError(operation="load_decisions", table="decisions") from e
  ```

### 8.4 Code Style

**Compliance:**
- PEP 8 adherence
- Max line length: 88 characters (project uses black formatter)
- Imports organized (standard library, third-party, local)
- Use of dataclasses for data models

---

## 9. KEY DESIGN DECISIONS

### 9.1 Conversation-Based Task Mapping (Critical Design)

**Decision:** Use conversation logs as authoritative source for project-task mapping

**Location:** `project_history.py` lines 547-555 (documented in docstring)

**Rationale:**
- Conversation metadata has explicit project_id-task_id coupling
- Avoids data inconsistencies if Decision.project_id conflicts with actual assignment
- Single source of truth for determining which tasks belong to which project

**Implementation:**
1. Extract task IDs from `logs/conversations/conversations_*.jsonl`
2. Filter by project_id in metadata
3. Use task_id set for filtering decisions and artifacts
4. Decision.project_id field only used for validation/debugging

### 9.2 Pagination Strategy

**Design:** Client-side filtering with server-side limit

**Tradeoff Accepted:**
- Query fetches (offset + limit) records from SQLite
- Applies filter function in Python
- Slices result in Python
- Not SQL-based offset (could be optimized in Phase 2)

**Rationale:**
- Simple, safe implementation avoiding complex SQL generation
- Prevents memory exhaustion with 10,000 record cap
- Can be optimized with SQL offset in future phases

### 9.3 Caching Strategy

**Design:** Simple in-memory cache with 60s TTL per project

**Location:** `aggregator.py` lines 259-304

```python
self._cache: dict[str, tuple[ProjectHistory, datetime]] = {}
self._cache_ttl = 60  # seconds
```

**Rationale:**
- Mirrors Cato system caching pattern
- Reduces repeated file I/O and Kanban API calls
- Ensures freshness within 1 minute
- Simple cache invalidation (TTL expiration)

### 9.4 JSON Storage + SQLite Hybrid

**Design:** SQLite for decisions/artifacts (scalable), files for snapshots (archival)

**Location:** `project_history.py` lines 354-391

**Rationale:**
- SQLite enables pagination and filtering at database level (future optimization)
- Files provide easy human inspection and export
- Decisions/artifacts are the highest volume data
- Snapshots are one-per-project, file storage is appropriate

---

## 10. INTEGRATION POINTS

### 10.1 Data Flow: How Information Enters the System

```
Agent Task Execution
    ↓
Conversation Logger → logs/conversations/conversations_*.jsonl
                    (metadata: project_id, task_id, agent_id, timestamp)
                    ↓
                    aggregator._load_conversations()

Context System (log_decision) → SQLite via ProjectHistoryPersistence
                              ↓
                              SQLite (decisions collection)
                              ↓
                              aggregator.aggregate_project()

Memory System → data/marcus_state/task_outcomes.json
             ↓
             aggregator._load_task_outcomes()
             ↓
             TaskHistory.outcome field

Artifact System → Project workspace files
              ↓
              Metadata logged via mcp__marcus__log_artifact
              ↓
              SQLite (artifacts collection)
              ↓
              aggregator.aggregate_project()
```

### 10.2 Data Flow: How Information is Queried

```
Agent requests via MCP
    ↓
query_project_history (MCP tool)
    ↓
ProjectHistoryQuery API
    ↓
ProjectHistoryAggregator.aggregate_project()
    ├─ Loads decisions (SQLite, paginated)
    ├─ Loads artifacts (SQLite, paginated)
    ├─ Loads snapshot (file)
    ├─ Loads conversations (JSONL)
    ├─ Extracts task IDs from conversations
    └─ Builds unified ProjectHistory
        ↓
        Returns filtered/summarized data
        ↓
        MCP response sent to agent
```

### 10.3 Event Integration

**Events Published:**
- `DECISION_LOGGED` - By Context.log_decision()
- `IMPLEMENTATION_FOUND` - By Context.add_implementation()

**Listeners:** Optional; aggregator does not depend on events

---

## 11. GAPS & ISSUES FOR PHASE 2

### 11.1 Architecture-Level Gaps

| Gap | Impact | Phase 2 Solution |
|-----|--------|------------------|
| No decision-artifact tracing | Can't link decisions to outputs | Add decision_id to artifacts; build impact graph |
| No requirement vs instruction comparison | Can't measure fidelity | Phase 2 AI analysis: compare specs → instructions |
| No root cause analysis | Can't learn from failures | Phase 2 AI analysis: blockers → failure causes |
| No instruction quality scoring | Can't improve prompts | Phase 2 AI analysis: assess instruction clarity |
| No multi-project comparative analysis | Can't identify meta-patterns | Phase 2: cross-project query aggregation |

### 11.2 Data Quality Issues

- **Conversation logs:** Might have incomplete/missing metadata
- **Memory outcomes:** Might not be recorded for all tasks
- **Artifact metadata:** Depends on agents calling log_artifact
- **Decision metadata:** affected_tasks field is optional, might be sparse

### 11.3 Performance Considerations

- **Query time:** Loads all project conversations for task ID extraction (slow for large projects)
- **Memory usage:** Loads entire ProjectHistory into memory (can be large)
- **Cache strategy:** Simple TTL, no invalidation on updates

### 11.4 Testing Gaps

- ⚠️ No integration tests for full data flow (conversations → aggregator → query)
- ⚠️ No tests for actual Kanban integration
- ⚠️ No performance tests for large projects (1000+ tasks)
- ⚠️ No tests for concurrent aggregation requests
- ⚠️ No tests for malformed conversation log entries

---

## 12. REUSABLE COMPONENTS FOR PHASE 2

### 12.1 Core Infrastructure to Build On

**Leverage These:**
1. **ProjectHistory dataclass** (aggregator.py lines 176-215)
   - Unified container for all project data
   - Properties for quick lookups (task_by_id, decision_impact_graph)

2. **Query API filters** (query_api.py)
   - Task filtering patterns (by status, agent, time)
   - Timeline search logic
   - Pagination utilities

3. **Aggregator methods** (aggregator.py)
   - Task/agent/timeline building logic
   - Cache pattern
   - Data source loading infrastructure

4. **TaskHistory fields** (aggregator.py lines 54-131)
   - Pre-positioned for Phase 2 analysis:
     - `requirement_fidelity` (line 99) - Ready for scoring
     - `instruction_quality` (line 100) - Ready for scoring
     - `failure_causes` (line 101) - Ready for root cause analysis

### 12.2 Recommended Phase 2 Additions

**Don't duplicate:** Use existing aggregator patterns

**Instead add to TaskHistory:**
```python
# Analysis outputs (Phase 2)
requirement_fidelity: Optional[float]      # Already defined
instruction_quality: Optional[float]       # Already defined
failure_causes: list[str]                 # Already defined
decision_to_artifact_mapping: dict[str, list[str]]  # NEW
architectural_impact_score: Optional[float]  # NEW
```

**Instead create AnalysisResult:**
```python
@dataclass
class ProjectAnalysisResult:
    project_id: str
    timestamp: datetime
    analysis_type: str  # "requirement_fidelity", "instruction_quality", etc.
    findings: dict[str, Any]
    recommendations: list[str]
    raw_data: ProjectHistory  # Reference to source data
```

---

## 13. RECOMMENDATIONS FOR PHASE 2 IMPLEMENTATION

### 13.1 Architecture Approach

**Leverage Phase 1:**
1. Use ProjectHistoryAggregator as data source (don't duplicate)
2. Add analysis methods to ProjectHistoryQuery or create AnalysisQuery wrapper
3. Reuse TaskHistory fields (requirement_fidelity, instruction_quality, failure_causes)
4. Extend aggregator._build_task_histories() with analysis enrichment

**Example Pattern:**
```python
# Phase 2: AnalysisQuery wraps ProjectHistoryQuery
class ProjectAnalysisQuery(ProjectHistoryQuery):
    async def analyze_requirement_fidelity(self, project_id: str):
        history = await self.get_project_history(project_id)

        for task in history.tasks:
            # Use AI to compare requirements vs instructions
            task.requirement_fidelity = await self._score_fidelity(task)

        return history
```

### 13.2 Data Schema Extensions

**Minimal additions to Phase 1:**
- TaskHistory already has requirement_fidelity, instruction_quality, failure_causes
- ProjectSnapshot already has outcome fields
- No schema migration needed; just populate existing fields

### 13.3 Integration Points

**Where to integrate Phase 2 analysis:**
1. **Aggregator methods** (option A):
   - Extend `_build_task_histories()` to include analysis
   - Requires AI engine, but cleanest

2. **Query wrapper** (option B, recommended):
   - Create `ProjectAnalysisQuery` extending `ProjectHistoryQuery`
   - Add analysis methods alongside query methods
   - Cleaner separation of concerns

3. **MCP tool routing** (option C):
   - Add new query_type: "analysis_requirement_fidelity", etc.
   - Query logic in history.py like existing queries

**Recommended:** Option B (Query wrapper) - cleanest, preserves Phase 1 stability

### 13.4 Testing Strategy

**Build incrementally:**
1. Unit test individual scorers (fidelity, quality, etc.)
2. Integration test scorer + aggregator
3. Integration test scorer + MCP tool
4. End-to-end test full analysis pipeline
5. Performance test with large projects

**Use existing fixtures:**
- sample_project_history from test_query_api.py
- Extend with pre-recorded AI responses
- Don't mock AI engine; test with actual Claude if in CI

---

## 14. IMPLEMENTATION CHECKLIST FOR PHASE 2

### Phase 2A: Requirement Fidelity Analysis
- [ ] Create AI prompt to compare specification vs instructions
- [ ] Implement fidelity scorer
- [ ] Add to AnalysisQuery
- [ ] Update MCP tool
- [ ] Test and document

### Phase 2B: Instruction Quality Analysis
- [ ] Create AI prompt to score instruction clarity
- [ ] Implement quality scorer
- [ ] Add to AnalysisQuery
- [ ] Test and document

### Phase 2C: Root Cause Analysis
- [ ] Create AI prompt to analyze failures
- [ ] Implement cause analyzer
- [ ] Populate failure_causes field
- [ ] Test and document

### Phase 2D: Decision Impact Tracking
- [ ] Link decisions to artifacts produced
- [ ] Build decision_impact_score
- [ ] Analyze decision effectiveness
- [ ] Test and document

### Phase 2E: Multi-Project Analysis
- [ ] Create cross-project query support
- [ ] Implement pattern detection across projects
- [ ] Build meta-analysis reports
- [ ] Test and document

---

## 15. KEY FILES REFERENCE

### Must Read (In Order)

1. **start here:** `/Users/lwgray/dev/marcus/docs/phase1_quickstart.md` - Phase 1 overview
2. **data models:** `/Users/lwgray/dev/marcus/src/core/project_history.py` lines 1-352
3. **aggregation:** `/Users/lwgray/dev/marcus/src/analysis/aggregator.py` lines 1-100 (initialization)
4. **queries:** `/Users/lwgray/dev/marcus/src/analysis/query_api.py` lines 26-100 (interface)
5. **MCP exposure:** `/Users/lwgray/dev/marcus/src/marcus_mcp/tools/history.py` lines 23-100

### Examples & Tests

- Example usage: `/Users/lwgray/dev/marcus/examples/query_project_history_example.py`
- Data model tests: `/Users/lwgray/dev/marcus/tests/unit/core/test_project_history.py`
- Query tests: `/Users/lwgray/dev/marcus/tests/unit/analysis/test_query_api.py`
- SQLite tests: `/Users/lwgray/dev/marcus/tests/unit/core/test_project_history_sqlite.py`

### Supporting Infrastructure

- Memory system: `/Users/lwgray/dev/marcus/src/core/memory.py`
- Context system: `/Users/lwgray/dev/marcus/src/core/context.py` (decision logging)
- Error framework: `/Users/lwgray/dev/marcus/src/core/error_framework.py`
- Persistence: `/Users/lwgray/dev/marcus/src/core/persistence.py` (SQLite backend)

---

## Summary

Phase 1 provides a **robust, well-structured foundation** for post-project analysis:
- Data models are clean and extensible
- Aggregation unifies multiple data sources efficiently
- Query API provides flexibility for various analysis needs
- MCP integration enables agent access
- Testing patterns are established
- Code quality is high (types, docs, error handling)

**Phase 2 can build confidently on this foundation** by:
- Adding analysis methods to the query layer
- Populating TaskHistory analysis fields
- Leveraging AI for intelligence without duplicating data access logic
- Extending test fixtures for analysis scenarios

The architecture supports growth to multi-project analysis while maintaining clean separation of concerns.
