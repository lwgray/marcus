#!/usr/bin/env python3
"""
Start PM Agent configured for Task Master Project
"""

import asyncio
import os
import sys

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from src.pm_agent_mvp_fixed import PMAgentMVP


async def start_pm_agent_for_task_master():
    """Start PM Agent configured for the Task Master project"""
    
    # Initialize PM Agent
    pm_agent = PMAgentMVP()
    
    # The kanban client will load config from config_pm_agent.json automatically
    # No need to override project_id here
    
    # Verify connection
    print("🔍 Connecting to Task Master project...", file=sys.stderr)
    async with pm_agent.kanban_client.connect() as conn:
        # This will use the board_id and project_id from config
        print(f"✅ Connected to project: {pm_agent.kanban_client.project_id}", file=sys.stderr)
        print(f"✅ Using board: {pm_agent.kanban_client.board_id}", file=sys.stderr)
    
    # Initialize PM Agent
    print("\n🚀 Starting PM Agent for Task Master project...", file=sys.stderr)
    await pm_agent.initialize()
    
    # Run as stdio server
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await pm_agent.server.run(
            read_stream,
            write_stream,
            pm_agent.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(start_pm_agent_for_task_master())