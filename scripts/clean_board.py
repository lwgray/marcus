#!/usr/bin/env python3
"""Clean all cards from a Planka board without repopulating.

This module provides functionality to quickly remove all cards from a specified
Planka board while preserving the board structure (lists remain intact). It's
useful for resetting a board to a clean state before starting new work or
testing.

The script connects to Planka through the MCP (Model Context Protocol) interface
and uses the kanban-mcp server to manage board operations. It provides a
confirmation prompt before deletion to prevent accidental data loss.

Constants
---------
BOARD_ID : str
    The ID of the Planka board to clean. Default is "1533859887128249584".

Examples
--------
Run the board cleaner:
    $ python scripts/clean_board.py

The script will:
    1. Connect to Planka at localhost:3333
    2. Show the number of cards found
    3. Ask for confirmation before deletion
    4. Remove all cards while keeping lists intact

Notes
-----
Requires the kanban-mcp server to be installed and accessible. The script
uses hardcoded Planka credentials for the demo environment.
"""

import asyncio
import json
import os
from typing import Dict, Any, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment
os.environ['PLANKA_BASE_URL'] = 'http://localhost:3333'
os.environ['PLANKA_AGENT_EMAIL'] = 'demo@demo.demo'
os.environ['PLANKA_AGENT_PASSWORD'] = 'demo'

# Configuration
BOARD_ID = "1533859887128249584"


async def clean_board_quick() -> None:
    """Remove all cards from the specified board while preserving lists.
    
    Connects to Planka via MCP, retrieves the board summary to count cards,
    prompts for user confirmation, then deletes all cards found. Lists and
    board structure remain intact after cleaning.
    
    The function performs the following steps:
        1. Initialize MCP client connection to kanban-mcp server
        2. Get board summary to count total cards
        3. If cards exist, prompt user for confirmation
        4. Delete each card individually with progress output
        5. Report final deletion count
    
    Returns
    -------
    None
    
    Side Effects
    ------------
    - Deletes all cards from the specified BOARD_ID
    - Prints progress messages to console
    - Requires user input for confirmation
    
    Notes
    -----
    The function uses exception handling to continue deletion even if
    individual card deletions fail, ensuring maximum cleanup.
    
    Examples
    --------
    >>> await clean_board_quick()
    🧹 Board Cleaner
    ========================================
    
    Found 15 cards to remove
    Continue? (y/n): y
    
    Deleting cards...
      ❌ Setup project structure
      ❌ Create API endpoints
      ...
    
    ✅ Cleaned 15 cards from the board
    """
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy()
    )
    
    print("🧹 Board Cleaner")
    print("=" * 40)
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get board summary first
            summary_result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {
                    "action": "get_board_summary",
                    "boardId": BOARD_ID,
                    "includeTaskDetails": False
                }
            )
            summary = json.loads(summary_result.content[0].text)
            
            total_cards = 0
            for lst in summary.get('lists', []):
                total_cards += len(lst.get('cards', []))
            
            if total_cards == 0:
                print("✅ Board is already clean!")
                return
            
            print(f"\nFound {total_cards} cards to remove")
            confirm = input("Continue? (y/n): ").strip().lower()
            
            if confirm != 'y':
                print("❌ Cancelled")
                return
            
            # Delete all cards
            print("\nDeleting cards...")
            deleted = 0
            
            for lst in summary.get('lists', []):
                for card in lst.get('cards', []):
                    try:
                        await session.call_tool(
                            "mcp_kanban_card_manager",
                            {"action": "delete", "id": card['id']}
                        )
                        deleted += 1
                        print(f"  ❌ {card['name']}")
                    except:
                        print(f"  ⚠️  Failed to delete: {card['name']}")
            
            print(f"\n✅ Cleaned {deleted} cards from the board")
            print("\nBoard is now empty and ready for new tasks!")


if __name__ == "__main__":
    asyncio.run(clean_board_quick())
