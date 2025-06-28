#!/usr/bin/env python3
"""
Standalone test for NLP project creation on board
This version doesn't require marcus_mcp_server to be running
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.integrations.kanban_factory import KanbanFactory
from src.ai.core.ai_engine import MarcusAIEngine
from mcp_natural_language_tools import NaturalLanguageProjectCreator

async def test_standalone_nlp_creation():
    """Test NLP project creation without running the full MCP server"""
    
    # Load environment
    load_dotenv()
    provider = os.getenv('KANBAN_PROVIDER', 'planka')
    
    print(f"🔧 Standalone NLP test with {provider}...")
    
    # Initialize components
    kanban_client = KanbanFactory.create(provider)  # Not async
    ai_engine = MarcusAIEngine()
    
    print("✓ Initialized kanban client and AI engine")
    
    # Create project creator
    creator = NaturalLanguageProjectCreator(kanban_client, ai_engine)
    
    # Test project creation
    project_name = f"Standalone Test {datetime.now():%Y%m%d_%H%M%S}"
    description = "I need a simple blog with posts and comments"
    
    print(f"\n📝 Creating project: {project_name}")
    print(f"   Description: {description}")
    
    try:
        # Create the project
        result = await creator.create_project_from_description(
            description=description,
            project_name=project_name,
            options={"team_size": 1}
        )
        
        if result["success"]:
            print(f"\n✅ Project created successfully!")
            print(f"   - Tasks created: {result['tasks_created']}")
            print(f"   - Phases: {', '.join(result['phases'])}")
            print(f"   - Dependencies: {result['dependencies_mapped']}")
            
            # Verify on board
            print(f"\n🔍 Verifying on {provider} board...")
            # Use get_available_tasks which exists in the simple client
            tasks = await kanban_client.get_available_tasks()
            
            # Find our tasks
            our_tasks = [
                t for t in tasks
                if project_name in (t.title or '') or
                   project_name in (t.description or '')
            ]
            
            print(f"✓ Found {len(our_tasks)} tasks on board")
            
            if our_tasks:
                print("\n📋 First 3 tasks:")
                for i, task in enumerate(our_tasks[:3]):
                    print(f"   {i+1}. {task.title}")
                    if task.labels:
                        print(f"      Labels: {', '.join(task.labels)}")
                        
            return True
        else:
            print(f"❌ Failed to create project: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_standalone_nlp_creation())
    print(f"\n{'='*60}")
    print(f"Test {'PASSED' if success else 'FAILED'}")
    exit(0 if success else 1)