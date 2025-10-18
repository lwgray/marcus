# Marcus Task & Subtask Flow Documentation

This documentation provides comprehensive visualizations of how tasks and subtasks are created, decomposed, and assigned to agents in the Marcus system.

## Quick Navigation

| Diagram | Description | Best For |
|---------|-------------|----------|
| [Flowchart](task_flow_flowchart.md) | Decision flow and logic branches | Understanding control flow and decision points |
| [Sequence Diagram](task_flow_sequence.md) | Temporal order of events | Understanding timing and component interactions |
| [Architecture Diagram](task_flow_architecture.md) | Component relationships and data flow | Understanding system structure and file locations |

## Overview

Marcus uses a sophisticated multi-layer architecture to manage task creation, decomposition, and assignment:

### Core Concepts

1. **Unified Task Graph**: Tasks and subtasks stored as same `Task` type in single list
   - Subtasks marked with `is_subtask=True`, `parent_task_id`, `subtask_index`
   - Enables unified dependency analysis

2. **5-Layer Storage**:
   - **Kanban Provider** (Planka/GitHub/Linear) - Source of truth
   - **In-Memory Graph** - Fast access
   - **Assignment Persistence** - Prevent duplicates
   - **Project Registry** - Project configs
   - **Subtask Manager** - Hierarchy metadata

3. **Eager Decomposition**: Subtasks created immediately during project creation (NOT on-demand during assignment)

4. **Subtask Priority**: System checks existing subtasks BEFORE regular tasks during assignment

5. **AI-Powered Assignment**: 4-phase engine (safety → dependencies → skills → impact)

## Key Workflows

### Project Creation (9 Stages)
1. AI PRD Analysis
2. Task Generation (8-15 tasks)
3. Dependency Application
4. Board Creation
5. Task Upload
6. **Task Decomposition** (immediate):
   - Heuristics check (>4hrs, not deployment)
   - AI generates 3-5 subtasks per eligible task
   - Register Task objects in unified graph
   - Cross-wire dependencies (embedding + LLM)
   - Create subtasks on Kanban board
7. Project Registration
8. State Refresh

**Duration**: ~15-20 seconds (task creation ~8s + decomposition ~8s in parallel)

**Note**: Decomposition happens during project creation, NOT during task assignment

### Task Assignment (Prioritized)
1. Check for existing subtasks FIRST (already created during project creation)
2. Filter by dependencies and assignment status
3. AI engine scores candidates
4. Immediate reservation (prevents race conditions)
5. Persist to assignments.json
6. Return to agent with context

**Duration**: ~2-3 seconds (fast because subtasks already exist)

## Component Map

```
src/marcus_mcp/
├── server.py                          # MCP Server + State Sync
├── tools/
│   ├── nlp.py                         # create_project, create_tasks
│   ├── task.py                        # request_next_task, report_*
│   └── agent.py                       # register_agent
└── coordinator/
    ├── decomposer.py                  # Decomposition logic
    ├── subtask_manager.py             # Hierarchy management
    ├── subtask_assignment.py          # Subtask selection
    ├── task_assignment_integration.py # Unified orchestration
    └── dependency_wiring.py           # Cross-parent deps

src/core/
├── models.py                          # Task models
├── project_registry.py                # Project state
├── assignment_persistence.py          # Assignment tracking
└── ai_powered_task_assignment.py      # AI engine
```

## Design Patterns

### Reservation Pattern
```python
# Immediate reservation prevents race conditions
tasks_being_assigned.add(task.id)
persist_assignment(agent_id, task.id)
return task
```

### State Synchronization
```python
# Triggered on: startup, project change, before assignment, after completion
def refresh_project_state():
    tasks = fetch_from_provider()
    wire_dependencies(tasks)
    load_subtask_hierarchy()
    rebuild_agent_mappings()
```

### Subtask Priority
```python
# Always check subtasks first
def find_optimal_task(agent):
    subtask = find_next_available_subtask(agent)
    if subtask:
        return subtask
    return find_regular_task(agent)
```

## Performance Characteristics

| Operation | Duration | Optimizations |
|-----------|----------|---------------|
| Project Creation + Decomposition | ~15-20s | Parallel AI calls for both (10x speedup) |
| Task Assignment | ~2-3s | In-memory graph + existing subtasks + immediate reservation |
| State Sync | ~1-2s | Batch operations, incremental updates |

## Integration Points

### For Agents
- **Entry**: `register_agent()` → `request_next_task()` loop
- **Execution**: `report_task_progress()` at milestones
- **Recovery**: `report_blocker()` for AI suggestions

### For Kanban Providers
- **Create**: Board + task creation APIs
- **Sync**: Bidirectional state synchronization
- **Update**: Status changes, assignments, completions

### For AI Services
- **PRD Analysis**: Requirements extraction
- **Task Generation**: Natural language → structured tasks
- **Skill Matching**: Agent capabilities → task requirements
- **Dependency Scoring**: Priority calculation
- **Impact Prediction**: Cascade effect forecasting

## Detailed Diagrams

### [1. Flowchart](task_flow_flowchart.md)
Shows the complete decision flow from project creation through assignment to completion. Best for understanding:
- What happens at each stage
- Decision points and branching logic
- Loop structures
- State transitions

### [2. Sequence Diagram](task_flow_sequence.md)
Shows the temporal order of interactions between components. Best for understanding:
- When events occur
- Component communication patterns
- Async operations
- Lifecycle phases

### [3. Architecture Diagram](task_flow_architecture.md)
Shows component relationships and data flow paths. Best for understanding:
- System structure
- File locations
- Data flow between layers
- Component dependencies

## Common Questions

**Q: When are subtasks created?**
A: Eagerly, immediately during project creation right after tasks are uploaded to the Kanban board (NOT on-demand during assignment).

**Q: How does Marcus prevent two agents getting the same task?**
A: Immediate reservation pattern - `tasks_being_assigned.add()` happens before returning the task, and assignment is persisted to `assignments.json`.

**Q: What determines task assignment order?**
A: Subtasks prioritized first, then 4-phase AI scoring: safety checks → dependency impact → skill matching → predictive impact.

**Q: How are cross-parent subtask dependencies discovered?**
A: Embedding similarity on semantic contracts (provides/requires) + LLM validation for high-similarity pairs.

**Q: What's the source of truth for task state?**
A: The Kanban provider (Planka/GitHub/Linear). Marcus maintains multiple caches for performance but syncs regularly.

## Related Documentation

- [Error Handling Framework](../error_framework.md)
- [MCP Tool Specifications](../mcp_tools.md)
- [AI Assignment Engine](../ai_assignment.md)
- [Subtask System Design](../subtask_design.md)
