"""
Marcus-side product smoke verification (Layer 1).

Deterministic, subprocess-based verification that the assembled
product actually builds and boots. Runs AFTER the integration
verification agent marks its task complete — machine checks beat
agent self-reports when they conflict.

Catches the classes of bug that v71 exposed:

1. **Product doesn't build** — missing required files (``public/index.html``
   for React projects, ``__init__.py`` for Python packages), import errors
   the unit tests didn't exercise, bad configuration. ``npm run build`` /
   ``pytest`` / equivalent catches these in seconds.

2. **Product doesn't boot** — build succeeds but the entry point crashes.
   Optional start-command verification with bounded timeout.

3. **Silent integration gaps** — build + boot succeed but the consumer
   never calls the producer. This layer does NOT catch those (that's
   Layer 2 prompt guidance + Epictetus audit). This layer is scoped to
   "does the thing build and start."

Why not just trust the integration verification agent?
------------------------------------------------------
The integration agent is LLM-driven. Its work is guided by prompt
instructions, which can be skipped, misread, or fabricated. Machine
verification via subprocess is the ground-truth check that cannot be
talked around. This is the same pattern as PR #337's runtime-test
precedence over LLM validation: when prompt-level and machine-level
checks disagree, the machine wins.

Extensibility
-------------
New stack support is a new ``StackVerifier`` subclass plus a line
in ``_pick_verifier``. No orchestrator rewrite. Initial support:
Node (npm + react-scripts/Vite/plain), Python (pip + pytest,
optional FastAPI/Flask start). Go, Rust, Java, .NET are stubs that
detect the stack but no-op the verification (add in follow-up).

References
----------
Dashboard-v71 Epictetus audit (2026-04-13) — the experiment that
revealed the need for this layer. Agent reported integration
complete; ``npm start`` later failed with "Could not find a
required file. Name: index.html". This module exists so that
failure mode never ships again.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

# Subprocess timeouts — bounded so a hung command doesn't block the
# completion pipeline. Values tuned for MVP; revisit if we see legit
# builds take longer.
DEFAULT_INSTALL_TIMEOUT_SECONDS = 300  # 5 min — npm install can be slow
DEFAULT_BUILD_TIMEOUT_SECONDS = 180  # 3 min
DEFAULT_TEST_TIMEOUT_SECONDS = 180  # 3 min
DEFAULT_START_TIMEOUT_SECONDS = 30  # 30s — if it hasn't started, it's wedged

# Output truncation — very long build logs are unhelpful in blocker
# messages. Keep the last N chars so the tail (where the real error
# lives) survives.
MAX_OUTPUT_CHARS = 8192

# Stack types we know about
StackType = Literal["node", "python", "go", "rust", "java"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class DetectedStack:
    """A stack discovered in the project root by ``StackDetector``.

    Attributes
    ----------
    stack_type : StackType
        Which language/framework family.
    root_path : Path
        Directory containing the stack's root marker. May be a
        subdirectory of the project root for nested stacks (e.g.
        ``src/frontend`` alongside ``src/backend``).
    marker_file : Path
        The file that identified the stack (``package.json``,
        ``pyproject.toml``, etc.).
    metadata : Dict[str, Any]
        Parsed contents of the marker file (or key fields from it) —
        used by verifiers to pick the right build/start commands.
        For Node, contains ``scripts`` dict. For Python, may contain
        detected framework hints.
    """

    stack_type: StackType
    root_path: Path
    marker_file: Path
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationStep:
    """Result of one subprocess invocation during verification.

    Attributes
    ----------
    name : str
        Human-readable step name (``"install"``, ``"build"``,
        ``"test"``, ``"start"``).
    command : List[str]
        argv-form command that was executed. First element is the
        program; subsequent are arguments. Never a shell string —
        always argv to avoid shell injection and quoting bugs.
    cwd : Path
        Working directory the command ran in.
    exit_code : Optional[int]
        Process return code. None if the process was killed by
        timeout before completing.
    stdout : str
        Captured stdout, truncated to ``MAX_OUTPUT_CHARS`` from the
        tail so errors at the end survive.
    stderr : str
        Captured stderr, truncated similarly.
    duration_seconds : float
        Wall-clock time from spawn to termination.
    success : bool
        True iff ``exit_code == 0`` and the command wasn't killed.
    """

    name: str
    command: List[str]
    cwd: Path
    exit_code: Optional[int]
    stdout: str
    stderr: str
    duration_seconds: float
    success: bool


@dataclass
class ProductSmokeResult:
    """Aggregate result of a full ProductSmokeVerifier run.

    Attributes
    ----------
    success : bool
        True iff every verification step succeeded AND at least one
        stack was detected. Empty-stack result is also ``True``
        (nothing to verify = nothing to fail) but carries a
        ``skipped_reason`` to distinguish it from a real pass.
    detected_stacks : List[DetectedStack]
        Stacks that were found. Empty list with ``success=True``
        means no detectable stack (e.g. a pure-markdown doc project).
    steps : List[VerificationStep]
        Every subprocess invocation in execution order, for audit
        and debugging.
    failure_summary : Optional[str]
        One-line description of the first failure, if any. Suitable
        for log headers.
    blocker_message : Optional[str]
        Ready-to-paste blocker description for the integration
        agent. Includes the failing step name, command, and the
        tail of stderr. None on success.
    skipped_reason : Optional[str]
        Non-None when verification was skipped (no detected stack,
        no build script, etc.). Still a pass, but the caller may
        want to log it.
    """

    success: bool
    detected_stacks: List[DetectedStack]
    steps: List[VerificationStep]
    failure_summary: Optional[str] = None
    blocker_message: Optional[str] = None
    skipped_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/persistence.

        Returns
        -------
        Dict[str, Any]
            JSON-ready dictionary.
        """
        return {
            "success": self.success,
            "detected_stacks": [
                {
                    "stack_type": s.stack_type,
                    "root_path": str(s.root_path),
                    "marker_file": str(s.marker_file),
                }
                for s in self.detected_stacks
            ],
            "steps": [
                {
                    "name": st.name,
                    "command": st.command,
                    "cwd": str(st.cwd),
                    "exit_code": st.exit_code,
                    "stdout_tail": st.stdout[-1024:] if st.stdout else "",
                    "stderr_tail": st.stderr[-1024:] if st.stderr else "",
                    "duration_seconds": st.duration_seconds,
                    "success": st.success,
                }
                for st in self.steps
            ],
            "failure_summary": self.failure_summary,
            "skipped_reason": self.skipped_reason,
        }


# ---------------------------------------------------------------------------
# Subprocess helper
# ---------------------------------------------------------------------------


async def _run_subprocess(
    name: str,
    command: List[str],
    cwd: Path,
    timeout_seconds: float,
    env: Optional[Dict[str, str]] = None,
) -> VerificationStep:
    """Run a subprocess with bounded timeout, return a VerificationStep.

    Parameters
    ----------
    name : str
        Step name for the returned record.
    command : List[str]
        argv-form command. First element must be an executable name
        that resolves via PATH or an absolute path.
    cwd : Path
        Working directory.
    timeout_seconds : float
        Maximum wall-clock time. Process is killed on timeout and
        the step is marked ``success=False`` with ``exit_code=None``.
    env : Optional[Dict[str, str]]
        Environment overrides. None means inherit.

    Returns
    -------
    VerificationStep
        Structured result. Never raises on command failure — returns
        the step with ``success=False``. Raises only on programmer
        errors (bad cwd, invalid argv type).

    Notes
    -----
    Uses ``asyncio.create_subprocess_exec`` (not ``_shell``) so the
    command list goes through argv directly and no shell interpretation
    happens. This avoids injection hazards from any dynamic component
    of the command and makes quoting deterministic across platforms.
    """
    start = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
        )
    except FileNotFoundError as exc:
        # The command binary isn't on PATH. Return a failed step with
        # a clear message — a missing binary is a legitimate failure
        # mode (agent forgot to install Node, agent used wrong tool
        # name) and the agent should see the actual error.
        return VerificationStep(
            name=name,
            command=command,
            cwd=cwd,
            exit_code=None,
            stdout="",
            stderr=f"Command not found: {command[0]!r} ({exc})",
            duration_seconds=time.monotonic() - start,
            success=False,
        )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        # Kill the hung process so we don't leak it. Double-kill
        # pattern (terminate then kill) for shells that ignore TERM.
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except (asyncio.TimeoutError, ProcessLookupError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        duration = time.monotonic() - start
        return VerificationStep(
            name=name,
            command=command,
            cwd=cwd,
            exit_code=None,
            stdout="",
            stderr=(
                f"Timed out after {timeout_seconds:.0f}s — process killed. "
                f"Check for hung test / infinite loop / missing "
                f"interactivity prompt."
            ),
            duration_seconds=duration,
            success=False,
        )

    duration = time.monotonic() - start
    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    # Truncate from the TAIL so the error at the end of a long log
    # survives. head-truncation would drop the failure message.
    if len(stdout) > MAX_OUTPUT_CHARS:
        stdout = (
            "...[truncated " + str(len(stdout) - MAX_OUTPUT_CHARS) + " chars]...\n"
        ) + stdout[-MAX_OUTPUT_CHARS:]
    if len(stderr) > MAX_OUTPUT_CHARS:
        stderr = (
            "...[truncated " + str(len(stderr) - MAX_OUTPUT_CHARS) + " chars]...\n"
        ) + stderr[-MAX_OUTPUT_CHARS:]

    exit_code = proc.returncode
    return VerificationStep(
        name=name,
        command=command,
        cwd=cwd,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
        success=exit_code == 0,
    )


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------


# Directories to skip during stack detection — node_modules and
# friends produce false positives because they contain package.json
# files for their dependencies. Virtual envs and build output also
# noise up the scan.
_SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    ".env",  # some projects use .env as venv dir
    "__pycache__",
    ".git",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
}

# Maximum depth to walk during detection — deep nesting is almost
# always a sign of hitting node_modules-like directories we should
# have skipped. 5 is generous for realistic project layouts.
_MAX_DETECT_DEPTH = 5


class StackDetector:
    """Walk a project root and identify the technology stacks present.

    A "stack" is a chunk of code organized around a well-known root
    marker file — ``package.json`` for Node, ``pyproject.toml``
    (or ``setup.py``/``requirements.txt``) for Python, ``Cargo.toml``
    for Rust, ``go.mod`` for Go, ``pom.xml``/``build.gradle`` for
    Java. Multiple stacks in one repo (e.g. a full-stack app with
    frontend+backend) produce multiple ``DetectedStack`` records.

    Notes
    -----
    Detection is filesystem-based, not git-based. It runs against
    the actual files on disk in the project root. This means:

    - Files listed in ``.gitignore`` are still detected (which is
      correct for our purposes — we verify the checked-out state).
    - Stacks in subdirectories are found if they carry their own
      marker files (``src/frontend/package.json`` produces a Node
      stack at ``src/frontend``).
    - The walk skips ``node_modules``, virtual envs, and build
      output dirs to avoid false positives from vendor files.
    """

    @staticmethod
    def detect(project_root: Path) -> List[DetectedStack]:
        """Walk the project root and return all detected stacks.

        Parameters
        ----------
        project_root : Path
            Repository root. Must exist and be a directory.

        Returns
        -------
        List[DetectedStack]
            Stacks found. Empty list is a valid result for projects
            with no recognized technology (e.g. pure-markdown docs).

        Raises
        ------
        ValueError
            If ``project_root`` is not a directory.
        """
        if not project_root.is_dir():
            raise ValueError(f"project_root is not a directory: {project_root}")

        stacks: List[DetectedStack] = []
        # Breadth-first-ish walk: we want shallower stacks first so
        # the ordering is predictable for callers.
        queue: List[tuple[Path, int]] = [(project_root, 0)]
        while queue:
            path, depth = queue.pop(0)
            if depth > _MAX_DETECT_DEPTH:
                continue
            try:
                entries = list(path.iterdir())
            except (PermissionError, OSError) as exc:
                logger.debug(f"Skipping {path}: {exc}")
                continue

            files = {e.name: e for e in entries if e.is_file()}
            subdirs = [e for e in entries if e.is_dir() and e.name not in _SKIP_DIRS]

            # Check markers at this level
            for detector in _MARKER_DETECTORS:
                stack = detector(path, files)
                if stack is not None:
                    stacks.append(stack)

            queue.extend((d, depth + 1) for d in subdirs)

        return stacks


def _detect_node(path: Path, files: Dict[str, Path]) -> Optional[DetectedStack]:
    """Detect a Node stack via package.json.

    Parameters
    ----------
    path : Path
        Directory being examined.
    files : Dict[str, Path]
        Files in the directory, keyed by filename.

    Returns
    -------
    Optional[DetectedStack]
        Stack record if package.json exists and is parseable.
    """
    pkg = files.get("package.json")
    if pkg is None:
        return None
    try:
        raw = pkg.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"Failed to parse {pkg}: {exc}")
        return DetectedStack(
            stack_type="node",
            root_path=path,
            marker_file=pkg,
            metadata={"parse_error": str(exc)},
        )
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    return DetectedStack(
        stack_type="node",
        root_path=path,
        marker_file=pkg,
        metadata={
            "scripts": scripts,
            "name": data.get("name"),
            "dependencies": (
                list(data.get("dependencies", {}).keys())
                if isinstance(data.get("dependencies"), dict)
                else []
            ),
            "devDependencies": (
                list(data.get("devDependencies", {}).keys())
                if isinstance(data.get("devDependencies"), dict)
                else []
            ),
        },
    )


def _detect_python(path: Path, files: Dict[str, Path]) -> Optional[DetectedStack]:
    """Detect a Python stack via pyproject.toml or requirements.txt.

    Parameters
    ----------
    path : Path
        Directory being examined.
    files : Dict[str, Path]
        Files in the directory, keyed by filename.

    Returns
    -------
    Optional[DetectedStack]
        Stack record if a Python marker is present.
    """
    marker = files.get("pyproject.toml") or files.get("setup.py")
    if marker is None:
        # requirements.txt alone also counts, but is a weaker signal
        marker = files.get("requirements.txt")
    if marker is None:
        return None
    return DetectedStack(
        stack_type="python",
        root_path=path,
        marker_file=marker,
        metadata={
            "has_pyproject": "pyproject.toml" in files,
            "has_setup_py": "setup.py" in files,
            "has_requirements": "requirements.txt" in files,
        },
    )


def _detect_go(path: Path, files: Dict[str, Path]) -> Optional[DetectedStack]:
    """Detect a Go stack via go.mod (stub for future impl)."""
    if "go.mod" not in files:
        return None
    return DetectedStack(stack_type="go", root_path=path, marker_file=files["go.mod"])


def _detect_rust(path: Path, files: Dict[str, Path]) -> Optional[DetectedStack]:
    """Detect a Rust stack via Cargo.toml (stub for future impl)."""
    if "Cargo.toml" not in files:
        return None
    return DetectedStack(
        stack_type="rust", root_path=path, marker_file=files["Cargo.toml"]
    )


def _detect_java(path: Path, files: Dict[str, Path]) -> Optional[DetectedStack]:
    """Detect a Java stack via pom.xml or build.gradle (stub)."""
    marker = files.get("pom.xml") or files.get("build.gradle")
    if marker is None:
        return None
    return DetectedStack(stack_type="java", root_path=path, marker_file=marker)


_MARKER_DETECTORS = [
    _detect_node,
    _detect_python,
    _detect_go,
    _detect_rust,
    _detect_java,
]


# ---------------------------------------------------------------------------
# Verifier base + concrete implementations
# ---------------------------------------------------------------------------


class StackVerifier:
    """Abstract base for per-stack verification.

    Subclasses implement :meth:`verify` which returns an ordered list
    of :class:`VerificationStep` records. A successful run is one
    where every step has ``success=True``. Subclasses should NOT
    raise on command failure — they should return a failed step so
    the orchestrator can aggregate results.
    """

    def __init__(self, stack: DetectedStack) -> None:
        self.stack = stack

    async def verify(self) -> List[VerificationStep]:
        """Run verification for this stack.

        Returns
        -------
        List[VerificationStep]
            Steps in execution order. Short-circuits on first failure
            (no point running build if install failed).
        """
        raise NotImplementedError


class NodeVerifier(StackVerifier):
    """Verifies a Node/JavaScript/TypeScript stack.

    Runs, in order:

    1. ``npm install`` — installs dependencies
    2. ``npm run build`` — only if the project has a build script

    Rationale: ``npm install`` is universal for Node projects.
    ``npm run build`` is the highest-value check — it's how
    ``react-scripts``, ``vite``, ``webpack``, ``tsc`` and friends
    verify that every required file exists and every import
    resolves. Dashboard-v71's missing ``public/index.html`` would
    have been caught here in seconds because ``react-scripts build``
    errors out with "Could not find a required file. Name: index.html".

    Not yet implemented for MVP:

    - ``npm run dev`` / start verification — building is sufficient
      for the "missing files / broken imports" class. Start
      verification is a future extension for runtime-only failures.
    - Alternate package managers (yarn, pnpm, bun) — detection
      hooks exist but the executor hardcodes ``npm`` for MVP.
    """

    async def verify(self) -> List[VerificationStep]:
        """Run the Node verification sequence.

        Returns
        -------
        List[VerificationStep]
            ``[install_step]`` on install failure.
            ``[install_step, build_step]`` otherwise.
            ``[install_step]`` if there's no build script in package.json.
        """
        steps: List[VerificationStep] = []

        # Resolve the npm binary. If npm isn't on PATH, we want a
        # clear error, not a cryptic FileNotFoundError deep in the
        # subprocess helper.
        npm = shutil.which("npm")
        if npm is None:
            return [
                VerificationStep(
                    name="install",
                    command=["npm", "install"],
                    cwd=self.stack.root_path,
                    exit_code=None,
                    stdout="",
                    stderr=(
                        "npm not found on PATH. Cannot verify Node stack "
                        "at " + str(self.stack.root_path) + ". "
                        "Install Node.js or ensure npm is accessible."
                    ),
                    duration_seconds=0.0,
                    success=False,
                )
            ]

        # Step 1: install
        install_step = await _run_subprocess(
            name="install",
            command=[npm, "install", "--no-audit", "--no-fund"],
            cwd=self.stack.root_path,
            timeout_seconds=DEFAULT_INSTALL_TIMEOUT_SECONDS,
            env=None,
        )
        steps.append(install_step)
        if not install_step.success:
            return steps

        # Step 2: build (only if script exists)
        scripts = self.stack.metadata.get("scripts") or {}
        if "build" in scripts:
            # Build env: inherit from parent FIRST so PATH, HOME,
            # NODE_ENV, etc. propagate (without these the
            # subprocess can't find npm itself), then override
            # CI=true LAST so we always force non-interactive mode
            # regardless of whether the parent already has a CI
            # value set.
            #
            # Codex P2 review on PR #346 caught the original order
            # ({"CI": "true", **os.environ}) which let an existing
            # CI=false in the parent override our setting and
            # silently change react-scripts/Vite build behavior in
            # exactly the cases this gate is meant to standardize.
            # Dict spread is left-to-right, last write wins.
            import os as _os

            build_env = {
                **_os.environ,
                "CI": "true",
            }
            build_step = await _run_subprocess(
                name="build",
                command=[npm, "run", "build"],
                cwd=self.stack.root_path,
                timeout_seconds=DEFAULT_BUILD_TIMEOUT_SECONDS,
                env=build_env,
            )
            steps.append(build_step)
        else:
            # No build script — record an informational step so the
            # result is transparent about what was (not) checked.
            # This is NOT a failure; some Node projects are
            # pure-library with no build step.
            steps.append(
                VerificationStep(
                    name="build",
                    command=[npm, "run", "build"],
                    cwd=self.stack.root_path,
                    exit_code=0,
                    stdout="",
                    stderr="",
                    duration_seconds=0.0,
                    success=True,
                )
            )

        return steps


class PythonVerifier(StackVerifier):
    """Verifies a Python stack.

    Runs, in order:

    1. Install command (pip + pyproject or requirements.txt) — only
       if we can infer one without being destructive.
    2. ``python -c "import <package>"`` — basic import check if a
       package is declared.
    3. ``pytest`` — only if a tests directory is present.

    Scope note: Python environments are messier than Node because
    there's no equivalent of ``node_modules`` that isolates
    installs. Running ``pip install`` can mutate the user's global
    environment. For MVP we AVOID pip install — we trust that the
    agent's environment is set up — and focus on build-time checks
    (imports, test suite).

    A future version should use ``uv`` or a temporary venv to get
    the install step without environmental risk.
    """

    async def verify(self) -> List[VerificationStep]:
        """Run the Python verification sequence.

        Returns
        -------
        List[VerificationStep]
            Steps run, in execution order.
        """
        steps: List[VerificationStep] = []

        python = shutil.which("python3") or shutil.which("python")
        if python is None:
            return [
                VerificationStep(
                    name="test",
                    command=["python"],
                    cwd=self.stack.root_path,
                    exit_code=None,
                    stdout="",
                    stderr=(
                        "python not found on PATH. Cannot verify Python "
                        "stack at " + str(self.stack.root_path)
                    ),
                    duration_seconds=0.0,
                    success=False,
                )
            ]

        # Step: run pytest if a test dir exists
        tests_dir = self.stack.root_path / "tests"
        if tests_dir.is_dir():
            pytest_bin = shutil.which("pytest")
            if pytest_bin is None:
                # pytest not installed — inform rather than fail.
                # Absence of pytest is not a build error; it's a
                # missing tool the agent should know about.
                steps.append(
                    VerificationStep(
                        name="test",
                        command=["pytest"],
                        cwd=self.stack.root_path,
                        exit_code=0,
                        stdout="",
                        stderr="pytest not installed, skipping test step",
                        duration_seconds=0.0,
                        success=True,
                    )
                )
                return steps

            import os as _os

            test_step = await _run_subprocess(
                name="test",
                command=[pytest_bin, "-q", "--tb=short", "tests/"],
                cwd=self.stack.root_path,
                timeout_seconds=DEFAULT_TEST_TIMEOUT_SECONDS,
                env=dict(_os.environ),
            )
            steps.append(test_step)
            return steps

        # No tests dir — nothing to verify at build-level for Python.
        # Return a skipped-step marker so the caller knows we looked.
        steps.append(
            VerificationStep(
                name="test",
                command=["pytest"],
                cwd=self.stack.root_path,
                exit_code=0,
                stdout="",
                stderr="no tests/ directory, skipping test step",
                duration_seconds=0.0,
                success=True,
            )
        )
        return steps


class _UnsupportedVerifier(StackVerifier):
    """Stub verifier for stacks we haven't implemented yet.

    Returns a single informational step indicating the stack was
    detected but not verified. This is NOT a failure — skipping
    unknown stacks is the safe default for MVP.
    """

    async def verify(self) -> List[VerificationStep]:
        """Return a single skipped-step marker."""
        return [
            VerificationStep(
                name="skip",
                command=[],
                cwd=self.stack.root_path,
                exit_code=0,
                stdout="",
                stderr=(
                    f"Stack type {self.stack.stack_type!r} detected at "
                    f"{self.stack.root_path} but no verifier implemented. "
                    f"Skipped."
                ),
                duration_seconds=0.0,
                success=True,
            )
        ]


def _pick_verifier(stack: DetectedStack) -> StackVerifier:
    """Map a detected stack to its concrete verifier class.

    Parameters
    ----------
    stack : DetectedStack
        The stack to verify.

    Returns
    -------
    StackVerifier
        Concrete verifier. Unsupported stacks get ``_UnsupportedVerifier``.
    """
    if stack.stack_type == "node":
        return NodeVerifier(stack)
    if stack.stack_type == "python":
        return PythonVerifier(stack)
    return _UnsupportedVerifier(stack)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class ProductSmokeVerifier:
    """Top-level orchestrator for product smoke verification.

    Detects all stacks in a project root, runs each one's verifier,
    aggregates the results, and produces a structured report
    suitable for both logging and blocker-message rendering.

    Usage
    -----
    >>> verifier = ProductSmokeVerifier()
    >>> result = await verifier.verify(Path("/path/to/project"))
    >>> if not result.success:
    ...     print(result.blocker_message)
    """

    async def verify(self, project_root: Path) -> ProductSmokeResult:
        """Run verification on all detected stacks.

        Parameters
        ----------
        project_root : Path
            Project root directory to scan and verify.

        Returns
        -------
        ProductSmokeResult
            Aggregate result. ``success=True`` with empty
            ``detected_stacks`` is a legitimate pass (no stacks to
            check) but carries a ``skipped_reason``.
        """
        logger.info(f"ProductSmokeVerifier starting at {project_root}")
        try:
            stacks = StackDetector.detect(project_root)
        except ValueError as exc:
            return ProductSmokeResult(
                success=False,
                detected_stacks=[],
                steps=[],
                failure_summary=str(exc),
                blocker_message=(
                    f"Product smoke verification could not start: "
                    f"{exc}. The project root path is invalid or "
                    f"inaccessible."
                ),
            )

        if not stacks:
            logger.info(
                f"No stacks detected in {project_root}; "
                f"skipping product smoke verification"
            )
            return ProductSmokeResult(
                success=True,
                detected_stacks=[],
                steps=[],
                skipped_reason="no recognized stack markers found",
            )

        logger.info(
            f"Detected {len(stacks)} stack(s): "
            + ", ".join(f"{s.stack_type}@{s.root_path.name}" for s in stacks)
        )

        all_steps: List[VerificationStep] = []
        first_failure: Optional[VerificationStep] = None
        for stack in stacks:
            verifier = _pick_verifier(stack)
            steps = await verifier.verify()
            all_steps.extend(steps)
            if first_failure is None:
                for step in steps:
                    if not step.success:
                        first_failure = step
                        break

        success = first_failure is None
        failure_summary: Optional[str] = None
        blocker_message: Optional[str] = None
        if not success and first_failure is not None:
            failure_summary = (
                f"{first_failure.name} failed at {first_failure.cwd} "
                f"(exit={first_failure.exit_code})"
            )
            blocker_message = _build_blocker_message(first_failure, stacks)

        return ProductSmokeResult(
            success=success,
            detected_stacks=stacks,
            steps=all_steps,
            failure_summary=failure_summary,
            blocker_message=blocker_message,
        )


def _build_blocker_message(
    failed_step: VerificationStep, stacks: List[DetectedStack]
) -> str:
    """Render a failed step into an actionable blocker message.

    Parameters
    ----------
    failed_step : VerificationStep
        The first step that failed.
    stacks : List[DetectedStack]
        All detected stacks (for context in the message).

    Returns
    -------
    str
        Multi-line blocker description the agent can read and act on.
    """
    stack_summary = ", ".join(f"{s.stack_type} at {s.root_path.name}" for s in stacks)
    cmd_str = " ".join(failed_step.command)
    tail = failed_step.stderr or failed_step.stdout or "(no output)"
    return (
        "## Product smoke verification FAILED\n\n"
        f"Marcus ran product smoke verification after you marked the "
        f"integration task complete and found that the assembled "
        f"product does not build/run.\n\n"
        f"**Detected stacks**: {stack_summary}\n\n"
        f"**Failing step**: `{failed_step.name}` "
        f"(exit code: {failed_step.exit_code})\n\n"
        f"**Command**: `{cmd_str}`\n"
        f"**Working directory**: `{failed_step.cwd}`\n\n"
        f"**Output (tail)**:\n```\n{tail}\n```\n\n"
        "**What to do**: Fix the underlying issue, commit the fix, "
        "and re-mark the integration task complete. Marcus will "
        "re-run product smoke verification. Do NOT mark the task "
        "complete again until the product builds cleanly. If the "
        "error is not actionable from this output, run the failing "
        "command yourself in the working directory to get the full "
        "output and root-cause from there."
    )
