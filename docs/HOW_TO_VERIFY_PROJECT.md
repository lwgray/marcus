# How to Verify: "Did We Build What We Said We Would Build?"

This guide shows you exactly how to use Phase 1 to answer this critical question.

## The Simple Answer

**You compare 2 things:**

1. **What you planned to build** (original task list)
2. **What actually got built** (completed tasks from project history)

Phase 1 gives you both pieces of data.

## Step-by-Step: Verify Any Project

### Step 1: Find Your Project ID

```bash
# List all projects with history data
python examples/verify_project_completion.py --list
```

This shows all projects that have been tracked. You'll see output like:
```
📁 Available Projects:
  • abc123
    Name: Task Management API
    Board: task-management-board
```

The project ID is `abc123`.

### Step 2: Run the Verification

```bash
# Verify a specific project
python examples/verify_project_completion.py abc123
```

You'll get a complete report showing:

```
PROJECT COMPLETION VERIFICATION: abc123
================================================================================

📋 STEP 1: Loading Original Specification...
✅ Project: Task Management API
   Original Plan: 25 tasks

🔨 STEP 2: Analyzing Actual Execution...
   Total Tasks Executed: 28
   Completed: 22
   Blocked: 3
   Completion Rate: 78.6%

🔍 STEP 3: Comparing Plan vs Reality...

📊 STEP 4: Completion Report
✨ FIDELITY SCORE: 88.0%
   (22/25 planned tasks completed)

✅ COMPLETED (22):
   • Create User Model
   • Setup Database
   • Implement Authentication
   • Build API Endpoints
   ...

⚠️  BLOCKED (3):
   • OAuth Integration
   • Email Notifications
   • Advanced Search

🔬 STEP 5: Root Cause Analysis
   Task: OAuth Integration
   Blockers: 2
      - Missing OAuth provider credentials
      - Dependency on external API not yet available

📈 STEP 6: Scope Changes
🆕 ADDITIONAL WORK (3 tasks not in original plan):
   • Add Rate Limiting
   • Implement Caching
   • Setup CI/CD

📦 STEP 7: Deliverables Verification
📄 Artifacts Produced:
   Specifications: 5
   Design Docs: 3
   API Docs: 8
   Total: 16

🎯 FINAL VERDICT
================================================================================

👍 GOOD - Most requirements met

Fidelity Score: 88.0%
Completion Rate: 78.6%
Blocked Tasks: 3
Scope Creep: 3 extra tasks
```

## What the Report Tells You

### **Fidelity Score** (Most Important!)
- **90-100%**: ✅ Excellent - Delivered as promised
- **75-89%**: 👍 Good - Most requirements met
- **50-74%**: ⚠️ Partial - Significant gaps
- **<50%**: ❌ Incomplete - Major issues

This directly answers: "Did we build what we said we would?"

### **Completion Rate**
How many tasks finished (completed vs total executed)

### **Blocked Tasks**
What got stuck and why

### **Scope Creep**
Extra work that wasn't in the original plan

### **Deliverables**
What artifacts (docs, specs, APIs) were produced

## Manual Verification (Python)

If you want more control, use the Python API directly:

```python
from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery
import asyncio

async def check_project():
    # Initialize
    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    project_id = "abc123"

    # Get the original plan
    history = await query.get_project_history(project_id)
    original_tasks = history.snapshot.tasks  # What you SAID you'd build

    # Get what actually happened
    completed = await query.find_tasks_by_status(project_id, "completed")
    blocked = await query.find_blocked_tasks(project_id)

    # Compare
    completed_names = {task.name for task in completed}
    original_names = {task['name'] for task in original_tasks}

    # Calculate fidelity
    matched = len(completed_names & original_names)
    fidelity = matched / len(original_tasks) * 100

    print(f"Fidelity Score: {fidelity:.1f}%")
    print(f"Completed {matched} of {len(original_tasks)} planned tasks")

    # Check what's missing
    missing = original_names - completed_names
    if missing:
        print(f"\nMissing tasks:")
        for task_name in missing:
            print(f"  - {task_name}")

    # Check why tasks failed
    if blocked:
        print(f"\nBlocked tasks:")
        for task in blocked:
            print(f"  - {task.name}")
            for blocker in task.blockers_reported:
                print(f"    Reason: {blocker.get('description')}")

asyncio.run(check_project())
```

## Using MCP Tools (For AI Agents/Claude Code)

```python
# Get project summary
result = await mcp__marcus__query_project_history(
    project_id="abc123",
    query_type="summary"
)

print(f"Completion Rate: {result['data']['completion_rate']}%")
print(f"Tasks: {result['data']['completed_tasks']}/{result['data']['total_tasks']}")

# Find what got blocked
blocked_result = await mcp__marcus__query_project_history(
    project_id="abc123",
    query_type="blocked_tasks"
)

print(f"Blocked: {blocked_result['count']} tasks")
for task in blocked_result['data']:
    print(f"  - {task['name']}")
```

## Real-World Example

Let's say you were building a "Task Management API" and promised:

**Original Spec (25 tasks):**
1. User authentication
2. Create/Read/Update/Delete tasks
3. Task assignment
4. Due dates and reminders
5. Email notifications
... (20 more)

**After Running Verification:**

```bash
python examples/verify_project_completion.py task-mgmt-api-123
```

**Results:**
- ✅ 22/25 tasks completed (88% fidelity)
- ⚠️ 3 tasks blocked:
  - Email notifications (missing SMTP credentials)
  - Advanced search (dependency on Elasticsearch)
  - OAuth integration (external API not ready)
- 🆕 3 extra tasks added:
  - Rate limiting (security requirement)
  - Caching (performance improvement)
  - CI/CD pipeline (DevOps request)

**Verdict:** 👍 **GOOD** - Delivered 88% of promised features. The 3 blocked tasks have clear external dependencies that weren't anticipated. Added valuable features (rate limiting, caching) that improve the product.

## When to Run This

1. **End of Sprint** - Did we deliver what we committed to?
2. **Project Completion** - Final verification before handoff
3. **Debugging Stalls** - Why isn't the project progressing?
4. **Retrospectives** - What went well vs poorly?
5. **Client Updates** - Show tangible progress

## What If My Project Doesn't Have a Snapshot?

The snapshot is created when you use `create_project` or when Marcus saves project state. If you don't have one:

**Option 1:** Create a snapshot manually by listing what you intended to build

**Option 2:** Use just the query API to analyze what DID get built:

```python
# Just see what was actually built
summary = await query.get_project_summary("abc123")
completed = await query.find_tasks_by_status("abc123", "completed")
blocked = await query.find_blocked_tasks("abc123")

print(f"Delivered: {len(completed)} tasks")
print(f"Blocked: {len(blocked)} tasks")
```

## Next Steps

Once you know what didn't get built:

1. **Check blockers** - See why tasks failed
2. **Find decisions** - What choices were made?
3. **Review conversations** - What did agents discuss?
4. **Analyze artifacts** - What documentation exists?

All of these are available through Phase 1 queries!

## Summary

**The Core Question:** Did we build what we said we would build?

**The Answer:** Compare `original_tasks` (snapshot) vs `completed_tasks` (history)

**The Tool:** `python examples/verify_project_completion.py <project_id>`

**The Metric:** Fidelity Score = (completed planned tasks / total planned tasks) × 100%

That's it! Phase 1 gives you data-driven answers instead of guessing.
