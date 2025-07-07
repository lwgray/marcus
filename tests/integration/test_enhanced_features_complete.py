#!/usr/bin/env python3
"""
Comprehensive integration test for all enhanced features improvements.

Tests:
1. Event system performance (fire-and-forget mode)
2. Graceful degradation with resilience patterns
3. Enhanced memory predictions with confidence
4. Context dependency inference
5. Granular configuration
6. Visibility integration with events
7. API endpoints for context and memory
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context import Context
from src.core.events import Events, EventTypes
from src.core.memory import Memory
from src.core.memory_advanced import MemoryAdvanced
from src.core.models import Priority, Task, TaskStatus, WorkerStatus
from src.core.persistence import MemoryPersistence, Persistence
from src.core.resilience import RetryConfig, with_fallback, with_retry
from src.visualization.event_integrated_visualizer import EventIntegratedVisualizer


class TestEnhancedFeaturesComplete:
    """Test all enhanced features working together"""

    @pytest.fixture
    async def setup_environment(self):
        """Set up test environment with all features"""
        # Create persistence
        persistence = Persistence(backend=MemoryPersistence())

        # Create events system
        events = Events(store_history=True, persistence=persistence)

        # Create context system
        context = Context(events=events, persistence=persistence)

        # Create enhanced memory system
        memory = MemoryAdvanced(events=events, persistence=persistence)

        # Create visualizer
        visualizer = EventIntegratedVisualizer(events_system=events)
        await visualizer.initialize()

        yield {
            "persistence": persistence,
            "events": events,
            "context": context,
            "memory": memory,
            "visualizer": visualizer,
        }

    @pytest.mark.asyncio
    async def test_event_performance_improvement(self, setup_environment):
        """Test that fire-and-forget mode improves performance"""
        events = setup_environment["events"]

        # Track handler execution
        handler_executed = []

        async def slow_handler(event):
            await asyncio.sleep(0.1)  # Simulate slow operation
            handler_executed.append(event.event_id)

        events.subscribe(EventTypes.TASK_ASSIGNED, slow_handler)

        # Test synchronous mode (wait_for_handlers=True)
        start = time.time()
        await events.publish(
            EventTypes.TASK_ASSIGNED, "test", {"task_id": "1"}, wait_for_handlers=True
        )
        sync_duration = time.time() - start

        # Should take at least 100ms
        assert sync_duration >= 0.1
        assert len(handler_executed) == 1

        # Test async mode (wait_for_handlers=False)
        start = time.time()
        await events.publish(
            EventTypes.TASK_ASSIGNED, "test", {"task_id": "2"}, wait_for_handlers=False
        )
        async_duration = time.time() - start

        # Should return immediately
        assert async_duration < 0.05  # Much faster

        # Wait for handler to complete
        await asyncio.sleep(0.2)
        assert len(handler_executed) == 2

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, setup_environment):
        """Test resilience patterns work correctly"""

        # Test retry with exponential backoff
        attempt_count = 0

        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def flaky_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await flaky_operation()
        assert result == "success"
        assert attempt_count == 3

        # Test fallback
        @with_fallback(lambda: "fallback_value")
        async def failing_operation():
            raise Exception("Primary failed")

        result = await failing_operation()
        assert result == "fallback_value"

    @pytest.mark.asyncio
    async def test_enhanced_memory_predictions(self, setup_environment):
        """Test memory predictions with confidence intervals"""
        memory = setup_environment["memory"]

        # Create test agent and task
        agent_id = "test_agent"
        task = Task(
            id="test_task",
            name="Complex API Task",
            description="Build complex API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=20.0,  # Complex task
            labels=["api", "complex"],
            dependencies=[],
        )

        # Record some history
        for i in range(10):
            # Create a unique task for each iteration
            test_task = Task(
                id=f"task_{i}",
                name=f"Test Task {i}",
                description="Test task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=5.0 + i * 0.5,
                labels=["test", "api"] if i % 2 == 0 else ["test", "backend"],
                dependencies=[],
            )

            await memory.record_task_start(agent_id, test_task)
            await memory.record_task_completion(
                agent_id=agent_id,
                task_id=test_task.id,
                success=i > 2,  # First 3 fail, rest succeed
                actual_hours=5.0 + i * 0.5,
                blockers=["database"] if i < 3 else [],
            )

        # Get enhanced predictions
        predictions = await memory.predict_task_outcome_v2(agent_id, task)

        # Debug: print prediction details
        print(f"Predictions: {predictions}")
        print(f"Agent history length: {len(memory.episodic['outcomes'])}")

        # Check enhanced fields
        assert "confidence" in predictions
        assert "confidence_interval" in predictions
        assert "complexity_factor" in predictions
        assert "risk_analysis" in predictions

        # Confidence should be moderate with 10 samples
        assert 0.4 < predictions["confidence"] < 0.8

        # Complexity factor should be high (20 hours vs ~7.5 average)
        assert predictions["complexity_factor"] > 2.0

        # Should identify database as risk
        risk_factors = [
            r["description"] for r in predictions["risk_analysis"]["factors"]
        ]
        assert any("database" in risk for risk in risk_factors)

    @pytest.mark.asyncio
    async def test_dependency_inference(self, setup_environment):
        """Test context system infers dependencies correctly"""
        context = setup_environment["context"]

        # Create tasks with implicit dependencies
        tasks = [
            Task(
                id="1",
                name="Create User Database Schema",
                description="Design user tables",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["database", "schema"],
                dependencies=[],
            ),
            Task(
                id="2",
                name="Build User API",
                description="REST API for users",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["api", "backend"],
                dependencies=[],  # No explicit dependency
            ),
            Task(
                id="3",
                name="Test User API",
                description="API tests",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["test", "api"],
                dependencies=[],
            ),
        ]

        # Analyze with inference
        dep_map = await context.analyze_dependencies(tasks, infer_implicit=True)

        # Debug output
        print(f"Dependency map: {dep_map}")
        print(f"Tasks: {[(t.id, t.name) for t in tasks]}")

        # Should infer that API depends on schema
        assert "1" in dep_map  # Schema has dependents
        assert "2" in dep_map["1"]  # API depends on schema

        # Should infer that tests depend on API
        assert "2" in dep_map  # API has dependents
        assert "3" in dep_map["2"]  # Tests depend on API

        # Test circular dependency detection
        circular_tasks = [
            Task(id="A", name="Task A", dependencies=["B"], **self._task_defaults()),
            Task(id="B", name="Task B", dependencies=["C"], **self._task_defaults()),
            Task(id="C", name="Task C", dependencies=["A"], **self._task_defaults()),
        ]

        dep_map = await context.analyze_dependencies(circular_tasks)
        cycles = context._detect_circular_dependencies(dep_map, circular_tasks)

        assert len(cycles) > 0
        assert any("Task A" in cycle for cycle in cycles)

    @pytest.mark.asyncio
    async def test_granular_configuration(self):
        """Test granular configuration support"""
        from src.config.config_loader import ConfigLoader

        # Create test config
        test_config = {
            "features": {
                "events": {
                    "enabled": True,
                    "store_history": True,
                    "history_limit": 500,
                    "async_handlers": True,
                },
                "context": {
                    "enabled": True,
                    "infer_dependencies": True,
                    "max_depth": 5,
                },
                "memory": {
                    "enabled": True,
                    "learning_rate": 0.2,
                    "min_samples": 10,
                    "use_v2_predictions": True,
                },
            }
        }

        # Mock config loader
        loader = ConfigLoader()
        loader._config = test_config

        # Test feature config retrieval
        events_config = loader.get_feature_config("events")
        assert events_config["enabled"] is True
        assert events_config["store_history"] is True
        assert events_config["history_limit"] == 500

        # Test backward compatibility
        loader._config = {"features": {"events": True}}  # Old format
        events_config = loader.get_feature_config("events")
        assert events_config == {"enabled": True}

    @pytest.mark.asyncio
    async def test_visibility_event_integration(self, setup_environment):
        """Test visibility system integrates with events"""
        events = setup_environment["events"]
        visualizer = setup_environment["visualizer"]

        # Publish various events
        await events.publish(
            EventTypes.TASK_ASSIGNED,
            "marcus",
            {
                "task_id": "123",
                "task_name": "Test Task",
                "agent_id": "agent_1",
                "has_context": True,
                "has_predictions": True,
            },
        )

        await events.publish(
            EventTypes.TASK_PROGRESS,
            "agent_1",
            {
                "task_id": "123",
                "progress": 50,
                "status": "in_progress",
                "message": "Halfway done",
            },
        )

        # Check visualizer captured events
        stats = visualizer.get_event_statistics()
        assert stats["total_events"] >= 2
        assert EventTypes.TASK_ASSIGNED in stats["event_counts"]
        assert EventTypes.TASK_PROGRESS in stats["event_counts"]

    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, setup_environment):
        """Test complete workflow with all systems"""
        events = setup_environment["events"]
        context = setup_environment["context"]
        memory = setup_environment["memory"]

        # Create a project workflow
        tasks = [
            Task(
                id="db_task",
                name="Create Database",
                description="Set up PostgreSQL",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["database", "infrastructure"],
                dependencies=[],
            ),
            Task(
                id="api_task",
                name="Build API",
                description="REST endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["api", "backend"],
                dependencies=["db_task"],
            ),
        ]

        # Analyze dependencies
        dep_map = context.analyze_dependencies(tasks)

        # Simulate agent working on first task
        agent_id = "alice"

        # Record task start
        await memory.record_task_start(agent_id, tasks[0])

        # Add implementation
        await context.add_implementation(
            "db_task",
            {
                "database": "PostgreSQL",
                "schema": {"users": "id, name, email"},
                "connection": "postgres://localhost/app",
            },
        )

        # Log decision
        await context.log_decision(
            agent_id=agent_id,
            task_id="db_task",
            what="Use PostgreSQL",
            why="Need ACID compliance",
            impact="All services must use PG client",
        )

        # Complete task
        await memory.record_task_completion(
            agent_id=agent_id, task_id="db_task", success=True, actual_hours=3.5
        )

        # Get context for next task
        api_context = await context.get_context("api_task", ["db_task"])

        # Verify context includes previous work
        assert "db_task" in api_context.previous_implementations
        assert (
            api_context.previous_implementations["db_task"]["database"] == "PostgreSQL"
        )
        assert len(api_context.architectural_decisions) > 0

        # Get predictions for next agent
        predictions = await memory.predict_task_outcome(agent_id, tasks[1])
        assert "success_probability" in predictions
        assert "estimated_duration" in predictions

    def _task_defaults(self):
        """Default task fields for testing"""
        return {
            "description": "Test task",
            "status": TaskStatus.TODO,
            "priority": Priority.MEDIUM,
            "assigned_to": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "due_date": None,
            "estimated_hours": 4.0,
            "labels": [],
        }


if __name__ == "__main__":
    asyncio.run(pytest.main([__file__, "-v"]))
