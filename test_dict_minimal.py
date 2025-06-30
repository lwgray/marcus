#!/usr/bin/env python3
"""
Minimal test to find dictionary iteration error
"""

import asyncio
import sys
import logging
import traceback
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')

# Import and test just the problem areas
from src.integrations.nlp_task_utils import TaskType, TaskClassifier


def test_task_classifier():
    """Test TaskClassifier to see if it causes the error"""
    print("Testing TaskClassifier...")
    
    # Test the TASK_KEYWORDS dictionary
    print(f"TASK_KEYWORDS keys: {list(TaskClassifier.TASK_KEYWORDS.keys())}")
    
    # Test enum iteration
    print(f"TaskType values: {list(TaskType)}")
    
    # Test classification
    from src.core.models import Task, TaskStatus, Priority
    from datetime import datetime
    
    task = Task(
        id="1",
        name="Deploy to production",
        description="Deploy the application",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["deployment"],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        estimated_hours=2,
        dependencies=[],
        due_date=None
    )
    
    result = TaskClassifier.classify(task)
    print(f"Classification result: {result}")
    
    # Test dictionary comprehension
    classified = {task_type: [] for task_type in list(TaskType)}
    print(f"Classified dict: {classified}")


async def test_dependency_inferer():
    """Test dependency inferer"""
    print("\n\nTesting DependencyInferer...")
    
    from src.intelligence.dependency_inferer import DependencyInferer
    from src.core.models import Task, TaskStatus, Priority
    from datetime import datetime
    
    tasks = []
    for i in range(3):
        task = Task(
            id=str(i),
            name=f"Task {i}",
            description=f"Description {i}",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["test"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_hours=1,
            dependencies=[],
            due_date=None
        )
        tasks.append(task)
    
    inferer = DependencyInferer()
    
    try:
        print("Before infer_dependencies...")
        graph = await inferer.infer_dependencies(tasks)
        print(f"Success! Created graph with {len(graph.nodes)} nodes")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    try:
        test_task_classifier()
        asyncio.run(test_dependency_inferer())
    except Exception as e:
        print(f"\nError occurred: {type(e).__name__}: {e}")
        traceback.print_exc()