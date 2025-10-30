# Cross-Parent Dependency Wiring - Integration Test

## Overview

This integration test validates that Marcus correctly serves tasks in dependency order, respecting **cross-parent dependencies** created by the hybrid dependency wiring system.

## What is Cross-Parent Dependency Wiring?

Cross-parent dependency wiring creates fine-grained dependencies between subtasks of different parent tasks. For example:

```
Parent Task 1: Design User Management
  ├─ Subtask 1.1: Research user data requirements
  ├─ Subtask 1.2: Design user data schema ← provides "User model schema"
  └─ Subtask 1.3: Design API specification

Parent Task 2: Implement User Management
  ├─ Subtask 2.1: Implement User Registration ← requires "User model schema"
  │                  ↓ CROSS-PARENT DEPENDENCY created!
  │                  └─ Depends on Subtask 1.2 (different parent)
  └─ Subtask 2.2: Implement User Login
```

Without cross-parent dependencies, Marcus would allow Subtask 2.1 to start before Subtask 1.2 completes, leading to poor agent utilization and blocked work.

## Test Files

- **test_dependency_wiring_order.py** - Main integration test
- **README_DEPENDENCY_WIRING.md** - This documentation

## Test Scenarios

The test includes three scenarios:

### 1. Single-Agent Sequential Execution
- One agent requests tasks sequentially
- Validates tasks are served in correct dependency order
- Logs all task execution and verifies no dependency violations

### 2. Multi-Agent Parallel Execution
- Three agents request tasks in parallel
- Validates independent tasks can run simultaneously
- Ensures dependencies are still respected across agents

### 3. Cross-Parent Dependency Validation
- Specifically tracks cross-parent dependency scenarios
- Validates Implementation tasks wait for Design tasks from different parents
- Checks that specific provides/requires relationships are enforced

## Usage

### Demo Mode (stdio)

Spawns isolated Marcus instances - no real tasks, but demonstrates the framework:

```bash
python tests/integration/test_dependency_wiring_order.py
```

**Output:**
```
✅ ALL TESTS PASSED!

⚠️  NOTE: Tests passed but no tasks were executed (demo mode)
   For real testing with E-Commerce project, run:
   python tests/integration/test_dependency_wiring_order.py --http
```

### Real Testing Mode (HTTP)

Connects to a running Marcus server with actual project data:

```bash
# 1. Start Marcus server
./marcus start

# 2. Ensure E-Commerce Cart System project is loaded
# (should happen automatically on startup)

# 3. Run the test
python tests/integration/test_dependency_wiring_order.py --http
```

**Expected Output:**
```
✅ ALL TESTS PASSED!

Cross-parent dependency wiring is working correctly!
Tasks are being served in the correct dependency order.
```

## Test Output Explained

The test logs detailed execution information:

```
TEST 1: Single-Agent Sequential Execution
======================================================================

🤖 Registering test agent...

📋 Starting task execution loop...

  ▶️  [test-agent-1] Started: Research user account data requirements (1621553828643997204_sub_1)
  ✅ [test-agent-1] Completed: Research user account data requirements (1621553828643997204_sub_1)
     Dependencies: []

  ▶️  [test-agent-1] Started: Design user account data schema (1621553828643997204_sub_2)
  ✅ [test-agent-1] Completed: Design user account data schema (1621553828643997204_sub_2)
     Dependencies: [1621553828643997204_sub_1]

  ▶️  [test-agent-1] Started: Implement User Registration (1621553830246221340_sub_1)
  ✅ [test-agent-1] Completed: Implement User Registration (1621553830246221340_sub_1)
     Dependencies: [1621553828643997204_sub_2]  ← CROSS-PARENT DEP!

======================================================================
EXECUTION SUMMARY
======================================================================
Total tasks completed: 20
Dependency violations: 0

✅ All tasks executed in correct dependency order!
```

## Validation Logic

The test validates several invariants:

1. **Dependency Satisfaction**: No task can complete if its dependencies haven't completed
2. **Cross-Parent Enforcement**: Implementation subtasks wait for Design subtasks from different parents
3. **Parallel Execution**: Independent tasks can run simultaneously across agents
4. **No Deadlocks**: The dependency graph is acyclic (no circular dependencies)

## Expected Task Ordering

Based on the E-Commerce Cart System project:

### Phase 1: Design (Parallel - No Dependencies)
- Design User Management (all 5 subtasks)
- Design Product Catalog (all 5 subtasks)
- Design Shopping Cart (all 5 subtasks)

**Expected:** All Design subtasks can start immediately and run in parallel.

### Phase 2: Implementation (After Design)
- Implement User Management subtasks
  - `Implement User Registration` **must wait for** `Design user account data schema`
  - `Implement User Login` **must wait for** `Design user account data schema`
- Implement Product Catalog subtasks
- Implement Shopping Cart subtasks
- Implement Performance

**Expected:** Implementation starts only after required Design subtasks complete.

### Phase 3: Testing (After Implementation)
- Test User Management
- Test Product Catalog
- Test Shopping Cart

**Expected:** Tests start only after Implementation completes.

### Phase 4: Security & Documentation
- Implement Security
- Create README documentation

**Expected:** Final tasks run after all dependencies complete.

## Troubleshooting

### Test shows "No tasks available"

**Problem:** The test isn't finding any tasks to execute.

**Solution:**
- Make sure you're using `--http` mode
- Verify Marcus server is running: `./marcus status`
- Check that the E-Commerce Cart System project is loaded
- Confirm tasks haven't already been completed

### Dependency violations reported

**Problem:** Tasks are being served before their dependencies complete.

**Example violation:**
```
❌ VIOLATION: Implement User Registration (1621553830246221340_sub_1)
   completed with unsatisfied dependencies: [1621553828643997204_sub_2]
```

**This indicates a bug in:**
- Dependency wiring (incorrect dependencies created)
- Task scheduler (not respecting dependencies)
- Assignment system (assigning blocked tasks)

### Test times out

**Problem:** Test hangs or takes very long (especially in stdio mode).

**Solution:**
- Use `--http` mode instead of stdio
- stdio mode spawns 3+ isolated Marcus instances which is slow
- HTTP mode connects to one shared server

## Implementation Details

### TaskExecutionLogger Class

Tracks task execution and validates dependency ordering:

```python
class TaskExecutionLogger:
    def log_task_start(self, agent_id, task_id, task_name)
    def log_task_complete(self, agent_id, task_id, task_name, dependencies)
    def get_summary(self) -> Dict[str, Any]
    def print_summary(self)
```

### simulate_agent_work_loop Function

Simulates an agent's work cycle:

```python
async def simulate_agent_work_loop(client, agent_id, logger, max_tasks):
    1. Request next task from Marcus
    2. If task assigned:
       a. Log task start
       b. Immediately mark as complete (simulate instant work)
       c. Log task completion with dependencies
    3. Repeat until no tasks available or max_tasks reached
```

## Cross-Parent Dependencies Tested

The test specifically validates these cross-parent relationships:

| Implementation Subtask | Requires | Design Subtask (Different Parent) |
|------------------------|----------|-----------------------------------|
| Implement User Registration | "User model schema from design phase" | Design user account data schema |
| Implement User Login | "User model schema from design phase" | Design user account data schema |
| Implement Product API | "Product data schema" | Design product data model |

## Success Criteria

The test passes if:

✅ All tasks complete in dependency order
✅ Zero dependency violations detected
✅ Cross-parent dependencies are enforced
✅ Multiple agents can work in parallel on independent tasks

## Related Documentation

- `/src/marcus_mcp/coordinator/dependency_wiring.py` - Implementation
- `/tests/unit/coordinator/test_dependency_wiring.py` - Unit tests
- `/tests/unit/coordinator/test_dependency_wiring_smoke.py` - Smoke tests

## Contributing

To add new test scenarios:

1. Add a new async test function following the pattern
2. Accept `connection_type` parameter
3. Use `TaskExecutionLogger` to track execution
4. Call from `main()` function
5. Document expected behavior in docstring

Example:

```python
async def test_new_scenario(connection_type: str = "stdio") -> None:
    """Test a new scenario."""
    logger = TaskExecutionLogger()
    client = Inspector(connection_type=connection_type)

    connect_kwargs = {}
    if connection_type == "http":
        connect_kwargs["url"] = "http://localhost:4298/mcp"

    async with client.connect(**connect_kwargs) as session:
        # Your test logic here
        pass
```
