#!/usr/bin/env python3
"""
Simple test to check if PRD parser generates tasks
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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
- Song chart system to define note patterns
- At least 3 playable songs with increasing difficulty
- Main menu and song selection screen
- Score tracking and combo system
- Visual feedback for hit accuracy (Sick, Good, Bad, Miss)
- Background stages with animated elements
- Modular architecture to support adding new songs and characters
- Use HTML5 Canvas or WebGL for rendering
- Audio system with precise timing for rhythm gameplay"""
    
    constraints = ProjectConstraints(
        team_size=3,
        technology_constraints=["JavaScript", "HTML5", "Canvas/WebGL", "Web Audio API"]
    )
    
    print("Testing PRD parser...")
    print(f"Description: {description[:100]}...")
    print(f"Constraints: team_size={constraints.team_size}")
    
    try:
        # Parse PRD to tasks
        result = await parser.parse_prd_to_tasks(description, constraints)
        
        print(f"\nGenerated {len(result.tasks)} tasks!")
        print(f"Task hierarchy has {len(result.task_hierarchy)} epics")
        print(f"Dependencies: {len(result.dependencies)}")
        print(f"Risk level: {result.risk_assessment.get('overall_risk_level', 'unknown')}")
        print(f"Confidence: {result.generation_confidence}")
        
        # Show first 10 tasks
        print("\nFirst 10 tasks:")
        for i, task in enumerate(result.tasks[:10]):
            print(f"\n{i+1}. {task.name}")
            print(f"   ID: {task.id}")
            print(f"   Priority: {task.priority}")
            print(f"   Labels: {task.labels}")
            print(f"   Estimated hours: {task.estimated_hours}")
            if hasattr(task, 'description'):
                print(f"   Description: {task.description[:100]}...")
                
        # Show task hierarchy
        print("\nTask Hierarchy:")
        for epic_id, task_ids in list(result.task_hierarchy.items())[:5]:
            print(f"\n{epic_id}:")
            for task_id in task_ids:
                print(f"  - {task_id}")
                
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_prd_parser())