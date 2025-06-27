#!/usr/bin/env python3
"""Setup and manage git worktrees for multiple agents"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorktreeManager:
    """Manages git worktrees for multiple agents"""
    
    def __init__(self, source_repo: str, workspace_dir: str):
        """
        Initialize worktree manager
        
        Args:
            source_repo: Path to the source git repository
            workspace_dir: Directory where worktrees will be created
        """
        self.source_repo = Path(source_repo).resolve()
        self.workspace_dir = Path(workspace_dir).resolve()
        
        # Validate source repo
        if not self.source_repo.exists():
            raise ValueError(f"Source repository does not exist: {self.source_repo}")
        
        if not (self.source_repo / ".git").exists():
            raise ValueError(f"Source path is not a git repository: {self.source_repo}")
        
        # Ensure workspace directory exists
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def create_worktree(self, agent_id: str, branch_name: str) -> Path:
        """
        Create a single worktree for an agent
        
        Args:
            agent_id: Unique identifier for the agent
            branch_name: Git branch name for this agent
            
        Returns:
            Path to the created worktree
        """
        worktree_path = self.workspace_dir / agent_id
        
        # Remove existing worktree if it exists
        if worktree_path.exists():
            self.remove_worktree(agent_id)
        
        # Create the worktree
        logger.info(f"Creating worktree for {agent_id} at {worktree_path}")
        
        try:
            subprocess.run(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_path)],
                cwd=self.source_repo,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create worktree: {e.stderr}")
            raise
        
        return worktree_path
    
    def setup_agent_worktrees(
        self, 
        num_agents: int,
        agent_prefix: str = "agent",
        cleanup_existing: bool = False
    ) -> Dict[str, Path]:
        """
        Setup worktrees for multiple agents
        
        Args:
            num_agents: Number of agents to create worktrees for
            agent_prefix: Prefix for agent IDs
            cleanup_existing: Whether to remove existing worktrees first
            
        Returns:
            Dictionary mapping agent IDs to worktree paths
        """
        if cleanup_existing:
            self._cleanup_all_worktrees()
        
        worktrees = {}
        
        for i in range(1, num_agents + 1):
            agent_id = f"{agent_prefix}{i}"
            branch_name = f"{agent_id}-work"
            
            worktree_path = self.create_worktree(agent_id, branch_name)
            worktrees[agent_id] = worktree_path
        
        logger.info(f"Created {len(worktrees)} worktrees")
        return worktrees
    
    def list_worktrees(self) -> Dict[str, Path]:
        """
        List all worktrees managed by this manager
        
        Returns:
            Dictionary mapping agent IDs to worktree paths
        """
        worktrees = {}
        
        # List all worktrees from git
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.source_repo,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        lines = result.stdout.strip().split('\n')
        current_path = None
        
        for line in lines:
            if line.startswith("worktree "):
                current_path = Path(line.split(" ", 1)[1])
                # Check if this worktree is in our workspace
                if self.workspace_dir in current_path.parents:
                    agent_id = current_path.name
                    worktrees[agent_id] = current_path
        
        return worktrees
    
    def remove_worktree(self, agent_id: str):
        """
        Remove a specific worktree
        
        Args:
            agent_id: ID of the agent whose worktree to remove
        """
        worktree_path = self.workspace_dir / agent_id
        
        if worktree_path.exists():
            logger.info(f"Removing worktree for {agent_id}")
            
            # Remove the worktree
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.source_repo,
                capture_output=True,
                text=True
            )
            
            # Clean up the branch
            branch_name = f"{agent_id}-work"
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=self.source_repo,
                capture_output=True,
                text=True
            )
    
    def get_worktree_info(self, agent_id: str) -> Dict[str, any]:
        """
        Get information about a specific worktree
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Dictionary with worktree information
        """
        worktree_path = self.workspace_dir / agent_id
        
        if not worktree_path.exists():
            raise ValueError(f"Worktree for {agent_id} does not exist")
        
        # Get branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        
        # Check if working directory is clean
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True
        )
        status = "clean" if not result.stdout.strip() else "dirty"
        
        return {
            "agent_id": agent_id,
            "branch": branch,
            "path": worktree_path,
            "status": status
        }
    
    def _cleanup_all_worktrees(self):
        """Remove all worktrees in the workspace directory"""
        existing = self.list_worktrees()
        for agent_id in existing:
            self.remove_worktree(agent_id)


def main():
    """Command-line interface for worktree setup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup git worktrees for multiple agents")
    parser.add_argument("--source-repo", required=True, help="Path to source git repository")
    parser.add_argument("--workspace-dir", required=True, help="Directory for agent worktrees")
    parser.add_argument("--num-agents", type=int, default=5, help="Number of agents")
    parser.add_argument("--prefix", default="agent", help="Agent ID prefix")
    parser.add_argument("--cleanup", action="store_true", help="Clean up existing worktrees first")
    parser.add_argument("--list", action="store_true", help="List existing worktrees")
    
    args = parser.parse_args()
    
    manager = WorktreeManager(args.source_repo, args.workspace_dir)
    
    if args.list:
        worktrees = manager.list_worktrees()
        if worktrees:
            print("Existing worktrees:")
            for agent_id, path in worktrees.items():
                print(f"  {agent_id}: {path}")
        else:
            print("No worktrees found")
    else:
        worktrees = manager.setup_agent_worktrees(
            num_agents=args.num_agents,
            agent_prefix=args.prefix,
            cleanup_existing=args.cleanup
        )
        
        print(f"Created {len(worktrees)} worktrees:")
        for agent_id, path in worktrees.items():
            print(f"  {agent_id}: {path}")


if __name__ == "__main__":
    main()