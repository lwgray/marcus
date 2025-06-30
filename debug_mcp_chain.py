#!/usr/bin/env python3
"""
Debug the exact chain where "Not initialized" error occurs
"""

import asyncio
import json
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.marcus_mcp.server import MarcusServer


async def debug_mcp_chain():
    """Debug exactly where the 'Not initialized' error is coming from"""
    
    print("=== Debugging MCP Chain ===\n")
    
    # Create Marcus server
    server = MarcusServer()
    print("1. Created Marcus server")
    
    # Step by step debugging
    try:
        print("\n2. Testing initialize_kanban()...")
        await server.initialize_kanban()
        print("   ✓ initialize_kanban() completed")
        
        if server.kanban_client:
            print("   ✓ kanban_client created")
            print(f"   ✓ Provider: {server.provider}")
            print(f"   ✓ Client type: {type(server.kanban_client)}")
            
            # Test the specific method that's failing
            print("\n3. Testing kanban_client.get_available_tasks()...")
            try:
                tasks = await server.kanban_client.get_available_tasks()
                print(f"   ✓ get_available_tasks() returned {len(tasks)} tasks")
            except Exception as e:
                print(f"   ✗ get_available_tasks() failed: {e}")
                print("   This is where the 'Not initialized' error is coming from!")
                
                # Let's check the actual kanban client's board_id
                if hasattr(server.kanban_client, 'client'):
                    inner_client = server.kanban_client.client
                    print(f"   Inner client board_id: {getattr(inner_client, 'board_id', 'None')}")
                
                if hasattr(server.kanban_client, 'board_id'):
                    print(f"   Client board_id: {server.kanban_client.board_id}")
                    
                return
                
        else:
            print("   ✗ kanban_client is None")
            return
            
        print("\n4. Testing refresh_project_state directly...")
        try:
            await server.refresh_project_state()
            print("   ✓ refresh_project_state() completed")
        except Exception as e:
            print(f"   ✗ refresh_project_state() failed: {e}")
            
    except Exception as e:
        print(f"Error in step: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_mcp_chain())