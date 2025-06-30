#!/usr/bin/env python3
"""
Debug why PRD parser is not generating tasks
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from marcus import load_config
load_config()

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


async def test_prd_parser():
    """Test PRD parser with FNF description"""
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
        result = await parser.parse_prd_to_tasks(description, constraints)
        print(f"\nGenerated {len(result.tasks)} tasks:")
        
        for i, task in enumerate(result.tasks[:10]):
            print(f"  {i+1}. {task.name}")
            print(f"     Priority: {task.priority}")
            print(f"     Labels: {task.labels}")
            print(f"     Estimated hours: {task.estimated_hours}")
            print()
            
        if len(result.tasks) == 0:
            print("\nDEBUG: No tasks generated!")
            print("Checking if LLM client is working...")
            print(f"LLM client exists: {parser.llm_client is not None}")
            print(f"Providers initialized: {parser.llm_client._providers_initialized}")
            
            # Test the LLM directly
            from src.ai.providers.llm_abstraction import LLMAbstraction
            llm = LLMAbstraction()
            llm._initialize_providers()
            print(f"Available providers: {list(llm.providers.keys())}")
            
            # Try a simple completion
            try:
                response = await llm.analyze("Say hello", type('Context', (), {'max_tokens': 10})())
                print(f"LLM response: {response}")
            except Exception as e:
                print(f"LLM test failed: {e}")
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_prd_parser())