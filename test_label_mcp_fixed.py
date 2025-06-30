#!/usr/bin/env python3
"""
Fixed test script showing the correct way to use kanban-mcp label manager.

Based on the schema discovered, this script demonstrates:
1. Creating labels with proper color names
2. Adding existing labels to cards
3. Managing label lifecycle
"""

import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Board ID provided by the user
BOARD_ID = "1533859887128249584"

# Valid colors from the schema
VALID_COLORS = [
    "berry-red", "pumpkin-orange", "lagoon-blue", "pink-tulip", "light-mud",
    "orange-peel", "bright-moss", "antique-blue", "dark-granite", "lagune-blue",
    "sunny-grass", "morning-sky", "light-orange", "midnight-blue", "tank-green",
    "gun-metal", "wet-moss", "red-burgundy", "light-concrete", "apricot-red",
    "desert-sand", "navy-blue", "egg-yellow", "coral-green", "light-cocoa"
]

# Set up environment for Planka
os.environ['PLANKA_BASE_URL'] = os.environ.get('PLANKA_BASE_URL', 'http://localhost:3333')
os.environ['PLANKA_AGENT_EMAIL'] = os.environ.get('PLANKA_AGENT_EMAIL', 'demo@demo.demo')
os.environ['PLANKA_AGENT_PASSWORD'] = os.environ.get('PLANKA_AGENT_PASSWORD', 'demo')


async def demonstrate_label_usage():
    """Demonstrate correct usage of the label manager."""
    print("🧪 Demonstrating Correct Label Manager Usage")
    print("=" * 60)
    print(f"Board ID: {BOARD_ID}")
    print()
    
    server_params = StdioServerParameters(
        command="node",
        args=["../kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ MCP session initialized")
                await session.initialize()
                
                # Step 1: Get existing labels
                print("\n📋 Step 1: Getting existing labels")
                print("-" * 40)
                
                result = await session.call_tool(
                    "mcp_kanban_label_manager",
                    {
                        "action": "get_all",
                        "boardId": BOARD_ID
                    }
                )
                
                existing_labels = []
                if result and hasattr(result, 'content') and result.content:
                    labels_data = json.loads(result.content[0].text)
                    existing_labels = labels_data if isinstance(labels_data, list) else []
                    
                    print(f"Found {len(existing_labels)} existing labels:")
                    # Group by name to show duplicates
                    label_names = {}
                    for label in existing_labels:
                        name = label.get('name', 'Unknown')
                        if name not in label_names:
                            label_names[name] = []
                        label_names[name].append(label)
                    
                    for name, labels in label_names.items():
                        if len(labels) == 1:
                            label = labels[0]
                            print(f"  - {name} ({label['color']}) - ID: {label['id']}")
                        else:
                            print(f"  - {name} ({len(labels)} variants):")
                            for label in labels[:3]:  # Show first 3
                                print(f"      * {label['color']} - ID: {label['id']}")
                
                # Step 2: Create a new label with valid color
                print("\n\n🏷️ Step 2: Creating a new label with valid color")
                print("-" * 40)
                
                new_label_name = "test-automation"
                new_label_color = "coral-green"  # Using a valid color from the enum
                
                try:
                    result = await session.call_tool(
                        "mcp_kanban_label_manager",
                        {
                            "action": "create",
                            "boardId": BOARD_ID,
                            "name": new_label_name,
                            "color": new_label_color
                        }
                    )
                    
                    if result and hasattr(result, 'content') and result.content:
                        created_label = json.loads(result.content[0].text)
                        print(f"✅ Created label: {created_label['name']} ({created_label['color']})")
                        print(f"   ID: {created_label['id']}")
                        new_label_id = created_label['id']
                    else:
                        print("❌ Failed to create label - no response")
                        new_label_id = None
                        
                except Exception as e:
                    print(f"❌ Error creating label: {e}")
                    new_label_id = None
                
                # Step 3: Add label to a card
                print("\n\n🃏 Step 3: Adding label to a card")
                print("-" * 40)
                
                # First get a card to work with
                lists_result = await session.call_tool(
                    "mcp_kanban_list_manager",
                    {
                        "action": "get_all",
                        "boardId": BOARD_ID
                    }
                )
                
                if lists_result and hasattr(lists_result, 'content') and lists_result.content:
                    lists_data = json.loads(lists_result.content[0].text)
                    lists = lists_data if isinstance(lists_data, list) else lists_data.get("items", [])
                    
                    if lists:
                        # Get cards from the first list
                        first_list = lists[0]
                        cards_result = await session.call_tool(
                            "mcp_kanban_card_manager",
                            {
                                "action": "get_all",
                                "listId": first_list["id"]
                            }
                        )
                        
                        if cards_result and hasattr(cards_result, 'content') and cards_result.content:
                            cards_text = cards_result.content[0].text
                            if cards_text and cards_text.strip():
                                cards_data = json.loads(cards_text)
                                cards = cards_data if isinstance(cards_data, list) else cards_data.get("items", [])
                                
                                if cards:
                                    test_card = cards[0]
                                    print(f"Using card: {test_card.get('name', 'Unnamed')} (ID: {test_card['id']})")
                                    
                                    # Add an existing label to the card
                                    if existing_labels:
                                        # Use the first Frontend label
                                        frontend_label = next((l for l in existing_labels if l['name'] == 'Frontend'), existing_labels[0])
                                        
                                        print(f"\nAdding existing label '{frontend_label['name']}' to card...")
                                        try:
                                            result = await session.call_tool(
                                                "mcp_kanban_label_manager",
                                                {
                                                    "action": "add_to_card",
                                                    "cardId": test_card["id"],
                                                    "labelId": frontend_label["id"]
                                                }
                                            )
                                            print("✅ Successfully added existing label to card")
                                        except Exception as e:
                                            print(f"❌ Error adding existing label: {e}")
                                    
                                    # Add the newly created label if it exists
                                    if new_label_id:
                                        print(f"\nAdding new label '{new_label_name}' to card...")
                                        try:
                                            result = await session.call_tool(
                                                "mcp_kanban_label_manager",
                                                {
                                                    "action": "add_to_card",
                                                    "cardId": test_card["id"],
                                                    "labelId": new_label_id
                                                }
                                            )
                                            print("✅ Successfully added new label to card")
                                        except Exception as e:
                                            print(f"❌ Error adding new label: {e}")
                
                # Step 4: Show correct usage patterns
                print("\n\n📚 Correct Usage Patterns")
                print("-" * 40)
                print("\n1. Creating a label:")
                print("   await session.call_tool('mcp_kanban_label_manager', {")
                print("       'action': 'create',")
                print("       'boardId': board_id,")
                print("       'name': 'my-label',")
                print(f"       'color': '{VALID_COLORS[0]}'  # Must be from: {', '.join(VALID_COLORS[:5])}...")
                print("   })")
                
                print("\n2. Adding label to card (use labelId, not name):")
                print("   await session.call_tool('mcp_kanban_label_manager', {")
                print("       'action': 'add_to_card',")
                print("       'cardId': card_id,")
                print("       'labelId': label_id  # NOT 'name' or 'color'")
                print("   })")
                
                print("\n3. To add a label by name, first find its ID:")
                print("   # Get all labels")
                print("   labels = await get_all_labels()")
                print("   # Find the label by name")
                print("   label = next((l for l in labels if l['name'] == 'Frontend'), None)")
                print("   # Use its ID")
                print("   if label:")
                print("       await add_label_to_card(card_id, label['id'])")
                
                print("\n\n🎨 Valid label colors:")
                for i in range(0, len(VALID_COLORS), 5):
                    print(f"   {', '.join(VALID_COLORS[i:i+5])}")
                
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


async def create_or_get_label(session, board_id: str, name: str, color: str) -> str:
    """Helper function to create a label or get existing one."""
    # First check if label exists
    result = await session.call_tool(
        "mcp_kanban_label_manager",
        {
            "action": "get_all",
            "boardId": board_id
        }
    )
    
    if result and hasattr(result, 'content') and result.content:
        labels = json.loads(result.content[0].text)
        existing = next((l for l in labels if l['name'] == name), None)
        if existing:
            return existing['id']
    
    # Create new label
    result = await session.call_tool(
        "mcp_kanban_label_manager",
        {
            "action": "create",
            "boardId": board_id,
            "name": name,
            "color": color
        }
    )
    
    if result and hasattr(result, 'content') and result.content:
        created = json.loads(result.content[0].text)
        return created['id']
    
    raise Exception(f"Failed to create label {name}")


if __name__ == "__main__":
    print("🚀 Starting fixed kanban-mcp label manager demo")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    try:
        asyncio.run(demonstrate_label_usage())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)