#!/usr/bin/env python3
"""
Test create_project functionality to debug why it returns 0 tasks
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from marcus import load_config
load_config()

from src.integrations.mcp_natural_language_tools import NaturalLanguageProjectCreator
from src.integrations.kanban_factory import KanbanFactory
from src.ai.core.ai_engine import MarcusAIEngine


async def test_create_project():
    """Test project creation from natural language"""
    
    # Initialize components
    print("Initializing components...")
    kanban_factory = KanbanFactory()
    kanban_client = kanban_factory.create("planka")
    ai_engine = MarcusAIEngine()
    
    creator = NaturalLanguageProjectCreator(kanban_client, ai_engine)
    
    # Test description
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
    
    project_name = "FNF Clone Test"
    
    print(f"Creating project: {project_name}")
    print(f"Description: {description[:100]}...")
    
    try:
        # Test process_natural_language directly
        print("\nTesting process_natural_language...")
        tasks = await creator.process_natural_language(description, project_name)
        print(f"process_natural_language returned {len(tasks)} tasks")
        
        if tasks:
            print("\nFirst 5 tasks:")
            for i, task in enumerate(tasks[:5]):
                print(f"  {i+1}. {task.name}")
                print(f"     Priority: {task.priority}")
                print(f"     Labels: {task.labels}")
        else:
            print("\nNo tasks generated!")
            
            # Let's debug the PRD parser directly
            from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
            
            parser = AdvancedPRDParser()
            constraints = ProjectConstraints(team_size=3)
            
            print("\nTesting PRD parser directly...")
            result = await parser.parse_prd_to_tasks(description, constraints)
            print(f"PRD parser returned {len(result.tasks)} tasks")
            print(f"Task hierarchy: {result.task_hierarchy}")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_create_project())