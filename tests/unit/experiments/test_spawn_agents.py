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
        spawner.marcus_mcp_url = "http://localhost:4298/mcp"
        # Slice B+ (#523) and agent-model wiring: see fixture below.
        spawner.agent_model = None
        spawner.claude_model_flag = ""

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
        config.stall_timeout_minutes = 20

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
        # Slice B+ (#523) and agent-model wiring: bypass-init fixture
        # must mirror __init__'s newer attributes so run()'s startup
        # banner doesn't AttributeError.  None / empty string match
        # the no-override / no-model path used by these tests.
        instance.agent_model = None
        instance.claude_model_flag = ""
        return instance

    def _write_project_info(self, path: Path, recommended_agents: int = 0) -> None:
        """Write project_info.json as Marcus now writes it (includes recommended_agents)."""
        path.write_text(
            json.dumps(
                {
                    "project_id": "proj-123",
                    "board_id": "board-456",
                    "tasks_created": 10,
                    "recommended_agents": recommended_agents,
                }
            )
        )

    def _make_wait_side_effect(self, path: Path, recommended: int = 0) -> Any:
        """Return a side_effect that rewrites project_info.json and returns True.

        run() deletes project_info.json during cleanup before calling
        wait_for_project_info. The mock must rewrite the file so that
        run() can open it in Phase 2.
        """

        def _side_effect(config: Any, **kwargs: Any) -> bool:
            self._write_project_info(path, recommended_agents=recommended)
            return True

        return _side_effect

    def _run_with_recommended(
        self,
        spawner_with_config: Any,
        recommended: int,
    ) -> list[dict[str, Any]]:
        """Run the spawner with recommended_agents embedded in project_info.json.

        After the Bug-1 fix the spawner reads ``recommended_agents`` from
        project_info.json (written by Marcus) rather than querying Marcus via
        a second HTTP session (which silently failed due to a race condition).
        """
        wait_se = self._make_wait_side_effect(
            spawner_with_config.config.project_info_file,
            recommended=recommended,
        )
        spawned_agents: list[dict[str, Any]] = []

        with (
            patch.object(spawner_with_config, "create_tmux_session"),
            patch.object(spawner_with_config, "spawn_project_creator"),
            patch.object(spawn_agents, "wait_for_project_info", side_effect=wait_se),
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

    def test_overflow_agents_have_zero_subagents(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """Overflow agents (CPM > template count) must not inherit template subagents.

        If templates declare subagents > 0, copying them into overflow agents
        would register extra subagents beyond max_agents, defeating the cap.
        """
        # Give the templates non-zero subagents to expose the bug
        for agent in spawner_with_config.config.agents:
            agent["subagents"] = 2

        # CPM recommends 4; templates = 2, so agents 2 and 3 are overflow
        spawned = self._run_with_recommended(spawner_with_config, recommended=4)

        overflow = spawned[2:]  # indices 2 and 3 are the cycled extras
        for agent in overflow:
            assert agent["subagents"] == 0, (
                f"Overflow agent {agent['id']} inherited subagents={agent['subagents']}; "
                "expected 0"
            )

    def test_overflow_agents_have_unique_ids_when_config_agents_empty(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """When config.agents is empty, overflow agents must get unique ids.

        Previously all agents fell back to "agent_unicorn_1", causing ID
        collisions across all spawned workers.
        """
        spawner_with_config.config.agents = []
        spawner_with_config.config.max_agents = 12
        spawned = self._run_with_recommended(spawner_with_config, recommended=3)

        ids = [a["id"] for a in spawned]
        assert len(ids) == len(set(ids)), f"Duplicate agent IDs: {ids}"

    def test_run_uses_config_count_when_project_info_has_zero(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """When project_info.json has recommended_agents=0, fall back to config count."""
        spawned = self._run_with_recommended(spawner_with_config, recommended=0)
        assert len(spawned) == 2

    def test_spawner_reads_recommended_agents_from_project_info_json(
        self, spawner_with_config: Any, tmp_path: Path
    ) -> None:
        """
        Verify spawner reads recommended_agents from project_info.json (Bug-1 fix).

        Dashboard-v98 post-mortem: the spawner queried Marcus via a second HTTP
        session to get the CPM recommendation. That session silently failed/timed
        out — the log shows zero evidence of the HTTP call. The spawner fell back
        to len(config.agents)=2 instead of CPM's recommendation of 8, losing ~4×
        throughput.

        Fix: Marcus writes recommended_agents to project_info.json during
        create_project. The spawner reads it from there — no race condition,
        no extra MCP session.
        """
        spawned = self._run_with_recommended(spawner_with_config, recommended=8)
        assert len(spawned) == 8, (
            f"Expected 8 agents (CPM recommendation from project_info.json), "
            f"got {len(spawned)}"
        )

    def test_creator_prompt_does_not_write_recommended_agents(
        self, tmp_path: Path
    ) -> None:
        """Creator prompt must NOT ask the LLM to extract or write recommended_agents.

        Marcus now writes recommended_agents to project_info.json directly inside
        create_project (server-side, no LLM relay). The creator agent must NOT
        overwrite the file with a version that drops recommended_agents.
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
        # The agent must not overwrite the server-written file with a stripped version
        assert '"recommended_agents"' not in prompt, (
            "Creator prompt must not instruct the LLM to write recommended_agents. "
            "Marcus writes it server-side; agent relay is fragile and was removed."
        )


class TestProjectInfoPathSync:
    """Tests for Codex P2 fix: project_info_file kept in sync with project_info_path."""

    def test_project_info_file_defaults_to_experiment_dir(self, tmp_path: Path) -> None:
        """Without override, project_info_file is <experiment_dir>/project_info.json."""
        config_data = {
            "project_name": "test",
            "project_spec_file": "spec.md",
            "project_options": {"complexity": "prototype", "provider": "sqlite"},
            "agents": [],
        }
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("Build something")
        config_path = tmp_path / "config.yaml"
        import yaml  # type: ignore[import-untyped]

        config_path.write_text(yaml.dump(config_data))

        config = spawn_agents.ExperimentConfig(config_path)

        assert config.project_info_file == tmp_path / "project_info.json"
        assert config.project_options["project_info_path"] == str(
            tmp_path / "project_info.json"
        )

    def test_project_info_file_syncs_with_custom_override(self, tmp_path: Path) -> None:
        """
        When project_info_path is pre-set in config, project_info_file must
        point to the same path so wait_for_project_info and the JSON read
        both target the file Marcus actually writes (Codex P2 fix).
        """
        custom_path = tmp_path / "custom" / "info.json"
        config_data = {
            "project_name": "test",
            "project_spec_file": "spec.md",
            "project_options": {
                "complexity": "prototype",
                "provider": "sqlite",
                "project_info_path": str(custom_path),
            },
            "agents": [],
        }
        spec_file = tmp_path / "spec.md"
        spec_file.write_text("Build something")
        config_path = tmp_path / "config.yaml"
        import yaml  # type: ignore[import-untyped]

        config_path.write_text(yaml.dump(config_data))

        config = spawn_agents.ExperimentConfig(config_path)

        assert (
            config.project_info_file == custom_path
        ), "project_info_file must match the pre-set project_info_path override"


# ---------------------------------------------------------------------------
# Agent model resolution + threading
# ---------------------------------------------------------------------------


def _make_config_yaml(tmp_path: Path, **extra: Any) -> Path:
    """Write a minimal config.yaml for ExperimentConfig tests.

    ``extra`` keys are merged into the top-level mapping so tests can
    add ``agent_model: ...`` without rewriting the full template.
    """
    import yaml as _yaml

    spec_path = tmp_path / "project_spec.md"
    spec_path.write_text("test spec")

    config_data: Dict[str, Any] = {
        "project_name": "agent-model-test",
        "project_spec_file": "project_spec.md",
        "project_options": {
            "complexity": "prototype",
            "provider": "sqlite",
            "mode": "new_project",
        },
        "agents": [
            {"id": "agent_1", "name": "Agent 1", "role": "full-stack", "skills": []}
        ],
    }
    config_data.update(extra)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(_yaml.dump(config_data))
    return config_path


class TestAgentModelResolution:
    """``ExperimentConfig.agent_model`` resolves from yaml then config_marcus.

    The Planner (Marcus-side LLM calls) is governed by ``ai.model`` in
    ``config_marcus.json``.  The Agent (spawned ``claude`` processes)
    defaults to the same value so a single config setting governs both
    classes.  Per-experiment override via ``agent_model`` in
    ``config.yaml``.  Per-invocation override via ``--model`` on
    ``run_experiment.py`` (handled at :class:`AgentSpawner` level,
    tested separately below).
    """

    def test_yaml_agent_model_wins_over_marcus_config(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``config.yaml.agent_model`` overrides ``config_marcus.json.ai.model``.

        Point ``__file__`` at a tmp-path repo root that DOES contain a
        ``config_marcus.json`` so the resolver's fallback branch is a
        live candidate.  The test then asserts the yaml hit short-
        circuits and the marcus-config value is never consulted.
        """
        # Build a fake repo root with a config_marcus.json that would
        # win if the resolver fell through to the fallback branch.
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"ai": {"model": "should-not-be-used"}})
        )
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))
        # Clear MARCUS_CONFIG so the env-var branch (Codex P2 fix on
        # PR #540) doesn't redirect this test to an unintended file.
        monkeypatch.delenv("MARCUS_CONFIG", raising=False)

        config_path = _make_config_yaml(tmp_path, agent_model="from-yaml")
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model == "from-yaml"

    def test_falls_back_to_marcus_config_when_yaml_silent(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Absent ``agent_model`` in yaml → read ``ai.model`` from
        ``config_marcus.json``.

        Patches ``Path(__file__).resolve()`` for the spawn_agents
        module so the resolver looks in a tmp-path repo root instead
        of the real one.
        """
        # Build a fake repo root containing config_marcus.json
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"ai": {"model": "claude-haiku-4-5-20251001"}})
        )
        # Pretend spawn_agents.py lives at
        # <fake_root>/dev-tools/experiments/runners/spawn_agents.py
        # so ``parents[3]`` lands on fake_root.
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")

        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        config_path = _make_config_yaml(tmp_path)  # no agent_model in yaml
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model == "claude-haiku-4-5-20251001"

    def test_returns_none_when_neither_source_has_model(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Yaml silent + ``config_marcus.json`` missing → ``None``.

        ``None`` is the signal AgentSpawner uses to omit the
        ``--model`` flag, letting ``claude`` use its global default.
        """
        # Repo root WITHOUT config_marcus.json
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model is None

    def test_malformed_marcus_config_is_treated_as_absent(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """Invalid JSON in ``config_marcus.json`` → ``None``, not raise.

        A broken Planner config must not also break agent spawning.
        The two failure modes are independent.
        """
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text("not-valid-json{")
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model is None

    def test_marcus_config_without_ai_block_returns_none(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``config_marcus.json`` missing ``ai`` block → ``None``."""
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"other_key": "value"})
        )
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model is None

    def test_marcus_config_env_var_redirects_resolver(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``MARCUS_CONFIG`` env var redirects the resolver (Codex P2 on #540).

        Marcus's Planner honors ``MARCUS_CONFIG`` for its own model
        lookup (``src/config/marcus_config.py:get_config()``).  The
        agent resolver must honor it too — otherwise the Planner
        reads the custom file while the resolver silently reads the
        repo-root default, and the documented "inherit the Planner
        model" behavior is false.
        """
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        # Repo-root config_marcus.json with a DIFFERENT model than
        # the env-var path — so we can prove the env var wins.
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"ai": {"model": "repo-root-should-be-ignored"}})
        )
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        custom_config = tmp_path / "custom_marcus.json"
        custom_config.write_text(json.dumps({"ai": {"model": "from-env-var-config"}}))
        monkeypatch.setenv("MARCUS_CONFIG", str(custom_config))

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model == "from-env-var-config"

    def test_marcus_config_env_var_missing_file_returns_none(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``MARCUS_CONFIG`` pointing at a missing file → ``None``.

        Defensive degradation, same as the unset-env-var case with
        missing repo-root config.  Does NOT silently fall back to
        the repo-root file when the env var is set but invalid —
        operator misconfiguration must surface as a missing model,
        not as a different model than expected.
        """
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"ai": {"model": "must-not-be-used-when-env-set"}})
        )
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        monkeypatch.setenv("MARCUS_CONFIG", str(tmp_path / "does_not_exist.json"))

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model is None

    def test_empty_marcus_config_env_var_falls_back_to_repo_root(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``MARCUS_CONFIG=""`` (empty string) ignored → repo-root used.

        Mirrors the Planner's env-var precedence: only treat the env
        var as a redirect when it carries a non-empty value.  An
        empty MARCUS_CONFIG (set by some shell wrappers as a "clear"
        signal) must NOT short-circuit the resolver to ``None`` —
        the repo-root fallback should still run.
        """
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        (fake_root / "config_marcus.json").write_text(
            json.dumps({"ai": {"model": "from-repo-root"}})
        )
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        monkeypatch.setenv("MARCUS_CONFIG", "")

        config_path = _make_config_yaml(tmp_path)
        config = spawn_agents.ExperimentConfig(config_path)

        assert config.agent_model == "from-repo-root"


class TestAgentSpawnerModelFlag:
    """``AgentSpawner.claude_model_flag`` renders the ``--model`` fragment.

    The flag string is spliced into every spawned ``claude`` command
    so all three pane types (project creator, workers, monitor) run
    on the same model.  Empty string means no ``--model`` is appended
    → ``claude`` uses its global default.
    """

    def _build_spawner(
        self,
        tmp_path: Path,
        monkeypatch: Any,
        yaml_model: str | None = None,
        cli_model: str | None = None,
    ) -> Any:
        """Build an AgentSpawner with a real ExperimentConfig + no MCP probe."""
        # Isolate config_marcus.json discovery to a non-existent dir so
        # the resolver's fallback is deterministically None.
        fake_root = tmp_path / "marcus_root"
        fake_root.mkdir()
        fake_module_path = (
            fake_root / "dev-tools" / "experiments" / "runners" / "spawn_agents.py"
        )
        fake_module_path.parent.mkdir(parents=True)
        fake_module_path.write_text("")
        monkeypatch.setattr(spawn_agents, "__file__", str(fake_module_path))

        extra = {"agent_model": yaml_model} if yaml_model else {}
        config_path = _make_config_yaml(tmp_path, **extra)
        config = spawn_agents.ExperimentConfig(config_path)

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "agent_prompt.md").write_text("stub")

        return spawn_agents.AgentSpawner(
            config=config,
            templates_dir=templates_dir,
            agent_model=cli_model,
        )

    def test_no_model_renders_empty_flag(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        spawner = self._build_spawner(tmp_path, monkeypatch)
        assert spawner.claude_model_flag == ""
        assert spawner.agent_model is None

    def test_yaml_model_renders_flag(self, tmp_path: Path, monkeypatch: Any) -> None:
        spawner = self._build_spawner(tmp_path, monkeypatch, yaml_model="haiku")
        assert spawner.claude_model_flag == "--model haiku "
        assert spawner.agent_model == "haiku"

    def test_cli_override_wins_over_yaml(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``--model`` on the CLI beats ``agent_model`` in yaml.

        Precedence order: CLI > yaml > config_marcus.json > None.
        """
        spawner = self._build_spawner(
            tmp_path,
            monkeypatch,
            yaml_model="should-be-overridden",
            cli_model="opus",
        )
        assert spawner.agent_model == "opus"
        assert spawner.claude_model_flag == "--model opus "

    def test_cli_none_falls_back_to_yaml(
        self, tmp_path: Path, monkeypatch: Any
    ) -> None:
        """``agent_model=None`` on CLI → use yaml's value."""
        spawner = self._build_spawner(
            tmp_path,
            monkeypatch,
            yaml_model="from-yaml",
            cli_model=None,
        )
        assert spawner.agent_model == "from-yaml"
        assert spawner.claude_model_flag == "--model from-yaml "


class TestClaudeModelFlagLandsInGeneratedScripts:
    """End-to-end: ``--model X`` actually reaches the rendered bash.

    The unit tests in :class:`TestAgentSpawnerModelFlag` verify the
    ``claude_model_flag`` attribute, but the load-bearing behaviour
    is whether it gets spliced into the generated project-creator
    script that tmux ultimately executes.  This class scrubs the
    rendered ``.sh`` file and asserts the flag is on the right line.
    """

    def _make_spawner(self, tmp_path: Path, agent_model: str) -> Any:
        """Build a bypass-init spawner with everything spawn_project_creator
        reads from ``self``.  Matches the pattern in
        :class:`TestTermNormalization`."""
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
        spawner.marcus_mcp_url = "http://localhost:4298/mcp"
        spawner.agent_model = agent_model
        spawner.claude_model_flag = f"--model {agent_model} " if agent_model else ""
        return spawner

    def test_project_creator_script_contains_model_flag(self, tmp_path: Path) -> None:
        """``--model X`` appears in the rendered project-creator script,
        on the same line as the ``claude`` invocation, before
        ``--dangerously-skip-permissions``."""
        spawner = self._make_spawner(tmp_path, agent_model="haiku")

        with (
            patch("subprocess.run"),
            patch.object(spawner, "copy_agent_workflow_to_implementation"),
            patch.object(spawner, "run_in_tmux_pane"),
        ):
            spawner.spawn_project_creator()

        script_file = spawner.config.prompts_dir / "project_creator.sh"
        content = script_file.read_text()
        assert "--model haiku" in content
        # And it precedes --dangerously-skip-permissions on the same line
        # so the claude CLI parses both flags correctly.
        claude_line = next(
            ln for ln in content.splitlines() if "--dangerously-skip-permissions" in ln
        )
        assert "--model haiku" in claude_line

    def test_project_creator_script_omits_flag_when_no_model(
        self, tmp_path: Path
    ) -> None:
        """No model resolved → no ``--model`` token in the rendered script.

        Backward compat: legacy experiments with no ``agent_model``
        wiring must produce scripts identical to pre-#540 output.
        """
        spawner = self._make_spawner(tmp_path, agent_model=None)

        with (
            patch("subprocess.run"),
            patch.object(spawner, "copy_agent_workflow_to_implementation"),
            patch.object(spawner, "run_in_tmux_pane"),
        ):
            spawner.spawn_project_creator()

        script_file = spawner.config.prompts_dir / "project_creator.sh"
        content = script_file.read_text()
        assert "--model" not in content


class TestTmuxBaseIndexDetection:
    """Test suite for non-zero tmux base-index handling (PR #568).

    A user's ``~/.tmux.conf`` may set ``base-index 1`` and
    ``pane-base-index 1`` — a common non-default configuration. The
    spawner builds ``session:window.pane`` target strings; with the
    indices hardcoded to ``0`` those targets address windows/panes that
    do not exist under such a config and every ``tmux`` call fails.

    ``AgentSpawner`` detects the two indices inside ``create_tmux_session``
    — by reading the first window/pane of the session that was just
    created — and offsets every target string by the detected base.

    Detection happens after the session exists (not in ``__init__``)
    because ``tmux new-session`` is what starts the tmux server and
    sources ``~/.tmux.conf``; reading the indices any earlier returns
    the default ``0`` even when the user's config sets ``base-index 1``
    (the cold-start bug). These tests cover the ``_first_int`` reader,
    the ``__init__`` placeholder defaults, the ``create_tmux_session``
    detection, and the offset applied to target strings.
    """

    # ------------------------------------------------------------------
    # _first_int — the stdout reader
    # ------------------------------------------------------------------

    def test_first_int_parses_first_line(self) -> None:
        """Returns the first stdout line as an int."""
        mock_result = MagicMock(returncode=0, stdout="1\n1\n")
        with patch("subprocess.run", return_value=mock_result):
            value = spawn_agents.AgentSpawner._first_int(["tmux", "x"], 0)
        assert value == 1

    def test_first_int_returns_default_on_nonzero_returncode(self) -> None:
        """Command failure (e.g. no tmux server) → default returned."""
        mock_result = MagicMock(returncode=1, stdout="")
        with patch("subprocess.run", return_value=mock_result):
            value = spawn_agents.AgentSpawner._first_int(["tmux", "x"], 0)
        assert value == 0

    def test_first_int_returns_default_on_non_numeric_output(self) -> None:
        """Non-numeric stdout → default returned."""
        mock_result = MagicMock(returncode=0, stdout="not-a-number\n")
        with patch("subprocess.run", return_value=mock_result):
            value = spawn_agents.AgentSpawner._first_int(["tmux", "x"], 0)
        assert value == 0

    def test_first_int_returns_default_when_command_missing(self) -> None:
        """``tmux`` binary absent → subprocess raises → default returned."""
        with patch("subprocess.run", side_effect=FileNotFoundError("tmux")):
            value = spawn_agents.AgentSpawner._first_int(["tmux", "x"], 0)
        assert value == 0

    # ------------------------------------------------------------------
    # __init__ — placeholder defaults only
    # ------------------------------------------------------------------

    def test_init_uses_placeholder_indices_before_session_exists(
        self, tmp_path: Path
    ) -> None:
        """Constructor sets placeholder 0/0; no tmux query happens at init."""
        config = MagicMock()
        config.project_name = "Test Project"
        config.agent_model = None
        templates = tmp_path / "templates"
        templates.mkdir()

        with patch("subprocess.run") as mock_run:
            spawner = spawn_agents.AgentSpawner(config, templates)

        assert spawner._tmux_base_index == 0
        assert spawner._tmux_pane_base_index == 0
        # __init__ must not shell out to tmux — detection is deferred.
        mock_run.assert_not_called()

    # ------------------------------------------------------------------
    # create_tmux_session — detection from the live session
    # ------------------------------------------------------------------

    def test_create_tmux_session_detects_indices_from_live_session(self) -> None:
        """Detection reads the real window/pane indices of the new session.

        Regression for the cold-start bug: a non-zero base-index is
        picked up because it is read from the session that exists,
        not from global options queried before the server started.
        """
        spawner = spawn_agents.AgentSpawner.__new__(spawn_agents.AgentSpawner)
        spawner.tmux_session = "marcus_test"

        def fake_run(cmd: list, *args: Any, **kwargs: Any) -> MagicMock:
            if "list-windows" in cmd:
                return MagicMock(returncode=0, stdout="1\n")
            if "list-panes" in cmd:
                return MagicMock(returncode=0, stdout="1\n")
            return MagicMock(returncode=0, stdout="")

        with patch("subprocess.run", side_effect=fake_run):
            spawner.create_tmux_session()

        assert spawner._tmux_base_index == 1
        assert spawner._tmux_pane_base_index == 1

    # ------------------------------------------------------------------
    # target-string offsets
    # ------------------------------------------------------------------

    def _bypass_init_spawner(self, base: int, pane_base: int) -> Any:
        """Build an AgentSpawner without running __init__, with tmux indices set."""
        instance = spawn_agents.AgentSpawner.__new__(spawn_agents.AgentSpawner)
        instance.tmux_session = "marcus_test"
        instance.panes_per_window = 2
        instance.current_window = 0
        instance.current_pane = 0
        instance._tmux_base_index = base
        instance._tmux_pane_base_index = pane_base
        return instance

    def test_new_window_target_includes_base_index_offset(self) -> None:
        """get_next_pane_location offsets the new-window target by base-index."""
        spawner = self._bypass_init_spawner(base=1, pane_base=1)
        spawner.current_pane = 2  # → window 1, pane 0 → triggers new-window

        with patch("subprocess.run") as mock_run:
            window, pane = spawner.get_next_pane_location()

        assert (window, pane) == (1, 0)
        cmd = mock_run.call_args[0][0]
        # window 1 + base-index 1 = 2
        assert "marcus_test:2" in cmd

    def test_first_pane_target_includes_both_offsets(self) -> None:
        """run_in_tmux_pane (pane 0) offsets window AND pane by their bases."""
        spawner = self._bypass_init_spawner(base=1, pane_base=1)

        with (
            patch("subprocess.run") as mock_run,
            patch.object(spawn_agents, "wait_for_pane_ready", return_value=True),
            patch.object(spawn_agents, "confirm_trust_if_prompted"),
            patch("time.sleep"),
        ):
            spawner.run_in_tmux_pane(
                window=0, pane=0, script_file=Path("dummy_script.sh"), title="t"
            )

        # First tmux call is select-pane -t <target>
        first_cmd = mock_run.call_args_list[0][0][0]
        # window 0 + base 1 = 1, pane base 1 → "marcus_test:1.1"
        assert "marcus_test:1.1" in first_cmd

    def test_default_indices_preserve_classic_zero_targets(self) -> None:
        """With both bases 0 (tmux default) targets are unchanged — back-compat."""
        spawner = self._bypass_init_spawner(base=0, pane_base=0)

        with (
            patch("subprocess.run") as mock_run,
            patch.object(spawn_agents, "wait_for_pane_ready", return_value=True),
            patch.object(spawn_agents, "confirm_trust_if_prompted"),
            patch("time.sleep"),
        ):
            spawner.run_in_tmux_pane(
                window=0, pane=0, script_file=Path("dummy_script.sh"), title="t"
            )

        first_cmd = mock_run.call_args_list[0][0][0]
        assert "marcus_test:0.0" in first_cmd
