# Dependency Awareness Workflow

## Overview

The dependency awareness system in Marcus uses sophisticated algorithms to understand task relationships, both explicit and implicit. This enables better task assignment, prevents deadlocks, and optimizes execution order.

## Core Components

### 1. Dependency Inference Engine

The system uses four complementary strategies to infer dependencies:

#### Pattern-Based Inference
- Analyzes task names for common patterns (e.g., "Create X" → "Test X")
- Uses regex patterns to identify relationships
- Example: "Build User API" depends on "Create User Schema"

#### Action-Based Inference
- Examines action verbs in task descriptions
- Maps relationships like:
  - create/build → test
  - design → implement
  - setup → configure

#### Entity-Based Inference
- Tracks entities mentioned across tasks
- Links tasks that operate on the same entities
- Example: Tasks mentioning "user" entity form a dependency chain

#### Tech Stack Inference
- Understands technology relationships
- Example: "backend" tasks must complete before "frontend" tasks

### 2. Circular Dependency Detection

Uses depth-first search (DFS) to detect cycles:

```python
def detect_circular_dependencies(dep_map, tasks):
    visited = set()
    rec_stack = set()
    cycles = []
    
    def dfs(task_id, path):
        if task_id in rec_stack:
            # Found cycle
            cycle_start = path.index(task_id)
            cycles.append(path[cycle_start:])
            return
            
        visited.add(task_id)
        rec_stack.add(task_id)
        
        for dependent in dep_map.get(task_id, []):
            dfs(dependent, path + [dependent])
            
        rec_stack.remove(task_id)
```

### 3. Optimal Task Ordering

Uses topological sort to determine execution order:

```python
def get_optimal_task_order(tasks, dependencies):
    # Build adjacency list
    graph = {task.id: [] for task in tasks}
    in_degree = {task.id: 0 for task in tasks}
    
    # Count incoming edges
    for task_id, deps in dependencies.items():
        for dep in deps:
            in_degree[dep] += 1
    
    # Find tasks with no dependencies
    queue = [t for t in in_degree if in_degree[t] == 0]
    ordered = []
    
    while queue:
        current = queue.pop(0)
        ordered.append(current)
        
        # Remove edges from current
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return ordered
```

## Integration Points

### 1. Context System Integration

The Context system uses dependency information to:
- Include relevant previous implementations
- Pass architectural decisions between dependent tasks
- Warn about breaking changes

### 2. Memory System Integration

Memory uses dependencies to:
- Predict task complexity based on dependency depth
- Identify common failure patterns in dependency chains
- Learn optimal agent assignments for dependent tasks

### 3. Events System Integration

Events are published for:
- Dependency inference completion
- Circular dependency detection
- Task order optimization

## Usage Workflow

### 1. Task Creation Phase
```python
# When tasks are created or imported
tasks = await kanban_client.get_all_tasks()

# Analyze dependencies (both explicit and implicit)
dependencies = context.analyze_dependencies(
    tasks, 
    infer_implicit=True  # Enable inference
)
```

### 2. Assignment Phase
```python
# Get optimal order considering dependencies
ordered_tasks = context.get_optimal_task_order(tasks, dependencies)

# Assign tasks in dependency order
for task_id in ordered_tasks:
    task = find_task_by_id(task_id)
    
    # Check if dependencies are satisfied
    ready = await context.are_dependencies_satisfied(task_id)
    
    if ready:
        # Safe to assign
        await assign_task_to_agent(task)
    else:
        # Queue for later
        await queue_task_for_dependencies(task)
```

### 3. Execution Phase
```python
# When agent requests context
context_data = await context.get_context(
    task_id,
    completed_dependencies  # Include completed deps
)

# Context includes:
# - Previous implementations from dependencies
# - Architectural decisions that affect this task
# - Warnings about potential conflicts
```

### 4. Completion Phase
```python
# When task completes
await context.mark_task_complete(task_id)

# This triggers:
# - Dependency satisfaction checks
# - Queued task activation
# - Event notifications
```

## Configuration

Configure dependency awareness in `config_marcus.json`:

```json
{
  "features": {
    "context": {
      "enabled": true,
      "infer_dependencies": true,
      "inference_strategies": ["pattern", "action", "entity", "tech_stack"],
      "max_inference_depth": 5,
      "circular_detection": true
    }
  }
}
```

## Best Practices

1. **Explicit Dependencies**: Always set explicit dependencies when known
2. **Label Consistency**: Use consistent labels to improve inference
3. **Task Naming**: Use clear action verbs and entity names
4. **Validation**: Regularly check for circular dependencies
5. **Monitoring**: Track dependency-related delays and bottlenecks

## Monitoring and Debugging

### Dependency Visualization
```python
# Get dependency graph
graph = await context.get_dependency_graph()

# Returns:
{
  "nodes": [...],  # Tasks
  "edges": [...],  # Dependencies
  "cycles": [...], # Detected cycles
  "critical_path": [...]  # Longest dependency chain
}
```

### Performance Metrics
- Inference accuracy rate
- Circular dependency frequency
- Average dependency chain length
- Task delay due to dependencies

## Future Enhancements

1. **Machine Learning**: Learn dependency patterns from historical data
2. **Dynamic Adjustment**: Adjust dependencies based on execution results
3. **Parallel Execution**: Identify independent task groups
4. **Risk Analysis**: Predict cascade failures in dependency chains