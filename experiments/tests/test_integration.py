#!/usr/bin/env python3
"""Integration tests for the complete real agent system"""

import os
import tempfile
import unittest
from pathlib import Path
import subprocess
import shutil
from unittest.mock import patch, MagicMock

import sys
sys.path.append(str(Path(__file__).parent.parent))

from scripts.setup_worktrees import WorktreeManager
from scripts.launch_agents import AgentLauncher, ClaudeAgentConfig


class TestRealAgentIntegration(unittest.TestCase):
    """Test the integration of all components"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo = Path(self.temp_dir) / "test-repo"
        self.workspace = Path(self.temp_dir) / "workspace"
        self.marcus_path = Path(self.temp_dir) / "marcus_mcp_server.py"
        
        # Create test repo
        self.test_repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.test_repo, check=True)
        subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=self.test_repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.test_repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.test_repo, check=True)
        
        (self.test_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=self.test_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.test_repo, check=True)
        
        # Create fake marcus server
        self.marcus_path.write_text("#!/usr/bin/env python3\nprint('Fake Marcus')")
        
    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir)
    
    def test_complete_workflow(self):
        """Test the complete workflow from worktree setup to agent launch"""
        # Step 1: Setup worktrees
        worktree_manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.workspace)
        )
        
        worktrees = worktree_manager.setup_agent_worktrees(num_agents=2)
        
        # Verify worktrees created
        self.assertEqual(len(worktrees), 2)
        self.assertTrue((self.workspace / "agent1").exists())
        self.assertTrue((self.workspace / "agent2").exists())
        
        # Step 2: Prepare to launch agents
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Verify launcher initialized
        self.assertEqual(launcher.workspace_dir, self.workspace)
        self.assertEqual(launcher.marcus_server_path, self.marcus_path)
        
        # Step 3: Verify prompt templating
        config = ClaudeAgentConfig(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path=str(self.workspace / "agent1"),
            marcus_server_path=str(self.marcus_path)
        )
        
        prompt = config.generate_system_prompt(
            "You are {AGENT_ID} on branch {BRANCH_NAME}"
        )
        
        self.assertEqual(prompt, "You are agent1 on branch agent1-work")
        
        # Step 4: Verify MCP config generation
        mcp_config = config.generate_mcp_config()
        
        self.assertIn("marcus", mcp_config)
        self.assertEqual(mcp_config["marcus"]["command"], "python")
        self.assertEqual(Path(mcp_config["marcus"]["args"][0]), self.marcus_path)
    
    def test_worktree_isolation(self):
        """Test that agents work in isolated worktrees"""
        manager = WorktreeManager(
            source_repo=str(self.test_repo),
            workspace_dir=str(self.workspace)
        )
        
        # Create worktrees
        worktrees = manager.setup_agent_worktrees(num_agents=2)
        
        # Make different changes in each worktree
        (worktrees["agent1"] / "agent1.txt").write_text("Agent 1 was here")
        (worktrees["agent2"] / "agent2.txt").write_text("Agent 2 was here")
        
        # Verify isolation - files don't appear in other worktrees
        self.assertTrue((worktrees["agent1"] / "agent1.txt").exists())
        self.assertFalse((worktrees["agent1"] / "agent2.txt").exists())
        
        self.assertTrue((worktrees["agent2"] / "agent2.txt").exists())
        self.assertFalse((worktrees["agent2"] / "agent1.txt").exists())
        
        # Verify different branches
        result1 = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktrees["agent1"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result1.stdout.strip(), "agent1-work")
        
        result2 = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktrees["agent2"],
            capture_output=True,
            text=True
        )
        self.assertEqual(result2.stdout.strip(), "agent2-work")
    
    @patch('subprocess.Popen')
    def test_launch_command_structure(self, mock_popen):
        """Test the structure of the Claude launch command"""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Create worktree
        (self.workspace / "agent1").mkdir(parents=True)
        
        # Launch agent
        launcher.launch_agent(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path=str(self.workspace / "agent1"),
            prompt_template="Test prompt for {AGENT_ID}"
        )
        
        # Verify command structure
        call_args = mock_popen.call_args[0][0]
        
        # Should be: claude --mcp-servers {json} --system-prompt "..."
        self.assertEqual(call_args[0], "claude")
        self.assertEqual(call_args[1], "--mcp-servers")
        self.assertEqual(call_args[3], "--system-prompt")
        self.assertIn("Test prompt for agent1", call_args[4])
    
    def test_prompt_file_loading(self):
        """Test loading prompt from file"""
        prompt_file = self.workspace / "test_prompt.md"
        prompt_file.parent.mkdir(exist_ok=True)
        prompt_file.write_text("Agent {AGENT_ID} ready to work!")
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace),
            marcus_server_path=str(self.marcus_path)
        )
        
        prompt_content = launcher.load_prompt_template(str(prompt_file))
        self.assertEqual(prompt_content, "Agent {AGENT_ID} ready to work!")


if __name__ == "__main__":
    unittest.main()