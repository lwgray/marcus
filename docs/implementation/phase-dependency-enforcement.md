# Phase Dependency Enforcement Implementation

## Overview

The Phase Dependency Enforcement system ensures that tasks follow the correct development lifecycle order within Marcus. This implementation enforces the sequence: **Design → Infrastructure → Implementation → Testing → Documentation → Deployment**.

## Implementation Details

### Core Component: PhaseDependencyEnforcer

**Location**: `/src/core/phase_dependency_enforcer.py`

The `PhaseDependencyEnforcer` class is the main component that:
1. Groups tasks by feature/component
2. Classifies tasks into development phases
3. Enforces phase-based dependencies
4. Validates dependency correctness

### Key Classes and Enums

```python
class TaskPhase(Enum):
    """Development lifecycle phases in execution order"""
    DESIGN = 1
    INFRASTRUCTURE = 2
    IMPLEMENTATION = 3
    TESTING = 4
    DOCUMENTATION = 5
    DEPLOYMENT = 6

class DependencyType(Enum):
    """Types of task dependencies"""
    PHASE = "phase"        # Based on development lifecycle
    FEATURE = "feature"    # Same feature/component
    TECHNICAL = "technical"# Technical requirement
    MANUAL = "manual"      # User-specified
```

### Integration Points

#### 1. Task Creation Flow

The phase dependency enforcement is integrated into the task creation pipeline at `/src/integrations/nlp_base.py`:

```python
async def apply_safety_checks(self, tasks: List[Task]) -> List[Task]:
    # Import phase dependency enforcer
    from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer

    # First apply phase-based dependencies
    phase_enforcer = PhaseDependencyEnforcer()
    tasks = phase_enforcer.enforce_phase_dependencies(tasks)

    # Then apply legacy safety checks
    # ... existing safety checks ...
```

This ensures all tasks created through natural language processing follow proper phase ordering.

#### 2. Task Assignment

The phase dependencies work seamlessly with the existing task assignment logic in `/src/marcus_mcp/tools/task.py`. Tasks are only assignable when all their dependencies are completed:

```python
available_tasks = [
    t for t in state.project_tasks
    if t.status == TaskStatus.TODO
    and all(dep_id in completed_task_ids for dep_id in (t.dependencies or []))
]
```

### Feature Grouping Algorithm

Tasks are grouped by feature using a multi-strategy approach:

1. **Explicit Labels**: Check for `feature:` prefixed labels
2. **Component Labels**: Match against known components (auth, payment, etc.)
3. **Name Pattern Extraction**: Extract features from task names using regex
4. **Keyword Clustering**: Group by shared meaningful keywords

Example feature identification:
- "Design authentication flow" → Feature: `auth`
- "Implement payment processing" → Feature: `payment`
- "Test user dashboard" → Feature: `dashboard`

### Phase Classification

Tasks are classified into phases based on:

1. **Task Type** (from TaskClassifier)
2. **Keyword Matching** with expanded vocabulary
3. **Context Analysis** from description and labels

The mapping is:
- `TaskType.DESIGN` → `TaskPhase.DESIGN`
- `TaskType.INFRASTRUCTURE` → `TaskPhase.INFRASTRUCTURE`
- `TaskType.IMPLEMENTATION` → `TaskPhase.IMPLEMENTATION`
- `TaskType.TESTING` → `TaskPhase.TESTING`
- `TaskType.DOCUMENTATION` → `TaskPhase.DOCUMENTATION`
- `TaskType.DEPLOYMENT` → `TaskPhase.DEPLOYMENT`

### Dependency Rules

#### Within Features
- Tasks in phase N depend on ALL tasks in phases < N
- Example: All testing tasks depend on all implementation tasks in the same feature

#### Cross-Feature
- Features are isolated by default
- Manual dependencies are preserved
- Global documentation tasks may depend on all features

### Usage Example

```python
from src.core.phase_dependency_enforcer import PhaseDependencyEnforcer
from src.core.models import Task

# Create tasks
tasks = [
    Task(id='1', name='Design auth system', labels=['auth']),
    Task(id='2', name='Implement login API', labels=['auth']),
    Task(id='3', name='Test authentication', labels=['auth']),
    Task(id='4', name='Document auth API', labels=['auth']),
]

# Apply phase dependencies
enforcer = PhaseDependencyEnforcer()
tasks_with_deps = enforcer.enforce_phase_dependencies(tasks)

# Result:
# - Design task: no dependencies
# - Implementation: depends on design
# - Testing: depends on design and implementation
# - Documentation: depends on all previous tasks
```

### Validation

The system includes validation to ensure:
1. No circular dependencies
2. Phase ordering is respected
3. All dependencies reference existing tasks

```python
# Validate dependencies
is_valid, errors = enforcer.validate_phase_ordering(tasks)
if not is_valid:
    for error in errors:
        print(f"Validation error: {error}")
```

### Performance Considerations

1. **Feature Grouping**: O(n) where n is number of tasks
2. **Dependency Assignment**: O(n²) worst case within features
3. **Validation**: O(n + e) where e is number of edges

For typical projects (< 1000 tasks), performance impact is negligible (< 100ms).

### Configuration

Currently, the phase order is fixed, but the system is designed to support configurable phase ordering in future versions:

```python
# Potential future configuration
CUSTOM_PHASE_ORDER = [
    TaskPhase.DESIGN,
    TaskPhase.IMPLEMENTATION,  # Skip infrastructure
    TaskPhase.TESTING,
    TaskPhase.DEPLOYMENT,      # Skip documentation
]
```

### Error Handling

The enforcer handles several edge cases:
- Empty projects
- Single task projects
- All tasks in same phase
- Missing or invalid labels
- Circular dependency prevention

### Testing

#### Unit Tests
Location: `/tests/unit/core/test_phase_dependency_enforcer.py`
- Phase ordering logic
- Feature grouping accuracy
- Dependency preservation
- Edge case handling

#### Integration Tests
Location: `/tests/integration/e2e/test_phase_dependency_e2e.py`
- End-to-end task creation and assignment
- Multi-feature projects
- Complex dependency scenarios
- Worker simulation

### Monitoring and Debugging

The enforcer provides detailed logging:

```python
import logging
logging.getLogger('src.core.phase_dependency_enforcer').setLevel(logging.DEBUG)
```

Statistics can be retrieved:

```python
stats = enforcer.get_phase_statistics(tasks)
print(f"Features identified: {stats['features_identified']}")
print(f"Dependencies added: {stats['dependency_count']}")
print(f"Phase distribution: {stats['phase_distribution']}")
```

### Future Enhancements

1. **Configurable Phase Order**: Allow projects to define custom phase sequences
2. **Phase Skipping**: Support skipping phases (e.g., no design needed)
3. **Parallel Phases**: Allow certain phases to run in parallel
4. **Phase Templates**: Pre-defined phase patterns for common project types
5. **Machine Learning**: Learn optimal phase ordering from historical data

### Troubleshooting

#### Tasks Assigned Out of Order
1. Check task labels are correctly set
2. Verify feature grouping with `enforcer._group_tasks_by_feature(tasks)`
3. Enable debug logging to see dependency assignments

#### Missing Dependencies
1. Ensure task names follow conventions
2. Check TaskClassifier is identifying types correctly
3. Verify phase mapping in `TYPE_TO_PHASE_MAP`

#### Performance Issues
1. For large projects (>1000 tasks), consider batching
2. Cache feature groups if tasks are static
3. Use task IDs instead of full objects where possible

## Conclusion

The Phase Dependency Enforcement system successfully ensures tasks follow the correct development lifecycle order. By integrating seamlessly with existing Marcus components and providing robust feature detection and phase classification, it prevents common issues like testing non-existent code or documenting incomplete features.
