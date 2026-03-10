#!/usr/bin/env python3
"""
Direct test of kanban-mcp get_details action.

This bypasses all Marcus code to directly test what kanban-mcp returns.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402


async def main() -> None:
    """Test get_details directly."""
    print("\n" + "=" * 70)
    print("🧪 DIRECT kanban-mcp get_details TEST")
    print("=" * 70)

    # Get board ID from environment
    board_id = os.getenv("PLANKA_BOARD_ID")
    if not board_id:
        print("❌ PLANKA_BOARD_ID not set")
        return

    print(f"\nBoard ID: {board_id}")

    # Set up MCP connection
    kanban_mcp_path = "/Users/lwgray/dev/kanban-mcp/dist/index.js"
    server_params = StdioServerParameters(
        command="node",
        args=[kanban_mcp_path],
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get all lists
            print("\n📋 Getting lists...")
            lists_result = await session.call_tool(
                "mcp_kanban_list_manager",
                {"action": "get_all", "boardId": board_id},
            )

            lists_data = json.loads(lists_result.content[0].text)
            lists = (
                lists_data
                if isinstance(lists_data, list)
                else lists_data.get("items", [])
            )
            print(f"Found {len(lists)} lists")

            # Get cards from first list
            if lists:
                list_id = lists[0]["id"]
                print(f"\n📇 Getting cards from list: {lists[0]['name']}")

                cards_result = await session.call_tool(
                    "mcp_kanban_card_manager",
                    {"action": "get_all", "listId": list_id},
                )

                cards_data = json.loads(cards_result.content[0].text)
                cards = (
                    cards_data
                    if isinstance(cards_data, list)
                    else cards_data.get("items", [])
                )
                print(f"Found {len(cards)} cards")

                # Get details for first card
                if cards:
                    card_id = cards[0]["id"]
                    card_name = cards[0].get("name", "unknown")

                    print(f"\n🔍 Getting details for card: {card_name}")
                    print(f"   Card ID: {card_id}")

                    details_result = await session.call_tool(
                        "mcp_kanban_card_manager",
                        {"action": "get_details", "cardId": card_id},
                    )

                    details_data = json.loads(details_result.content[0].text)

                    print("\n" + "=" * 70)
                    print("📦 CARD DETAILS")
                    print("=" * 70)
                    print(f"Keys in details: {list(details_data.keys())}")

                    if "labels" in details_data:
                        labels = details_data["labels"]
                        print(f"\n✅ Has 'labels' field: {len(labels)} labels")
                        for i, label in enumerate(labels, 1):
                            print(
                                f"   {i}. {label.get('name')} (id: {label.get('id')})"
                            )
                    else:
                        print("\n❌ NO 'labels' field in details")

                    if "labelIds" in details_data:
                        label_ids = details_data["labelIds"]
                        print(f"\n✅ Has 'labelIds' field: {label_ids}")
                    else:
                        print("\n❌ NO 'labelIds' field in details")

                    print("\n" + "=" * 70)
                    print("Full card details:")
                    print("=" * 70)
                    print(json.dumps(details_data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
