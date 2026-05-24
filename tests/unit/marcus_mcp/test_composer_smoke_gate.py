"""Unit tests for the composer smoke gate (bug #649 root cause 2 — enforcement).

Background
----------
PR #650's first attempt at fixing bug #649 root cause 2 added a
text-only instruction to the composition task description ("DO NOT
MARK THIS TASK COMPLETE on a broken build").  That was a step but
not a gate — if the composer agent reported the task done anyway,
no Marcus layer rejected it.  The Kaia review of PR #650 surfaced
this as the gap.

This module's tests pin the **enforcement layer**: Marcus detects
the project's build tooling from the implementation directory
(mechanically, no LLM, no hardcoded language ontology) and runs the
universal build command for whichever package manifest is present.
On non-zero exit, the composition task is rejected.

Detection rules:

- ``package.json`` with ``scripts.build`` -> ``npm install && npm run build``
- ``pyproject.toml`` -> ``python -m compileall -q .``
  (compileall is in the stdlib; avoids requiring the ``build`` package)
- ``Cargo.toml`` -> ``cargo build --quiet``
- ``go.mod`` -> ``go build ./...``
- Nothing matches -> empty list (permissive pass; no build to verify)

Per Invariant #2 v2 (CLAUDE.md MULTIAGENCY_PROCLAMATION): Marcus
authors the verification command; the agent owns implementation.
The detection function maps a file-presence signal to the
universally-known build command for that toolchain — not a
prescriptive ontology, just the mechanical fact that ``package.json``
means Node.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _is_composition_task — task-type detection
# ---------------------------------------------------------------------------


class TestIsCompositionTask:
    """``_is_composition_task`` recognizes Marcus-synthesized composition tasks."""

    def _task(self, *, labels=None, source_type=None) -> MagicMock:
        """Minimal task stub with the attributes the detector reads."""
        task = MagicMock()
        task.labels = labels
        task.source_type = source_type
        return task

    def test_detects_via_composition_label(self) -> None:
        """Tasks with ``composition`` in labels are composition tasks."""
        from src.marcus_mcp.tools.task import _is_composition_task

        task = self._task(labels=["composition", "marcus_synthesized"])
        assert _is_composition_task(task) is True

    def test_detects_via_source_type(self) -> None:
        """Tasks with ``source_type='composition_synthesis'`` are composition tasks.

        Survives kanban round-trips that strip labels but preserve
        source_type (matches the existing detection at
        ``composition_synthesis.py:_has_existing_composition_task``).
        """
        from src.marcus_mcp.tools.task import _is_composition_task

        task = self._task(labels=[], source_type="composition_synthesis")
        assert _is_composition_task(task) is True

    def test_rejects_integration_task(self) -> None:
        """Integration tasks are not composition tasks (distinct gates)."""
        from src.marcus_mcp.tools.task import _is_composition_task

        task = self._task(labels=["type:integration", "integration"])
        assert _is_composition_task(task) is False

    def test_rejects_implementation_task(self) -> None:
        """Plain implementation tasks are not composition tasks."""
        from src.marcus_mcp.tools.task import _is_composition_task

        task = self._task(labels=["implementation"])
        assert _is_composition_task(task) is False

    def test_handles_missing_labels(self) -> None:
        """No labels and no source_type returns False (no crash)."""
        from src.marcus_mcp.tools.task import _is_composition_task

        task = self._task(labels=None, source_type=None)
        assert _is_composition_task(task) is False


# ---------------------------------------------------------------------------
# _detect_composer_build_specs — mechanical build-command detection
# ---------------------------------------------------------------------------


class TestDetectComposerBuildSpecs:
    """Mechanical detection from package manifest files in the project root."""

    def test_node_with_scripts_build_returns_npm_spec(self, tmp_path: Path) -> None:
        """package.json with ``scripts.build`` -> npm install && npm run build."""
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "name": "verify-snake-4",
                    "scripts": {"dev": "vite", "build": "vite build"},
                }
            )
        )
        specs = _detect_composer_build_specs(tmp_path)
        assert len(specs) == 1
        spec = specs[0]
        assert "npm" in spec.command
        assert "run build" in spec.command
        assert spec.signal_id  # non-empty

    def test_node_without_scripts_build_returns_empty(self, tmp_path: Path) -> None:
        """package.json with no ``scripts.build`` -> no spec (no build configured).

        Permissive default: if there's nothing to build (a pure
        static HTML+JS project may have package.json only for
        devDeps), the gate passes rather than fabricating a fake
        check.
        """
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "package.json").write_text(
            json.dumps({"name": "x", "scripts": {"start": "node main.js"}})
        )
        specs = _detect_composer_build_specs(tmp_path)
        assert specs == []

    def test_node_with_malformed_package_json_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """A corrupt package.json is treated as absent — gate stays permissive.

        Marcus should not fail to load on agent-side corruption; the
        ordinary smoke pipeline downstream catches truly broken
        projects.  Composer gate's job is only to reject when build
        is definitely broken.
        """
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "package.json").write_text("this is not json {{{")
        specs = _detect_composer_build_specs(tmp_path)
        assert specs == []

    def test_python_with_pyproject_returns_compileall_spec(
        self, tmp_path: Path
    ) -> None:
        """pyproject.toml present -> python -m compileall.

        Using ``compileall`` (stdlib) rather than ``python -m build``
        because the latter requires the ``build`` package which may
        not be installed.  Syntax-level compile is the minimum
        signal that the assembled Python project is at least
        parseable.
        """
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "pyproject.toml").write_text(
            "[build-system]\nrequires = ['hatchling']\n"
        )
        specs = _detect_composer_build_specs(tmp_path)
        assert len(specs) == 1
        assert "compileall" in specs[0].command

    def test_rust_cargo_toml_returns_cargo_build_spec(self, tmp_path: Path) -> None:
        """Cargo.toml -> cargo build."""
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "Cargo.toml").write_text(
            "[package]\nname = 'x'\nversion = '0.1.0'\n"
        )
        specs = _detect_composer_build_specs(tmp_path)
        assert len(specs) == 1
        assert "cargo build" in specs[0].command

    def test_go_mod_returns_go_build_spec(self, tmp_path: Path) -> None:
        """go.mod -> go build ./..."""
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "go.mod").write_text("module x\n\ngo 1.21\n")
        specs = _detect_composer_build_specs(tmp_path)
        assert len(specs) == 1
        assert "go build" in specs[0].command

    def test_empty_project_returns_empty(self, tmp_path: Path) -> None:
        """Empty project -> empty list (nothing to verify, permissive pass)."""
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        specs = _detect_composer_build_specs(tmp_path)
        assert specs == []

    def test_polyglot_project_returns_all_applicable_specs(
        self, tmp_path: Path
    ) -> None:
        """Multiple manifests present -> all applicable specs.

        Polyglot projects (rare but real — e.g. a JS frontend with a
        Python backend) should have ALL their build commands run.
        The gate either accepts all or rejects on the first failure.
        """
        from src.marcus_mcp.tools.task import _detect_composer_build_specs

        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"build": "vite build"}})
        )
        (tmp_path / "pyproject.toml").write_text("[build-system]\nrequires = []\n")
        specs = _detect_composer_build_specs(tmp_path)
        assert len(specs) == 2
        commands = {s.command for s in specs}
        assert any("npm" in c for c in commands)
        assert any("compileall" in c for c in commands)


# ---------------------------------------------------------------------------
# _run_composer_smoke_gate — full gate behavior
# ---------------------------------------------------------------------------


class TestRunComposerSmokeGate:
    """Composition completion gate — Marcus-authored, subprocess-enforced."""

    def _state(self, project_root: Path) -> MagicMock:
        """Mock Marcus state with workspace state pointing at ``project_root``."""
        state = MagicMock()
        kanban = MagicMock()
        kanban._load_workspace_state = MagicMock(
            return_value={"project_root": str(project_root)}
        )
        state.kanban_client = kanban
        return state

    def _composition_task(self) -> MagicMock:
        task = MagicMock()
        task.id = "composition_test"
        task.name = "Compose verify-snake-4 entry point"
        task.labels = ["composition", "marcus_synthesized"]
        task.source_type = "composition_synthesis"
        return task

    @pytest.mark.asyncio
    async def test_passes_when_no_build_configured(self, tmp_path: Path) -> None:
        """Empty project -> no specs -> gate passes (returns None).

        Permissive pass when there's nothing to verify — the
        composition root may legitimately be a pure static HTML
        project with no build step.
        """
        from src.marcus_mcp.tools.task import _run_composer_smoke_gate

        state = self._state(tmp_path)
        result = await _run_composer_smoke_gate(
            task=self._composition_task(), agent_id="agent_1", state=state
        )
        assert result is None  # Gate passed

    @pytest.mark.asyncio
    async def test_passes_when_subprocess_succeeds(self, tmp_path: Path) -> None:
        """Detected build that exits 0 -> gate passes."""
        from src.marcus_mcp.tools.task import _run_composer_smoke_gate

        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"build": "echo ok"}})
        )

        success_result = MagicMock()
        success_result.success = True
        success_result.failure_summary = ""

        state = self._state(tmp_path)
        with patch(
            "src.marcus_mcp.tools.task.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=success_result,
        ) as mock_verify:
            result = await _run_composer_smoke_gate(
                task=self._composition_task(),
                agent_id="agent_1",
                state=state,
            )

        assert result is None  # Gate passed
        mock_verify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_when_subprocess_fails(self, tmp_path: Path) -> None:
        """Detected build that exits non-zero -> gate rejects.

        This is the verify-snake-3 failure mode the fix targets:
        composer agent reported done, but ``npm run build`` would
        have failed with the @/physics/engine resolution error.
        Pre-fix nothing rejected.  Post-fix Marcus subprocess-runs
        the build and rejects.
        """
        from src.marcus_mcp.tools.task import _run_composer_smoke_gate

        (tmp_path / "package.json").write_text(
            json.dumps({"scripts": {"build": "vite build"}})
        )

        failure_result = MagicMock()
        failure_result.success = False
        failure_result.failure_summary = (
            "build failed: cannot resolve import @/physics/engine"
        )

        state = self._state(tmp_path)
        with patch(
            "src.marcus_mcp.tools.task.verify_verification_specs",
            new_callable=AsyncMock,
            return_value=failure_result,
        ):
            result = await _run_composer_smoke_gate(
                task=self._composition_task(),
                agent_id="agent_1",
                state=state,
            )

        assert result is not None
        assert result["success"] is False
        # Rejection carries enough info for the agent to fix the
        # underlying problem rather than retrying blindly.
        assert "build" in result.get("blocker", "").lower()
        assert result["task_id"] == "composition_test"

    @pytest.mark.asyncio
    async def test_logs_when_no_project_root_resolved(self) -> None:
        """Missing workspace state -> permissive pass with a warning log.

        Unlike the integration smoke gate (which hard-rejects on
        missing project_root because every integration task MUST be
        verifiable), the composer gate is best-effort: when Marcus
        cannot locate the implementation directory, the downstream
        integration verification catches anything still broken.
        Composer-gate failure-to-load should not block completion
        on a configuration glitch.
        """
        from src.marcus_mcp.tools.task import _run_composer_smoke_gate

        state = MagicMock()
        state.kanban_client = None  # No workspace state

        result = await _run_composer_smoke_gate(
            task=self._composition_task(), agent_id="agent_1", state=state
        )
        # Permissive: no rejection, downstream gate is the catch-all.
        assert result is None
