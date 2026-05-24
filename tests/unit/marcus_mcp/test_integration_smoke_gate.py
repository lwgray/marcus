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
    async def test_coverage_satisfied_runs_specs(self, tmp_path: Path) -> None:
        """When all required outcomes are covered, the gate runs the runner.

        Coverage check is structural — when every in-scope outcome id
        has at least one matching ``signal_id`` in the declared list,
        the gate hands off to ``verify_verification_specs`` as normal.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        # source_context declares two required outcomes
        task.source_context = {
            "in_scope_outcome_ids": ["outcome_play", "outcome_score"]
        }
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_run:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "outcome_play", "command": "true"},
                    {"signal_id": "outcome_score", "command": "true"},
                ],
            )

        assert response is None
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_coverage_missing_rejects_before_running_subprocess(
        self, tmp_path: Path
    ) -> None:
        """Missing coverage → rejection BEFORE any subprocess runs.

        Slice B (#523) acceptance criterion: every required in-scope
        outcome must be matched by a declared ``signal_id``.  The
        rejection's ``failure_summary`` and ``blocker`` name the
        missing outcome IDs so the agent fixes their next call rather
        than guessing.
        """
        task = _make_integration_task()
        task.source_context = {
            "in_scope_outcome_ids": ["outcome_play", "outcome_score"]
        }
        state = _make_state(task, project_root=str(tmp_path))

        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
        ) as mock_run:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    # Only outcome_play covered — outcome_score is missing
                    {"signal_id": "outcome_play", "command": "true"},
                ],
            )

        # Rejected without running any spec.
        mock_run.assert_not_awaited()
        assert response is not None
        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        assert response["error"] == "verifications_missing_coverage"
        assert response["missing_outcome_ids"] == ["outcome_score"]
        assert set(response["declared_signal_ids"]) == {"outcome_play"}
        assert "outcome_score" in response["failure_summary"]
        # Blocker names the missing outcome plus the required + declared
        # sets so the agent can diff and fix in one pass.
        blocker = response["blocker"]
        assert "outcome_score" in blocker
        assert "outcome_play" in blocker
        assert "Missing coverage" in blocker

    @pytest.mark.asyncio
    async def test_all_outcomes_missing_lists_them_all(self, tmp_path: Path) -> None:
        """Empty ``verifications`` payloads (no signal_ids) → reject all."""
        task = _make_integration_task()
        task.source_context = {"in_scope_outcome_ids": ["o1", "o2", "o3"]}
        state = _make_state(task, project_root=str(tmp_path))

        # Each verification has empty signal_id — none match the required
        # set, so all three required outcomes are missing.
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
        ) as mock_run:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[{"signal_id": "", "command": "true"}],
            )

        mock_run.assert_not_awaited()
        assert response is not None
        assert response["missing_outcome_ids"] == ["o1", "o2", "o3"]

    @pytest.mark.asyncio
    async def test_no_required_outcomes_skips_coverage_check(
        self, tmp_path: Path
    ) -> None:
        """Legacy integration tasks (no source_context) bypass coverage.

        Pre-Slice-B integration tasks were created with
        ``source_context=None``.  Coverage check must NOT fire on
        them — they are valid via the legacy contract (any verifications
        the agent declares are sufficient).
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        assert task.source_context is None  # baseline
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_run:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "arbitrary", "command": "true"},
                ],
            )

        assert response is None
        mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_required_list_is_satisfied(self, tmp_path: Path) -> None:
        """``in_scope_outcome_ids=[]`` → no required coverage, run specs.

        Distinguishes "outcomes wired, none in scope" from "outcomes
        not wired at all."  Both bypass the missing-coverage rejection
        but the former is the explicit-empty case.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        task.source_context = {"in_scope_outcome_ids": []}
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_run:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "anything", "command": "true"},
                ],
            )

        assert response is None
        mock_run.assert_awaited_once()

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


class TestVerificationsRequiredWhenOutcomesDeclared:
    """Escape-hatch closure (Kaia review on PR #525).

    When the integration task carries declared in-scope outcomes on
    ``source_context["in_scope_outcome_ids"]``, the agent MUST use
    the new ``verifications`` path.  ``verifications=None`` or ``[]``
    plus a legacy ``start_command`` previously slipped through and
    bypassed the coverage check — the exact failure mode Slice B
    targets.  The escape-hatch check fires BEFORE either branch
    decision so neither the verifications runner nor the legacy
    ``verify_deliverable`` executes.

    Tasks that have NO declared outcomes (``source_context is None``
    or ``in_scope_outcome_ids`` empty/missing/malformed) are unaffected
    — backward compat preserved.
    """

    @pytest.mark.asyncio
    async def test_outcomes_declared_no_verifications_rejects(
        self, tmp_path: Path
    ) -> None:
        """Outcomes on task + ``verifications=None`` → rejection BEFORE legacy.

        The snake-game class of failure: agent declares
        ``start_command="python -m src.main"`` (exits 0) without
        ``verifications``.  Pre-fix this slipped through.  Now rejected.
        """
        task = _make_integration_task()
        task.source_context = {
            "in_scope_outcome_ids": ["outcome_play", "outcome_score"]
        }
        state = _make_state(task, project_root=str(tmp_path))

        with (
            patch(
                "src.integrations.product_smoke.verify_verification_specs",
                new_callable=AsyncMock,
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
                start_command="python -m src.main",
                readiness_probe=None,
                verifications=None,
            )

        # Neither path ran — escape hatch closed BEFORE branch decision.
        mock_specs.assert_not_awaited()
        mock_legacy.assert_not_awaited()
        assert response is not None
        assert response["success"] is False
        assert response["status"] == "smoke_verification_failed"
        assert response["error"] == "verifications_required_but_missing"
        assert response["missing_outcome_ids"] == ["outcome_play", "outcome_score"]
        assert response["required_outcome_ids"] == ["outcome_play", "outcome_score"]
        assert response["declared_signal_ids"] == []
        # Blocker names the outcomes so the agent knows what to add.
        assert "outcome_play" in response["blocker"]
        assert "outcome_score" in response["blocker"]

    @pytest.mark.asyncio
    async def test_outcomes_declared_empty_verifications_rejects(
        self, tmp_path: Path
    ) -> None:
        """``verifications=[]`` is treated the same as ``None`` for the check.

        Both falsy; both bypass the verifications branch.  The
        escape-hatch check fires above the branch decision and
        catches them uniformly.
        """
        task = _make_integration_task()
        task.source_context = {"in_scope_outcome_ids": ["outcome_play"]}
        state = _make_state(task, project_root=str(tmp_path))

        with (
            patch(
                "src.integrations.product_smoke.verify_verification_specs",
                new_callable=AsyncMock,
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
                start_command="npm run build",
                readiness_probe=None,
                verifications=[],
            )

        mock_specs.assert_not_awaited()
        mock_legacy.assert_not_awaited()
        assert response is not None
        assert response["error"] == "verifications_required_but_missing"

    @pytest.mark.asyncio
    async def test_outcomes_declared_with_verifications_proceeds(
        self, tmp_path: Path
    ) -> None:
        """Outcomes + matching verifications → normal flow runs.

        Sanity check that the escape-hatch closure does not
        accidentally block the happy path.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task()
        task.source_context = {"in_scope_outcome_ids": ["outcome_play"]}
        state = _make_state(task, project_root=str(tmp_path))

        passing = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=passing,
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[{"signal_id": "outcome_play", "command": "true"}],
            )

        assert response is None
        mock_specs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_legacy_task_without_outcomes_bypasses_check(
        self, tmp_path: Path
    ) -> None:
        """``source_context=None`` → escape-hatch check does not fire.

        Backward compat: pre-Slice-B integration tasks were created
        without outcomes.  They must continue to work with the
        legacy ``start_command`` contract.
        """
        from src.integrations.product_smoke import ProductSmokeResult

        task = _make_integration_task()
        assert task.source_context is None
        state = _make_state(task, project_root=str(tmp_path))

        passing = ProductSmokeResult(
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
            return_value=passing,
        ) as mock_legacy:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
                verifications=None,
            )

        assert response is None
        mock_legacy.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_malformed_source_context_treated_as_absent(
        self, tmp_path: Path
    ) -> None:
        """Non-list ``in_scope_outcome_ids`` is treated as missing.

        Defensive ``isinstance`` guard: kanban providers that
        rehydrate ``source_context`` from JSON could in theory return
        a string here.  ``list("outcome_play")`` would silently
        iterate characters and corrupt the required set.  Instead
        we treat malformed values as "wiring absent" and let the
        legacy path run.
        """
        from src.integrations.product_smoke import ProductSmokeResult

        task = _make_integration_task()
        # Malformed: string instead of list.
        task.source_context = {"in_scope_outcome_ids": "outcome_play"}
        state = _make_state(task, project_root=str(tmp_path))

        passing = ProductSmokeResult(
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
            return_value=passing,
        ) as mock_legacy:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command="npm run build",
                readiness_probe=None,
                verifications=None,
            )

        # Escape-hatch did not fire (string treated as absent).
        # Legacy path ran successfully.
        assert response is None
        mock_legacy.assert_awaited_once()


def _make_integration_task_with_contract(
    *,
    in_scope_outcome_ids: list[str],
    contract_verifications: list[dict] | None,
    task_id: str = "int-soft",
) -> Task:
    """Build an integration task carrying contract verifications.

    ``contract_verifications=None`` means the field is absent from
    source_context (Phase A generator never ran). ``[]`` means
    generation ran but produced nothing (Codex P2 case). Both are
    valid input states for the soft-rollout test cases below.
    """
    src_ctx: dict = {"in_scope_outcome_ids": in_scope_outcome_ids}
    if contract_verifications is not None:
        src_ctx["contract_verifications"] = contract_verifications
    return Task(
        id=task_id,
        name="Integration verification for Soft-Rollout Project",
        description="Build and verify",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        assigned_to="agent-001",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        labels=["integration", "verification", "type:integration"],
        source_context=src_ctx,
    )


class TestPhaseBSoftRollout:
    """Phase B (#636): prefer Marcus-authored contract verifications;
    fall back to agent-supplied on absence, empty, incomplete coverage,
    or any failure. Fallback is the safety net while the LLM-based
    generator (PR #642 Phase A) is being hardened.
    """

    @pytest.mark.asyncio
    async def test_contract_accept_skips_agent_path(self, tmp_path: Path) -> None:
        """Contract present with full coverage and all pass ->
        accept via contract; the agent-supplied path is not run.
        """
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1"],
            contract_verifications=[
                {
                    "signal_id": "o1",
                    "command": "true",
                    "description": "demonstrates o1",
                }
            ],
        )
        state = _make_state(task, project_root=str(tmp_path))

        contract_pass = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=contract_pass,
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                # Agent supplied a parallel set — but contract wins,
                # so this list is never consulted.
                verifications=[
                    {"signal_id": "o1", "command": "false", "description": "x"}
                ],
            )

        assert response is None
        # Called exactly once — with the contract specs, not the
        # agent-supplied ones.
        mock_specs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_contract_failure_falls_back_to_agent_supplied(
        self, tmp_path: Path
    ) -> None:
        """Contract verification fails -> WARNING logged, fall through
        to agent-supplied path. If agent's verifications pass, the
        completion is accepted (legacy gameability preserved as the
        fallback safety net — strict M3 will close this later)."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1"],
            contract_verifications=[
                {"signal_id": "o1", "command": "false", "description": "fails"}
            ],
        )
        state = _make_state(task, project_root=str(tmp_path))

        # First call (contract) fails; second call (agent) passes.
        contract_fail = VerificationsResult(
            success=False,
            spec_results=[],
            failure_summary="contract command failed",
        )
        agent_pass = VerificationsResult(success=True, spec_results=[])

        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            side_effect=[contract_fail, agent_pass],
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "o1", "command": "true", "description": "ok"}
                ],
            )

        # Accepted via the fallback.
        assert response is None
        # Verifier was called twice: once for contract, once for agent.
        assert mock_specs.await_count == 2

    @pytest.mark.asyncio
    async def test_contract_incomplete_coverage_falls_back_to_agent(
        self, tmp_path: Path
    ) -> None:
        """Contract missing coverage for one in-scope outcome ->
        WARNING, fall through to agent-supplied. Don't partial-verify."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1", "o2"],
            # Contract only covers o1; o2 is missing
            contract_verifications=[
                {"signal_id": "o1", "command": "true", "description": "ok"}
            ],
        )
        state = _make_state(task, project_root=str(tmp_path))

        agent_pass = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=agent_pass,
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "o1", "command": "true", "description": "ok"},
                    {"signal_id": "o2", "command": "true", "description": "ok"},
                ],
            )

        assert response is None
        # Only the agent-supplied call ran; contract was skipped
        # entirely because coverage was incomplete.
        mock_specs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_contract_empty_list_falls_back_to_agent(
        self, tmp_path: Path
    ) -> None:
        """Contract is ``[]`` (Codex P2 case — generation ran but the
        LLM declined every outcome) -> WARNING, fall through to agent-
        supplied. Empty list IS distinguishable from absent (semantics
        from Codex P2 fix on PR #642)."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1"],
            contract_verifications=[],  # empty, not None
        )
        state = _make_state(task, project_root=str(tmp_path))

        agent_pass = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=agent_pass,
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "o1", "command": "true", "description": "ok"}
                ],
            )

        assert response is None
        # Agent-supplied was the only path that ran.
        mock_specs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_contract_absent_uses_legacy_agent_path(self, tmp_path: Path) -> None:
        """Contract field absent (Phase A never ran for this project) ->
        existing agent-supplied behavior unchanged. This is the
        backwards-compatible path for projects created before Phase A
        shipped."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1"],
            contract_verifications=None,  # field absent
        )
        state = _make_state(task, project_root=str(tmp_path))

        agent_pass = VerificationsResult(success=True, spec_results=[])
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=agent_pass,
        ) as mock_specs:
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=[
                    {"signal_id": "o1", "command": "true", "description": "ok"}
                ],
            )

        assert response is None
        mock_specs.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_contract_failure_with_no_agent_supplied_rejects(
        self, tmp_path: Path
    ) -> None:
        """Contract fails AND agent did not supply -> the existing
        escape-hatch rejection fires (in-scope outcomes + no
        verifications). Soft rollout does not bypass the existing
        gate when neither path can verify."""
        from src.integrations.product_smoke import VerificationsResult

        task = _make_integration_task_with_contract(
            in_scope_outcome_ids=["o1"],
            contract_verifications=[
                {"signal_id": "o1", "command": "false", "description": "fails"}
            ],
        )
        state = _make_state(task, project_root=str(tmp_path))

        contract_fail = VerificationsResult(
            success=False,
            spec_results=[],
            failure_summary="contract command failed",
        )
        with patch(
            "src.integrations.product_smoke.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=contract_fail,
        ):
            response = await _run_product_smoke_gate(
                task=task,
                agent_id="agent-001",
                state=state,
                start_command=None,
                readiness_probe=None,
                verifications=None,  # agent didn't supply
            )

        # Escape-hatch fires: in_scope outcomes set + no agent
        # verifications. The existing Slice B rejection path runs
        # AFTER the contract path falls through.
        assert response is not None
        assert response.get("success") is False
        assert response.get("error") == "verifications_required_but_missing"
