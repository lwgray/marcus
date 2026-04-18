"""
Unit tests for the log_artifact git-tracked file guardrail (GH-385 fix #7).

When an agent calls log_artifact with a path that resolves to a git-tracked
source file, the tool must reject the write and return a descriptive error.
dashboard-v82 post-mortem: Agent 1 overwrote theme.css and design-tokens.json
via log_artifact and had to restore from git (commit d44dd5a).

Tests:
- tracked file → rejected with clear error message
- untracked file → write proceeds normally
- git not available → write proceeds (fail-open so non-git projects work)
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.marcus_mcp.tools.attachment import log_artifact

# Pre-stub the live_experiment_monitor module so that tests which patch
# subprocess.run don't accidentally trigger mlflow's module-level
# subprocess.check_output call (platform detection) when the real module
# would be imported for the first time inside log_artifact's function body.
_MONITOR_MODULE_PATH = "src.experiments.live_experiment_monitor"
if _MONITOR_MODULE_PATH not in sys.modules:
    _mock_monitor_mod = Mock()
    _mock_monitor_mod.get_active_monitor = Mock(return_value=None)
    sys.modules[_MONITOR_MODULE_PATH] = _mock_monitor_mod

pytestmark = pytest.mark.unit


class _MockState:
    """Minimal state stub for log_artifact calls."""

    def __init__(self) -> None:
        self.task_artifacts: Dict[str, List[Dict[str, Any]]] = {}
        self.project_tasks: List[Any] = []
        self.kanban_client: Any = None


@pytest.fixture()
def state() -> _MockState:
    """Return a fresh MockState for each test."""
    return _MockState()


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Return a temporary directory to use as project_root."""
    return tmp_path


class TestLogArtifactGitGuard:
    """Tests for the git-tracked file write guard."""

    @pytest.mark.asyncio
    async def test_rejects_git_tracked_file(
        self, project_root: Path, state: _MockState
    ) -> None:
        """
        Verify log_artifact returns an error when the target file is tracked by git.

        The guard calls ``git ls-files --error-unmatch``; returncode 0 means
        tracked. The tool must refuse the write without touching the filesystem.
        """
        tracked_file = project_root / "src" / "widgets" / "theme.css"

        tracked_result = Mock(spec=subprocess.CompletedProcess)
        tracked_result.returncode = 0

        with patch(
            "src.marcus_mcp.tools.attachment.subprocess.run",
            return_value=tracked_result,
        ):
            result = await log_artifact(
                task_id="task-1",
                filename="theme.css",
                content="body { color: red; }",
                artifact_type="design",
                project_root=str(project_root),
                location=str(tracked_file.relative_to(project_root)),
                state=state,
            )

        assert result["success"] is False
        assert "git-tracked" in result["error"]
        assert not tracked_file.exists(), "Guard must not write the file"

    @pytest.mark.asyncio
    async def test_allows_untracked_file(
        self, project_root: Path, state: _MockState
    ) -> None:
        """
        Verify log_artifact proceeds normally when the target is not tracked.

        git ls-files --error-unmatch exits non-zero for untracked paths.
        The tool should write the artifact to docs/ as usual.
        """
        untracked_result = Mock(spec=subprocess.CompletedProcess)
        untracked_result.returncode = 1

        with (
            patch(
                "src.marcus_mcp.tools.attachment.subprocess.run",
                return_value=untracked_result,
            ),
            patch(
                "src.marcus_mcp.tools.attachment._persist_artifact_to_history",
                new_callable=AsyncMock,
            ),
        ):
            result = await log_artifact(
                task_id="task-2",
                filename="design-spec.md",
                content="# Design Spec",
                artifact_type="design",
                project_root=str(project_root),
                state=state,
            )

        assert result["success"] is True
        written = project_root / "docs" / "design" / "design-spec.md"
        assert written.exists()
        assert written.read_text() == "# Design Spec"

    @pytest.mark.asyncio
    async def test_proceeds_when_git_not_available(
        self, project_root: Path, state: _MockState
    ) -> None:
        """
        Verify log_artifact proceeds when git is not installed.

        The guard must be fail-open: non-git projects and CI environments
        without git should not be blocked from writing artifacts.
        """
        with (
            patch(
                "src.marcus_mcp.tools.attachment.subprocess.run",
                side_effect=FileNotFoundError("git: No such file"),
            ),
            patch(
                "src.marcus_mcp.tools.attachment._persist_artifact_to_history",
                new_callable=AsyncMock,
            ),
        ):
            result = await log_artifact(
                task_id="task-3",
                filename="api-spec.md",
                content="# API",
                artifact_type="api",
                project_root=str(project_root),
                state=state,
            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_error_message_names_the_path(
        self, project_root: Path, state: _MockState
    ) -> None:
        """
        Verify the rejection error message includes the offending relative path.

        Agents need to know WHICH file was rejected, not just that a rejection
        happened, so they can choose an appropriate docs/ location instead.
        """
        tracked_result = Mock(spec=subprocess.CompletedProcess)
        tracked_result.returncode = 0

        with patch(
            "src.marcus_mcp.tools.attachment.subprocess.run",
            return_value=tracked_result,
        ):
            result = await log_artifact(
                task_id="task-4",
                filename="design-tokens.json",
                content='{"color": "blue"}',
                artifact_type="design",
                project_root=str(project_root),
                location="src/styles/design-tokens.json",
                state=state,
            )

        assert result["success"] is False
        assert (
            "design-tokens.json" in result["error"] or "src/styles" in result["error"]
        )
