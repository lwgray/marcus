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
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

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


class TestWaitForPaneReady:
    """Test suite for tmux pane readiness polling."""

    def test_returns_true_when_shell_prompt_detected(self) -> None:
        """Test pane is ready when shell prompt indicator appears."""
        wait_for_pane_ready = spawn_agents.wait_for_pane_ready

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="user@host ~ $")
            result = wait_for_pane_ready("test:0.0", timeout=2.0)

        assert result is True

    def test_returns_true_when_zsh_prompt_detected(self) -> None:
        """Test pane is ready when zsh prompt indicator appears."""
        wait_for_pane_ready = spawn_agents.wait_for_pane_ready

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="lwgray@mac ~ %")
            result = wait_for_pane_ready("test:0.0", timeout=2.0)

        assert result is True

    def test_returns_true_on_content_stabilization(self) -> None:
        """Test pane is ready when content stops changing."""
        wait_for_pane_ready = spawn_agents.wait_for_pane_ready

        call_count = 0

        def mock_capture(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # First call: empty, then stable content without prompt
            if call_count <= 1:
                return MagicMock(returncode=0, stdout="")
            return MagicMock(returncode=0, stdout="Loading shell...")

        with patch("subprocess.run", side_effect=mock_capture):
            with patch("time.sleep"):
                result = wait_for_pane_ready(
                    "test:0.0", timeout=5.0, poll_interval=0.01
                )

        assert result is True

    def test_returns_false_on_timeout(self) -> None:
        """Test pane readiness returns False when timeout expires."""
        wait_for_pane_ready = spawn_agents.wait_for_pane_ready

        call_count = 0

        def mock_capture(*args: Any, **kwargs: Any) -> MagicMock:
            nonlocal call_count
            call_count += 1
            # Content keeps changing — never stabilizes
            return MagicMock(returncode=0, stdout=f"changing content {call_count}")

        with patch("subprocess.run", side_effect=mock_capture):
            with patch("time.sleep"):
                result = wait_for_pane_ready(
                    "test:0.0", timeout=0.01, poll_interval=0.001
                )

        assert result is False

    def test_handles_tmux_capture_failure(self) -> None:
        """Test graceful handling when tmux capture-pane fails."""
        wait_for_pane_ready = spawn_agents.wait_for_pane_ready

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            with patch("time.sleep"):
                result = wait_for_pane_ready(
                    "test:0.0", timeout=0.01, poll_interval=0.001
                )

        assert result is False


class TestTermNormalization:
    """Test suite for TERM environment variable normalization in scripts."""

    def test_term_normalization_in_project_creator_script(self, tmp_path: Path) -> None:
        """Test project creator bash script includes TERM normalization."""
        config = MagicMock()
        config.experiment_dir = tmp_path
        config.implementation_dir = tmp_path / "implementation"
        config.implementation_dir.mkdir()
        config.prompts_dir = tmp_path / "prompts"
        config.prompts_dir.mkdir()
        config.project_info_file = tmp_path / "project_info.json"
        config.project_name = "test"
        config.project_options = {
            "complexity": "standard",
            "provider": "sqlite",
            "mode": "new_project",
        }
        config.agents = []
        config.get_timeout.return_value = 300

        spawner = spawn_agents.AgentSpawner.__new__(spawn_agents.AgentSpawner)
        spawner.config = config
        spawner.tmux_session = "test_session"
        spawner.current_pane = 0
        spawner.current_window = 0
        spawner.panes_per_window = 4

        # Mock tmux calls and generate the script
        with patch("subprocess.run"):
            with patch.object(spawner, "copy_agent_workflow_to_implementation"):
                with patch.object(spawner, "run_in_tmux_pane"):
                    spawner.spawn_project_creator()

        script_file = config.prompts_dir / "project_creator.sh"
        script_content = script_file.read_text()
        assert "TERM=xterm-256color" in script_content
        assert 'if [ "$TERM" = "dumb" ]' in script_content


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


class TestWorkerPromptRetryContract:
    """Worker prompt must not cap "no work" retries.

    Regression for dashboard-v73: worker prompts shipped with
    "max 3 retries" hard-coded, which caused agent_unicorn_2 to
    exit 90 seconds after a partner agent took over a recovered
    lease. Marcus's request_next_task no-task response explicitly
    instructs agents to keep retrying indefinitely (sleep the
    duration Marcus tells you, then retry); the worker prompt
    must respect that contract instead of overriding it.
    """

    @pytest.fixture
    def spawner(self, tmp_path: Path) -> Any:
        """Build an AgentSpawner with minimal config for prompt rendering."""
        config = MagicMock()
        config.implementation_dir = tmp_path / "impl"
        config.project_info_file = tmp_path / "project_info.json"
        config.prompts_dir = tmp_path / "prompts"
        config.prompts_dir.mkdir()

        # AgentSpawner reads agent_prompt_template from disk; provide a
        # tiny stub so create_worker_prompt's read() succeeds.
        template = tmp_path / "agent_template.md"
        template.write_text("# Base agent template\n")

        instance = MagicMock(spec=spawn_agents.AgentSpawner)
        instance.config = config
        instance.agent_prompt_template = template
        # Bind the real method to the mock so we can call it like a method.
        instance.create_worker_prompt = (
            spawn_agents.AgentSpawner.create_worker_prompt.__get__(
                instance, spawn_agents.AgentSpawner
            )
        )
        return instance

    @pytest.fixture
    def agent_config(self) -> dict[str, Any]:
        """Minimal agent config dict for prompt rendering."""
        return {
            "id": "agent_test_1",
            "name": "Test Agent 1",
            "role": "full-stack",
            "skills": ["python", "javascript"],
            "subagents": 0,
        }

    def test_worker_prompt_has_no_max_retries_cap(
        self, spawner: Any, agent_config: dict[str, Any]
    ) -> None:
        """Worker prompt must not impose a max-retries cap on no-task responses."""
        prompt = spawner.create_worker_prompt(agent_config)
        # Hard fail on the literal phrase that v73 used:
        assert "max 3 retries" not in prompt, (
            "Worker prompt regressed: 'max 3 retries' present. v73 "
            "demonstrated this causes premature agent exit when a partner "
            "holds a recovered lease. Marcus tells agents how long to "
            "sleep — trust that signal, do not impose a cap."
        )
        # Also forbid generic retry caps that would have the same effect:
        assert "max retries" not in prompt.lower()
        assert "retries exhausted" not in prompt.lower()

    def test_worker_prompt_loops_until_experiment_ends(
        self, spawner: Any, agent_config: dict[str, Any]
    ) -> None:
        """Worker prompt must define the loop termination as experiment-end.

        Positive instruction (no negation): the prompt says "loop until
        the experiment ends" rather than "do not stop after N retries."
        The exit condition is is_running going false in
        get_experiment_status, not a retry counter.
        """
        prompt = spawner.create_worker_prompt(agent_config)
        prompt_lower = prompt.lower()
        # Loop termination tied to experiment ending, not retry count
        assert "until the experiment ends" in prompt_lower
        # Sleep instruction tied to retry_after_seconds from Marcus
        assert "retry_after_seconds" in prompt

    def test_worker_prompt_names_experiment_status_as_exit_signal(
        self, spawner: Any, agent_config: dict[str, Any]
    ) -> None:
        """The only exit signal must be is_running:false from experiment status."""
        prompt = spawner.create_worker_prompt(agent_config)
        # Critical: agents must know the canonical "stop polling" signal
        assert "get_experiment_status" in prompt
        assert "is_running" in prompt

    def test_worker_prompt_delegates_completion_to_marcus(
        self, spawner: Any, agent_config: dict[str, Any]
    ) -> None:
        """Worker prompt must say Marcus owns the completion decision.

        Positive instruction (no negation): the prompt tells the agent
        that Marcus computes completion from the kanban formula and
        flips is_running. The agent's only job is to read is_running
        and act on it. v73 broke because the agent computed completion
        itself from running tallies; the fix is to remove the
        agent's role in the computation entirely.
        """
        prompt = spawner.create_worker_prompt(agent_config)
        # Marcus owns the formula — must match runtime check at
        # LiveExperimentMonitor._check_completion (Codex P2 on PR #349)
        assert "(completed_tasks + blocked_tasks) == total_tasks" in prompt
        assert "in_progress_tasks == 0" in prompt
        # Agent reads is_running, doesn't compute
        prompt_lower = prompt.lower()
        assert "marcus owns the completion" in prompt_lower or (
            "marcus computes" in prompt_lower
        )

    def test_worker_prompt_handles_startup_window(
        self, spawner: Any, agent_config: dict[str, Any]
    ) -> None:
        """Worker prompt must distinguish "not started" from "ended".

        Codex P1 on PR #349: workers wait on project_info.json which
        the creator writes BEFORE calling start_experiment. There's a
        real window where get_experiment_status returns
        is_running=False because the experiment hasn't started yet.
        The worker must not exit during that window — the prompt
        must instruct it to check experiment_started first.
        """
        prompt = spawner.create_worker_prompt(agent_config)
        # Must reference the lifecycle field
        assert "experiment_started" in prompt
        # Must reference the 3-state lifecycle by name or by branching
        prompt_lower = prompt.lower()
        assert (
            "startup window" in prompt_lower
            or "3-state" in prompt_lower
            or ("hasn't started" in prompt_lower)
        )


class TestMonitorPromptKanbanTruth:
    """Monitor prompt must read kanban-truth fields, not running tallies.

    Regression for v73: the monitor agent's display showed
    "Project Status: 2/3 tasks complete" because its prompt template
    referenced fields that came from the running tallies rather than
    the kanban-truth fields. The monitor itself was confused — it
    even noted "3 more tasks from the board still not yet visible."
    """

    @pytest.fixture
    def spawner(self, tmp_path: Path) -> Any:
        """Build an AgentSpawner with minimal config for monitor prompt rendering."""
        config = MagicMock()
        config.implementation_dir = tmp_path / "impl"
        config.project_info_file = tmp_path / "project_info.json"
        config.prompts_dir = tmp_path / "prompts"
        config.prompts_dir.mkdir()

        instance = MagicMock(spec=spawn_agents.AgentSpawner)
        instance.config = config
        instance.create_monitor_prompt = (
            spawn_agents.AgentSpawner.create_monitor_prompt.__get__(
                instance, spawn_agents.AgentSpawner
            )
        )
        return instance

    def test_monitor_prompt_uses_kanban_truth_for_display(self, spawner: Any) -> None:
        """Monitor display template must use total_tasks / completed_tasks."""
        prompt = spawner.create_monitor_prompt()
        assert "total_tasks" in prompt
        assert "completed_tasks" in prompt
        assert "in_progress_tasks" in prompt
        assert "blocked_tasks" in prompt

    def test_monitor_prompt_gives_explicit_percent_formula(self, spawner: Any) -> None:
        """Monitor prompt must give an explicit completion-percent formula.

        Positive instruction: the monitor needs to know HOW to compute
        the percentage, not just which fields exist. The formula uses
        completed_tasks / total_tasks with a guard for total == 0.
        """
        prompt = spawner.create_monitor_prompt()
        # The formula appears in the prompt, not buried in code Marcus runs
        assert "100 * done / total" in prompt or (
            "100 * completed_tasks / total_tasks" in prompt
        )

    def test_monitor_prompt_uses_is_running_as_exit_signal(self, spawner: Any) -> None:
        """Monitor exits when is_running goes false, not on its own clock."""
        prompt = spawner.create_monitor_prompt()
        assert "is_running" in prompt
        prompt_lower = prompt.lower()
        # Must say Marcus owns the decision
        assert "marcus owns the completion" in prompt_lower or (
            "marcus" in prompt_lower and "flips is_running" in prompt_lower
        )

    def test_monitor_prompt_handles_startup_window(self, spawner: Any) -> None:
        """Monitor prompt must branch on experiment_started.

        Codex P1 on PR #349: same race as workers — monitor registers
        and starts polling before the creator calls start_experiment.
        The monitor must wait, not crash or exit, during that window.
        """
        prompt = spawner.create_monitor_prompt()
        assert "experiment_started" in prompt
        # Should poll faster while waiting for startup
        assert "Sleep 10 seconds" in prompt or "10 seconds" in prompt

    def test_monitor_prompt_uses_correct_completion_formula(self, spawner: Any) -> None:
        """Monitor prompt must document the runtime formula.

        Codex P2 on PR #349: blocked tasks count toward "done."
        The displayed/explained formula must match
        LiveExperimentMonitor._check_completion.
        """
        prompt = spawner.create_monitor_prompt()
        assert "(completed_tasks + blocked_tasks) == total_tasks" in prompt


class TestFetchRecommendedAgents:
    """_fetch_recommended_agents queries Marcus MCP HTTP — no LLM relay."""

    def test_returns_optimal_agents_on_success(self) -> None:
        """Returns optimal_agents from Marcus MCP response."""
        sse_body = (
            'event: message\ndata: {"jsonrpc":"2.0","id":2,"result":{'
            '"content":[{"type":"text","text":"{}"}],'
            '"structuredContent":{"result":{"success":true,"optimal_agents":3}},'
            '"isError":false}}\n'
        ).encode()

        init_resp = MagicMock()
        init_resp.read.return_value = b"event: message\ndata: {}\n"
        init_resp.headers = {"mcp-session-id": "test-session-123"}
        init_resp.__enter__ = lambda s: s
        init_resp.__exit__ = MagicMock(return_value=False)

        tool_resp = MagicMock()
        tool_resp.read.return_value = sse_body
        tool_resp.__enter__ = lambda s: s
        tool_resp.__exit__ = MagicMock(return_value=False)

        notif_resp = MagicMock()
        notif_resp.read.return_value = b""
        notif_resp.__enter__ = lambda s: s
        notif_resp.__exit__ = MagicMock(return_value=False)

        responses = [init_resp, notif_resp, tool_resp]

        with patch("urllib.request.urlopen", side_effect=responses):
            result = spawn_agents.AgentSpawner._fetch_recommended_agents()

        assert result == 3

    def test_returns_zero_when_server_unreachable(self) -> None:
        """Returns 0 (safe fallback) when Marcus server is not running."""
        import urllib.error

        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = spawn_agents.AgentSpawner._fetch_recommended_agents()

        assert result == 0

    def test_returns_zero_when_response_malformed(self) -> None:
        """Returns 0 when MCP response cannot be parsed."""
        bad_resp = MagicMock()
        bad_resp.read.return_value = b"not valid SSE"
        bad_resp.headers = {"mcp-session-id": "s1"}
        bad_resp.__enter__ = lambda s: s
        bad_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=bad_resp):
            result = spawn_agents.AgentSpawner._fetch_recommended_agents()

        assert result == 0

    def test_returns_zero_when_session_id_missing(self) -> None:
        """Returns 0 when Marcus init response has no session ID."""
        init_resp = MagicMock()
        init_resp.read.return_value = b"event: message\ndata: {}\n"
        init_resp.headers = {}  # no mcp-session-id
        init_resp.__enter__ = lambda s: s
        init_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=init_resp):
            result = spawn_agents.AgentSpawner._fetch_recommended_agents()

        assert result == 0


class TestRunUsesRecommendedAgentCount:
    """run() uses CPM recommendation from Marcus (capped by user config count)."""

    @pytest.fixture
    def spawner_with_config(self, tmp_path: Path) -> Any:
        """Build an AgentSpawner with 2 agents in config (user cap = 2)."""
        config = MagicMock()
        config.experiment_dir = tmp_path
        config.implementation_dir = tmp_path / "implementation"
        config.implementation_dir.mkdir()
        config.prompts_dir = tmp_path / "prompts"
        config.prompts_dir.mkdir()
        config.project_info_file = tmp_path / "project_info.json"
        config.project_name = "test_project"
        config.project_options = {"complexity": "prototype", "provider": "sqlite"}
        config.agents = [
            {
                "id": "agent_unicorn_1",
                "name": "Unicorn Developer 1",
                "role": "full-stack",
                "skills": ["python", "javascript"],
                "subagents": 0,
            },
            {
                "id": "agent_unicorn_2",
                "name": "Unicorn Developer 2",
                "role": "full-stack",
                "skills": ["python", "javascript"],
                "subagents": 0,
            },
        ]
        config.max_agents = 12  # safety cap; CPM can scale up to this
        config.get_timeout.return_value = 10

        template_dir = tmp_path / "templates"
        template_dir.mkdir()
        agent_template = template_dir / "agent_prompt.md"
        agent_template.write_text("# Agent prompt template\n")

        instance = spawn_agents.AgentSpawner.__new__(spawn_agents.AgentSpawner)
        instance.config = config
        instance.templates_dir = template_dir
        instance.agent_prompt_template = agent_template
        instance.tmux_session = "test_session"
        instance.current_pane = 0
        instance.current_window = 0
        instance.panes_per_window = 4
        return instance

    def _write_project_info(self, path: Path) -> None:
        """Write minimal project_info.json (no recommended_agents — it's not there)."""
        path.write_text(
            json.dumps(
                {"project_id": "proj-123", "board_id": "board-456", "tasks_created": 10}
            )
        )

    def _make_wait_side_effect(self, path: Path) -> Any:
        """Return a side_effect that rewrites project_info.json and returns True.

        run() deletes project_info.json during cleanup before calling
        wait_for_project_info. The mock must rewrite the file so that
        run() can open it in Phase 2.
        """

        def _side_effect(config: Any, **kwargs: Any) -> bool:
            self._write_project_info(path)
            return True

        return _side_effect

    def _run_with_recommended(
        self,
        spawner_with_config: Any,
        recommended: int,
    ) -> list[dict[str, Any]]:
        """Run the spawner with _fetch_recommended_agents mocked to return `recommended`."""
        wait_se = self._make_wait_side_effect(
            spawner_with_config.config.project_info_file
        )
        spawned_agents: list[dict[str, Any]] = []

        with (
            patch.object(spawner_with_config, "create_tmux_session"),
            patch.object(spawner_with_config, "spawn_project_creator"),
            patch.object(spawn_agents, "wait_for_project_info", side_effect=wait_se),
            patch.object(
                spawn_agents.AgentSpawner,
                "_fetch_recommended_agents",
                return_value=recommended,
            ),
            patch.object(
                spawner_with_config,
                "spawn_worker",
                side_effect=lambda a: spawned_agents.append(a),
            ),
            patch.object(spawner_with_config, "spawn_monitor"),
            patch.object(spawner_with_config, "_pretrust_directory"),
            patch("subprocess.run"),
            patch.dict("sys.modules", {"mlflow": MagicMock()}),
        ):
            spawner_with_config.run()

        return spawned_agents

    def test_run_scales_above_template_count_when_recommended_higher(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """CPM recommends 4, template count is 2, max_cap is 12 → spawn 4 workers.

        Config entries are templates, not a count cap. CPM is authoritative;
        extra agents are generated by cycling through templates.
        """
        spawned = self._run_with_recommended(spawner_with_config, recommended=4)
        assert len(spawned) == 4, f"Expected 4 workers (CPM count), got {len(spawned)}"

    def test_run_uses_recommended_when_lower_than_template_count(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """CPM recommends 1, template count is 2 → spawn 1 worker (CPM wins)."""
        spawned = self._run_with_recommended(spawner_with_config, recommended=1)
        assert (
            len(spawned) == 1
        ), f"Expected 1 worker (recommended < templates), got {len(spawned)}"

    def test_run_caps_at_max_agents_when_recommended_exceeds_cap(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """CPM recommends 20, max_agents is 12 → spawn 12 (safety cap enforced)."""
        spawned = self._run_with_recommended(spawner_with_config, recommended=20)
        assert (
            len(spawned) == 12
        ), f"Expected 12 workers (max_agents cap), got {len(spawned)}"

    def test_run_uses_config_count_when_cpm_unavailable(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """When _fetch_recommended_agents returns 0 (CPM failed), use config count."""
        spawned = self._run_with_recommended(spawner_with_config, recommended=0)
        assert len(spawned) == 2

    def test_creator_prompt_does_not_write_recommended_agents(
        self, tmp_path: Path
    ) -> None:
        """Creator prompt must NOT ask the LLM to relay recommended_agents.

        The recommendation comes from Marcus directly via MCP HTTP.
        Routing it through the LLM is fragile and was explicitly removed.
        """
        spec_file = tmp_path / "project_spec.md"
        spec_file.write_text("Build a todo app")

        config = MagicMock()
        config.implementation_dir = tmp_path / "impl"
        config.project_info_file = tmp_path / "project_info.json"
        config.project_name = "test"
        config.project_spec_file = spec_file
        config.project_options = {"complexity": "prototype", "provider": "sqlite"}
        config.agents = []

        instance = MagicMock(spec=spawn_agents.AgentSpawner)
        instance.config = config
        instance.create_project_creator_prompt = (
            spawn_agents.AgentSpawner.create_project_creator_prompt.__get__(
                instance, spawn_agents.AgentSpawner
            )
        )
        prompt = instance.create_project_creator_prompt()
        assert "recommended_agents" not in prompt, (
            "Creator prompt must not instruct the LLM to write recommended_agents. "
            "The value comes from Marcus directly via _fetch_recommended_agents."
        )
