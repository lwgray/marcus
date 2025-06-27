#!/usr/bin/env python3
"""Tests for Claude agent launcher functionality"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call, mock_open
import subprocess

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.launch_agents import AgentLauncher, ClaudeAgentConfig


class TestClaudeAgentConfig(unittest.TestCase):
    """Test Claude agent configuration"""
    
    def test_agent_config_creation(self):
        """Test creating agent configuration"""
        config = ClaudeAgentConfig(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path="/path/to/worktree",
            marcus_server_path="/path/to/marcus_mcp_server.py"
        )
        
        self.assertEqual(config.agent_id, "agent1")
        self.assertEqual(config.branch_name, "agent1-work")
        self.assertEqual(config.worktree_path, Path("/path/to/worktree"))
        self.assertEqual(config.marcus_server_path, Path("/path/to/marcus_mcp_server.py"))
    
    def test_generate_mcp_config(self):
        """Test generating MCP server configuration"""
        config = ClaudeAgentConfig(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path="/path/to/worktree",
            marcus_server_path="/path/to/marcus_mcp_server.py"
        )
        
        mcp_config = config.generate_mcp_config()
        
        self.assertIn("marcus", mcp_config)
        self.assertEqual(mcp_config["marcus"]["command"], "python")
        self.assertEqual(mcp_config["marcus"]["args"], ["/path/to/marcus_mcp_server.py"])
    
    def test_generate_system_prompt(self):
        """Test generating system prompt for agent"""
        config = ClaudeAgentConfig(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path="/path/to/worktree",
            marcus_server_path="/path/to/marcus_mcp_server.py"
        )
        
        prompt_template = """You are {AGENT_ID} working on branch {BRANCH_NAME}."""
        prompt = config.generate_system_prompt(prompt_template)
        
        self.assertEqual(prompt, "You are agent1 working on branch agent1-work.")


class TestAgentLauncher(unittest.TestCase):
    """Test agent launcher functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_dir = Path(self.temp_dir) / "workspace"
        self.workspace_dir.mkdir()
        self.marcus_path = Path(self.temp_dir) / "marcus_mcp_server.py"
        self.marcus_path.touch()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_launcher_initialization(self):
        """Test AgentLauncher initialization"""
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        self.assertEqual(launcher.workspace_dir, self.workspace_dir)
        self.assertEqual(launcher.marcus_server_path, self.marcus_path)
        self.assertEqual(launcher.active_agents, {})
    
    def test_validate_marcus_server_exists(self):
        """Test validation fails for missing Marcus server"""
        with self.assertRaises(ValueError) as context:
            AgentLauncher(
                workspace_dir=str(self.workspace_dir),
                marcus_server_path="/path/that/does/not/exist.py"
            )
        
        self.assertIn("Marcus server not found", str(context.exception))
    
    @patch('subprocess.Popen')
    def test_launch_single_agent(self, mock_popen):
        """Test launching a single Claude agent"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Create worktree directory
        worktree_path = self.workspace_dir / "agent1"
        worktree_path.mkdir()
        
        # Launch agent
        pid = launcher.launch_agent(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path=str(worktree_path),
            prompt_template="Test prompt"
        )
        
        # Verify process was launched
        self.assertEqual(pid, 12345)
        self.assertIn("agent1", launcher.active_agents)
        
        # Verify command was constructed correctly
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        
        # Should launch claude with proper arguments
        self.assertIn("claude", call_args[0])
        self.assertIn("--mcp-servers", call_args)
    
    @patch('subprocess.Popen')
    def test_launch_multiple_agents(self, mock_popen):
        """Test launching multiple agents"""
        # Set up mock processes
        mock_processes = []
        for i in range(3):
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345 + i
            mock_processes.append(mock_process)
        
        mock_popen.side_effect = mock_processes
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Create worktrees
        worktrees = {}
        for i in range(1, 4):
            worktree_path = self.workspace_dir / f"agent{i}"
            worktree_path.mkdir()
            worktrees[f"agent{i}"] = worktree_path
        
        # Launch agents
        pids = launcher.launch_multiple_agents(
            worktrees=worktrees,
            prompt_template="Test prompt"
        )
        
        # Verify all agents launched
        self.assertEqual(len(pids), 3)
        self.assertEqual(len(launcher.active_agents), 3)
        self.assertEqual(mock_popen.call_count, 3)
    
    @patch('subprocess.Popen')
    def test_check_agent_status(self, mock_popen):
        """Test checking agent status"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Create and launch agent
        worktree_path = self.workspace_dir / "agent1"
        worktree_path.mkdir()
        
        launcher.launch_agent("agent1", "agent1-work", str(worktree_path), "Test")
        
        # Check status
        status = launcher.get_agent_status("agent1")
        self.assertEqual(status["status"], "running")
        self.assertEqual(status["pid"], 12345)
        
        # Simulate process termination
        mock_process.poll.return_value = 0
        status = launcher.get_agent_status("agent1")
        self.assertEqual(status["status"], "terminated")
        self.assertEqual(status["exit_code"], 0)
    
    @patch('subprocess.Popen')
    def test_terminate_agent(self, mock_popen):
        """Test terminating an agent"""
        # Set up mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Create and launch agent
        worktree_path = self.workspace_dir / "agent1"
        worktree_path.mkdir()
        
        launcher.launch_agent("agent1", "agent1-work", str(worktree_path), "Test")
        
        # Terminate agent
        launcher.terminate_agent("agent1")
        
        # Verify termination was called
        mock_process.terminate.assert_called_once()
        
        # Agent should be removed from active list
        self.assertNotIn("agent1", launcher.active_agents)
    
    @patch('subprocess.Popen')
    def test_terminate_all_agents(self, mock_popen):
        """Test terminating all agents"""
        # Set up mock processes
        mock_processes = []
        for i in range(3):
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345 + i
            mock_processes.append(mock_process)
        
        mock_popen.side_effect = mock_processes
        
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        # Launch multiple agents
        for i in range(1, 4):
            worktree_path = self.workspace_dir / f"agent{i}"
            worktree_path.mkdir()
            launcher.launch_agent(f"agent{i}", f"agent{i}-work", str(worktree_path), "Test")
        
        # Terminate all
        launcher.terminate_all_agents()
        
        # Verify all were terminated
        for process in mock_processes:
            process.terminate.assert_called_once()
        
        self.assertEqual(len(launcher.active_agents), 0)
    
    def test_generate_launch_command(self):
        """Test generating Claude launch command"""
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        config = ClaudeAgentConfig(
            agent_id="agent1",
            branch_name="agent1-work",
            worktree_path=str(self.workspace_dir / "agent1"),
            marcus_server_path=str(self.marcus_path)
        )
        
        cmd = launcher._generate_launch_command(config, "Test prompt")
        
        # Verify command structure
        self.assertEqual(cmd[0], "claude")
        self.assertIn("--mcp-servers", cmd)
        
        # Find MCP config in command
        mcp_idx = cmd.index("--mcp-servers") + 1
        mcp_config = json.loads(cmd[mcp_idx])
        self.assertIn("marcus", mcp_config)
    
    @patch('builtins.open', new_callable=mock_open, read_data="Prompt template with {AGENT_ID}")
    def test_load_prompt_template(self, mock_file):
        """Test loading prompt template from file"""
        launcher = AgentLauncher(
            workspace_dir=str(self.workspace_dir),
            marcus_server_path=str(self.marcus_path)
        )
        
        prompt = launcher.load_prompt_template("/path/to/prompt.md")
        
        self.assertEqual(prompt, "Prompt template with {AGENT_ID}")
        mock_file.assert_called_once_with("/path/to/prompt.md", 'r')


if __name__ == "__main__":
    unittest.main()