#!/usr/bin/env python3
"""
Fix colors of existing labels on the board
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


async def fix_existing_label_colors():
    """Fix colors of existing labels"""
    
    # Setup
    client = SimpleMCPKanbanClient()
    board_id = "1533859887128249584"
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("=== Fixing Existing Label Colors ===\n")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get all labels
            print("1. Getting all labels...\n")
            result = await session.call_tool(
                "mcp_kanban_label_manager",
                {
                    "action": "get_all",
                    "boardId": board_id
                }
            )
            
            if result and hasattr(result, 'content'):
                labels_data = json.loads(result.content[0].text)
                
                # Find labels that need color updates
                labels_to_fix = []
                for label in labels_data:
                    name = label['name']
                    current_color = label['color']
                    expected_color = LabelManagerHelper.get_color_for_label(name)
                    
                    # Only fix labels with prefixes that should have specific colors
                    if ':' in name and current_color != expected_color:
                        labels_to_fix.append({
                            'label': label,
                            'expected_color': expected_color
                        })
                
                print(f"Found {len(labels_to_fix)} labels that need color updates\n")
                
                # Update each label
                print("2. Updating label colors...\n")
                
                fixed_count = 0
                failed_count = 0
                
                for item in labels_to_fix:
                    label = item['label']
                    expected_color = item['expected_color']
                    
                    print(f"   Updating '{label['name']}': {label['color']} -> {expected_color}")
                    
                    try:
                        update_result = await session.call_tool(
                            "mcp_kanban_label_manager",
                            {
                                "action": "update",
                                "id": label['id'],
                                "boardId": board_id,
                                "name": label['name'],
                                "color": expected_color,
                                "position": label.get('position', 65536)
                            }
                        )
                        
                        if update_result and hasattr(update_result, 'content'):
                            updated = json.loads(update_result.content[0].text)
                            if updated['color'] == expected_color:
                                print(f"   ✓ Success!")
                                fixed_count += 1
                            else:
                                print(f"   ✗ Color not updated properly")
                                failed_count += 1
                        else:
                            print(f"   ✗ No response")
                            failed_count += 1
                            
                    except Exception as e:
                        print(f"   ✗ Error: {e}")
                        failed_count += 1
                    
                    # Small delay to avoid overwhelming the API
                    await asyncio.sleep(0.1)
                
                # Summary
                print(f"\n3. Summary:")
                print(f"   ✓ Fixed: {fixed_count} labels")
                print(f"   ✗ Failed: {failed_count} labels")
                print(f"   Total: {len(labels_to_fix)} labels")
                
                # Show final color distribution
                print(f"\n4. Verifying final color distribution...\n")
                
                # Get labels again to verify
                verify_result = await session.call_tool(
                    "mcp_kanban_label_manager",
                    {
                        "action": "get_all",
                        "boardId": board_id
                    }
                )
                
                if verify_result and hasattr(verify_result, 'content'):
                    labels_data = json.loads(verify_result.content[0].text)
                    
                    # Count colors for prefixed labels
                    color_counts = {}
                    for label in labels_data:
                        if ':' in label['name']:
                            color = label['color']
                            color_counts[color] = color_counts.get(color, 0) + 1
                    
                    print("Color distribution for prefixed labels:")
                    for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
                        print(f"   {color}: {count} labels")


if __name__ == "__main__":
    try:
        asyncio.run(fix_existing_label_colors())
    except Exception as e:
        print(f"\nError: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()