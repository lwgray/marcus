#!/usr/bin/env python3
"""
Integration test for cross-parent dependency wiring task ordering.

This test validates that Marcus correctly serves tasks in dependency order,
respecting cross-parent dependencies created by the hybrid dependency wiring
system. It simulates agents requesting tasks, immediately marking them complete,
and requesting the next task, documenting the entire execution flow.

Expected Behavior
-----------------
1. Design tasks with no dependencies should be served first
2. Implementation tasks should only be served after their Design dependencies complete
3. Test tasks should only be served after their Implementation dependencies complete
4. Multiple agents should be able to work on independent tasks in parallel

Test Scenarios
--------------
1. Single-agent sequential execution
2. Multi-agent parallel execution

Expected Task Ordering (based on E-Commerce Cart System)
---------------------------------------------------------
Phase 1 - Design (all can run in parallel):
  - Design User Management (subtasks 1-5)
  - Design Product Catalog (subtasks 1-5)
  - Design Shopping Cart (subtasks 1-5)

Phase 2 - Implementation (after Design completes):
  - Implement User Management (depends on Design User Management + cross-parent deps)
    - Subtask: Implement User Registration
      ✓ Cross-parent dep: Design user account data schema (from Design User Management)
    - Subtask: Implement User Login
      ✓ Cross-parent dep: Design user account data schema
  - Implement Product Catalog (depends on Design tasks)
  - Implement Shopping Cart (depends on Design tasks)
  - Implement Performance (depends on Design tasks)

Phase 3 - Testing (after Implementation completes):
  - Test User Management
  - Test Product Catalog
  - Test Shopping Cart

Phase 4 - Security & Documentation:
  - Implement Security (depends on Design + Implementation)
  - Create PROJECT_SUCCESS documentation (depends on all tasks)

Cross-Parent Dependencies Validated
------------------------------------
The test specifically validates that:
1. "Implement User Registration" is NOT served until "Design user account data schema" completes
2. "Implement User Login" is NOT served until "Design user account data schema" completes
3. Implementation tasks respect dependencies on Design tasks from different parent tasks
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.worker.inspector import Inspector  # noqa: E402


class TaskExecutionLogger:
    """Log and validate task execution order."""

    def __init__(self):
        """Initialize the execution logger."""
        self.completed_tasks: Set[str] = set()
        self.execution_order: List[Dict[str, Any]] = []
        self.violations: List[str] = []

    def log_task_start(self, agent_id: str, task_id: str, task_name: str) -> None:
        """
        Log when a task starts execution.

        Parameters
        ----------
        agent_id : str
            ID of the agent executing the task
        task_id : str
            ID of the task
        task_name : str
            Name of the task
        """
        self.execution_order.append(
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "task_name": task_name,
                "action": "started",
            }
        )
        print(f"  ▶️  [{agent_id}] Started: {task_name} ({task_id})")

    def log_task_complete(
        self, agent_id: str, task_id: str, task_name: str, dependencies: List[str]
    ) -> None:
        """
        Log when a task completes and validate dependencies.

        Parameters
        ----------
        agent_id : str
            ID of the agent executing the task
        task_id : str
            ID of the task
        task_name : str
            Name of the task
        dependencies : List[str]
            List of task IDs this task depends on
        """
        # Validate dependencies were satisfied
        unsatisfied = [dep for dep in dependencies if dep not in self.completed_tasks]
        if unsatisfied:
            violation = (
                f"❌ VIOLATION: {task_name} ({task_id}) completed with "
                f"unsatisfied dependencies: {unsatisfied}"
            )
            self.violations.append(violation)
            print(violation)

        self.completed_tasks.add(task_id)
        self.execution_order.append(
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "task_name": task_name,
                "action": "completed",
                "dependencies": dependencies,
                "dependencies_satisfied": len(unsatisfied) == 0,
            }
        )
        print(f"  ✅ [{agent_id}] Completed: {task_name} ({task_id})")

        if dependencies:
            print(f"     Dependencies: {', '.join(dependencies)}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get execution summary.

        Returns
        -------
        Dict[str, Any]
            Summary with tasks completed, violations, and execution order
        """
        return {
            "tasks_completed": len(self.completed_tasks),
            "violations": self.violations,
            "violation_count": len(self.violations),
            "execution_order": self.execution_order,
        }

    def print_summary(self) -> None:
        """Print a formatted summary of execution."""
        print("\n" + "=" * 70)
        print("EXECUTION SUMMARY")
        print("=" * 70)
        print(f"Total tasks completed: {len(self.completed_tasks)}")
        print(f"Dependency violations: {len(self.violations)}")

        if self.violations:
            print("\n⚠️  VIOLATIONS FOUND:")
            for violation in self.violations:
                print(f"  {violation}")
        else:
            print("\n✅ All tasks executed in correct dependency order!")

        print("\nExecution Order:")
        for idx, entry in enumerate(self.execution_order, 1):
            action_icon = "▶️ " if entry["action"] == "started" else "✅"
            print(f"  {idx}. {action_icon} [{entry['agent_id']}] {entry['task_name']}")


async def simulate_agent_work_loop(
    client: Inspector,
    agent_id: str,
    logger: TaskExecutionLogger,
    max_tasks: Optional[int] = None,
) -> int:
    """
    Simulate an agent's work loop: request task → mark complete → repeat.

    Parameters
    ----------
    client : Inspector
        The Inspector client instance
    agent_id : str
        ID of the agent
    logger : TaskExecutionLogger
        Logger for tracking execution
    max_tasks : Optional[int]
        Maximum number of tasks to complete (None = unlimited)

    Returns
    -------
    int
        Number of tasks completed
    """
    tasks_completed = 0

    while max_tasks is None or tasks_completed < max_tasks:
        # Request next task
        task_result = await client.request_next_task(agent_id)

        # Check if we got a task
        task = task_result.get("task")
        if not task:
            print(f"  ℹ️  [{agent_id}] No tasks available, stopping")
            break

        task_id = task["id"]
        task_name = task["name"]
        dependencies = task.get("dependencies", [])

        # Log task start
        logger.log_task_start(agent_id, task_id, task_name)

        # Immediately mark as complete (simulating instant work)
        await client.report_task_progress(
            agent_id=agent_id,
            task_id=task_id,
            status="completed",
            progress=100,
            message=f"Test completion by {agent_id}",
        )

        # Log task completion
        logger.log_task_complete(agent_id, task_id, task_name, dependencies)

        tasks_completed += 1

        # Small delay to allow other agents to grab tasks
        await asyncio.sleep(0.1)

    return tasks_completed


async def test_single_agent_sequential_execution(
    connection_type: str = "stdio",
) -> None:
    """
    Test single agent sequential execution.

    Parameters
    ----------
    connection_type : str
        "stdio" or "http"

    Validates that a single agent receives tasks in correct dependency order.
    """
    print("\n" + "=" * 70)
    print("TEST 1: Single-Agent Sequential Execution")
    print("=" * 70)
    print(
        "\nThis test validates that tasks are served in dependency order\n"
        "when a single agent processes them sequentially."
    )
    print("=" * 70)

    logger = TaskExecutionLogger()
    client = Inspector(connection_type=connection_type)  # type: ignore

    # Use URL for HTTP mode
    connect_kwargs = {}
    if connection_type == "http":
        connect_kwargs["url"] = "http://localhost:4298/mcp"

    async with client.connect(**connect_kwargs) as session:
        # Register agent
        print("\n🤖 Registering test agent...")
        await client.register_agent(
            agent_id="test-agent-1",
            name="Single Agent Test",
            role="Developer",
            skills=["python", "testing"],
        )

        # Run work loop
        print("\n📋 Starting task execution loop...\n")
        tasks_completed = await simulate_agent_work_loop(
            client, "test-agent-1", logger, max_tasks=20  # Limit for testing
        )

        # Print summary
        logger.print_summary()

        # Validate no violations
        assert (
            len(logger.violations) == 0
        ), f"Found {len(logger.violations)} dependency violations!\n" + "\n".join(
            logger.violations
        )

        print(
            f"\n✅ Single-agent test passed! "
            f"{tasks_completed} tasks completed in correct order."
        )


async def test_multi_agent_parallel_execution(connection_type: str = "stdio") -> None:
    """
    Test multi-agent parallel execution.

    Parameters
    ----------
    connection_type : str
        "stdio" or "http"

    Validates that multiple agents can work on independent tasks in parallel
    while still respecting dependencies.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Multi-Agent Parallel Execution")
    print("=" * 70)
    print(
        "\nThis test validates that multiple agents can work in parallel\n"
        "on independent tasks while respecting dependencies."
    )
    print("=" * 70)

    logger = TaskExecutionLogger()
    client = Inspector(connection_type=connection_type)  # type: ignore

    # Use URL for HTTP mode
    connect_kwargs = {}
    if connection_type == "http":
        connect_kwargs["url"] = "http://localhost:4298/mcp"

    async with client.connect(**connect_kwargs) as session:
        # Register multiple agents
        print("\n🤖 Registering test agents...")
        agents = ["test-agent-1", "test-agent-2", "test-agent-3"]
        for agent_id in agents:
            await client.register_agent(
                agent_id=agent_id,
                name=f"Agent {agent_id}",
                role="Developer",
                skills=["python", "testing"],
            )
            print(f"  ✅ Registered: {agent_id}")

        # Run agents in parallel
        print("\n📋 Starting parallel task execution...\n")
        tasks = [
            simulate_agent_work_loop(client, agent_id, logger, max_tasks=10)
            for agent_id in agents
        ]

        results = await asyncio.gather(*tasks)
        total_completed = sum(results)

        # Print summary
        logger.print_summary()

        # Validate no violations
        assert (
            len(logger.violations) == 0
        ), f"Found {len(logger.violations)} dependency violations!\n" + "\n".join(
            logger.violations
        )

        print(
            f"\n✅ Multi-agent test passed! "
            f"{total_completed} tasks completed across {len(agents)} agents."
        )
        print(f"   Agent results: {dict(zip(agents, results))}")


async def test_cross_parent_dependency_validation(
    connection_type: str = "stdio",
) -> None:
    """
    Test that cross-parent dependencies are correctly enforced.

    Parameters
    ----------
    connection_type : str
        "stdio" or "http"

    Validates specific cross-parent dependency scenarios:
    - Implementation tasks wait for Design tasks from different parents
    """
    print("\n" + "=" * 70)
    print("TEST 3: Cross-Parent Dependency Validation")
    print("=" * 70)
    print(
        "\nThis test validates that cross-parent dependencies created by\n"
        "the hybrid dependency wiring system are correctly enforced."
    )
    print("=" * 70)

    logger = TaskExecutionLogger()
    client = Inspector(connection_type=connection_type)  # type: ignore

    # Use URL for HTTP mode
    connect_kwargs = {}
    if connection_type == "http":
        connect_kwargs["url"] = "http://localhost:4298/mcp"

    async with client.connect(**connect_kwargs) as session:
        # Register agent
        print("\n🤖 Registering test agent...")
        await client.register_agent(
            agent_id="test-agent-cross-parent",
            name="Cross-Parent Test Agent",
            role="Developer",
            skills=["python", "testing"],
        )

        # Run work loop and track specific cross-parent deps
        print("\n📋 Tracking cross-parent dependencies...\n")

        # Track these specific cross-parent relationships
        cross_parent_checks = {
            "1621553830246221340_sub_1": [  # Implement User Registration
                "1621553828643997204_sub_2"  # Design user account data schema
            ],
            "1621553830246221340_sub_2": [  # Implement User Login
                "1621553828643997204_sub_2"  # Design user account data schema
            ],
        }

        tasks_completed = await simulate_agent_work_loop(
            client, "test-agent-cross-parent", logger, max_tasks=25
        )

        # Validate cross-parent dependencies specifically
        print("\n🔍 Validating cross-parent dependencies...")
        cross_parent_violations = []

        for entry in logger.execution_order:
            if entry["action"] == "completed":
                task_id = entry["task_id"]
                if task_id in cross_parent_checks:
                    expected_deps = cross_parent_checks[task_id]
                    actual_deps = entry.get("dependencies", [])

                    # Check that cross-parent deps are present
                    for expected_dep in expected_deps:
                        if expected_dep not in actual_deps:
                            cross_parent_violations.append(
                                f"Task {task_id} missing cross-parent "
                                f"dependency: {expected_dep}"
                            )
                        elif expected_dep not in logger.completed_tasks:
                            cross_parent_violations.append(
                                f"Task {task_id} executed before cross-parent "
                                f"dependency {expected_dep} completed"
                            )
                        else:
                            print(
                                f"  ✅ Cross-parent dep satisfied: "
                                f"{entry['task_name']} waited for {expected_dep}"
                            )

        # Print summary
        logger.print_summary()

        # Validate
        if cross_parent_violations:
            print("\n❌ Cross-parent dependency violations:")
            for violation in cross_parent_violations:
                print(f"  {violation}")
            raise AssertionError(
                f"Found {len(cross_parent_violations)} cross-parent violations"
            )

        print(
            f"\n✅ Cross-parent dependency test passed! "
            f"All cross-parent dependencies correctly enforced."
        )


async def main() -> None:
    """Run all dependency wiring order tests."""
    print("\n🚀 Dependency Wiring Task Order Integration Tests")
    print("=" * 70)
    print(
        "\nThese tests validate that Marcus correctly serves tasks in\n"
        "dependency order, respecting cross-parent dependencies created\n"
        "by the hybrid dependency wiring system."
    )
    print("\nConnection Mode:")
    print("- stdio: Spawns isolated Marcus instance (NO TASKS - demo mode)")
    print("- http: Connects to running Marcus with project data (REAL TEST)")
    print("\nPrerequisites for HTTP mode:")
    print("- Marcus server running: ./marcus start")
    print("- E-Commerce Cart System project loaded in Marcus")
    print("- Cross-parent dependencies created during project initialization")
    print("\nUsage:")
    print("  Demo (stdio): python tests/integration/test_dependency_wiring_order.py")
    print(
        "  Real test:    python tests/integration/test_dependency_wiring_order.py --http"
    )
    print("=" * 70)

    # Parse command line arguments
    connection_type = "stdio"
    if len(sys.argv) > 1:
        if "--http" in sys.argv:
            connection_type = "http"
            print(f"\n✓ Using HTTP mode (connecting to running Marcus server)")
        elif "--help" in sys.argv or "-h" in sys.argv:
            print("\nUsage: python test_dependency_wiring_order.py [--http]")
            print("\nOptions:")
            print("  --http    Connect to running Marcus server (real test)")
            print("  (no args) Use stdio mode (demo only, no tasks)")
            return

    if connection_type == "stdio":
        print(f"\n⚠️  Running in DEMO mode (stdio) - no tasks will be available")
        print("   To test with real tasks, run: python {} --http".format(sys.argv[0]))

    try:
        # Run tests
        await test_single_agent_sequential_execution(connection_type)
        await test_multi_agent_parallel_execution(connection_type)
        await test_cross_parent_dependency_validation(connection_type)

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        if connection_type == "stdio":
            print("\n⚠️  NOTE: Tests passed but no tasks were executed (demo mode)")
            print("   For real testing with E-Commerce project, run:")
            print(f"   python {sys.argv[0]} --http")
        else:
            print("\nCross-parent dependency wiring is working correctly!")
            print("Tasks are being served in the correct dependency order.")

    except AssertionError as e:
        print("\n" + "=" * 70)
        print("❌ TEST FAILED")
        print("=" * 70)
        print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ TEST ERROR")
        print("=" * 70)
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
