#!/usr/bin/env python3
"""
AppForge Benchmark Runner for Marcus.

Standalone tool for running AppForge benchmarks with Marcus.
No Marcus source code changes required.

Usage:
    # Single benchmark
    python appforge_runner.py --task-id 63 --num-agents 5

    # Multiple configurations
    python appforge_runner.py --task-id 63 --agents 1,3,5,10 --compare

    # Suite of benchmarks
    python appforge_runner.py --suite configs/example_suite.yaml

Requirements:
    - Python 3.11+
    - uiautomator2 and opencv-python installed (pip install uiautomator2 opencv-python)
"""

import asyncio
import importlib.util
import json
import sys
import time
from pathlib import Path

import yaml

# Check Python version
if sys.version_info < (3, 11):
    print("Error: Python 3.11+ required")
    print("Please use Python 3.11 or higher")
    sys.exit(1)

from evaluator import evaluate_benchmark, save_evaluation_results
from task_converter import convert_appforge_to_marcus_spec

# Import Marcus Inspector for HTTP connection to running server
# appforge_runner.py -> appforge -> benchmarks -> experiments -> dev-tools -> marcus
MARCUS_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Load Inspector module directly to avoid import issues
inspector_path = MARCUS_ROOT / "src" / "worker" / "inspector.py"
spec = importlib.util.spec_from_file_location("inspector", inspector_path)
inspector_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector_module)
Inspector = inspector_module.Inspector
# Marcus MCP server URL (default HTTP endpoint)
MARCUS_MCP_URL = "http://localhost:4298/mcp"


def _extract_text_from_result(result: any) -> str:
    """
    Safely extract text from MCP result content.

    Pattern from demo_http_connection.py (line 27).

    Parameters
    ----------
    result : any
        MCP tool result (CallToolResult object)

    Returns
    -------
    str
        Extracted text content
    """
    # MCP SDK returns CallToolResult with content array
    if hasattr(result, "content") and result.content:
        return result.content[0].text if result.content else str(result)
    return str(result)


async def wait_for_marcus_completion_async(
    experiment_dir: Path, task_id: int, timeout: int = 3600, poll_interval: int = 30
) -> bool:
    """
    Wait for Marcus experiment to complete using MCP tools.

    Connects to existing Marcus MCP server via HTTP and monitors
    project progress via `query_project_history` tool.
    Polls every poll_interval seconds to check if all tasks are DONE.

    Parameters
    ----------
    experiment_dir : Path
        Marcus experiment directory
    task_id : int
        AppForge task ID (for authentication metadata)
    timeout : int
        Maximum wait time in seconds (default: 1 hour)
    poll_interval : int
        Seconds between polls (default: 30s)

    Returns
    -------
    bool
        True if completed successfully, False on timeout/error
    """
    print("Waiting for Marcus to complete...")

    project_info_file = experiment_dir / "project_info.json"
    start_time = time.time()

    # First, wait for project_info.json to be created
    while not project_info_file.exists():
        if time.time() - start_time > 300:  # 5 minutes for project creation
            print("✗ Timeout waiting for project creation")
            return False
        await asyncio.sleep(5)

    print("  ✓ Project created")

    # Read project info
    with open(project_info_file, "r") as f:
        project_info = json.load(f)

    project_id = project_info.get("project_id")
    tasks_created = project_info.get("tasks_created", 0)
    print(f"  Project ID: {project_id}")
    print(f"  Tasks created: {tasks_created}")

    if not project_id:
        print("✗ No project_id found in project_info.json")
        return False

    print(f"  Polling Marcus every {poll_interval}s (timeout: {timeout}s)...")
    print()

    # Connect to existing Marcus MCP server via HTTP
    client = Inspector(connection_type="http")

    try:
        async with client.connect(url=MARCUS_MCP_URL) as session:
            # Authenticate as a benchmark worker
            await session.call_tool(
                "authenticate",
                arguments={
                    "client_id": f"appforge_benchmark_{task_id}",
                    "client_type": "worker",
                    "role": "benchmark",
                    "metadata": {
                        "benchmark_type": "appforge",
                        "task_id": task_id,
                        "connection": "http",
                    },
                },
            )

            # Poll until all tasks are complete
            poll_count = 0
            last_status = None

            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    print(f"\n✗ Timeout after {elapsed:.0f}s")
                    return False

                poll_count += 1

                # Query project summary via MCP
                result = await session.call_tool(
                    "mcp__marcus__query_project_history",
                    arguments={"project_id": project_id, "query_type": "summary"},
                )

                # Parse result
                result_text = _extract_text_from_result(result)
                if not result_text:
                    print(f"  [Poll {poll_count}] No response from Marcus MCP")
                    await asyncio.sleep(poll_interval)
                    continue

                # Debug: print raw result if JSON parsing fails
                try:
                    summary = json.loads(result_text)
                except json.JSONDecodeError as e:
                    print(f"  [Poll {poll_count}] JSON decode error: {e}")
                    print(f"  Raw result_text: {repr(result_text[:200])}")
                    print(f"  Raw result object: {result}")
                    await asyncio.sleep(poll_interval)
                    continue

                if not summary.get("success"):
                    error = summary.get("error", "Unknown error")
                    print(f"  [Poll {poll_count}] Query failed: {error}")
                    await asyncio.sleep(poll_interval)
                    continue

                data = summary.get("data", {})
                task_counts = data.get("task_counts", {})

                total_tasks = task_counts.get("total", 0)
                completed_tasks = task_counts.get("DONE", 0)
                in_progress_tasks = task_counts.get("IN_PROGRESS", 0)
                todo_tasks = task_counts.get("TODO", 0)
                blocked_tasks = task_counts.get("BLOCKED", 0)

                # Format status for display
                status_str = (
                    f"{completed_tasks}/{total_tasks} done, "
                    f"{in_progress_tasks} in progress, "
                    f"{todo_tasks} todo"
                )
                if blocked_tasks > 0:
                    status_str += f", {blocked_tasks} blocked"

                # Only print if status changed
                if status_str != last_status:
                    print(f"  [Poll {poll_count}] {status_str}")
                    last_status = status_str

                # Check completion criteria
                if total_tasks > 0 and completed_tasks == total_tasks:
                    print()
                    print(
                        f"  ✓ All tasks completed! ({completed_tasks}/"
                        f"{total_tasks})"
                    )
                    return True

                # Check for blocked state (no progress possible)
                if (
                    in_progress_tasks == 0
                    and todo_tasks > 0
                    and blocked_tasks >= todo_tasks
                ):
                    print()
                    print(
                        f"  ⚠️  Project appears stuck: {blocked_tasks} "
                        "blocked tasks, none in progress"
                    )
                    return False

                # Wait before next poll
                await asyncio.sleep(poll_interval)

    except Exception as e:
        print(f"\n✗ Error connecting to Marcus MCP server: {e}")
        print(f"\nMake sure Marcus MCP server is running at {MARCUS_MCP_URL}")
        import traceback

        traceback.print_exc()
        return False


def wait_for_marcus_completion(
    experiment_dir: Path, task_id: int, timeout: int = 3600, poll_interval: int = 30
) -> bool:
    """
    Synchronous wrapper for wait_for_marcus_completion_async.

    Parameters
    ----------
    experiment_dir : Path
        Marcus experiment directory
    task_id : int
        AppForge task ID (for authentication metadata)
    timeout : int
        Maximum wait time in seconds
    poll_interval : int
        Seconds between polls

    Returns
    -------
    bool
        True if completed successfully
    """
    return asyncio.run(
        wait_for_marcus_completion_async(
            experiment_dir, task_id, timeout, poll_interval
        )
    )


def run_appforge_benchmark(
    task_id: int, num_agents: int = 5, skip_marcus: bool = False
) -> dict:
    """
    Run a single AppForge benchmark with Marcus.

    Parameters
    ----------
    task_id : int
        AppForge task ID
    num_agents : int
        Number of Marcus agents
    skip_marcus : bool
        Skip Marcus execution (for testing evaluation only)

    Returns
    -------
    dict
        Benchmark results
    """
    print("=" * 70)
    print(f"AppForge Benchmark - Task {task_id}")
    print("=" * 70)
    print(f"Agents: {num_agents}")
    print()

    # Step 1: Convert AppForge task to Marcus format
    print("[1/4] Converting AppForge task to Marcus format...")
    print()
    exp_dir = convert_appforge_to_marcus_spec(
        task_id=task_id,
        num_agents=num_agents,
        output_dir=Path.home()
        / "appforge_benchmarks"
        / "experiments"
        / f"task_{task_id}_agents_{num_agents}",
    )
    print()

    if not skip_marcus:
        # Step 2: Monitor Marcus (assumes Marcus is already running)
        print("[2/4] Monitoring Marcus execution...")
        print()
        print(f"Experiment directory: {exp_dir}")
        print()

        # Wait for completion (connects to existing Marcus via HTTP)
        if not wait_for_marcus_completion(exp_dir, task_id):
            print("✗ Marcus did not complete successfully")
            return {
                "task_id": task_id,
                "num_agents": num_agents,
                "status": "failed",
                "error": "Marcus execution failed or timed out",
            }

        print("  ✓ Marcus completed")
    else:
        print("[2/4] Skipping Marcus execution (--skip-marcus)")

    # Step 3: Evaluate with AppForge
    print()
    print("[3/4] Evaluating with AppForge tests...")
    print()

    implementation_dir = exp_dir / "implementation"
    result = evaluate_benchmark(task_id=task_id, implementation_dir=implementation_dir)

    # Step 4: Save results
    print()
    print("[4/4] Saving results...")

    results_file = (
        Path.home()
        / "appforge_benchmarks"
        / "results"
        / f"task_{task_id}_agents_{num_agents}.json"
    )

    save_evaluation_results(result, results_file)

    print()
    print("=" * 70)
    print("Benchmark Complete")
    print("=" * 70)
    print(f"Task ID: {task_id}")
    print(f"Agents: {num_agents}")
    print(f"Compiled: {'✓' if result.get('compile') else '✗'}")
    print(f"All Tests Passed: {'✓' if result.get('all_pass') else '✗'}")
    print(f"Pass Rate: {result.get('pass_rate', 0) * 100:.1f}%")
    print(f"Duration: {result['duration_seconds']:.1f}s")
    print(f"Results: {results_file}")
    print()

    return result


def run_benchmark_suite(suite_config_file: Path) -> list[dict]:
    """
    Run a suite of benchmarks from configuration file.

    Parameters
    ----------
    suite_config_file : Path
        YAML configuration file

    Returns
    -------
    list[dict]
        List of benchmark results
    """
    with open(suite_config_file, "r") as f:
        config = yaml.safe_load(f)

    tasks = config.get("tasks", [])
    marcus_configs = config.get("marcus_configs", [{"agents": 5}])

    results = []

    print(f"Running benchmark suite: {suite_config_file.name}")
    print(f"  Tasks: {len(tasks)}")
    print(f"  Configurations: {len(marcus_configs)}")
    print()

    for task in tasks:
        task_id = task["id"]

        for marcus_config in marcus_configs:
            num_agents = marcus_config["agents"]

            result = run_appforge_benchmark(task_id=task_id, num_agents=num_agents)

            results.append(result)

            # Save intermediate results
            suite_results_file = (
                Path.home()
                / "appforge_benchmarks"
                / "results"
                / f"suite_{suite_config_file.stem}.json"
            )
            with open(suite_results_file, "w") as f:
                json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run AppForge benchmarks with Marcus",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single benchmark
  python appforge_runner.py --task-id 63 --num-agents 5

  # Compare different agent counts
  python appforge_runner.py --task-id 63 --agents 1,3,5,10

  # Run benchmark suite
  python appforge_runner.py --suite configs/example_suite.yaml

  # Test evaluation only (skip Marcus)
  python appforge_runner.py --task-id 63 --skip-marcus
        """,
    )

    parser.add_argument("--task-id", type=int, help="AppForge task ID")
    parser.add_argument(
        "--num-agents", type=int, default=5, help="Number of Marcus agents (default: 5)"
    )
    parser.add_argument(
        "--agents",
        type=str,
        help="Comma-separated list of agent counts to compare (e.g., 1,3,5,10)",
    )
    parser.add_argument("--suite", type=Path, help="Benchmark suite configuration file")
    parser.add_argument(
        "--skip-marcus",
        action="store_true",
        help="Skip Marcus execution (for testing evaluation only)",
    )

    args = parser.parse_args()

    # Validate arguments
    if args.suite:
        # Run suite
        run_benchmark_suite(args.suite)

    elif args.task_id:
        if args.agents:
            # Run with multiple agent counts
            agent_counts = [int(n) for n in args.agents.split(",")]
            results = []

            for num_agents in agent_counts:
                result = run_appforge_benchmark(
                    task_id=args.task_id,
                    num_agents=num_agents,
                    skip_marcus=args.skip_marcus,
                )
                results.append(result)

            # Print comparison
            print("\n" + "=" * 70)
            print("Comparison Results")
            print("=" * 70)
            print(
                f"{'Agents':<10} {'Compiled':<10} {'Pass Rate':<15} "
                f"{'Duration (s)':<15}"
            )
            print("-" * 70)
            for r in results:
                compiled = "✓" if r.get("compile") else "✗"
                pass_rate = f"{r.get('pass_rate', 0) * 100:.1f}%"
                print(
                    f"{r.get('num_agents', '?'):<10} "
                    f"{compiled:<10} "
                    f"{pass_rate:<15} "
                    f"{r.get('duration_seconds', 0):<15.1f}"
                )

        else:
            # Run single benchmark
            run_appforge_benchmark(
                task_id=args.task_id,
                num_agents=args.num_agents,
                skip_marcus=args.skip_marcus,
            )

    else:
        parser.print_help()
        print("\nError: Either --task-id or --suite is required")
        exit(1)
