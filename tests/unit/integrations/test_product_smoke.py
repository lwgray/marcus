"""Unit tests for product_smoke (Layer 1 of the systemic fix).

Verifies that ``ProductSmokeVerifier`` actually catches the
classes of bug it's designed to catch — most importantly the
dashboard-v71 regression where a React project shipped without
``public/index.html`` and Marcus accepted the integration task as
complete because nobody ran ``npm run build``.

Test strategy
-------------
Each test creates a tmp directory shaped like a real project root
(via ``tmp_path``), then runs ``StackDetector`` and/or one of the
verifier classes against it. Subprocess-running tests are gated
by a feature-detect of ``npm`` / ``python3`` on PATH so they
degrade gracefully on CI runners that don't have the toolchains
installed — the assertion strategy is "the verifier reports the
right structured outcome", not "the build actually succeeds".

When subprocess-running tests are skipped, we still verify the
dispatch logic, the failure message rendering, and the
integration with ``ProductSmokeVerifier`` orchestration via
mocked subprocess invocation.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.integrations.product_smoke import (
    DetectedStack,
    NodeVerifier,
    ProductSmokeResult,
    ProductSmokeVerifier,
    PythonVerifier,
    StackDetector,
    VerificationStep,
    _build_blocker_message,
    _pick_verifier,
    _UnsupportedVerifier,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# StackDetector tests
# ---------------------------------------------------------------------------


class TestStackDetector:
    """Stack detection from filesystem markers."""

    def test_empty_directory_returns_no_stacks(self, tmp_path: Path) -> None:
        """Empty repo → empty stack list, no exceptions."""
        stacks = StackDetector.detect(tmp_path)
        assert stacks == []

    def test_node_project_at_root(self, tmp_path: Path) -> None:
        """package.json at repo root → one Node stack."""
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "test-project",
                    "version": "1.0.0",
                    "scripts": {"build": "react-scripts build"},
                    "dependencies": {"react": "^18.0.0"},
                }
            )
        )
        stacks = StackDetector.detect(tmp_path)
        assert len(stacks) == 1
        assert stacks[0].stack_type == "node"
        assert stacks[0].root_path == tmp_path
        assert "build" in stacks[0].metadata["scripts"]

    def test_python_project_at_root(self, tmp_path: Path) -> None:
        """pyproject.toml at repo root → one Python stack."""
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='test'\nversion='1.0'\n"
        )
        stacks = StackDetector.detect(tmp_path)
        assert len(stacks) == 1
        assert stacks[0].stack_type == "python"

    def test_full_stack_project_detects_both(self, tmp_path: Path) -> None:
        """Frontend + backend in subdirs → two stacks detected."""
        # Frontend
        frontend = tmp_path / "src" / "frontend"
        frontend.mkdir(parents=True)
        (frontend / "package.json").write_text(
            json.dumps({"name": "fe", "scripts": {"build": "vite build"}})
        )
        # Backend
        backend = tmp_path / "src" / "backend"
        backend.mkdir(parents=True)
        (backend / "pyproject.toml").write_text("[project]\nname='backend'\n")
        stacks = StackDetector.detect(tmp_path)
        stack_types = sorted(s.stack_type for s in stacks)
        assert stack_types == ["node", "python"]

    def test_node_modules_is_skipped(self, tmp_path: Path) -> None:
        """Vendor package.json files in node_modules must not match."""
        # Real package.json at root
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "app", "scripts": {}})
        )
        # Fake vendor package.json that should be skipped
        nm = tmp_path / "node_modules" / "react"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text(json.dumps({"name": "react", "scripts": {}}))
        stacks = StackDetector.detect(tmp_path)
        # Only the root package.json counts
        assert len(stacks) == 1
        assert stacks[0].root_path == tmp_path

    def test_invalid_root_raises(self, tmp_path: Path) -> None:
        """Passing a non-directory raises ValueError."""
        bogus = tmp_path / "does-not-exist"
        with pytest.raises(ValueError, match="not a directory"):
            StackDetector.detect(bogus)

    def test_malformed_package_json_does_not_crash(self, tmp_path: Path) -> None:
        """A package.json that isn't valid JSON returns a stack
        with parse_error metadata, not a crash."""
        (tmp_path / "package.json").write_text("{not valid json")
        stacks = StackDetector.detect(tmp_path)
        assert len(stacks) == 1
        assert "parse_error" in stacks[0].metadata


# ---------------------------------------------------------------------------
# Helper to build a fake successful subprocess for verifier tests
# ---------------------------------------------------------------------------


def _make_step(
    name: str,
    success: bool = True,
    exit_code: int = 0,
    stderr: str = "",
    cwd: Path | None = None,
) -> VerificationStep:
    """Build a VerificationStep without running a subprocess."""
    return VerificationStep(
        name=name,
        command=["fake"],
        cwd=cwd or Path.cwd(),
        exit_code=exit_code,
        stdout="",
        stderr=stderr,
        duration_seconds=0.0,
        success=success,
    )


# ---------------------------------------------------------------------------
# NodeVerifier tests
# ---------------------------------------------------------------------------


class TestNodeVerifier:
    """Node verifier dispatches subprocess correctly per stack metadata."""

    @pytest.mark.asyncio
    async def test_node_verifier_runs_install_then_build_when_script_present(
        self, tmp_path: Path
    ) -> None:
        """package.json with build script → install + build steps."""
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"build": "echo built"}})
        )
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path / "package.json",
            metadata={"scripts": {"build": "echo built"}},
        )

        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            mock_run.side_effect = [
                _make_step("install", success=True),
                _make_step("build", success=True),
            ]
            verifier = NodeVerifier(stack)
            steps = await verifier.verify()

        assert len(steps) == 2
        assert [s.name for s in steps] == ["install", "build"]
        assert all(s.success for s in steps)
        assert mock_run.call_count == 2

    @pytest.mark.asyncio
    async def test_node_verifier_skips_build_when_no_script(
        self, tmp_path: Path
    ) -> None:
        """No build script → install only, build step is a skip marker."""
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path / "package.json",
            metadata={"scripts": {}},
        )
        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            mock_run.return_value = _make_step("install", success=True)
            verifier = NodeVerifier(stack)
            steps = await verifier.verify()

        # install ran via subprocess; build was a skip marker (success
        # without subprocess call)
        assert mock_run.call_count == 1
        assert len(steps) == 2
        assert steps[1].name == "build"
        assert steps[1].duration_seconds == 0.0  # didn't actually run

    @pytest.mark.asyncio
    async def test_node_verifier_short_circuits_on_install_failure(
        self, tmp_path: Path
    ) -> None:
        """Install failure → no build attempt."""
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path / "package.json",
            metadata={"scripts": {"build": "build cmd"}},
        )
        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            mock_run.return_value = _make_step(
                "install", success=False, exit_code=1, stderr="no internet"
            )
            verifier = NodeVerifier(stack)
            steps = await verifier.verify()

        assert len(steps) == 1
        assert steps[0].name == "install"
        assert steps[0].success is False
        assert mock_run.call_count == 1  # build was never attempted

    @pytest.mark.asyncio
    async def test_node_verifier_handles_missing_npm(self, tmp_path: Path) -> None:
        """npm not on PATH → returns a clear failure step."""
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path / "package.json",
            metadata={"scripts": {}},
        )
        with patch("shutil.which", return_value=None):
            verifier = NodeVerifier(stack)
            steps = await verifier.verify()

        assert len(steps) == 1
        assert steps[0].success is False
        assert "npm not found" in steps[0].stderr.lower()

    @pytest.mark.asyncio
    async def test_build_env_forces_ci_true_over_parent_env(
        self, tmp_path: Path
    ) -> None:
        """
        Codex P2 regression on PR #346.

        The build env must override any pre-existing CI value from
        the parent process. The original order
        (``{"CI": "true", **os.environ}``) silently let
        ``CI=false`` from the parent override our setting,
        defeating the non-interactive mode this gate is meant to
        standardize. Order matters in dict spread — last write
        wins, so the override must come AFTER the spread.

        This test pins the fix: even with ``CI=false`` set in the
        parent, the env passed to the build subprocess has
        ``CI=true``. PATH is still inherited (sanity check we
        didn't accidentally drop the parent env entirely).
        """
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path / "package.json",
            metadata={"scripts": {"build": "react-scripts build"}},
        )

        captured_env: dict = {}

        async def _capture_env(
            name: str,
            command: list,
            cwd: Path,
            timeout_seconds: float,
            env=None,
        ) -> VerificationStep:
            if name == "build" and env is not None:
                captured_env.update(env)
            return _make_step(name, success=True)

        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new=_capture_env,
            ),
            patch("shutil.which", return_value="/usr/bin/npm"),
            patch.dict("os.environ", {"CI": "false", "PATH": "/usr/bin"}, clear=False),
        ):
            verifier = NodeVerifier(stack)
            await verifier.verify()

        # CI must be "true" even though parent env had "false"
        assert captured_env.get("CI") == "true", (
            f"CI must be forced to 'true' regardless of parent env. "
            f"Got: {captured_env.get('CI')!r}"
        )
        # PATH must still be inherited (we didn't drop parent env)
        assert "PATH" in captured_env


# ---------------------------------------------------------------------------
# PythonVerifier tests
# ---------------------------------------------------------------------------


class TestPythonVerifier:
    """Python verifier detects pytest and runs it when tests/ exists."""

    @pytest.mark.asyncio
    async def test_python_verifier_runs_pytest_when_tests_dir_exists(
        self, tmp_path: Path
    ) -> None:
        """tests/ directory present → pytest invoked."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
        (tmp_path / "tests").mkdir()
        stack = DetectedStack(
            stack_type="python",
            root_path=tmp_path,
            marker_file=tmp_path / "pyproject.toml",
        )
        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch(
                "shutil.which",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
        ):
            mock_run.return_value = _make_step("test", success=True)
            verifier = PythonVerifier(stack)
            steps = await verifier.verify()

        assert len(steps) == 1
        assert steps[0].name == "test"
        assert steps[0].success is True
        mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_python_verifier_skips_when_no_tests_dir(
        self, tmp_path: Path
    ) -> None:
        """No tests/ directory → skipped, success=True."""
        stack = DetectedStack(
            stack_type="python",
            root_path=tmp_path,
            marker_file=tmp_path / "pyproject.toml",
        )
        with patch(
            "shutil.which",
            side_effect=lambda name: f"/usr/bin/{name}",
        ):
            verifier = PythonVerifier(stack)
            steps = await verifier.verify()

        assert len(steps) == 1
        assert steps[0].success is True
        assert "no tests" in steps[0].stderr.lower()


# ---------------------------------------------------------------------------
# Verifier dispatch
# ---------------------------------------------------------------------------


class TestVerifierDispatch:
    """``_pick_verifier`` returns the right concrete class per stack type."""

    def test_node_stack_picks_node_verifier(self, tmp_path: Path) -> None:
        stack = DetectedStack(
            stack_type="node",
            root_path=tmp_path,
            marker_file=tmp_path,
        )
        assert isinstance(_pick_verifier(stack), NodeVerifier)

    def test_python_stack_picks_python_verifier(self, tmp_path: Path) -> None:
        stack = DetectedStack(
            stack_type="python",
            root_path=tmp_path,
            marker_file=tmp_path,
        )
        assert isinstance(_pick_verifier(stack), PythonVerifier)

    def test_unsupported_stack_picks_unsupported(self, tmp_path: Path) -> None:
        """Go/Rust/Java fall through to the no-op stub."""
        stack = DetectedStack(
            stack_type="go",
            root_path=tmp_path,
            marker_file=tmp_path,
        )
        assert isinstance(_pick_verifier(stack), _UnsupportedVerifier)


# ---------------------------------------------------------------------------
# ProductSmokeVerifier orchestrator
# ---------------------------------------------------------------------------


class TestProductSmokeVerifier:
    """Top-level orchestrator behavior."""

    @pytest.mark.asyncio
    async def test_empty_repo_returns_success_with_skip_reason(
        self, tmp_path: Path
    ) -> None:
        """No detected stacks → pass with skipped_reason set."""
        result = await ProductSmokeVerifier().verify(tmp_path)
        assert result.success is True
        assert result.detected_stacks == []
        assert result.skipped_reason is not None

    @pytest.mark.asyncio
    async def test_single_stack_success(self, tmp_path: Path) -> None:
        """One Node stack, all steps pass → overall success."""
        (tmp_path / "package.json").write_text(json.dumps({"name": "x", "scripts": {}}))
        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            mock_run.return_value = _make_step("install", success=True)
            result = await ProductSmokeVerifier().verify(tmp_path)

        assert result.success is True
        assert len(result.detected_stacks) == 1
        assert result.failure_summary is None
        assert result.blocker_message is None

    @pytest.mark.asyncio
    async def test_first_failure_short_circuits_summary(self, tmp_path: Path) -> None:
        """When a step fails, failure_summary names that step."""
        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"build": "x"}})
        )
        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            mock_run.return_value = _make_step(
                "install", success=False, exit_code=2, stderr="boom"
            )
            result = await ProductSmokeVerifier().verify(tmp_path)

        assert result.success is False
        assert result.failure_summary is not None
        assert "install" in result.failure_summary
        assert result.blocker_message is not None
        assert "boom" in result.blocker_message

    @pytest.mark.asyncio
    async def test_v71_regression_missing_index_html_is_caught(
        self, tmp_path: Path
    ) -> None:
        """
        REGRESSION TEST FOR DASHBOARD-V71.

        A React project missing public/index.html must produce a
        verification failure when ProductSmokeVerifier runs. This
        is the exact bug shape that v71 shipped: every src/ file
        was correct, all unit tests passed, but `npm start` fails
        with "Could not find a required file. Name: index.html"
        because react-scripts requires the HTML shell.

        We simulate the failure by mocking the build subprocess to
        return the actual react-scripts error message. The test
        proves that the orchestrator correctly:
        1. Detects the Node stack
        2. Runs the build step
        3. Surfaces the build error in the blocker message
        4. Returns success=False
        """
        # Build a v71-shaped React project (everything except index.html)
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "dashboard",
                    "version": "1.0.0",
                    "scripts": {
                        "start": "react-scripts start",
                        "build": "react-scripts build",
                    },
                    "dependencies": {"react": "^18.0.0"},
                }
            )
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "index.tsx").write_text(
            "import React from 'react';\n"
            "import ReactDOM from 'react-dom/client';\n"
            "ReactDOM.createRoot(document.getElementById('root')!)"
            ".render(<div>hi</div>);\n"
        )
        (tmp_path / "public").mkdir()
        # NO index.html — this is the v71 bug shape

        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch("shutil.which", return_value="/usr/bin/npm"),
        ):
            # First call: install succeeds. Second call: build fails
            # with the actual react-scripts error message.
            mock_run.side_effect = [
                _make_step("install", success=True),
                _make_step(
                    "build",
                    success=False,
                    exit_code=1,
                    stderr=(
                        "Could not find a required file.\n"
                        "  Name: index.html\n"
                        "  Searched in: " + str(tmp_path / "public")
                    ),
                ),
            ]
            result = await ProductSmokeVerifier().verify(tmp_path)

        assert result.success is False, (
            "v71 regression: missing public/index.html must fail "
            "product smoke verification"
        )
        assert result.blocker_message is not None
        assert "index.html" in result.blocker_message, (
            "blocker must surface the actual react-scripts error so "
            "the agent knows what to fix"
        )
        # The build step should be the failing one
        build_steps = [s for s in result.steps if s.name == "build"]
        assert len(build_steps) == 1
        assert build_steps[0].success is False

    @pytest.mark.asyncio
    async def test_multi_stack_runs_all_stacks(self, tmp_path: Path) -> None:
        """Frontend + backend → both verified."""
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text(
            json.dumps({"name": "fe", "scripts": {}})
        )
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\nname='be'\n")

        with (
            patch(
                "src.integrations.product_smoke._run_subprocess",
                new_callable=AsyncMock,
            ) as mock_run,
            patch(
                "shutil.which",
                side_effect=lambda name: f"/usr/bin/{name}",
            ),
        ):
            mock_run.return_value = _make_step("install", success=True)
            result = await ProductSmokeVerifier().verify(tmp_path)

        stack_types = sorted(s.stack_type for s in result.detected_stacks)
        assert stack_types == ["node", "python"]
        assert result.success is True

    @pytest.mark.asyncio
    async def test_invalid_project_root_returns_failure(self, tmp_path: Path) -> None:
        """Bogus path → structured failure, not exception."""
        bogus = tmp_path / "does-not-exist"
        result = await ProductSmokeVerifier().verify(bogus)
        assert result.success is False
        assert result.failure_summary is not None


# ---------------------------------------------------------------------------
# Result serialization & blocker rendering
# ---------------------------------------------------------------------------


class TestResultRendering:
    """``ProductSmokeResult`` serializes cleanly for logs/blockers."""

    def test_to_dict_has_required_keys(self, tmp_path: Path) -> None:
        result = ProductSmokeResult(
            success=False,
            detected_stacks=[
                DetectedStack(
                    stack_type="node",
                    root_path=tmp_path,
                    marker_file=tmp_path,
                )
            ],
            steps=[_make_step("install", success=False, stderr="bad")],
            failure_summary="install failed",
            blocker_message="fix it",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert len(d["detected_stacks"]) == 1
        assert len(d["steps"]) == 1
        assert d["failure_summary"] == "install failed"

    def test_blocker_message_includes_command_and_stderr_tail(
        self, tmp_path: Path
    ) -> None:
        """The blocker message must contain enough info to debug."""
        step = VerificationStep(
            name="build",
            command=["npm", "run", "build"],
            cwd=tmp_path,
            exit_code=1,
            stdout="",
            stderr="ENOENT: index.html",
            duration_seconds=2.5,
            success=False,
        )
        stacks = [
            DetectedStack(stack_type="node", root_path=tmp_path, marker_file=tmp_path)
        ]
        msg = _build_blocker_message(step, stacks)
        assert "FAILED" in msg
        assert "npm run build" in msg
        assert "ENOENT" in msg
        assert "exit code: 1" in msg.lower() or "exit code: 1" in msg
