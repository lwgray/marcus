#!/usr/bin/env python3
"""Launch Claude agents with Marcus MCP integration"""

import os
import json
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ClaudeAgentConfig:
    """Configuration for a Claude agent"""
    agent_id: str
    branch_name: str
    worktree_path: str
    marcus_server_path: str
    
    def __post_init__(self):
        """Convert string paths to Path objects"""
        self.worktree_path = Path(self.worktree_path)
        self.marcus_server_path = Path(self.marcus_server_path)
    
    def generate_mcp_config(self) -> Dict[str, Any]:
        """Generate MCP server configuration for Claude"""
        return {
            "marcus": {
                "command": "python",
                "args": [str(self.marcus_server_path)]
            }
        }
    
    def generate_system_prompt(self, template: str) -> str:
        """Generate system prompt from template"""
        return template.format(
            AGENT_ID=self.agent_id,
            BRANCH_NAME=self.branch_name,
            WORKTREE_PATH=str(self.worktree_path)
        )


class AgentLauncher:
    """Manages launching and monitoring Claude agents"""
    
    def __init__(self, workspace_dir: str, marcus_server_path: str):
        """
        Initialize agent launcher
        
        Args:
            workspace_dir: Directory containing agent worktrees
            marcus_server_path: Path to marcus_mcp_server.py
        """
        self.workspace_dir = Path(workspace_dir)
        self.marcus_server_path = Path(marcus_server_path)
        self.active_agents: Dict[str, subprocess.Popen] = {}
        
        # Validate Marcus server exists
        if not self.marcus_server_path.exists():
            raise ValueError(f"Marcus server not found at: {self.marcus_server_path}")
    
    def launch_agent(
        self,
        agent_id: str,
        branch_name: str,
        worktree_path: str,
        prompt_template: str
    ) -> int:
        """
        Launch a single Claude agent
        
        Args:
            agent_id: Unique identifier for the agent
            branch_name: Git branch name for this agent
            worktree_path: Path to the agent's worktree
            prompt_template: System prompt template or prompt content
            
        Returns:
            Process ID of the launched agent
        """
        config = ClaudeAgentConfig(
            agent_id=agent_id,
            branch_name=branch_name,
            worktree_path=worktree_path,
            marcus_server_path=str(self.marcus_server_path)
        )
        
        # Generate launch command
        cmd = self._generate_launch_command(config, prompt_template)
        
        # Launch the process
        logger.info(f"Launching agent {agent_id} in {worktree_path}")
        
        process = subprocess.Popen(
            cmd,
            cwd=worktree_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Store the process
        self.active_agents[agent_id] = process
        
        # Give it a moment to start
        time.sleep(1)
        
        # Check if it's still running
        if process.poll() is not None:
            # Process terminated immediately
            stdout, stderr = process.communicate()
            logger.error(f"Agent {agent_id} failed to start")
            logger.error(f"stdout: {stdout}")
            logger.error(f"stderr: {stderr}")
            raise RuntimeError(f"Failed to launch agent {agent_id}")
        
        logger.info(f"Agent {agent_id} launched with PID {process.pid}")
        return process.pid
    
    def launch_multiple_agents(
        self,
        worktrees: Dict[str, Path],
        prompt_template: str
    ) -> Dict[str, int]:
        """
        Launch multiple agents
        
        Args:
            worktrees: Dictionary mapping agent IDs to worktree paths
            prompt_template: System prompt template
            
        Returns:
            Dictionary mapping agent IDs to process IDs
        """
        pids = {}
        
        for agent_id, worktree_path in worktrees.items():
            branch_name = f"{agent_id}-work"
            
            try:
                pid = self.launch_agent(
                    agent_id=agent_id,
                    branch_name=branch_name,
                    worktree_path=str(worktree_path),
                    prompt_template=prompt_template
                )
                pids[agent_id] = pid
                
                # Small delay between launches
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to launch {agent_id}: {e}")
                # Clean up any launched agents on failure
                self.terminate_all_agents()
                raise
        
        return pids
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get status of a specific agent
        
        Args:
            agent_id: ID of the agent to check
            
        Returns:
            Dictionary with status information
        """
        if agent_id not in self.active_agents:
            return {"status": "not_found", "agent_id": agent_id}
        
        process = self.active_agents[agent_id]
        poll_result = process.poll()
        
        if poll_result is None:
            # Process is still running
            return {
                "status": "running",
                "agent_id": agent_id,
                "pid": process.pid
            }
        else:
            # Process has terminated
            return {
                "status": "terminated",
                "agent_id": agent_id,
                "pid": process.pid,
                "exit_code": poll_result
            }
    
    def terminate_agent(self, agent_id: str):
        """
        Terminate a specific agent
        
        Args:
            agent_id: ID of the agent to terminate
        """
        if agent_id not in self.active_agents:
            logger.warning(f"Agent {agent_id} not found in active agents")
            return
        
        process = self.active_agents[agent_id]
        
        if process.poll() is None:
            logger.info(f"Terminating agent {agent_id} (PID {process.pid})")
            process.terminate()
            
            # Give it time to terminate gracefully
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Agent {agent_id} did not terminate gracefully, killing")
                process.kill()
                process.wait()
        
        # Remove from active agents
        del self.active_agents[agent_id]
    
    def terminate_all_agents(self):
        """Terminate all active agents"""
        agent_ids = list(self.active_agents.keys())
        
        for agent_id in agent_ids:
            self.terminate_agent(agent_id)
        
        logger.info("All agents terminated")
    
    def _generate_launch_command(
        self,
        config: ClaudeAgentConfig,
        prompt_template: str
    ) -> List[str]:
        """
        Generate the command to launch Claude
        
        Args:
            config: Agent configuration
            prompt_template: System prompt template or content
            
        Returns:
            Command as list of strings
        """
        # First, setup the agent (CLAUDE.md and MCP)
        self._setup_agent(config, prompt_template)
        
        # Use claude -p to send "start work" command
        cmd = [
            "claude", "-p", "start work"
        ]
        
        return cmd
    
    def _setup_agent(self, config: ClaudeAgentConfig, prompt_template: str):
        """Setup CLAUDE.md and MCP for an agent"""
        # Configure MCP server
        server_name = f"marcus_{config.agent_id}"
        
        # Remove existing server if it exists
        subprocess.run(["claude", "mcp", "remove", server_name], 
                      capture_output=True, text=True)
        
        # Add the MCP server
        add_cmd = [
            "claude", "mcp", "add", 
            server_name,
            "--",
            "python", str(config.marcus_server_path)
        ]
        
        try:
            subprocess.run(add_cmd, check=True, capture_output=True, text=True)
            logger.info(f"Added MCP server {server_name}")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to add MCP server: {e.stderr}")
        
        # Load and customize the prompt template
        if os.path.exists(prompt_template):
            with open(prompt_template, 'r') as f:
                prompt_content = f.read()
        else:
            prompt_content = prompt_template
        
        # Replace placeholders
        prompt = prompt_content.format(
            AGENT_ID=config.agent_id,
            BRANCH_NAME=config.branch_name,
            WORKTREE_PATH=str(config.worktree_path)
        )
        
        # Create CLAUDE.md
        claude_md_content = f"""# Agent {config.agent_id} - Autonomous Marcus Agent

When you see "start work", immediately:

1. Connect to Marcus MCP by typing `/mcp` and connecting to `{server_name}`
2. Begin the autonomous workflow described below
3. Work continuously until no more tasks are available

---

{prompt}
"""
        
        claude_md_path = config.worktree_path / "CLAUDE.md"
        claude_md_path.write_text(claude_md_content)
        logger.info(f"Created CLAUDE.md for agent {config.agent_id}")
    
    def load_prompt_template(self, prompt_file: str) -> str:
        """
        Load prompt template from file
        
        Args:
            prompt_file: Path to prompt file
            
        Returns:
            Prompt template content
        """
        with open(prompt_file, 'r') as f:
            return f.read()


def main():
    """Command-line interface for agent launcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Launch Claude agents with Marcus MCP")
    parser.add_argument("--workspace-dir", required=True, help="Directory containing worktrees")
    parser.add_argument("--marcus-server", required=True, help="Path to marcus_mcp_server.py")
    parser.add_argument("--prompt-file", required=True, help="Path to agent prompt template")
    parser.add_argument("--agents", type=int, default=1, help="Number of agents to launch")
    parser.add_argument("--monitor", action="store_true", help="Monitor agent status")
    
    args = parser.parse_args()
    
    launcher = AgentLauncher(args.workspace_dir, args.marcus_server)
    
    # Find worktrees
    worktrees = {}
    workspace_path = Path(args.workspace_dir)
    
    for i in range(1, args.agents + 1):
        agent_id = f"agent{i}"
        worktree_path = workspace_path / agent_id
        
        if not worktree_path.exists():
            logger.error(f"Worktree not found: {worktree_path}")
            logger.error("Run setup_worktrees.py first")
            return 1
        
        worktrees[agent_id] = worktree_path
    
    # Launch agents
    try:
        pids = launcher.launch_multiple_agents(worktrees, args.prompt_file)
        
        print(f"Launched {len(pids)} agents:")
        for agent_id, pid in pids.items():
            print(f"  {agent_id}: PID {pid}")
        
        if args.monitor:
            print("\nMonitoring agents (Ctrl+C to stop)...")
            try:
                while True:
                    time.sleep(5)
                    print("\nAgent Status:")
                    for agent_id in worktrees:
                        status = launcher.get_agent_status(agent_id)
                        print(f"  {agent_id}: {status['status']}")
            except KeyboardInterrupt:
                print("\nStopping monitoring...")
        
    except Exception as e:
        logger.error(f"Failed to launch agents: {e}")
        return 1
    finally:
        # Clean up on exit
        if not args.monitor:
            input("\nPress Enter to terminate all agents...")
        launcher.terminate_all_agents()
    
    return 0


if __name__ == "__main__":
    exit(main())