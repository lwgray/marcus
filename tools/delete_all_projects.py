#!/usr/bin/env python3
"""Delete all projects from Planka.

WARNING: This is a destructive operation that will permanently delete
all projects and their associated boards, cards, and data.
"""

import asyncio
import json
import os
import sys
from typing import Any, List

import httpx
from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

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


def confirm_deletion(project_count: int) -> bool:
    """Prompt user to confirm deletion of all projects.

    Parameters
    ----------
    project_count : int
        Number of projects that will be deleted

    Returns
    -------
    bool
        True if user confirms, False otherwise
    """
    print(f"\n⚠️  WARNING: You are about to delete {project_count} projects!")
    print("This action cannot be undone and will delete:")
    print("  • All projects")
    print("  • All boards within projects")
    print("  • All cards/tasks")
    print("  • All associated data")
    print("\nType 'DELETE ALL' to confirm (case-sensitive): ", end="")

    confirmation = input().strip()
    return confirmation == "DELETE ALL"


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


async def delete_all_projects(skip_confirmation: bool = False) -> None:
    """Delete all projects from Planka.

    Parameters
    ----------
    skip_confirmation : bool, optional
        If True, skip confirmation prompt (for automated use), by default False

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

                print(f"✅ Found {len(projects)} projects:")
                for project in projects:
                    print(f"   • {project['name']} (ID: {project['id']})")

                # Confirm deletion
                if not skip_confirmation:
                    if not confirm_deletion(len(projects)):
                        print("\n❌ Deletion cancelled by user")
                        return

                # Delete all projects
                print(f"\n🗑️  Deleting {len(projects)} projects...")
                deleted = 0
                failed = 0

                for project in projects:
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

    try:
        asyncio.run(delete_all_projects(skip_confirmation=skip_confirmation))
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)
