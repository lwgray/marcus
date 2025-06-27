#!/usr/bin/env python3
"""Tests for git worktree setup functionality"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
import subprocess
from unittest.mock import patch, MagicMock, call

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.setup_worktrees import WorktreeManager


class TestWorktreeManager(unittest.TestCase):
    """Test git worktree setup for multiple agents"""
    
    def setUp(self):
        """Create temporary directories for testing"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo = Path(self.temp_dir) / "test-repo"
        self.experiments_dir = Path(self.temp_dir) / "experiments"
        self.experiments_dir.mkdir()
        
        # Initialize a test git repo
        self.test_repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.test_repo, check=True)
        
        # Disable GPG signing for test repo
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=self.test_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_repo, check=True)
        
        # Create initial commit
        (self.test_repo / "README.md").write_text("# Test Repo")
        subprocess.run(["git", "add", "."], cwd=self.test_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.test_repo, check=True)
        
    def tearDown(self):
        """Clean up temporary directories"""
        shutil.rmtree(self.temp_dir)
    
    def test_worktree_manager_initialization(self):
        """Test WorktreeManager can be initialized with repo path"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        self.assertEqual(manager.source_repo, self.test_repo.resolve())
        self.assertEqual(manager.workspace_dir, self.experiments_dir.resolve())
        
    def test_validate_source_repo_exists(self):
        """Test validation fails for non-existent repo"""
        with self.assertRaises(ValueError) as context:
            WorktreeManager(
                source_repo="/path/that/does/not/exist",
                workspace_dir=str(self.experiments_dir)
            )
        
        self.assertIn("does not exist", str(context.exception))
    
    def test_validate_source_repo_is_git(self):
        """Test validation fails for non-git directory"""
        non_git_dir = Path(self.temp_dir) / "not-a-git-repo"
        non_git_dir.mkdir()
        
        with self.assertRaises(ValueError) as context:
            WorktreeManager(
                source_repo=str(non_git_dir),
                workspace_dir=str(self.experiments_dir)
            )
        
        self.assertIn("not a git repository", str(context.exception))
    
    def test_create_single_worktree(self):
        """Test creating a single worktree"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        worktree_path = manager.create_worktree(
            agent_id="agent1",
            branch_name="agent1-work"
        )
        
        # Verify worktree was created
        self.assertTrue(worktree_path.exists())
        self.assertTrue((worktree_path / ".git").exists())
        self.assertTrue((worktree_path / "README.md").exists())
        
        # Verify branch was created
        result = subprocess.run(
            ["git", "branch", "--list", "agent1-work"],
            cwd=self.test_repo,
            capture_output=True,
            text=True
        )
        self.assertIn("agent1-work", result.stdout)
    
    def test_create_multiple_worktrees(self):
        """Test creating worktrees for multiple agents"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        worktrees = manager.setup_agent_worktrees(num_agents=3)
        
        self.assertEqual(len(worktrees), 3)
        
        # Verify each worktree
        for i, (agent_id, worktree_path) in enumerate(worktrees.items(), 1):
            self.assertEqual(agent_id, f"agent{i}")
            self.assertTrue(worktree_path.exists())
            self.assertTrue((worktree_path / ".git").exists())
            
            # Verify branch exists
            result = subprocess.run(
                ["git", "branch", "--list", f"agent{i}-work"],
                cwd=self.test_repo,
                capture_output=True,
                text=True
            )
            self.assertIn(f"agent{i}-work", result.stdout)
    
    def test_cleanup_existing_worktrees(self):
        """Test cleaning up existing worktrees before creating new ones"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        # Create initial worktrees
        manager.setup_agent_worktrees(num_agents=2)
        
        # Create again with cleanup
        worktrees = manager.setup_agent_worktrees(num_agents=2, cleanup_existing=True)
        
        # Should succeed without errors
        self.assertEqual(len(worktrees), 2)
    
    def test_worktree_with_custom_prefix(self):
        """Test creating worktrees with custom prefix"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        worktrees = manager.setup_agent_worktrees(
            num_agents=2,
            agent_prefix="swe-bench-agent"
        )
        
        self.assertIn("swe-bench-agent1", worktrees)
        self.assertIn("swe-bench-agent2", worktrees)
    
    def test_list_existing_worktrees(self):
        """Test listing existing worktrees"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        # Create some worktrees
        manager.setup_agent_worktrees(num_agents=3)
        
        # List them
        existing = manager.list_worktrees()
        
        self.assertEqual(len(existing), 3)
        self.assertIn("agent1", existing)
        self.assertIn("agent2", existing)
        self.assertIn("agent3", existing)
    
    def test_remove_specific_worktree(self):
        """Test removing a specific worktree"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        # Create worktrees
        manager.setup_agent_worktrees(num_agents=2)
        
        # Remove one
        manager.remove_worktree("agent1")
        
        # Verify only one remains
        existing = manager.list_worktrees()
        self.assertEqual(len(existing), 1)
        self.assertIn("agent2", existing)
        self.assertNotIn("agent1", existing)
    
    def test_worktree_info(self):
        """Test getting information about a worktree"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.experiments_dir)
        )
        
        manager.create_worktree("agent1", "agent1-work")
        
        info = manager.get_worktree_info("agent1")
        
        self.assertEqual(info["agent_id"], "agent1")
        self.assertEqual(info["branch"], "agent1-work")
        self.assertTrue(info["path"].exists())
        self.assertEqual(info["status"], "clean")  # No uncommitted changes


if __name__ == "__main__":
    unittest.main()