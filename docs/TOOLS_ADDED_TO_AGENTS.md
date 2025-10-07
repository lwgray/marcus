# Diagnostic Tools Now Available to Agents

## Summary

The project stall analyzer tools have been registered with Marcus MCP server and are now available to:
- **Agents** (autonomous workers)
- **Humans** (you, via Claude Code)
- **Analytics** (Seneca and other analytics tools)

## Tools Added

### 1. `diagnose_project`

**Available to:** agents, humans, analytics
**Purpose:** Quick diagnostic of current project state

**Usage:**
```python
# Agent can call this when stuck
result = await diagnose_project()

# Shows:
# - Circular dependencies
# - Bottleneck tasks
# - Missing dependencies
# - Long dependency chains
```

**When agents should use it:**
- After 3+ failed `request_next_task` calls returning no tasks
- When reporting a blocker related to dependencies
- Before escalating to human for help

---

### 2. `capture_stall_snapshot`

**Available to:** agents, humans
**Purpose:** Comprehensive snapshot when development stalls

**Usage:**
```python
# Capture detailed snapshot
result = await capture_stall_snapshot(include_conversation_hours=48)

# Returns:
{
    "success": True,
    "snapshot_file": "logs/stall_snapshots/stall_snapshot_20251006_223045.json",
    "summary": {
        "stall_reason": "all_tasks_blocked: ...",
        "total_issues": 3,
        "dependency_locks": 5,
        "early_completions": 1,
        "conversation_events": 47
    },
    "snapshot": { ... full data ... }
}
```

**What it captures:**
- Full diagnostic report
- Last 24-48 hours of conversation
- Task completion timeline
- Dependency lock visualization
- Anomalous completions (tasks done out of order)
- Pattern detection (repeated failures)
- Actionable recommendations

**When agents should use it:**
- Development completely stalled (no progress for >1 hour)
- Circular dependency suspected
- Multiple tasks failing repeatedly
- Before requesting human intervention

---

### 3. `replay_snapshot_conversations`

**Available to:** humans, analytics
**Purpose:** Analyze what led to a stall

**Usage:**
```python
# Replay from saved snapshot
result = await replay_snapshot_conversations(
    snapshot_file="logs/stall_snapshots/stall_snapshot_20251006_223045.json"
)

# Returns conversation analysis with:
# - Event timeline
# - Key events (errors, blockers)
# - Pattern detection
# - Recommendations
```

**Use cases:**
- Post-mortem analysis
- Identifying recurring issues
- Training agents to avoid similar stalls

---

## Tool Access by Endpoint

### Agent Endpoint
Agents can call:
- `diagnose_project` ✅
- `capture_stall_snapshot` ✅

**Not available to agents:**
- `replay_snapshot_conversations` (analysis tool for humans)

### Human Endpoint
You can call:
- `diagnose_project` ✅
- `capture_stall_snapshot` ✅
- `replay_snapshot_conversations` ✅

### Analytics Endpoint
Analytics tools can call:
- `diagnose_project` ✅
- `capture_stall_snapshot` ✅
- `replay_snapshot_conversations` ✅

---

## Recommended Agent Workflow

When an agent encounters "no tasks available":

```python
# Step 1: Try again (might be temporary)
task = await request_next_task(agent_id)

# Step 2: If still no tasks after 3 tries, diagnose
if no_task_count >= 3:
    diag = await diagnose_project()

    # Check diagnostic results
    if diag["summary"]["total_issues"] > 0:
        # Log the issue
        await log_decision(
            agent_id=agent_id,
            task_id="system",
            decision=f"Found {diag['summary']['total_issues']} project issues"
        )

        # If critical issues, capture snapshot
        if has_critical_issues(diag):
            snapshot = await capture_stall_snapshot(
                include_conversation_hours=24
            )

            # Report blocker with snapshot reference
            await report_blocker(
                agent_id=agent_id,
                task_id="project",
                blocker_description=f"Project stalled. Snapshot: {snapshot['snapshot_file']}",
                severity="high"
            )
```

---

## Files Modified

1. **`src/marcus_mcp/tool_groups.py`**
   - Added `diagnose_project` to agent, human, analytics groups
   - Added `capture_stall_snapshot` to agent, human, analytics groups
   - Added `replay_snapshot_conversations` to human, analytics groups

2. **`src/marcus_mcp/server.py`**
   - Registered `diagnose_project` tool (lines 1278-1298)
   - Registered `capture_stall_snapshot` tool (lines 1300-1339)
   - Registered `replay_snapshot_conversations` tool (lines 1341-1366)

3. **`src/marcus_mcp/tools/diagnostics.py`**
   - Added `capture_stall_snapshot()` function
   - Added `replay_snapshot_conversations()` function
   - Already had `diagnose_project()` function

---

## Testing

All tools tested and verified:
- ✅ Tool registration compiles without errors
- ✅ Unit tests pass (8/8 tests)
- ✅ Tools added to correct endpoint groups
- ✅ MCP server compiles successfully

---

## Next Steps for Agents

Autonomous agents can now:

1. **Self-diagnose** when stuck using `diagnose_project`
2. **Capture evidence** of stalls using `capture_stall_snapshot`
3. **Report issues** with concrete diagnostic data
4. **Avoid escalating** simple dependency issues to humans

This gives agents the ability to understand *why* they're blocked and provide detailed context when asking for help.
