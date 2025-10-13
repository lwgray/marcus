#!/usr/bin/env python3
"""
Marcus Multi-Agent Experiment Spawner.

Spawns autonomous agents for a Marcus experiment based on config.yaml.
All agents work on the main branch in the experiment's implementation directory.
"""

import json
import subprocess  # nosec B404
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import yaml


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
        self.timeouts = self.config.get("timeouts", {})

        # Set up experiment directories
        self.prompts_dir = self.experiment_dir / "prompts"
        self.logs_dir = self.experiment_dir / "logs"
        self.implementation_dir = self.experiment_dir / "implementation"

        # Create directories
        self.prompts_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.implementation_dir.mkdir(exist_ok=True)

        # Project info file (shared between creator and workers)
        self.project_info_file = self.experiment_dir / "project_info.json"

    def get_timeout(self, key: str, default: int) -> int:
        """Get timeout value from config or use default."""
        return int(self.timeouts.get(key, default))


class AgentSpawner:
    """Spawns and manages autonomous agents for an experiment."""

    def __init__(self, config: ExperimentConfig, templates_dir: Path):
        """
        Initialize the agent spawner.

        Parameters
        ----------
        config : ExperimentConfig
            Experiment configuration
        templates_dir : Path
            Path to templates directory (in marcus repo)
        """
        self.config = config
        self.templates_dir = templates_dir
        self.agent_prompt_template = templates_dir / "agent_prompt.md"
        self.processes: List[subprocess.Popen[bytes]] = []

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

2. IMMEDIATELY call mcp__marcus__create_project with these EXACT parameters:
   - project_name: "{self.config.project_name}"
   - description: (the full spec below)
   - options: {options_str}

PROJECT SPECIFICATION:
{project_description}

3. As soon as the project is created (DO NOT WAIT for user input):
   - Write project_id and board_id to: {self.config.project_info_file}
   - Format: {{"project_id": "<id>", "board_id": "<board_id>"}}
   - Run: git add -A && git commit -m "Initial commit: Marcus project created"
   - Print: "PROJECT CREATED: project_id=<id> board_id=<board_id>"

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
"provider": "{self.config.project_options.get('provider', 'planka')}"}}
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

    def create_worker_prompt(self, agent: Dict[str, Any]) -> str:
        """
        Create the prompt for a worker agent.

        Parameters
        ----------
        agent : Dict
            Agent configuration from config.yaml

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

        worker_prompt = f"""You are {agent_name} (ID: {agent_id})
in a Marcus multi-agent experiment.

Your role: {agent_role}
Your skills: {", ".join(agent_skills)}
Project root: {self.config.implementation_dir}

STARTUP SEQUENCE:
1. Wait for project_info.json to exist at {self.config.project_info_file}
   (check every 5 seconds, max 60 seconds)

2. Read project_info.json to get project_id and board_id

3. Use mcp__marcus__select_project with the project_id

4. Use mcp__marcus__register_agent to register yourself:
   - agent_id: "{agent_id}"
   - name: "{agent_name}"
   - role: "{agent_role}"
   - skills: {json.dumps(agent_skills)}

5. Register {num_subagents} subagents:
   For i in 1 to {num_subagents}:
   - Use mcp__marcus__register_agent with:
     - agent_id: "{agent_id}_sub{{i}}"
     - name: "{agent_name} Subagent {{i}}"
     - role: "{agent_role}"
     - skills: {json.dumps(agent_skills)}

6. Call mcp__marcus__request_next_task:
   - No parameters needed
   - This will find tasks suitable for your skills
   - If you get "no suitable tasks", wait 30 seconds and try again (max 3 retries)

7. When you get a task:
   - Check dependencies with get_task_context
   - Work on it in: {self.config.implementation_dir}
   - Report progress at 25%, 50%, 75%, 100%
   - Commit to main branch (git add, commit, push)
   - When 100% complete, IMMEDIATELY call request_next_task again

8. Repeat step 7 until NO_TASKS_AVAILABLE or all retries exhausted

---

{base_prompt}

---

CRITICAL REMINDERS:
- Work directory: {self.config.implementation_dir}
- Git branch: main (all agents work together on main)
- After EVERY task completion, IMMEDIATELY request_next_task
- Use get_task_context for tasks with dependencies
- Use log_decision for architectural choices
- Use log_artifact with project_root: {self.config.implementation_dir}
- If "no suitable tasks", wait 30s and try again (max 3 retries)

START NOW!
"""
        return worker_prompt

    def spawn_project_creator(self) -> subprocess.Popen[bytes]:
        """
        Spawn the project creator agent in a new terminal window.

        Returns
        -------
        subprocess.Popen
            Process handle
        """
        print("=" * 60)
        print("Spawning Project Creator Agent")
        print("=" * 60)

        prompt = self.create_project_creator_prompt()
        prompt_file = self.config.prompts_dir / "project_creator.txt"

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Create a script to run in the terminal
        script = f"""#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

cd {self.config.implementation_dir} || exit 1
echo "=========================================="
echo "PROJECT CREATOR AGENT"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Configuring Marcus MCP..."
claude mcp add marcus -t http http://localhost:4298/mcp
echo ""
echo "Creating Marcus project: {self.config.project_name}"
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --dangerously-skip-permissions --print < {prompt_file}
echo ""
echo "=========================================="
echo "Project Creator Complete"
echo "=========================================="
echo ""
echo "Press any key to close this window..."
read -n 1
"""
        script_file = self.config.prompts_dir / "project_creator.sh"
        with open(script_file, "w") as f:
            f.write(script)
        script_file.chmod(0o755)

        # Open in new Terminal window (macOS)
        cmd = [
            "osascript",
            "-e",
            f'tell application "Terminal" to do script "bash {script_file}"',
        ]

        process = subprocess.Popen(  # nosec B603
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        print("✓ Project creator terminal opened")
        print(f"  Prompt: {prompt_file}")
        return process

    def spawn_worker(self, agent: Dict[str, Any]) -> subprocess.Popen[bytes]:
        """
        Spawn a worker agent in a new terminal window.

        Parameters
        ----------
        agent : Dict
            Agent configuration

        Returns
        -------
        subprocess.Popen
            Process handle
        """
        agent_id = agent["id"]
        agent_name = agent["name"]
        agent_role = agent["role"]
        num_subagents = agent.get("subagents", 0)

        print(f"\nSpawning {agent_name} ({agent_id})")
        print("-" * 60)

        prompt = self.create_worker_prompt(agent)
        prompt_file = self.config.prompts_dir / f"{agent_id}.txt"

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Create a script to run in the terminal
        script = f"""#!/bin/bash
# Source shell profile to get nvm/claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

cd {self.config.implementation_dir} || exit 1
echo "=========================================="
echo "{agent_name.upper()}"
echo "ID: {agent_id}"
echo "Role: {agent_role}"
echo "Branch: main (shared)"
echo "Working Directory: $(pwd)"
echo "=========================================="
echo ""
echo "Waiting for project creation..."
while [ ! -f {self.config.project_info_file} ]; do
    sleep 2
done
echo "✓ Project found, starting agent..."
echo ""
# Launch Claude from the implementation directory (cwd matters!)
claude --dangerously-skip-permissions < {prompt_file}
echo ""
echo "=========================================="
echo "{agent_name} - Work Complete"
echo "=========================================="
"""
        script_file = self.config.prompts_dir / f"{agent_id}.sh"
        with open(script_file, "w") as f:
            f.write(script)
        script_file.chmod(0o755)

        # Open in new Terminal window (macOS)
        cmd = [
            "osascript",
            "-e",
            f'tell application "Terminal" to do script "bash {script_file}"',
        ]

        process = subprocess.Popen(  # nosec B603
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        print("  ✓ Terminal window opened")
        print(f"  Prompt: {prompt_file}")
        print(f"  Subagents: {num_subagents}")
        return process

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
        print("=" * 60)

        # Phase 1: Spawn project creator
        print("\n[Phase 1] Creating Project")
        creator_process = self.spawn_project_creator()
        self.processes.append(creator_process)

        # Wait for project creation
        timeout = self.config.get_timeout("project_creation", 300)
        start_time = time.time()

        print("\nWaiting for project creation...")
        while not self.config.project_info_file.exists():
            if time.time() - start_time > timeout:
                print("✗ Project creation timed out!")
                return False

            # Check if creator process failed
            if creator_process.poll() is not None:
                if creator_process.returncode != 0:
                    print("✗ Project creator failed!")
                    return False
                # Process exited successfully, check for file
                if not self.config.project_info_file.exists():
                    time.sleep(2)
                    continue

            time.sleep(5)

        print("✓ Project created!")

        # Read project info
        with open(self.config.project_info_file, "r") as f:
            project_info = json.load(f)
            project_id = project_info.get("project_id")
            board_id = project_info.get("board_id")

        print(f"  Project ID: {project_id}")
        print(f"  Board ID: {board_id}")

        # Phase 2: Spawn worker agents
        print("\n" + "=" * 60)
        num_agents = len(self.config.agents)
        print(f"[Phase 2] Spawning {num_agents} Worker Agents")
        print("=" * 60)

        for agent in self.config.agents:
            worker_process = self.spawn_worker(agent)
            self.processes.append(worker_process)
            time.sleep(2)  # Stagger starts slightly

        print("\n" + "=" * 60)
        print("All Agents Spawned!")
        print("=" * 60)
        print(f"\n✓ {len(self.processes)} terminal windows opened")
        print(f"✓ 1 project creator + {len(self.config.agents)} worker agents")
        print(f"✓ {total_subagents} subagents will be registered by workers")
        print("\n📺 Watch the terminal windows to see agents working!")
        print("\nAgent windows:")
        print("  - Project Creator (will close when done)")
        for agent in self.config.agents:
            print(f"  - {agent['name']} ({agent.get('subagents', 0)} subagents)")
        print(
            "\nAll agents work on the MAIN branch in the same implementation directory."
        )
        print("Marcus coordinates task assignment to prevent conflicts.")
        print(
            "\nPress Ctrl+C when all agents complete to exit "
            "(agent terminals remain open)."
        )

        # Wait for user interrupt
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\n\nExperiment manager shutting down...")
            print("Agent terminal windows will continue running.")
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
