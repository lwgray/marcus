# Understanding Task "Lockup" vs Circular Dependencies

## The Situation

When you see the diagnostic report showing:
```
Available for assignment: 0
Blocked by dependencies: 4
Issues found: 3

⚠️  ISSUES DETECTED
1. [CRITICAL] All Tasks Blocked
   All 4 TODO tasks are blocked by dependencies
```

**This is usually CORRECT behavior, not a bug!**

## Why Tasks Get Blocked

### Normal Blocking (Good)
```
Design Task (IN PROGRESS)
    ↓
Implementation Task (TODO - BLOCKED)
    ↓
Test Task (TODO - BLOCKED)
```

Tasks wait for their dependencies to complete. This is intentional!

### Circular Dependency (Bad - Caught by Marcus)
```
Task A depends on Task B
Task B depends on Task C
Task C depends on Task A  ← CIRCULAR!
```

Marcus's circular dependency detection **will catch this** and report it.

## What the Diagnostic Shows

### Example from Calculator Project

```
📊 DIAGNOSTIC SUMMARY
----------------------------------------------------------------------
Available for assignment: 0
Blocked by dependencies: 4
Issues found: 3

⚠️  ISSUES DETECTED
----------------------------------------------------------------------
1. [CRITICAL] All Tasks Blocked
   All 4 TODO tasks are blocked by dependencies

2. [MEDIUM] Bottleneck
   Task 'Design Addition Operation' is blocking 4 other tasks
   💡 Prioritize completing 'Design Addition Operation' to unblock 4 tasks

3. [MEDIUM] Bottleneck
   Task 'Design Subtraction Operation' is blocking 4 other tasks
   💡 Prioritize completing 'Design Subtraction Operation' to unblock 4 tasks
```

**What This Means:**
- ✅ Design tasks are IN PROGRESS
- ⏳ Implementation tasks are waiting for design to complete
- ⏳ Test tasks are waiting for implementation to complete
- 🎯 This is working as designed!

## How to Diagnose Issues

### 1. View Diagnostic Report in Logs

```bash
# View the latest diagnostic
marcus logs --tail 50 | grep -A 50 "Diagnostic Report"

# Or view the full log
tail -f /Users/lwgray/dev/marcus/logs/marcus_*.log
```

### 2. Check Task Dependencies (via MCP Tool)

```python
from src.worker.inspector import Inspector

client = Inspector(connection_type="http")
async with client.connect(url="http://localhost:4298/mcp") as session:
    # Check a specific task's dependencies
    result = await session.call_tool(
        "check_task_dependencies",
        arguments={"task_id": "task-123"}
    )
```

**This shows:**
- What this task depends on
- What tasks depend on this task
- Whether dependencies form cycles
- Recommended completion order

### 3. Check Board Health

```python
# Check overall board health
result = await session.call_tool(
    "check_board_health",
    arguments={}
)
```

**This detects:**
- ❌ Circular dependencies (critical)
- ⚠️  Bottlenecks (medium)
- 📊 Skill mismatches
- 🔗 Long dependency chains
- 👥 Agent workload imbalances

## How to Create a Project and View Dependencies

### Quick Example

```bash
# 1. Start Marcus
./marcus start

# 2. Run the visualization example
python examples/visualize_dependencies.py

# 3. Run the complete workflow example
python examples/calculator_project_workflow.py
```

### Using MCP Tools

```python
from src.worker.inspector import Inspector

async def create_and_visualize():
    client = Inspector(connection_type="http")

    async with client.connect(url="http://localhost:4298/mcp") as session:
        # 1. Authenticate
        await session.call_tool("authenticate", arguments={
            "client_id": "my-agent",
            "client_type": "admin",
            "role": "admin"
        })

        # 2. Create project
        result = await session.call_tool("create_project", arguments={
            "description": "Build a calculator with add, subtract, multiply, divide",
            "project_name": "Calculator",
            "options": {"mode": "new_project", "complexity": "prototype"}
        })

        # 3. Check board health
        health = await session.call_tool("check_board_health", arguments={})

        # 4. View diagnostics in logs
        # Logs are at: /Users/lwgray/dev/marcus/logs/marcus_<timestamp>.log
```

## When It's Actually a Problem

### Red Flags 🚩

1. **Circular Dependencies**
   ```
   CRITICAL: Circular dependency detected: Task A → Task B → Task C → Task A
   ```
   **Action:** Break the cycle by removing one dependency link

2. **All Tasks Blocked with No In-Progress Tasks**
   ```
   TODO: 10 tasks
   IN_PROGRESS: 0 tasks
   Blocked: 10 tasks
   ```
   **Action:** There may be a circular dependency or all tasks have unsatisfied dependencies

3. **Tasks Blocked by Non-Existent Dependencies**
   ```
   HIGH: Task 'Implement Feature' references non-existent dependencies: ['task-999']
   ```
   **Action:** Remove invalid dependency references or create the missing tasks

## How Marcus Prevents Circular Dependencies

Marcus has **multiple layers** of protection:

### 1. Project Creation (AI-Powered)
```python
# src/integrations/nlp_tools.py
# AI analyzes task relationships and creates dependency-free graphs
dependency_graph = await ai_analyzer.create_dependency_graph(tasks)
```

### 2. Task Assignment (Runtime Checks)
```python
# src/core/task_diagnostics.py
cycles = self.analyzer.find_circular_dependencies()
if cycles:
    # Report as CRITICAL issue
    # Prevents assignment until resolved
```

### 3. Diagnostic System (Automatic Monitoring)
```python
# Runs automatically when no tasks can be assigned
# Detects and reports:
# - Circular dependencies
# - Bottlenecks
# - Missing dependencies
# - Long chains
```

## Summary

**"Locked Up" Tasks Are Usually Normal!**

✅ **Normal Blocking:**
- Implementation waiting for design ✓
- Tests waiting for implementation ✓
- Sequential phases enforced ✓

❌ **Actual Problems:**
- Circular dependencies (caught by diagnostic)
- Missing dependencies (caught by diagnostic)
- All tasks blocked with none in progress

**Check the diagnostic logs at:**
```
/Users/lwgray/dev/marcus/logs/marcus_<timestamp>.log
```

**Or use MCP tools:**
- `check_task_dependencies` - Check specific task
- `check_board_health` - Check entire board
- Diagnostic runs automatically when `request_next_task` finds no available tasks

**The diagnostic is working correctly!** It's telling you which in-progress tasks are bottlenecks and recommending you complete them to unblock the others.
