#!/usr/bin/env python3
"""Delete projects from Planka.

Supports two modes:
1. Delete all projects (default)
2. Select specific projects to delete (--select)

WARNING: This is a destructive operation that will permanently delete
projects and their associated boards, cards, and data.
"""

import asyncio
import json
import os
import sys
from typing import Any, List

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Set environment - demo credentials for local development only
os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
os.environ["PLANKA_AGENT_PASSWORD"] = "demo"  # nosec B105  # pragma: allowlist secret


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


async def check_board_availability() -> bool:
    """Check if the Kanban board service is running.

    Returns
    -------
    bool
        True if service is available, False otherwise
    """
    base_url = os.environ.get("PLANKA_BASE_URL", "http://localhost:3333")

    try:
        async with httpx.AsyncClient() as client:
            await client.get(base_url, timeout=5.0)
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
    except Exception:
        return False


def select_projects_to_delete(projects: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Allow user to select which projects to delete.

    Parameters
    ----------
    projects : List[dict[str, Any]]
        List of all available projects

    Returns
    -------
    List[dict[str, Any]]
        List of selected projects to delete
    """
    print("\n📋 Select projects to delete:")
    print("=" * 50)
    for idx, project in enumerate(projects, 1):
        print(f"  {idx}. {project['name']} (ID: {project['id']})")

    print("\n" + "=" * 50)
    print("Selection options:")
    print("  • Enter numbers: 1 3 5")
    print("  • Enter ranges: 1-3")
    print("  • Combine: 1 3-5 7")
    print("  • Enter 'all' to delete all projects")
    print("  • Enter 'cancel' or 'q' to quit")
    print("=" * 50)

    while True:
        user_input = input("\nYour selection: ").strip().lower()

        if user_input in ["cancel", "q", "quit", "exit"]:
            return []

        if user_input == "all":
            return projects

        try:
            selected_indices: set[int] = set()
            parts = user_input.split()

            for part in parts:
                if "-" in part:
                    # Handle range (e.g., "1-3")
                    start, end = part.split("-")
                    start_idx = int(start)
                    end_idx = int(end)
                    if start_idx < 1 or end_idx > len(projects):
                        raise ValueError(
                            f"Range {part} is out of bounds (1-{len(projects)})"
                        )
                    selected_indices.update(range(start_idx, end_idx + 1))
                else:
                    # Handle single number
                    idx = int(part)
                    if idx < 1 or idx > len(projects):
                        raise ValueError(
                            f"Number {idx} is out of bounds (1-{len(projects)})"
                        )
                    selected_indices.add(idx)

            # Convert to project list
            selected_projects = [projects[idx - 1] for idx in sorted(selected_indices)]

            if not selected_projects:
                print("❌ No projects selected. Please try again.")
                continue

            # Show selection for confirmation
            print(f"\n✅ You selected {len(selected_projects)} project(s):")
            for project in selected_projects:
                print(f"   • {project['name']}")

            return selected_projects

        except ValueError as e:
            print(f"❌ Invalid input: {e}")
            print("Please try again.")
            continue


def confirm_deletion(projects: List[dict[str, Any]]) -> bool:
    """Prompt user to confirm deletion of selected projects.

    Parameters
    ----------
    projects : List[dict[str, Any]]
        List of projects that will be deleted

    Returns
    -------
    bool
        True if user confirms, False otherwise
    """
    project_count = len(projects)
    print(f"\n⚠️  WARNING: You are about to delete {project_count} project(s)!")
    print("This action cannot be undone and will delete:")
    print("  • Selected projects")
    print("  • All boards within projects")
    print("  • All cards/tasks")
    print("  • All associated data")
    print("\nType 'DELETE' to confirm (case-sensitive): ", end="")

    confirmation = input().strip()
    return confirmation == "DELETE"


async def get_all_projects(session: ClientSession) -> List[dict[str, Any]]:
    """Retrieve all projects from Planka.

    Parameters
    ----------
    session : ClientSession
        Active MCP client session

    Returns
    -------
    List[dict]
        List of project dictionaries with id and name

    Raises
    ------
    Exception
        If projects cannot be retrieved
    """
    print("\n📋 Fetching all projects...")
    result = await session.call_tool(
        "mcp_kanban_project_board_manager",
        {"action": "get_projects", "page": 1, "perPage": 100},
    )

    if not result or not _extract_text_from_result(result):
        raise Exception("Failed to retrieve projects from MCP server")

    projects_data = json.loads(_extract_text_from_result(result))
    items: List[dict[str, Any]] = projects_data.get("items", [])
    return items


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
        print(f"   ✅ Deleted: {project_name} (ID: {project_id})")
        return True
    except Exception as e:
        print(f"   ⚠️  Failed to delete: {project_name} - {str(e)}")
        return False


async def delete_all_projects(
    skip_confirmation: bool = False, select_mode: bool = False
) -> None:
    """Delete projects from Planka.

    Parameters
    ----------
    skip_confirmation : bool, optional
        If True, skip confirmation prompt (for automated use), by default False
    select_mode : bool, optional
        If True, allow user to select specific projects to delete, by default False

    Raises
    ------
    Exception
        If Planka service is not available or deletion operations fail
    """
    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy(),
    )

    print("🗑️  Project Deletion Tool")
    print("=" * 50)

    # Check if board is available first
    print("\n🔍 Checking Planka availability...")
    board_available = await check_board_availability()

    if not board_available:
        base_url = os.environ.get("PLANKA_BASE_URL", "http://localhost:3333")
        print(f"\n❌ ERROR: Planka service is not available at {base_url}")
        print("Please start the Planka service and try again.")
        print("Hint: Check if Docker containers are running with 'docker ps'")
        sys.exit(1)

    print("✅ Planka is available")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get all projects
                projects = await get_all_projects(session)

                if not projects:
                    print("\n✅ No projects found. Nothing to delete!")
                    return

                print(f"✅ Found {len(projects)} projects")

                # Select projects to delete
                if select_mode:
                    projects_to_delete = select_projects_to_delete(projects)
                    if not projects_to_delete:
                        print("\n❌ Operation cancelled by user")
                        return
                else:
                    # Show all projects when deleting all
                    for project in projects:
                        print(f"   • {project['name']} (ID: {project['id']})")
                    projects_to_delete = projects

                # Confirm deletion
                if not skip_confirmation:
                    if not confirm_deletion(projects_to_delete):
                        print("\n❌ Deletion cancelled by user")
                        return

                # Delete selected projects
                print(f"\n🗑️  Deleting {len(projects_to_delete)} project(s)...")
                deleted = 0
                failed = 0

                for project in projects_to_delete:
                    success = await delete_project(
                        session, project["id"], project["name"]
                    )
                    if success:
                        deleted += 1
                    else:
                        failed += 1

                # Summary
                print("\n" + "=" * 50)
                print(f"✅ Successfully deleted {deleted} projects")
                if failed > 0:
                    print(f"⚠️  Failed to delete {failed} projects")
                print("🎯 Planka cleanup complete!")

    except json.JSONDecodeError as e:
        print("\n❌ ERROR: Invalid JSON response from MCP server")
        print(f"Details: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    skip_confirmation = "--yes" in sys.argv or "-y" in sys.argv
    select_mode = "--select" in sys.argv or "-s" in sys.argv

    # Show usage if --help
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Project Deletion Tool")
        print("\nUsage:")
        print("  python delete_all_projects.py [OPTIONS]")
        print("\nOptions:")
        print("  -s, --select    Select specific projects to delete (interactive)")
        print("  -y, --yes       Skip confirmation prompt (delete all)")
        print("  -h, --help      Show this help message")
        print("\nExamples:")
        print("  # Interactive selection")
        print("  python delete_all_projects.py --select")
        print("\n  # Delete all without confirmation")
        print("  python delete_all_projects.py --yes")
        print("\n  # Default: delete all with confirmation")
        print("  python delete_all_projects.py")
        sys.exit(0)

    try:
        asyncio.run(
            delete_all_projects(
                skip_confirmation=skip_confirmation, select_mode=select_mode
            )
        )
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
