# CRITICAL CORRECTION: Subtask Decomposition Timing

## The Question
**When does subtask decomposition happen - before or after `request_next_task` call?**

## The Answer
**BEFORE** - Subtask decomposition happens during **project creation**, NOT during task assignment.

## Code Evidence

### Where Decomposition Happens
**File**: `src/integrations/nlp_base.py:216`
```python
async def create_tasks_on_board(...):
    # ... create tasks ...
    created_tasks = []
    for task in tasks:
        kanban_task = await self.kanban_client.create_task(task_data)
        created_tasks.append(kanban_task)

    # Decompose tasks that meet criteria and add as checklist items
    await self._decompose_and_add_subtasks(created_tasks, tasks, project_tasks)  # <-- HERE
```

### What Happens During Decomposition
**File**: `src/integrations/nlp_base.py:223-319`
```python
async def _decompose_and_add_subtasks(...):
    # Check if task should be decomposed
    if not should_decompose(original_task):  # >4hrs AND not deployment
        continue

    # Add decomposition job to parallel execution list
    decomposition_jobs.append(
        decompose_task(task_with_real_id, self.ai_engine, project_context=None)
    )

    # Execute all decompositions in parallel
    decomposition_results = await asyncio.gather(*decomposition_jobs)

    # Register subtasks with SubtaskManager
    self.subtask_manager.add_subtasks(
        parent_task_id=created_task.id,
        subtasks=subtasks,
        metadata=metadata,
        project_tasks=unified_storage
    )
```

### What Happens During Assignment
**File**: `src/marcus_mcp/tools/task.py:282-378`
```python
async def request_next_task(agent_id: str, state: Any):
    # ... setup ...

    # Find optimal task for this agent
    optimal_task = await find_optimal_task_for_agent(agent_id, state)  # <-- NO DECOMPOSITION
```

**File**: `src/marcus_mcp/coordinator/task_assignment_integration.py:68`
```python
async def find_optimal_task_with_subtasks(...):
    # Try to find available subtask (searches existing subtasks)
    subtask_task = find_next_available_subtask(...)  # <-- SEARCH ONLY

    if subtask_task:
        return subtask_task

    # No subtasks available, use fallback
    return await fallback_task_finder(agent_id, state)
```

**File**: `src/marcus_mcp/coordinator/subtask_assignment.py:84`
```python
def find_next_available_subtask(...):
    """Find the next available subtask for an agent using unified graph."""
    # Filter to only subtasks (Task objects with is_subtask=True)
    subtasks = [t for t in project_tasks if t.is_subtask]  # <-- SEARCH EXISTING
    # ... filter and return ...
```

## Verification
- ✅ `grep "decompose" src/marcus_mcp/tools/task.py` returns **NO matches**
- ✅ Decomposition only called from `nlp_base.py` during `create_tasks_on_board()`
- ✅ Assignment logic only searches for existing subtasks

## Correct Flow

### 1. Project Creation (Seconds 0-20)
```
create_project()
  ↓
NLP Pipeline
  ↓
Create tasks on Kanban board
  ↓
DECOMPOSITION HAPPENS HERE  <-- EAGER
  ↓
Register project
  ↓
State refresh
```

### 2. Task Assignment (Ongoing)
```
request_next_task()
  ↓
Search for existing subtasks  <-- NO DECOMPOSITION
  ↓
If found: Return subtask
If not: Return regular task
```

## Why This Matters

### Performance Implications
- **Project creation**: Takes 15-20 seconds (task creation + decomposition in parallel)
- **Task assignment**: Fast at 2-3 seconds (no AI calls for decomposition)
- **Agent waiting time**: Minimal - subtasks already exist

### Architecture Implications
- **Eager strategy**: All subtasks created upfront
- **Parallel execution**: All eligible tasks decomposed concurrently
- **Predictable state**: Assignment logic only searches, never creates

### Design Trade-offs
**Advantages**:
- Fast task assignment (no waiting for decomposition)
- Predictable project structure (all subtasks visible upfront)
- Better dependency analysis (complete graph available immediately)

**Disadvantages**:
- Longer initial project creation time
- Subtasks created even if project is abandoned early
- More upfront AI API calls

## Impact on Documentation

### Previously Incorrect Statement
> "Subtask decomposition happens on-demand during first assignment attempt (lazy decomposition)"

### Corrected Statement
> "Subtask decomposition happens immediately during project creation, right after tasks are uploaded to the Kanban board (eager decomposition)"

## Updated Documentation Files
All documentation has been corrected:
1. ✅ `task_flow_flowchart.md` - Moved decomposition to project creation phase
2. ✅ `task_flow_sequence.md` - Added decomposition phase after task upload
3. ✅ `task_flow_architecture.md` - Clarified decomposition timing with notes
4. ✅ `task_flow_overview.md` - Updated performance characteristics and FAQs

## Key Takeaway
**Decomposition is an EAGER, UPFRONT process that happens during project creation, NOT a LAZY, ON-DEMAND process during task assignment.**
