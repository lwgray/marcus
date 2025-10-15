#!/usr/bin/env python3
"""
Automated Optimal Agent Count Testing.

This script automatically tests optimal agent configuration without requiring
manual MCP interaction. It connects directly to Marcus MCP server via HTTP.

Usage:
    python test_optimal_agents_automated.py ~/experiments/my-project
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

import httpx
import yaml


def call_marcus_mcp(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Marcus MCP tool via HTTP.

    Parameters
    ----------
    tool_name : str
        Name of the MCP tool (e.g., "create_project")
    arguments : Dict[str, Any]
        Tool arguments

    Returns
    -------
    Dict[str, Any]
        Tool result
    """
    url = "http://localhost:4298/mcp/"

    # MCP protocol format
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": f"mcp__marcus__{tool_name}", "arguments": arguments},
    }

    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        response.raise_for_status()
        result = response.json()

        if "error" in result:
            raise Exception(f"MCP error: {result['error']}")

        return result.get("result", {}).get("content", [{}])[0].get("text", {})

    except httpx.ConnectError:
        print("\n❌ Could not connect to Marcus MCP server at http://localhost:4298")
        print("   Make sure Marcus server is running.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error calling Marcus MCP: {e}")
        raise


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


def display_results(
    analysis: Dict[str, Any], current_config: Dict[str, Any], config_file: Path
) -> None:
    """Display analysis results and recommendations."""
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

    # Show current configuration
    current_total = current_config.get("num_agents", 0)

    print(f"\n⚙️  Current config.yaml: {current_total} agents")

    if current_total < optimal:
        diff = optimal - current_total
        print(f"\n⚠️  WARNING: You have {diff} fewer agent(s) than optimal")
        print("   Some tasks will wait longer than necessary")
    elif current_total > optimal:
        diff = current_total - optimal
        print(f"\n⚠️  WARNING: You have {diff} more agent(s) than needed")
        print("   Extra agents will be idle, wasting resources")
    else:
        print("\n✅ Your configuration matches the optimal agent count!")

    # Show parallelism timeline (first 10 time points)
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

    # Show recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIG.YAML UPDATE")
    print("=" * 70)

    print(f"\nnum_agents: {optimal}  # Optimal based on task dependencies")

    # Offer to update config
    print("\n" + "=" * 70)
    response = input("\n💾 Update config.yaml with optimal settings? [y/N]: ")

    if response.lower() == "y":
        # Backup original
        import shutil

        backup_file = config_file.parent / "config.yaml.backup"
        shutil.copy(config_file, backup_file)
        print(f"✅ Backed up original to: {backup_file}")

        # Update config
        current_config["num_agents"] = optimal
        with open(config_file, "w") as f:
            yaml.dump(current_config, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Updated {config_file} with optimal agent count: {optimal}")
        print("\n🚀 Ready to run experiment:")
        print(f"   python run_experiment.py {config_file.parent}")
    else:
        print("\n📝 Config not updated. Manually set num_agents in config.yaml")


def main() -> None:
    """Run automated optimal agent test."""
    parser = argparse.ArgumentParser(
        description="Automated test for optimal agent count",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python test_optimal_agents_automated.py ~/experiments/my-project

This will:
1. Read your experiment config and project spec
2. Create the project in Marcus/Planka automatically
3. Analyze task dependencies with CPM
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
        print("\nCreate it first with:")
        print(f"  python run_experiment.py --init {experiment_dir}")
        sys.exit(1)

    print("=" * 70)
    print(f"Testing optimal agent count for: {experiment_dir.name}")
    print("=" * 70)

    # Read configuration
    config = read_experiment_config(experiment_dir)
    project_name = config["project_name"]
    spec_file = config["project_spec_file"]
    options = config.get("project_options", {})

    print(f"\n📋 Project: {project_name}")
    print(f"📄 Spec: {spec_file}")

    # Read project specification
    description = read_project_spec(experiment_dir, spec_file)

    # Step 1: Create project via MCP
    print("\n" + "=" * 70)
    print("Step 1: Creating project in Marcus/Planka...")
    print("=" * 70)

    try:
        result = call_marcus_mcp(
            "create_project",
            {
                "project_name": project_name,
                "description": description,
                "options": options,
            },
        )

        # Parse JSON result
        if isinstance(result, str):
            result = json.loads(result)

        if result.get("success"):
            tasks_created = result.get("tasks_created", 0)
            print(f"✅ Project created: {project_name}")
            print(f"   Tasks created: {tasks_created}")
        else:
            print(f"❌ Project creation failed: {result.get('message')}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error creating project: {e}")
        sys.exit(1)

    # Step 2: Get optimal agent count
    print("\n" + "=" * 70)
    print("Step 2: Analyzing task dependencies...")
    print("=" * 70)

    try:
        result = call_marcus_mcp("get_optimal_agent_count", {"include_details": True})

        # Parse JSON result
        if isinstance(result, str):
            result = json.loads(result)

        if not result.get("success"):
            print(f"❌ Analysis failed: {result.get('message')}")
            sys.exit(1)

        # Display results
        display_results(result, config, experiment_dir / "config.yaml")

    except Exception as e:
        print(f"❌ Error analyzing dependencies: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
