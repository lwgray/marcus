#!/usr/bin/env python3
"""
Test PRD parser directly to debug the issue
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from marcus import load_config
load_config()

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints


async def test_prd_parser():
    """Test PRD parser directly"""
    
    parser = AdvancedPRDParser()
    
    description = """Create a Friday Night Funkin' rhythm game clone with the following features:
- Core rhythm gameplay with arrow key inputs synced to music
- Health bar system that responds to player performance
- Multiple difficulty levels (Easy, Normal, Hard)
- Character animation system for Boyfriend, Girlfriend, and opponents
- Song chart system to define note patterns"""
    
    constraints = ProjectConstraints(
        team_size=3,
        available_skills=["JavaScript", "HTML5", "Canvas", "Web Audio API"],
        technology_constraints=["JavaScript", "HTML5", "Canvas", "Web Audio API"]
    )
    
    print(f"Testing PRD parser with Friday Night Funkin' description")
    print(f"Description: {description[:100]}...")
    
    result = await parser.parse_prd_to_tasks(description, constraints)
    
    print(f"\nResult:")
    print(f"  Tasks generated: {len(result.tasks)}")
    print(f"  Task hierarchy epics: {len(result.task_hierarchy)}")
    print(f"  Dependencies: {len(result.dependencies)}")
    print(f"  Confidence: {result.generation_confidence}")
    
    if result.tasks:
        print("\nFirst 5 tasks:")
        for task in result.tasks[:5]:
            print(f"  - {task.name} (Priority: {task.priority}, Hours: {task.estimated_hours})")
    else:
        print("\nNo tasks generated!")
        print(f"Task hierarchy: {result.task_hierarchy}")


if __name__ == "__main__":
    asyncio.run(test_prd_parser())