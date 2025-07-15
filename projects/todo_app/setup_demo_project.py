#!/usr/bin/env python3
"""
Marcus Todo App Demo Setup Script

Automatically creates:
1. Planka project and board
2. Updates config_marcus.json with IDs
3. Creates todo app cards
4. Provides final setup instructions

One command to go from fresh Planka to working Marcus demo!
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters


# Colors for terminal output
class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_step(step_num, total_steps, message):
    """Print a formatted step message"""
    print(
        f"\n{Colors.BLUE}[{step_num}/{total_steps}]{Colors.END} {Colors.BOLD}{message}{Colors.END}"
    )


def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}❌ {message}{Colors.END}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")


async def check_planka_connection():
    """Test if we can connect to Planka"""
    print_step(1, 6, "Testing Planka connection...")

    # Set environment variables for Planka
    os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
    os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
    os.environ["PLANKA_AGENT_PASSWORD"] = "demo"  # pragma: allowlist secret

    # Check if kanban-mcp is available
    kanban_mcp_path = Path.home() / "dev" / "kanban-mcp" / "dist" / "index.js"
    if not kanban_mcp_path.exists():
        print_error(f"kanban-mcp not found at {kanban_mcp_path}")
        print("Please ensure kanban-mcp is cloned and built:")
        print("  cd ~/dev && git clone https://github.com/bradrisse/kanban-mcp.git")
        print("  cd kanban-mcp && npm install && npm run build")
        return False

    try:
        server_params = StdioServerParameters(
            command="node", args=[str(kanban_mcp_path)], env=os.environ.copy()
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print_success("Connected to Planka via kanban-mcp")
                return True

    except Exception as e:
        print_error(f"Cannot connect to Planka: {e}")
        print("Make sure Planka is running:")
        print("  cd ~/dev/kanban-mcp && docker-compose up -d")
        print("  Then visit http://localhost:3333 and login with demo@demo.demo / demo")
        return False


async def create_marcus_project():
    """Create Marcus Demo project and board"""
    print_step(2, 6, "Creating Marcus Demo project and board...")

    kanban_mcp_path = Path.home() / "dev" / "kanban-mcp" / "dist" / "index.js"
    server_params = StdioServerParameters(
        command="node", args=[str(kanban_mcp_path)], env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Check if "Marcus Todo Demo" project exists
            result = await session.call_tool(
                "mcp_kanban_project_board_manager",
                {"action": "get_projects", "page": 1, "perPage": 25},
            )

            projects_data = json.loads(result.content[0].text)
            existing_project = None

            for p in projects_data["items"]:
                if p["name"] == "Marcus Todo Demo":
                    existing_project = p
                    break

            if existing_project:
                print_success(
                    f"Found existing project: Marcus Todo Demo (ID: {existing_project['id']})"
                )
                project_id = existing_project["id"]

                # Find the board
                board_id = None
                if "boards" in projects_data.get("included", {}):
                    for board in projects_data["included"]["boards"]:
                        if board["projectId"] == project_id:
                            board_id = board["id"]
                            print_success(
                                f"Found existing board: {board['name']} (ID: {board_id})"
                            )
                            break

                if not board_id:
                    print_error("Project exists but no board found!")
                    return None, None

            else:
                # Create new project
                try:
                    result = await session.call_tool(
                        "mcp_kanban_project_board_manager",
                        {
                            "action": "create_project",
                            "name": "Marcus Todo Demo",
                            "description": "Demo project for Marcus AI agent coordination - Todo App",
                        },
                    )

                    project_data = json.loads(result.content[0].text)
                    project_id = project_data["id"]
                    print_success(
                        f"Created project: Marcus Todo Demo (ID: {project_id})"
                    )

                    # Create board in the project
                    result = await session.call_tool(
                        "mcp_kanban_project_board_manager",
                        {
                            "action": "create_board",
                            "projectId": project_id,
                            "name": "Todo App Development",
                            "description": "Todo app built by Marcus AI agents",
                        },
                    )

                    board_data = json.loads(result.content[0].text)
                    board_id = board_data["id"]
                    print_success(
                        f"Created board: Todo App Development (ID: {board_id})"
                    )

                except Exception as e:
                    print_error(f"Failed to create project/board: {e}")
                    return None, None

            return project_id, board_id


def update_config_file(project_id, board_id):
    """Update config_marcus.json with the project and board IDs"""
    print_step(3, 6, "Updating config_marcus.json...")

    marcus_root = Path(__file__).parent.parent.parent
    config_path = marcus_root / "config_marcus.json"
    example_config_path = marcus_root / "config_marcus.json.example"

    # Load config (prefer existing, fallback to example)
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
        print_success("Loaded existing config_marcus.json")
    elif example_config_path.exists():
        with open(example_config_path, "r") as f:
            config = json.load(f)
        print_success("Loaded config_marcus.json.example as template")
    else:
        print_error("No config file found!")
        return False

    # Update the IDs
    config["project_id"] = project_id
    config["board_id"] = board_id
    config["project_name"] = "Marcus Todo Demo"
    config["auto_find_board"] = False

    # Ensure Planka settings are correct
    config["kanban"] = {"provider": "planka"}
    config["planka"] = {
        "base_url": "http://localhost:3333",
        "email": "demo@demo.demo",
        "password": "demo",
    }

    # Save the updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print_success(f"Updated config_marcus.json with:")
    print(f"  - project_id: {project_id}")
    print(f"  - board_id: {board_id}")
    return True


async def create_todo_cards(board_id):
    """Create the todo app cards in the board"""
    print_step(4, 6, "Creating todo app cards...")

    # Load card data
    cards_file = Path(__file__).parent / "todo_app_planka_cards.json"
    with open(cards_file, "r") as f:
        todo_data = json.load(f)

    kanban_mcp_path = Path.home() / "dev" / "kanban-mcp" / "dist" / "index.js"
    server_params = StdioServerParameters(
        command="node", args=[str(kanban_mcp_path)], env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Get or create lists
            result = await session.call_tool(
                "mcp_kanban_list_manager", {"action": "get_all", "boardId": board_id}
            )

            lists = json.loads(result.content[0].text)

            # Create standard lists if they don't exist
            list_names = ["Backlog", "TODO", "In Progress", "Review", "Done"]
            list_ids = {}

            existing_lists = {l["name"]: l["id"] for l in lists}

            for i, list_name in enumerate(list_names):
                if list_name in existing_lists:
                    list_ids[list_name] = existing_lists[list_name]
                else:
                    # Create missing list
                    result = await session.call_tool(
                        "mcp_kanban_list_manager",
                        {
                            "action": "create",
                            "boardId": board_id,
                            "name": list_name,
                            "position": i,
                        },
                    )
                    new_list = json.loads(result.content[0].text)
                    list_ids[list_name] = new_list["id"]

            print_success(f"Prepared {len(list_ids)} lists")

            # Clear existing cards in Backlog
            backlog_id = list_ids["Backlog"]
            result = await session.call_tool(
                "mcp_kanban_card_manager", {"action": "get_all", "listId": backlog_id}
            )

            existing_cards = []
            if result.content and result.content[0].text.strip():
                try:
                    existing_cards = json.loads(result.content[0].text)
                    if not isinstance(existing_cards, list):
                        existing_cards = []
                except:
                    existing_cards = []

            for card in existing_cards:
                await session.call_tool(
                    "mcp_kanban_card_manager",
                    {"action": "delete", "cardId": card["id"]},
                )

            if existing_cards:
                print_success(f"Cleared {len(existing_cards)} existing cards")

            # Create cards with minimal information
            cards_created = 0
            total_cards = len(todo_data["cards"])

            for card_data in todo_data["cards"]:
                try:
                    # Create basic card
                    result = await session.call_tool(
                        "mcp_kanban_card_manager",
                        {
                            "action": "create",
                            "listId": backlog_id,
                            "name": card_data["title"],
                            "description": (
                                card_data["description"][:500] + "..."
                                if len(card_data["description"]) > 500
                                else card_data["description"]
                            ),
                        },
                    )

                    cards_created += 1
                    if cards_created % 5 == 0:
                        print(f"  Created {cards_created}/{total_cards} cards...")

                except Exception as e:
                    print_warning(f"Failed to create card '{card_data['title']}': {e}")

            print_success(f"Created {cards_created}/{total_cards} todo app cards!")
            return cards_created > 0


def print_next_steps(project_id, board_id):
    """Print final instructions for the user"""
    print_step(5, 6, "Setup complete! Next steps:")

    print(f"\n{Colors.GREEN}🎉 Marcus Todo Demo Setup Complete!{Colors.END}\n")

    print(f"{Colors.BOLD}Your Marcus Configuration:{Colors.END}")
    print(f"  📋 Project: Marcus Todo Demo (ID: {project_id})")
    print(f"  📋 Board: Todo App Development (ID: {board_id})")
    print(f"  📝 Config: Updated config_marcus.json")

    print(f"\n{Colors.BOLD}Ready to Run Marcus Demo:{Colors.END}")
    print(f"  1. Start Marcus MCP server:")
    print(f"     {Colors.BLUE}cd ~/dev/marcus{Colors.END}")
    print(f"     {Colors.BLUE}python src/marcus_mcp/server.py{Colors.END}")

    print(f"\n  2. In Claude Code, add Marcus MCP:")
    print(
        f"     {Colors.BLUE}claude mcp add python ~/dev/marcus/src/marcus_mcp/server.py{Colors.END}"
    )

    print(f"\n  3. Copy the agent prompt:")
    print(f"     {Colors.BLUE}cat ~/dev/marcus/prompts/Agent_prompt.md{Colors.END}")
    print(f"     (Copy this content as your Claude Code system prompt)")

    print(f"\n  4. Start the demo in Claude Code:")
    print(
        f'     {Colors.GREEN}"Register with Marcus and start working on the todo app"{Colors.END}'
    )

    print(f"\n{Colors.BOLD}Watch the Magic:{Colors.END}")
    print(f"  🌐 Planka Board: {Colors.BLUE}http://localhost:3333{Colors.END}")
    print(
        f"  👀 Watch tasks move through: Backlog → TODO → In Progress → Review → Done"
    )
    print(f"  🤖 AI agents will automatically:")
    print(f"      - Pick up tasks from the backlog")
    print(f"      - Report progress as they work")
    print(f"      - Move cards through the workflow")
    print(f"      - Share context between agents")

    print(f"\n{Colors.YELLOW}Need Help?{Colors.END}")
    print(f"  📖 Full docs: ~/dev/marcus/docs/")
    print(f"  🔧 API reference: ~/dev/marcus/docs/api/")
    print(f"  🏗️  Architecture: ~/dev/marcus/docs/systems/")


async def main():
    """Main setup workflow"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("🏛️  Marcus Todo Demo Setup")
    print("=" * 50)
    print("Setting up your 5-minute Marcus demo!")
    print(f"{Colors.END}")

    # Step 1: Check Planka connection
    if not await check_planka_connection():
        sys.exit(1)

    # Step 2: Create project and board
    project_id, board_id = await create_marcus_project()
    if not project_id or not board_id:
        print_error("Failed to create project/board")
        sys.exit(1)

    # Step 3: Update config
    if not update_config_file(project_id, board_id):
        sys.exit(1)

    # Step 4: Create cards
    if not await create_todo_cards(board_id):
        print_error("Failed to create cards")
        sys.exit(1)

    # Step 5: Print next steps
    print_next_steps(project_id, board_id)

    print_step(6, 6, "Demo ready! 🚀")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1)
