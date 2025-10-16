#!/usr/bin/env python3
"""
Test Optimal Agent Count for Marcus Experiments.

This script helps you determine the right number of agents to spawn
BEFORE running a full experiment. It creates a project, analyzes the
task dependency graph, and shows optimal agent configuration.

Usage:
    python test_optimal_agents.py ~/experiments/blog-platform-mvp

This will:
1. Read your experiment config
2. Create the project in Marcus/Planka
3. Call get_optimal_agent_count to analyze dependencies
4. Show recommended agent configuration
5. Provide updated config.yaml with optimal settings
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import yaml


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


def create_test_script(
    experiment_dir: Path, project_name: str, description: str, options: Dict[str, Any]
) -> Path:
    """Create a script that uses Claude Code to create project and query agents."""
    script_content = f'''#!/usr/bin/env python3
"""Auto-generated test script for optimal agent calculation."""

import json

# Print instructions for Claude Code
print("""
AUTONOMOUS TEST SCRIPT - EXECUTE IMMEDIATELY

You are testing optimal agent count. Follow these steps WITHOUT asking permission:

1. Verify Marcus connection:
   mcp__marcus__ping()

2. Create the project:
   mcp__marcus__create_project(
       project_name="{project_name}",
       description='''"""
PROJECT SPEC:
{description}
"""'''
       options={json.dumps(options)}
   )

3. IMMEDIATELY after project creation, get optimal agent count:
   result = mcp__marcus__get_optimal_agent_count(include_details=True)

4. Print the result in this exact format:

   OPTIMAL_AGENT_ANALYSIS_START
   {{
       "optimal_agents": <number>,
       "critical_path_hours": <number>,
       "max_parallelism": <number>,
       "total_tasks": <number>,
       "efficiency_gain": <percentage>,
       "parallel_opportunities": [...]
   }}
   OPTIMAL_AGENT_ANALYSIS_END

5. Exit immediately after printing.

DO NOT:
- Ask for permission
- Wait for user input
- Start working on tasks
- Spawn agents

Just create project, get optimal count, print result, exit.
""")
'''

    script_file = experiment_dir / "test_optimal_agents_runner.py"
    with open(script_file, "w") as f:
        f.write(script_content)
    script_file.chmod(0o755)
    return script_file


def run_claude_test(script_file: Path, experiment_dir: Path) -> Dict[str, Any]:
    """Run Claude Code with the test script and parse results."""
    print("\n" + "=" * 70)
    print("Running Claude Code to create project and analyze dependencies...")
    print("=" * 70)

    # Create shell script to run Claude with proper environment
    shell_script = experiment_dir / "run_test.sh"
    shell_content = f"""#!/bin/bash
# Source shell profile to get claude in PATH
[ -f ~/.zshrc ] && source ~/.zshrc
[ -f ~/.bashrc ] && source ~/.bashrc

# Configure Marcus MCP
claude mcp add marcus -t http http://localhost:4298/mcp 2>/dev/null || true

# Run Claude with the test script
python {script_file} | claude --dangerously-skip-permissions --print
"""
    with open(shell_script, "w") as f:
        f.write(shell_content)
    shell_script.chmod(0o755)

    try:
        result = subprocess.run(
            ["bash", str(shell_script)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        # Parse the output for our JSON result
        output = result.stdout
        if "OPTIMAL_AGENT_ANALYSIS_START" in output:
            start_idx = output.index("OPTIMAL_AGENT_ANALYSIS_START")
            end_idx = output.index("OPTIMAL_AGENT_ANALYSIS_END")
            json_str = output[start_idx + len("OPTIMAL_AGENT_ANALYSIS_START") : end_idx]
            return json.loads(json_str.strip())
        else:
            print("\n❌ Could not find optimal agent analysis in output")
            print("\nClaude Code output:")
            print(output)
            if result.stderr:
                print("\nErrors:")
                print(result.stderr)
            return None

    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 5 minutes")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Could not parse JSON result: {e}")
        return None
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return None


def display_results(analysis: Dict[str, Any], current_config: Dict[str, Any]) -> None:
    """Display analysis results and recommendations."""
    print("\n" + "=" * 70)
    print("OPTIMAL AGENT ANALYSIS")
    print("=" * 70)

    optimal = analysis["optimal_agents"]
    critical_path = analysis["critical_path_hours"]
    max_parallel = analysis["max_parallelism"]
    total_tasks = analysis.get("total_tasks", "unknown")
    efficiency = analysis["efficiency_gain"]

    print(f"\n📊 Project Analysis:")
    print(f"   Total tasks: {total_tasks}")
    print(f"   Critical path: {critical_path:.2f} hours")
    print(f"   Max parallelism: {max_parallel} tasks can run simultaneously")
    print(f"   Efficiency gain: {efficiency:.1%} vs single agent")

    print(f"\n✅ RECOMMENDED: {optimal} agents")
    print(f"   (Based on peak parallelism - agents will idle during low-demand periods)")

    # Show current configuration
    current_total = sum(agent.get("subagents", 0) for agent in current_config["agents"])
    current_total += len(current_config["agents"])  # Include main agents

    print(f"\n⚙️  Current config.yaml: {current_total} total agents")
    for agent in current_config["agents"]:
        subagents = agent.get("subagents", 0)
        print(
            f"   - {agent['name']}: {subagents} subagents + 1 main = {subagents + 1} total"
        )

    if current_total < optimal:
        print(f"\n⚠️  WARNING: You have {optimal - current_total} fewer agents than optimal")
        print("   Some tasks will wait longer than necessary")
    elif current_total > optimal:
        print(
            f"\n⚠️  WARNING: You have {current_total - optimal} more agents than needed"
        )
        print("   Extra agents will be idle, wasting resources")
    else:
        print("\n✅ Your configuration matches the optimal agent count!")

    # Show parallelism timeline
    if "parallel_opportunities" in analysis:
        print("\n📈 Parallelism Timeline:")
        print(
            "   (Shows how many tasks can run at different time points)\n"
        )
        print("   Time (h) │ Tasks │ Utilization")
        print("   ─────────┼───────┼────────────")

        for opp in analysis["parallel_opportunities"][:10]:  # Show first 10
            time_h = opp["time"]
            count = opp["task_count"]
            util = opp["utilization_percent"]
            bar = "█" * int(util / 10)
            print(f"   {time_h:>7.2f}  │  {count:>3}  │ {util:>3.0f}% {bar}")

        if len(analysis["parallel_opportunities"]) > 10:
            print(f"   ... ({len(analysis['parallel_opportunities']) - 10} more time points)")


def generate_optimal_config(
    current_config: Dict[str, Any], optimal_agents: int
) -> Dict[str, Any]:
    """Generate updated config with optimal agent count."""
    new_config = current_config.copy()

    # Simple strategy: distribute agents proportionally across roles
    num_roles = len(new_config["agents"])
    agents_per_role = optimal_agents // num_roles
    remainder = optimal_agents % num_roles

    for i, agent in enumerate(new_config["agents"]):
        # Each agent gets base allocation, first agents get remainder
        subagents = agents_per_role - 1  # -1 because main agent counts
        if i < remainder:
            subagents += 1
        agent["subagents"] = max(1, subagents)  # At least 1 subagent

    return new_config


def main() -> None:
    """Run the optimal agent test."""
    parser = argparse.ArgumentParser(
        description="Test optimal agent count for a Marcus experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python test_optimal_agents.py ~/experiments/blog-platform-mvp

This will create the project and show you how many agents to configure.
        """,
    )

    parser.add_argument(
        "experiment_dir", type=str, help="Path to experiment directory"
    )

    parser.add_argument(
        "--skip-create",
        action="store_true",
        help="Skip project creation (project already exists)",
    )

    args = parser.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()

    if not experiment_dir.exists():
        print(f"❌ Experiment directory not found: {experiment_dir}")
        print("\nCreate it first with:")
        print(f"  python run_experiment.py --init {experiment_dir}")
        sys.exit(1)

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

    if not args.skip_create:
        # Create test script
        script_file = create_test_script(
            experiment_dir, project_name, description, options
        )
        print(f"✅ Created test script: {script_file}")

        # Run Claude Code test
        analysis = run_claude_test(script_file, experiment_dir)

        if not analysis:
            print("\n❌ Test failed - could not get optimal agent count")
            sys.exit(1)
    else:
        print("\n⏩ Skipping project creation (using existing project)")
        print("   Make sure to manually call get_optimal_agent_count")
        sys.exit(0)

    # Display results
    display_results(analysis, config)

    # Generate optimal configuration
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIG.YAML UPDATE")
    print("=" * 70)

    optimal_config = generate_optimal_config(config, analysis["optimal_agents"])

    print("\nagents:")
    for agent in optimal_config["agents"]:
        print(f"  - id: \"{agent['id']}\"")
        print(f"    name: \"{agent['name']}\"")
        print(f"    role: \"{agent['role']}\"")
        print(f"    skills: {agent['skills']}")
        print(f"    subagents: {agent['subagents']}")
        print()

    total = sum(a.get("subagents", 0) for a in optimal_config["agents"]) + len(
        optimal_config["agents"]
    )
    print(f"# Total agents: {total} (matches optimal: {analysis['optimal_agents']})")

    # Offer to update config.yaml
    print("\n" + "=" * 70)
    response = input("\n💾 Update config.yaml with optimal settings? [y/N]: ")

    if response.lower() == "y":
        config_file = experiment_dir / "config.yaml"
        backup_file = experiment_dir / "config.yaml.backup"

        # Backup original
        import shutil

        shutil.copy(config_file, backup_file)
        print(f"✅ Backed up original to: {backup_file}")

        # Write updated config
        config["agents"] = optimal_config["agents"]
        with open(config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"✅ Updated {config_file} with optimal agent configuration")
        print("\n🚀 Ready to run experiment:")
        print(f"   python run_experiment.py {experiment_dir}")
    else:
        print("\n📝 Config not updated. You can manually adjust config.yaml")


if __name__ == "__main__":
    main()
