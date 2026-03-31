"""Unit tests for Marcus CLI status command."""

import argparse
import importlib.machinery
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Import the marcus CLI script as a module
_marcus_path = Path(__file__).resolve().parents[2] / "marcus"


def _import_marcus() -> types.ModuleType:
    """Import the marcus CLI script as a module.

    Returns
    -------
    types.ModuleType
        The marcus module.
    """
    loader = importlib.machinery.SourceFileLoader("marcus_cli", str(_marcus_path))
    spec = importlib.util.spec_from_loader("marcus_cli", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["marcus_cli"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestStatusShowsKanbanProvider:
    """Test that status command displays the kanban provider."""

    @pytest.fixture(scope="class")
    def marcus_module(self) -> types.ModuleType:
        """Import the marcus CLI module once for the class."""
        with patch("psutil.Process"):
            return _import_marcus()

    @pytest.fixture
    def cli(self, marcus_module: types.ModuleType) -> Any:
        """Create a MarcusCLI instance."""
        return marcus_module.MarcusCLI()

    @pytest.fixture
    def args(self) -> argparse.Namespace:
        """Create a minimal args namespace for status."""
        return argparse.Namespace(command="status")

    @pytest.mark.unit
    def test_status_displays_kanban_provider_when_running(
        self,
        cli: Any,
        args: argparse.Namespace,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that status shows kanban provider when Marcus is running."""
        with (
            patch.object(cli, "_is_running", return_value=True),
            patch.object(cli, "_get_pid", return_value=12345),
            patch.object(cli, "_get_git_commit", return_value="abc1234 some msg"),
            patch("psutil.Process") as mock_process,
            patch("marcus_cli.get_config") as mock_config,
            patch("marcus_cli.get_kanban_provider", return_value="sqlite"),
        ):
            proc = MagicMock()
            proc.cpu_percent.return_value = 1.0
            proc.memory_info.return_value = MagicMock(rss=50 * 1024 * 1024)
            proc.create_time.return_value = 1000000.0
            mock_process.return_value = proc

            config_obj = MagicMock()
            config_obj.get.return_value = {"type": "stdio"}
            mock_config.return_value = config_obj

            # Mock the multi config file to not exist
            cli.pid_file = MagicMock()
            cli.pid_file.parent.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )

            cli.status(args)
            output = capsys.readouterr().out

            assert "Provider: sqlite" in output

    @pytest.mark.unit
    def test_status_displays_planka_provider(
        self,
        cli: Any,
        args: argparse.Namespace,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that status shows planka when configured as provider."""
        with (
            patch.object(cli, "_is_running", return_value=True),
            patch.object(cli, "_get_pid", return_value=12345),
            patch.object(cli, "_get_git_commit", return_value="abc1234 some msg"),
            patch("psutil.Process") as mock_process,
            patch("marcus_cli.get_config") as mock_config,
            patch("marcus_cli.get_kanban_provider", return_value="planka"),
        ):
            proc = MagicMock()
            proc.cpu_percent.return_value = 1.0
            proc.memory_info.return_value = MagicMock(rss=50 * 1024 * 1024)
            proc.create_time.return_value = 1000000.0
            mock_process.return_value = proc

            config_obj = MagicMock()
            config_obj.get.return_value = {"type": "stdio"}
            mock_config.return_value = config_obj

            cli.pid_file = MagicMock()
            cli.pid_file.parent.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )

            cli.status(args)
            output = capsys.readouterr().out

            assert "Provider: planka" in output

    @pytest.mark.unit
    def test_status_no_provider_when_not_running(
        self,
        cli: Any,
        args: argparse.Namespace,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that provider is not shown when Marcus is not running."""
        with (
            patch.object(cli, "_is_running", return_value=False),
            patch.object(cli, "_get_git_commit", return_value="abc1234 some msg"),
        ):
            cli.status(args)
            output = capsys.readouterr().out

            assert "Provider:" not in output


class TestStatusShowsGitCommit:
    """Test that status command displays the git commit."""

    @pytest.fixture(scope="class")
    def marcus_module(self) -> types.ModuleType:
        """Import the marcus CLI module once for the class."""
        with patch("psutil.Process"):
            return _import_marcus()

    @pytest.fixture
    def cli(self, marcus_module: types.ModuleType) -> Any:
        """Create a MarcusCLI instance."""
        return marcus_module.MarcusCLI()

    @pytest.fixture
    def args(self) -> argparse.Namespace:
        """Create a minimal args namespace for status."""
        return argparse.Namespace(command="status")

    @pytest.mark.unit
    def test_status_shows_commit_when_running(
        self,
        cli: Any,
        args: argparse.Namespace,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that status shows git commit when Marcus is running."""
        with (
            patch.object(cli, "_is_running", return_value=True),
            patch.object(cli, "_get_pid", return_value=12345),
            patch.object(
                cli,
                "_get_git_commit",
                return_value="c5b1361 chore: sync updates",
            ),
            patch("psutil.Process") as mock_process,
            patch("marcus_cli.get_config") as mock_config,
            patch("marcus_cli.get_kanban_provider", return_value="sqlite"),
        ):
            proc = MagicMock()
            proc.cpu_percent.return_value = 1.0
            proc.memory_info.return_value = MagicMock(rss=50 * 1024 * 1024)
            proc.create_time.return_value = 1000000.0
            mock_process.return_value = proc

            config_obj = MagicMock()
            config_obj.get.return_value = {"type": "stdio"}
            mock_config.return_value = config_obj

            cli.pid_file = MagicMock()
            cli.pid_file.parent.__truediv__ = MagicMock(
                return_value=MagicMock(exists=MagicMock(return_value=False))
            )

            cli.status(args)
            output = capsys.readouterr().out

            assert "Commit: c5b1361 chore: sync updates" in output

    @pytest.mark.unit
    def test_status_shows_commit_when_not_running(
        self,
        cli: Any,
        args: argparse.Namespace,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that status shows git commit even when not running."""
        with (
            patch.object(cli, "_is_running", return_value=False),
            patch.object(
                cli,
                "_get_git_commit",
                return_value="c5b1361 chore: sync updates",
            ),
        ):
            cli.status(args)
            output = capsys.readouterr().out

            assert "Commit: c5b1361 chore: sync updates" in output

    @pytest.mark.unit
    def test_get_git_commit_returns_oneline(
        self,
        cli: Any,
    ) -> None:
        """Test _get_git_commit calls git log --oneline."""
        with patch("marcus_cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="abc1234 fix: something\n",
            )
            result = cli._get_git_commit()

            assert result == "abc1234 fix: something"
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ["git", "log", "--oneline", "-1"]

    @pytest.mark.unit
    def test_get_git_commit_returns_unknown_on_failure(
        self,
        cli: Any,
    ) -> None:
        """Test _get_git_commit returns 'unknown' when git fails."""
        with patch("marcus_cli.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
            )
            result = cli._get_git_commit()

            assert result == "unknown"
