# Project Stall Analyzer

Comprehensive diagnostics tool for analyzing why Marcus project development stalls.

## Problem It Solves

You mentioned experiencing these issues:
- **Development stalls** with Marcus reporting "no more available tasks" when tasks exist
- **Dependency locks** blocking progress
- **Early task completion** - "Project Success" task completing prematurely
- Need to **replay conversations** to understand what led to the stall

## What It Does

The Project Stall Analyzer captures a complete snapshot when development stalls:

1. **Project State Snapshot** - Complete diagnostic report with all tasks, statuses, and dependencies
2. **Conversation Replay** - Last 24-48 hours of conversation history analyzed for patterns
3. **Dependency Lock Visualization** - ASCII art showing which tasks block which
4. **Task Completion Timeline** - Detects tasks completed out of order (like "Project Success" finishing at 40%)
5. **Pattern Detection** - Identifies repeated failures, "no task available" loops, activity gaps

## Usage

### When Development Stalls

Run this immediately when you notice development has stopped:

```bash
python scripts/analyze_stall.py capture
```

**Output:**
```
🔍 Capturing project stall snapshot...

✅ Snapshot captured successfully!
📁 Saved to: logs/stall_snapshots/stall_snapshot_20251006_223045.json

📊 Summary:
   Stall Reason: all_tasks_blocked: All 5 TODO tasks blocked by dependencies
   Total Issues: 3
   Dependency Locks: 5
   Early Completions: 1
   Conversation Events: 47

💡 Recommendations: 7

🔒 Dependency Locks Detected:
Dependency Lock Visualization:
======================================================================

🔒 BLOCKED: Documentation (Status: todo)
   Waiting for:
   ❌ Add Tests (todo)
...

⚠️  Early/Anomalous Task Completions:
   • Project Success Task
     Completed at 40% progress
     Issue: Final task completed at 40% progress
```

### Analyzing a Snapshot

After capturing, analyze what happened:

```bash
python scripts/analyze_stall.py replay logs/stall_snapshots/stall_snapshot_20251006_223045.json
```

**Shows:**
- Full diagnostic report
- Conversation timeline
- Key events (errors, blockers, failures)
- Early completions with context
- Actionable recommendations

### List All Snapshots

```bash
python scripts/analyze_stall.py list
```

## What To Look For

### 1. Dependency Locks

Look for circular dependencies:
```
🔒 Task A blocked by Task B
🔒 Task B blocked by Task C
🔒 Task C blocked by Task A  ← CIRCULAR!
```

### 2. Early Completions

Tasks that should be last but completed early:
```
⚠️ "Project Success" completed at 40% progress
⚠️ "Deploy to Production" completed at 60% progress
⚠️ "Final Testing" completed before "Initial Setup"
```

### 3. Conversation Patterns

**Repeated "No Tasks":**
```
Agent requested tasks 15 times but none available
→ All tasks likely blocked
```

**Repeated Failures:**
```
Task 'setup-database' failed 5 times
→ Agent stuck in failure loop
```

**Activity Gaps:**
```
Only 3 events in 6 hours
→ System stalled, no progress
```

## Integration with Existing Tools

The stall analyzer builds on Marcus's existing diagnostic tools:

- **`TaskDiagnosticCollector`** - Already captures task state
- **`DependencyChainAnalyzer`** - Already finds circular dependencies
- **`ConversationLogger`** - Already logs all conversations
- **New:** Ties everything together with timeline analysis

## Snapshot File Format

Snapshots are saved as JSON in `logs/stall_snapshots/`:

```json
{
  "timestamp": "2025-10-06T22:30:45",
  "project_name": "MyProject",
  "stall_reason": "dependency_lock: Task A blocks 5 others",
  "diagnostic_report": { ... },
  "conversation_history": [ ... ],
  "task_completion_timeline": [ ... ],
  "dependency_locks": {
    "total_locks": 5,
    "locks": [ ... ],
    "ascii_visualization": "..."
  },
  "early_completions": [
    {
      "task_name": "Project Success",
      "completion_percentage": 40.0,
      "issue": "Final task completed at 40% progress"
    }
  ],
  "recommendations": [ ... ]
}
```

## API Usage (Programmatic)

You can also use this from code:

```python
from src.marcus_mcp.tools.project_stall_analyzer import capture_project_stall_snapshot

# When stall detected
result = await capture_project_stall_snapshot(
    state=marcus_state,
    include_conversation_hours=48  # Last 48 hours
)

if result['success']:
    print(f"Snapshot: {result['snapshot_file']}")
    print(f"Issues: {result['summary']['total_issues']}")
    print(f"Locks: {result['summary']['dependency_locks']}")

    # Check for early completions
    if result['summary']['early_completions'] > 0:
        print("⚠️ Tasks completed out of order!")
        for ec in result['snapshot']['early_completions']:
            print(f"  {ec['task_name']} at {ec['completion_percentage']}%")
```

## Files Created

- `src/marcus_mcp/tools/project_stall_analyzer.py` - Core analysis engine
- `scripts/analyze_stall.py` - CLI tool
- `tests/unit/tools/test_project_stall_analyzer.py` - Unit tests
- Snapshots saved to: `logs/stall_snapshots/`

## Next Steps

When you encounter a stall:

1. **Capture** - Run `python scripts/analyze_stall.py capture`
2. **Review** - Look at the summary for quick insights
3. **Deep Dive** - Run replay to see full conversation timeline
4. **Fix** - Follow recommendations (break circular dependencies, complete blocking tasks)
5. **Monitor** - Keep snapshots to identify recurring patterns

## Tips

- **Capture Early** - Don't wait until completely stuck
- **Compare Snapshots** - Look for patterns across multiple stalls
- **Focus on Early Completions** - These often indicate task dependency modeling issues
- **Check Circular Dependencies** - Most common cause of "all tasks blocked"
