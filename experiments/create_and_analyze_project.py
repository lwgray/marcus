#!/usr/bin/env python3
"""
Create project and analyze optimal agent count directly via Marcus HTTP API.

This script bypasses Claude Code and directly uses the Inspector client to:
1. Create a project from a specification
2. Get optimal agent count analysis
3. Display recommendations

Usage:
    python create_and_analyze_project.py ~/experiments/test1
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Add project root to path - must be before src imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


def read_experiment_config(experiment_dir: Path) -> Dict[str, Any]:
    """Read experiment configuration."""
    config_file = experiment_dir / "config.yaml"
    if not config_file.exists():
        print(f"❌ No config.yaml found at {config_file}")
        sys.exit(1)

    with open(config_file, "r") as f:
        config: Dict[str, Any] = yaml.safe_load(f)
        return config


def read_project_spec(experiment_dir: Path, spec_filename: str) -> str:
    """Read project specification."""
    spec_file = experiment_dir / spec_filename
    if not spec_file.exists():
        print(f"❌ No project spec found at {spec_file}")
        sys.exit(1)

    with open(spec_file, "r") as f:
        return f.read()


def display_results(analysis: Dict[str, Any], current_config: Dict[str, Any]) -> None:
    """Display analysis results and recommendations."""
    print("\n" + "=" * 70)
    print("OPTIMAL AGENT ANALYSIS")
    print("=" * 70)

    optimal = analysis["optimal_agents"]
    critical_path = analysis["critical_path_hours"]
    max_parallel = analysis["max_parallelism"]
    total_tasks = analysis.get("total_tasks", "unknown")
    efficiency = analysis["efficiency_gain_percent"]

    print("\n📊 Project Analysis:")
    print(f"   Total tasks: {total_tasks}")
    print(f"   Critical path: {critical_path:.2f} hours")
    print(f"   Max parallelism: {max_parallel} tasks can run simultaneously")
    print(f"   Efficiency gain: {efficiency:.1f}% vs single agent")

    print(f"\n✅ RECOMMENDED: {optimal} agents")
    print("   (Based on peak parallelism - agents will idle during low-demand periods)")

    # Show current configuration
    current_total = sum(agent.get("subagents", 0) for agent in current_config["agents"])
    current_total += len(current_config["agents"])  # Include main agents

    print(f"\n⚙️  Current config.yaml: {current_total} total agents")
    for agent in current_config["agents"]:
        subagents = agent.get("subagents", 0)
        total_for_agent = subagents + 1
        print(
            f"   - {agent['name']}: {subagents} subagents + "
            f"1 main = {total_for_agent} total"
        )

    if current_total < optimal:
        diff = optimal - current_total
        print(f"\n⚠️  WARNING: You have {diff} fewer agents than optimal")
        print("   Some tasks will wait longer than necessary")
    elif current_total > optimal:
        diff = current_total - optimal
        print(f"\n⚠️  WARNING: You have {diff} more agents than needed")
        print("   Extra agents will be idle, wasting resources")
    else:
        print("\n✅ Your configuration matches the optimal agent count!")

    # Show parallelism timeline
    if "parallel_opportunities" in analysis:
        print("\n📈 Parallelism Timeline:")
        print("   (Shows how many tasks can run at different time points)\n")
        print("   Time (h) │ Tasks │ Utilization")
        print("   ─────────┼───────┼────────────")

        for opp in analysis["parallel_opportunities"][:10]:  # Show first 10
            time_h = opp["time"]
            count = opp["task_count"]
            util = opp["utilization_percent"]
            bar = "█" * int(util / 10)
            print(f"   {time_h:>7.2f}  │  {count:>3}  │ {util:>3.0f}% {bar}")

        if len(analysis["parallel_opportunities"]) > 10:
            remaining = len(analysis["parallel_opportunities"]) - 10
            print(f"   ... ({remaining} more time points)")


async def create_and_analyze_project(
    experiment_dir: Path,
    project_name: str,
    description: str,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create project and get optimal agent analysis.

    Parameters
    ----------
    experiment_dir : Path
        Path to experiment directory
    project_name : str
        Name of the project
    description : str
        Project specification/description
    options : Dict[str, Any]
        Project creation options

    Returns
    -------
    Dict[str, Any]
        Optimal agent analysis results
    """
    client = Inspector(connection_type="http")
    url = "http://localhost:4298/mcp"
    agent_id = "test-optimal-agent"

    print("\n" + "=" * 70)
    print("Creating Project and Analyzing Dependencies")
    print("=" * 70)

    try:
        async with client.connect(url=url) as session:
            # Step 1: Authenticate
            print("\n🔐 Authenticating...")
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": agent_id,
                    "client_type": "admin",
                    "role": "admin",
                    "metadata": {"workflow": "test_optimal", "connection": "http"},
                },
            )
            print("✅ Authenticated")

            # Step 2: Create project
            print(f"\n📂 Creating project: {project_name}")
            print(f"   Complexity: {options.get('complexity', 'standard')}")

            create_result = await session.call_tool(
                "create_project",
                arguments={
                    "project_name": project_name,
                    "description": description,
                    "options": options,
                },
            )

            # Parse result
            create_data = json.loads(create_result.content[0].text)
            if not create_data.get("success"):
                error_msg = f"Failed to create project: {create_data.get('error')}"
                print(f"\n❌ {error_msg}")
                sys.exit(1)

            total_tasks = create_data.get("tasks_created", 0)
            board_info = create_data.get("board", {})
            print(f"✅ Project created with {total_tasks} tasks")
            print(f"   Board: {board_info.get('board_name', 'N/A')}")

            # Step 3: Get optimal agent count
            print("\n📊 Analyzing task dependencies...")

            optimal_result = await session.call_tool(
                "get_optimal_agent_count",
                arguments={"include_details": True},
            )

            # Parse result
            optimal_data: Dict[str, Any] = json.loads(optimal_result.content[0].text)
            if not optimal_data.get("success"):
                error_msg = f"Failed to analyze: {optimal_data.get('error')}"
                print(f"\n❌ {error_msg}")
                sys.exit(1)

            print("✅ Analysis complete")

            return optimal_data

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


async def main_async(experiment_dir: Path) -> None:
    """Run the async workflow."""
    print(f"Testing optimal agent count for: {experiment_dir.name}")

    # Read configuration
    config = read_experiment_config(experiment_dir)
    project_name = config["project_name"]
    spec_file = config["project_spec_file"]
    options = config.get("project_options", {})

    print(f"\n📋 Project: {project_name}")
    print(f"📄 Spec: {spec_file}")

    # Read project specification
    description = read_project_spec(experiment_dir, spec_file)

    # Create project and analyze
    analysis = await create_and_analyze_project(
        experiment_dir, project_name, description, options
    )

    # Display results
    display_results(analysis, config)


def main() -> None:
    """Run the optimal agent test."""
    parser = argparse.ArgumentParser(
        description="Create project and analyze optimal agent count",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python create_and_analyze_project.py ~/experiments/test1

This will create the project via Marcus HTTP API and show optimal agent count.
        """,
    )

    parser.add_argument("experiment_dir", type=str, help="Path to experiment directory")

    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()

    if not experiment_dir.exists():
        print(f"❌ Experiment directory not found: {experiment_dir}")
        sys.exit(1)

    # Run async workflow
    asyncio.run(main_async(experiment_dir))


if __name__ == "__main__":
    main()
