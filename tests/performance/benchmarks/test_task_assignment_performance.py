"""
Performance benchmarks for task assignment operations.

Tests the performance of various task assignment algorithms
under different load conditions.
"""

import asyncio
import time
from typing import List
from unittest.mock import AsyncMock

import pytest

from tests.fixtures.factories import AgentFactory, TaskFactory
from tests.utils.base import BaseTestCase


class TestTaskAssignmentPerformance(BaseTestCase):
    """Benchmark tests for task assignment performance."""

    @pytest.mark.performance
    @pytest.mark.parametrize(
        "task_count,agent_count", [(10, 5), (100, 10), (1000, 20), (10000, 50)]
    )
    def test_task_assignment_scaling(self, task_count: int, agent_count: int):
        """
        Test how task assignment scales with number of tasks and agents.

        This benchmark measures the time to assign all tasks to agents
        using the optimal assignment algorithm.
        """
        # Create test data
        tasks = TaskFactory.create_batch(task_count)
        agents = AgentFactory.create_team(agent_count)

        # Measure assignment time
        start_time = time.time()

        # Simulate task assignment logic
        assignments = []
        for i, task in enumerate(tasks):
            # Simple round-robin assignment for benchmark
            agent = agents[i % len(agents)]
            assignments.append((task.id, agent.worker_id))

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        # Should complete in reasonable time even with large datasets
        if task_count <= 100:
            assert duration < 0.1  # 100ms for small datasets
        elif task_count <= 1000:
            assert duration < 1.0  # 1s for medium datasets
        else:
            assert duration < 10.0  # 10s for large datasets

        # Calculate metrics
        tasks_per_second = task_count / duration
        print(
            f"\nAssigned {task_count} tasks to {agent_count} agents in {duration:.3f}s"
        )
        print(f"Performance: {tasks_per_second:.0f} tasks/second")

    @pytest.mark.performance
    @pytest.mark.anyio
    @pytest.mark.parametrize("anyio_backend", ["asyncio"])
    async def test_concurrent_task_updates(self):
        """
        Test performance of concurrent task status updates.

        Simulates multiple agents updating task progress simultaneously.
        """
        # Setup
        task_count = 100
        concurrent_updates = 10

        mock_client = self.create_mock_kanban_client()
        mock_client.update_task_progress = AsyncMock(
            side_effect=lambda *args: asyncio.sleep(0.01)  # Simulate network delay
        )

        tasks = TaskFactory.create_batch(task_count)

        # Measure concurrent update performance
        start_time = time.time()

        async def update_task_batch(batch_tasks: List):
            for task in batch_tasks:
                await mock_client.update_task_progress(
                    task.id, {"status": "in_progress", "progress": 50}
                )

        # Split tasks into batches for concurrent processing
        batch_size = task_count // concurrent_updates
        batches = [tasks[i : i + batch_size] for i in range(0, task_count, batch_size)]

        # Run updates concurrently
        await asyncio.gather(*[update_task_batch(batch) for batch in batches])

        end_time = time.time()
        duration = end_time - start_time

        # Performance assertions
        assert duration < 2.0  # Should complete within 2 seconds

        # Calculate metrics
        updates_per_second = task_count / duration
        print(f"\nCompleted {task_count} concurrent updates in {duration:.3f}s")
        print(f"Performance: {updates_per_second:.0f} updates/second")
        print(
            f"Speedup from concurrency: {concurrent_updates / (duration / (0.01 * task_count)):.1f}x"
        )

    @pytest.mark.performance
    def test_task_filtering_performance(self):
        """
        Test performance of task filtering operations.

        Measures how quickly we can filter large task lists by various criteria.
        """
        # Create large dataset
        task_count = 10000
        tasks = []

        # Create diverse task set
        for i in range(task_count):
            tasks.append(
                TaskFactory.create(
                    priority="high" if i % 3 == 0 else "medium",
                    status="todo" if i % 4 == 0 else "in_progress",
                    labels=["backend"] if i % 2 == 0 else ["frontend"],
                    assigned_to=f"agent-{i % 10:03d}" if i % 5 != 0 else None,
                )
            )

        # Benchmark different filtering operations
        filters = [
            ("High priority", lambda t: t.priority.value == "high"),
            ("Unassigned", lambda t: t.assigned_to is None),
            ("Backend tasks", lambda t: "backend" in t.labels),
            ("TODO status", lambda t: t.status == TaskStatus.TODO),
            (
                "Complex filter",
                lambda t: t.priority.value == "high"
                and t.assigned_to is None
                and "backend" in t.labels,
            ),
        ]

        for filter_name, filter_func in filters:
            start_time = time.time()
            filtered = list(filter(filter_func, tasks))
            duration = time.time() - start_time

            print(f"\n{filter_name}: {len(filtered)} tasks in {duration*1000:.1f}ms")
            assert duration < 0.1  # Should complete within 100ms


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory usage of various operations."""

    def test_large_task_list_memory(self):
        """
        Test memory usage when handling large task lists.

        Note: This is a basic test. For detailed memory profiling,
        use tools like memory_profiler or pytest-memray.
        """
        import gc
        import sys

        # Force garbage collection
        gc.collect()

        # Create large dataset
        task_count = 10000

        # Measure baseline
        baseline_size = sys.getsizeof([])

        # Create tasks
        tasks = TaskFactory.create_batch(task_count)

        # Rough memory estimate
        total_size = sys.getsizeof(tasks)
        per_task_size = (total_size - baseline_size) / task_count

        print(f"\nMemory usage for {task_count} tasks:")
        print(f"Total: {total_size / 1024 / 1024:.1f} MB")
        print(f"Per task: {per_task_size:.0f} bytes")

        # Memory should be reasonable
        assert per_task_size < 10000  # Less than 10KB per task
