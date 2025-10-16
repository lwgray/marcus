#!/usr/bin/env python3
"""
Simple Automated Optimal Agent Testing - Imports Marcus Directly.

This script tests optimal agent configuration by importing Marcus
modules directly, avoiding MCP HTTP complexity.

Usage:
    python test_optimal_simple.py ~/experiments/my-project
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

# Add Marcus to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.marcus_mcp.tools.project_management import create_project
from src.marcus_mcp.tools.scheduler_tools import get_optimal_agent_count
from src.marcus_mcp.server import MarcusServer


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
    config_file = experiment_dir / "config.yaml"
    if not config_file.exists():
        print(f"❌ No config.yaml found at {config_file}")
        sys.exit(1)

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    project_name = config["project_name"]
    spec_filename = config["project_spec_file"]
    options = config.get("project_options", {})
    current_num_agents = config.get("num_agents", 0)

    print(f"\n📋 Project: {project_name}")
    print(f"📄 Spec: {spec_filename}")
    print(f"⚙️  Current config: {current_num_agents} agents\n")

    # Read project specification
    spec_file = experiment_dir / spec_filename
    if not spec_file.exists():
        print(f"❌ No project spec found at {spec_file}")
        sys.exit(1)

    with open(spec_file, "r") as f:
        description = f.read()

    # Initialize Marcus server
    print("Initializing Marcus server...")
    server = MarcusServer()
    await server.initialize()

    try:
        # Step 1: Create project
        print("\n" + "=" * 70)
        print("Step 1: Creating project...")
        print("=" * 70)

        result = await create_project(
            server,
            {
                "project_name": project_name,
                "description": description,
                "options": options,
            },
        )

        if not result.get("success"):
            print(f"❌ Project creation failed: {result.get('message')}")
            sys.exit(1)

        tasks_created = result.get("tasks_created", 0)
        print(f"✅ Project created: {project_name}")
        print(f"   Tasks created: {tasks_created}")

        # Step 2: Get optimal agent count
        print("\n" + "=" * 70)
        print("Step 2: Analyzing task dependencies...")
        print("=" * 70)

        result = await get_optimal_agent_count(
            server, {"include_details": True}
        )

        if not result.get("success"):
            print(f"❌ Analysis failed: {result.get('message')}")
            sys.exit(1)

        # Display results
        print("\n" + "=" * 70)
        print("OPTIMAL AGENT ANALYSIS")
        print("=" * 70)

        optimal = result["optimal_agents"]
        critical_path = result["critical_path_hours"]
        max_parallel = result["max_parallelism"]
        total_tasks = result["total_tasks"]
        efficiency = result["efficiency_gain_percent"]

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
        if "parallel_opportunities" in result:
            print("\n📈 Parallelism Timeline:")
            print("   (Shows how many tasks can run at different time points)\n")
            print("   Time (h) │ Tasks │ Utilization")
            print("   ─────────┼───────┼────────────")

            opportunities = result["parallel_opportunities"][:10]
            for opp in opportunities:
                time_h = opp["time"]
                count = opp["task_count"]
                util = opp["utilization_percent"]
                bar = "█" * int(util / 10)
                print(f"   {time_h:>7.1f}  │  {count:>3}  │ {util:>3.0f}% {bar}")

            if len(result["parallel_opportunities"]) > 10:
                remaining = len(result["parallel_opportunities"]) - 10
                print(f"   ... ({remaining} more time points)")

        # Offer to update config
        print("\n" + "=" * 70)
        print("RECOMMENDED CONFIG UPDATE")
        print("=" * 70)
        print(f"\nnum_agents: {optimal}  # Optimal based on CPM analysis")

        response = input("\n💾 Update config.yaml with optimal setting? [y/N]: ")

        if response.lower() == "y":
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

    finally:
        # Clean up
        await server.cleanup()


def main() -> None:
    """Run the test."""
    parser = argparse.ArgumentParser(
        description="Test optimal agent count (simple version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python test_optimal_simple.py ~/experiments/my-project

This will:
1. Import Marcus modules directly
2. Create the project
3. Analyze dependencies with CPM
4. Show optimal agent count
5. Offer to update config.yaml
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
