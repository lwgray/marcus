#!/usr/bin/env python3
"""
Get all task IDs from the Task Master Test board
"""

import asyncio
import json
import os
import sys

import httpx
from mcp.client.stdio import stdio_client

from mcp import ClientSession, StdioServerParameters

# Add parent directory to Python path for imports
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.core.error_framework import (
    ErrorContext,
    KanbanIntegrationError,
    RemediationSuggestion,
    ServiceUnavailableError,
)

# Set environment
os.environ["PLANKA_BASE_URL"] = "http://localhost:3333"
os.environ["PLANKA_AGENT_EMAIL"] = "demo@demo.demo"
os.environ["PLANKA_AGENT_PASSWORD"] = "demo"


async def check_board_availability():
    """Check if the Kanban board service is running"""
    base_url = os.environ.get("PLANKA_BASE_URL", "http://localhost:3333")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(base_url, timeout=5.0)
            return True
    except (httpx.ConnectError, httpx.TimeoutException):
        return False
    except Exception:
        return False


async def get_board_task_ids():
    """Get all task IDs from the Task Master Test board"""

    server_params = StdioServerParameters(
        command="node",
        args=["/Users/lwgray/dev/kanban-mcp/dist/index.js"],
        env=os.environ.copy(),
    )

    print("📋 Task ID Reader for Task Master Test")
    print("=" * 50)

    # Check if board is available first
    print("\n🔍 Checking Kanban board availability...")
    board_available = await check_board_availability()

    if not board_available:
        base_url = os.environ.get("PLANKA_BASE_URL", "http://localhost:3333")
        raise ServiceUnavailableError(
            service_name="Planka Kanban Board",
            context=ErrorContext(
                operation="get_board_task_ids",
                integration_name="planka",
                integration_state={"url": base_url, "status": "unreachable"},
            ),
            remediation=RemediationSuggestion(
                immediate_action=f"Start the Planka Kanban board service on {base_url}",
                long_term_solution="Add health checks to verify board is running before operations",
                fallback_strategy="Check if Docker containers are running with 'docker ps'",
                escalation_path="Run 'docker-compose up -d' in the Kanban board directory",
            ),
        )

    print("✅ Kanban board is available")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Find Task Master Test project
                print("\n📋 Finding Task Master Test project...")
                result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {"action": "get_projects", "page": 1, "perPage": 25},
                )

                # Check if result has content before parsing
                if not result or not result.content or not result.content[0].text:
                    raise KanbanIntegrationError(
                        board_name="Task Master Test",
                        operation="get_projects",
                        context=ErrorContext(
                            operation="get_board_task_ids", integration_name="planka_mcp"
                        ),
                        remediation=RemediationSuggestion(
                            immediate_action="Check MCP server logs for errors",
                            long_term_solution="Ensure MCP server is properly configured",
                            fallback_strategy="Restart the MCP server and retry",
                        ),
                    )

                projects_data = json.loads(result.content[0].text)
                project_id = None
                board_id = None

                for project in projects_data["items"]:
                    if project["name"] == "Task Master Test":
                        project_id = project["id"]
                        print(f"✅ Found project: {project['name']} (ID: {project_id})")
                        break

                if not project_id:
                    print("❌ Task Master Test project not found!")
                    return []

                # Find the board
                if "boards" in projects_data.get("included", {}):
                    for board in projects_data["included"]["boards"]:
                        if board["projectId"] == project_id:
                            board_id = board["id"]
                            print(f"✅ Found board: {board['name']} (ID: {board_id})")
                            break

                if not board_id:
                    print("❌ No board found for Task Master Test!")
                    return []

                # Get board summary with task details
                summary_result = await session.call_tool(
                    "mcp_kanban_project_board_manager",
                    {
                        "action": "get_board_summary",
                        "boardId": board_id,
                        "includeTaskDetails": True,  # Include task details to get task IDs
                    },
                )
                summary = json.loads(summary_result.content[0].text)

                # Collect all task IDs
                all_task_ids = []
                cards_by_list = {}

                for lst in summary.get("lists", []):
                    list_name = lst["name"]
                    cards_by_list[list_name] = []
                    
                    for card in lst.get("cards", []):
                        card_info = {
                            "card_id": card["id"],
                            "card_name": card["name"],
                            "list": list_name,
                            "task_ids": []
                        }
                        
                        # Extract task IDs from card description or other fields
                        # The task ID might be in the description, name, or a custom field
                        if "description" in card and card["description"]:
                            # Look for patterns like "Task ID: XXX" or "task-XXX" in description
                            import re
                            task_id_patterns = [
                                r'[Tt]ask[-\s]?[Ii][Dd][:=\s]+([^\s,]+)',
                                r'task[-_](\d+)',
                                r'TASK-(\d+)',
                                r'#(\d+)'
                            ]
                            
                            for pattern in task_id_patterns:
                                matches = re.findall(pattern, card["description"])
                                card_info["task_ids"].extend(matches)
                        
                        # Also check the card name for task IDs
                        if card["name"]:
                            import re
                            # Common patterns in card names
                            name_patterns = [
                                r'^(?:Task[-\s]?)?(\d+)[:.\s-]',  # "Task 1:", "1.", "1 -"
                                r'\[(\d+)\]',  # "[123]"
                                r'#(\d+)',  # "#123"
                                r'task[-_](\d+)',  # "task-123", "task_123"
                            ]
                            
                            for pattern in name_patterns:
                                matches = re.findall(pattern, card["name"], re.IGNORECASE)
                                card_info["task_ids"].extend(matches)
                        
                        # Remove duplicates
                        card_info["task_ids"] = list(set(card_info["task_ids"]))
                        
                        cards_by_list[list_name].append(card_info)
                        all_task_ids.extend(card_info["task_ids"])

                # Display results
                print(f"\n📊 Board Summary:")
                print(f"Total cards: {sum(len(cards) for cards in cards_by_list.values())}")
                print(f"Total task IDs found: {len(set(all_task_ids))}")
                
                print("\n📋 Cards by List:")
                for list_name, cards in cards_by_list.items():
                    print(f"\n{list_name} ({len(cards)} cards):")
                    for card in cards:
                        task_ids_str = f" [Task IDs: {', '.join(card['task_ids'])}]" if card['task_ids'] else ""
                        print(f"  • {card['card_name']} (ID: {card['card_id']}){task_ids_str}")
                
                # Return summary data
                return {
                    "board_id": board_id,
                    "total_cards": sum(len(cards) for cards in cards_by_list.values()),
                    "unique_task_ids": list(set(all_task_ids)),
                    "cards_by_list": cards_by_list,
                    "all_cards": [
                        card 
                        for cards in cards_by_list.values() 
                        for card in cards
                    ]
                }

    except json.JSONDecodeError as e:
        raise KanbanIntegrationError(
            board_name="Task Master Test",
            operation="parse_response",
            context=ErrorContext(
                operation="get_board_task_ids",
                integration_name="planka_mcp",
                custom_context={
                    "error": str(e),
                    "response": str(
                        result.content[0].text
                        if result and result.content
                        else "No content"
                    ),
                },
            ),
            remediation=RemediationSuggestion(
                immediate_action="Check if MCP server is returning valid JSON",
                long_term_solution="Add response validation to MCP client",
                fallback_strategy="Enable debug logging to see raw responses",
            ),
            cause=e,
        )
    except Exception as e:
        # Re-raise Marcus errors as-is
        if isinstance(e, (ServiceUnavailableError, KanbanIntegrationError)):
            raise

        # Wrap other errors
        raise KanbanIntegrationError(
            board_name="Task Master Test",
            operation="get_board_task_ids",
            context=ErrorContext(
                operation="get_board_task_ids",
                integration_name="planka",
                custom_context={"error": str(e), "error_type": type(e).__name__},
            ),
            remediation=RemediationSuggestion(
                immediate_action="Check logs for detailed error information",
                long_term_solution="Improve error handling and logging",
                fallback_strategy="Try accessing the board manually through the UI",
            ),
            cause=e,
        )


def display_marcus_error(error):
    """Display Marcus error in a user-friendly format"""
    print("\n❌ ERROR DETECTED")
    print("=" * 50)
    print(f"Error: {error.message}")
    print(f"Severity: {error.severity.value}")

    if error.remediation:
        print("\n📋 REMEDIATION STEPS:")
        if error.remediation.immediate_action:
            print(f"• Immediate: {error.remediation.immediate_action}")
        if error.remediation.fallback_strategy:
            print(f"• Fallback: {error.remediation.fallback_strategy}")
        if error.remediation.long_term_solution:
            print(f"• Long-term: {error.remediation.long_term_solution}")
        if error.remediation.escalation_path:
            print(f"• Escalation: {error.remediation.escalation_path}")

    if error.context and error.context.integration_state:
        print("\n🔍 CONTEXT:")
        for key, value in error.context.integration_state.items():
            print(f"• {key}: {value}")

    print("\n" + "=" * 50)


if __name__ == "__main__":
    try:
        result = asyncio.run(get_board_task_ids())
        
        # Print summary of unique task IDs
        if result and result["unique_task_ids"]:
            print(f"\n🎯 Unique Task IDs found: {', '.join(result['unique_task_ids'])}")
        else:
            print("\n⚠️  No task IDs found in card names or descriptions")
            
    except (ServiceUnavailableError, KanbanIntegrationError) as e:
        display_marcus_error(e)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)