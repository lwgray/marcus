#!/usr/bin/env python3
"""
Example: Using the get_optimal_agent_count MCP Tool.

This demonstrates the complete workflow:
1. Connect to Marcus using Inspector client
2. Authenticate as admin
3. List or create a project
4. Get optimal agent count for the project
5. Use the recommendations to scale agents

Prerequisites
-------------
- Marcus server must be running
- For HTTP mode: python -m src.marcus_mcp.server --http
- For stdio mode: No prerequisites (spawns isolated instance)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def pretty_print(label: str, result: Any) -> None:
    """
    Pretty print MCP tool results.

    Parameters
    ----------
    label : str
        Label to display before the result
    result : Any
        Result object to print
    """
    print(f"\n{label}")
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        try:
            data = json.loads(text)
            print(json.dumps(data, indent=2))
        except (json.JSONDecodeError, AttributeError):
            print(text)
    else:
        print(result)


async def demo_optimal_agents_stdio() -> None:
    """
    Demo: Calculate optimal agents using stdio connection.

    This spawns an isolated Marcus instance for testing.
    Best for: Development, testing, experimentation
    """
    print("\n" + "=" * 70)
    print("🎯 OPTIMAL AGENT COUNT DEMO (Stdio Mode)")
    print("=" * 70)
    print("\nThis demo shows how to:")
    print("1. Connect to Marcus")
    print("2. Create or select a project")
    print("3. Calculate optimal agent count")
    print("4. Use the recommendations")
    print("=" * 70)

    client = Inspector(connection_type="stdio")

    try:
        print("\n📡 Starting Marcus instance via stdio...")
        async with client.connect() as session:
            # Step 1: Authenticate as admin (required for full access)
            print("\n🔐 Step 1: Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "optimal-agent-test",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"test_mode": True, "workflow": "optimal_agents"},
                },
            )
            print("✅ Authenticated successfully")

            # Step 2: List available projects
            print("\n📂 Step 2: Listing available projects...")
            projects_result = await session.call_tool("list_projects", arguments={})
            pretty_print("Available projects:", projects_result)

            projects_text = projects_result.content[0].text
            projects_data = json.loads(projects_text)

            # Step 3: Create or select a project
            if not projects_data or len(projects_data) == 0:
                print("\n📋 Step 3: No projects found, creating sample project...")
                create_result = await session.call_tool(
                    "create_project",
                    arguments={
                        "description": (
                            "Build a web scraping tool with these features: "
                            "1. Configure target URLs and selectors "
                            "2. Implement parallel scraping with rate limiting "
                            "3. Add data validation and cleaning "
                            "4. Create storage backends (JSON, CSV, database) "
                            "5. Build CLI interface with progress reporting "
                            "6. Add comprehensive error handling and retries "
                            "7. Write unit and integration tests "
                            "Use Python with requests, BeautifulSoup4, and SQLAlchemy."
                        ),
                        "project_name": "Web Scraper",
                        "options": {
                            "mode": "new_project",
                            "complexity": "production",
                            "planka_project_name": "Web Scraper",
                            "planka_board_name": "Development Board",
                        },
                    },
                )
                pretty_print("✅ Project created:", create_result)

                create_data = json.loads(create_result.content[0].text)
                if not create_data.get("success"):
                    print(f"\n❌ Failed to create project: {create_data.get('error')}")
                    return

                total_tasks = create_data.get("tasks_created", 0)
                print(f"\n📊 Project created with {total_tasks} tasks")
            else:
                print(
                    f"\n📋 Step 3: Found {len(projects_data)} existing project(s), "
                    "using current project..."
                )
                current_result = await session.call_tool(
                    "get_current_project", arguments={}
                )
                pretty_print("Current project:", current_result)

            # Step 4: Calculate optimal agent count
            print("\n" + "=" * 70)
            print("🎯 Step 4: Calculating optimal agent count...")
            print("=" * 70)

            # Call the get_optimal_agent_count tool
            optimal_result = await session.call_tool(
                "get_optimal_agent_count",
                arguments={"include_details": True},  # Get detailed analysis
            )
            pretty_print("📊 Optimal Agent Analysis:", optimal_result)

            # Parse and display recommendations
            optimal_text = optimal_result.content[0].text
            optimal_data = json.loads(optimal_text)

            if optimal_data.get("success"):
                print("\n" + "=" * 70)
                print("💡 RECOMMENDATIONS")
                print("=" * 70)

                optimal = optimal_data["optimal_agents"]
                critical_path = optimal_data["critical_path_hours"]
                efficiency = optimal_data["efficiency_gain_percent"]
                max_parallel = optimal_data["max_parallelism"]
                single_agent_hours = optimal_data["single_agent_hours"]
                multi_agent_hours = optimal_data["estimated_completion_hours"]

                print(f"\n🎯 Recommended Agents: {optimal}")
                print(f"📊 Critical Path: {critical_path} hours")
                print(
                    f"🔄 Max Parallelism: {max_parallel} tasks can run simultaneously"
                )
                print(
                    f"⏱️  Time Savings: {single_agent_hours}h → {multi_agent_hours}h "
                    f"({efficiency}% faster)"
                )

                if optimal == 1:
                    print("\n💡 Project has sequential dependencies.")
                    print("   → Adding more agents won't speed up completion")
                    print("   → Stick with 1 agent")
                elif optimal > 1:
                    print("\n💡 Project has parallel work opportunities!")
                    print(f"   → Recommended: {optimal} agents")
                    speedup_msg = (
                        f"   → Expected speedup: {efficiency}% faster "
                        f"than single agent"
                    )
                    print(speedup_msg)
                    print(f"   → Completion time: {multi_agent_hours} hours")

                # Show parallel opportunities if available
                if "parallel_opportunities" in optimal_data:
                    print("\n🔀 Parallel Opportunities:")
                    print("-" * 70)
                    for opp in optimal_data["parallel_opportunities"]:
                        opp_msg = (
                            f"   At {opp['time']}h: {opp['task_count']} "
                            f"tasks can run in parallel"
                        )
                        print(opp_msg)
                        print(f"      Tasks: {', '.join(opp['tasks'])}")

                print("\n" + "=" * 70)

            else:
                error_msg = (
                    f"\n❌ Failed to calculate optimal agents: "
                    f"{optimal_data.get('error')}"
                )
                print(error_msg)
                if "suggestion" in optimal_data:
                    print(f"💡 Suggestion: {optimal_data['suggestion']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


async def demo_optimal_agents_http() -> None:
    """
    Demo: Calculate optimal agents using HTTP connection.

    Connects to a running Marcus server.
    Best for: Production use, multiple workers, shared state
    """
    print("\n" + "=" * 70)
    print("🎯 OPTIMAL AGENT COUNT DEMO (HTTP Mode)")
    print("=" * 70)

    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"

    try:
        print(f"\n📡 Connecting to Marcus at {url}...")
        async with client.connect(url=url) as session:
            # Step 1: Authenticate
            print("\n🔐 Step 1: Authenticating as admin...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": "optimal-agent-http",
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"connection": "http", "workflow": "optimal_agents"},
                },
            )
            print("✅ Authenticated")

            # Step 2: Get current project
            print("\n📂 Step 2: Getting current project...")
            current_result = await session.call_tool(
                "get_current_project", arguments={}
            )
            pretty_print("Current project:", current_result)

            # Step 3: Calculate optimal agents
            print("\n🎯 Step 3: Calculating optimal agent count...")
            optimal_result = await session.call_tool(
                "get_optimal_agent_count",
                arguments={"include_details": True},
            )
            pretty_print("📊 Optimal Agent Analysis:", optimal_result)

            # Parse recommendations
            optimal_text = optimal_result.content[0].text
            optimal_data = json.loads(optimal_text)

            if optimal_data.get("success"):
                print("\n💡 Use these recommendations to:")
                print("   1. Scale up/down your agent pool")
                print("   2. Report resource constraints via report_blocker")
                print("   3. Optimize project scheduling")
                recommended_msg = (
                    f"\n🎯 Recommended Agents: "
                    f"{optimal_data['optimal_agents']} "
                    f"({optimal_data['efficiency_gain_percent']}% "
                    f"efficiency gain)"
                )
                print(recommended_msg)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure Marcus server is running in HTTP mode:")
        print("   python -m src.marcus_mcp.server --http")
        import traceback

        traceback.print_exc()


async def demo_agent_usage() -> None:
    """
    Demo: How an agent would use optimal agent calculation.

    Shows how autonomous agents can self-assess resource needs
    and report blockers when under-resourced.
    """
    print("\n" + "=" * 70)
    print("🤖 AGENT USAGE PATTERN")
    print("=" * 70)
    print("\nHow autonomous agents use get_optimal_agent_count:\n")

    print(
        """
1. AGENT STARTUP - Check resource needs
   ```python
   async def agent_startup():
       result = await session.call_tool(
           "get_optimal_agent_count",
           arguments={}
       )
       data = json.loads(result.content[0].text)

       if data['optimal_agents'] > 1:
           # Report that project could benefit from more agents
           await session.call_tool(
               "report_blocker",
               arguments={
                   "agent_id": "agent-1",
                   "blocker_type": "Resource Constraint",
                   "description": (
                       f"Project could benefit from "
                       f"{data['optimal_agents']} agents"
                   )
               }
           )
   ```

2. PERIODIC ASSESSMENT - Monitor as project evolves
   ```python
   async def periodic_check():
       # Check every N tasks completed
       result = await session.call_tool(
           "get_optimal_agent_count",
           arguments={"include_details": True}
       )

       # Use parallel_opportunities to identify bottlenecks
       # Report if max_parallelism > current_agent_count
   ```

3. DYNAMIC SCALING - Request more agents when beneficial
   ```python
   async def request_scaling():
       result = await session.call_tool("get_optimal_agent_count", {})
       data = json.loads(result.content[0].text)

       if data['efficiency_gain_percent'] > 50:
           # Significant speedup possible
           await notify_orchestrator({
               "action": "scale_up",
               "target_agents": data['optimal_agents'],
               "expected_speedup": data['efficiency_gain_percent']
           })
   ```
    """
    )


async def main() -> None:
    """Run the optimal agent count demos."""
    print("\n" + "=" * 70)
    print("🚀 GET_OPTIMAL_AGENT_COUNT MCP TOOL - USAGE GUIDE")
    print("=" * 70)
    print("\nThis tool uses Critical Path Method (CPM) to calculate")
    print("the optimal number of agents for maximum efficiency.")
    print("\nAvailable demos:")
    print("  1. Stdio mode (isolated testing)")
    print("  2. HTTP mode (production usage)")
    print("  3. Agent usage patterns")
    print("=" * 70)

    # Run stdio demo (works without prerequisites)
    await demo_optimal_agents_stdio()

    # Show agent usage patterns
    await demo_agent_usage()

    # HTTP demo requires running server
    print("\n" + "=" * 70)
    print("💡 To test HTTP mode:")
    print("   1. Start Marcus: python -m src.marcus_mcp.server --http")
    print("   2. Run this script again")
    print("=" * 70)

    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
