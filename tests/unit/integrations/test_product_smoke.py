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

import asyncio
import os
import signal
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


# ---------------------------------------------------------------------------
# Real-shell execution regression tests (#125)
# ---------------------------------------------------------------------------


class TestRunOneShotRealShell:
    """
    ``_run_one_shot`` runs the agent's command through ``/bin/sh -c``,
    not through ``shlex.split`` + ``create_subprocess_exec``.

    Regression for the dashboard-v73 vacuous-pass class. Pre-#125 the
    runner used exec, and ``cd /tmp && true`` parsed to
    ``['cd', '/tmp', '&&', 'true']``. On macOS, ``/usr/bin/cd`` is a
    real POSIX-conformance binary that returns exit 0 for any args,
    so the smoke gate silently false-passed. v73's
    ``cd worktrees/agent_unicorn_1 && npm test`` was reported as
    PASSED in 0.0s and we believed it; vitest never ran through
    Marcus.

    These tests use real subprocess invocations against shell
    builtins so they catch any future regression to exec semantics.
    """

    @pytest.mark.asyncio
    async def test_shell_chain_executes_both_commands(self, tmp_path: Path) -> None:
        """Shell chain with && must run BOTH halves and reflect their result."""
        from src.integrations.product_smoke import _run_one_shot

        marker = tmp_path / "marker.txt"
        step = await _run_one_shot(
            command=f"cd {tmp_path} && touch marker.txt",
            cwd=tmp_path,
            timeout_seconds=10,
        )

        assert step.success is True
        assert step.exit_code == 0
        assert marker.exists(), (
            "Shell chain second-half (touch) must have executed. If "
            "this fails, the runner has regressed to exec semantics "
            "and the && was treated as a literal argument."
        )

    @pytest.mark.asyncio
    async def test_shell_chain_short_circuits_on_first_failure(
        self, tmp_path: Path
    ) -> None:
        """Shell && must short-circuit: first failure prevents second from running."""
        from src.integrations.product_smoke import _run_one_shot

        marker = tmp_path / "should_not_exist.txt"
        step = await _run_one_shot(
            command=f"false && touch {marker}",
            cwd=tmp_path,
            timeout_seconds=10,
        )

        assert step.success is False
        assert step.exit_code != 0
        assert not marker.exists(), (
            "Shell && must short-circuit. If the marker exists, the "
            "second command ran despite the first failing — runner "
            "has regressed."
        )

    @pytest.mark.asyncio
    async def test_v73_vacuous_pass_mode_is_dead(self, tmp_path: Path) -> None:
        """
        REGRESSION for dashboard-v73 specifically.

        v73 declared start_command='cd worktrees/agent_unicorn_1 && npm test'.
        Under exec semantics, this ran /usr/bin/cd with literal args
        and returned exit 0 in 0ms — vitest never ran. Under shell
        semantics, this ACTUALLY chdirs and runs npm test, so a
        broken target would actually fail.

        Test it with a chain that SHOULD fail under shell semantics
        but DID pass under exec: cd to a nonexistent path, then run
        a command that would have succeeded. Under shell, cd fails
        and the chain short-circuits → exit non-zero → success=False.
        Under exec, /usr/bin/cd swallows the bad path and exit 0 →
        success=True (the bug). Asserting failure here pins the fix.
        """
        from src.integrations.product_smoke import _run_one_shot

        nonexistent = tmp_path / "definitely_does_not_exist"
        step = await _run_one_shot(
            command=f"cd {nonexistent} && true",
            cwd=tmp_path,
            timeout_seconds=10,
        )

        assert step.success is False, (
            "v73 regression: cd to nonexistent path must FAIL under "
            "shell semantics. If this passes, /usr/bin/cd is "
            "swallowing the bad path and the runner has regressed "
            "to exec semantics."
        )
        assert step.exit_code != 0

    @pytest.mark.asyncio
    async def test_simple_single_binary_still_works(self, tmp_path: Path) -> None:
        """Plain single-binary commands (the common case) must still work."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="true",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is True
        assert step.exit_code == 0

    @pytest.mark.asyncio
    async def test_command_with_args_still_works(self, tmp_path: Path) -> None:
        """Single-binary commands with args must still work."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="echo hello world",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is True
        assert "hello world" in step.stdout

    @pytest.mark.asyncio
    async def test_failing_binary_reports_nonzero_exit(self, tmp_path: Path) -> None:
        """Single-binary failures must propagate exit code."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="false",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is False
        assert step.exit_code != 0

    @pytest.mark.asyncio
    async def test_empty_command_rejected(self, tmp_path: Path) -> None:
        """Empty/whitespace command is rejected without subprocess."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="   \t  ",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is False
        assert "empty" in step.stderr.lower()

    @pytest.mark.asyncio
    async def test_pipe_works(self, tmp_path: Path) -> None:
        """Shell pipes (|) must work — used in many real-world probes."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="echo abc | grep abc",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is True
        assert step.exit_code == 0

    @pytest.mark.asyncio
    async def test_or_operator_works(self, tmp_path: Path) -> None:
        """Shell || must work — common in probe-with-fallback patterns."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="false || true",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is True
        assert step.exit_code == 0

    @pytest.mark.asyncio
    async def test_subshell_substitution_works(self, tmp_path: Path) -> None:
        """$(...) command substitution must work."""
        from src.integrations.product_smoke import _run_one_shot

        step = await _run_one_shot(
            command="echo $(echo nested)",
            cwd=tmp_path,
            timeout_seconds=10,
        )
        assert step.success is True
        assert "nested" in step.stdout


class TestKillProcessReapsDescendantTree:
    """
    ``_kill_process`` must reap the entire descendant tree of the
    spawned shell, not just the shell PID.

    Codex P1 on PR #352 caught this. Under
    ``create_subprocess_shell`` with shell chains like
    ``"sleep 60 && echo done"``, the shell stays as parent and the
    sleep is a child. Naive ``proc.terminate()`` only signals the
    shell, leaving the sleep alive — port stays bound, server keeps
    running, subsequent verifications fail. The fix is
    ``start_new_session=True`` + ``os.killpg`` to signal the entire
    process group at once.

    Empirically reproduced and verified on macOS during the PR #352
    review cycle.
    """

    @pytest.mark.asyncio
    async def test_chain_descendant_killed_by_runner_timeout(
        self, tmp_path: Path
    ) -> None:
        """
        REGRESSION: a chained command's child process is killed by
        the one-shot timeout path.

        Spawns ``sleep 60 && echo done`` via ``_run_one_shot`` with
        a 1-second timeout. After the timeout fires and
        ``_kill_process`` runs, asserts that the original sleep
        child is gone (not leaked).
        """
        import psutil

        from src.integrations.product_smoke import _run_one_shot

        # We need to capture the descendant PIDs BEFORE the timeout
        # fires. Easiest way: spawn a task that polls psutil for the
        # children, then await the runner.
        captured_pids: list[int] = []

        async def capture_children_after_spawn() -> None:
            # Wait for the process to actually start
            await asyncio.sleep(0.4)
            # Find the sleep process by walking from the test pid
            me = psutil.Process(os.getpid())
            for desc in me.children(recursive=True):
                try:
                    cmd = " ".join(desc.cmdline())
                    if "sleep 60" in cmd:
                        captured_pids.append(desc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        capture_task = asyncio.create_task(capture_children_after_spawn())
        step = await _run_one_shot(
            command="sleep 60 && echo done",
            cwd=tmp_path,
            timeout_seconds=1.0,
        )
        await capture_task

        assert step.success is False
        assert "Timed out" in step.stderr
        assert captured_pids, (
            "Test setup error: did not capture any sleep PID before "
            "timeout fired. Increase the spawn-detect delay."
        )

        # Wait briefly for OS to clean up
        await asyncio.sleep(0.3)

        # Every captured PID must now be dead (or at least not running)
        leaked = []
        for pid in captured_pids:
            try:
                p = psutil.Process(pid)
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    leaked.append(pid)
            except psutil.NoSuchProcess:
                pass

        # Cleanup any leaks before failing so we don't pollute the
        # process table on regression
        for pid in leaked:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        assert not leaked, (
            f"Codex P1 regression: descendant sleep PIDs {leaked} "
            f"survived _kill_process. The runner is leaking children."
        )


class TestRunProbeRealShell:
    """``_run_probe`` uses the same shell execution model as one-shot."""

    @pytest.mark.asyncio
    async def test_probe_supports_shell_pipes(self, tmp_path: Path) -> None:
        """Probe commands must support the same shell features as start_command."""
        from src.integrations.product_smoke import _run_probe

        exit_code, stdout, _ = await _run_probe("echo ready | grep ready", tmp_path)
        assert exit_code == 0
        assert "ready" in stdout

    @pytest.mark.asyncio
    async def test_probe_failure_propagates(self, tmp_path: Path) -> None:
        """Failed probe must return non-zero."""
        from src.integrations.product_smoke import _run_probe

        exit_code, _, _ = await _run_probe("false", tmp_path)
        assert exit_code != 0

    @pytest.mark.asyncio
    async def test_empty_probe_rejected(self, tmp_path: Path) -> None:
        """Empty/whitespace probe is rejected without subprocess."""
        from src.integrations.product_smoke import _run_probe

        exit_code, _, stderr = await _run_probe("   ", tmp_path)
        assert exit_code == -1
        assert "empty" in stderr.lower()
