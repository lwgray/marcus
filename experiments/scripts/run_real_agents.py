#!/usr/bin/env python3
"""
Run real Claude agents with Marcus MCP for experiments
This script orchestrates the complete workflow.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from scripts.setup_worktrees import WorktreeManager
from scripts.launch_agents import AgentLauncher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_real_agent_experiment(
    source_repo: str,
    workspace_dir: str,
    marcus_server_path: str,
    num_agents: int = 5,
    prompt_file: str = None
):
    """
    Run a complete experiment with real Claude agents
    
    Args:
        source_repo: Path to the git repository to work on
        workspace_dir: Directory for agent worktrees
        marcus_server_path: Path to marcus_mcp_server.py
        num_agents: Number of agents to launch
        prompt_file: Path to agent prompt template
    """
    
    # Default prompt if not provided
    if prompt_file is None:
        prompt_file = Path(__file__).parent.parent / "prompts" / "marcus_agent.md"
    
    logger.info("=== Starting Real Agent Experiment ===")
    logger.info(f"Source repo: {source_repo}")
    logger.info(f"Workspace: {workspace_dir}")
    logger.info(f"Agents: {num_agents}")
    
    # Step 1: Setup worktrees
    logger.info("\n1. Setting up git worktrees...")
    worktree_manager = WorktreeManager(source_repo, workspace_dir)
    
    # Clean up any existing worktrees
    worktrees = worktree_manager.setup_agent_worktrees(
        num_agents=num_agents,
        cleanup_existing=True
    )
    
    logger.info(f"Created {len(worktrees)} worktrees")
    
    # Step 2: Launch agents
    logger.info("\n2. Launching Claude agents...")
    launcher = AgentLauncher(workspace_dir, marcus_server_path)
    
    try:
        pids = launcher.launch_multiple_agents(worktrees, str(prompt_file))
        
        logger.info(f"\nLaunched {len(pids)} agents:")
        for agent_id, pid in pids.items():
            logger.info(f"  {agent_id}: PID {pid}")
        
        # Step 3: Monitor
        logger.info("\n3. Monitoring agents (Ctrl+C to stop)...")
        logger.info("Check Marcus UI at http://localhost:8765 for real-time progress")
        
        try:
            while True:
                time.sleep(10)
                
                # Check agent status
                active_count = 0
                for agent_id in worktrees:
                    status = launcher.get_agent_status(agent_id)
                    if status["status"] == "running":
                        active_count += 1
                    elif status["status"] == "terminated":
                        logger.warning(f"Agent {agent_id} has terminated")
                
                if active_count == 0:
                    logger.info("All agents have terminated")
                    break
                
                logger.info(f"Active agents: {active_count}/{num_agents}")
                
        except KeyboardInterrupt:
            logger.info("\nStopping experiment...")
    
    finally:
        # Step 4: Cleanup
        logger.info("\n4. Cleaning up...")
        launcher.terminate_all_agents()
        
        # Optionally keep worktrees for inspection
        keep_worktrees = input("\nKeep worktrees for inspection? (y/N): ").lower() == 'y'
        
        if not keep_worktrees:
            logger.info("Removing worktrees...")
            for agent_id in worktrees:
                worktree_manager.remove_worktree(agent_id)
        
    logger.info("\n=== Experiment Complete ===")


def main():
    parser = argparse.ArgumentParser(
        description="Run real Claude agents with Marcus MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  # Run with a test repository
  python run_real_agents.py \\
    --source-repo /path/to/test-repo \\
    --workspace /tmp/agent-workspace \\
    --marcus-server /path/to/marcus/marcus_mcp_server.py \\
    --agents 3

  # Use custom prompt
  python run_real_agents.py \\
    --source-repo /path/to/test-repo \\
    --workspace /tmp/agent-workspace \\
    --marcus-server /path/to/marcus/marcus_mcp_server.py \\
    --prompt my_custom_prompt.md
"""
    )
    
    parser.add_argument(
        "--source-repo", 
        required=True,
        help="Path to source git repository"
    )
    parser.add_argument(
        "--workspace", 
        required=True,
        help="Directory for agent worktrees (will be created)"
    )
    parser.add_argument(
        "--marcus-server", 
        required=True,
        help="Path to marcus_mcp_server.py"
    )
    parser.add_argument(
        "--agents", 
        type=int, 
        default=5,
        help="Number of agents to launch (default: 5)"
    )
    parser.add_argument(
        "--prompt",
        help="Path to agent prompt template (default: marcus_agent.md)"
    )
    
    args = parser.parse_args()
    
    # Validate paths
    source_repo = Path(args.source_repo)
    if not source_repo.exists():
        logger.error(f"Source repository not found: {source_repo}")
        return 1
    
    marcus_server = Path(args.marcus_server)
    if not marcus_server.exists():
        logger.error(f"Marcus server not found: {marcus_server}")
        return 1
    
    # Run experiment
    try:
        run_real_agent_experiment(
            source_repo=str(source_repo),
            workspace_dir=args.workspace,
            marcus_server_path=str(marcus_server),
            num_agents=args.agents,
            prompt_file=args.prompt
        )
        return 0
    
    except Exception as e:
        logger.error(f"Experiment failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())