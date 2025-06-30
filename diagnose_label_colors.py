#!/usr/bin/env python3
"""
Diagnose why labels are all showing the same color
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


async def diagnose_label_colors():
    """Diagnose label color issues"""
    
    # Setup
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Label Color Diagnosis ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 1. Get all labels and check their colors
            print("1. Checking all labels on the board...\n")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if result and hasattr(result, 'content'):
                labels_data = json.loads(result.content[0].text)
                
                # Group by color
                color_groups = {}
                for label in labels_data:
                    color = label.get('color', 'unknown')
                    if color not in color_groups:
                        color_groups[color] = []
                    color_groups[color].append(label['name'])
                
                # Show distribution
                print("Color Distribution:")
                for color, names in sorted(color_groups.items()):
                    print(f"\n{color} ({len(names)} labels):")
                    # Show labels that should have different colors
                    relevant = [n for n in names if any(p in n for p in ['priority:', 'skill:', 'type:', 'complexity:', 'component:'])]
                    for name in relevant[:10]:
                        print(f"  - {name}")
                    if len(relevant) > 10:
                        print(f"  ... and {len(relevant) - 10} more")
                
                # 2. Check specific labels from the screenshot
                print("\n\n2. Checking specific labels from your screenshot...\n")
                
                screenshot_labels = [
                    "complexity:moderate",
                    "priority:medium", 
                    "component:authentication",
                    "skill:frontend",
                    "type:setup",
                    "type:feature"
                ]
                
                print("Label Name -> Current Color (Expected Color)")
                print("-" * 60)
                
                from src.integrations.label_manager_helper import LabelManagerHelper
                
                for label_name in screenshot_labels:
                    # Find the label
                    found = False
                    for label in labels_data:
                        if label['name'] == label_name:
                            current_color = label['color']
                            expected_color = LabelManagerHelper.get_color_for_label(label_name)
                            match = "✓" if current_color == expected_color else "✗"
                            print(f"{match} {label_name:<30} -> {current_color:<15} ({expected_color})")
                            found = True
                            break
                    
                    if not found:
                        expected_color = LabelManagerHelper.get_color_for_label(label_name)
                        print(f"? {label_name:<30} -> NOT FOUND      ({expected_color})")
                
                # 3. Try to update an existing label's color
                print("\n\n3. Testing if we can update a label's color...\n")
                
                # Find a label to update
                test_label = None
                for label in labels_data:
                    if label['name'] == "priority:medium":
                        test_label = label
                        break
                
                if test_label:
                    print(f"Found 'priority:medium' with color: {test_label['color']}")
                    print(f"Expected color: egg-yellow")
                    
                    if test_label['color'] != 'egg-yellow':
                        print("\nAttempting to update color...")
                        try:
                            update_result = await session.call_tool(
                                "mcp_kanban_label_manager",
                                {
                                    "action": "update",
                                    "id": test_label['id'],
                                    "boardId": board_id,
                                    "name": test_label['name'],
                                    "color": "egg-yellow",
                                    "position": test_label.get('position', 65536)
                                }
                            )
                            
                            if update_result and hasattr(update_result, 'content'):
                                print(f"Update result: {update_result.content[0].text}")
                            else:
                                print("Update failed - no response")
                                
                        except Exception as e:
                            print(f"Update failed with error: {e}")
                    else:
                        print("Color is already correct!")


if __name__ == "__main__":
    try:
        asyncio.run(diagnose_label_colors())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()