#!/usr/bin/env python3
"""
Start PM Agent configured for Task Master Project
"""

import asyncio
import os
import sys
from src.pm_agent_mvp_fixed import PMAgentMVP


async def start_pm_agent_for_task_master():
    """Start PM Agent configured for the Task Master project"""
    
    # Initialize PM Agent
    pm_agent = PMAgentMVP()
    
    # Configure for Task Master project
    pm_agent.kanban_client.project_id = "1533678301472621705"  # Your Task Master project ID
    
    # Find or create the active board
    print("🔍 Connecting to Task Master project...", file=sys.stderr)
    async with pm_agent.kanban_client.connect() as conn:
        # This will automatically find the board
        print(f"✅ Connected to project: {pm_agent.kanban_client.project_id}", file=sys.stderr)
        print(f"✅ Using board: {pm_agent.kanban_client.board_id}", file=sys.stderr)
    
    # Start the PM Agent server
    print("\n🚀 Starting PM Agent for Task Master project...", file=sys.stderr)
    await pm_agent.start()


if __name__ == "__main__":
    asyncio.run(start_pm_agent_for_task_master())