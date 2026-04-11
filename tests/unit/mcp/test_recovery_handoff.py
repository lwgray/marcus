"""
Unit tests for recovery handoff in task instructions.

When a task is recovered from a failed/timed-out agent, the next agent
should receive context about the previous work so they can pick up where
the last agent left off rather than starting from scratch.

This tests the "last mile" wiring: RecoveryInfo is created by
AssignmentLeaseManager.recover_expired_lease() and attached to the task
model, but build_tiered_instructions must include it in the instructions
sent to the next agent.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from src.core.models import Priority, RecoveryInfo, Task, TaskStatus
from src.marcus_mcp.tools.task import build_tiered_instructions


def _create_task(
    task_id: str = "task-123",
    name: str = "Implement auth module",
    description: str = "Build the authentication module",
    recovery_info: Optional[RecoveryInfo] = None,
) -> Task:
    """
    Create a test task with optional recovery info.

    Parameters
    ----------
    task_id : str
        Task identifier
    name : str
        Task name
    description : str
        Task description
    recovery_info : Optional[RecoveryInfo]
        Recovery handoff data from previous agent

    Returns
    -------
    Task
        Test task instance
    """
    now = datetime.now(timezone.utc)
    task = Task(
        id=task_id,
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=4.0,
        labels=[],
        dependencies=[],
    )
    task.recovery_info = recovery_info
    return task


def _create_recovery_info(
    previous_progress: int = 30,
    agent_id: str = "agent-3",
    time_spent_minutes: float = 45.0,
    recovery_reason: str = "lease_expired",
    expired: bool = False,
) -> RecoveryInfo:
    """
    Create a RecoveryInfo instance for testing.

    Parameters
    ----------
    previous_progress : int
        Progress percentage at time of recovery
    agent_id : str
        ID of the agent that was previously working on the task
    time_spent_minutes : float
        How long the previous agent worked
    recovery_reason : str
        Why the task was recovered
    expired : bool
        Whether the recovery info should be expired (>24h old)

    Returns
    -------
    RecoveryInfo
        Test recovery info instance
    """
    now = datetime.now(timezone.utc)

    if expired:
        recovered_at = now - timedelta(hours=25)
        expires_at = now - timedelta(hours=1)
    else:
        recovered_at = now - timedelta(minutes=10)
        expires_at = now + timedelta(hours=24)

    branch = f"marcus/{agent_id}"
    return RecoveryInfo(
        recovered_at=recovered_at,
        recovered_from_agent=agent_id,
        previous_progress=previous_progress,
        time_spent_minutes=time_spent_minutes,
        recovery_reason=recovery_reason,
        previous_agent_branch=branch,
        instructions=(
            f"⚠️ **RECOVERY ADDENDUM** - This task was recovered "
            f"from agent {agent_id}\n\n"
            f"**FIRST: Pick up committed work from the previous agent:**\n"
            f"```\n"
            f"git merge {branch} --no-edit\n"
            f"```\n"
            f"This merges any commits the previous agent made before "
            f"they disconnected.\n\n"
            f"**Then check what was done:**\n"
            f"1. Run `git log {branch}` to see their commits\n"
            f"2. Check for artifacts or design documents\n"
            f"3. Previous agent reached {previous_progress}%\n"
            f"4. **Continue from where they left off** - "
            f"don't restart from scratch\n"
        ),
        recovery_expires_at=expires_at,
    )


@pytest.mark.unit
class TestRecoveryHandoffLayer:
    """Test that recovery info is included in tiered instructions."""

    def test_recovery_info_included_in_instructions(self) -> None:
        """Test that task with recovery_info includes handoff in instructions."""
        recovery = _create_recovery_info(previous_progress=30, agent_id="agent-3")
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base task instructions",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "RECOVERY" in instructions
        assert "agent-3" in instructions
        assert "30%" in instructions

    def test_no_recovery_info_no_change(self) -> None:
        """Test that task without recovery_info has no recovery section."""
        task = _create_task(recovery_info=None)

        instructions = build_tiered_instructions(
            base_instructions="Base task instructions",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "RECOVERY" not in instructions
        assert "recovered" not in instructions.lower()

    def test_expired_recovery_info_excluded(self) -> None:
        """Test that expired recovery info (>24h) is not included."""
        recovery = _create_recovery_info(expired=True)
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base task instructions",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "RECOVERY" not in instructions

    def test_recovery_layer_appears_after_base(self) -> None:
        """Test recovery layer comes after base instructions."""
        recovery = _create_recovery_info()
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base task instructions",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        base_pos = instructions.find("Base task instructions")
        recovery_pos = instructions.find("RECOVERY")

        assert (
            base_pos < recovery_pos
        ), "Recovery layer should appear after base instructions"

    def test_recovery_includes_previous_progress(self) -> None:
        """Test that recovery instructions show previous agent's progress."""
        recovery = _create_recovery_info(previous_progress=65, time_spent_minutes=120.0)
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "65%" in instructions
        assert "120" in instructions

    def test_recovery_includes_worktree_merge_instruction(self) -> None:
        """Test that recovery tells agent to merge the dead agent's branch."""
        recovery = _create_recovery_info(agent_id="agent-7")
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "git merge marcus/agent-7" in instructions
        assert "agent-7" in instructions

    def test_recovery_includes_branch_name(self) -> None:
        """Test that recovery info references the dead agent's branch."""
        recovery = _create_recovery_info(agent_id="agent-5")
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "marcus/agent-5" in instructions

    def test_recovery_with_zero_progress(self) -> None:
        """Test recovery when previous agent made no progress at all."""
        recovery = _create_recovery_info(previous_progress=0, time_spent_minutes=2.0)
        task = _create_task(recovery_info=recovery)

        instructions = build_tiered_instructions(
            base_instructions="Base",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # Should still include recovery section (agent may have uncommitted work)
        assert "RECOVERY" in instructions
        assert "0%" in instructions
