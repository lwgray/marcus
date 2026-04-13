"""Unit tests for the deliverable verification runner.

Covers ``verify_deliverable`` and its two execution modes:

- **One-shot**: no readiness_probe → run start_command, wait for exit,
  require exit 0 within the timeout.
- **Server+probe**: with readiness_probe → start command in background,
  poll probe once per second, pass when probe returns exit 0.

Regression tests for the v71 bug class: a declared start_command that
fails (missing file, bad import, etc.) must produce a structured
failure with the real stderr in the blocker message.

The runner is deterministic subprocess orchestration, so tests mock
the subprocess helpers at the boundary and verify the runner's
decisions (what it runs, in what order, how it handles timeouts and
crashes) rather than actually spawning shells.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.product_smoke import (
    ProductSmokeResult,
    VerificationStep,
    _render_failure_blocker,
    _render_missing_blocker,
    verify_deliverable,
)

pytestmark = pytest.mark.unit


def _make_step(
    name: str,
    command: str = "fake",
    success: bool = True,
    exit_code: int = 0,
    stderr: str = "",
    stdout: str = "",
) -> VerificationStep:
    """Build a VerificationStep for test setup."""
    return VerificationStep(
        name=name,
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=0.0,
        success=success,
    )


# ---------------------------------------------------------------------------
# Missing start_command rejection
# ---------------------------------------------------------------------------


class TestMissingStartCommand:
    """The runner strictly rejects missing/empty start_command."""

    @pytest.mark.asyncio
    async def test_none_start_command_returns_rejection(self, tmp_path: Path) -> None:
        """start_command=None → structured rejection, not an exception."""
        result = await verify_deliverable(
            start_command=None, readiness_probe=None, cwd=tmp_path
        )
        assert result.success is False
        assert len(result.steps) == 1
        assert result.steps[0].name == "missing_start_command"
        assert result.failure_summary is not None
        assert "missing required start_command" in result.failure_summary
        assert result.blocker_message is not None
        assert "missing start_command" in result.blocker_message

    @pytest.mark.asyncio
    async def test_empty_string_start_command_returns_rejection(
        self, tmp_path: Path
    ) -> None:
        """Empty string is treated the same as None."""
        result = await verify_deliverable(
            start_command="", readiness_probe=None, cwd=tmp_path
        )
        assert result.success is False
        assert result.steps[0].name == "missing_start_command"

    @pytest.mark.asyncio
    async def test_whitespace_only_start_command_returns_rejection(
        self, tmp_path: Path
    ) -> None:
        """Whitespace-only is also rejected."""
        result = await verify_deliverable(
            start_command="   \t  ", readiness_probe=None, cwd=tmp_path
        )
        assert result.success is False
        assert result.steps[0].name == "missing_start_command"


# ---------------------------------------------------------------------------
# One-shot mode (no readiness_probe)
# ---------------------------------------------------------------------------


class TestOneShotMode:
    """One-shot commands: run, wait for exit, require exit 0."""

    @pytest.mark.asyncio
    async def test_one_shot_success(self, tmp_path: Path) -> None:
        """Command exits 0 → success=True with one step."""
        with patch(
            "src.integrations.product_smoke._run_one_shot",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = _make_step(
                name="start_command", command="npm run build", success=True
            )
            result = await verify_deliverable(
                start_command="npm run build",
                readiness_probe=None,
                cwd=tmp_path,
            )

        assert result.success is True
        assert len(result.steps) == 1
        assert result.steps[0].name == "start_command"
        assert result.steps[0].success is True
        assert result.failure_summary is None
        assert result.blocker_message is None

    @pytest.mark.asyncio
    async def test_one_shot_failure_surfaces_stderr(self, tmp_path: Path) -> None:
        """Command exits non-zero → failure with stderr in blocker."""
        with patch(
            "src.integrations.product_smoke._run_one_shot",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = _make_step(
                name="start_command",
                command="npm run build",
                success=False,
                exit_code=1,
                stderr="Could not find a required file.\n  Name: index.html",
            )
            result = await verify_deliverable(
                start_command="npm run build",
                readiness_probe=None,
                cwd=tmp_path,
            )

        assert result.success is False
        assert result.failure_summary is not None
        assert "start_command failed" in result.failure_summary
        assert result.blocker_message is not None
        assert "index.html" in result.blocker_message
        assert "Could not find a required file" in result.blocker_message

    @pytest.mark.asyncio
    async def test_one_shot_v71_regression(self, tmp_path: Path) -> None:
        """
        REGRESSION for dashboard-v71.

        A React project missing public/index.html must fail
        verification when the agent declares `npm run build` as
        their start_command. This is the exact bug shape that
        shipped broken in v71 because no one ran `npm run build`
        before marking the task complete.
        """
        with patch(
            "src.integrations.product_smoke._run_one_shot",
            new_callable=AsyncMock,
        ) as mock_run:
            # Simulate the real react-scripts error
            mock_run.return_value = _make_step(
                name="start_command",
                command="npm run build",
                success=False,
                exit_code=1,
                stderr=(
                    "Failed to compile.\n\n"
                    "Could not find a required file.\n"
                    "  Name: index.html\n"
                    f"  Searched in: {tmp_path}/public"
                ),
            )
            result = await verify_deliverable(
                start_command="npm run build",
                readiness_probe=None,
                cwd=tmp_path,
            )

        assert result.success is False, (
            "v71 regression: missing public/index.html must fail "
            "declared start_command"
        )
        assert "index.html" in (result.blocker_message or "")


# ---------------------------------------------------------------------------
# Server+probe mode (with readiness_probe)
# ---------------------------------------------------------------------------


class TestServerWithProbeMode:
    """Server mode: start in background, poll probe until ready."""

    @pytest.mark.asyncio
    async def test_server_with_probe_success(self, tmp_path: Path) -> None:
        """Server starts, probe passes → overall success."""
        with patch(
            "src.integrations.product_smoke._run_server_with_probe",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_step(
                    name="start_command",
                    command="uvicorn main:app",
                    success=True,
                ),
                _make_step(
                    name="readiness_probe",
                    command="curl -f http://localhost:8000/health",
                    success=True,
                ),
            ]
            result = await verify_deliverable(
                start_command="uvicorn main:app --port 8000",
                readiness_probe="curl -f http://localhost:8000/health",
                cwd=tmp_path,
            )

        assert result.success is True
        assert len(result.steps) == 2
        assert result.steps[0].name == "start_command"
        assert result.steps[1].name == "readiness_probe"
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_with_probe_fails_when_probe_never_passes(
        self, tmp_path: Path
    ) -> None:
        """
        Server runs but probe never returns exit 0 → failure.
        This catches the hung-server-no-error case: server binds
        port, deadlocks on init, looks alive but can't serve.
        """
        with patch(
            "src.integrations.product_smoke._run_server_with_probe",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_step(
                    name="start_command",
                    command="uvicorn main:app",
                    success=True,
                ),
                _make_step(
                    name="readiness_probe",
                    command="curl -f http://localhost:8000/health",
                    success=False,
                    stderr="Readiness probe failed after 15 attempts. Last exit=7.",
                ),
            ]
            result = await verify_deliverable(
                start_command="uvicorn main:app --port 8000",
                readiness_probe="curl -f http://localhost:8000/health",
                cwd=tmp_path,
            )

        assert result.success is False
        assert result.failure_summary is not None
        assert "readiness_probe failed" in result.failure_summary
        assert result.blocker_message is not None
        assert "readiness probe never returned exit 0" in result.blocker_message

    @pytest.mark.asyncio
    async def test_server_with_probe_fails_when_server_crashes(
        self, tmp_path: Path
    ) -> None:
        """Server exits non-zero before readiness → failure."""
        with patch(
            "src.integrations.product_smoke._run_server_with_probe",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = [
                _make_step(
                    name="start_command",
                    command="uvicorn main:app",
                    success=False,
                    exit_code=1,
                    stderr="ImportError: No module named 'main'",
                ),
                _make_step(
                    name="readiness_probe",
                    command="curl -f http://localhost:8000/health",
                    success=False,
                    stderr="Server exited before readiness",
                ),
            ]
            result = await verify_deliverable(
                start_command="uvicorn main:app --port 8000",
                readiness_probe="curl -f http://localhost:8000/health",
                cwd=tmp_path,
            )

        assert result.success is False
        assert result.failure_summary is not None
        assert "start_command failed" in result.failure_summary


# ---------------------------------------------------------------------------
# Result rendering
# ---------------------------------------------------------------------------


class TestBlockerMessages:
    """Blocker messages render actionable info for agents."""

    def test_missing_blocker_explains_how_to_declare(self) -> None:
        msg = _render_missing_blocker()
        assert "missing start_command" in msg
        assert "report_task_progress" in msg
        assert "npm run build" in msg  # one-shot example
        assert "uvicorn" in msg  # server example
        assert "readiness_probe" in msg

    def test_failure_blocker_includes_command_and_stderr(self, tmp_path: Path) -> None:
        failed = _make_step(
            name="start_command",
            command="npm run build",
            success=False,
            exit_code=1,
            stderr="ENOENT: index.html",
        )
        msg = _render_failure_blocker(failed, [failed])
        assert "FAILED" in msg
        assert "npm run build" in msg
        assert "ENOENT" in msg
        assert "start_command did not exit 0" in msg

    def test_failure_blocker_for_probe_failure_names_probe_mode(self) -> None:
        failed = _make_step(
            name="readiness_probe",
            command="curl -f http://localhost:8000/health",
            success=False,
            stderr="Probe never passed",
        )
        msg = _render_failure_blocker(failed, [failed])
        assert "readiness probe never returned exit 0" in msg


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    """``ProductSmokeResult.to_dict`` produces JSON-ready output."""

    def test_to_dict_has_required_keys(self) -> None:
        result = ProductSmokeResult(
            success=False,
            steps=[_make_step("start_command", success=False, stderr="bad")],
            failure_summary="start_command failed",
            blocker_message="fix it",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["failure_summary"] == "start_command failed"
        assert len(d["steps"]) == 1
        assert d["steps"][0]["name"] == "start_command"
        assert d["steps"][0]["success"] is False

    def test_to_dict_truncates_long_outputs(self) -> None:
        long_stderr = "x" * 10000
        result = ProductSmokeResult(
            success=False,
            steps=[_make_step("start_command", success=False, stderr=long_stderr)],
            failure_summary="x",
            blocker_message="x",
        )
        d = result.to_dict()
        # Serialized stderr tail is limited to 1024 chars
        assert len(d["steps"][0]["stderr_tail"]) <= 1024
