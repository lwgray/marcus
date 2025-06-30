#!/usr/bin/env python3
"""
Create the Smart Recipe Manager project directly
"""

import asyncio
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.integrations.mcp_natural_language_tools import NaturalLanguageProjectCreator
from src.integrations.kanban_client_with_create import KanbanClientWithCreate
from src.ai.core.ai_engine import MarcusAIEngine


async def create_recipe_project():
    """Create the Smart Recipe Manager project"""
    
    project_name = "Smart Recipe Manager"
    description = """Build a web application that helps users manage their recipes, plan meals for the week, and automatically generate shopping lists. 

The app should allow users to:
- Add/edit/delete recipes with ingredients and instructions
- Search recipes by ingredients or dietary restrictions
- Plan meals by dragging recipes to calendar days
- Generate consolidated shopping lists from selected meals
- Scale recipes up/down based on servings
- Track nutritional information

Technical requirements:
- Frontend: React with TypeScript for responsive UI
- Backend: Node.js/Express API with JWT authentication
- Database: PostgreSQL for recipe and user data
- Features: Recipe CRUD, meal planning calendar, shopping list generator
- Additional: Nutritional data integration, recipe sharing, meal prep timers"""

    print(f"Creating project: {project_name}")
    print("=" * 60)
    
    try:
        # Initialize components
        kanban_client = KanbanClientWithCreate()
        ai_engine = MarcusAIEngine()
        
        # Create project creator
        project_creator = NaturalLanguageProjectCreator(kanban_client, ai_engine)
        
        # Create the project
        result = await project_creator.create_project_from_description(
            description=description,
            project_name=project_name,
            options={
                "max_tasks": 20,
                "include_tests": True,
                "tech_stack": ["react", "typescript", "nodejs", "postgresql"]
            }
        )
        
        print(f"\n✅ Project created successfully!")
        print(f"   Created {len(result['tasks'])} tasks")
        
        # Show first few tasks
        print("\nCreated tasks:")
        for i, task in enumerate(result['tasks'][:5], 1):
            print(f"\n{i}. {task.name}")
            if hasattr(task, 'labels') and task.labels:
                print(f"   Labels: {', '.join(task.labels)}")
            if hasattr(task, 'estimated_hours') and task.estimated_hours:
                print(f"   Estimated: {task.estimated_hours} hours")
        
        if len(result['tasks']) > 5:
            print(f"\n   ... and {len(result['tasks']) - 5} more tasks")
            
        return result
        
    except Exception as e:
        print(f"\n❌ Error creating project: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(create_recipe_project())
    if result:
        print(f"\n🎉 Project '{result['project_name']}' is ready on your kanban board!")