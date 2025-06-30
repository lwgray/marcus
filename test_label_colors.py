#!/usr/bin/env python3
"""
Test label color assignment
"""

import asyncio
import json
import os
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
from src.integrations.label_manager_helper import LabelManagerHelper


async def test_label_colors():
    """Test that labels are created with proper colors"""
    
    # Setup
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Testing Label Color Assignment ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Create label helper
            helper = LabelManagerHelper(session, board_id)
            
            # Test labels with different patterns
            test_labels = [
                "priority:high",      # Should be berry-red
                "skill:frontend",     # Should be lagoon-blue
                "type:feature",       # Should be pink-tulip
                "complexity:moderate", # Should be egg-yellow
                "component:authentication", # Should be midnight-blue (from suffix)
            ]
            
            print("1. Creating test labels with proper colors...\n")
            
            for label_name in test_labels:
                try:
                    # Get the color that will be used
                    expected_color = LabelManagerHelper.get_color_for_label(label_name)
                    print(f"   Creating '{label_name}'...")
                    print(f"   Expected color: {expected_color}")
                    
                    # Create the label
                    label_id = await helper.ensure_label_exists(label_name)
                    print(f"   ✓ Created with ID: {label_id[:8]}...")
                    
                except Exception as e:
                    print(f"   ✗ Failed: {e}")
                
                print()
            
            # Check what was actually created
            print("\n2. Verifying created labels...\n")
            
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if result and hasattr(result, 'content'):
                all_labels = json.loads(result.content[0].text)
                
                # Find our test labels
                for test_label in test_labels:
                    found = False
                    for label in all_labels:
                        if label['name'] == test_label:
                            print(f"   '{test_label}' -> {label['color']}")
                            found = True
                            break
                    
                    if not found:
                        print(f"   '{test_label}' -> NOT FOUND")


if __name__ == "__main__":
    try:
        asyncio.run(test_label_colors())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()