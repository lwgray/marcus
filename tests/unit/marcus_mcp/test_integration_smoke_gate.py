"""Unit tests for the integration smoke gate in report_task_progress.

Covers the wiring between ``report_task_progress`` and the deliverable
verification runner. The gate fires only on integration verification
tasks (``"type:integration"`` label), strictly requires the agent to
declare ``start_command`` on completion, and rejects the completion
if verification fails or the declaration is missing.

Non-integration tasks bypass the gate entirely — ``start_command``
and ``readiness_probe`` are ignored for implementation tasks so the
API surface doesn't accidentally block normal agent work.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskAssignment, TaskStatus
from src.integrations.product_smoke import (
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
    """Build a Mock state for report_task_progress."""
    if project_root is None:
        project_root = str(Path(tempfile.gettempdir()) / "marcus_smoke_gate_test")
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
        assert _is_integration_task(_make_integration_task()) is True

    def test_label_absent_returns_false(self) -> None:
        assert _is_integration_task(_make_impl_task()) is False

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
    """Direct tests of ``_run_product_smoke_gate`` with new signature."""

    @pytest.mark.asyncio
    async def test_gate_rejects_missing_start_command(self, tmp_path: Path) -> None:
        """
        Missing start_command on an integration task → rejection
        with the missing-declaration blocker. STRICT.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        # The runner returns a missing-declaration result
        missing_result = ProductSmokeResult(
            success=False,
            steps=[
                VerificationStep(
                    name="missing_start_command",
                    command="",
                    exit_code=None,
                    stdout="",
                    stderr="No start_command declared.",
                    duration_seconds=0.0,
                    success=False,
                )
            ],
            failure_summary="integration task missing required start_command",
            blocker_message="## Integration task rejected: missing start_command",
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=missing_result,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
            )

        assert response is not None
        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        assert response["error"] == "product_smoke_failed"
        assert "missing start_command" in response["blocker"]

    @pytest.mark.asyncio
    async def test_gate_passes_with_valid_start_command(self, tmp_path: Path) -> None:
        """Valid start_command + runner success → gate returns None."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing = ProductSmokeResult(
            success=True,
            steps=[
                VerificationStep(
                    name="start_command",
                    command="npm run build",
                    exit_code=0,
                    stdout="built",
                    stderr="",
                    duration_seconds=5.0,
                    success=True,
                )
            ],
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_verify:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
            )

        assert response is None
        # Verify the runner was called with the declared params
        call_kwargs = mock_verify.call_args.kwargs
        assert call_kwargs["start_command"] == "npm run build"
        assert call_kwargs["readiness_probe"] is None

    @pytest.mark.asyncio
    async def test_gate_rejects_failing_start_command(self, tmp_path: Path) -> None:
        """Declared start_command fails → gate rejects with stderr."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        failing = ProductSmokeResult(
            success=False,
            steps=[
                VerificationStep(
                    name="start_command",
                    command="npm run build",
                    exit_code=1,
                    stdout="",
                    stderr="Could not find index.html",
                    duration_seconds=2.0,
                    success=False,
                )
            ],
            failure_summary="start_command failed (exit=1)",
            blocker_message="## Deliverable verification FAILED\nindex.html missing",
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=failing,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
            )

        assert response is not None
        assert response["success"] is False
        assert "index.html" in response["blocker"]

    @pytest.mark.asyncio
    async def test_gate_passes_server_mode_with_probe(self, tmp_path: Path) -> None:
        """Both start_command and readiness_probe are forwarded to the runner."""
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing = ProductSmokeResult(
            success=True,
            steps=[
                VerificationStep(
                    name="start_command",
                    command="uvicorn main:app",
                    exit_code=None,
                    stdout="",
                    stderr="",
                    duration_seconds=4.0,
                    success=True,
                ),
                VerificationStep(
                    name="readiness_probe",
                    command="curl -f http://localhost:8000/health",
                    exit_code=0,
                    stdout="OK",
                    stderr="",
                    duration_seconds=0.5,
                    success=True,
                ),
            ],
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_verify:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="uvicorn main:app --port 8000",
                readiness_probe="curl -f http://localhost:8000/health",
            )

        assert response is None
        call_kwargs = mock_verify.call_args.kwargs
        assert call_kwargs["start_command"] == "uvicorn main:app --port 8000"
        assert call_kwargs["readiness_probe"] == "curl -f http://localhost:8000/health"

    @pytest.mark.asyncio
    async def test_gate_rejects_when_no_workspace_state(self) -> None:
        """No project_root → gate rejects completion (P2-2 fix: was None/pass)."""
        task = _make_integration_task()
        state = _make_state(task)
        state.kanban_client._load_workspace_state = Mock(return_value=None)

        response = await _run_product_smoke_gate(
            task=task,
            agent_id="agent-001",
            state=state,
            start_command="npm run build",
            readiness_probe=None,
        )
        assert (
            response is not None
        ), "P2-2 fix: missing workspace state must be a hard rejection, not None"
        assert response["success"] is False
        assert response["error"] == "smoke_gate_unavailable"
        assert "project_root not found" in response["failure_summary"]


class TestReportTaskProgressIntegration:
    """End-to-end: report_task_progress forwards declared commands to the gate."""

    @pytest.mark.asyncio
    async def test_integration_task_completion_runs_gate_with_declared_command(
        self, tmp_path: Path
    ) -> None:
        """
        When an integration task completes with a declared
        start_command, the gate runs with that exact command.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing = ProductSmokeResult(success=True, steps=[])
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_verify:
            await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
            )
            mock_verify.assert_called_once()
            call_kwargs = mock_verify.call_args.kwargs
            assert call_kwargs["start_command"] == "npm run build"

    @pytest.mark.asyncio
    async def test_integration_completion_without_start_command_rejected(
        self, tmp_path: Path
    ) -> None:
        """
        Integration task completes without declaring start_command
        → rejected. Kanban DONE write must NOT happen.
        """
        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        missing = ProductSmokeResult(
            success=False,
            steps=[
                VerificationStep(
                    name="missing_start_command",
                    command="",
                    exit_code=None,
                    stdout="",
                    stderr="missing",
                    duration_seconds=0.0,
                    success=False,
                )
            ],
            failure_summary="integration task missing required start_command",
            blocker_message="## Integration task rejected: missing start_command",
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=missing,
        ):
            response = await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
                # No start_command passed — strict rejection
            )

        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        state.kanban_client.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_integration_task_ignores_start_command(
        self, tmp_path: Path
    ) -> None:
        """
        Implementation tasks do NOT trigger the smoke gate even if
        the caller accidentally passes start_command. Parameter is
        silently ignored for non-integration tasks.
        """
        task = _make_impl_task()
        state = _make_state(task, project_root=str(tmp_path))

        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
        ) as mock_verify:
            await report_task_progress(
                agent_id="agent-001",
                task_id=task.id,
                status="completed",
                progress=100,
                message="done",
                state=state,
                start_command="npm run build",  # ignored on impl tasks
                readiness_probe=None,
            )
            mock_verify.assert_not_called()

    @pytest.mark.asyncio
    async def test_non_integration_task_completes_without_declaration(
        self, tmp_path: Path
    ) -> None:
        """
        Implementation tasks can complete without declaring a
        start_command. The strict requirement only applies to
        integration tasks.
        """
        task = _make_impl_task()
        state = _make_state(task, project_root=str(tmp_path))

        response = await report_task_progress(
            agent_id="agent-001",
            task_id=task.id,
            status="completed",
            progress=100,
            message="done",
            state=state,
        )

        assert response["success"] is True
        state.kanban_client.update_task.assert_called_once()


# ---------------------------------------------------------------------------
# Slice B (#523): verifications list path
# ---------------------------------------------------------------------------


class TestVerificationsPath:
    """``_run_product_smoke_gate`` routes through ``verify_verification_specs``
    when the agent declared a non-empty ``verifications`` list.

    Backward compat is exercised in ``TestProductSmokeGate`` above: a
    completion that passes only ``start_command`` (no ``verifications``)
    continues to use the legacy ``verify_deliverable`` path unchanged.
    """

    @pytest.mark.asyncio
    async def test_verifications_takes_precedence_over_start_command(
        self, tmp_path: Path
    ) -> None:
        """When both fields are present, ``verifications`` wins.

        The legacy ``verify_deliverable`` must not run at all when the
        agent declared ``verifications`` — otherwise we double-run
        commands and conflate two contracts.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with (
            patch(
                "src.integrations.product_smoke.verify_verification_specs",
                new_callable=AsyncMock,
                return_value=passing,
            ) as mock_specs,
            patch(
                "src.integrations.product_smoke.verify_deliverable",
                new_callable=AsyncMock,
            ) as mock_legacy,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="legacy command that must not run",
                readiness_probe=None,
                verifications=[
                    {
                        "signal_id": "o1",
                        "command": "echo ok",
                        "description": "ok",
                    }
                ],
            )

        assert response is None  # passed → no rejection
        mock_specs.assert_awaited_once()
        mock_legacy.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verifications_pass_returns_none(self, tmp_path: Path) -> None:
        """All specs pass → gate returns None (completion proceeds)."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=passing,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "o1", "command": "true", "description": ""}
                ],
            )

        assert response is None

    @pytest.mark.asyncio
    async def test_verifications_fail_returns_structured_rejection(
        self, tmp_path: Path
    ) -> None:
        """Any failure → rejection dict carrying the runner's blocker.

        Slice B acceptance criterion: rejection includes the failing
        signal_id, description, command, exit code, and stderr.  Those
        all live inside the runner's ``blocker_message`` (verified in
        product_smoke tests); the gate is responsible for passing it
        through unchanged.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        failing_blocker = (
            "## Verification FAILED\n\n"
            "Failing verification: `outcome_play` — snake renders\n"
            "Command: `false`\n"
            "Exit code: 1\n"
        )
        failing = VerificationsResult(
            success=False,
            spec_results=[],
            failure_summary="verification 'outcome_play' (snake renders) failed",
            blocker_message=failing_blocker,
        )
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=failing,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {
                        "signal_id": "outcome_play",
                        "command": "false",
                        "description": "snake renders",
                    }
                ],
            )

        assert response is not None
        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        assert response["error"] == "verifications_failed"
        assert response["blocker"] == failing_blocker
        assert "outcome_play" in response["failure_summary"]

    @pytest.mark.asyncio
    async def test_spec_dicts_coerced_to_dataclass(self, tmp_path: Path) -> None:
        """The gate converts JSON dicts to ``VerificationSpec`` instances.

        Agents send dict-shaped payloads through the MCP boundary
        (FastMCP JSON-schemas everything as dicts).  The gate is
        responsible for coercing them into typed ``VerificationSpec``
        records before handing to the runner.  Verify the conversion
        preserves all fields including the optional ones.
        """
        from src.integrations.product_smoke import (
            VerificationSpec,
            VerificationsResult,
        )

        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        captured_specs: list[VerificationSpec] = []

        async def _capture(specs, cwd, **_):
            captured_specs.extend(specs)
            return VerificationsResult(success=True, spec_results=[])

        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            side_effect=_capture,
        ):
            await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {
                        "signal_id": "outcome_render",
                        "command": "npm run dev",
                        "description": "renders snake",
                        "readiness_probe": "curl -f http://localhost:5173",
                    },
                    {
                        "signal_id": "outcome_score",
                        "command": "curl -fs http://localhost:8765/score",
                    },
                ],
            )

        assert len(captured_specs) == 2
        assert isinstance(captured_specs[0], VerificationSpec)
        assert captured_specs[0].signal_id == "outcome_render"
        assert captured_specs[0].command == "npm run dev"
        assert captured_specs[0].description == "renders snake"
        assert captured_specs[0].readiness_probe == "curl -f http://localhost:5173"
        # Second spec exercises the all-defaults path
        assert captured_specs[1].signal_id == "outcome_score"
        assert captured_specs[1].description == ""
        assert captured_specs[1].readiness_probe is None

    @pytest.mark.asyncio
    async def test_empty_verifications_falls_through_to_legacy_path(
        self, tmp_path: Path
    ) -> None:
        """``verifications=[]`` is treated as absent — legacy path runs.

        Distinguishes "agent explicitly opted out of new path" from
        "agent provided a non-empty list."  Empty list = no specs
        declared = legacy start_command path runs with its usual
        missing-declaration rejection if start_command is also absent.
        """
        from src.integrations.product_smoke import ProductSmokeResult

        task = _make_integration_task()
        state = _make_state(task, project_root=str(tmp_path))

        passing_legacy = ProductSmokeResult(
            success=True,
            steps=[
                VerificationStep(
                    name="start_command",
                    command="npm run build",
                    exit_code=0,
                    stdout="",
                    stderr="",
                    duration_seconds=1.0,
                    success=True,
                )
            ],
        )
        with patch(
            "src.integrations.product_smoke.verify_deliverable",
            new_callable=AsyncMock,
            return_value=passing_legacy,
        ) as mock_legacy:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
                verifications=[],
            )

        assert response is None
        mock_legacy.assert_awaited_once()
