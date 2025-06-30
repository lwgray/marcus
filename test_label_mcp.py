#!/usr/bin/env python3
"""
Test script to debug kanban-mcp label manager functionality.

This script directly tests the label manager to understand why we're getting
empty responses. It performs the following tests:
1. Initialize the MCP client
2. Try to create a label with all required parameters
3. Print the full response details
4. Try to get all labels to see if they exist
5. Check if there's a response format issue
"""

import asyncio
import json
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Board ID provided by the user
BOARD_ID = "1533859887128249584"

# Set up environment for Planka
os.environ['PLANKA_BASE_URL'] = os.environ.get('PLANKA_BASE_URL', 'http://localhost:3333')
os.environ['PLANKA_AGENT_EMAIL'] = os.environ.get('PLANKA_AGENT_EMAIL', 'demo@demo.demo')
os.environ['PLANKA_AGENT_PASSWORD'] = os.environ.get('PLANKA_AGENT_PASSWORD', 'demo')


async def test_label_manager():
    """Test the label manager functionality."""
    print("🧪 Testing kanban-mcp label manager")
    print("=" * 60)
    print(f"Board ID: {BOARD_ID}")
    print(f"Planka URL: {os.environ['PLANKA_BASE_URL']}")
    print()
    
    # Set up MCP connection
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
                
                # List available tools to verify label manager exists
                print("\n📋 Available tools:")
                tools = await session.list_tools()
                label_tools = [t for t in tools.tools if 'label' in t.name.lower()]
                for tool in label_tools:
                    print(f"  - {tool.name}: {tool.description[:100] if tool.description else 'No description'}")
                
                if not any('label' in t.name.lower() for t in tools.tools):
                    print("❌ No label manager tool found!")
                    return
                
                # Test 1: Try to get all labels (this should work even if no labels exist)
                print("\n\n🔍 Test 1: Getting all labels")
                print("-" * 40)
                try:
                    result = await session.call_tool(
                        "mcp_kanban_label_manager",
                        {
                            "action": "get_all",
                            "boardId": BOARD_ID
                        }
                    )
                    
                    print(f"Result type: {type(result)}")
                    print(f"Has content: {hasattr(result, 'content')}")
                    
                    if hasattr(result, 'content') and result.content:
                        print(f"Content length: {len(result.content)}")
                        for i, content_item in enumerate(result.content):
                            print(f"\nContent item {i}:")
                            print(f"  Type: {type(content_item)}")
                            print(f"  Has text: {hasattr(content_item, 'text')}")
                            if hasattr(content_item, 'text'):
                                print(f"  Text: {content_item.text}")
                                if content_item.text:
                                    try:
                                        parsed = json.loads(content_item.text)
                                        print(f"  Parsed JSON: {json.dumps(parsed, indent=2)}")
                                    except json.JSONDecodeError as e:
                                        print(f"  JSON parse error: {e}")
                    else:
                        print("❌ No content in response")
                        
                except Exception as e:
                    print(f"❌ Error getting labels: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 2: Try to create a label
                print("\n\n🏷️ Test 2: Creating a new label")
                print("-" * 40)
                try:
                    # Try different action names based on common patterns
                    actions_to_try = ["create", "create_label", "add"]
                    
                    for action in actions_to_try:
                        print(f"\n  Trying action: '{action}'")
                        try:
                            result = await session.call_tool(
                                "mcp_kanban_label_manager",
                                {
                                    "action": action,
                                    "boardId": BOARD_ID,
                                    "name": "test-label",
                                    "color": "#4CAF50"  # Green color
                                }
                            )
                            
                            print(f"  ✅ Success with action '{action}'!")
                            print(f"  Result: {result}")
                            
                            if hasattr(result, 'content') and result.content:
                                for content_item in result.content:
                                    if hasattr(content_item, 'text') and content_item.text:
                                        print(f"  Response: {content_item.text}")
                            break
                            
                        except Exception as e:
                            print(f"  ❌ Failed with '{action}': {str(e)[:100]}")
                    
                except Exception as e:
                    print(f"❌ Error creating label: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 3: Try to add label to a card (first we need a card)
                print("\n\n🃏 Test 3: Adding label to a card")
                print("-" * 40)
                
                # First, get lists to find a card
                try:
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
                                        first_card = cards[0]
                                        print(f"  Found card: {first_card.get('name', 'Unnamed')} (ID: {first_card['id']})")
                                        
                                        # Try to add label to this card
                                        actions_to_try = ["add_to_card", "add_label", "assign", "attach"]
                                        
                                        for action in actions_to_try:
                                            print(f"\n  Trying action: '{action}'")
                                            try:
                                                result = await session.call_tool(
                                                    "mcp_kanban_label_manager",
                                                    {
                                                        "action": action,
                                                        "cardId": first_card["id"],
                                                        "name": "test-label",
                                                        "color": "#2196F3"  # Blue color
                                                    }
                                                )
                                                
                                                print(f"  ✅ Success with action '{action}'!")
                                                if hasattr(result, 'content') and result.content:
                                                    for content_item in result.content:
                                                        if hasattr(content_item, 'text') and content_item.text:
                                                            print(f"  Response: {content_item.text}")
                                                break
                                                
                                            except Exception as e:
                                                print(f"  ❌ Failed with '{action}': {str(e)[:100]}")
                                    else:
                                        print("  ℹ️ No cards found to test with")
                                        
                except Exception as e:
                    print(f"❌ Error in card label test: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Test 4: Check tool schema
                print("\n\n📐 Test 4: Examining tool schema")
                print("-" * 40)
                
                label_tool = next((t for t in tools.tools if t.name == "mcp_kanban_label_manager"), None)
                if label_tool:
                    print("Label manager tool found!")
                    print(f"Description: {label_tool.description}")
                    if hasattr(label_tool, 'inputSchema'):
                        print(f"\nInput schema: {json.dumps(label_tool.inputSchema, indent=2)}")
                else:
                    print("❌ Could not find label manager tool details")
                
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting kanban-mcp label manager test")
    print(f"Working directory: {os.getcwd()}")
    print(f"kanban-mcp expected at: {os.path.abspath('../kanban-mcp')}")
    print()
    
    try:
        asyncio.run(test_label_manager())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
        sys.exit(1)