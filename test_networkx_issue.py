#!/usr/bin/env python3
"""
Test to isolate the NetworkX issue
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Test if NetworkX is being used in our dependencies
try:
    from src.intelligence.dependency_inferer import DependencyInferer
    from src.core.models import Task, TaskStatus, Priority
    from datetime import datetime
    
    print("Testing DependencyInferer...")
    
    # Create multiple tasks like a complex project would
    tasks = []
    for i in range(15):
        task = Task(
            id=str(i),
            name=f"Task {i}: Complex feature implementation",
            description=f"Implement complex feature {i} with multiple dependencies",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["feature", "complex", "backend", "frontend"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            estimated_hours=8,
            dependencies=[],
            due_date=None
        )
        tasks.append(task)
    
    print(f"Created {len(tasks)} tasks")
    
    # Test dependency inference
    inferer = DependencyInferer()
    
    print("Running dependency inference...")
    
    # This is where the error likely occurs
    import asyncio
    graph = asyncio.run(inferer.infer_dependencies(tasks))
    
    print(f"Success! Graph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    
    # Check if NetworkX is involved
    tb_str = traceback.format_exc()
    if 'networkx' in tb_str.lower():
        print("\nNetworkX is involved in the error!")
    else:
        print("\nNetworkX not directly involved")