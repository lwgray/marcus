#!/usr/bin/env python3
"""Tests for prompt templating functionality"""

import unittest
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))


class TestPromptTemplating(unittest.TestCase):
    """Test prompt template substitution"""
    
    def setUp(self):
        """Load the marcus agent prompt"""
        prompt_path = Path(__file__).parent.parent / "prompts" / "marcus_agent.md"
        with open(prompt_path, 'r') as f:
            self.prompt_template = f.read()
    
    def test_prompt_has_required_placeholders(self):
        """Test that prompt contains all required placeholders"""
        required_placeholders = [
            "{AGENT_ID}",
            "{BRANCH_NAME}",
            "{WORKTREE_PATH}"
        ]
        
        for placeholder in required_placeholders:
            self.assertIn(placeholder, self.prompt_template,
                         f"Prompt missing required placeholder: {placeholder}")
    
    def test_prompt_substitution(self):
        """Test that placeholders are properly substituted"""
        # Substitute values
        prompt = self.prompt_template.format(
            AGENT_ID="test-agent-1",
            BRANCH_NAME="test-agent-1-work",
            WORKTREE_PATH="/path/to/worktree"
        )
        
        # Verify substitutions worked
        self.assertIn("Agent ID: test-agent-1", prompt)
        self.assertIn("Working Branch: test-agent-1-work", prompt)
        self.assertIn("Working Directory: /path/to/worktree", prompt)
        
        # Verify no placeholders remain
        self.assertNotIn("{AGENT_ID}", prompt)
        self.assertNotIn("{BRANCH_NAME}", prompt)
        self.assertNotIn("{WORKTREE_PATH}", prompt)
    
    def test_prompt_contains_marcus_tools(self):
        """Test that prompt mentions all Marcus MCP tools"""
        marcus_tools = [
            "marcus.register_agent",
            "marcus.request_next_task",
            "marcus.report_task_progress",
            "marcus.report_blocker",
            "marcus.get_agent_status",
            "marcus.get_project_status"
        ]
        
        for tool in marcus_tools:
            self.assertIn(tool, self.prompt_template,
                         f"Prompt missing Marcus tool: {tool}")
    
    def test_prompt_structure(self):
        """Test that prompt has expected sections"""
        expected_sections = [
            "## Your Identity",
            "## Your Mission",
            "## Available Marcus MCP Tools",
            "## Workflow",
            "### 1. Registration",
            "### 2. Task Loop",
            "### 3. Task Execution",
            "### 4. Handling Blockers",
            "### 5. Task Completion",
            "## Best Practices",
            "## Git Workflow",
            "## Success Criteria"
        ]
        
        for section in expected_sections:
            self.assertIn(section, self.prompt_template,
                         f"Prompt missing section: {section}")
    
    def test_prompt_mentions_swe_bench(self):
        """Test that prompt mentions SWE-bench context"""
        swe_bench_terms = [
            "SWE-bench",
            "FAIL_TO_PASS",
            "PASS_TO_PASS",
            "instance_id",
            "base_commit"
        ]
        
        for term in swe_bench_terms:
            self.assertIn(term, self.prompt_template,
                         f"Prompt missing SWE-bench term: {term}")


if __name__ == "__main__":
    unittest.main()