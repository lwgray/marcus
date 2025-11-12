# Artifact Diagnostic Guide

This guide helps you diagnose why artifacts are showing as 0 for your project.

## Quick Diagnostic

Run this to check artifact status for your project:

```python
import asyncio
from src.core.project_history import ProjectHistoryPersistence
from src.analysis.aggregator import ProjectHistoryAggregator

async def diagnose_artifacts(project_id: str):
    """Diagnose why artifacts aren't showing up."""
    persistence = ProjectHistoryPersistence()

    print(f"\n=== Artifact Diagnostic for {project_id} ===\n")

    # Step 1: Check SQLite directly (bypassing conversation filter)
    print("1. Checking SQLite database...")
    backend = persistence._backend
    all_artifacts = await backend.query("artifacts", limit=10000)
    project_artifacts = [a for a in all_artifacts if a.get("project_id") == project_id]

    print(f"   Total artifacts in SQLite for this project: {len(project_artifacts)}")

    if project_artifacts:
        print(f"\n   Artifact details:")
        for art in project_artifacts[:5]:  # Show first 5
            print(f"     - {art.get('filename')} (task_id: {art.get('task_id')})")
        if len(project_artifacts) > 5:
            print(f"     ... and {len(project_artifacts) - 5} more")

    # Step 2: Check conversation logs
    print("\n2. Checking conversation logs...")
    task_ids = await persistence._get_task_ids_from_conversations(project_id)
    print(f"   Task IDs found in conversations: {len(task_ids)}")

    if task_ids:
        print(f"   Task IDs: {list(task_ids)[:10]}")  # Show first 10
        if len(task_ids) > 10:
            print(f"     ... and {len(task_ids) - 10} more")

    # Step 3: Check which artifacts match conversation task_ids
    if project_artifacts and task_ids:
        print("\n3. Checking task_id matches...")
        matched = 0
        unmatched = []

        for art in project_artifacts:
            art_task_id = art.get("task_id")
            if art_task_id in task_ids:
                matched += 1
            else:
                unmatched.append((art.get('filename'), art_task_id))

        print(f"   Matched artifacts (in conversations): {matched}")
        print(f"   Unmatched artifacts (NOT in conversations): {len(unmatched)}")

        if unmatched:
            print(f"\n   Unmatched artifact details:")
            for filename, task_id in unmatched[:5]:
                print(f"     - {filename} has task_id '{task_id}' (not in conversations)")
            if len(unmatched) > 5:
                print(f"     ... and {len(unmatched) - 5} more")

    # Step 4: Check what aggregator returns
    print("\n4. Checking what aggregator returns...")
    aggregator = ProjectHistoryAggregator()
    history = await aggregator.aggregate_project(project_id)

    print(f"   Artifacts returned by aggregator: {len(history.artifacts)}")

    # Step 5: Diagnosis
    print("\n=== DIAGNOSIS ===")

    if len(project_artifacts) == 0:
        print("❌ NO ARTIFACTS FOUND in SQLite")
        print("   Possible causes:")
        print("   1. log_artifact() was never called")
        print("   2. Artifacts were logged for a different project_id")
        print("   3. SQLite database is empty or corrupted")
        print("\n   Action: Check logs for 'Persisted artifact' messages")

    elif len(task_ids) == 0:
        print("❌ NO TASK IDS FOUND in conversation logs")
        print("   Possible causes:")
        print("   1. Conversation logs are missing or empty")
        print("   2. Project has no recorded task conversations")
        print("\n   Action: Check if conversation logs exist for this project")

    elif len(unmatched) > 0 and len(unmatched) == len(project_artifacts):
        print("❌ ALL ARTIFACTS ARE UNMATCHED")
        print(f"   {len(project_artifacts)} artifacts exist in SQLite")
        print(f"   BUT their task_ids don't match conversation logs")
        print("\n   Possible causes:")
        print("   1. Task IDs in log_artifact() don't match conversation task_ids")
        print("   2. Artifacts were logged before conversations started")
        print("   3. Task ID format mismatch (e.g., 'task_123' vs '123')")
        print("\n   Action: Use Option 2 fix (fallback to project_id)")

    elif len(unmatched) > 0:
        print(f"⚠️  PARTIAL MATCH: {matched}/{len(project_artifacts)} artifacts matched")
        print(f"   {len(unmatched)} artifacts have task_ids not in conversations")
        print("\n   Action: Investigate unmatched task_ids")

    else:
        print("✅ ALL ARTIFACTS MATCHED")
        print(f"   All {len(project_artifacts)} artifacts have matching task_ids")
        print("\n   If CATO still shows 0, check:")
        print("   1. CATO is querying the correct project_id")
        print("   2. Aggregator summary calculation is correct")

# Run diagnostic
# asyncio.run(diagnose_artifacts("YOUR_PROJECT_ID_HERE"))
```

## How to Use This Diagnostic

### Step 1: Get your project ID

From CATO, or run:
```python
from src.core.project_registry import ProjectRegistry

async def list_projects():
    registry = ProjectRegistry()
    await registry.initialize()
    projects = await registry.list_projects()
    for p in projects:
        print(f"{p.name}: {p.id}")

asyncio.run(list_projects())
```

### Step 2: Run diagnostic

```python
asyncio.run(diagnose_artifacts("marcus_proj_abc123"))
```

### Step 3: Interpret results

**Scenario A: "NO ARTIFACTS FOUND in SQLite"**
```
Total artifacts in SQLite for this project: 0
```
**Cause**: `log_artifact()` was never called or failed
**Action**:
1. Check Marcus logs for `"Persisted artifact"` messages
2. Check if `log_artifact()` returned `success: true`
3. Verify project_root was provided correctly

**Scenario B: "NO TASK IDS FOUND in conversation logs"**
```
Total artifacts in SQLite: 5
Task IDs found in conversations: 0
```
**Cause**: Conversation logs missing or empty
**Action**:
1. Check if `logs/conversations/` directory exists
2. Check if project has conversation files
3. **FIX**: Apply Option 2 (fallback to project_id filter)

**Scenario C: "ALL ARTIFACTS ARE UNMATCHED"**
```
Total artifacts in SQLite: 5
Task IDs found in conversations: 10
Matched: 0
Unmatched: 5
  - api_spec.md has task_id 'task_123' (not in conversations)
  - design.md has task_id 'task_456' (not in conversations)
```
**Cause**: Task ID mismatch between artifacts and conversations
**Action**:
1. Check task_id format consistency
2. Check if artifacts logged before task conversations started
3. **FIX**: Apply Option 2 (fallback to project_id filter)

**Scenario D: "PARTIAL MATCH"**
```
Matched: 3
Unmatched: 2
```
**Cause**: Some artifacts have valid task_ids, others don't
**Action**:
1. Investigate unmatched task_ids specifically
2. May be timing issue (artifact logged before conversation)
3. **FIX**: Apply Option 3 (include orphaned artifacts with warning)

**Scenario E: "ALL ARTIFACTS MATCHED" but CATO shows 0**
```
All 5 artifacts have matching task_ids
Artifacts returned by aggregator: 5
```
**Cause**: Issue is in CATO or summary calculation
**Action**:
1. Check CATO is querying correct project_id
2. Check `get_project_summary()` is counting artifacts correctly
3. Check CATO API response structure

## Common Causes and Fixes

### Cause 1: Conversation logs not synced

**Symptom**: Artifacts in SQLite, but no task_ids in conversations

**Why this happens**:
- Artifacts logged via direct MCP call
- No conversation happened (automation/script)
- Conversation logs not written yet

**Fix**: Use Option 2 (fallback to project_id)

```python
# In src/core/project_history.py:668
if not project_task_ids:
    logger.warning(
        f"No task IDs found in conversations for {project_id}, "
        f"falling back to project_id filter"
    )
    def task_filter(item: dict[str, Any]) -> bool:
        return item.get("project_id") == project_id
else:
    def task_filter(item: dict[str, Any]) -> bool:
        return item.get("task_id") in project_task_ids
```

### Cause 2: Task ID format mismatch

**Symptom**: Task IDs exist in both, but don't match

**Example**:
- Artifact has `task_id = "task_123"`
- Conversation has `task_id = "marcus_task_123"`

**Why this happens**:
- Task ID prefixing inconsistency
- Different ID generation methods

**Fix**: Normalize task IDs during comparison

```python
# Normalize task IDs
def normalize_task_id(task_id: str) -> str:
    """Remove common prefixes for comparison."""
    prefixes = ["marcus_task_", "task_", "tsk_"]
    for prefix in prefixes:
        if task_id.startswith(prefix):
            return task_id[len(prefix):]
    return task_id

# Use normalized IDs
normalized_conversation_ids = {normalize_task_id(tid) for tid in project_task_ids}

def task_filter(item: dict[str, Any]) -> bool:
    art_task_id = normalize_task_id(item.get("task_id", ""))
    return art_task_id in normalized_conversation_ids
```

### Cause 3: Timing issue (artifact before conversation)

**Symptom**: Early artifacts unmatched, later ones matched

**Why this happens**:
- Agent logs artifact before conversation log is written
- Artifact logged in setup phase before task assignment

**Fix**: Use Option 3 (include orphaned with warning)

```python
# Load matched artifacts
artifacts_by_task = [filter by task_ids]

# Also load all project artifacts
all_project_artifacts = [filter by project_id]

# Include orphans
orphaned = [a for a in all_project_artifacts if a not in artifacts_by_task]
if orphaned:
    logger.warning(f"Including {len(orphaned)} orphaned artifacts")
    artifacts.extend(orphaned)
```

## Testing Your Fix

After applying a fix, verify it works:

```python
async def test_fix(project_id: str):
    """Test that artifacts are now loaded correctly."""
    from src.analysis.query_api import ProjectHistoryQuery
    from src.analysis.aggregator import ProjectHistoryAggregator

    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    # Get summary
    summary = await query.get_project_summary(project_id)

    print(f"\n=== FIX VERIFICATION ===")
    print(f"Project: {project_id}")
    print(f"Total artifacts in summary: {summary['total_artifacts']}")

    if summary['total_artifacts'] > 0:
        print("✅ SUCCESS: Artifacts are now being counted!")

        # Get full history to see artifacts
        history = await query.get_project_history(project_id)
        print(f"\nArtifacts loaded:")
        for art in history.artifacts[:10]:
            print(f"  - {art.filename} ({art.artifact_type})")
    else:
        print("❌ FAILED: Artifacts still showing as 0")
        print("\nRun diagnostic again to identify remaining issues")

# asyncio.run(test_fix("YOUR_PROJECT_ID"))
```

## Recommended Solution

Based on the investigation, **Option 2 (fallback to project_id)** is recommended because:

1. **Preserves design intent**: Still uses task_id when available
2. **Adds safety net**: Falls back to project_id when conversation logs incomplete
3. **Simple**: Minimal code change
4. **Safe**: No data loss
5. **Surfaces issues**: Logs warning when falling back

Implement in `src/core/project_history.py:664-676`:

```python
# Get task IDs for this project from conversation logs
project_task_ids = await self._get_task_ids_from_conversations(project_id)

if not project_task_ids:
    logger.warning(
        f"No task IDs found in conversations for {project_id}, "
        f"falling back to project_id-based artifact filtering"
    )
    # Fallback: filter by project_id instead
    def task_filter(item: dict[str, Any]) -> bool:
        return item.get("project_id") == project_id
else:
    # Normal path: filter by task_id from conversations
    def task_filter(item: dict[str, Any]) -> bool:
        return item.get("task_id") in project_task_ids
```

This fix:
- ✅ Handles missing conversation logs
- ✅ Handles incomplete conversation logs
- ✅ Logs warning for debugging
- ✅ Still uses task_id filtering when available
- ✅ Prevents artifact count = 0 when artifacts exist
