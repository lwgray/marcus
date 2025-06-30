#!/usr/bin/env python3
"""
Test PRD simulation without LLM
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from marcus import load_config
load_config()

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser


async def test_simulation():
    """Test PRD simulation directly"""
    
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
    
    print("Testing PRD simulation...")
    
    # Call simulation directly
    analysis_data = await parser._simulate_prd_analysis(description)
    
    print(f"\nSimulation Results:")
    print(f"Functional requirements: {len(analysis_data['functional_requirements'])}")
    for req in analysis_data['functional_requirements']:
        print(f"  - {req['id']}: {req['description']}")
    
    print(f"\nNon-functional requirements: {len(analysis_data['non_functional_requirements'])}")
    for req in analysis_data['non_functional_requirements']:
        print(f"  - {req['id']}: {req['description']}")
        
    print(f"\nTechnical constraints: {analysis_data['technical_constraints']}")
    print(f"Complexity: {analysis_data['complexity_assessment']}")
    print(f"Confidence: {analysis_data['confidence']}")


if __name__ == "__main__":
    asyncio.run(test_simulation())