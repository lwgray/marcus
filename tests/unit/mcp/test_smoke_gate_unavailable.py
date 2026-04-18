"""
Unit tests for _run_product_smoke_gate infrastructure-failure rejections (P2-2 fix).

Codex P2-2 post-mortem: _run_product_smoke_gate previously returned None
(pass) in three error paths where the smoke gate could not be initialised:
  1. workspace state load raised an exception
  2. project_root not present in workspace state
  3. project_root path is not a directory

None is the "verification passed" sentinel; these cases should be hard
rejections so that integration tasks cannot slip through on misconfigured
environments.

Tests:
- workspace state load failure  → smoke_gate_unavailable rejection
- project_root missing from state → smoke_gate_unavailable rejection
- project_root not a directory   → smoke_gate_unavailable rejection
- valid project_root + passing verify_deliverable → returns None (pass)
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Import the private function under test.
# We reach into the module to grab the private coroutine directly.
# ---------------------------------------------------------------------------
from src.marcus_mcp.tools.task import _run_product_smoke_gate  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------


def _make_task(task_id: str = "task-42") -> Any:
    """Return a minimal Task-like stub."""
    task = Mock()
    task.id = task_id
    return task


def _make_state(ws_state: Any = None, ws_raises: Any = None) -> Any:
    """Return a minimal state stub with a mock kanban_client.

    Parameters
    ----------
    ws_state : Any
        Dict returned by `_load_workspace_state()`, or None.
    ws_raises : Any
        If set, `_load_workspace_state()` raises this exception instead.
    """
    state = Mock()
    kanban = Mock()
    if ws_raises is not None:
        kanban._load_workspace_state = Mock(side_effect=ws_raises)
    else:
        kanban._load_workspace_state = Mock(return_value=ws_state)
    state.kanban_client = kanban
    return state


def _make_verify_result(success: bool) -> Any:
    """Return a minimal VerifyResult-like stub."""
    result = Mock()
    result.success = success
    result.steps = []
    result.failure_summary = "command exited non-zero"
    result.blocker_message = "Fix the command."
    result.to_dict = Mock(return_value={})
    return result


# ---------------------------------------------------------------------------
# Tests: _gate_unavailable paths
# ---------------------------------------------------------------------------


class TestSmokeGateUnavailable:
    """Tests for the P2-2 hard-rejection paths in _run_product_smoke_gate."""

    @pytest.mark.asyncio
    async def test_rejects_when_workspace_state_load_raises(self) -> None:
        """
        Verify a rejection dict is returned when workspace state load fails.

        Previously this path returned None (pass). After the P2-2 fix it
        must return a rejection with error='smoke_gate_unavailable'.
        """
        task = _make_task("task-ws-err")
        state = _make_state(ws_raises=RuntimeError("db unavailable"))

        result = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-1",
            state=state,
            start_command="npm start",
            readiness_probe=None,
        )

        assert result is not None, "Must not return None (pass) on ws load failure"
        assert result["success"] is False
        assert result["error"] == "smoke_gate_unavailable"
        assert result["status"] == "smoke_verification_failed"
        assert "workspace state load failed" in result["failure_summary"]
        assert result["task_id"] == "task-ws-err"

    @pytest.mark.asyncio
    async def test_rejects_when_project_root_missing(self) -> None:
        """
        Verify a rejection dict is returned when project_root is absent.

        workspace state loads successfully but contains no project_root key.
        Previously returned None; now must reject.
        """
        task = _make_task("task-no-root")
        state = _make_state(ws_state={"other_key": "value"})

        result = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-2",
            state=state,
            start_command="python -m app",
            readiness_probe=None,
        )

        assert result is not None, "Must not return None when project_root absent"
        assert result["success"] is False
        assert result["error"] == "smoke_gate_unavailable"
        assert "project_root not found" in result["failure_summary"]

    @pytest.mark.asyncio
    async def test_rejects_when_project_root_not_a_directory(
        self, tmp_path: Path
    ) -> None:
        """
        Verify a rejection dict is returned when project_root is not a directory.

        project_root in workspace state points to a non-existent path.
        Previously returned None; now must reject.
        """
        task = _make_task("task-bad-dir")
        nonexistent = str(tmp_path / "does_not_exist")
        state = _make_state(ws_state={"project_root": nonexistent})

        result = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-3",
            state=state,
            start_command="cargo run",
            readiness_probe=None,
        )

        assert result is not None, "Must not return None when project_root not a dir"
        assert result["success"] is False
        assert result["error"] == "smoke_gate_unavailable"
        assert "not a directory" in result["failure_summary"]

    @pytest.mark.asyncio
    async def test_returns_none_when_verification_passes(self, tmp_path: Path) -> None:
        """
        Verify the function returns None (pass sentinel) on successful verification.

        This is the golden-path test: valid project_root + passing
        verify_deliverable → None.
        """
        task = _make_task("task-ok")
        state = _make_state(ws_state={"project_root": str(tmp_path)})
        passing_result = _make_verify_result(success=True)

        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=passing_result,
        ):
            result = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-4",
                state=state,
                start_command="echo ok",
                readiness_probe=None,
            )

        assert result is None, "Passing verification must return None"

    @pytest.mark.asyncio
    async def test_rejection_includes_task_and_agent_ids(self) -> None:
        """
        Verify task_id and agent_id appear in the rejection payload.

        Agents need these fields to correlate the rejection with their work.
        """
        task = _make_task("task-id-check")
        state = _make_state(ws_state={})  # no project_root

        result = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-id-check",
            state=state,
            start_command="yarn dev",
            readiness_probe=None,
        )

        assert result is not None
        assert result["task_id"] == "task-id-check"
        assert result["agent_id"] == "agent-id-check"

    @pytest.mark.asyncio
    async def test_rejection_blocker_mentions_workspace_state(self) -> None:
        """
        Verify the blocker message guides the agent toward the root cause.

        The message must mention 'workspace state' so the agent (or the
        experiment runner) knows where to look.
        """
        task = _make_task("task-blocker-msg")
        state = _make_state(ws_state=None)  # _load_workspace_state returns None

        result = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-5",
            state=state,
            start_command="make serve",
            readiness_probe=None,
        )

        assert result is not None
        assert "workspace state" in result["blocker"].lower()
