#!/usr/bin/env python3
"""
Example workflow demonstrating Marcus enhanced features:
- Events for monitoring
- Context for dependency awareness
- Memory for learning and prediction

This simulates a small project with multiple agents working on related tasks.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add marcus to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.context import Context, DependentTask
from src.core.events import Events, EventTypes
from src.core.memory import Memory
from src.core.models import Priority, Task, TaskStatus, WorkerStatus
from src.core.persistence import Persistence, SQLitePersistence


class MockMarcus:
    """Simplified Marcus for demonstration"""

    def __init__(self) -> None:
        # Create persistence
        self.persistence = Persistence(
            backend=SQLitePersistence(Path("./demo_marcus.db"))
        )

        # Create enhanced systems
        self.events = Events(store_history=True, persistence=self.persistence)
        self.context = Context(events=self.events, persistence=self.persistence)
        self.memory = Memory(events=self.events, persistence=self.persistence)

        # Sample agents
        self.agents = {
            "alice": WorkerStatus(
                worker_id="alice",
                name="Alice",
                role="Backend Developer",
                email="alice@example.com",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=["python", "api", "database"],
                availability={"monday": True, "tuesday": True},
            ),
            "bob": WorkerStatus(
                worker_id="bob",
                name="Bob",
                role="Frontend Developer",
                email="bob@example.com",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=["javascript", "react", "ui"],
                availability={"monday": True, "tuesday": True},
            ),
            "charlie": WorkerStatus(
                worker_id="charlie",
                name="Charlie",
                role="Full Stack Developer",
                email="charlie@example.com",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=["python", "javascript", "testing"],
                availability={"monday": True, "tuesday": True},
            ),
        }

        # Sample tasks for a todo app project
        self.tasks = [
            Task(
                id="task_1",
                name="Design Database Schema",
                description="Design schema for todo items",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["database", "backend"],
                dependencies=[],
            ),
            Task(
                id="task_2",
                name="Build Todo API",
                description="Create REST API for todo operations",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=8.0,
                labels=["api", "backend", "python"],
                dependencies=["task_1"],
            ),
            Task(
                id="task_3",
                name="Create Todo UI",
                description="Build React components for todo list",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=6.0,
                labels=["frontend", "react", "ui"],
                dependencies=["task_2"],
            ),
            Task(
                id="task_4",
                name="Add API Tests",
                description="Write tests for todo API endpoints",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
                labels=["testing", "backend", "python"],
                dependencies=["task_2"],
            ),
        ]

    async def run_demo(self) -> None:
        """Run the demo workflow"""
        print("🚀 Marcus Enhanced Features Demo\n")

        # Subscribe to events for monitoring
        async def event_monitor(event: Any) -> None:
            print(
                f"📡 Event: {event.event_type} | Source: {event.source} | "
                f"Data: {json.dumps(event.data, indent=2)}"
            )

        self.events.subscribe("*", event_monitor)

        # Analyze dependencies
        print("1️⃣ Analyzing task dependencies...")
        dep_map = self.context.analyze_dependencies(self.tasks)
        print(f"Dependencies found: {json.dumps(dep_map, indent=2)}\n")

        # Simulate Alice working on database schema
        print("2️⃣ Alice requests work...")
        task_1 = await self.assign_task("alice", self.tasks[0])

        print("\n3️⃣ Alice completes database schema...")
        await self.complete_task("alice", task_1, success=True, actual_hours=3.5)

        # Alice logs a decision
        await self.context.log_decision(
            agent_id="alice",
            task_id="task_1",
            what="Use PostgreSQL with normalized schema",
            why="Need ACID compliance and complex queries",
            impact="All backend services must use PostgreSQL adapter",
        )

        # Add implementation details
        await self.context.add_implementation(
            "task_1",
            {
                "schema": {
                    "todos": "id, title, description, completed, created_at, user_id",
                    "users": "id, email, password_hash, created_at",
                },
                "database": "PostgreSQL",
                "patterns": [{"type": "database", "name": "normalized"}],
            },
        )

        # Bob requests work - will get API task with context
        print("\n4️⃣ Bob requests work...")
        task_2 = await self.assign_task("bob", self.tasks[1])

        # Simulate Bob having issues
        print("\n5️⃣ Bob encounters a blocker...")
        await self.report_progress(
            "bob", task_2, "blocked", 50, "Can't connect to PostgreSQL database"
        )

        # Charlie helps complete the API
        print("\n6️⃣ Charlie takes over API task...")
        task_2_retry = await self.assign_task("charlie", self.tasks[1])
        await self.complete_task(
            "charlie", task_2_retry, success=True, actual_hours=9.0
        )

        # Add API implementation
        await self.context.add_implementation(
            "task_2",
            {
                "endpoints": [
                    "GET /api/todos",
                    "POST /api/todos",
                    "PUT /api/todos/:id",
                    "DELETE /api/todos/:id",
                ],
                "authentication": "JWT tokens",
                "patterns": [{"type": "api", "name": "RESTful"}],
            },
        )

        # Bob gets UI task with full context
        print("\n7️⃣ Bob requests UI work...")
        task_3 = await self.assign_task("bob", self.tasks[2])

        # Show memory statistics
        print("\n8️⃣ Memory System Statistics:")
        stats = self.memory.get_memory_stats()
        print(json.dumps(stats, indent=2))

        # Show agent profiles
        print("\n9️⃣ Agent Profiles:")
        for agent_id in ["alice", "bob", "charlie"]:
            if agent_id in self.memory.semantic["agent_profiles"]:
                profile = self.memory.semantic["agent_profiles"][agent_id]
                print(f"\n{agent_id.capitalize()}:")
                print(f"  Total tasks: {profile.total_tasks}")
                print(f"  Success rate: {profile.success_rate:.1%}")
                print(f"  Skills: {profile.skill_success_rates}")

        # Cleanup
        print("\n✅ Demo complete!")
        if Path("./demo_marcus.db").exists():
            Path("./demo_marcus.db").unlink()

    async def assign_task(self, agent_id: str, task: Task) -> Task:
        """Simulate task assignment with context and predictions"""
        print(f"\n📋 Assigning '{task.name}' to {agent_id}")

        # Get predictions
        predictions = await self.memory.predict_task_outcome(agent_id, task)
        print(
            f"   Predictions: Success={predictions['success_probability']:.1%}, "
            f"Duration={predictions['estimated_duration']:.1f}h"
        )

        # Get context
        context = await self.context.get_context(task.id, task.dependencies or [])
        if context.previous_implementations:
            print(
                f"   Context: {len(context.previous_implementations)} previous implementations"
            )
        if context.architectural_decisions:
            print(
                f"   Decisions: {len(context.architectural_decisions)} relevant decisions"
            )

        # Record in memory
        await self.memory.record_task_start(agent_id, task)

        # Emit event
        await self.events.publish(
            EventTypes.TASK_ASSIGNED,
            "marcus",
            {"agent_id": agent_id, "task_id": task.id, "task_name": task.name},
        )

        return task

    async def complete_task(
        self, agent_id: str, task: Task, success: bool, actual_hours: float
    ) -> None:
        """Simulate task completion"""
        outcome = await self.memory.record_task_completion(
            agent_id=agent_id,
            task_id=task.id,
            success=success,
            actual_hours=actual_hours,
            blockers=[],
        )

        print(
            f"   ✅ Completed: Success={success}, Time={actual_hours}h, "
            f"Accuracy={outcome.estimation_accuracy:.1%}"
        )

    async def report_progress(
        self, agent_id: str, task: Task, status: str, progress: int, message: str
    ):
        """Simulate progress report"""
        if status == "blocked":
            await self.memory.record_task_completion(
                agent_id=agent_id,
                task_id=task.id,
                success=False,
                actual_hours=4.0,  # Time spent before blocking
                blockers=[message],
            )

        await self.events.publish(
            (
                EventTypes.TASK_BLOCKED
                if status == "blocked"
                else EventTypes.TASK_PROGRESS
            ),
            agent_id,
            {
                "task_id": task.id,
                "status": status,
                "progress": progress,
                "message": message,
            },
        )


async def main() -> None:
    """Run the demo"""
    marcus = MockMarcus()
    await marcus.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
