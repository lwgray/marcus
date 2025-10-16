# Function Reference: CPM and Subtask Dependency System

## Quick Navigation

- [CPM Functions](#cpm-functions)
- [Subtask Manager Functions](#subtask-manager-functions)
- [Dependency Wiring Functions](#dependency-wiring-functions)
- [Trigger Points](#trigger-points)

---

## CPM Functions

### `get_optimal_agent_count()`

**Location:** `src/marcus_mcp/tools/scheduling.py:16-96`

```python
async def get_optimal_agent_count(
    include_details: bool = False,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Calculate optimal number of agents using CPM analysis.

    Uses the unified dependency graph (including parent tasks and subtasks)
    to determine the optimal agent count for maximum efficiency.

    Parameters
    ----------
    include_details : bool
        Whether to include detailed parallel opportunities (default: False)
    state : Any
        Marcus server state instance (provides access to project_tasks)

    Returns
    -------
    Dict[str, Any]
        {
            "success": bool,
            "optimal_agents": int,
            "critical_path_hours": float,
            "max_parallelism": int,
            "estimated_completion_hours": float,
            "single_agent_hours": float,
            "efficiency_gain_percent": float,
            "total_tasks": int,
            "parallel_opportunities": List[Dict]  # if include_details=True
        }

    Raises
    ------
    ValueError
        If dependency graph contains cycles

    When called
    -----------
    - On-demand via API
    - NOT called automatically
    - NOT called during project selection
    - NOT called during refresh_project_state
    """
```

**Usage:**
```python
# In agent code
result = await get_optimal_agent_count(include_details=True, state=server)
if result["success"]:
    optimal_agents = result["optimal_agents"]
    efficiency = result["efficiency_gain_percent"]
```

---

### `calculate_optimal_agents()`

**Location:** `src/marcus_mcp/coordinator/scheduler.py:210-337`

```python
def calculate_optimal_agents(tasks: List[Task]) -> ProjectSchedule:
    """
    Calculate optimal number of agents using unified dependency graph.

    Uses critical path method (CPM) to find:
    1. Longest dependency chain (critical path)
    2. Maximum parallelism at any time point
    3. Optimal agent count for maximum efficiency

    Algorithm
    ---------
    1. Filter to workable tasks (is_subtask=True, status != DONE)
    2. Check for dependency cycles
    3. Calculate earliest start/finish times via topological sort
    4. Find critical path length (max finish time)
    5. Find peak parallelism (max concurrent tasks)
    6. Set optimal_agents = max_parallelism (peak allocation strategy)

    Parameters
    ----------
    tasks : List[Task]
        All tasks in the project (parents + subtasks)

    Returns
    -------
    ProjectSchedule
        Dataclass with:
        - optimal_agents: int
        - critical_path_hours: float
        - max_parallelism: int
        - estimated_completion_hours: float
        - single_agent_hours: float
        - efficiency_gain: float (0.0-1.0)
        - parallel_opportunities: List[Dict]

    Raises
    ------
    ValueError
        If cycles detected in dependency graph

    Notes
    -----
    - ONLY subtasks (is_subtask=True) are analyzed
    - Parent tasks are EXCLUDED from calculation
    - Completed tasks (status=DONE) are EXCLUDED
    - Strategy: provision for PEAK demand (max_parallelism)
    - Rationale: Idle agents are cheap; bottlenecks are not resolvable
    """
```

**Key Lines:**
- Line 248-250: Filter to workable tasks
- Line 265: Cycle detection
- Line 269: Calculate task times
- Line 272: Find critical path
- Line 279: Find max parallelism
- Line 291: Set optimal = max_parallelism

---

### `topological_sort()`

**Location:** `src/marcus_mcp/coordinator/scheduler.py:50-104`

```python
def topological_sort(tasks: List[Task]) -> List[Task]:
    """
    Sort tasks in topological order (dependencies before dependents).

    Uses Kahn's algorithm for topological sorting of DAG.

    Parameters
    ----------
    tasks : List[Task]
        List of tasks to sort

    Returns
    -------
    List[Task]
        Tasks sorted in dependency order

    Raises
    ------
    ValueError
        If the dependency graph contains a cycle
    """
```

---

### `calculate_task_times()`

**Location:** `src/marcus_mcp/coordinator/scheduler.py:166-207`

```python
def calculate_task_times(tasks: List[Task]) -> Dict[str, Dict[str, Any]]:
    """
    Calculate earliest start and finish times for each task using CPM.

    Forward pass through DAG to compute start/finish times.

    Parameters
    ----------
    tasks : List[Task]
        List of tasks (must be in topological order)

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Mapping of task_id to {
            "start": float,
            "finish": float,
            "task": Task
        }
    """
```

---

## Subtask Manager Functions

### `SubtaskManager.add_subtasks()`

**Location:** `src/marcus_mcp/coordinator/subtask_manager.py:130-243`

```python
def add_subtasks(
    self,
    parent_task_id: str,
    subtasks: List[Dict[str, Any]],
    project_tasks: Optional[List[Task]] = None,
    metadata: Optional[SubtaskMetadata] = None,
) -> List[Task]:
    """
    Add subtasks for a parent task to unified project_tasks storage.

    Creates Task objects with is_subtask=True and appends to project_tasks.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    subtasks : List[Dict[str, Any]]
        List of subtask dictionaries with fields:
        - name: str (required)
        - description: str (required)
        - estimated_hours: float (required)
        - dependencies: List[str] (optional)
        - priority: Priority (optional)
        - provides: str (optional) - what this outputs
        - requires: str (optional) - what this needs
        - file_artifacts: List[str] (optional)
    project_tasks : Optional[List[Task]]
        Unified task storage. If None, uses legacy mode only.
    metadata : Optional[SubtaskMetadata]
        Metadata about the decomposition

    Returns
    -------
    List[Task]
        Created Task objects (with is_subtask=True)

    Storage
    -------
    - Stores in legacy format (self.subtasks dict)
    - Stores in unified format (appends to project_tasks)
    - Persists to disk (data/marcus_state/subtasks.json)

    When called
    -----------
    - During task decomposition (NLP phase)
    - NOT called during project selection
    """
```

**Key Fields Set:**
- `is_subtask=True`: Marks as subtask
- `parent_task_id`: Links to parent
- `provides`: Output for cross-parent matching
- `requires`: Input requirements for matching
- `dependencies`: List of task IDs (intra-parent deps)

---

### `SubtaskManager.migrate_to_unified_storage()`

**Location:** `src/marcus_mcp/coordinator/subtask_manager.py:666-731`

```python
def migrate_to_unified_storage(self, project_tasks: List[Task]) -> None:
    """
    Migrate old Subtask objects to unified Task storage.

    Converts legacy Subtask objects to Task objects with is_subtask=True
    and appends them to project_tasks.

    CRITICAL: Only migrates subtasks whose parent tasks exist in project_tasks.
    This ensures subtasks from other projects don't leak in.

    Parameters
    ----------
    project_tasks : List[Task]
        Unified task storage to migrate subtasks into

    Triggers
    --------
    - Called in refresh_project_state() (server.py line 844)
    - Only called once per project (checked by _subtasks_migrated flag)
    - After migration completes, cross-parent deps are wired

    Safety Checks
    -------------
    parent_task_ids = {t.id for t in project_tasks if not t.is_subtask}
    for subtask_id, subtask in self.subtasks.items():
        if subtask.parent_task_id not in parent_task_ids:
            continue  # Skip if parent doesn't exist

    Result
    ------
    - Legacy subtasks converted to unified format
    - Only subtasks for current project included
    - State persisted to disk
    """
```

**When Called:**
- Line 844 in `server.py` during `refresh_project_state()`
- Condition: `if not self._subtasks_migrated`
- Only ONCE per project selection

---

### `SubtaskManager.get_subtasks()`

**Location:** `src/marcus_mcp/coordinator/subtask_manager.py:245-301`

```python
def get_subtasks(
    self,
    parent_task_id: str,
    project_tasks: Optional[List[Task]] = None,
) -> List[Task]:
    """
    Get all subtasks for a parent task from unified storage.

    Queries from unified storage or falls back to legacy storage.

    Parameters
    ----------
    parent_task_id : str
        ID of the parent task
    project_tasks : Optional[List[Task]]
        Unified task storage. If None, falls back to legacy.

    Returns
    -------
    List[Task]
        List of Task objects (with is_subtask=True) ordered by subtask_index
    """
```

---

### `SubtaskManager.update_subtask_status()`

**Location:** `src/marcus_mcp/coordinator/subtask_manager.py:343-401`

```python
def update_subtask_status(
    self,
    subtask_id: str,
    status: TaskStatus,
    project_tasks: Optional[List[Task]] = None,
    assigned_to: Optional[str] = None,
) -> bool:
    """
    Update the status of a subtask in unified storage.

    Updates both unified and legacy storage for backwards compatibility.

    Parameters
    ----------
    subtask_id : str
        ID of the subtask
    status : TaskStatus
        New status (TODO, IN_PROGRESS, DONE, BLOCKED)
    project_tasks : Optional[List[Task]]
        Unified task storage. If None, falls back to legacy.
    assigned_to : Optional[str]
        Agent ID assigned to the subtask

    Returns
    -------
    bool
        True if update successful
    """
```

---

## Dependency Wiring Functions

### `wire_cross_parent_dependencies()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:410-496`

```python
async def wire_cross_parent_dependencies(
    project_tasks: List[Task],
    ai_engine: Any,
    embedding_model: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Create cross-parent dependencies using hybrid matching.

    After all tasks have been decomposed, analyzes each subtask's
    'requires' field and matches it against other subtasks' 'provides'
    fields to create fine-grained cross-parent dependencies.

    Pipeline
    --------
    For each subtask with requires field:
        1. Filter candidates using embeddings (fast semantic matching)
        2. Use LLM to validate candidates (accurate reasoning)
        3. Run sanity checks (cycles, phase order, etc.)
        4. Add validated deps to task.dependencies

    Parameters
    ----------
    project_tasks : List[Task]
        All tasks in the project (parents and subtasks)
    ai_engine : Any
        AI engine for LLM reasoning
    embedding_model : Optional[Any]
        Sentence transformer model for embeddings (optional)

    Returns
    -------
    Dict[str, Any]
        Statistics:
        {
            "subtasks_analyzed": int,
            "dependencies_created": int,
            "llm_calls": int,
            "rejected_cycles": int,
            "skipped_no_requires": int,
            "skipped_no_candidates": int,
            "total_time_seconds": float
        }

    When called
    -----------
    - Line 872 in refresh_project_state() (server.py)
    - After migrate_to_unified_storage() completes
    - Only run once per project (not re-run on subsequent refreshes)
    """
```

**Key Algorithm:**
1. Embedding filter: Fast semantic matching (cosine similarity ≥ 0.6)
2. LLM reasoning: Accurate validation on candidate set
3. Sanity checks:
   - Cycle detection (DFS)
   - Same-parent check (skip intra-parent)
   - Phase ordering (Design → Implement → Test)

---

### `hybrid_dependency_resolution()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:325-407`

```python
async def hybrid_dependency_resolution(
    subtask: Task,
    all_tasks: List[Task],
    ai_engine: Any,
    embedding_model: Optional[Any] = None,
) -> List[str]:
    """
    Find cross-parent dependencies using hybrid approach.

    Combines embeddings (fast filtering) with LLM reasoning (accurate)
    and sanity checks (prevent errors).

    Parameters
    ----------
    subtask : Task
        The subtask to analyze
    all_tasks : List[Task]
        All tasks in the project
    ai_engine : Any
        AI engine for LLM reasoning
    embedding_model : Optional[Any]
        Sentence transformer model (optional)

    Returns
    -------
    List[str]
        List of task IDs to add as dependencies

    Process
    -------
    1. Stage 1: Filter candidates using embeddings
    2. Stage 2: Use LLM to make final decision
    3. Stage 3: Sanity checks (cycles, phase order, etc.)
    """
```

---

### `filter_candidates_by_embeddings()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:21-98`

```python
def filter_candidates_by_embeddings(
    subtask: Task,
    all_tasks: List[Task],
    embedding_model: Any,
    similarity_threshold: float = 0.6,
    max_candidates: int = 10,
) -> List[Tuple[Task, float]]:
    """
    Filter potential dependency candidates using semantic embeddings.

    Uses sentence transformers to compute semantic similarity between
    the subtask's requires field and other tasks' provides fields.

    Parameters
    ----------
    subtask : Task
        The subtask being analyzed
    all_tasks : List[Task]
        All tasks in the project
    embedding_model : Any
        Sentence transformer model
    similarity_threshold : float
        Minimum cosine similarity (default 0.6)
    max_candidates : int
        Maximum candidates to return (default 10)

    Returns
    -------
    List[Tuple[Task, float]]
        List of (task, similarity_score) tuples, sorted by similarity descending

    Process
    -------
    1. Encode subtask.requires field
    2. For each other subtask:
       - Skip if same parent (intra-parent handled separately)
       - Skip if no provides field
       - Encode provides field
       - Compute cosine similarity
       - Keep if >= threshold
    3. Sort by similarity, return top N
    """
```

---

### `resolve_dependencies_with_llm()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:101-216`

```python
async def resolve_dependencies_with_llm(
    subtask: Task,
    candidates: List[Task],
    ai_engine: Any,
) -> Dict[str, Any]:
    """
    Use LLM to determine which candidates are true dependencies.

    Given a subtask and candidate providers, asks LLM to reason
    about which should actually be dependencies.

    Parameters
    ----------
    subtask : Task
        The subtask being analyzed
    candidates : List[Task]
        Candidate provider tasks (pre-filtered by embeddings)
    ai_engine : Any
        AI engine for LLM reasoning

    Returns
    -------
    Dict[str, Any]
        {
            "dependencies": List[str],  # task IDs to add
            "reasoning": Dict[str, str] # explanations
        }

    LLM Rules (from prompt)
    -----------------------
    - Only create if task TRULY NEEDS the output
    - Match requires semantically with provides
    - DO NOT create same-parent dependencies
    - Respect workflow: Design → Implement → Test
    - Conservative: false negative > false positive
    - Match actual specification, not research
    """
```

---

### `would_create_cycle()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:219-274`

```python
def would_create_cycle(
    from_task_id: str,
    to_task_id: str,
    all_tasks: List[Task],
) -> bool:
    """
    Check if adding a dependency would create a circular dependency.

    Uses depth-first search to detect if edge from_task_id → to_task_id
    would create a cycle in the dependency graph.

    Parameters
    ----------
    from_task_id : str
        The task that would gain a new dependency
    to_task_id : str
        The task being added as a dependency
    all_tasks : List[Task]
        All tasks in the project

    Returns
    -------
    bool
        True if adding this dependency would create a cycle
    """
```

---

### `validate_phase_order()`

**Location:** `src/marcus_mcp/coordinator/dependency_wiring.py:277-322`

```python
def validate_phase_order(subtask: Task, dependency_task: Task) -> bool:
    """
    Validate that dependency follows proper phase ordering.

    Ensures dependencies follow Design → Implement → Test workflow.
    For example, Implementation can depend on Design, but Design
    cannot depend on Implementation.

    Parameters
    ----------
    subtask : Task
        The task that would gain the dependency
    dependency_task : Task
        The task being added as a dependency

    Returns
    -------
    bool
        True if phase ordering is valid

    Phase Order
    -----------
    0: design
    1: implement
    2: test
    3: integration

    Valid Dependencies
    ------------------
    implement → design ✓
    test → implement ✓
    design → implement ✗
    """
```

---

## Trigger Points

### Subtask Migration Trigger

**Location:** `server.py:839-845`

```python
if self.subtask_manager and self.project_tasks is not None and not self._subtasks_migrated:
    self.subtask_manager.migrate_to_unified_storage(self.project_tasks)
    self._subtasks_migrated = True
```

**When:** First call to `refresh_project_state()` after `select_project()`
**Condition:** `_subtasks_migrated == False`
**Called by:** `select_project()` → `refresh_project_state()`

---

### Cross-Parent Wiring Trigger

**Location:** `server.py:847-886`

```python
try:
    from src.marcus_mcp.coordinator import wire_cross_parent_dependencies

    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

    stats = await wire_cross_parent_dependencies(
        self.project_tasks,
        self.ai_engine,
        embedding_model
    )
except Exception as e:
    logger.error(f"Failed to wire cross-parent dependencies: {e}")
```

**When:** After migration completes successfully
**Condition:** After `_subtasks_migrated = True` and no errors
**Called by:** `refresh_project_state()`

---

### CPM Calculation Trigger

**Location:** External API call

```python
await get_optimal_agent_count(include_details=True, state=server)
```

**When:** On-demand, never automatic
**Called by:** User/agent explicitly via API
**Never called by:** `select_project()`, `refresh_project_state()`, or any internal function

---

## Data Structures

### ProjectSchedule (dataclass)

**Location:** `scheduler.py:18-47`

```python
@dataclass
class ProjectSchedule:
    optimal_agents: int
    critical_path_hours: float
    max_parallelism: int
    estimated_completion_hours: float
    single_agent_hours: float
    efficiency_gain: float  # 0.0-1.0
    parallel_opportunities: List[Dict[str, Any]] = field(default_factory=list)
```

---

### Subtask (dataclass)

**Location:** `subtask_manager.py:20-73`

```python
@dataclass
class Subtask:
    id: str
    parent_task_id: str
    name: str
    description: str
    status: TaskStatus
    priority: Priority
    assigned_to: Optional[str]
    created_at: datetime
    estimated_hours: float
    dependencies: List[str] = field(default_factory=list)
    dependency_types: List[str] = field(default_factory=list)
    file_artifacts: List[str] = field(default_factory=list)
    provides: Optional[str] = None
    requires: Optional[str] = None
    order: int = 0
```

---

### SubtaskMetadata (dataclass)

**Location:** `subtask_manager.py:75-93`

```python
@dataclass
class SubtaskMetadata:
    shared_conventions: Dict[str, Any] = field(default_factory=dict)
    decomposed_at: datetime = field(default_factory=datetime.now)
    decomposed_by: str = "ai"
```

---

## Configuration and Constants

### Embedding Similarity Threshold
- **File:** `dependency_wiring.py:21-98`
- **Default:** 0.6 (cosine similarity)
- **Meaning:** Tasks with similarity < 0.6 are filtered out

### Max Candidates for LLM
- **File:** `dependency_wiring.py:21-98`
- **Default:** 10
- **Meaning:** Only top 10 similar tasks sent to LLM

### Subtask State File
- **Location:** `data/marcus_state/subtasks.json`
- **Format:** JSON with structure {subtasks, parent_to_subtasks, metadata}
- **Purpose:** Persist subtask state across restarts

### Embedding Model
- **Model:** `all-MiniLM-L6-v2`
- **Library:** `sentence-transformers`
- **Fallback:** If unavailable, uses LLM-only matching
- **Location:** Loaded in `refresh_project_state()` line 861

---

## Error Handling

### CPM Calculation Errors

```python
except ValueError as e:
    # Dependency cycles detected
    return {
        "success": False,
        "error": f"Cannot calculate optimal agents: {str(e)}",
        "suggestion": "Check for circular dependencies"
    }
except Exception as e:
    logger.error(f"Error calculating optimal agents: {e}")
    return {"success": False, "error": str(e)}
```

### Dependency Wiring Errors

```python
try:
    await wire_cross_parent_dependencies(...)
except Exception as e:
    logger.error(f"Failed to wire cross-parent dependencies: {e}")
    # Don't fail refresh - wiring is optional
```

---

## Performance Considerations

1. **CPM Calculation:** O(V + E) where V=tasks, E=dependencies
   - Topological sort: O(V + E)
   - Task times calculation: O(V + E)
   - Critical path: O(V)

2. **Embedding Filtering:** O(N * M) where N=subtasks, M=candidates
   - Reduced by similarity threshold

3. **LLM Reasoning:** Bound by max_candidates (default 10)
   - One LLM call per subtask with requires field

4. **Cross-Parent Wiring:** Only runs once per project

---

## Testing

### Test Files

- Unit tests: `tests/unit/coordinator/test_scheduler.py`
- Integration tests: `tests/integration/e2e/test_task_decomposition_e2e.py`
- Dependency wiring: `tests/unit/coordinator/test_dependency_wiring.py`

### Key Test Cases

- `test_calculate_optimal_agents_sequential`: Linear dependency chain
- `test_calculate_optimal_agents_fully_parallel`: Independent tasks
- `test_calculate_optimal_agents_mixed`: Mix of sequential and parallel
- `test_calculate_optimal_agents_with_subtasks`: Includes subtask filtering
