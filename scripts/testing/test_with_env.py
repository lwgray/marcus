#!/usr/bin/env python3
"""
Test connection with proper environment variables
"""

import asyncio
import json
import sys
import os

# Set environment variables
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.integrations.mcp_kanban_client_refactored import MCPKanbanClient


async def test_boards():
    """Test getting boards"""
    print("🔍 Testing board access with environment variables set...")
    
    client = MCPKanbanClient()
    client.project_id = "1533678301472621705"
    
    try:
        async with client.connect() as conn:
            print("✅ Connection established!")
            
            # Get boards
            result = await conn.call_tool("mcp_kanban_project_board_manager", {
                "action": "get_boards",
                "projectId": client.project_id
            })
            
            boards = json.loads(result.content[0].text)
            print(f"\n📋 Found {len(boards)} board(s):")
            for board in boards:
                print(f"  - {board['name']} (ID: {board['id']})")
            
            return boards
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_boards())