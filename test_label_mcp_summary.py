#!/usr/bin/env python3
"""
Summary of kanban-mcp label manager findings and correct usage.

Key findings:
1. Label colors must be from a specific enum list (not hex colors)
2. Adding labels to cards requires the label ID, not the name
3. Labels should be created at the board level first, then added to cards
4. The board already has many duplicate labels with the same name
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Add project root to path  
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from src.integrations.label_manager_helper import LabelManagerHelper

BOARD_ID = "1533859887128249584"

# Set up environment
os.environ['PLANKA_BASE_URL'] = os.environ.get('PLANKA_BASE_URL', 'http://localhost:3333')
os.environ['PLANKA_AGENT_EMAIL'] = os.environ.get('PLANKA_AGENT_EMAIL', 'demo@demo.demo')
os.environ['PLANKA_AGENT_PASSWORD'] = os.environ.get('PLANKA_AGENT_PASSWORD', 'demo')


async def main():
    """Demonstrate complete label management workflow."""
    print("📊 KANBAN-MCP LABEL MANAGER - COMPLETE GUIDE")
    print("=" * 70)
    print()
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Initialize helper
                helper = LabelManagerHelper(session, BOARD_ID)
                
                print("✅ Connected to kanban-mcp")
                print(f"📋 Board ID: {BOARD_ID}")
                print()
                
                # 1. Show current label situation
                print("1️⃣ CURRENT LABEL SITUATION")
                print("-" * 40)
                
                all_labels = await helper.refresh_labels()
                print(f"Total labels on board: {len(all_labels)}")
                
                # Group by name to show duplicates
                label_groups: Dict[str, List[Dict]] = {}
                for label in all_labels:
                    name = label.get('name', 'Unknown')
                    if name not in label_groups:
                        label_groups[name] = []
                    label_groups[name].append(label)
                
                print(f"Unique label names: {len(label_groups)}")
                print("\nLabel distribution:")
                for name, labels in sorted(label_groups.items()):
                    if len(labels) > 1:
                        print(f"  ⚠️  {name}: {len(labels)} duplicates")
                    else:
                        print(f"  ✅ {name}: 1 instance ({labels[0]['color']})")
                
                # 2. Demonstrate proper label creation
                print("\n\n2️⃣ PROPER LABEL CREATION")
                print("-" * 40)
                
                test_labels = [
                    ("deployment", "tank-green"),
                    ("urgent", "red-burgundy"),
                    ("review", "egg-yellow")
                ]
                
                for name, color in test_labels:
                    try:
                        label_id = await helper.ensure_label_exists(name, color)
                        print(f"✅ Label '{name}' ready (ID: {label_id})")
                    except Exception as e:
                        print(f"❌ Failed to ensure '{name}': {e}")
                
                # 3. Demonstrate adding labels to a card
                print("\n\n3️⃣ ADDING LABELS TO CARDS")
                print("-" * 40)
                
                # Get a test card
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": BOARD_ID
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else []
                    
                    # Find a list with cards
                    for lst in lists:
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": lst["id"]
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content') and cards_result.content:
                            cards_text = cards_result.content[0].text
                            if cards_text and cards_text.strip():
                                cards_data = json.loads(cards_text)
                                cards = cards_data if isinstance(cards_data, list) else []
                                
                                if cards:
                                    test_card = cards[0]
                                    print(f"Test card: {test_card.get('name', 'Unnamed')}")
                                    
                                    # Add multiple labels
                                    labels_to_add = ["backend", "testing", "urgent"]
                                    added = await helper.add_labels_to_card(test_card['id'], labels_to_add)
                                    print(f"Added {len(added)} labels to the card")
                                    break
                
                # 4. Best practices summary
                print("\n\n4️⃣ BEST PRACTICES")
                print("-" * 40)
                
                print("\n✅ DO:")
                print("- Use valid color names from the enum list")
                print("- Create labels at board level before adding to cards")
                print("- Use label IDs (not names) when adding to cards")
                print("- Check if a label exists before creating it")
                print("- Use the LabelManagerHelper for simplified workflows")
                
                print("\n❌ DON'T:")
                print("- Use hex colors like '#4CAF50'")
                print("- Try to create labels directly on cards")
                print("- Pass label names to add_to_card action")
                print("- Create duplicate labels with the same name")
                
                print("\n\n5️⃣ CODE EXAMPLES")
                print("-" * 40)
                
                print("\n# Initialize helper")
                print("helper = LabelManagerHelper(session, board_id)")
                
                print("\n# Add labels to a card (creates if needed)")
                print("labels = ['backend', 'python', 'high-priority']")
                print("await helper.add_labels_to_card(card_id, labels)")
                
                print("\n# Get recommended color for a label")
                print("color = LabelManagerHelper.get_color_for_label('frontend')")
                print(f"# Returns: '{LabelManagerHelper.get_color_for_label('frontend')}'")
                
                print("\n# Valid colors:")
                for i in range(0, len(LabelManagerHelper.VALID_COLORS), 8):
                    colors = LabelManagerHelper.VALID_COLORS[i:i+8]
                    print(f"# {', '.join(colors)}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting kanban-mcp label manager summary")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)