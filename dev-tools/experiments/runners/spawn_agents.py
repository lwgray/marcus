#!/usr/bin/env python3
"""
Marcus Multi-Agent Experiment Spawner.

Spawns autonomous agents for a Marcus experiment based on config.yaml.
All agents work on the main branch in the experiment's implementation directory.
"""

import json
import os
import subprocess  # nosec B404
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def wait_for_pane_ready(
    pane_target: str,
    timeout: float = 10.0,
    poll_interval: float = 0.3,
) -> bool:
    """Wait for a tmux pane's shell to be ready before sending commands.

    Polls the pane content until a shell prompt indicator appears or the
    content stabilizes (stops changing for 2+ consecutive polls). This
    prevents send-keys from firing before the shell is initialized.

    Parameters
    ----------
    pane_target : str
        Tmux pane target (e.g. ``session:window.pane`` or a pane ID).
    timeout : float
        Maximum seconds to wait before giving up.
    poll_interval : float
        Seconds between polls.

    Returns
    -------
    bool
        True if the pane is ready, False if timed out.
    """
    prompt_indicators = {"$", "%", "#", "❯", ">", "›"}
    deadline = time.monotonic() + timeout
    prev_content = ""
    stable_count = 0

    while time.monotonic() < deadline:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_target],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            time.sleep(poll_interval)
            continue

        content = result.stdout.rstrip()

        # Check for shell prompt indicators on the last non-empty line
        lines = [ln for ln in content.split("\n") if ln.strip()]
        if lines:
            last_line = lines[-1].strip()
            if any(last_line.endswith(ind) for ind in prompt_indicators):
                return True

        # Content stabilization: if content hasn't changed for 2 polls
        # and there IS content, the shell is ready
        if content and content == prev_content:
            stable_count += 1
            if stable_count >= 2:
                return True
        else:
            stable_count = 0

        prev_content = content
        time.sleep(poll_interval)

    return False


def confirm_trust_if_prompted(
    pane_target: str,
    timeout: float = 5.0,
    poll_interval: float = 0.2,
) -> bool:
    """Poll a tmux pane and auto-confirm Claude trust/permission dialogs.

    Claude Code can pause on a directory trust prompt or a
    --dangerously-skip-permissions confirmation dialog when launched in a
    fresh directory. This detects those screens and sends the appropriate
    keystrokes to proceed.

    Parameters
    ----------
    pane_target : str
        Tmux pane target (e.g. ``session:window.pane`` or a pane ID).
    timeout : float
        Maximum seconds to poll before giving up.
    poll_interval : float
        Seconds between polls.

    Returns
    -------
    bool
        True if a prompt was detected and confirmed.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", pane_target],
            capture_output=True,
            text=True,
        )
        text = result.stdout.lower() if result.returncode == 0 else ""

        # Trust prompt: "Do you trust this folder?"
        if ("trust this folder" in text or "trust the contents" in text) and (
            "enter to confirm" in text
            or "press enter" in text
            or "enter to continue" in text
        ):
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, "Enter"],
                capture_output=True,
            )
            time.sleep(0.5)
            return True

        # --dangerously-skip-permissions confirmation dialog
        if "yes, i accept" in text and (
            "dangerously-skip-permissions" in text
            or "skip permissions" in text
            or "permission" in text
            or "approval" in text
        ):
            # Move selection to "Yes, I accept" then confirm
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, "-l", "\x1b[B"],
                capture_output=True,
            )
            time.sleep(0.2)
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, "Enter"],
                capture_output=True,
            )
            time.sleep(0.5)
            return True

        # Early exit: trust/permission prompts appear immediately on
        # startup and dominate the pane. If the pane has substantial
        # content without any trust-related keywords, Claude has
        # started normally and no prompt is coming.
        if (
            len(text) > 200
            and "trust" not in text
            and "permission" not in text
            and "approval" not in text
        ):
            return False

        time.sleep(poll_interval)

    return False


def check_mcp_health(url: str = "") -> bool:
    """Check if the Marcus MCP server is running and healthy.

    Parameters
    ----------
    url : str
        Base URL of the MCP server. Defaults to MARCUS_URL env var or
        http://localhost:4298/mcp.

    Returns
    -------
    bool
        True if server responds successfully.
    """
    import os

    if not url:
        url = os.environ.get("MARCUS_URL", "http://localhost:4298/mcp")
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", f"{url}/health"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def wait_for_project_info(
    config: "ExperimentConfig",
    poll_interval: float = 5.0,
    log_interval: float = 15.0,
) -> bool:
    """Wait for project_info.json with countdown logging.

    Parameters
    ----------
    config : ExperimentConfig
        Experiment configuration containing project_info_file path
        and timeout settings.
    poll_interval : float
        Seconds between file existence checks.
    log_interval : float
        Seconds between status log messages.

    Returns
    -------
    bool
        True if file was found, False if timed out.
    """
    timeout = config.get_timeout("project_creation", 600)
    start_time = time.time()
    last_log_time = start_time

    print("\nWaiting for project creation...")
    print("  (create_project will take 30-60s for AI task decomposition)")

    while not config.project_info_file.exists():
        elapsed = time.time() - start_time
        if elapsed > timeout:
            remaining = 0
            print(f"\n✗ Project creation timed out after " f"{int(elapsed)}s!")
            return False

        # Log countdown at regular intervals
        if time.time() - last_log_time >= log_interval:
            remaining = int(timeout - elapsed)
            print(
                f"  ... still waiting ({int(elapsed)}s elapsed, "
                f"{remaining}s remaining)"
            )
            last_log_time = time.time()

        time.sleep(poll_interval)

    print("✓ Project created!")
    return True


class ExperimentConfig:
    """Configuration for a Marcus experiment."""

    def __init__(self, config_path: Path):
        """
        Initialize experiment configuration from YAML file.

        Parameters
        ----------
        config_path : Path
            Path to config.yaml file
        """
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.experiment_dir = config_path.parent
        self.project_name = self.config["project_name"]
        self.project_spec_file = self.experiment_dir / self.config["project_spec_file"]
        self.project_options = self.config.get("project_options", {})
        self.agents = self.config["agents"]
        self.max_agents = int(self.config.get("max_agents", 12))
        self.timeouts = self.config.get("timeouts", {})
        # CPM override: when True, Marcus's CPM-derived
        # ``recommended_agents`` overrides the agent template count and
        # determines how many workers spawn. When False (default),
        # exactly ``len(self.agents)`` workers spawn — the count the
        # user configured. Defaults to OFF so controlled experiments
        # (where agent count is the independent variable) get the
        # exact count specified.
        self.cpm_override = bool(self.config.get("cpm_override", False))

        # Set up experiment directories
        self.prompts_dir = self.experiment_dir / "prompts"
        self.logs_dir = self.experiment_dir / "logs"
        self.implementation_dir = self.experiment_dir / "implementation"

        # Create directories
        self.prompts_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.implementation_dir.mkdir(exist_ok=True)

        # Add project_root to project_options (required by Marcus validation)
        # This tells Marcus where agents will write code
        if "project_root" not in self.project_options:
            self.project_options["project_root"] = str(self.implementation_dir)

        # Project info file (shared between creator and workers)
        self.project_info_file = self.experiment_dir / "project_info.json"

        # Tell Marcus where to write project_info.json server-side so the
        # spawner can read recommended_agents without a second HTTP session.
        # If project_info_path is pre-set in options (custom override), keep
        # self.project_info_file in sync so wait_for_project_info and the
        # project_info open() both target the same path (Codex P2 fix).
        if "project_info_path" not in self.project_options:
            self.project_options["project_info_path"] = str(self.project_info_file)
        else:
            from pathlib import Path as _Path

            self.project_info_file = _Path(self.project_options["project_info_path"])

    def get_timeout(self, key: str, default: int) -> int:
        """Get timeout value from config or use default."""
        return int(self.timeouts.get(key, default))


class AgentSpawner:
    """Spawns and manages autonomous agents for an experiment."""

    def __init__(
        self,
        config: ExperimentConfig,
        templates_dir: Path,
        epictetus: bool = False,
    ):
        """
        Initialize the agent spawner.

        Parameters
        ----------
        config : ExperimentConfig
            Experiment configuration
        templates_dir : Path
            Path to templates directory (in marcus repo)
        epictetus : bool, optional
            When True, suppresses tmux session kill on experiment completion
            so that the Epictetus post-experiment interrogation tool can
            query agents after the project is done.  Default: False (kill).
        """
        self.config = config
        self.templates_dir = templates_dir
        self.epictetus = epictetus
        self.agent_prompt_template = templates_dir / "agent_prompt.md"
        self.processes: List[subprocess.Popen[bytes]] = []
        self.tmux_session = (
            f"marcus_{self.config.project_name.lower().replace(' ', '_')}"
        )
        self.panes_per_window = 2
        self.current_window = 0
        self.current_pane = 0
        # Resolve the Marcus MCP URL once at spawner init time so it is
        # baked into each generated shell script. tmux new-session does NOT
        # inherit the calling process's environment (tmux runs a daemon), so
        # ${MARCUS_URL:-...} inside pane shells always falls back to the
        # default port 4298 even when MARCUS_URL is set in the caller's env.
        self.marcus_mcp_url: str = os.environ.get(
            "MARCUS_URL", "http://localhost:4298/mcp"
        )

    @staticmethod
    def _pretrust_directory(directory: Path) -> None:
        """Pre-trust a directory in ~/.claude.json.

        Marks the directory as trusted so Claude skips the
        'Do you trust this folder?' prompt.

        Uses an exclusive lock file so parallel experiments don't race
        to read-modify-write ~/.claude.json simultaneously, which can
        cause one process to overwrite another's trust entry.

        Parameters
        ----------
        directory : Path
            Directory to mark as trusted.
        """
        import fcntl

        claude_json = Path.home() / ".claude.json"
        lock_path = Path.home() / ".claude.json.lock"
        try:
            with open(lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    if claude_json.exists():
                        with open(claude_json, "r") as f:
                            config = json.load(f)
                    else:
                        config = {}

                    projects = config.setdefault("projects", {})
                    dir_key = str(directory)

                    if dir_key not in projects:
                        projects[dir_key] = {
                            "allowedTools": [],
                            "mcpContextUris": [],
                            "mcpServers": {},
                            "enabledMcpjsonServers": [],
                            "disabledMcpjsonServers": [],
                            "hasTrustDialogAccepted": True,
                        }
                        print(f"  ✓ Pre-trusted directory: {directory}")
                    elif not projects[dir_key].get("hasTrustDialogAccepted"):
                        projects[dir_key]["hasTrustDialogAccepted"] = True
                        print(f"  ✓ Re-trusted directory: {directory}")
                    else:
                        print(f"  ✓ Directory already trusted: {directory}")
                        return

                    with open(claude_json, "w") as f:
                        json.dump(config, f, indent=2)
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠️  Could not pre-trust directory: {e}")

    def create_project_creator_prompt(self) -> str:
        """
        Create the prompt for the project creator agent.

        Returns
        -------
        str
            Prompt for project creation
        """
        with open(self.config.project_spec_file, "r") as f:
            project_description = f.read()

        options_str = json.dumps(self.config.project_options)

        prompt = f"""You are an autonomous Project Creator Agent. Execute these \
steps IMMEDIATELY without asking for permission.

WORKING DIRECTORY: {self.config.implementation_dir}

EXECUTE NOW - DO NOT ASK FOR CONFIRMATION:

1. First, verify the environment (quick checks only):
   - Confirm working directory: {self.config.implementation_dir}
   - Ping Marcus: mcp__marcus__ping

2. Call mcp__marcus__create_project and WAIT FOR COMPLETE RESPONSE:
   - project_name: "{self.config.project_name}"
   - description: (the full spec below)
   - options: {options_str}

   CRITICAL: This call is SYNCHRONOUS and takes 30-60 seconds
   - The AI will break down the spec into tasks AND subtasks
   - Do NOT proceed to step 3 until you see the FULL response
   - The response contains project_id, board_id, and tasks_created count
   - When the response arrives, ALL subtasks are already created in Kanban

PROJECT SPECIFICATION:
{project_description}

3. ONLY AFTER create_project returns with full response:
   - Marcus has already written {self.config.project_info_file} automatically.
     DO NOT overwrite this file — it contains recommended_agents from CPM.
   - Just verify {self.config.project_info_file} exists (it must be there).
   - Extract project_id from the create_project response for use in step 4.
   - Run: git add -A && git commit -m "Initial commit: Marcus project created"
   - Print: "PROJECT CREATED: project_id=<id> tasks=<count>"

4. IMMEDIATELY start MLflow experiment tracking:
   - Call mcp__marcus__start_experiment with:
     - experiment_name: "\
{self.config.project_name.lower().replace(' ', '_')}_experiment"
     - run_name: "\
{self.config.project_name.lower().replace(' ', '_')}_{{timestamp}}"
     - project_id: (the project_id from step 2)
     - board_id: (the board_id from step 2)
     - tags: {{"project_type": \
"{self.config.project_options.get('complexity', 'standard')}", \
"provider": "{self.config.project_options.get('provider', 'sqlite')}"}}
     - params: {{"num_agents": {len(self.config.agents)}}}
   - Print: "EXPERIMENT STARTED: <experiment_name>"
   - Exit

CRITICAL INSTRUCTIONS:
- Work in: {self.config.implementation_dir}
- DO NOT ask "May I proceed?" - just do it
- DO NOT wait for confirmation - execute immediately
- This is an automated process - no human interaction needed
"""
        return prompt

    def create_worker_prompt(
        self,
        agent: Dict[str, Any],
        workspace: Optional[Path] = None,
        branch: str = "main",
    ) -> str:
        """
        Create the prompt for a worker agent.

        Parameters
        ----------
        agent : Dict
            Agent configuration from config.yaml
        workspace : Path, optional
            Agent's worktree path. Defaults to implementation_dir.
        branch : str
            Agent's git branch. Defaults to "main".

        Returns
        -------
        str
            Prompt for worker agent
        """
        # Read the base agent prompt template
        with open(self.agent_prompt_template, "r") as f:
            base_prompt = f.read()

        agent_id = agent["id"]
        agent_name = agent["name"]
        agent_role = agent["role"]
        agent_skills = agent["skills"]
        num_subagents = agent.get("subagents", 0)

        work_dir = workspace or self.config.implementation_dir

        worker_prompt = f"""You are {agent_name} (ID: {agent_id})
in a Marcus multi-agent experiment.

Your role: {agent_role}
Your skills: {", ".join(agent_skills)}
Project root: {work_dir}

STARTUP SEQUENCE:
1. Wait for project_info.json to exist at {self.config.project_info_file}
   (check every 5 seconds, max 60 seconds)
   (This signals the project has been created and is ready)

2. Read project_info.json at {self.config.project_info_file} and extract
   project_id (required for project-scoped task assignment — GH-388).
   Then use mcp__marcus__register_agent to register yourself:
   - agent_id: "{agent_id}"
   - name: "{agent_name}"
   - role: "{agent_role}"
   - skills: {json.dumps(agent_skills)}
   - project_id: <project_id from project_info.json>

3. Register {num_subagents} subagents:
   For i in 1 to {num_subagents}:
   - Use mcp__marcus__register_agent with:
     - agent_id: "{agent_id}_sub{{i}}"
     - name: "{agent_name} Subagent {{i}}"
     - role: "{agent_role}"
     - skills: {json.dumps(agent_skills)}
     - project_id: <same project_id from project_info.json>

4. Call mcp__marcus__request_next_task:
   - No parameters needed
   - This will find tasks suitable for your skills
   - If you get "no suitable tasks": Marcus will tell you EXACTLY how
     long to sleep in the response (`retry_after_seconds`) and instruct
     you to keep retrying. TRUST that signal. Sleep the requested
     duration, then call request_next_task again. There is NO retry
     cap — keep looping. Marcus knows when work is genuinely done and
     will signal experiment completion separately.

5. When you get a task:
   - FIRST: run `git merge main --no-edit` to get latest completed work
   - Check dependencies with get_task_context
   - Work on it in: {work_dir}
   - Report progress at 25%, 50%, 75%, 100%
   - Commit to your branch: {branch} (git add, commit)
   - When 100% complete, IMMEDIATELY call request_next_task again

6. Repeat step 4-5 until the experiment ends. To check experiment
   state, call mcp__marcus__get_experiment_status and read TWO
   fields together:
     status["experiment_started"]  and  status["is_running"]

   These describe a 3-state lifecycle:
     - experiment_started=False                  → startup window.
       The project creator hasn't called start_experiment yet. Sleep
       10 seconds and re-poll. Do NOT exit; the experiment hasn't
       begun.
     - experiment_started=True, is_running=True  → active. Keep
       working. Sleep retry_after_seconds from your last
       request_next_task response, then call request_next_task again.
     - experiment_started=True, is_running=False → finished. Print a
       summary of your work and exit.

   Marcus owns the completion decision. It computes project completion
   from kanban state using this formula:
     in_progress_tasks == 0
     AND (completed_tasks + blocked_tasks) == total_tasks
   and flips is_running to false when the condition is met. blocked
   tasks count toward "done" because Marcus treats a blocked task as
   terminal — the project should not stall waiting for it. Your only
   job is to read the lifecycle fields and act on them. You do not
   compute completion yourself.

---

{base_prompt}

---

CRITICAL REMINDERS:
- Work directory: {work_dir}
- Git branch: {branch} (your isolated workspace)
- After EVERY task completion, IMMEDIATELY request_next_task
- Use get_task_context for tasks with dependencies
- Use log_decision for architectural choices
- Use log_artifact with project_root: {work_dir}
- A "no suitable tasks" response from request_next_task means
  "sleep retry_after_seconds, then call request_next_task again."
  That is your only correct action. Lease recovery and dependency
  unblocking can take minutes — keep polling until is_running goes
  false in get_experiment_status.
- The single source of truth for "should I stop?" is
  get_experiment_status → is_running. When is_running is true, keep
  polling. When is_running is false, exit.

START NOW!
"""
        return worker_prompt

    def _monitor_completion_action(self) -> str:
        """
        Return the completion-action instructions for the monitor prompt.

        When epictetus mode is OFF (default), the monitor kills the tmux
        session after a 60-second grace period so worker agents stop
        burning tokens.  The kill targets ONLY this experiment's session
        by name, leaving other concurrent Marcus sessions unaffected.

        When epictetus mode is ON, the session is kept alive so that the
        Epictetus post-experiment interrogation tool can query agents after
        the project finishes.

        Returns
        -------
        str
            One or more instruction lines to embed in the monitor prompt.
        """
        if self.epictetus:
            return (
                'Print: "Epictetus mode active — session kept alive for '
                'agent interrogation"\n'
                "      - Exit this monitor process. Do NOT kill the tmux session."
            )
        return (
            f"Sleep 60 seconds (grace period for agents to exit cleanly via "
            f"the EXPERIMENT_COMPLETE signal from request_next_task)\n"
            f"      - Run this bash command to terminate all agent panes:\n"
            f"          tmux kill-session -t {self.tmux_session}\n"
            f"        (This kills ONLY the '{self.tmux_session}' session. "
            f"Other concurrent Marcus sessions are unaffected.)\n"
            f"      - Exit"
        )

    def create_monitor_prompt(self) -> str:
        """
        Create the prompt for the experiment monitor agent.

        Returns
        -------
        str
            Prompt for monitor agent
        """
        prompt = f"""You are the Experiment Monitor Agent for a Marcus \
multi-agent experiment.

WORKING DIRECTORY: {self.config.implementation_dir}

YOUR MISSION:
Monitor project progress and end the experiment when all work is complete.

EXECUTE NOW - DO NOT ASK FOR CONFIRMATION:

1. Wait for project creation:
   - Wait for {self.config.project_info_file} to exist
   - Read project_id and board_id from it

2. Register with Marcus:
   - Call mcp__marcus__register_agent:
     - agent_id: "monitor"
     - name: "Experiment Monitor"
     - role: "monitor"
     - skills: ["monitoring", "analytics"]
     - project_id: <project_id from project_info.json>

3. Enter monitoring loop. Read the lifecycle fields
   (experiment_started, is_running) from the response and branch on
   the 3-state lifecycle:

   a. Call mcp__marcus__get_experiment_status. The MCP tool
      description documents every field in the response — read it
      if you need to know what a field means.

   b. If status["experiment_started"] is False:
      - Print "Waiting for experiment to start..."
      - Sleep 10 seconds, then loop back to (a)

   c. If status["experiment_started"] is True and \
status["is_running"] is True:
      - done = status["completed_tasks"]
      - total = status["total_tasks"]
      - percent = round(100 * done / total, 1) if total else 0.0
      - Print:
        "Project Status: {{done}}/{{total}} tasks complete \
({{percent}}%)"
        "  In Progress: {{status['in_progress_tasks']}}, \
Blocked: {{status['blocked_tasks']}}"
        "  Registered agents: {{status['registered_agents']}}"
      - Sleep 120 seconds, then loop back to (a)

   d. If status["experiment_started"] is True and \
status["is_running"] is False:
      - Print "EXPERIMENT COMPLETE!"
      - Print the final values of total_tasks, completed_tasks,
        in_progress_tasks, blocked_tasks, and registered_agents
      - {self._monitor_completion_action()}

CRITICAL INSTRUCTIONS:
- Work in: {self.config.implementation_dir}
- Poll interval: 120 seconds (2 minutes) between get_experiment_status
  calls during the active state. Use 10 seconds while waiting for
  experiment_started to become True.
- Marcus owns the completion decision. It flips is_running to False
  when the project is done — when in_progress_tasks == 0 AND
  (completed_tasks + blocked_tasks) == total_tasks. Your job is to
  display progress while the experiment is active and exit when it
  finishes.
- This is an automated process - no human interaction needed
"""
        return prompt

    def create_tmux_session(self) -> None:
        """Create tmux session for the experiment."""
        # Kill existing session if it exists
        subprocess.run(
            ["tmux", "kill-session", "-t", self.tmux_session],
            capture_output=True,
        )

        # Create new session (detached) with explicit dimensions so panes
        # are large enough for Claude's TUI even before a client attaches.
        subprocess.run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                self.tmux_session,
                "-n",
                "agents-0",
                "-x",
                "200",
                "-y",
                "50",
            ],
            check=True,
        )

        # Enable mouse mode for easy pane navigation
        subprocess.run(
            ["tmux", "set-option", "-t", self.tmux_session, "mouse", "on"],
            check=True,
        )

        # Enable pane border status to show pane titles
        subprocess.run(
            [
                "tmux",
                "set-option",
                "-t",
                self.tmux_session,
                "pane-border-status",
                "top",
            ],
            check=True,
        )

        # Set pane border format to show the title clearly
        subprocess.run(
            [
                "tmux",
                "set-option",
                "-t",
                self.tmux_session,
                "pane-border-format",
                "#{pane_index}: #{pane_title}",
            ],
            check=True,
        )

        print(f"✓ Created tmux session: {self.tmux_session}")
        print("  - Mouse mode enabled (click to switch panes)")
        print("  - Pane borders show agent names")

    def get_next_pane_location(self) -> tuple[int, int]:
        """
        Get the next window and pane number for an agent.

        Returns
        -------
        tuple[int, int]
            (window_number, pane_number)
        """
        window = self.current_pane // self.panes_per_window
        pane = self.current_pane % self.panes_per_window

        # Create new window if needed
        if pane == 0 and window > self.current_window:
            subprocess.run(
                [
                    "tmux",
                    "new-window",
                    "-t",
                    f"{self.tmux_session}:{window}",
                    "-n",
                    f"agents-{window}",
                ],
                check=True,
            )
            self.current_window = window

        self.current_pane += 1
        return window, pane

    def run_in_tmux_pane(
        self, window: int, pane: int, script_file: Path, title: str
    ) -> None:
        """
        Run a script in a specific tmux pane.

        Parameters
        ----------
        window : int
            Window number
        pane : int
            Pane number within the window
        script_file : Path
            Path to the script to run
        title : str
            Title for the pane
        """
        # For first pane in window, use existing pane
        if pane == 0:
            target = f"{self.tmux_session}:{window}.0"
        else:
            # Split the window and get the new pane's target.
            # Layout: 0=left, 1=right (2 panes per window, side-by-side).
            if pane == 1:
                # Split window horizontally so pane 1 lands to the
                # right of pane 0.
                split_direction = "-h"
                split_target = f"{self.tmux_session}:{window}.0"
            else:
                raise ValueError(
                    f"Invalid pane number: {pane} "
                    f"(expected 0 or 1 with panes_per_window=2)"
                )

            # Split and capture the new pane ID
            result = subprocess.run(
                [
                    "tmux",
                    "split-window",
                    split_direction,
                    "-t",
                    split_target,
                    "-P",  # Print new pane ID
                    "-F",
                    "#{pane_id}",  # Format: just the pane ID
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            # Use the actual pane ID returned by tmux
            target = result.stdout.strip()
            time.sleep(0.2)  # Give tmux time to stabilize

        # Set pane title
        subprocess.run(
            ["tmux", "select-pane", "-t", target, "-T", title],
            check=True,
        )

        # Wait for the pane shell to be ready before sending commands
        if not wait_for_pane_ready(target):
            print(f"  ⚠ Pane {target} did not stabilize, sending anyway")

        # Send commands to the pane using its actual ID
        subprocess.run(
            ["tmux", "send-keys", "-t", target, f"bash {script_file}", "Enter"],
            check=True,
        )

        # Auto-confirm any trust or permission prompts from Claude
        time.sleep(1)  # Let Claude start up before polling
        confirm_trust_if_prompted(target)

    def copy_agent_workflow_to_implementation(self) -> None:
        """
        Copy agent workflow instructions to CLAUDE.md in implementation directory.

        This ensures agents can reference the workflow throughout their session
        even after the initial prompt is forgotten.
        """
        claude_md_path = self.config.implementation_dir / "CLAUDE.md"

        # Read the agent prompt template
        with open(self.agent_prompt_template, "r") as f:
            workflow_content = f.read()

        # Write to CLAUDE.md in implementation directory
        with open(claude_md_path, "w") as f:
            f.write(workflow_content)

        print(f"✓ Agent workflow copied to {claude_md_path}")

    def spawn_project_creator(self) -> None:
        """Spawn the project creator agent in a tmux pane."""
        print("=" * 60)
        print("Spawning Project Creator Agent")
        print("=" * 60)

        # Copy agent workflow to implementation directory
        self.copy_agent_workflow_to_implementation()

        prompt = self.create_project_creator_prompt()
        prompt_file = self.config.prompts_dir / "project_creator.txt"

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Create a script to run in tmux
        script = f"""#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

# Normalize TERM for non-interactive shells (IDE terminals, CI, cron)
if [ "$TERM" = "dumb" ] || [ -z "$TERM" ]; then
    export TERM=xterm-256color
fi

cd {self.config.implementation_dir} || exit 1
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Configuring Marcus MCP..."
MARCUS_MCP_URL="{self.marcus_mcp_url}"
claude mcp add marcus -t http "$MARCUS_MCP_URL" 2>/dev/null || true
echo ""
echo "Creating Marcus project: {self.config.project_name}"
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir {self.config.implementation_dir} \
  --dangerously-skip-permissions --print < {prompt_file}
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
"""
        script_file = self.config.prompts_dir / "project_creator.sh"
        with open(script_file, "w") as f:
            f.write(script)
        script_file.chmod(0o755)

        # Get pane location and run
        window, pane = self.get_next_pane_location()
        self.run_in_tmux_pane(window, pane, script_file, "Project Creator")

        print(f"✓ Project creator in tmux window {window}, pane {pane}")
        print(f"  Prompt: {prompt_file}")

    def _create_agent_worktree(
        self,
        agent_id: str,
        agent_name: str,
        branch: str,
        workspace: Path,
    ) -> None:
        """
        Create an isolated git worktree for a worker agent.

        Each agent gets its own worktree branched from main HEAD.
        Git identity is set per worktree for commit attribution.
        See: https://github.com/lwgray/marcus/issues/250

        Parameters
        ----------
        agent_id : str
            Agent identifier
        agent_name : str
            Human-readable agent name (for git user.name)
        branch : str
            Branch name (e.g., marcus/agent_unicorn_1)
        workspace : Path
            Path for the worktree directory
        """
        repo = self.config.implementation_dir

        # Clean up stale worktree/branch if re-running
        if workspace.exists():
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "remove",
                    "--force",
                    str(workspace),
                ],
                cwd=repo,
                capture_output=True,
            )
        # Prune stale worktree references (e.g., from rm -rf cleanup)
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=repo,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-D", branch],
            cwd=repo,
            capture_output=True,
        )

        # Create worktree (branches from current main HEAD)
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                str(workspace),
                "-b",
                branch,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Git identity is set via GIT_AUTHOR_NAME/GIT_COMMITTER_NAME
        # environment variables in the agent's shell script, NOT via
        # git config — because worktrees share .git/config and the
        # second agent overwrites the first. (GH-308)

        print(f"  ✓ Worktree: {workspace} (branch: {branch})")

    def spawn_worker(self, agent: Dict[str, Any]) -> None:
        """
        Spawn a worker agent in a tmux pane with git worktree isolation.

        Each worker gets its own git worktree on branch marcus/{agent_id}.
        Git identity is set per worktree for commit attribution.
        See: https://github.com/lwgray/marcus/issues/250

        Parameters
        ----------
        agent : Dict
            Agent configuration
        """
        agent_id = agent["id"]
        agent_name = agent["name"]
        agent_role = agent["role"]
        num_subagents = agent.get("subagents", 0)

        print(f"\nSpawning {agent_name} ({agent_id})")
        print("-" * 60)

        # Create git worktree for this agent (GH-250)
        agent_branch = f"marcus/{agent_id}"
        agent_workspace = self.config.experiment_dir / "worktrees" / agent_id
        self._create_agent_worktree(agent_id, agent_name, agent_branch, agent_workspace)

        prompt = self.create_worker_prompt(agent, agent_workspace, agent_branch)
        prompt_file = self.config.prompts_dir / f"{agent_id}.txt"

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Create a script to run in tmux
        script = f"""#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

# Normalize TERM for non-interactive shells (IDE terminals, CI, cron)
if [ "$TERM" = "dumb" ] || [ -z "$TERM" ]; then
    export TERM=xterm-256color
fi

# Set git identity via env vars — per-process, not shared config (GH-308)
# Worktrees share .git/config so git config user.name gets overwritten.
export GIT_AUTHOR_NAME="{agent_name}"
export GIT_AUTHOR_EMAIL="{agent_id}@marcus.ai"
export GIT_COMMITTER_NAME="{agent_name}"
export GIT_COMMITTER_EMAIL="{agent_id}@marcus.ai"

cd {agent_workspace} || exit 1
echo "=========================================="
echo "{agent_name.upper()}"
echo "ID: {agent_id}"
echo "Role: {agent_role}"
echo "Branch: {agent_branch} (isolated worktree)"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f {self.config.project_info_file} ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
echo "Configuring Marcus MCP..."
MARCUS_MCP_URL="{self.marcus_mcp_url}"
claude mcp add marcus -t http "$MARCUS_MCP_URL" 2>/dev/null || true
echo ""
# Sync worktree with main to get design artifacts and any
# previously merged code (GH-302: per-task visibility)
echo "Syncing worktree with main..."
git merge main --no-edit 2>/dev/null || true
echo "✓ Worktree synced"
echo ""
# Launch Claude from the agent's isolated worktree (cwd matters!)
claude --add-dir {agent_workspace} \
  --dangerously-skip-permissions < {prompt_file}
echo ""
echo "=========================================="
echo "{agent_name} - Work Complete"
echo "=========================================="
"""
        script_file = self.config.prompts_dir / f"{agent_id}.sh"
        with open(script_file, "w") as f:
            f.write(script)
        script_file.chmod(0o755)

        # Get pane location and run
        window, pane = self.get_next_pane_location()
        self.run_in_tmux_pane(window, pane, script_file, agent_name)

        print(f"  ✓ Spawned in tmux window {window}, pane {pane}")
        print(f"  Prompt: {prompt_file}")
        print(f"  Subagents: {num_subagents}")

    def spawn_monitor(self) -> None:
        """Spawn the experiment monitor agent in a tmux pane."""
        print("\nSpawning Experiment Monitor")
        print("-" * 60)

        prompt = self.create_monitor_prompt()
        prompt_file = self.config.prompts_dir / "monitor.txt"

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Create a script to run in tmux
        script = f"""#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Prevent Claude from detecting nesting and refusing to start
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT CLAUDE_CODE_SESSION

# Normalize TERM for non-interactive shells (IDE terminals, CI, cron)
if [ "$TERM" = "dumb" ] || [ -z "$TERM" ]; then
    export TERM=xterm-256color
fi

cd {self.config.implementation_dir} || exit 1
echo "=========================================="
echo "EXPERIMENT MONITOR"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f {self.config.project_info_file} ]; do
    sleep 2
done
echo "✓ Project found, starting monitor..."
echo ""
echo "Configuring Marcus MCP..."
MARCUS_MCP_URL="{self.marcus_mcp_url}"
claude mcp add marcus -t http "$MARCUS_MCP_URL" 2>/dev/null || true
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --add-dir {self.config.implementation_dir} \
  --dangerously-skip-permissions < {prompt_file}
echo ""
echo "=========================================="
echo "Experiment Monitor - Complete"
echo "=========================================="
"""
        script_file = self.config.prompts_dir / "monitor.sh"
        with open(script_file, "w") as f:
            f.write(script)
        script_file.chmod(0o755)

        # Get pane location and run
        window, pane = self.get_next_pane_location()
        self.run_in_tmux_pane(window, pane, script_file, "Monitor")

        print(f"  ✓ Spawned in tmux window {window}, pane {pane}")
        print(f"  Prompt: {prompt_file}")

    @staticmethod
    def _fetch_recommended_agents(
        marcus_url: str = "http://localhost:4298/mcp",
        timeout: float = 10.0,
    ) -> int:
        """Query Marcus directly for the recommended agent count via MCP HTTP.

        Bypasses the LLM creator agent entirely.  Called after Phase 1 so
        that ``create_project`` has already populated the server's in-memory
        task list, giving CPM meaningful data to work with.

        Parameters
        ----------
        marcus_url : str
            Base MCP endpoint for the running Marcus server.
        timeout : float
            Per-request timeout in seconds.

        Returns
        -------
        int
            Recommended agent count, or 0 if the call fails (caller falls
            back to the user-supplied config count).
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        def _post(payload: Dict[str, Any], extra_headers: Dict[str, str]) -> bytes:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                marcus_url,
                data=data,
                headers={**headers, **extra_headers},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                result: bytes = resp.read()
            return result

        try:
            # Step 1 — initialize session
            init_payload: Dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "experiment-runner", "version": "1.0"},
                },
            }
            init_req = urllib.request.Request(
                marcus_url,
                data=json.dumps(init_payload).encode(),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(
                init_req, timeout=timeout
            ) as resp:  # nosec B310
                session_id = resp.headers.get("mcp-session-id", "")

            if not session_id:
                return 0

            session_headers = {"mcp-session-id": session_id}

            # Step 2 — notifications/initialized (required by MCP spec)
            _post(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
                session_headers,
            )

            # Step 3 — call get_optimal_agent_count
            raw = _post(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "get_optimal_agent_count",
                        "arguments": {"include_details": False},
                    },
                },
                session_headers,
            )

            # Parse SSE envelope: lines starting with "data: "
            for line in raw.decode().splitlines():
                if not line.startswith("data:"):
                    continue
                envelope = json.loads(line[len("data:") :].strip())
                structured = (
                    envelope.get("result", {})
                    .get("structuredContent", {})
                    .get("result", {})
                )
                optimal = structured.get("optimal_agents", 0)
                return int(optimal)

        except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError) as e:
            print(
                f"\n  CPM query failed ({type(e).__name__}: {e}); "
                "falling back to config count."
            )

        return 0

    def run(self) -> bool:
        """Run the multi-agent experiment and return success status."""
        print("\n" + "=" * 60)
        print("Marcus Multi-Agent Experiment")
        print("=" * 60)
        print(f"Experiment: {self.config.experiment_dir}")
        print(f"Project: {self.config.project_name}")
        print(f"Implementation: {self.config.implementation_dir}")
        print(f"Agents: {len(self.config.agents)}")
        total_subagents = sum(a.get("subagents", 0) for a in self.config.agents)
        print(f"Subagents: {total_subagents}")

        # Calculate tmux layout
        total_agents = 1 + len(self.config.agents) + 1  # creator + workers + monitor
        num_windows = (
            total_agents + self.panes_per_window - 1
        ) // self.panes_per_window
        print(
            f"Tmux Layout: {num_windows} window(s) with up to "
            f"{self.panes_per_window} panes each"
        )
        print("=" * 60)

        # Verify MLflow is available
        print("\n[Setup] Verifying MLflow installation...")
        try:
            import warnings

            warnings.filterwarnings(
                "ignore",
                message='Field "model_name" has conflict with protected namespace',
            )
            import mlflow  # noqa: F401

            print("✓ MLflow is installed and ready")
            print("  Experiments will be tracked in: ./mlruns")
        except ImportError:
            print("⚠️  MLflow not found!")
            print("  Install with: pip install mlflow")
            print("  Experiment tracking will not be available")

        # Clean up state from previous runs
        print("\n[Setup] Cleaning up previous experiment state...")
        if self.config.project_info_file.exists():
            self.config.project_info_file.unlink()
            print("  ✓ Removed old project_info.json")

        # Initialize git repository if not already present
        git_dir = self.config.implementation_dir / ".git"
        if not git_dir.exists():
            print("\n[Setup] Initializing git repository...")
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=self.config.implementation_dir,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "checkout", "-b", "main"],
                    cwd=self.config.implementation_dir,
                    check=True,
                    capture_output=True,
                )
                # Create initial commit so worktrees and merges work
                subprocess.run(
                    ["git", "commit", "--allow-empty", "-m", "Initial commit"],
                    cwd=self.config.implementation_dir,
                    check=True,
                    capture_output=True,
                )
                print("  ✓ Git repository initialized on main branch")
            except subprocess.CalledProcessError as e:
                print(f"  ⚠️  Git initialization failed: {e}")
        else:
            print("\n[Setup] Git repository already initialized")

        # Pre-trust the implementation directory so Claude doesn't
        # show the "Do you trust this folder?" prompt.
        self._pretrust_directory(self.config.implementation_dir)

        # Create tmux session
        print("\n[Setup] Creating tmux session")
        self.create_tmux_session()

        # Phase 1: Spawn project creator
        print("\n[Phase 1] Creating Project")
        self.spawn_project_creator()

        # Wait for project creation
        # (create_project is synchronous - when project_info.json exists,
        #  all subtasks are already created)
        if not wait_for_project_info(self.config):
            return False

        # Read project info
        with open(self.config.project_info_file, "r") as f:
            project_info = json.load(f)
            project_id = project_info.get("project_id")
            board_id = project_info.get("board_id")
            tasks_created = project_info.get("tasks_created", "unknown")

        print(f"  Project ID: {project_id}")
        print(f"  Board ID: {board_id}")
        print(f"  Tasks Created: {tasks_created}")

        # Determine worker count.
        #
        # Two modes, controlled by ``cpm_override`` in config.yaml:
        #
        # cpm_override = False (default):
        #     Use the exact agent count from config templates. This is
        #     the right behavior for controlled experiments where the
        #     agent count IS the independent variable — letting CPM
        #     override silently corrupts the experimental design.
        #
        # cpm_override = True:
        #     Defer to Marcus's CPM-derived ``recommended_agents`` from
        #     project_info.json. Templates cycle if CPM wants more
        #     agents than templates exist. Use this when running
        #     production work and you want Marcus to right-size the
        #     pool to the work graph.
        #
        # Safety valve: max_agents (config.yaml key, default 12) caps
        # both modes to prevent runaway spawning.
        template_count = len(self.config.agents)
        max_cap = self.config.max_agents
        recommended = project_info.get("recommended_agents", 0)
        if self.config.cpm_override and recommended:
            agents_count = min(recommended, max_cap)
            print(
                f"\n  cpm_override=ON: CPM recommends {recommended} agents "
                f"(cap: {max_cap}, templates: {template_count}). "
                f"Spawning {agents_count}."
            )
        else:
            agents_count = min(template_count, max_cap)
            mode_label = (
                "cpm_override=OFF"
                if not self.config.cpm_override
                else ("cpm_override=ON but CPM unavailable")
            )
            print(
                f"\n  {mode_label}: using exact template count "
                f"({agents_count} agents)."
            )

        # Build agent list: use config templates in order; when CPM needs
        # more agents than templates exist, cycle through templates and give
        # each extra a unique id/name suffix.
        agents_to_spawn: list[dict[str, Any]] = []
        for i in range(agents_count):
            if i < len(self.config.agents):
                agents_to_spawn.append(dict(self.config.agents[i]))
            else:
                # Cycle through templates for overflow agents
                template = dict(
                    self.config.agents[i % len(self.config.agents)]
                    if self.config.agents
                    else {
                        "id": f"agent_unicorn_{i + 1}",
                        "name": f"Unicorn Developer {i + 1}",
                        "role": "full-stack",
                        "skills": ["python", "javascript"],
                        "subagents": 0,
                    }
                )
                template["id"] = f"{template['id']}_x{i + 1}"
                template["name"] = f"{template['name']} (extra {i + 1})"
                template["subagents"] = 0  # overflow agents never inherit subagents
                agents_to_spawn.append(template)

        # Phase 2: Spawn worker agents
        print("\n" + "=" * 60)
        num_agents = len(agents_to_spawn)
        print(f"[Phase 2] Spawning {num_agents} Worker Agents")
        print("=" * 60)

        for agent in agents_to_spawn:
            self.spawn_worker(agent)
            time.sleep(0.5)  # Stagger starts to avoid tmux race conditions

        # Phase 3: Spawn monitor agent
        print("\n" + "=" * 60)
        print("[Phase 3] Spawning Experiment Monitor")
        print("=" * 60)
        self.spawn_monitor()

        print("\n" + "=" * 60)
        print("All Agents Spawned!")
        print("=" * 60)
        print(f"\n✓ All agents running in tmux session: {self.tmux_session}")
        print(f"✓ 1 project creator + {num_agents} workers + 1 monitor")
        print(f"✓ {total_subagents} subagents will be registered by workers")
        print("✓ Monitor will poll project status every 2 minutes")
        print(
            f"\n📺 Tmux layout: {num_windows} window(s), "
            f"{self.panes_per_window} panes max per window"
        )
        print("\nTmux Navigation:")
        print(f"  - Attach to session: tmux attach -t {self.tmux_session}")
        print("  - Switch panes: Click with mouse OR Ctrl+b arrow keys")
        print("  - Switch windows: Ctrl+b n (next) or Ctrl+b p (previous)")
        print("  - Zoom pane: Ctrl+b z (toggle fullscreen)")
        print("  - Detach: Ctrl+b d")
        print(f"  - Kill session: tmux kill-session -t {self.tmux_session}")
        print(
            "\nAll agents work on the MAIN branch in the same "
            "implementation directory."
        )
        print("Marcus coordinates task assignment to prevent conflicts.")

        # Check if we're in an interactive terminal
        import os

        is_tty = os.isatty(sys.stdout.fileno())

        if is_tty:
            print("\n" + "=" * 60)
            print("Attaching to tmux session in 3 seconds...")
            print("=" * 60)
            print("\n💡 TIP: You can now click between panes with your mouse!")
            print("   Each pane shows a different agent's terminal.")
            # Give time to read the instructions
            time.sleep(3)

            # Select the first pane before attaching
            subprocess.run(
                ["tmux", "select-window", "-t", f"{self.tmux_session}:0"],
                check=False,
            )
            subprocess.run(
                ["tmux", "select-pane", "-t", f"{self.tmux_session}:0.0"],
                check=False,
            )

            # Attach to the tmux session (this blocks until user detaches)
            try:
                result = subprocess.run(
                    ["tmux", "attach", "-t", self.tmux_session],
                    check=False,
                )
                if result.returncode != 0:
                    print("\n⚠️  Failed to attach to tmux session.")
                    print(
                        f"   Manually attach with: tmux attach -t {self.tmux_session}"
                    )
            except KeyboardInterrupt:
                print("\n\nDetached from tmux session.")
            except Exception as e:
                print(f"\n⚠️  Error attaching to tmux: {e}")
                print(f"   Manually attach with: tmux attach -t {self.tmux_session}")
        else:
            print("\n⚠️  Not running in interactive terminal - skipping auto-attach")
            print(f"   Manually attach with: tmux attach -t {self.tmux_session}")

        print("\nExperiment manager shutting down...")
        print(f"Tmux session '{self.tmux_session}' is still running.")
        print(f"To re-attach: tmux attach -t {self.tmux_session}")
        print(f"To kill session: tmux kill-session -t {self.tmux_session}")
        return True


def main() -> None:
    """Run the experiment spawner."""
    if len(sys.argv) < 2:
        print("Usage: python spawn_agents.py <experiment_dir>")
        print("Example: python spawn_agents.py ~/my-experiments/task-api")
        sys.exit(1)

    experiment_dir = Path(sys.argv[1]).resolve()
    config_file = experiment_dir / "config.yaml"

    if not config_file.exists():
        print(f"Error: config.yaml not found at {config_file}")
        template_path = "experiments/templates/config.yaml.template"
        print(
            f"\nCreate a config.yaml in {experiment_dir} "
            f"using the template at {template_path}"
        )
        sys.exit(1)

    # Find templates directory (relative to this script)
    script_dir = Path(__file__).parent
    templates_dir = script_dir / "templates"

    if not templates_dir.exists():
        print(f"Error: Templates directory not found at {templates_dir}")
        sys.exit(1)

    # Load config and spawn agents
    config = ExperimentConfig(config_file)
    spawner = AgentSpawner(config, templates_dir)
    success = spawner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
