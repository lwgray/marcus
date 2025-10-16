# CPM Calculation Timing and Subtask Dependency Creation Analysis

## Executive Summary

This document traces the timing and triggers for:
1. **CPM (Critical Path Method) Calculation** - When and how optimal agent count is determined
2. **Subtask Dependency Creation** - When and how subtask dependencies are generated and wired

---

## Part 1: CPM Calculation Timing

### Overview
CPM calculation determines the optimal number of agents needed to complete a project by analyzing the critical path (longest dependency chain) and maximum parallelism in the task graph.

### Key Components

#### 1.1 Main Entry Point: `get_optimal_agent_count()`
**File:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/tools/scheduling.py` (Lines 16-96)

```
async def get_optimal_agent_count(include_details=False, state=None)
    ├─ Gets tasks from state.project_tasks (unified storage)
    ├─ Calls calculate_optimal_agents(tasks)
    └─ Returns ProjectSchedule with optimal_agents, critical_path, efficiency metrics
```

**Parameters:**
- `state.project_tasks`: List containing BOTH parents AND subtasks (unified)
- `include_details`: Whether to include parallel opportunity details

**Returns:**
```python
{
    "success": True,
    "optimal_agents": int,           # Recommended agent count
    "critical_path_hours": float,    # Duration of longest path
    "max_parallelism": int,          # Max tasks running simultaneously
    "estimated_completion_hours": float,
    "single_agent_hours": float,
    "efficiency_gain_percent": float,
    "total_tasks": int,
    "parallel_opportunities": List[Dict]  # (if include_details=True)
}
```

#### 1.2 Core Algorithm: `calculate_optimal_agents()`
**File:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/scheduler.py` (Lines 210-337)

**Algorithm Steps:**

```
Input: tasks (List[Task])
  ├─ Filter to WORKABLE tasks (subtasks only, not DONE)
  │   Line 248-250:
  │   workable_tasks = [t for t in tasks
  │       if t.is_subtask and t.status != TaskStatus.DONE]
  │
  ├─ Check for cycles
  │   Line 265: if detect_cycles(workable_tasks) → raise ValueError
  │
  ├─ Calculate task times (CPM forward pass)
  │   Line 269: task_times = calculate_task_times(workable_tasks)
  │   ├─ For each task: earliest_start = max(finish times of dependencies)
  │   └─ finish = earliest_start + task.estimated_hours
  │
  ├─ Find critical path (longest path in DAG)
  │   Line 272: critical_path = max(t["finish"] for t in task_times.values())
  │
  ├─ Find maximum parallelism (peak concurrent tasks)
  │   Line 279: max_parallelism = max(len(tasks_at_time) for time in time_slices)
  │
  ├─ Calculate efficiency gain
  │   total_work = sum(task.estimated_hours for all workable_tasks)
  │   efficiency_gain = (total_work - critical_path) / total_work
  │
  └─ Optimal agents = max_parallelism (strategy at lines 284-291)
      (Provision for PEAK demand, not average)

Output: ProjectSchedule
```

**CRITICAL FILTERING (Lines 245-262):**
- Only analyzes SUBTASKS (`is_subtask=True`)
- Excludes DONE tasks (`task.status != TaskStatus.DONE`)
- Parent tasks are IGNORED from calculation
- Result: Only "workable" leaf-level tasks contribute to optimal count

### 1.3 When Is CPM Calculated? (Timing)

#### Trigger Points:

**PRIMARY TRIGGER: On-Demand via API**
- Called by external tools when `get_optimal_agent_count` is invoked
- NO automatic periodic calculation
- NO automatic recalculation on project selection

**SECONDARY: During Project Refresh**
- `refresh_project_state()` loads all tasks
- Caller must separately invoke `get_optimal_agent_count()`
- CPM is NOT called automatically during refresh

#### Related Flow in `select_project()` (project_management.py, Lines 515-543)

```python
async def select_project(server, arguments):
    project_id = arguments.get("project_id")

    if project_id:
        await server.project_manager.switch_project(project_id)
        server.kanban_client = await server.project_manager.get_kanban_client()

        # Reset subtask migration flag
        server._subtasks_migrated = False

        # ← THIS LOADS TASKS but DOES NOT CALCULATE CPM
        await server.refresh_project_state()

        # CPM is only calculated IF caller explicitly requests it:
        # await get_optimal_agent_count(state=server)
```

### 1.4 Project State Refresh: `refresh_project_state()`
**File:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/server.py` (Lines 827-951)

**Sequence:**

```
refresh_project_state()
    ├─ Get all tasks from kanban: project_tasks = await kanban_client.get_all_tasks()
    │
    ├─ Migrate subtasks (ONCE per project)
    │   if not self._subtasks_migrated:
    │       subtask_manager.migrate_to_unified_storage(project_tasks)
    │       self._subtasks_migrated = True
    │
    ├─ Wire cross-parent dependencies (Lines 847-886)
    │   await wire_cross_parent_dependencies(
    │       project_tasks,
    │       ai_engine,
    │       embedding_model
    │   )
    │   ← Creates dependencies between subtasks of different parents
    │
    ├─ Update memory system (if enabled)
    │   if self.memory and project_tasks:
    │       self.memory.update_project_tasks(project_tasks)
    │
    └─ Create ProjectState summary

Note: CPM is NOT called here - only explicit API calls trigger calculation
```

### 1.5 Caching and Optimization

**NO CACHING IMPLEMENTED:**
- Each call to `get_optimal_agent_count()` performs full CPM analysis
- No memoization of results
- No TTL or invalidation logic
- Result: Multiple calls = multiple calculations

**OPTIMIZATION IN CALCULATION (Line 284-291):**
- Uses max_parallelism directly (peak allocation strategy)
- Avoids expensive dynamic scaling scenarios
- Simple and effective for agent provisioning

---

## Part 2: Subtask Dependency Creation

### Overview
Subtasks are decomposed task units with fine-grained dependencies. Dependencies are created in TWO stages:
1. **Intra-parent dependencies** - between subtasks of same parent (during creation)
2. **Cross-parent dependencies** - between subtasks of different parents (during refresh)

### 2.1 Subtask Lifecycle

```
Timeline: Task Creation → Subtask Decomposition → Unified Storage → Cross-Parent Wiring → CPM Calculation

Step 1: TASK CREATION
  └─ When: During project creation or manual task creation
  └─ Where: NLP tools in src/integrations/nlp_*.py

Step 2: SUBTASK DECOMPOSITION (Lines 837-845 in server.py)
  └─ When: During refresh_project_state() - ONLY ONCE per project
  └─ Trigger: First time refresh_project_state() is called after project select
  └─ Flag: _subtasks_migrated prevents re-running migration

Step 3: UNIFIED STORAGE MIGRATION (Lines 666-731 in subtask_manager.py)
  └─ Converts Subtask objects → Task objects with is_subtask=True
  └─ Appends to project_tasks list

Step 4: CROSS-PARENT DEPENDENCY WIRING (Lines 847-886 in server.py)
  └─ When: After migration completes
  └─ Uses: Hybrid approach (embeddings + LLM)
  └─ Creates: Dependencies between different parent tasks' subtasks

Step 5: CPM CALCULATION (Manual trigger)
  └─ When: Caller invokes get_optimal_agent_count()
  └─ Uses: All project_tasks (parents + subtasks with unified dependencies)
```

### 2.2 Subtask Manager: Creation and Storage

**File:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/subtask_manager.py`

#### Creation: `add_subtasks()` (Lines 130-243)

```python
def add_subtasks(parent_task_id, subtasks, project_tasks=None, metadata=None):

    for idx, subtask_data in enumerate(subtasks):
        # Generate ID
        subtask_id = f"{parent_task_id}_sub_{idx + 1}"

        # Create Legacy Subtask object
        legacy_subtask = Subtask(
            id=subtask_id,
            parent_task_id=parent_task_id,
            dependencies=subtask_data.get("dependencies", []),
            ...
        )

        # Create new Task object (unified format)
        task = Task(
            id=subtask_id,
            is_subtask=True,
            parent_task_id=parent_task_id,
            provides=subtask_data.get("provides"),
            requires=subtask_data.get("requires"),
            ...
        )

        # Add to unified storage
        if project_tasks is not None:
            project_tasks.append(task)  # ← Adds to unified list

        created_tasks.append(task)

    # Persist to file
    self._save_state()

    return created_tasks
```

**Key Fields for Dependency Wiring:**
- `is_subtask=True`: Marks as subtask for filtering
- `parent_task_id`: Links to parent task
- `provides`: What this subtask outputs (for dependency matching)
- `requires`: What this subtask needs (for dependency matching)
- `dependencies`: List of task IDs this depends on

#### Migration: `migrate_to_unified_storage()` (Lines 666-731)

```python
def migrate_to_unified_storage(self, project_tasks):
    """
    Convert legacy Subtask objects to unified Task format.

    Called ONCE per project during first refresh_project_state().
    Only migrates subtasks whose parent tasks exist in project_tasks.
    """

    parent_task_ids = {t.id for t in project_tasks if not t.is_subtask}

    for subtask_id, subtask in self.subtasks.items():
        # Only migrate if parent exists in current project
        if subtask.parent_task_id not in parent_task_ids:
            continue

        # Convert Subtask → Task
        task = Task(
            is_subtask=True,
            parent_task_id=subtask.parent_task_id,
            provides=subtask.provides,
            requires=subtask.requires,
            ...
        )

        project_tasks.append(task)  # ← Unified storage
```

**CRITICAL FILTERING (Lines 689-701):**
- Only migrates subtasks whose **parent tasks exist** in current project
- Prevents subtasks from other projects leaking into unified storage
- Parent task must be in project_tasks (not is_subtask)

### 2.3 Cross-Parent Dependency Wiring

**File:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/dependency_wiring.py`

#### Entry Point: `wire_cross_parent_dependencies()` (Lines 410-496)

```
Triggered: After migration, during refresh_project_state() (line 872)

For each subtask in project_tasks:
    if not task.is_subtask:
        continue  # Skip parent tasks

    if not task.requires:
        continue  # Skip if no requirements specified

    # Find matching providers using hybrid approach
    new_deps = await hybrid_dependency_resolution(
        subtask=task,
        all_tasks=project_tasks,
        ai_engine=ai_engine,
        embedding_model=embedding_model
    )

    # Add new dependencies (preserve existing)
    for dep_id in new_deps:
        if dep_id not in task.dependencies:
            task.dependencies.append(dep_id)

Output: Statistics
    - subtasks_analyzed: Count analyzed
    - dependencies_created: Cross-parent deps added
    - llm_calls: LLM invocations
```

#### Hybrid Resolution Pipeline

**Stage 1: Embedding-Based Filtering (Lines 21-98)**

```python
def filter_candidates_by_embeddings(subtask, all_tasks, embedding_model):
    """Fast first-pass filtering using semantic similarity."""

    if not subtask.requires:
        return []

    # Encode subtask's "requires" field
    requires_embedding = embedding_model.encode(subtask.requires)

    candidates = []
    for task in all_tasks:
        if not task.is_subtask or task.id == subtask.id:
            continue

        if task.parent_task_id == subtask.parent_task_id:
            continue  # Skip same-parent (handled by intra-parent deps)

        if not task.provides:
            continue

        # Compute cosine similarity
        provides_embedding = embedding_model.encode(task.provides)
        similarity = cosine_similarity(requires_embedding, provides_embedding)

        if similarity >= threshold (0.6):
            candidates.append((task, similarity))

    # Sort by similarity, return top N
    return sorted(candidates, key=lambda x: x[1], reverse=True)[:max_candidates]
```

**Stage 2: LLM Reasoning (Lines 101-216)**

```python
async def resolve_dependencies_with_llm(subtask, candidates, ai_engine):
    """Use LLM to validate candidates and provide reasoning."""

    # Build prompt with:
    # - Subtask requirements
    # - Candidate providers
    # - Critical rules (no same-parent, design→implement→test ordering)

    response = await ai_engine.generate_structured_response(
        prompt=detailed_analysis_prompt,
        response_format={
            "type": "object",
            "properties": {
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "reasoning": {"type": "object", ...}
            }
        }
    )

    return {
        "dependencies": [list of task IDs],
        "reasoning": {task_id: explanation, ...}
    }
```

**Stage 3: Sanity Checks (Lines 380-407)**

```python
for dep_id in proposed_deps:
    dep_task = next((t for t in all_tasks if t.id == dep_id), None)
    if not dep_task:
        continue  # Check 1: Exists

    if dep_task.parent_task_id == subtask.parent_task_id:
        continue  # Check 2: Not same parent

    if would_create_cycle(subtask.id, dep_id, all_tasks):
        continue  # Check 3: No cycles

    if not validate_phase_order(subtask, dep_task):
        continue  # Check 4: Valid phase ordering

    validated_deps.append(dep_id)
```

---

## Part 3: Integration and Timing Diagram

### Complete Flow: Project Selection to CPM Calculation

```
User calls select_project(project_id)
│
├─ 1. Switch project context
│     await project_manager.switch_project(project_id)
│
├─ 2. Get kanban client
│     kanban_client = await project_manager.get_kanban_client()
│
├─ 3. Reset migration flag
│     server._subtasks_migrated = False
│
├─ 4. REFRESH PROJECT STATE (Line 525)
│     await server.refresh_project_state()
│     │
│     ├─ Get all tasks from kanban
│     │  project_tasks = await kanban_client.get_all_tasks()
│     │  (Contains parents + any existing subtasks)
│     │
│     ├─ FIRST TIME ONLY: Migrate subtasks (Lines 839-845)
│     │  if not server._subtasks_migrated:
│     │      subtask_manager.migrate_to_unified_storage(project_tasks)
│     │      server._subtasks_migrated = True
│     │
│     └─ FIRST TIME ONLY: Wire cross-parent deps (Lines 847-886)
│        try:
│            from src.marcus_mcp.coordinator import wire_cross_parent_dependencies
│            embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
│            stats = await wire_cross_parent_dependencies(
│                project_tasks,
│                ai_engine,
│                embedding_model
│            )
│        except Exception as e:
│            logger.error(...) # Don't fail refresh
│
├─ 5. Return project info to caller
│     task_count = len(project_tasks)
│
└─ CALLER OPTIONALLY: Calculate optimal agents
   User calls: get_optimal_agent_count(include_details=True, state=server)
   │
   └─ CPM Analysis:
      - Filter to workable tasks (subtasks, not DONE)
      - Build task times using topological sort
      - Find critical path length
      - Calculate max parallelism
      - Return optimal_agents = max_parallelism
```

### Condition for Each Stage

| Stage | Condition | Location | Executed |
|-------|-----------|----------|----------|
| Subtask Migration | `_subtasks_migrated == False` | line 839 | ONCE per project |
| Cross-Parent Wiring | After migration succeeds | line 847 | ONCE per project |
| CPM Calculation | Explicit API call | scheduling.py:16 | ON-DEMAND |

---

## Part 4: Key Findings and Implications

### Finding 1: CPM is NOT Automatic
- CPM calculation requires explicit `get_optimal_agent_count()` call
- NOT triggered by project selection
- NOT triggered by refresh_project_state()
- NOT recalculated on task updates
- Caller must manually request analysis

### Finding 2: Subtask Dependencies are Created ONCE
- Intra-parent dependencies: During task decomposition (NLP phase)
- Cross-parent dependencies: During first refresh_project_state() after selection
- Wiring uses hybrid approach: embeddings (fast) + LLM (accurate) + sanity checks
- Once created, dependencies persist (stored in task.dependencies list)

### Finding 3: Unified Storage Strategy
- All tasks (parents + subtasks) in single project_tasks list
- Differentiation via `is_subtask` flag
- CPM filters to subtasks only, ignores parents
- Unified graph enables accurate parallelism analysis

### Finding 4: Migration Safety
- Only migrates subtasks whose parent tasks exist in project_tasks
- Prevents cross-project subtask pollution
- Called once, flag-protected against re-runs
- State persisted to disk (data/marcus_state/subtasks.json)

### Finding 5: Optimization in CPM
- Provisions for PEAK parallelism, not average
- Strategy: max_parallelism = optimal_agents
- Rationale: Idle agents have low cost; bottleneck cannot be resolved dynamically
- Result: Better to overprovision than underprovision

---

## Part 5: Files and Line Numbers Reference

### CPM Implementation
- **Entry point:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/tools/scheduling.py:16-96`
- **Algorithm:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/scheduler.py:210-337`
- **Topological sort:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/scheduler.py:50-104`
- **Cycle detection:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/scheduler.py:107-163`
- **Task timing:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/scheduler.py:166-207`

### Subtask Creation & Dependency Wiring
- **Subtask Manager:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/subtask_manager.py:95-731`
  - `add_subtasks()`: Lines 130-243
  - `migrate_to_unified_storage()`: Lines 666-731

- **Dependency Wiring:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/coordinator/dependency_wiring.py:1-496`
  - `wire_cross_parent_dependencies()`: Lines 410-496
  - `hybrid_dependency_resolution()`: Lines 325-407
  - Embedding filter: Lines 21-98
  - LLM resolution: Lines 101-216
  - Cycle detection: Lines 219-274
  - Phase validation: Lines 277-322

### Integration Points
- **Project refresh:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/server.py:827-951`
  - Migration trigger: Lines 839-845
  - Wiring trigger: Lines 847-886

- **Project selection:** `/Users/lwgray/dev/worktrees/independent-tasks/src/marcus_mcp/tools/project_management.py:475-682`
  - Lines 522, 526 (reset flag & refresh state)
  - Lines 589-593, 625-629 (in board_name search flow)

---

## Conclusion

The system implements a two-phase approach:
1. **Synchronous Phase:** Subtask creation & unified storage (happens on project load)
2. **Asynchronous Phase:** CPM analysis (on-demand via API)

This allows for:
- Lazy evaluation of CPM (only when needed)
- Efficient project switching (minimal upfront cost)
- Accurate dependency analysis (full graph resolved before CPM)
- Safety checks (cycle detection, phase validation)

The trigger for subtask wiring is `refresh_project_state()`, which is called during `select_project()`. CPM is never automatically calculated; it's always on-demand.
