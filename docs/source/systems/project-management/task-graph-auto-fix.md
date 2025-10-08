# Task Graph Auto-Fix System

## Overview

The Task Graph Auto-Fix system automatically corrects common task dependency issues before tasks are created on the Kanban board. Instead of failing with developer-focused error messages that users can't act on, Marcus automatically fixes problems and continues with valid task graphs.

**Core Principle**: Users should always get working task graphs, even if the AI makes mistakes during task generation.

## Problem Solved

**Before Auto-Fix:**
```
User: "Create a todo app"
Marcus: ValueError: INVALID TASK GRAPH: 1 final tasks have NO dependencies
        but 8 implementation tasks exist!
        FIX: Call enhance_project_with_documentation() AFTER all
        implementation tasks are created.
User: "...what? How do I do that?"
```

**After Auto-Fix:**
```
User: "Create a todo app"
Marcus: ✓ Created 9 tasks
        Auto-fixed 1 issue: Added 8 implementation task dependencies
        to 'PROJECT_SUCCESS' to ensure it runs last
User: "Perfect!"
```

## Architecture

### Component Diagram

```
create_project
    ↓
NaturalLanguageTaskCreator.create_tasks_on_board()
    ↓
TaskGraphValidator.validate_and_fix(tasks)
    ├─→ _fix_orphaned_dependencies()
    ├─→ _fix_circular_dependencies()
    └─→ _fix_final_tasks_missing_dependencies()
    ↓
(fixed_tasks, warnings) → logs warnings → continues with valid tasks
    ↓
KanbanClient.create_task() × N
```

### Data Flow

```
Input: List[Task] (potentially invalid)
   ↓
1. Build task_map: Dict[task_id, Task]
   ↓
2. Fix orphaned dependencies (remove non-existent refs)
   ↓
3. Fix circular dependencies (break cycles)
   ↓
4. Fix final task dependencies (add impl task deps)
   ↓
Output: (List[Task], List[str])
        ↑              ↑
   fixed tasks    user warnings
```

## Issues Fixed

### 1. Orphaned Dependencies

**Problem**: Task depends on non-existent task ID

**Cause**:
- AI generated invalid task ID
- Task was removed but dependencies not updated
- Copy-paste error in task generation

**Fix Strategy**: Remove invalid dependencies

**Example**:
```python
# Before
task = Task(
    id="test_task",
    name="Run tests",
    dependencies=["impl_task", "task_999"]  # task_999 doesn't exist
)

# After auto-fix
task = Task(
    id="test_task",
    name="Run tests",
    dependencies=["impl_task"]  # orphaned dependency removed
)
```

**Warning**: `"Removed 1 invalid dependency from 'Run tests'"`

### 2. Circular Dependencies

**Problem**: Task graph contains cycles (A→B→C→A)

**Cause**:
- AI created incorrect dependency relationships
- Misunderstood task ordering
- Complex project with unclear dependencies

**Fix Strategy**: Break cycle by removing last edge (least disruptive)

**Example**:
```python
# Before (cycle)
task_a.dependencies = ["task_b"]
task_b.dependencies = ["task_c"]
task_c.dependencies = ["task_a"]  # Creates cycle!

# After auto-fix (cycle broken)
task_a.dependencies = ["task_b"]
task_b.dependencies = ["task_c"]
task_c.dependencies = []  # Removed to break cycle
```

**Warning**: `"Broke circular dependency: removed link from 'Task C' to 'Task A'"`

**Algorithm**:
1. Use DFS (Depth-First Search) to detect cycle
2. Identify cycle path: [A, B, C, A]
3. Remove last edge in cycle (C→A)
4. Repeat until no cycles (max 10 iterations)

### 3. Final Tasks Missing Dependencies

**Problem**: PROJECT_SUCCESS or other final tasks have no dependencies

**Cause**:
- DocumentationTaskGenerator called before implementation tasks created
- Task IDs not yet assigned when dependencies were set
- Timing issue in task creation flow

**Fix Strategy**: Add ALL implementation task IDs as dependencies

**Example**:
```python
# Before
impl_tasks = [task1, task2, task3, task4, task5]  # 5 implementation tasks
final_task = Task(
    name="PROJECT_SUCCESS",
    labels=["final", "verification"],
    dependencies=[]  # EMPTY! Can complete immediately
)

# After auto-fix
final_task = Task(
    name="PROJECT_SUCCESS",
    labels=["final", "verification"],
    dependencies=["task1", "task2", "task3", "task4", "task5"]  # Fixed!
)
```

**Warning**: `"Added 5 implementation task dependencies to 'PROJECT_SUCCESS' to ensure it runs last"`

## API Reference

### Primary Method: `validate_and_fix()`

```python
@staticmethod
def validate_and_fix(tasks: List[Task]) -> Tuple[List[Task], List[str]]:
    """
    Validate and automatically fix task graph issues.

    This is the PRIMARY method for task graph validation.
    It fixes problems automatically rather than raising exceptions.

    Parameters
    ----------
    tasks : List[Task]
        Tasks to validate and fix

    Returns
    -------
    Tuple[List[Task], List[str]]
        (fixed_tasks, user_warnings)
        - fixed_tasks: Tasks with issues corrected
        - user_warnings: Human-readable descriptions of what was fixed

    Notes
    -----
    This method NEVER raises exceptions for fixable issues.
    Users always get valid task graphs.
    """
```

**Usage**:
```python
from src.core.task_graph_validator import TaskGraphValidator

# Validate and fix task graph
fixed_tasks, warnings = TaskGraphValidator.validate_and_fix(tasks)

# Log warnings if any
if warnings:
    logger.warning(f"Auto-fixed {len(warnings)} issues")
    for warning in warnings:
        logger.info(f"  • {warning}")

# Use fixed tasks
tasks = fixed_tasks
```

### Legacy Method: `validate_strictly()`

```python
@staticmethod
def validate_strictly(tasks: List[Task]) -> None:
    """
    Validate task graph with strict checking (raises exceptions).

    LEGACY METHOD: Used for tests and debugging only.
    For production use validate_and_fix() instead.

    Raises
    ------
    ValueError
        If graph contains circular dependencies, orphaned dependencies,
        or final tasks with no dependencies
    """
```

**Usage** (tests only):
```python
# Test that validator detects issues
with pytest.raises(ValueError) as exc_info:
    TaskGraphValidator.validate_strictly(invalid_tasks)

assert "circular dependency" in str(exc_info.value)
```

## Integration Points

### 1. nlp_base.py - Task Creation

**File**: `src/integrations/nlp_base.py`
**Method**: `create_tasks_on_board()`
**Lines**: 80-98

```python
# Auto-fix task graph issues BEFORE committing to Kanban
if not skip_validation:
    # Auto-fix task graph issues
    fixed_tasks, user_warnings = TaskGraphValidator.validate_and_fix(tasks)
    tasks = fixed_tasks  # Use the fixed version

    # Log user-friendly warnings
    if user_warnings:
        logger.warning(
            f"Task graph auto-fixed: {len(user_warnings)} issues corrected"
        )
        for warning in user_warnings:
            logger.info(f"  • {warning}")
```

### 2. Create Project Flow

```
User calls create_project()
    ↓
AI generates task descriptions
    ↓
Tasks converted to Task objects
    ↓
TaskGraphValidator.validate_and_fix(tasks) ← AUTO-FIX HAPPENS HERE
    ↓
Fixed tasks pushed to Kanban
    ↓
User sees created project (no errors!)
```

## Logging and Monitoring

### Warning Logs

When issues are fixed, warnings are logged at INFO level:

```
2025-10-07 12:34:56 WARNING Task graph auto-fixed: 2 issues corrected
2025-10-07 12:34:56 INFO   • Removed 1 invalid dependency from 'Test Task'
2025-10-07 12:34:56 INFO   • Added 3 implementation task dependencies to 'PROJECT_SUCCESS' to ensure it runs last
```

### Success Logs

When graph is valid (no fixes needed):

```
2025-10-07 12:34:56 INFO ✓ Task graph validation passed for 9 tasks
```

### Developer Investigation

Warnings provide enough detail to investigate root causes:

```python
# In logs/marcus_YYYYMMDD_HHMMSS.log
[WARNING] Task graph auto-fixed: 1 issues corrected
[INFO]   • Broke circular dependency: removed link from 'Deploy Backend' to 'Setup Database'
```

This tells developers:
- What was fixed (circular dependency)
- Which tasks were affected
- What action was taken (removed specific link)

## Configuration

No configuration needed - auto-fix is always enabled when validation runs.

To disable validation (not recommended):

```python
await creator.create_tasks_on_board(
    tasks,
    skip_validation=True  # Bypasses auto-fix
)
```

## Testing

### Auto-Fix Tests

**File**: `tests/unit/core/test_task_graph_auto_fix.py`

**Coverage**:
- ✓ Orphaned dependency removal
- ✓ Orphaned dependency removal while keeping valid ones
- ✓ Simple circular dependency breaking (A→B→A)
- ✓ Complex circular dependency breaking (A→B→C→A)
- ✓ Final task dependency addition
- ✓ Multiple issues fixed simultaneously
- ✓ Valid graphs produce no warnings
- ✓ Empty task list handling
- ✓ Self-referencing task fixing

**Run tests**:
```bash
pytest tests/unit/core/test_task_graph_auto_fix.py -v
```

### Strict Validation Tests

**File**: `tests/unit/core/test_task_graph_validator.py`

Tests that strict validator correctly detects issues (for debugging).

## Performance

**Complexity**:
- Orphaned deps: O(n × m) where n=tasks, m=avg dependencies
- Circular deps: O(n + e) where n=tasks, e=edges (DFS)
- Final task deps: O(n)
- **Overall**: O(n + e) - linear in graph size

**Typical Performance**:
- 10 tasks: < 1ms
- 100 tasks: < 5ms
- 1000 tasks: < 50ms

## Edge Cases

### 1. All Tasks in One Giant Cycle

```python
# A→B→C→D→E→A (all 5 tasks in cycle)
```

**Handling**: Breaks cycle at arbitrary point, resulting in linear chain

### 2. Multiple Separate Cycles

```python
# Cycle 1: A→B→A
# Cycle 2: C→D→C
```

**Handling**: Fixes up to 10 cycles (configurable in `max_iterations`)

### 3. Task with Only Circular Dependencies

```python
task_a.dependencies = ["task_a"]  # Self-reference only
```

**Handling**: Removes self-reference, task ends up with no dependencies

### 4. Final Task is Also Part of Cycle

```python
impl_task.dependencies = ["final_task"]
final_task.dependencies = ["impl_task"]  # Cycle + missing impl deps
```

**Handling**:
1. First pass: Breaks cycle
2. Second pass: Adds impl task deps
3. Result: Valid final task with proper dependencies

## Troubleshooting

### Issue: Too Many Warnings in Production

**Symptom**: Every `create_project` logs 3-5 auto-fix warnings

**Root Cause**: Task generation AI consistently creating invalid graphs

**Solution**:
1. Check AI prompt in `nlp_tools.py`
2. Add more examples of valid task dependencies
3. Improve task generation validation
4. Consider adjusting complexity estimation

### Issue: Circular Dependency Fix Breaks Project Flow

**Symptom**: After auto-fix, tasks run in wrong order

**Root Cause**: Breaking cycle removed important dependency

**Solution**:
1. Check logs to see which link was removed
2. Improve AI task generation to avoid cycles
3. Consider manual task ordering for critical projects

### Issue: Final Task Still Completes Early

**Symptom**: PROJECT_SUCCESS done at 58% despite auto-fix

**Root Cause**: Final task was given correct deps, but task got stuck IN_PROGRESS

**Solution**: Not an auto-fix issue - see Gridlock Detection System

## Best Practices

### 1. Monitor Warnings in Production

Track frequency and types of auto-fixes:

```python
# Add to monitoring dashboard
auto_fix_count = len(warnings)
if auto_fix_count > 0:
    metrics.increment("task_graph.auto_fix.count", auto_fix_count)
    for warning in warnings:
        if "circular" in warning.lower():
            metrics.increment("task_graph.auto_fix.circular")
        elif "orphaned" in warning.lower():
            metrics.increment("task_graph.auto_fix.orphaned")
        elif "final" in warning.lower():
            metrics.increment("task_graph.auto_fix.final_task")
```

### 2. Improve AI Based on Patterns

If seeing frequent auto-fixes of same type, improve AI:

```python
# If 80% of projects need final task fix:
# → AI isn't generating final task dependencies correctly
# → Update prompt or add validation before task creation
```

### 3. Use Strict Validation in Tests

For integration tests, use strict validation to catch issues:

```python
# In tests, verify AI generates valid graphs
def test_ai_task_generation_is_valid():
    tasks = await ai_engine.generate_tasks("Build a blog")

    # Should NOT need auto-fix
    TaskGraphValidator.validate_strictly(tasks)  # Raises if invalid
```

### 4. Document Persistent Issues

If certain project types always need fixes:

```python
# Known issue: E-commerce projects often have circular deps
# between "Setup Payment" and "Create Orders" tasks.
# Auto-fix handles this, but consider improving prompt.
```

## Metrics

Track these metrics for health monitoring:

| Metric | Description | Healthy Range |
|--------|-------------|---------------|
| `auto_fix_rate` | % of projects needing fixes | < 20% |
| `circular_deps_fixed` | Circular dependency fixes per day | < 5 |
| `orphaned_deps_fixed` | Orphaned dependency fixes per day | < 10 |
| `final_task_fixes` | Final task fixes per day | < 3 |
| `avg_fixes_per_project` | Average fixes per project | < 0.5 |

## Related Systems

- **Gridlock Detection System**: Detects when all tasks blocked by dependencies
- **Task Assignment Lease System**: Manages task ownership with time limits
- **Dependency Validator**: Legacy strict validation (diagnostic only)

## References

- **Implementation**: `src/core/task_graph_validator.py`
- **Integration**: `src/integrations/nlp_base.py`
- **Tests**: `tests/unit/core/test_task_graph_auto_fix.py`
- **Commit**: 483d2a3 - feat(auto-fix): convert TaskGraphValidator
