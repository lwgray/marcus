#!/usr/bin/env python3
"""Test if board_id is loaded correctly"""

import sys
sys.path.insert(0, '.')

from src.pm_agent_mvp_fixed import PMAgentMVP

# Create PM Agent instance
agent = PMAgentMVP()

print(f"Kanban client board_id: {agent.kanban_client.board_id}")
print(f"Kanban client project_id: {agent.kanban_client.project_id}")