# Recovery Handoff Information Should Be Structured Task Data, Not Comments

## Problem Statement

When Marcus recovers a task from an agent (due to lease expiration, crash, etc.), the next agent needs to know:
- This task was previously worked on
- Who worked on it and for how long
- What progress was made
- Where to look for existing work (git history, artifacts)

**Current Implementation:**
Recovery handoff information is written as Kanban comments by `_create_recovery_handoff()` in `src/core/assignment_lease.py`. However, agents don't automatically see these comments because:
1. `get_task_context()` doesn't fetch comments (this was intentionally removed)
2. Agents would need to explicitly call a separate API to fetch comments
3. No mechanism signals to the agent that recovery occurred

**Why This Is a Problem:**
- **Operational information hidden in audit trail**: Recovery info is operational (agents need it to work correctly), but comments are primarily for observability/audit (humans and Cato)
- **No guaranteed visibility**: Agents may miss critical context about previous work
- **Risk of duplicated/conflicting work**: Next agent might take a completely different approach, leaving dead code
- **Poor separation of concerns**: Mixing operational coordination data with audit trail

## Proposed Solution: Structured Recovery Field (Option 3)

Add explicit `recovery_info` field to the Task model that is:
- **Structured data** (not unstructured comment text)
- **Automatically included** in `get_task_context()` response
- **Easy to detect programmatically** (agents can check `if task.recovery_info`)
- **Versioned and evolvable** (can add fields without breaking changes)

**Plus** dual-write to Kanban comments for audit trail (humans and Cato still see it).

## Implementation Details

### 1. Add Recovery Data Model

Create new dataclass in `src/core/models.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class RecoveryInfo:
    """
    Information about task recovery from a previous agent.

    This is operational data that the next agent needs to avoid
    duplicating work or taking conflicting approaches.
    """

    # When and from whom
    recovered_at: datetime
    recovered_from_agent: str

    # Progress information
    previous_progress: int  # Percentage (0-100)
    time_spent_minutes: float

    # Why recovery happened
    recovery_reason: str  # "lease_expired", "agent_crashed", "manual_recovery"

    # Guidance for next agent
    instructions: str  # Multi-line guidance about what to check

    # Optional: If recovery becomes stale
    recovery_expires_at: Optional[datetime] = None  # See "Stale Recovery" section

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "recovered_at": self.recovered_at.isoformat(),
            "recovered_from_agent": self.recovered_from_agent,
            "previous_progress": self.previous_progress,
            "time_spent_minutes": round(self.time_spent_minutes, 1),
            "recovery_reason": self.recovery_reason,
            "instructions": self.instructions,
            "recovery_expires_at": (
                self.recovery_expires_at.isoformat()
                if self.recovery_expires_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecoveryInfo":
        """Create from dictionary (for deserialization)."""
        from dateutil.parser import parse
        return cls(
            recovered_at=parse(data["recovered_at"]),
            recovered_from_agent=data["recovered_from_agent"],
            previous_progress=data["previous_progress"],
            time_spent_minutes=data["time_spent_minutes"],
            recovery_reason=data["recovery_reason"],
            instructions=data["instructions"],
            recovery_expires_at=(
                parse(data["recovery_expires_at"])
                if data.get("recovery_expires_at") else None
            ),
        )
```

### 2. Update Task Model

In `src/core/models.py`, add field to `Task` class:

```python
@dataclass
class Task:
    # ... existing fields ...

    # Recovery information (if this task was recovered from another agent)
    recovery_info: Optional[RecoveryInfo] = None
```

### 3. Update Recovery Logic

In `src/core/assignment_lease.py`, modify `recover_expired_lease()`:

```python
async def recover_expired_lease(self, lease: AssignmentLease) -> bool:
    """
    Recover a task from an expired lease.

    Now includes dual-write:
    1. Update task model with structured recovery info
    2. Post to Kanban comments for audit trail
    """
    try:
        # Calculate time spent
        time_spent = datetime.now(timezone.utc) - lease.assigned_at
        time_spent_minutes = time_spent.total_seconds() / 60

        # Create structured recovery info
        recovery_info = RecoveryInfo(
            recovered_at=datetime.now(timezone.utc),
            recovered_from_agent=lease.agent_id,
            previous_progress=lease.progress_percentage,
            time_spent_minutes=time_spent_minutes,
            recovery_reason="lease_expired",
            instructions=(
                f"⚠️ This task was recovered from agent {lease.agent_id}\n\n"
                f"**What to check:**\n"
                f"1. Run `git log --author={lease.agent_id}` to see any commits made\n"
                f"2. Check for any artifacts or design documents left by previous agent\n"
                f"3. Review progress: previous agent reached {lease.progress_percentage}%\n"
                f"4. Continue from where they left off to avoid duplicated work\n\n"
                f"**Context:**\n"
                f"- Previous agent worked for {time_spent_minutes:.1f} minutes\n"
                f"- Recovery reason: lease expired (no progress updates)\n"
            ),
            # Optional: Set expiration (e.g., 24 hours)
            recovery_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )

        # 1. Update task model (source of truth)
        task = self._find_task(lease.task_id)
        if task:
            task.recovery_info = recovery_info

        # 2. Dual-write to Kanban for audit trail
        # Don't fail entire recovery if Kanban write fails
        try:
            await self._create_recovery_handoff_comment(lease, recovery_info)
        except Exception as e:
            logger.warning(f"Failed to write recovery comment to Kanban: {e}")
            # Continue - task model update is what matters

        # ... rest of existing recovery logic ...

    except Exception as e:
        logger.error(f"Failed to recover lease for {lease.task_id}: {e}")
        return False
```

### 4. Update Task Context

In `src/marcus_mcp/tools/context.py`, ensure recovery info is included:

```python
async def get_task_context(task_id: str, state: Any) -> Dict[str, Any]:
    """Get the full context for a specific task."""
    try:
        # ... existing logic ...

        context_dict = context.to_dict()
        context_dict["is_subtask"] = False

        # Add artifact information
        artifacts = await _collect_task_artifacts(task_id, task, state)
        context_dict["artifacts"] = artifacts

        # Add recovery information if present
        if task.recovery_info:
            context_dict["recovery_info"] = task.recovery_info.to_dict()

        return {"success": True, "context": context_dict}
```

### 5. Update Kanban Comment Creation

Rename and update the comment method to accept structured data:

```python
async def _create_recovery_handoff_comment(
    self,
    lease: AssignmentLease,
    recovery_info: RecoveryInfo
) -> None:
    """
    Post recovery information to Kanban as a comment (audit trail).

    This is the dual-write for observability. The task model holds
    the authoritative recovery info that agents use.
    """
    comment = (
        f"⚠️ **TASK RECOVERED FROM AGENT {recovery_info.recovered_from_agent}**\n\n"
        f"**Recovery Details:**\n"
        f"- Recovered at: {recovery_info.recovered_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"- Progress: {recovery_info.previous_progress}%\n"
        f"- Time spent: {recovery_info.time_spent_minutes:.1f} minutes\n"
        f"- Reason: {recovery_info.recovery_reason}\n\n"
        f"{recovery_info.instructions}"
    )

    await self.kanban_client.add_comment(lease.task_id, comment)
```

## Edge Cases and Nuances

### 1. State Synchronization

**Problem**: Task model and Kanban must stay in sync. What if Kanban write fails?

**Solution**:
- Task model is source of truth (where agents read from)
- Kanban is audit trail (where humans/Cato read from)
- If Kanban write fails: log error, continue
- Don't fail entire recovery if audit trail write fails

```python
# Correct approach
task.recovery_info = recovery_info  # Critical - must succeed

try:
    await self._create_recovery_handoff_comment(lease, recovery_info)
except Exception as e:
    logger.warning(f"Audit trail write failed: {e}")
    # Don't raise - recovery succeeded even if audit failed
```

### 2. Multiple Recoveries

**Problem**: What if a task is recovered multiple times? Should we keep history?

**Solution Options**:

**Option A (Simple)**: Replace recovery_info each time
- Pro: Simple, agent always sees latest recovery
- Con: Lose history of multiple failures

**Option B (Recommended)**: Keep list of recoveries
```python
@dataclass
class Task:
    recovery_history: List[RecoveryInfo] = field(default_factory=list)

    @property
    def recovery_info(self) -> Optional[RecoveryInfo]:
        """Get most recent recovery (if any)."""
        return self.recovery_history[-1] if self.recovery_history else None
```

- Pro: Full history preserved
- Pro: Can analyze patterns (task recovered 3 times = problem?)
- Con: More complex

**Recommendation for initial implementation**: Use Option A (simple replacement). Add Option B later if needed.

### 3. Stale Recovery Information

**Problem**: What if a recovered task sits in backlog for hours/days? Is old recovery info still relevant?

**Example**: Task recovered at 9am, sits in backlog until 9am next day. Is 24-hour-old recovery info useful?

**Solution**: Add expiration

```python
# When creating recovery info
recovery_info.recovery_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

# When agent gets task context
if task.recovery_info:
    if task.recovery_info.recovery_expires_at < datetime.now(timezone.utc):
        # Recovery info is stale - treat as fresh task
        context_dict["recovery_info"] = None
        context_dict["stale_recovery"] = task.recovery_info.to_dict()  # For debugging
    else:
        context_dict["recovery_info"] = task.recovery_info.to_dict()
```

**Recommendation**: Set 24-hour expiration. After that, recovery info moved to "stale_recovery" field (visible but not actionable).

### 4. Schema Migration

**Problem**: Existing tasks don't have `recovery_info` field.

**Solution**: Field is `Optional[RecoveryInfo] = None`, so:
- Existing tasks: `recovery_info` is `None` (not recovered)
- No data migration needed
- Backward compatible

### 5. Testing Edge Case

**Problem**: How to test recovery handoff in unit tests?

**Solution**: Mock task recovery, verify both writes happen

```python
async def test_recovery_creates_structured_info_and_comment():
    """Test dual-write: task model + Kanban comment."""
    # Arrange
    lease = create_expired_lease()

    # Act
    await lease_manager.recover_expired_lease(lease)

    # Assert: Task model updated
    task = find_task(lease.task_id)
    assert task.recovery_info is not None
    assert task.recovery_info.recovered_from_agent == lease.agent_id
    assert task.recovery_info.previous_progress == lease.progress_percentage

    # Assert: Kanban comment posted
    kanban_client.add_comment.assert_called_once()
    comment_text = kanban_client.add_comment.call_args[0][1]
    assert "TASK RECOVERED" in comment_text
    assert lease.agent_id in comment_text
```

## Acceptance Criteria

- [ ] `RecoveryInfo` dataclass created in `src/core/models.py`
- [ ] `Task.recovery_info` field added (Optional[RecoveryInfo])
- [ ] `recover_expired_lease()` populates `task.recovery_info` on recovery
- [ ] `recover_expired_lease()` dual-writes to Kanban comment (don't fail if comment fails)
- [ ] `get_task_context()` includes `recovery_info` in response when present
- [ ] Recovery info includes expiration timestamp (24 hours)
- [ ] Stale recovery info (past expiration) moved to `stale_recovery` field
- [ ] Unit tests verify task model update
- [ ] Unit tests verify Kanban comment posted
- [ ] Unit tests verify recovery info in task context
- [ ] Unit tests verify graceful degradation if Kanban write fails
- [ ] Integration test: trigger lease expiration, verify next agent sees recovery info
- [ ] Documentation updated in recovery guide

## Files to Modify

1. `src/core/models.py` - Add `RecoveryInfo` dataclass and `Task.recovery_info` field
2. `src/core/assignment_lease.py` - Update `recover_expired_lease()` with dual-write
3. `src/marcus_mcp/tools/context.py` - Include recovery_info in task context
4. `tests/unit/core/test_assignment_lease.py` - Add recovery info tests
5. `tests/unit/mcp/test_context_tools.py` - Add recovery info in context tests
6. `tests/integration/e2e/test_recovery_handoff.py` - NEW: End-to-end recovery test

## Related Issues

- Current implementation writes to comments only (no structured data)
- Comment fetching was removed from `get_task_context()` (see commit b998151)
- Progressive timeout system implemented (commits 98d17b8, fabacbe)

## Questions for Reviewer

1. Should we use Option A (simple replacement) or Option B (keep history) for multiple recoveries?
2. Is 24-hour expiration reasonable for recovery info staleness?
3. Should we backfill recovery_info for any currently-in-recovery tasks?

---

**Priority**: High - affects agent coordination and work quality
**Complexity**: Medium - requires model changes and dual-write logic
**Risk**: Low - field is optional, backward compatible, dual-write has fallback
