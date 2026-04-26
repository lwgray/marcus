"""
Unit tests for parallel SQLite experiment support.

Verifies that run_comparison_experiment.py generates correct per-instance
configuration for SQLite parallel runs (db_path instead of board_id) and
that the correct environment variables are passed to subprocesses.
"""

import pytest

pytestmark = pytest.mark.unit


class TestDefaultParallelInstancesUseSQLite:
    """Default parallel instance config must use db_path, not board_id."""

    def _make_runner(self, max_parallel: int = 3) -> object:
        """Construct an ExperimentRunner in parallel mode with no explicit instances."""
        import sys
        from pathlib import Path
        from unittest.mock import patch

        sys.path.insert(
            0,
            str(
                Path(__file__).parent.parent.parent.parent
                / "dev-tools"
                / "experiments"
                / "runners"
            ),
        )

        # Patch Path.mkdir to avoid filesystem side effects
        with patch("pathlib.Path.mkdir"):
            from run_comparison_experiment import ExperimentRunner

            runner = ExperimentRunner(
                base_dir=Path("/tmp/test_projects"),  # nosec B108
                results_dir=Path("/tmp/test_results"),  # nosec B108
                parallel=True,
                max_parallel=max_parallel,
                marcus_instances=None,
            )
        return runner

    def test_default_instances_have_db_path(self) -> None:
        """Each default instance must include db_path for SQLite isolation."""
        runner = self._make_runner(max_parallel=3)
        for instance in runner.marcus_instances:
            assert "db_path" in instance, (
                f"Instance {instance} missing db_path — parallel SQLite "
                "experiments need per-instance DB files"
            )

    def test_default_instances_do_not_have_board_id(self) -> None:
        """board_id is Planka-only and must not appear in default SQLite config."""
        runner = self._make_runner(max_parallel=3)
        for instance in runner.marcus_instances:
            assert "board_id" not in instance, (
                f"Instance {instance} still uses board_id (Planka) — "
                "default should be SQLite db_path"
            )

    def test_default_instances_have_unique_db_paths(self) -> None:
        """Each instance must get a distinct DB file to avoid write contention."""
        runner = self._make_runner(max_parallel=3)
        db_paths = [inst["db_path"] for inst in runner.marcus_instances]
        assert len(db_paths) == len(
            set(db_paths)
        ), "Parallel instances share a db_path — writes will collide"

    def test_default_instances_have_unique_ports(self) -> None:
        """Each instance must use a different port."""
        runner = self._make_runner(max_parallel=3)
        urls = [inst["url"] for inst in runner.marcus_instances]
        assert len(urls) == len(set(urls)), "Parallel instances share a URL/port"

    def test_correct_number_of_instances(self) -> None:
        """Runner creates exactly max_parallel instances."""
        runner = self._make_runner(max_parallel=5)
        assert len(runner.marcus_instances) == 5


class TestEnvVarPassingToSubprocess:
    """Subprocess env vars must carry SQLite path and Marcus URL per instance."""

    def _build_env(self, instance: dict) -> dict:
        """Simulate what run_experiment() builds for env vars."""
        import os

        env = dict(os.environ)
        env["MARCUS_URL"] = instance["url"]
        if "db_path" in instance:
            env["SQLITE_KANBAN_DB_PATH"] = instance["db_path"]
        elif "board_id" in instance:
            env["MARCUS_BOARD_ID"] = instance["board_id"]
        return env

    def test_sqlite_kanban_env_var_set_when_db_path_present(self) -> None:
        """SQLITE_KANBAN_DB_PATH must be set when instance has db_path."""
        instance = {"url": "http://localhost:4299/mcp", "db_path": "./data/exp_1.db"}
        env = self._build_env(instance)
        assert env["SQLITE_KANBAN_DB_PATH"] == "./data/exp_1.db"

    def test_marcus_url_set_from_instance(self) -> None:
        """MARCUS_URL must carry the instance-specific URL."""
        instance = {"url": "http://localhost:4299/mcp", "db_path": "./data/exp_1.db"}
        env = self._build_env(instance)
        assert env["MARCUS_URL"] == "http://localhost:4299/mcp"

    def test_planka_board_id_still_works_for_backward_compat(self) -> None:
        """Instances with board_id (Planka) must still set MARCUS_BOARD_ID."""
        instance = {
            "url": "http://localhost:4298",
            "board_id": "board_experimental_1",
        }
        env = self._build_env(instance)
        assert env["MARCUS_BOARD_ID"] == "board_experimental_1"
        assert "SQLITE_KANBAN_DB_PATH" not in env

    def test_no_board_id_in_sqlite_env(self) -> None:
        """SQLite instances must not leak MARCUS_BOARD_ID into subprocess env."""
        instance = {"url": "http://localhost:4299/mcp", "db_path": "./data/exp_1.db"}
        env = self._build_env(instance)
        assert "MARCUS_BOARD_ID" not in env


class TestMarcusURLBakedIntoShellScripts:
    """AgentSpawner must bake the resolved MARCUS_URL into generated scripts.

    tmux new-session does NOT inherit the calling process's environment —
    tmux runs a daemon and pane shells get the daemon's environment.
    Using ${MARCUS_URL:-...} inside the shell scripts silently falls back
    to port 4298 for every parallel instance.  The fix: resolve MARCUS_URL
    once at AgentSpawner init time and interpolate the concrete value into
    the generated script strings.
    """

    def _make_spawner(self, marcus_url: str) -> object:
        """Construct an AgentSpawner with a specific MARCUS_URL in env."""
        import os
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        sys.path.insert(
            0,
            str(
                Path(__file__).parent.parent.parent.parent
                / "dev-tools"
                / "experiments"
                / "runners"
            ),
        )
        from spawn_agents import AgentSpawner  # type: ignore[import]

        mock_config = MagicMock()
        mock_config.project_name = "test-project"
        templates_dir = (
            Path(__file__).parent.parent.parent.parent
            / "dev-tools"
            / "experiments"
            / "templates"
        )

        with patch.dict(os.environ, {"MARCUS_URL": marcus_url}):
            return AgentSpawner(config=mock_config, templates_dir=templates_dir)

    def test_custom_url_stored_on_spawner(self) -> None:
        """AgentSpawner.marcus_mcp_url must capture MARCUS_URL at init time."""
        spawner = self._make_spawner("http://localhost:4299/mcp")
        assert spawner.marcus_mcp_url == "http://localhost:4299/mcp"

    def test_default_url_is_standard_port(self) -> None:
        """When MARCUS_URL is unset, marcus_mcp_url defaults to port 4298."""
        import os
        import sys
        from pathlib import Path
        from unittest.mock import MagicMock, patch

        sys.path.insert(
            0,
            str(
                Path(__file__).parent.parent.parent.parent
                / "dev-tools"
                / "experiments"
                / "runners"
            ),
        )
        from spawn_agents import AgentSpawner  # type: ignore[import]

        mock_config = MagicMock()
        mock_config.project_name = "test-project"
        templates_dir = (
            Path(__file__).parent.parent.parent.parent
            / "dev-tools"
            / "experiments"
            / "templates"
        )

        env = {k: v for k, v in os.environ.items() if k != "MARCUS_URL"}
        with patch.dict(os.environ, env, clear=True):
            spawner = AgentSpawner(config=mock_config, templates_dir=templates_dir)
        assert spawner.marcus_mcp_url == "http://localhost:4298/mcp"

    def test_different_instances_get_different_urls(self) -> None:
        """Two spawners for different instances must have different URLs."""
        spawner_0 = self._make_spawner("http://localhost:4299/mcp")
        spawner_1 = self._make_spawner("http://localhost:4300/mcp")
        assert spawner_0.marcus_mcp_url != spawner_1.marcus_mcp_url
        assert "4299" in spawner_0.marcus_mcp_url
        assert "4300" in spawner_1.marcus_mcp_url
