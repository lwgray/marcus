#!/usr/bin/env python3
"""
Agent Runner - Executes an autonomous agent in a continuous loop

This script simulates an autonomous agent by repeatedly calling Claude Code
with prompts, implementing the continuous work loop required by Agent_prompt.md
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class AgentRunner:
    """Runs a single agent in autonomous mode."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        skills: list,
        num_subagents: int,
        project_root: Path,
        demo_root: Path,
        branch_name: str,
    ):
        """
        Initialize agent runner.

        Parameters
        ----------
        agent_id : str
            Unique agent identifier
        name : str
            Agent name
        role : str
            Agent role
        skills : list
            List of agent skills
        num_subagents : int
            Number of subagents to register
        project_root : Path
            Root directory for implementation
        demo_root : Path
            Demo root directory
        branch_name : str
            Git branch for this agent
        """
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.skills = skills
        self.num_subagents = num_subagents
        self.project_root = project_root
        self.demo_root = demo_root
        self.branch_name = branch_name

        self.project_id: Optional[str] = None
        self.board_id: Optional[str] = None
        self.iteration = 0
        self.max_iterations = 100  # Safety limit

    def wait_for_project(self) -> bool:
        """
        Wait for project_info.json to be created.

        Returns
        -------
        bool
            True if project info found, False if timeout
        """
        project_info_file = self.demo_root / "project_info.json"
        timeout = 300  # 5 minutes
        start_time = time.time()

        print(f"[{self.agent_id}] Waiting for project creation...")

        while not project_info_file.exists():
            if time.time() - start_time > timeout:
                print(f"[{self.agent_id}] ✗ Timeout waiting for project")
                return False
            time.sleep(5)

        # Read project info
        with open(project_info_file, "r") as f:
            project_info = json.load(f)
            self.project_id = project_info.get("project_id")
            self.board_id = project_info.get("board_id")

        print(f"[{self.agent_id}] ✓ Project found: {self.project_id}")
        return True

    def create_startup_prompt(self) -> str:
        """
        Create the initial startup prompt for the agent.

        Returns
        -------
        str
            Startup prompt
        """
        prompt = f"""You are {self.name} (ID: {self.agent_id}) - an autonomous agent in the Marcus Multi-Agent Demo.

Your role: {self.role}
Your skills: {", ".join(self.skills)}
Your git branch: {self.branch_name}
Project root: {self.project_root}
Project ID: {self.project_id}
Board ID: {self.board_id}

STARTUP SEQUENCE (execute these steps NOW):

1. Use mcp__marcus__select_project with project_id: "{self.project_id}"

2. Use mcp__marcus__register_agent to register yourself:
   - agent_id: "{self.agent_id}"
   - name: "{self.name}"
   - role: "{self.role}"
   - skills: {json.dumps(self.skills)}

3. Register {self.num_subagents} subagents by calling mcp__marcus__register_agent {self.num_subagents} times:
   - For i in 1 to {self.num_subagents}: agent_id: "{self.agent_id}_sub{{i}}", name: "{self.name} Subagent {{i}}"

4. Call mcp__marcus__request_next_task to get your first task

5. If you get a task:
   - Use get_task_context if task has dependencies
   - Start working on it
   - Report when you reach 25% progress
   - When complete, IMMEDIATELY request the next task

6. If no task available:
   - Print "NO_TASKS_AVAILABLE"
   - Exit

IMPORTANT:
- Work in: {self.project_root}
- Commit to branch: {self.branch_name}
- Use log_artifact with project_root: {self.project_root}
- Follow Agent_prompt.md workflow for continuous operation

BEGIN NOW!
"""
        return prompt

    def create_continuation_prompt(self, previous_output: str) -> str:
        """
        Create a continuation prompt after a response.

        Parameters
        ----------
        previous_output : str
            Output from previous Claude execution

        Returns
        -------
        str
            Continuation prompt
        """
        # Check if agent reported completion
        if "completed" in previous_output.lower() or "100%" in previous_output:
            return f"""Task complete!

Now IMMEDIATELY call mcp__marcus__request_next_task to get the next task.

If you get a task:
- Use get_task_context if it has dependencies
- Start working on it
- Report progress at 25%, 50%, 75%
- When complete, request next task again

If no task available:
- Print "NO_TASKS_AVAILABLE"

Project root: {self.project_root}
Branch: {self.branch_name}

CONTINUE NOW!
"""

        # Agent is still working on current task
        return f"""Continue working on your current task.

Remember to:
- Report progress at milestones (25%, 50%, 75%, 100%)
- Use get_task_context for dependencies
- Use log_decision when making architectural choices
- Use log_artifact to share specs with other agents (project_root: {self.project_root})
- Commit code with task IDs to branch: {self.branch_name}

CONTINUE NOW!
"""

    def run_claude(self, prompt: str) -> tuple[str, int]:
        """
        Run Claude Code with a prompt.

        Parameters
        ----------
        prompt : str
            Prompt to send to Claude

        Returns
        -------
        tuple[str, int]
            Output from Claude and return code
        """
        cmd = ["claude", "--dangerously-skip-permissions", "--print"]

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per iteration
                cwd=self.project_root,
            )
            return result.stdout, result.returncode

        except subprocess.TimeoutExpired:
            return "TIMEOUT", 1
        except Exception as e:
            return f"ERROR: {e}", 1

    def run(self) -> None:
        """Run the agent in autonomous mode."""
        print(f"\n{'='*60}")
        print(f"{self.name} Starting")
        print(f"{'='*60}")

        # Wait for project
        if not self.wait_for_project():
            sys.exit(1)

        # Startup
        print(f"[{self.agent_id}] Iteration 1: Startup & Registration")
        startup_prompt = self.create_startup_prompt()
        output, returncode = self.run_claude(startup_prompt)

        print(f"[{self.agent_id}] Startup output:\n{output[:500]}...")

        if returncode != 0:
            print(f"[{self.agent_id}] ✗ Startup failed")
            sys.exit(1)

        # Check if registered successfully
        if "NO_TASKS_AVAILABLE" in output:
            print(f"[{self.agent_id}] ✓ Registered but no tasks available yet")
            return

        # Continuous work loop
        self.iteration = 1
        while self.iteration < self.max_iterations:
            self.iteration += 1
            time.sleep(5)  # Brief pause between iterations

            print(f"\n[{self.agent_id}] Iteration {self.iteration}")

            continuation_prompt = self.create_continuation_prompt(output)
            output, returncode = self.run_claude(continuation_prompt)

            # Log output
            print(f"[{self.agent_id}] Output:\n{output[:300]}...")

            # Check for completion signals
            if "NO_TASKS_AVAILABLE" in output:
                print(f"[{self.agent_id}] ✓ All tasks complete!")
                break

            if "ERROR" in output or returncode != 0:
                print(f"[{self.agent_id}] ⚠️  Error encountered, retrying...")
                time.sleep(10)
                continue

        print(f"\n[{self.agent_id}] Agent runner stopped after {self.iteration} iterations")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run an autonomous agent")
    parser.add_argument("--agent-id", required=True, help="Agent ID")
    parser.add_argument("--name", required=True, help="Agent name")
    parser.add_argument("--role", required=True, help="Agent role")
    parser.add_argument("--skills", required=True, help="Comma-separated skills")
    parser.add_argument(
        "--num-subagents", type=int, default=5, help="Number of subagents"
    )
    parser.add_argument("--project-root", required=True, help="Project root directory")
    parser.add_argument("--demo-root", required=True, help="Demo root directory")
    parser.add_argument("--branch", required=True, help="Git branch name")

    args = parser.parse_args()

    runner = AgentRunner(
        agent_id=args.agent_id,
        name=args.name,
        role=args.role,
        skills=args.skills.split(","),
        num_subagents=args.num_subagents,
        project_root=Path(args.project_root),
        demo_root=Path(args.demo_root),
        branch_name=args.branch,
    )

    runner.run()


if __name__ == "__main__":
    main()
