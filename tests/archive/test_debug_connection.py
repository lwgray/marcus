#!/usr/bin/env python3
"""Debug the exact connection issue"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.integrations.mcp_kanban_client import MCPKanbanClient

async def debug_connection():
    print("🔍 Debugging Kanban MCP Connection")
    print("-" * 50)
    
    client = MCPKanbanClient()
    
    try:
        print("1. Starting connection...")
        await client.connect()
        print("✅ Connected successfully!")
        
        print(f"   Board ID: {client.board_id}")
        print(f"   Project ID: {client.project_id}")
        
        # Try to get tasks
        print("\n2. Getting available tasks...")
        tasks = await client.get_available_tasks()
        print(f"✅ Found {len(tasks)} tasks")
        
        # Disconnect
        print("\n3. Disconnecting...")
        await client.disconnect()
        print("✅ Disconnected")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Add timeout to prevent hanging forever
    try:
        asyncio.run(asyncio.wait_for(debug_connection(), timeout=30))
    except asyncio.TimeoutError:
        print("\n❌ Connection timed out after 30 seconds")
        sys.exit(1)