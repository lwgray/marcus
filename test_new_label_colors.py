#!/usr/bin/env python3
"""
Test creating NEW labels with proper colors
"""

import asyncio
import json
import os
import time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient
from src.integrations.label_manager_helper import LabelManagerHelper


async def test_new_label_colors():
    """Test creating brand new labels with proper colors"""
    
    # Setup
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Testing NEW Label Color Assignment ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Create label helper
            helper = LabelManagerHelper(session, board_id)
            
            # Use timestamp to ensure unique labels
            timestamp = str(int(time.time()))[-6:]
            
            # Test labels with different patterns
            test_labels = [
                (f"priority:urgent-{timestamp}", "berry-red"),      # Priority prefix
                (f"skill:python-{timestamp}", "bright-moss"),       # Python from DEFAULT_LABEL_COLORS
                (f"type:bug-{timestamp}", "midnight-blue"),         # Bug from DEFAULT_LABEL_COLORS
                (f"complexity:complex-{timestamp}", "berry-red"),   # Complex from DEFAULT_LABEL_COLORS
                (f"component:api-{timestamp}", "berry-red"),        # API from DEFAULT_LABEL_COLORS
            ]
            
            print(f"1. Creating new test labels (suffix: {timestamp})...\n")
            
            created_labels = []
            
            for label_name, expected_color in test_labels:
                try:
                    print(f"   Creating '{label_name}'...")
                    print(f"   Expected color: {expected_color}")
                    
                    # Create the label
                    label_id = await helper.ensure_label_exists(label_name)
                    created_labels.append(label_name)
                    print(f"   ✓ Created with ID: {label_id[:8]}...")
                    
                except Exception as e:
                    print(f"   ✗ Failed: {e}")
                
                print()
            
            # Verify what was actually created
            print("\n2. Verifying created label colors...\n")
            
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if result and hasattr(result, 'content'):
                all_labels = json.loads(result.content[0].text)
                
                # Find our newly created labels
                print("   Label Name -> Actual Color (Expected)\n")
                for label_name, expected_color in test_labels:
                    found = False
                    for label in all_labels:
                        if label['name'] == label_name:
                            match = "✓" if label['color'] == expected_color else "✗"
                            print(f"   {match} '{label_name}' -> {label['color']} ({expected_color})")
                            found = True
                            break
                    
                    if not found:
                        print(f"   ? '{label_name}' -> NOT FOUND")
                
                # Summary
                print("\n3. Color distribution for our test labels:")
                color_counts = {}
                for label in all_labels:
                    if label['name'] in [ln for ln, _ in test_labels]:
                        color = label['color']
                        color_counts[color] = color_counts.get(color, 0) + 1
                
                for color, count in sorted(color_counts.items()):
                    print(f"   {color}: {count} labels")


if __name__ == "__main__":
    try:
        asyncio.run(test_new_label_colors())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()