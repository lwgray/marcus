#!/usr/bin/env python3
"""Interactive project management tool for Planka.

This script provides an interactive CLI to help you select which projects
to keep or delete from your Planka board.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, List

import httpx
from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def _extract_text_from_result(result: Any) -> str:
    """Safely extract text from MCP result content.

    Parameters
    ----------
    result : Any
        The MCP result object containing content

    Returns
    -------
    str
        Extracted text or empty string if extraction fails
    """
    if hasattr(result, "content") and result.content:
        first_content = result.content[0]
        if hasattr(first_content, "text"):
            return str(first_content.text)
    return ""


def load_config() -> dict[str, Any]:
    """Load configuration from config_marcus.json.

    Returns
    -------
    dict[str, Any]
        Configuration dictionary with Planka credentials

    Raises
    ------
    FileNotFoundError
        If config file is not found
    """
    config_paths = [
        Path("config_marcus.json"),
        project_root / "config_marcus.json",
    ]

    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, "r") as f:
                config: dict[str, Any] = json.load(f)
                return config

    raise FileNotFoundError(
        "config_marcus.json not found. Please create it with Planka credentials."
    )


async def check_planka_availability(base_url: str) -> bool:
    """Check if Planka service is running.

    Parameters
    ----------
    base_url : str
        Planka base URL

    Returns
    -------
    bool
        True if service is available, False otherwise
    """
    try:
        async with httpx.AsyncClient() as client:
            await client.get(base_url, timeout=5.0)
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
    except Exception:
        return False


async def get_all_projects(session: ClientSession) -> List[dict[str, Any]]:
    """Retrieve all projects from Planka.

    Parameters
    ----------
    session : ClientSession
        Active MCP client session

    Returns
    -------
    List[dict[str, Any]]
        List of project dictionaries with id, name, and boards

    Raises
    ------
    Exception
        If projects cannot be retrieved
    """
    result = await session.call_tool(
        "mcp_kanban_project_board_manager",
        {"action": "get_projects", "page": 1, "perPage": 100},
    )

    if not result or not _extract_text_from_result(result):
        raise Exception("Failed to retrieve projects from MCP server")

    projects_data: dict[str, Any] = json.loads(_extract_text_from_result(result))
    items: list[dict[str, Any]] = projects_data.get("items", [])
    return items


async def get_boards_for_project(
    session: ClientSession, project_id: str
) -> List[dict[str, Any]]:
    """Get all boards for a specific project.

    Parameters
    ----------
    session : ClientSession
        Active MCP client session
    project_id : str
        Project ID

    Returns
    -------
    List[dict[str, Any]]
        List of boards for the project
    """
    result = await session.call_tool(
        "mcp_kanban_project_board_manager",
        {"action": "get_boards", "projectId": project_id},
    )

    if result and _extract_text_from_result(result):
        boards_data: Any = json.loads(_extract_text_from_result(result))
        if isinstance(boards_data, list):
            result_list: list[dict[str, Any]] = boards_data
            return result_list
        elif isinstance(boards_data, dict) and "items" in boards_data:
            items_list: list[dict[str, Any]] = boards_data["items"]
            return items_list

    return []


async def delete_project(
    session: ClientSession, project_id: str, project_name: str
) -> bool:
    """Delete a single project.

    Parameters
    ----------
    session : ClientSession
        Active MCP client session
    project_id : str
        ID of the project to delete
    project_name : str
        Name of the project (for logging)

    Returns
    -------
    bool
        True if deletion successful, False otherwise
    """
    try:
        await session.call_tool(
            "mcp_kanban_project_board_manager",
            {"action": "delete_project", "id": project_id},
        )
        print(f"   ✅ Deleted: {project_name}")
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to delete: {project_name} - {str(e)}")
        return False


def display_projects(projects: List[dict[str, Any]]) -> None:
    """Display projects with numbering for selection.

    Parameters
    ----------
    projects : List[dict[str, Any]]
        List of projects to display
    """
    print("\n📋 Available Projects:")
    print("=" * 70)
    for idx, project in enumerate(projects, 1):
        board_count = len(project.get("boards", []))
        board_text = "board" if board_count == 1 else "boards"
        print(f"  {idx:2d}. {project['name']}")
        print(f"      ID: {project['id']} | {board_count} {board_text}")
    print("=" * 70)


def parse_selection(selection: str, total: int) -> tuple[list[int], bool, str | None]:
    """Parse user selection input.

    Supports:
    - Single numbers: "1" or "5"
    - Ranges: "1-5" or "3-7"
    - Multiple selections: "1,3,5" or "1-3,7,9-11"
    - "all" to select all
    - "none" to select none

    Parameters
    ----------
    selection : str
        User input string
    total : int
        Total number of projects

    Returns
    -------
    tuple[list[int], bool, str | None]
        (list of selected indices, success flag, error message)
    """
    selection = selection.strip().lower()

    if selection == "all":
        return list(range(1, total + 1)), True, None

    if selection == "none" or selection == "":
        return [], True, None

    selected: set[int] = set()

    try:
        parts = selection.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                # Range
                start, end = part.split("-")
                start_idx = int(start.strip())
                end_idx = int(end.strip())

                if start_idx < 1 or end_idx > total or start_idx > end_idx:
                    return (
                        [],
                        False,
                        f"Invalid range: {part} (valid: 1-{total})",
                    )

                selected.update(range(start_idx, end_idx + 1))
            else:
                # Single number
                idx = int(part)
                if idx < 1 or idx > total:
                    return [], False, f"Invalid number: {idx} (valid: 1-{total})"
                selected.add(idx)

        return sorted(list(selected)), True, None

    except ValueError as e:
        return [], False, f"Invalid input format: {str(e)}"


def get_user_selection(
    projects: List[dict[str, Any]], mode: str
) -> List[dict[str, Any]]:
    """Get user's project selection interactively.

    Parameters
    ----------
    projects : List[dict[str, Any]]
        List of projects to choose from
    mode : str
        "delete" or "keep" mode

    Returns
    -------
    List[dict[str, Any]]
        List of selected projects
    """
    action_verb = "delete" if mode == "delete" else "keep"
    inverse_verb = "keep" if mode == "delete" else "delete"

    print(f"\n🎯 Select projects to {action_verb.upper()}:")
    print(f"   • Enter numbers: 1,3,5 or ranges: 1-5 or both: 1-3,7,9-11")
    print(f"   • Type 'all' to {action_verb} all projects")
    print(f"   • Type 'none' or press Enter to {action_verb} none")
    print()

    while True:
        selection = input(f"Projects to {action_verb} > ").strip()

        indices, success, error = parse_selection(selection, len(projects))

        if not success:
            print(f"❌ Error: {error}")
            print("Please try again.")
            continue

        if not indices:
            print(f"\n✅ No projects selected to {action_verb}.")
            return []

        # Show what was selected
        selected_projects = [projects[i - 1] for i in indices]
        print(
            f"\n📌 You selected {len(selected_projects)} project(s) to {action_verb}:"
        )
        for idx in indices:
            project = projects[idx - 1]
            print(f"   • {project['name']}")

        # Confirm
        confirm = (
            input(f"\n✓ Proceed to {action_verb} these projects? (y/n) > ")
            .strip()
            .lower()
        )
        if confirm in ["y", "yes"]:
            return selected_projects
        else:
            print("\n🔄 Let's try again...")
            continue


async def interactive_project_management() -> None:
    """Run interactive project management session."""
    print("🎯 Interactive Project Management Tool")
    print("=" * 70)

    # Load configuration
    print("\n📝 Loading configuration...")
    try:
        config = load_config()
        planka_config = config.get("planka", {})

        base_url = planka_config.get("base_url", "http://localhost:3333")
        email = planka_config.get("email", "demo@demo.demo")
        password = planka_config.get("password", "demo")

        # Set environment variables
        os.environ["PLANKA_BASE_URL"] = base_url
        os.environ["PLANKA_AGENT_EMAIL"] = email
        os.environ["PLANKA_AGENT_PASSWORD"] = password

        print(f"✅ Connected to: {base_url}")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

    # Check Planka availability
    print("\n🔍 Checking Planka availability...")
    if not await check_planka_availability(base_url):
        print(f"\n❌ ERROR: Planka service is not available at {base_url}")
        print("Please start the Planka service and try again.")
        sys.exit(1)

    print("✅ Planka is available")

    # Detect kanban-mcp path
    kanban_mcp_paths = [
        Path("/app/kanban-mcp/dist/index.js"),  # Docker
        project_root.parent / "kanban-mcp" / "dist" / "index.js",  # Sibling
        Path(os.environ.get("KANBAN_MCP_PATH", "")),  # Env var
    ]

    kanban_mcp_path = None
    for path in kanban_mcp_paths:
        if path.exists():
            kanban_mcp_path = str(path)
            break

    if not kanban_mcp_path:
        print("\n❌ ERROR: Cannot find kanban-mcp")
        print("Please set KANBAN_MCP_PATH environment variable")
        sys.exit(1)

    server_params = StdioServerParameters(
        command="node",
        args=[kanban_mcp_path],
        env=os.environ.copy(),
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get all projects
                print("\n📋 Fetching projects from Planka...")
                projects = await get_all_projects(session)

                if not projects:
                    print("\n✅ No projects found. Nothing to manage!")
                    return

                # Fetch boards for each project
                for project in projects:
                    project["boards"] = await get_boards_for_project(
                        session, project["id"]
                    )

                print(f"✅ Found {len(projects)} project(s)")

                # Display projects
                display_projects(projects)

                # Choose mode
                print("\n🔧 What would you like to do?")
                print("  1. Select projects to DELETE")
                print("  2. Select projects to KEEP (delete all others)")
                print("  3. Exit without changes")
                print()

                while True:
                    choice = input("Enter choice (1-3) > ").strip()

                    if choice == "3":
                        print("\n👋 Exiting without changes.")
                        return

                    if choice in ["1", "2"]:
                        break

                    print("❌ Invalid choice. Please enter 1, 2, or 3.")

                # Get selection based on mode
                if choice == "1":
                    # Delete mode
                    selected = get_user_selection(projects, "delete")
                    to_delete = selected
                    to_keep = [p for p in projects if p not in selected]
                else:
                    # Keep mode
                    selected = get_user_selection(projects, "keep")
                    to_keep = selected
                    to_delete = [p for p in projects if p not in selected]

                if not to_delete:
                    print("\n✅ No projects will be deleted.")
                    return

                # Show final summary
                print("\n" + "=" * 70)
                print("📊 SUMMARY")
                print("=" * 70)
                print(f"\n✅ Projects to KEEP ({len(to_keep)}):")
                if to_keep:
                    for project in to_keep:
                        print(f"   • {project['name']}")
                else:
                    print("   (none)")

                print(f"\n❌ Projects to DELETE ({len(to_delete)}):")
                for project in to_delete:
                    boards = project.get("boards", [])
                    board_count = len(boards)
                    print(f"   • {project['name']} ({board_count} boards)")

                print("\n" + "=" * 70)

                # Final confirmation
                print("\n⚠️  WARNING: This action cannot be undone!")
                print(f"You are about to DELETE {len(to_delete)} project(s).")
                confirm = input(
                    "\nType 'DELETE' to confirm (case-sensitive) > "
                ).strip()

                if confirm != "DELETE":
                    print("\n❌ Deletion cancelled.")
                    return

                # Perform deletions
                print(f"\n🗑️  Deleting {len(to_delete)} project(s)...")
                deleted = 0
                failed = 0

                for project in to_delete:
                    success = await delete_project(
                        session, project["id"], project["name"]
                    )
                    if success:
                        deleted += 1
                    else:
                        failed += 1

                # Final summary
                print("\n" + "=" * 70)
                print(f"✅ Successfully deleted {deleted} project(s)")
                if failed > 0:
                    print(f"⚠️  Failed to delete {failed} project(s)")
                print("🎯 Project management complete!")
                print("=" * 70)

    except json.JSONDecodeError as e:
        print("\n❌ ERROR: Invalid JSON response from MCP server")
        print(f"Details: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(interactive_project_management())
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
