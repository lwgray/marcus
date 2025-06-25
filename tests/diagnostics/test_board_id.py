#!/usr/bin/env python3
"""
Test if board_id is loaded correctly from configuration.

This diagnostic test verifies that the PM Agent can successfully load board and project
IDs from the configuration, which is essential for kanban integration.

Notes
-----
This is a smoke test to quickly verify configuration loading without requiring
a full MCP connection.
"""

import sys
import os
from typing import None as NoneType

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.pm_agent_mvp_fixed import PMAgentMVP

def test_board_config() -> NoneType:
    """
    Test that board_id and project_id are loaded correctly.
    
    This function creates a PM Agent instance and verifies that both the board_id
    and project_id are successfully loaded from the configuration files.
    
    Raises
    ------
    AssertionError
        If either board_id or project_id is None.
    
    Notes
    -----
    This test does not require a connection to the MCP server, making it useful
    for quick configuration verification.
    
    Examples
    --------
    >>> test_board_config()
    Kanban client board_id: 1533678301472621705
    Kanban client project_id: 1533678301472621705
    ✅ Board configuration loaded successfully
    """
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