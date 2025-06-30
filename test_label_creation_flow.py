#!/usr/bin/env python3
"""
Test the complete label creation flow during task creation
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


async def test_label_creation_flow():
    """Test how labels are created in the actual flow"""
    
    # Setup
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Testing Label Creation Flow ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Create label helper (mimicking what happens in _add_labels_to_card)
            label_helper = LabelManagerHelper(session, board_id)
            
            # Test creating a new label with unique name
            timestamp = str(int(time.time()))[-6:]
            test_label = f"priority:urgent-test-{timestamp}"
            
            print(f"1. Testing label creation for: '{test_label}'")
            print(f"   Expected color: {LabelManagerHelper.get_color_for_label(test_label)}")
            
            # Create the label using the helper (this is what happens in the actual flow)
            try:
                label_id = await label_helper.ensure_label_exists(test_label)
                print(f"   Created with ID: {label_id}")
                
                # Now check what color it actually got
                result = await session.call_tool(
                    "mcp_kanban_label_manager",
                    {
                        "action": "get_all",
                        "boardId": board_id
                    }
                )
                
                if result and hasattr(result, 'content'):
                    labels_data = json.loads(result.content[0].text)
                    for label in labels_data:
                        if label['name'] == test_label:
                            print(f"   Actual color: {label['color']}")
                            expected = LabelManagerHelper.get_color_for_label(test_label)
                            if label['color'] == expected:
                                print("   ✓ Color is correct!")
                            else:
                                print(f"   ✗ Color mismatch! Expected: {expected}")
                            break
                
            except Exception as e:
                print(f"   Error: {e}")
            
            # Test with the exact labels from task creation
            print("\n2. Testing with actual task labels...")
            
            task_labels = [
                "component:authentication",
                "type:feature", 
                "priority:medium",
                "skill:frontend",
                "complexity:moderate"
            ]
            
            for label_name in task_labels:
                # Check if it exists first
                await label_helper.refresh_labels()
                
                print(f"\n   Label: '{label_name}'")
                expected_color = LabelManagerHelper.get_color_for_label(label_name)
                print(f"   Expected color: {expected_color}")
                
                # The helper should use existing label if it exists
                # Let's trace what happens
                if label_name.lower() in label_helper._label_cache:
                    cached_label = label_helper._label_cache[label_name.lower()]
                    print(f"   Found in cache with color: {cached_label['color']}")
                    if cached_label['color'] != expected_color:
                        print(f"   ✗ Cached label has wrong color!")
                else:
                    print(f"   Not in cache - would create new")


if __name__ == "__main__":
    try:
        asyncio.run(test_label_creation_flow())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()