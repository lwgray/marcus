#!/usr/bin/env python3
"""Test if board_id is loaded correctly from configuration"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pm_agent_mvp_fixed import PMAgentMVP

def test_board_config():
    """Test that board_id and project_id are loaded correctly"""
    # Create PM Agent instance
    agent = PMAgentMVP()
    
    print(f"Kanban client board_id: {agent.kanban_client.board_id}")
    print(f"Kanban client project_id: {agent.kanban_client.project_id}")
    
    # Verify they're not None
    assert agent.kanban_client.board_id is not None, "board_id should be loaded from config"
    assert agent.kanban_client.project_id is not None, "project_id should be loaded from config"
    
    print("✅ Board configuration loaded successfully")

if __name__ == "__main__":
    test_board_config()