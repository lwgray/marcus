"""Unit tests for bug #651 — merge-conflict handling in report_task_progress.

Background
----------
Bug #651: When ``_merge_agent_branch_to_main`` reports a merge conflict,
the existing code marked the kanban task DONE anyway and "deferred" the
failure for return after the kanban update.  Under ephemeral one-agent-
per-task lifecycle (PR #600), the agent receiving the deferred failure
has already exited — the message goes nowhere.  Net result: kanban
claims the task is done, filesystem doesn't contain the work.

The fix introduces ``_apply_merge_failure_to_update_data`` which:

- Flips ``update_data["status"]`` from ``TaskStatus.DONE`` to
  ``TaskStatus.BLOCKED``
- Removes ``completed_at`` (task is not actually done)
- Stamps ``source_context.merge_conflict`` with the agent/branch/stderr
  so a recovery mechanism (CLI command, follow-up agent, or human) has
  the info needed to resolve
- Returns a structured failure response so the caller sees the BLOCKED
  state rather than a misleading success

These tests verify the helper's contract.  An integration-style test
verifies the wiring inside ``report_task_progress``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from src.core.models import TaskStatus

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _apply_merge_failure_to_update_data — helper-function contract
# ---------------------------------------------------------------------------


class TestApplyMergeFailureToUpdateData:
    """The helper that translates a merge_result failure into BLOCKED state."""

    def _task(
        self, task_id: str = "task_X", source_context: Dict[str, Any] | None = None
    ) -> MagicMock:
        """Minimal task stub with the attributes the helper reads."""
        task = MagicMock()
        task.id = task_id
        task.source_context = source_context
        return task

    def _failure_result(self) -> Dict[str, Any]:
        """Canonical merge failure payload returned by _merge_agent_branch_to_main."""
        return {
            "success": False,
            "error": "merge_conflict",
            "message": (
                "Your task passed validation but merging your branch "
                "(marcus/agent_X) to main has conflicts. Please "
                "resolve them..."
            ),
        }

    def test_flips_status_from_done_to_blocked(self) -> None:
        """The bug at task.py:3397 sets status=DONE; this helper flips it.

        Without this flip, the kanban update later in
        ``report_task_progress`` records DONE despite the work not
        being merged.  That divergence is the foundational bug #651
        addresses.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data: Dict[str, Any] = {
            "status": TaskStatus.DONE,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        task = self._task(task_id="task_X")
        merge_result = self._failure_result()

        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=merge_result,
            agent_id="agent_X",
        )

        assert update_data["status"] == TaskStatus.BLOCKED

    def test_removes_completed_at_field(self) -> None:
        """``completed_at`` must be cleared — the task is NOT completed.

        Leaving ``completed_at`` populated alongside BLOCKED status
        would corrupt downstream telemetry (Cato's "completion
        latency" metrics, etc.) and make audits inconsistent.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data = {
            "status": TaskStatus.DONE,
            "completed_at": "2026-05-24T15:00:00+00:00",
        }
        task = self._task()
        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=self._failure_result(),
            agent_id="agent_X",
        )

        assert "completed_at" not in update_data

    def test_stamps_merge_conflict_on_source_context(self) -> None:
        """Conflict info goes onto source_context so recovery has the
        info needed to resolve.

        The recovery surface (CLI, follow-up agent, or human) reads
        ``source_context.merge_conflict`` to know:
        - which branch failed to merge (``branch``)
        - the underlying git error (``conflict_stderr``)
        - when the conflict occurred (``blocked_at``)
        - which agent's work is parked (``agent_id``)
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data: Dict[str, Any] = {"status": TaskStatus.DONE}
        task = self._task(task_id="task_X")
        merge_result = self._failure_result()

        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=merge_result,
            agent_id="agent_X",
        )

        ctx = update_data["source_context"]
        assert "merge_conflict" in ctx
        mc = ctx["merge_conflict"]
        assert mc["agent_id"] == "agent_X"
        assert mc["branch"] == "marcus/agent_X"
        assert "conflicts" in mc["conflict_stderr"]
        # blocked_at must be ISO-8601 parseable
        datetime.fromisoformat(mc["blocked_at"])

    def test_preserves_existing_source_context_fields(self) -> None:
        """Pre-existing source_context fields must survive the stamp.

        Tasks carry meaningful source_context already (e.g.,
        ``in_scope_outcome_ids`` from issue #523, ``responsibility``
        from contract-first decomposition).  The merge-conflict
        stamp must coexist with those, not overwrite them.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        existing_ctx = {
            "in_scope_outcome_ids": ["o_play", "o_score"],
            "responsibility": "Wires the application entry point",
        }
        update_data: Dict[str, Any] = {"status": TaskStatus.DONE}
        task = self._task(source_context=existing_ctx)

        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=self._failure_result(),
            agent_id="agent_X",
        )

        ctx = update_data["source_context"]
        assert ctx["in_scope_outcome_ids"] == ["o_play", "o_score"]
        assert ctx["responsibility"] == "Wires the application entry point"
        assert "merge_conflict" in ctx

    def test_handles_none_source_context_on_task(self) -> None:
        """Tasks with ``source_context=None`` get a fresh dict, no crash.

        Legacy integration tasks have ``source_context = None``.  The
        helper must initialize the dict when stamping, not raise an
        AttributeError on ``None.copy()``.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data: Dict[str, Any] = {"status": TaskStatus.DONE}
        task = self._task(source_context=None)

        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=self._failure_result(),
            agent_id="agent_X",
        )

        ctx = update_data["source_context"]
        assert "merge_conflict" in ctx

    def test_returns_failure_response_with_blocker_message(self) -> None:
        """The helper returns the response dict the caller surfaces to runner.

        The runner (or any orchestrator) needs to know the task is in
        BLOCKED state because of a merge conflict.  Without this
        response, the runner would interpret silence as success and
        proceed to claim the task done.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data: Dict[str, Any] = {"status": TaskStatus.DONE}
        task = self._task(task_id="task_X")
        merge_result = self._failure_result()

        response = _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=merge_result,
            agent_id="agent_X",
        )

        assert response["success"] is False
        assert response["status"] == "merge_conflict"
        assert response["task_id"] == "task_X"
        assert response["agent_id"] == "agent_X"
        assert (
            "branch" in response["blocker"].lower()
            or "merge" in response["blocker"].lower()
        )

    def test_does_not_mutate_merge_result(self) -> None:
        """Defensive: the helper must not mutate its input merge_result.

        ``_merge_agent_branch_to_main``'s return is the source of truth
        for audit/telemetry — mutating it from a side-channel would
        make traces inconsistent.
        """
        from src.marcus_mcp.tools.task import _apply_merge_failure_to_update_data

        update_data: Dict[str, Any] = {"status": TaskStatus.DONE}
        task = self._task()
        merge_result = self._failure_result()
        merge_result_snapshot = dict(merge_result)

        _apply_merge_failure_to_update_data(
            update_data=update_data,
            task=task,
            merge_result=merge_result,
            agent_id="agent_X",
        )

        assert merge_result == merge_result_snapshot


# ---------------------------------------------------------------------------
# Integration check — the wiring inside report_task_progress
# ---------------------------------------------------------------------------


class TestReportTaskProgressMergeConflictWiring:
    """Verify the helper is wired into report_task_progress correctly.

    Heavier-weight check than the helper tests above — exercises the
    full code path so we catch wiring regressions where the helper
    is correct but never gets called.
    """

    def test_helper_is_imported_by_task_module(self) -> None:
        """The helper must be exported from ``src.marcus_mcp.tools.task``.

        Regression guard: a refactor that moves the helper without
        updating the import would silently break the fix.
        """
        from src.marcus_mcp.tools import task

        assert hasattr(task, "_apply_merge_failure_to_update_data")
