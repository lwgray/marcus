#!/usr/bin/env python3
"""Debug the task ordering issue"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.core.context import Context
from src.core.events import Events
from src.core.models import Task, TaskStatus, Priority
from src.core.persistence import Persistence, MemoryPersistence


async def main():
    # Create simple test tasks
    tasks = [
        Task(
            id="deploy",
            name="Deploy",
            description="Deploy to production",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["deploy"],
            dependencies=[]  # No explicit deps
        ),
        Task(
            id="build",
            name="Build API",
            description="Build the API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
            labels=["api", "build"],
            dependencies=[]
        ),
        Task(
            id="setup",
            name="Setup Environment",
            description="Setup dev environment",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=2.0,
            labels=["setup"],
            dependencies=[]
        )
    ]
    
    # Set up context
    persistence = Persistence(backend=MemoryPersistence())
    events = Events(store_history=True, persistence=persistence)
    context = Context(events=events, persistence=persistence)
    
    # Analyze dependencies
    print("Analyzing dependencies...")
    dep_map = await context.analyze_dependencies(tasks, infer_implicit=True)
    
    print("\nDependency map:")
    for dep_id, dependents in dep_map.items():
        dep_task = next(t for t in tasks if t.id == dep_id)
        print(f"{dep_task.name} is required by:")
        for dependent_id in dependents:
            dependent_task = next(t for t in tasks if t.id == dependent_id)
            print(f"  - {dependent_task.name}")
    
    # Get optimal order
    print("\nSuggesting task order...")
    ordered = await context.suggest_task_order(tasks)
    
    print("\nOptimal order:")
    for i, task in enumerate(ordered, 1):
        print(f"{i}. {task.name}")


if __name__ == "__main__":
    asyncio.run(main())