# CPM and Subtask Dependency Analysis Overview

This section contains comprehensive analysis of the Critical Path Method (CPM) calculation timing and subtask dependency creation system in Marcus.

## Key Documents

### [CPM and Subtask Timing Analysis](cpm-subtask-timing-analysis)
Comprehensive analysis covering:
- CPM Calculation Timing and Architecture
- Subtask Dependency Creation System
- Integration and Complete Flow Diagram
- Key Findings and Implications
- Detailed File and Line Number Reference

**Best for:** Understanding the complete system architecture and flow

## Quick Answer Lookup

### Where is CPM calculated?
- **File:** `src/marcus_mcp/coordinator/scheduler.py:210-337`
- **Function:** `calculate_optimal_agents(tasks)`
- **Entry point:** `src/marcus_mcp/tools/scheduling.py:16-96`

### When is CPM triggered?
- **Trigger:** On-demand via API call to `get_optimal_agent_count()`
- **NOT automatic:** Never triggered by project selection or refresh
- **NOT called during:** select_project(), refresh_project_state()
- **Result:** Always on-demand, lazy evaluation

### When are subtask dependencies created?
- **Intra-parent dependencies:** During task decomposition (NLP phase)
- **Cross-parent dependencies:** During first `refresh_project_state()` after project selection
- **Trigger:** `select_project()` → `switch_project()` → `refresh_project_state()` → migration → wiring

### How does CPM filtering work?
- **Filters:** Only subtasks (`is_subtask=True`) that are NOT completed
- **Excludes:** Parent tasks and DONE tasks
- **Strategy:** Peak allocation (max_parallelism) not average
- **Code:** scheduler.py lines 248-250

## Key Findings

### 1. CPM is Never Automatic
- Requires explicit `get_optimal_agent_count()` call
- No automatic periodic recalculation
- No caching (each call recalculates)
- Caller responsibility to request analysis

### 2. Subtask Dependencies Created Once
- Intra-parent: During decomposition
- Cross-parent: During first refresh after selection
- Wiring uses hybrid approach (embeddings + LLM + checks)
- Persisted to disk (data/marcus_state/subtasks.json)

### 3. Unified Storage Strategy
- Single project_tasks list for parents + subtasks
- Differentiation via `is_subtask` flag
- CPM filters to subtasks only
- Unified graph enables accurate parallelism analysis

### 4. Migration Safety
- Only migrates subtasks whose parents exist in project
- Prevents cross-project subtask pollution
- Flag-protected against re-runs
- Parent check: lines 689-701 in subtask_manager.py

### 5. Peak Allocation Strategy
- Provisions for PEAK parallelism, not average
- optimal_agents = max_parallelism
- Rationale: Idle agents cheap; bottlenecks not resolvable
- Code: scheduler.py lines 284-291

## Timing Summary

| Operation | Trigger | Location | Runs |
|-----------|---------|----------|------|
| **Subtask Migration** | First refresh after select_project | server.py:839 | ONCE |
| **Cross-Parent Wiring** | After migration succeeds | server.py:847 | ONCE |
| **CPM Calculation** | Explicit get_optimal_agent_count() call | scheduling.py:16 | ON-DEMAND |

## Code Locations Reference

### Critical Files

**CPM System:**
- `src/marcus_mcp/coordinator/scheduler.py` - Algorithm implementation
- `src/marcus_mcp/tools/scheduling.py` - API entry point

**Subtask System:**
- `src/marcus_mcp/coordinator/subtask_manager.py` - Subtask storage & migration
- `src/marcus_mcp/coordinator/dependency_wiring.py` - Cross-parent dependencies

**Integration Points:**
- `src/marcus_mcp/server.py` - refresh_project_state(), main orchestration
- `src/marcus_mcp/tools/project_management.py` - select_project(), switch_project()

## Performance Characteristics

- **CPM Calculation:** O(V + E) where V=subtasks, E=dependencies
- **Embedding Filtering:** O(N * M) where N=subtasks, M=candidates (bounded by threshold)
- **LLM Reasoning:** One call per subtask with requires field (bound by max_candidates=10)
- **Migration:** O(S) where S=subtasks to migrate (one-time cost)
- **Wiring:** O(S * M) for all subtasks (one-time cost)

## Testing

See `tests/` directory for:
- Unit tests: `tests/unit/coordinator/test_scheduler.py`
- Integration tests: `tests/integration/e2e/test_task_decomposition_e2e.py`
- Dependency tests: `tests/unit/coordinator/test_dependency_wiring.py`

Key test cases:
- Sequential task chains
- Fully parallel tasks
- Mixed sequential/parallel
- Subtask filtering
- Cycle detection

## Related Documentation

- [CPM Function Reference](/docs/source/api/cpm-function-reference) - Complete API reference for all CPM and subtask functions
- [Active Project Selection Reference](/docs/source/systems/project-management/active-project-selection-reference) - How project selection integrates with CPM
