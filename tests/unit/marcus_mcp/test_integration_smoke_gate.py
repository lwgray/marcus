"""Unit tests for the product smoke gate in report_task_progress.

When an integration verification task (label ``"type:integration"``)
reports completion, Marcus must run ``ProductSmokeVerifier`` as an
independent check — and reject the completion if verification
fails, regardless of what the agent claimed.

These tests cover the wiring at the ``report_task_progress`` level:
- Integration tasks invoke the smoke gate
- Non-integration tasks do NOT invoke the smoke gate (no overhead)
- A failing smoke gate rejects the completion with a structured error
- A passing smoke gate lets the completion proceed
- Verifier crashes log-and-continue (don't block on infrastructure)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskAssignment, TaskStatus
from src.integrations.product_smoke import (
    DetectedStack,
    ProductSmokeResult,
    VerificationStep,
)
from src.marcus_mcp.tools.task import (
    _is_integration_task,
    _run_product_smoke_gate,
    report_task_progress,
)

pytestmark = pytest.mark.unit


def _make_integration_task(task_id: str = "int-001") -> Task:
    return Task(
        id=task_id,
        name="Integration verification for Test Project",
        description="Build and verify",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        assigned_to="agent-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        labels=["integration", "verification", "type:integration"],
    )


def _make_impl_task(task_id: str = "impl-001") -> Task:
    return Task(
        id=task_id,
        name="Implement Feature",
        description="Build it",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        assigned_to="agent-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        labels=["implementation", "backend"],
    )


def _make_assignment(task_id: str, agent_id: str = "agent-001") -> TaskAssignment:
    return TaskAssignment(
        task_id=task_id,
        task_name="t",
        description="d",
        instructions="i",
        estimated_hours=1.0,
        priority=Priority.HIGH,
        dependencies=[],
        assigned_to=agent_id,
        assigned_at=datetime.now(timezone.utc),
        due_date=None,
    )


def _make_state(
    task: Task,
    agent_id: str = "agent-001",
    project_root: str | None = None,
) -> Mock:
    """Build a Mock state suitable for report_task_progress.

    ``project_root`` defaults to a stable subdirectory under the
    system temp dir (resolved via ``tempfile.gettempdir()``) when
    not provided, so we don't hardcode ``/tmp`` paths that bandit
    flags as B108. Tests that need a specific directory should
    pass their own ``tmp_path``.
    """
    import tempfile as _tempfile

    if project_root is None:
        project_root = str(Path(_tempfile.gettempdir()) / "marcus_smoke_gate_test")
    state = Mock()
    state.initialize_kanban = AsyncMock()
    state.kanban_client = Mock()
    state.kanban_client.get_all_tasks = AsyncMock(return_value=[task])
    state.kanban_client.update_task = AsyncMock()
    state.kanban_client.update_task_progress = AsyncMock()
    state.kanban_client._load_workspace_state = Mock(
        return_value={"project_root": project_root}
    )
    state.agent_tasks = {agent_id: _make_assignment(task.id, agent_id)}
    state.project_tasks = [task]
    state.lease_manager = None
    state.agent_status = {}
    state.assignment_persistence = Mock()
    state.assignment_persistence.remove_assignment = AsyncMock()
    state.memory = None
    state.provider = "sqlite"
    state.code_analyzer = None
    state.subtask_manager = None
    return state


class TestIsIntegrationTask:
    """``_is_integration_task`` correctly identifies integration tasks."""

    def test_label_present_returns_true(self) -> None:
        task = _make_integration_task()
        assert _is_integration_task(task) is True

    def test_label_absent_returns_false(self) -> None:
        task = _make_impl_task()
        assert _is_integration_task(task) is False

    def test_no_labels_returns_false(self) -> None:
        task = Task(
            id="x",
            name="x",
            description="x",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=1.0,
            labels=[],
        )
        assert _is_integration_task(task) is False


class TestProductSmokeGate:
    """Direct tests of ``_run_product_smoke_gate``."""

    @pytest.mark.asyncio
    async def test_smoke_gate_passes_returns_none(self, tmp_path: Path) -> None:
        """Passing smoke verification → gate returns None (proceed)."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing_result = ProductSmokeResult(
            success=True,
            detected_stacks=[],
            steps=[],
            skipped_reason="no stack detected",
        )
        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
            return_value=passing_result,
        ):
            response = await _run_product_smoke_gate(
                task=task, agent_id="agent-001", state=state
            )
        assert response is None

    @pytest.mark.asyncio
    async def test_smoke_gate_failure_returns_rejection(self, tmp_path: Path) -> None:
        """Failing smoke verification → gate returns a rejection dict."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        failing_step = VerificationStep(
            name="build",
            command=["npm", "run", "build"],
            cwd=tmp_path,
            exit_code=1,
            stdout="",
            stderr="Could not find a required file. Name: index.html",
            duration_seconds=1.5,
            success=False,
        )
        failing_result = ProductSmokeResult(
            success=False,
            detected_stacks=[
                DetectedStack(
                    stack_type="node", root_path=tmp_path, marker_file=tmp_path
                )
            ],
            steps=[failing_step],
            failure_summary="build failed",
            blocker_message="## Product smoke verification FAILED\nindex.html missing",
        )
        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
            return_value=failing_result,
        ):
            response = await _run_product_smoke_gate(
                task=task, agent_id="agent-001", state=state
            )

        assert response is not None
        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        assert response["error"] == "product_smoke_failed"
        assert response["task_id"] == task.id
        assert "index.html" in response["blocker"]
        assert response["smoke_result"]["success"] is False

    @pytest.mark.asyncio
    async def test_smoke_gate_skips_when_no_workspace_state(self) -> None:
        """No project_root in workspace state → gate skips, returns None."""
        task = _make_integration_task()
        state = _make_state(task)
        state.kanban_client._load_workspace_state = Mock(return_value=None)

        response = await _run_product_smoke_gate(
            task=task, agent_id="agent-001", state=state
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_smoke_gate_skips_when_workspace_load_raises(self) -> None:
        """Workspace state load crash → gate skips with warning, returns None."""
        task = _make_integration_task()
        state = _make_state(task)
        state.kanban_client._load_workspace_state = Mock(
            side_effect=RuntimeError("kanban down")
        )

        response = await _run_product_smoke_gate(
            task=task, agent_id="agent-001", state=state
        )
        assert response is None

    @pytest.mark.asyncio
    async def test_smoke_gate_skips_when_project_root_not_a_dir(
        self, tmp_path: Path
    ) -> None:
        """project_root that doesn't exist as dir → skip, no crash."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path / "does-not-exist"))

        response = await _run_product_smoke_gate(
            task=task, agent_id="agent-001", state=state
        )
        assert response is None


class TestReportTaskProgressIntegration:
    """End-to-end test: report_task_progress invokes the smoke gate."""

    @pytest.mark.asyncio
    async def test_integration_task_completion_triggers_smoke_gate(
        self, tmp_path: Path
    ) -> None:
        """
        When report_task_progress receives status=completed for an
        integration task, ProductSmokeVerifier.verify is called.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing_result = ProductSmokeResult(
            success=True,
            detected_stacks=[],
            steps=[],
            skipped_reason="no stack",
        )
        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
            return_value=passing_result,
        ) as mock_verify:
            await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
            )
            mock_verify.assert_called_once()

    @pytest.mark.asyncio
    async def test_failing_smoke_gate_rejects_completion(self, tmp_path: Path) -> None:
        """
        Failing smoke verification rejects the completion. Kanban
        DONE write must NOT happen.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        failing_result = ProductSmokeResult(
            success=False,
            detected_stacks=[
                DetectedStack(
                    stack_type="node", root_path=tmp_path, marker_file=tmp_path
                )
            ],
            steps=[
                VerificationStep(
                    name="build",
                    command=["npm", "run", "build"],
                    cwd=tmp_path,
                    exit_code=1,
                    stdout="",
                    stderr="missing index.html",
                    duration_seconds=1.0,
                    success=False,
                )
            ],
            failure_summary="build failed",
            blocker_message="missing index.html in public/",
        )
        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
            return_value=failing_result,
        ):
            response = await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
            )

        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        # Kanban DONE write was blocked because the smoke gate
        # short-circuited before the completion path.
        state.kanban_client.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_integration_task_skips_smoke_gate(self, tmp_path: Path) -> None:
        """
        Implementation tasks completing should NOT trigger the smoke
        gate — only integration tasks do.
        """
        task = _make_impl_task()
        state = _make_state(task, project_root=str(tmp_path))

        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
        ) as mock_verify:
            await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
            )
            mock_verify.assert_not_called()

    @pytest.mark.asyncio
    async def test_smoke_gate_system_error_falls_through(self, tmp_path: Path) -> None:
        """
        ProductSmokeVerifier crashes (not a smoke failure — an
        actual exception) → log-and-continue. The task completion
        proceeds to avoid blocking on infrastructure problems.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        with patch(
            "src.integrations.product_smoke.ProductSmokeVerifier.verify",
            new_callable=AsyncMock,
            side_effect=RuntimeError("verifier internal error"),
        ):
            response = await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
            )

        # Completion proceeds (kanban WAS called) — verifier crash
        # doesn't block, just logs.
        assert response.get("success") is True
        state.kanban_client.update_task.assert_called_once()
