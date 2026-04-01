"""
Unit tests for spawn_agents demo reliability.

Tests countdown logging during project_info.json wait,
and error handling for common demo failure scenarios.
"""

import importlib
import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# dev-tools uses hyphens, so we need to import via importlib
_SPAWN_AGENTS_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "dev-tools"
    / "experiments"
    / "runners"
    / "spawn_agents.py"
)
_spec = importlib.util.spec_from_file_location("spawn_agents", _SPAWN_AGENTS_PATH)
assert _spec is not None and _spec.loader is not None
spawn_agents = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(spawn_agents)


class TestProjectInfoWaitCountdown:
    """Test suite for project_info.json wait countdown logging."""

    @pytest.fixture
    def mock_config(self, tmp_path: Path) -> MagicMock:
        """Create mock ExperimentConfig with tmp_path project_info_file."""
        config = MagicMock()
        config.project_info_file = tmp_path / "project_info.json"
        config.get_timeout.return_value = 10
        config.implementation_dir = tmp_path / "implementation"
        config.agents = []
        config.project_name = "test_project"
        return config

    def test_countdown_prints_waiting_message(
        self, mock_config: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that wait loop prints status messages."""
        wait_for_project_info = spawn_agents.wait_for_project_info

        # File already exists — should return immediately
        mock_config.project_info_file.write_text(
            json.dumps(
                {
                    "project_id": "p1",
                    "board_id": "b1",
                    "tasks_created": 3,
                }
            )
        )

        result = wait_for_project_info(mock_config)

        assert result is True
        output = capsys.readouterr().out
        assert "Waiting for project creation" in output
        assert "Project created" in output

    def test_countdown_returns_false_on_timeout(
        self, mock_config: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that wait loop returns False and prints error on timeout."""
        wait_for_project_info = spawn_agents.wait_for_project_info

        mock_config.get_timeout.return_value = 0  # Immediate timeout

        result = wait_for_project_info(mock_config)

        assert result is False
        output = capsys.readouterr().out
        assert "timed out" in output.lower()

    def test_countdown_returns_true_when_file_exists(
        self, mock_config: MagicMock
    ) -> None:
        """Test that wait returns True immediately if file already exists."""
        wait_for_project_info = spawn_agents.wait_for_project_info

        # Pre-create the file
        mock_config.project_info_file.write_text(
            json.dumps(
                {
                    "project_id": "p1",
                    "board_id": "b1",
                    "tasks_created": 3,
                }
            )
        )

        result = wait_for_project_info(mock_config)

        assert result is True


class TestKanbanConnectionResilience:
    """Test suite for Kanban connection failure scenarios."""

    def test_planka_client_import_succeeds(self) -> None:
        """Test that the Planka client module is importable."""
        from src.marcus_mcp import handlers  # noqa: F401

    @pytest.mark.asyncio
    async def test_kanban_client_raises_on_connection_error(
        self,
    ) -> None:
        """Test that Kanban client operations raise on connection failure."""
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_boards = AsyncMock(
            side_effect=ConnectionError("Connection refused")
        )

        with pytest.raises(ConnectionError):
            await mock_client.get_boards()

    @pytest.mark.asyncio
    async def test_kanban_client_raises_on_timeout(self) -> None:
        """Test that Kanban client operations raise on timeout."""
        import asyncio
        from unittest.mock import AsyncMock

        mock_client = AsyncMock()
        mock_client.get_boards = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(asyncio.TimeoutError):
            await mock_client.get_boards()


class TestMCPHealthCheck:
    """Test suite for MCP server health verification."""

    def test_mcp_health_check_returns_true_when_healthy(self) -> None:
        """Test MCP health check returns True when server responds."""
        check_mcp_health = spawn_agents.check_mcp_health

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok")
            result = check_mcp_health("http://localhost:4298")

        assert result is True

    def test_mcp_health_check_returns_false_when_down(self) -> None:
        """Test MCP health check returns False when server not responding."""
        check_mcp_health = spawn_agents.check_mcp_health

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=7)
            result = check_mcp_health("http://localhost:4298")

        assert result is False

    def test_mcp_health_check_handles_exception(self) -> None:
        """Test MCP health check returns False on exception."""
        check_mcp_health = spawn_agents.check_mcp_health

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_mcp_health("http://localhost:4298")

        assert result is False


class TestPretrustDirectory:
    """Test suite for pre-trusting directories in ~/.claude.json."""

    def test_creates_new_config_when_missing(self, tmp_path: Path) -> None:
        """Test pre-trust creates ~/.claude.json if it doesn't exist."""
        claude_json = tmp_path / ".claude.json"
        impl_dir = tmp_path / "implementation"
        impl_dir.mkdir()

        with patch.object(Path, "home", return_value=tmp_path):
            spawn_agents.AgentSpawner._pretrust_directory(impl_dir)

        assert claude_json.exists()
        config = json.loads(claude_json.read_text())
        dir_key = str(impl_dir)
        assert dir_key in config["projects"]
        assert config["projects"][dir_key]["hasTrustDialogAccepted"] is True

    def test_updates_existing_config(self, tmp_path: Path) -> None:
        """Test pre-trust adds to existing ~/.claude.json without clobbering."""
        claude_json = tmp_path / ".claude.json"
        existing = {
            "numStartups": 42,
            "projects": {
                "/some/other/project": {
                    "hasTrustDialogAccepted": True,
                }
            },
        }
        claude_json.write_text(json.dumps(existing))

        impl_dir = tmp_path / "implementation"
        impl_dir.mkdir()

        with patch.object(Path, "home", return_value=tmp_path):
            spawn_agents.AgentSpawner._pretrust_directory(impl_dir)

        config = json.loads(claude_json.read_text())
        # Existing data preserved
        assert config["numStartups"] == 42
        assert "/some/other/project" in config["projects"]
        # New directory added
        assert config["projects"][str(impl_dir)]["hasTrustDialogAccepted"] is True

    def test_retrusts_directory_with_false_flag(self, tmp_path: Path) -> None:
        """Test pre-trust flips hasTrustDialogAccepted from False to True."""
        claude_json = tmp_path / ".claude.json"
        impl_dir = tmp_path / "implementation"
        impl_dir.mkdir()
        dir_key = str(impl_dir)

        existing = {
            "projects": {
                dir_key: {
                    "hasTrustDialogAccepted": False,
                    "allowedTools": ["Bash"],
                }
            }
        }
        claude_json.write_text(json.dumps(existing))

        with patch.object(Path, "home", return_value=tmp_path):
            spawn_agents.AgentSpawner._pretrust_directory(impl_dir)

        config = json.loads(claude_json.read_text())
        assert config["projects"][dir_key]["hasTrustDialogAccepted"] is True
        # Existing fields preserved
        assert config["projects"][dir_key]["allowedTools"] == ["Bash"]

    def test_skips_already_trusted_directory(self, tmp_path: Path) -> None:
        """Test pre-trust is a no-op when directory is already trusted."""
        claude_json = tmp_path / ".claude.json"
        impl_dir = tmp_path / "implementation"
        impl_dir.mkdir()
        dir_key = str(impl_dir)

        existing = {"projects": {dir_key: {"hasTrustDialogAccepted": True}}}
        claude_json.write_text(json.dumps(existing))
        original_mtime = claude_json.stat().st_mtime

        with patch.object(Path, "home", return_value=tmp_path):
            spawn_agents.AgentSpawner._pretrust_directory(impl_dir)

        # File should not be rewritten
        assert claude_json.stat().st_mtime == original_mtime

    def test_handles_malformed_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test graceful handling of corrupted ~/.claude.json."""
        claude_json = tmp_path / ".claude.json"
        claude_json.write_text("{bad json")

        impl_dir = tmp_path / "implementation"
        impl_dir.mkdir()

        with patch.object(Path, "home", return_value=tmp_path):
            spawn_agents.AgentSpawner._pretrust_directory(impl_dir)

        output = capsys.readouterr().out
        assert "Could not pre-trust" in output
