# Task execution order not respecting dependencies - Tests assigned before Implementation

## Problem Description

Tasks are being assigned to workers in an incorrect order, violating the logical development flow. For example, "Test" tasks are being assigned before "Implement" tasks, and "Document" tasks are being assigned before features are complete. This breaks the expected development lifecycle.

## Expected Behavior

### Single Feature, Single Worker
For a feature like "Clock Display", tasks should be assigned in this order:
1. Design Clock Display
2. Implement Clock Display
3. Test Clock Display
4. Document Clock Display

### Multiple Features
- Features may have inter-dependencies (Feature A must complete before Feature B)
- Within each feature: Design → Implement → Test → Document
- Documentation should be the FINAL task across ALL features

## Actual Behavior

Tasks are being assigned out of order:
- Design tasks
- Test tasks (nothing to test yet!)
- Document tasks (premature documentation)
- Implementation tasks missing or out of sequence

This causes:
- Workers receiving test tasks for unimplemented features
- Blocked workers who cannot complete assigned tasks
- Documentation being written before features exist

## Technical Analysis

### How Dependencies Should Work

1. **Task Creation** (`src/ai/advanced/prd/advanced_parser.py`):
   - Tasks are created with empty dependencies initially
   - Dependencies need to be inferred

2. **Dependency Inference** (`src/intelligence/dependency_inferer_hybrid.py`):
   - Uses pattern matching + AI to determine dependencies
   - Should identify task types and create appropriate links

3. **Safety Checks** (`src/integrations/nlp_task_utils.py`):
   ```python
   # Expected safety rules:
   - Design → Implementation
   - Implementation → Testing
   - All → Deployment
   ```

4. **Task Assignment** (`request_next_task`, line 861):
   ```python
   available_tasks = [
       t for t in state.project_tasks
       if t.status == TaskStatus.TODO
       and all(dep_id in completed_task_ids for dep_id in (t.dependencies or []))
   ]
   ```

### Root Causes

1. **Incomplete Dependency Inference**:
   - Pattern matching may not recognize all task types
   - Keywords like "test", "implement", "design" might be missing or ambiguous
   - AI inference might produce incorrect relationships

2. **Missing Safety Check Coverage**:
   - Safety checks rely on keyword matching
   - Non-standard task names might bypass checks
   - Feature-level dependencies not captured

3. **Documentation Task Handling**:
   - No explicit rule making documentation depend on ALL other tasks
   - Documentation tasks might only depend on their feature's tasks

## Steps to Reproduce

1. Create a project with a single feature (e.g., "Clock app that shows current time")
2. Observe the generated tasks and their order
3. Have a single worker request tasks repeatedly
4. Note that tasks are assigned out of logical order

## Proposed Solution

### 1. Strengthen Task Type Detection

```python
def identify_task_type(task_name: str) -> TaskType:
    """More robust task type identification"""
    name_lower = task_name.lower()

    # Expanded keyword lists
    DESIGN_KEYWORDS = ['design', 'plan', 'architect', 'ui/ux', 'wireframe', 'mockup']
    IMPLEMENT_KEYWORDS = ['implement', 'build', 'create', 'develop', 'code', 'write']
    TEST_KEYWORDS = ['test', 'verify', 'validate', 'qa', 'quality', 'check']
    DOC_KEYWORDS = ['document', 'docs', 'readme', 'guide', 'manual']

    # Check each category
    if any(keyword in name_lower for keyword in DESIGN_KEYWORDS):
        return TaskType.DESIGN
    # ... etc
```

### 2. Enforce Strict Phase Dependencies

```python
def apply_phase_dependencies(tasks: List[Task]) -> List[Task]:
    """Ensure proper phase ordering within features"""

    # Group tasks by feature
    feature_tasks = group_by_feature(tasks)

    for feature, feature_tasks in feature_tasks.items():
        # Identify tasks by phase
        design_tasks = [t for t in feature_tasks if t.type == TaskType.DESIGN]
        impl_tasks = [t for t in feature_tasks if t.type == TaskType.IMPLEMENT]
        test_tasks = [t for t in feature_tasks if t.type == TaskType.TEST]

        # Create dependencies
        for impl_task in impl_tasks:
            impl_task.dependencies.extend([t.id for t in design_tasks])

        for test_task in test_tasks:
            test_task.dependencies.extend([t.id for t in impl_tasks])
```

### 3. Global Documentation Dependencies

```python
def set_documentation_dependencies(tasks: List[Task]) -> List[Task]:
    """Make documentation tasks depend on ALL non-doc tasks"""

    doc_tasks = [t for t in tasks if t.type == TaskType.DOCUMENTATION]
    non_doc_tasks = [t for t in tasks if t.type != TaskType.DOCUMENTATION]

    for doc_task in doc_tasks:
        # Documentation depends on everything else
        doc_task.dependencies = [t.id for t in non_doc_tasks]
```

### 4. Add Dependency Validation

```python
def validate_dependencies(tasks: List[Task]) -> List[str]:
    """Validate dependency graph for logical errors"""
    errors = []

    for task in tasks:
        if task.type == TaskType.TEST:
            # Ensure test has implementation dependency
            has_impl_dep = any(
                dep_task.type == TaskType.IMPLEMENT
                for dep_task in get_dependencies(task)
            )
            if not has_impl_dep:
                errors.append(f"Test task '{task.name}' has no implementation dependency")

    return errors
```

## Testing Strategy

1. **Unit Tests**:
   - Test task type identification with various naming patterns
   - Verify dependency generation for different scenarios
   - Test safety check application

2. **Integration Tests**:
   - Create projects with known structures
   - Verify task assignment order matches expectations
   - Test with multiple workers to ensure consistency

3. **Test Cases**:
   - Single feature, single worker
   - Multiple features with dependencies
   - Edge cases: ambiguous task names, custom phases

## Impact

- **Severity**: High - Breaks fundamental development workflow
- **Users Affected**: All users creating projects with multiple phases
- **Current Workaround**: Manual task management, which defeats the purpose of Marcus

## Related Code Files

- `/Users/lwgray/dev/marcus/src/integrations/nlp_task_utils.py` - Safety checks
- `/Users/lwgray/dev/marcus/src/intelligence/dependency_inferer_hybrid.py` - Dependency inference
- `/Users/lwgray/dev/marcus/src/marcus_mcp/handlers.py` - Task assignment logic
- `/Users/lwgray/dev/marcus/src/ai/advanced/prd/advanced_parser.py` - Task generation

## Additional Notes

The current system has the infrastructure for proper dependency management but needs:
1. More robust task type identification
2. Stricter enforcement of phase dependencies
3. Better handling of global constraints (like documentation being last)
4. Validation to catch dependency errors before task assignment
