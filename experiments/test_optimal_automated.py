#!/usr/bin/env python3
"""
Automated Optimal Agent Count Testing using Inspector.

This script automatically tests optimal agent configuration using
the Inspector HTTP client to connect to a running Marcus instance.

Usage:
    python test_optimal_automated.py ~/experiments/my-project
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector


def read_experiment_config(experiment_dir: Path) -> Dict[str, Any]:
    """Read experiment configuration."""
    config_file = experiment_dir / "config.yaml"
    if not config_file.exists():
        print(f"❌ No config.yaml found at {config_file}")
        sys.exit(1)

    with open(config_file, "r") as f:
        return yaml.safe_load(f)


def read_project_spec(experiment_dir: Path, spec_filename: str) -> str:
    """Read project specification."""
    spec_file = experiment_dir / spec_filename
    if not spec_file.exists():
        print(f"❌ No project spec found at {spec_file}")
        sys.exit(1)

    with open(spec_file, "r") as f:
        return f.read()


def parse_result(result: Any) -> Dict[str, Any]:
    """Parse MCP tool result to dict."""
    if hasattr(result, "content") and result.content:
        text = result.content[0].text if result.content else str(result)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "Could not parse result", "raw": text}
    return {"error": "No content in result"}


async def test_optimal_agents(experiment_dir: Path) -> None:
    """
    Test optimal agent configuration for an experiment.

    Parameters
    ----------
    experiment_dir : Path
        Experiment directory with config.yaml and project_spec.md
    """
    print("=" * 70)
    print(f"Testing optimal agent count for: {experiment_dir.name}")
    print("=" * 70)

    # Read configuration
    config = read_experiment_config(experiment_dir)
    project_name = config["project_name"]
    spec_filename = config["project_spec_file"]
    options = config.get("project_options", {})
    current_num_agents = config.get("num_agents", 0)

    print(f"\n📋 Project: {project_name}")
    print(f"📄 Spec: {spec_filename}")
    print(f"⚙️  Current config: {current_num_agents} agents")

    # Read project specification
    description = read_project_spec(experiment_dir, spec_filename)

    # Connect to Marcus via Inspector
    print("\n📡 Connecting to Marcus MCP server...")
    client = Inspector(connection_type="http")

    try:
        async with client.connect(url="http://localhost:4298/mcp"):
            print("✅ Connected to Marcus")

            # Step 1: Create project
            print("\n" + "=" * 70)
            print("Step 1: Creating project...")
            print("=" * 70)

            result = await client.session.call_tool(
                "create_project",
                arguments={
                    "project_name": project_name,
                    "description": description,
                    "options": options,
                },
            )

            project_result = parse_result(result)

            if not project_result.get("success"):
                print(f"❌ Project creation failed: {project_result.get('message')}")
                sys.exit(1)

            tasks_created = project_result.get("tasks_created", 0)
            print(f"✅ Project created: {project_name}")
            print(f"   Tasks created: {tasks_created}")

            # Step 2: List and select project
            print("\n" + "=" * 70)
            print("Step 2: Selecting project...")
            print("=" * 70)

            # List projects to find ours
            list_result = await client.session.call_tool("list_projects", arguments={})
            projects = parse_result(list_result)

            # The result might be a list or dict, handle both
            if isinstance(projects, dict):
                # Single project returned
                project_id = projects.get("id")
            elif isinstance(projects, list) and len(projects) > 0:
                # Multiple projects, find the one we just created
                for p in projects:
                    if isinstance(p, dict) and project_name in p.get("name", ""):
                        project_id = p.get("id")
                        break
            else:
                print(f"❌ Could not find project: {project_name}")
                print(f"Projects result: {projects}")
                sys.exit(1)

            # Select the project
            select_result = await client.session.call_tool(
                "select_project", arguments={"project_id": project_id}
            )
            select_data = parse_result(select_result)
            print(f"✅ Selected project: {project_name}")

            # Step 3: Get optimal agent count
            print("\n" + "=" * 70)
            print("Step 3: Analyzing task dependencies...")
            print("=" * 70)

            optimal_result = await client.session.call_tool(
                "get_optimal_agent_count", arguments={"include_details": True}
            )

            analysis = parse_result(optimal_result)

            if not analysis.get("success"):
                print(f"❌ Analysis failed: {analysis.get('message')}")
                sys.exit(1)

            # Display results
            print("\n" + "=" * 70)
            print("OPTIMAL AGENT ANALYSIS")
            print("=" * 70)

            optimal = analysis["optimal_agents"]
            critical_path = analysis["critical_path_hours"]
            max_parallel = analysis["max_parallelism"]
            total_tasks = analysis["total_tasks"]
            efficiency = analysis["efficiency_gain_percent"]

            print(f"\n📊 Project Analysis:")
            print(f"   Total tasks: {total_tasks}")
            print(f"   Critical path: {critical_path:.2f} hours")
            print(f"   Max parallelism: {max_parallel} tasks can run simultaneously")
            print(f"   Efficiency gain: {efficiency:.1f}% vs single agent")

            print(f"\n✅ RECOMMENDED: {optimal} agents")
            print("   (Based on peak parallelism)")

            if current_num_agents < optimal:
                diff = optimal - current_num_agents
                print(f"\n⚠️  WARNING: You have {diff} fewer agent(s) than optimal")
                print("   Some tasks will wait longer than necessary")
            elif current_num_agents > optimal:
                diff = current_num_agents - optimal
                print(f"\n⚠️  WARNING: You have {diff} more agent(s) than needed")
                print("   Extra agents will be idle, wasting resources")
            else:
                print("\n✅ Your configuration matches the optimal agent count!")

            # Show parallelism timeline
            if "parallel_opportunities" in analysis:
                print("\n📈 Parallelism Timeline:")
                print("   (Shows how many tasks can run at different time points)\n")
                print("   Time (h) │ Tasks │ Utilization")
                print("   ─────────┼───────┼────────────")

                opportunities = analysis["parallel_opportunities"][:10]
                for opp in opportunities:
                    time_h = opp["time"]
                    count = opp["task_count"]
                    util = opp["utilization_percent"]
                    bar = "█" * int(util / 10)
                    print(f"   {time_h:>7.1f}  │  {count:>3}  │ {util:>3.0f}% {bar}")

                if len(analysis["parallel_opportunities"]) > 10:
                    remaining = len(analysis["parallel_opportunities"]) - 10
                    print(f"   ... ({remaining} more time points)")

            # Offer to update config
            print("\n" + "=" * 70)
            print("RECOMMENDED CONFIG UPDATE")
            print("=" * 70)
            print(f"\nnum_agents: {optimal}  # Optimal based on CPM analysis")

            response = input("\n💾 Update config.yaml with optimal setting? [y/N]: ")

            if response.lower() == "y":
                config_file = experiment_dir / "config.yaml"
                # Backup original
                import shutil

                backup_file = config_file.parent / "config.yaml.backup"
                shutil.copy(config_file, backup_file)
                print(f"✅ Backed up original to: {backup_file}")

                # Update config
                config["num_agents"] = optimal
                with open(config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

                print(f"✅ Updated {config_file} with optimal count: {optimal}")
                print("\n🚀 Ready to run experiment:")
                print(f"   python run_experiment.py {config_file.parent}")
            else:
                print("\n📝 Config not updated")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        print("\n💡 Make sure Marcus server is running:")
        print("   Check if MCP server is accessible at http://localhost:4298/mcp")


def main() -> None:
    """Run the test."""
    parser = argparse.ArgumentParser(
        description="Automated test for optimal agent count (Inspector)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python test_optimal_automated.py ~/experiments/my-project

Prerequisites:
  - Marcus MCP server running at http://localhost:4298/mcp

This will:
1. Connect to Marcus via Inspector (HTTP)
2. Create the project
3. Select the project
4. Analyze dependencies with CPM
5. Show optimal agent count
6. Offer to update config.yaml
        """,
    )

    parser.add_argument(
        "experiment_dir", type=str, help="Path to experiment directory"
    )

    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()

    if not experiment_dir.exists():
        print(f"❌ Experiment directory not found: {experiment_dir}")
        sys.exit(1)

    # Run async test
    asyncio.run(test_optimal_agents(experiment_dir))


if __name__ == "__main__":
    main()
