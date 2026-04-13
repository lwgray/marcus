"""
Marcus-side deliverable verification — agent-declared start command.

Deterministic, subprocess-based verification that the assembled
deliverable actually starts and works. Runs AFTER the integration
verification agent marks its task complete — machine checks beat
agent self-reports when they conflict.

Design
------
The previous version of this module auto-detected software stacks
(Node, Python, Go, Rust, Java) and ran canonical build commands per
stack. That baked software-stack assumptions into Marcus and duplicated
PR #337's ``_validate_runtime`` layer (both ran pytest against the same
Python code). Dashboard-v71 taught us that "tests pass" is the wrong
check — the right check is "does the thing actually start and serve
its purpose."

This version removes auto-detection entirely. The integration agent
declares how to start their deliverable as part of ``report_task_progress``
when marking the task complete. Marcus enforces that the declared command
exits 0. The agent owns stack knowledge; Marcus owns enforcement.

The contract
------------
Integration verification tasks must declare a ``start_command`` on
completion. Optionally, they may also declare a ``readiness_probe``
for long-running servers.

**Mode 1 — one-shot (no readiness_probe):**
    Marcus runs ``start_command`` with a 60s timeout. Pass requires
    exit code 0. Timeout or non-zero exit is a failure. Examples:

    - ``npm run build``
    - ``python -m mypackage --help``
    - ``tsc --noEmit``
    - ``go build ./...``

**Mode 2 — server+probe (with readiness_probe):**
    Marcus starts ``start_command`` in the background, then polls
    ``readiness_probe`` once per second for up to 15 seconds. Pass
    requires the probe to return exit 0 at least once before the
    timeout. Fail if the probe never passes or the background process
    exits non-zero before the probe succeeds. Marcus always kills the
    background process before returning. Examples:

    - start: ``uvicorn main:app --port 8000``,
      probe: ``curl -f http://localhost:8000/health``
    - start: ``node server.js``,
      probe: ``curl -f http://localhost:3000/``
    - start: ``flask run --port 5000``,
      probe: ``curl -f http://localhost:5000/``

Why two fields instead of one
-----------------------------
A single ``start_command`` that combines start-and-probe forces the
agent to write shell plumbing: background the server, sleep, probe,
capture exit code, kill the background process, propagate the probe's
exit code through the ``timeout`` wrapper. Different agents write
different buggy versions. ``timeout`` returns 124 on timeout (not 0),
so even a healthy server running cleanly for 10s looks like a failure
without extra bash handling.

Splitting into ``start_command`` + ``readiness_probe`` moves the
orchestration into Marcus where it can be tested once and reused. The
agent declares intent; Marcus runs it correctly.

Why no auto-detection
---------------------
Auto-detection sounds helpful but creates three problems:

1. **Silent pass on unknown stacks.** Stacks Marcus doesn't recognize
   return "no stack detected, success=True" which defeats the purpose
   of the gate — every non-software project would pass.

2. **Software bias.** Auto-detection hardcodes package.json,
   pyproject.toml, Cargo.toml, etc. Marcus is supposed to be the
   coordination layer for all agent work (marketing, research, content,
   data pipelines — per docs/marcus-validation.md). A detection layer
   that only knows code stacks tells every non-code deliverable that
   Marcus doesn't understand it.

3. **The agent knows better.** The integration agent just finished
   verifying the deliverable manually. They already know the exact
   command to start it because they ran it. Asking them to declare it
   is a smaller ask than asking Marcus to guess.

References
----------
- Dashboard-v71 Epictetus audit (2026-04-13) — the experiment that
  revealed the need for this layer. Missing ``public/index.html`` would
  have been caught by ``npm run build``, which the agents never ran.
- Simon decision 967555f6 — locked the two-field design after
  considering single-command (shell wizardry), exit-0-or-alive (hung
  server false pass), and single-field approaches.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# One-shot command timeout. Covers npm run build, pip install + entry
# point, cargo build, etc. Larger projects may exceed this — revisit if
# we see legitimate one-shot builds timing out.
DEFAULT_ONE_SHOT_TIMEOUT_SECONDS = 60

# Server readiness window. How long we wait for a server to become
# ready AFTER starting it in the background. Polled every
# ``READINESS_POLL_INTERVAL_SECONDS``.
DEFAULT_READINESS_TIMEOUT_SECONDS = 15
READINESS_POLL_INTERVAL_SECONDS = 1.0

# Probe command timeout. Each individual probe invocation (e.g. a
# ``curl`` call) should complete quickly; if a probe takes longer than
# this we treat it as a failed poll and move on to the next attempt.
PROBE_INVOCATION_TIMEOUT_SECONDS = 3.0

# Grace period for killing the background process after readiness
# passes or fails. SIGTERM first, SIGKILL if the process ignores it.
KILL_GRACE_PERIOD_SECONDS = 2.0

# Output truncation — long logs aren't useful in blocker messages.
# Keep the tail so the actual error survives.
MAX_OUTPUT_CHARS = 8192


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class VerificationStep:
    """Result of a single subprocess invocation during verification.

    Attributes
    ----------
    name : str
        Human-readable step name: ``"start_command"``, ``"readiness_probe"``,
        or ``"missing_start_command"``.
    command : str
        The command as it was declared by the agent. Stored as a string
        (not argv) because agents declare it as a shell-style string and
        we run it through ``shlex.split`` at execution time.
    exit_code : Optional[int]
        Process return code. ``None`` if the process was killed by
        timeout or never executed.
    stdout : str
        Captured stdout, tail-truncated to ``MAX_OUTPUT_CHARS``.
    stderr : str
        Captured stderr, tail-truncated similarly.
    duration_seconds : float
        Wall-clock time from spawn to termination. ``0.0`` for steps
        that didn't execute.
    success : bool
        True iff the step met its contract (exit 0 for one-shots;
        probe returned 0 for server modes).
    """

    name: str
    command: str
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_seconds: float
    success: bool


@dataclass
class ProductSmokeResult:
    """Aggregate result of a deliverable verification run.

    Attributes
    ----------
    success : bool
        True iff all steps succeeded. ``False`` if any step failed or
        if the required ``start_command`` was missing.
    steps : List[VerificationStep]
        Every subprocess step in execution order. May contain one step
        (one-shot mode) or two (server+probe mode).
    failure_summary : Optional[str]
        One-line human-readable description of the first failure.
    blocker_message : Optional[str]
        Ready-to-paste blocker description for the integration agent.
        Includes the failing step, the command, and the tail of stderr.
    """

    success: bool
    steps: List[VerificationStep] = field(default_factory=list)
    failure_summary: Optional[str] = None
    blocker_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/persistence.

        Returns
        -------
        Dict[str, Any]
            JSON-ready dictionary with truncated outputs.
        """
        return {
            "success": self.success,
            "steps": [
                {
                    "name": st.name,
                    "command": st.command,
                    "exit_code": st.exit_code,
                    "stdout_tail": st.stdout[-1024:] if st.stdout else "",
                    "stderr_tail": st.stderr[-1024:] if st.stderr else "",
                    "duration_seconds": st.duration_seconds,
                    "success": st.success,
                }
                for st in self.steps
            ],
            "failure_summary": self.failure_summary,
        }


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------


def _truncate_output(text: str) -> str:
    """Tail-truncate captured output to MAX_OUTPUT_CHARS."""
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    dropped = len(text) - MAX_OUTPUT_CHARS
    return f"...[truncated {dropped} chars]...\n" + text[-MAX_OUTPUT_CHARS:]


def _build_subprocess_env() -> Dict[str, str]:
    """Environment for subprocess invocations.

    Inherits the parent env so PATH, HOME, and framework-specific
    variables propagate, then forces ``CI=true`` to disable interactive
    prompts (react-scripts, Vite, etc.). Order matters: parent env
    first, override second, so our override wins regardless of any
    existing ``CI`` value in the parent. See Codex P2 review on PR #346.
    """
    return {**os.environ, "CI": "true"}


async def _run_one_shot(
    command: str, cwd: Path, timeout_seconds: float
) -> VerificationStep:
    """Run a command and wait for it to exit.

    Mode 1 of the verification contract. The command must exit 0
    within ``timeout_seconds`` to succeed.

    Parameters
    ----------
    command : str
        Shell-style command string declared by the agent (e.g.
        ``"npm run build"``). Parsed via ``shlex.split`` to argv form
        before invocation, so no shell interpretation happens.
    cwd : Path
        Working directory for the subprocess.
    timeout_seconds : float
        Maximum wall-clock time. Process is killed on timeout and the
        step is marked ``success=False``.

    Returns
    -------
    VerificationStep
        Structured result. Never raises on command failure — returns
        the step with ``success=False``.
    """
    start_time = time.monotonic()

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return VerificationStep(
            name="start_command",
            command=command,
            exit_code=None,
            stdout="",
            stderr=f"Could not parse command as shell-style string: {exc}",
            duration_seconds=0.0,
            success=False,
        )
    if not argv:
        return VerificationStep(
            name="start_command",
            command=command,
            exit_code=None,
            stdout="",
            stderr="start_command parsed to empty argv",
            duration_seconds=0.0,
            success=False,
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=_build_subprocess_env(),
        )
    except FileNotFoundError as exc:
        return VerificationStep(
            name="start_command",
            command=command,
            exit_code=None,
            stdout="",
            stderr=f"Command not found: {argv[0]!r} ({exc})",
            duration_seconds=time.monotonic() - start_time,
            success=False,
        )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        await _kill_process(proc)
        return VerificationStep(
            name="start_command",
            command=command,
            exit_code=None,
            stdout="",
            stderr=(
                f"Timed out after {timeout_seconds:.0f}s — process killed. "
                f"Declare a readiness_probe if this is a long-running "
                f"server, or shorten the start_command if this is a "
                f"one-shot that ran long."
            ),
            duration_seconds=time.monotonic() - start_time,
            success=False,
        )

    stdout = _truncate_output(stdout_bytes.decode("utf-8", errors="replace"))
    stderr = _truncate_output(stderr_bytes.decode("utf-8", errors="replace"))
    exit_code = proc.returncode
    return VerificationStep(
        name="start_command",
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=time.monotonic() - start_time,
        success=exit_code == 0,
    )


async def _kill_process(proc: asyncio.subprocess.Process) -> None:
    """Kill a subprocess with SIGTERM→SIGKILL escalation.

    Parameters
    ----------
    proc : asyncio.subprocess.Process
        Process to terminate. No-op if already dead.
    """
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=KILL_GRACE_PERIOD_SECONDS)
    except (asyncio.TimeoutError, ProcessLookupError):
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass


async def _run_probe(probe_command: str, cwd: Path) -> tuple[int, str, str]:
    """Run a single readiness probe invocation.

    Parameters
    ----------
    probe_command : str
        Shell-style probe command (e.g. ``"curl -f http://localhost:8000/health"``).
    cwd : Path
        Working directory for the probe.

    Returns
    -------
    tuple[int, str, str]
        ``(exit_code, stdout_tail, stderr_tail)``. Exit code -1 on
        parse/launch failure, -2 on probe timeout.
    """
    try:
        argv = shlex.split(probe_command)
    except ValueError:
        return -1, "", f"could not parse probe: {probe_command!r}"
    if not argv:
        return -1, "", "empty probe command"

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=_build_subprocess_env(),
        )
    except FileNotFoundError as exc:
        return -1, "", f"probe binary not found: {argv[0]!r} ({exc})"

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=PROBE_INVOCATION_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        await _kill_process(proc)
        return -2, "", f"probe timed out after {PROBE_INVOCATION_TIMEOUT_SECONDS}s"

    return (
        proc.returncode if proc.returncode is not None else -1,
        stdout_bytes.decode("utf-8", errors="replace"),
        stderr_bytes.decode("utf-8", errors="replace"),
    )


async def _run_server_with_probe(
    start_command: str,
    readiness_probe: str,
    cwd: Path,
    readiness_timeout_seconds: float,
) -> List[VerificationStep]:
    """Start a background server and poll the readiness probe.

    Mode 2 of the verification contract. The server is started as a
    background subprocess and the probe is polled once per second for
    up to ``readiness_timeout_seconds``. Pass requires the probe to
    return exit 0 at least once within the window.

    The background server is always killed before this function returns
    — pass, fail, or exception.

    Parameters
    ----------
    start_command : str
        Shell-style command that starts the long-running process
        (e.g. ``"uvicorn main:app --port 8000"``).
    readiness_probe : str
        Shell-style probe command polled for readiness (e.g.
        ``"curl -f http://localhost:8000/health"``).
    cwd : Path
        Working directory for both the server and the probe.
    readiness_timeout_seconds : float
        Maximum wait for readiness before declaring failure.

    Returns
    -------
    List[VerificationStep]
        Two steps: one for the background start (always present,
        reports whether the server even launched) and one for the
        readiness probe (reports whether the probe eventually passed).
    """
    server_start_time = time.monotonic()

    try:
        argv = shlex.split(start_command)
    except ValueError as exc:
        return [
            VerificationStep(
                name="start_command",
                command=start_command,
                exit_code=None,
                stdout="",
                stderr=f"Could not parse start_command: {exc}",
                duration_seconds=0.0,
                success=False,
            )
        ]
    if not argv:
        return [
            VerificationStep(
                name="start_command",
                command=start_command,
                exit_code=None,
                stdout="",
                stderr="start_command parsed to empty argv",
                duration_seconds=0.0,
                success=False,
            )
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=_build_subprocess_env(),
        )
    except FileNotFoundError as exc:
        return [
            VerificationStep(
                name="start_command",
                command=start_command,
                exit_code=None,
                stdout="",
                stderr=f"Command not found: {argv[0]!r} ({exc})",
                duration_seconds=time.monotonic() - server_start_time,
                success=False,
            )
        ]

    # Poll the readiness probe. The server runs in the background;
    # we poll once per second until either:
    # - the probe succeeds (pass)
    # - the server process exits before readiness (fail — server crashed)
    # - the readiness timeout fires (fail — server never became ready)
    probe_success = False
    last_probe_stdout = ""
    last_probe_stderr = ""
    last_probe_exit = -1
    probe_attempts = 0
    probe_start_time = time.monotonic()
    deadline = probe_start_time + readiness_timeout_seconds

    while time.monotonic() < deadline:
        # If the server process exited before readiness, that's a
        # fatal fail — no point continuing to probe a dead server.
        if proc.returncode is not None:
            break

        probe_attempts += 1
        last_probe_exit, last_probe_stdout, last_probe_stderr = await _run_probe(
            readiness_probe, cwd
        )
        if last_probe_exit == 0:
            probe_success = True
            break

        await asyncio.sleep(READINESS_POLL_INTERVAL_SECONDS)

    # Capture the server's output before killing it. This gives us
    # early-crash stack traces in the blocker message.
    server_stdout = ""
    server_stderr = ""
    server_exit_code: Optional[int] = proc.returncode

    # If the process has already exited, grab its output. Otherwise
    # kill it and then grab what came out before the kill.
    if server_exit_code is None:
        await _kill_process(proc)

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=2.0
        )
        server_stdout = _truncate_output(stdout_bytes.decode("utf-8", errors="replace"))
        server_stderr = _truncate_output(stderr_bytes.decode("utf-8", errors="replace"))
    except (asyncio.TimeoutError, ValueError):
        # ValueError raised by communicate() if already consumed.
        pass

    server_exit_code = proc.returncode

    # The start_command step is successful if the server stayed alive
    # long enough to be probed. It's unsuccessful if it exited before
    # the probe could run.
    server_step = VerificationStep(
        name="start_command",
        command=start_command,
        exit_code=server_exit_code,
        stdout=server_stdout,
        stderr=server_stderr,
        duration_seconds=time.monotonic() - server_start_time,
        success=(
            # Success = server was still running when we started
            # probing OR readiness probe eventually passed.
            probe_success
            or (server_exit_code is None or server_exit_code < 0)
        ),
    )

    probe_duration = time.monotonic() - probe_start_time
    probe_step = VerificationStep(
        name="readiness_probe",
        command=readiness_probe,
        exit_code=last_probe_exit if probe_attempts else None,
        stdout=last_probe_stdout,
        stderr=(
            last_probe_stderr
            if probe_success
            else (
                f"Readiness probe failed after {probe_attempts} attempt(s) "
                f"over {probe_duration:.1f}s. "
                f"Last exit={last_probe_exit}. "
                + (
                    "Server process exited before readiness "
                    f"(exit code {server_exit_code})."
                    if server_exit_code is not None and not probe_success
                    else "Probe never returned exit 0 within the window."
                )
                + (f" Last stderr: {last_probe_stderr}" if last_probe_stderr else "")
            )
        ),
        duration_seconds=probe_duration,
        success=probe_success,
    )

    return [server_step, probe_step]


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------


async def verify_deliverable(
    start_command: Optional[str],
    readiness_probe: Optional[str],
    cwd: Path,
    one_shot_timeout_seconds: float = DEFAULT_ONE_SHOT_TIMEOUT_SECONDS,
    readiness_timeout_seconds: float = DEFAULT_READINESS_TIMEOUT_SECONDS,
) -> ProductSmokeResult:
    """Verify a deliverable via its declared start command.

    This is Marcus-side enforcement that an integration task's declared
    deliverable actually runs. Runs in one of two modes based on whether
    ``readiness_probe`` was declared:

    **Mode 1 — one-shot** (no readiness_probe):
        Runs ``start_command`` as a subprocess and waits for it to exit.
        Success requires exit code 0 within ``one_shot_timeout_seconds``.

    **Mode 2 — server+probe** (with readiness_probe):
        Starts ``start_command`` as a background subprocess, then polls
        ``readiness_probe`` once per second for up to
        ``readiness_timeout_seconds``. Success requires the probe to
        return exit 0 at least once. The background process is always
        killed before this function returns.

    Parameters
    ----------
    start_command : Optional[str]
        Shell-style command to start the deliverable. When ``None`` or
        empty, the verification is rejected as missing a required field.
    readiness_probe : Optional[str]
        Shell-style command that probes whether the deliverable is
        ready. When provided, switches the runner into server+probe
        mode. When absent, uses one-shot mode.
    cwd : Path
        Working directory for both commands. Typically the project
        root as resolved from the kanban workspace state.
    one_shot_timeout_seconds : float
        Maximum wait for one-shot commands. Default 60s.
    readiness_timeout_seconds : float
        Maximum wait for a server to become ready. Default 15s.

    Returns
    -------
    ProductSmokeResult
        Structured result with steps, pass/fail status, and a
        ready-to-paste blocker message on failure.

    Notes
    -----
    Never raises on command failure — returns a ``ProductSmokeResult``
    with ``success=False`` and populated blocker fields. Programmer
    errors (e.g. invalid ``cwd``) propagate as exceptions so the caller
    can distinguish infrastructure problems from deliverable failures.
    """
    if not start_command or not start_command.strip():
        missing_step = VerificationStep(
            name="missing_start_command",
            command="",
            exit_code=None,
            stdout="",
            stderr=(
                "No start_command declared. Integration tasks must "
                "declare start_command when marking the task complete "
                "via report_task_progress."
            ),
            duration_seconds=0.0,
            success=False,
        )
        return ProductSmokeResult(
            success=False,
            steps=[missing_step],
            failure_summary="integration task missing required start_command",
            blocker_message=_render_missing_blocker(),
        )

    if not cwd.is_dir():
        raise ValueError(f"cwd is not a directory: {cwd}")

    logger.info(
        f"verify_deliverable: cwd={cwd} start_command={start_command!r} "
        f"readiness_probe={readiness_probe!r}"
    )

    if readiness_probe and readiness_probe.strip():
        steps = await _run_server_with_probe(
            start_command=start_command,
            readiness_probe=readiness_probe.strip(),
            cwd=cwd,
            readiness_timeout_seconds=readiness_timeout_seconds,
        )
    else:
        steps = [
            await _run_one_shot(
                command=start_command,
                cwd=cwd,
                timeout_seconds=one_shot_timeout_seconds,
            )
        ]

    # Overall success = every step succeeded.
    success = all(step.success for step in steps)
    if success:
        total_duration = sum(s.duration_seconds for s in steps)
        logger.info(f"verify_deliverable PASSED in {total_duration:.1f}s")
        return ProductSmokeResult(success=True, steps=steps)

    first_failure = next(step for step in steps if not step.success)
    failure_summary = (
        f"{first_failure.name} failed " f"(exit={first_failure.exit_code}) in {cwd}"
    )
    blocker_message = _render_failure_blocker(first_failure, steps)
    logger.warning(f"verify_deliverable FAILED: {failure_summary}")

    return ProductSmokeResult(
        success=False,
        steps=steps,
        failure_summary=failure_summary,
        blocker_message=blocker_message,
    )


def _render_missing_blocker() -> str:
    """Blocker message for integration tasks that omit start_command."""
    return (
        "## Integration task rejected: missing start_command\n\n"
        "Marcus requires integration verification tasks to declare a "
        "`start_command` when marking the task complete. This is how "
        "Marcus independently verifies that the assembled deliverable "
        "actually runs — agent self-reports alone are not sufficient, "
        "as dashboard-v71 demonstrated when a React app shipped missing "
        "`public/index.html` but passed every agent-level check.\n\n"
        "**What to do:**\n\n"
        "1. Decide how to start your deliverable. Examples:\n"
        "   - Node build: `npm run build`\n"
        "   - Python CLI: `python -m mypackage --help`\n"
        "   - Type check: `tsc --noEmit`\n"
        "   - Python web server: `uvicorn main:app --port 8000`\n"
        "     (also declare a readiness_probe for servers — see below)\n"
        "   - Flask: `flask run --port 5000`\n\n"
        "2. If the command is a long-running server, also declare a "
        "`readiness_probe`. Examples:\n"
        "   - `curl -f http://localhost:8000/health`\n"
        "   - `curl -f http://localhost:3000/`\n\n"
        "3. Call `report_task_progress` with both fields:\n\n"
        "   ```python\n"
        "   report_task_progress(\n"
        "       task_id=task_id,\n"
        "       status='completed',\n"
        "       progress=100,\n"
        "       message='...',\n"
        "       start_command='uvicorn main:app --port 8000',\n"
        "       readiness_probe='curl -f http://localhost:8000/health',\n"
        "   )\n"
        "   ```\n\n"
        "Marcus will run the command (with a bounded timeout) and "
        "accept the completion only if it exits 0 (one-shot) or the "
        "readiness_probe returns exit 0 within 15s (server mode)."
    )


def _render_failure_blocker(
    failed_step: VerificationStep, all_steps: List[VerificationStep]
) -> str:
    """Blocker message for a start_command/readiness_probe failure.

    Parameters
    ----------
    failed_step : VerificationStep
        The first step that failed.
    all_steps : List[VerificationStep]
        All steps in the run (for context in the blocker).

    Returns
    -------
    str
        Multi-line actionable blocker description.
    """
    tail = failed_step.stderr or failed_step.stdout or "(no output)"
    mode_description = (
        "readiness probe never returned exit 0"
        if failed_step.name == "readiness_probe"
        else "start_command did not exit 0"
    )
    return (
        "## Deliverable verification FAILED\n\n"
        "Marcus ran the declared start_command/readiness_probe and "
        "the deliverable did not meet the pass contract.\n\n"
        f"**Failing step**: `{failed_step.name}` — {mode_description}\n"
        f"**Exit code**: {failed_step.exit_code}\n"
        f"**Command**: `{failed_step.command}`\n\n"
        f"**Output (tail)**:\n```\n{tail}\n```\n\n"
        "**What to do**: Run the same command locally. If it fails for "
        "you too, fix the underlying issue (missing file, broken "
        "import, bad config, etc.), commit, and re-mark the integration "
        "task complete. If it passes for you but not for Marcus, check "
        "the working directory, environment variables, and any "
        "side-effects that differ between your environment and a clean "
        "subprocess run. Marcus runs commands with `CI=true` set; if "
        "your command relies on interactive prompts it will fail here."
    )
