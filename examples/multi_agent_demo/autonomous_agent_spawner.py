#!/usr/bin/env python3
"""
Autonomous Multi-Agent Spawner for Marcus Demo

Spawns 5 processes:
- Process 1: Creates the Marcus project
- Processes 2-5: Four worker agents, each with 5 subagents (20 total)

Each agent runs Claude Code with --dangerously-skip-permissions and follows
the Agent_prompt.md workflow autonomously.
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class AgentConfig:
    """Configuration for an autonomous agent."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        skills: List[str],
        num_subagents: int = 5,
    ):
        """
        Initialize agent configuration.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier
        name : str
            Human-readable agent name
        role : str
            Agent role (backend, frontend, devops, etc.)
        skills : List[str]
            List of skills this agent has
        num_subagents : int
            Number of subagents to register
        """
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.skills = skills
        self.num_subagents = num_subagents


class AutonomousAgentSpawner:
    """Spawns and manages autonomous agents for the demo."""

    def __init__(self, demo_root: Path, project_root: Path):
        """
        Initialize the spawner.

        Parameters
        ----------
        demo_root : Path
            Root directory of the demo
        project_root : Path
            Root directory where the implementation will be created
        """
        self.demo_root = demo_root
        self.project_root = project_root
        self.project_spec_path = demo_root / "PROJECT_SPEC.md"
        self.agent_prompt_path = Path(
            "/Users/lwgray/dev/marcus/prompts/Agent_prompt.md"
        )

        # Agent configurations
        self.agents = [
            AgentConfig(
                agent_id="agent_foundation",
                name="Foundation Agent",
                role="backend",
                skills=[
                    "python",
                    "sqlalchemy",
                    "postgresql",
                    "alembic",
                    "database-design",
                ],
                num_subagents=5,
            ),
            AgentConfig(
                agent_id="agent_auth",
                name="Authentication Agent",
                role="backend",
                skills=["python", "fastapi", "jwt", "security", "bcrypt", "testing"],
                num_subagents=5,
            ),
            AgentConfig(
                agent_id="agent_api",
                name="API Development Agent",
                role="backend",
                skills=["python", "fastapi", "rest-api", "pydantic", "testing"],
                num_subagents=5,
            ),
            AgentConfig(
                agent_id="agent_integration",
                name="Integration & QA Agent",
                role="qa",
                skills=[
                    "python",
                    "pytest",
                    "integration-testing",
                    "api-testing",
                    "validation",
                ],
                num_subagents=5,
            ),
        ]

        self.project_id: Optional[str] = None
        self.board_id: Optional[str] = None
        self.processes: List[subprocess.Popen] = []

    def create_project_creator_prompt(self) -> str:
        """
        Create the prompt for the project creator agent.

        Returns
        -------
        str
            Prompt for project creation
        """
        with open(self.project_spec_path, "r") as f:
            project_description = f.read()

        prompt = f"""You are the Project Creator Agent for the Marcus Multi-Agent Demo.

Your ONLY task is to:

1. Use the mcp__marcus__create_project tool to create a new project called "Task Management API Demo"
2. Use this exact description:

{project_description}

3. Use these options: {{"complexity": "standard", "provider": "planka", "mode": "new_project"}}

4. When the project is created successfully:
   - Save the project_id and board_id to {self.demo_root / "project_info.json"}
   - Print "PROJECT CREATED: project_id=<id> board_id=<board_id>"
   - Exit immediately

5. If creation fails, print the error and exit with code 1

DO NOT do anything else. Just create the project and exit.
"""
        return prompt

    def create_worker_prompt(self, agent: AgentConfig, branch_name: str) -> str:
        """
        Create the prompt for a worker agent.

        Parameters
        ----------
        agent : AgentConfig
            Agent configuration
        branch_name : str
            Git branch name for this agent

        Returns
        -------
        str
            Prompt for worker agent
        """
        # Read the base agent prompt
        with open(self.agent_prompt_path, "r") as f:
            base_prompt = f.read()

        # Replace placeholder
        base_prompt = base_prompt.replace("{BRANCH_NAME}", branch_name)

        # Add agent-specific instructions
        worker_prompt = f"""You are {agent.name} (ID: {agent.agent_id}) in the Marcus Multi-Agent Demo.

Your role: {agent.role}
Your skills: {", ".join(agent.skills)}
Your git branch: {branch_name}
Project root: {self.project_root}

STARTUP SEQUENCE:
1. Wait for project_info.json to exist at {self.demo_root / "project_info.json"} (check every 5 seconds)
2. Read project_info.json to get project_id and board_id
3. Use mcp__marcus__select_project with the project_id
4. Use mcp__marcus__register_agent to register yourself:
   - agent_id: "{agent.agent_id}"
   - name: "{agent.name}"
   - role: "{agent.role}"
   - skills: {json.dumps(agent.skills)}

5. Register {agent.num_subagents} subagents:
   For i in 1 to {agent.num_subagents}:
   - Use mcp__marcus__register_agent with agent_id: "{agent.agent_id}_sub{{i}}"
   - name: "{agent.name} Subagent {{i}}"
   - role: "{agent.role}"
   - skills: {json.dumps(agent.skills)}

6. Use mcp__marcus__start_experiment to start tracking:
   - experiment_name: "marcus_multi_agent_demo"
   - run_name: "task_api_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
   - project_id: <from project_info.json>
   - board_id: <from project_info.json>
   - tags: {{"agent_id": "{agent.agent_id}", "role": "{agent.role}"}}
   - params: {{"num_subagents": {agent.num_subagents}}}

7. Enter the continuous work loop following the workflow below:

---

{base_prompt}

---

REMEMBER:
- Work in {self.project_root}
- All code goes in the implementation/ directory
- Commit to branch: {branch_name}
- NEVER STOP - always request the next task after completing one
- Use get_task_context for tasks with dependencies
- Use log_decision for architectural choices
- Use log_artifact to share specifications/docs with other agents
- project_root parameter for log_artifact MUST be: {self.project_root}

START NOW!
"""
        return worker_prompt

    def spawn_project_creator(self) -> subprocess.Popen:
        """
        Spawn the project creator agent.

        Returns
        -------
        subprocess.Popen
            Process handle
        """
        print("=" * 60)
        print("Spawning Project Creator Agent")
        print("=" * 60)

        prompt = self.create_project_creator_prompt()
        prompt_file = self.demo_root / "prompts" / "project_creator.txt"
        prompt_file.parent.mkdir(exist_ok=True)

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Spawn Claude Code with the prompt (using stdin)
        cmd = ["claude", "--dangerously-skip-permissions", "--print"]

        log_file = self.demo_root / "logs" / "project_creator.log"
        log_file.parent.mkdir(exist_ok=True)

        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd,
                cwd=self.demo_root,
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True
            )
            # Send the prompt to stdin
            process.stdin.write(prompt)
            process.stdin.close()

        print(f"✓ Project creator spawned (PID: {process.pid})")
        print(f"  Log: {log_file}")
        return process

    def spawn_worker(self, agent: AgentConfig) -> subprocess.Popen:
        """
        Spawn a worker agent.

        Parameters
        ----------
        agent : AgentConfig
            Agent configuration

        Returns
        -------
        subprocess.Popen
            Process handle
        """
        print(f"\nSpawning {agent.name} ({agent.agent_id})")
        print("-" * 60)

        branch_name = f"agent/{agent.agent_id}"
        prompt = self.create_worker_prompt(agent, branch_name)

        prompt_file = self.demo_root / "prompts" / f"{agent.agent_id}.txt"
        prompt_file.parent.mkdir(exist_ok=True)

        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Spawn Claude Code with prompt as argument
        cmd = ["claude", "--dangerously-skip-permissions", prompt]

        log_file = self.demo_root / "logs" / f"{agent.agent_id}.log"
        log_file.parent.mkdir(exist_ok=True)

        with open(log_file, "w") as log:
            process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )

        print(f"  ✓ Spawned (PID: {process.pid})")
        print(f"  Log: {log_file}")
        print(f"  Branch: {branch_name}")
        print(f"  Subagents: {agent.num_subagents}")
        return process

    async def run(self):
        """Run the autonomous multi-agent demo."""
        print("\n" + "=" * 60)
        print("Marcus Autonomous Multi-Agent Demo")
        print("=" * 60)
        print(f"Demo root: {self.demo_root}")
        print(f"Project root: {self.project_root}")
        print(f"Total agents: 4 (+ 20 subagents)")
        print("=" * 60)

        # Phase 1: Spawn project creator
        print("\n[Phase 1] Creating Project")
        creator_process = self.spawn_project_creator()
        self.processes.append(creator_process)

        # Wait for project creation (check for project_info.json)
        project_info_file = self.demo_root / "project_info.json"
        timeout = 300  # 5 minutes
        start_time = time.time()

        print("\nWaiting for project creation...")
        while not project_info_file.exists():
            if time.time() - start_time > timeout:
                print("✗ Project creation timed out!")
                self.cleanup()
                sys.exit(1)

            # Check if creator process failed
            if creator_process.poll() is not None:
                if creator_process.returncode != 0:
                    print("✗ Project creator failed!")
                    self.cleanup()
                    sys.exit(1)
                # Process exited successfully, check for file
                if not project_info_file.exists():
                    time.sleep(2)
                    continue

            time.sleep(5)

        print("✓ Project created!")

        # Read project info
        with open(project_info_file, "r") as f:
            project_info = json.load(f)
            self.project_id = project_info.get("project_id")
            self.board_id = project_info.get("board_id")

        print(f"  Project ID: {self.project_id}")
        print(f"  Board ID: {self.board_id}")

        # Phase 2: Spawn worker agents
        print("\n" + "=" * 60)
        print(f"[Phase 2] Spawning {len(self.agents)} Worker Agents")
        print("=" * 60)

        for agent in self.agents:
            worker_process = self.spawn_worker(agent)
            self.processes.append(worker_process)
            time.sleep(2)  # Stagger starts slightly

        print("\n" + "=" * 60)
        print("All Agents Spawned!")
        print("=" * 60)
        print(f"\n✓ {len(self.processes)} processes running")
        print(f"✓ 20 subagents will be registered by workers")
        print(f"✓ Logs in: {self.demo_root / 'logs'}")
        print("\nMonitoring agents (Ctrl+C to stop)...")

        # Monitor processes
        try:
            while True:
                time.sleep(30)

                # Check process status
                running = sum(1 for p in self.processes if p.poll() is None)
                print(
                    f"\n[{datetime.now().strftime('%H:%M:%S')}] Status: {running}/{len(self.processes)} processes running"
                )

                # If all workers are done (creator can exit)
                worker_processes = self.processes[1:]  # Skip creator
                if all(p.poll() is not None for p in worker_processes):
                    print("\n✓ All worker agents completed!")
                    break

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.cleanup()

    def cleanup(self):
        """Clean up spawned processes."""
        print("\nCleaning up processes...")
        for process in self.processes:
            if process.poll() is None:
                print(f"  Terminating PID {process.pid}...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print(f"  Force killing PID {process.pid}...")
                    process.kill()

        print("✓ Cleanup complete")


async def main():
    """Main entry point."""
    demo_root = Path(__file__).parent
    project_root = demo_root / "implementation"
    project_root.mkdir(exist_ok=True)

    spawner = AutonomousAgentSpawner(demo_root, project_root)
    await spawner.run()


if __name__ == "__main__":
    asyncio.run(main())
