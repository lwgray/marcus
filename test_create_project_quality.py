#!/usr/bin/env python3
"""
Test script to validate create_project task generation quality

This test demonstrates the current issues with task name and description generation
in the create_project tool.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.ai.providers.llm_abstraction import LLMAbstraction


async def test_task_generation_quality():
    """Test the current task generation quality"""
    
    print("🔍 Testing create_project task generation quality...")
    print("=" * 60)
    
    # Test with a realistic PRD
    prd_content = """
    Build a Task Management Application
    
    Requirements:
    - Users can create, edit, and delete tasks
    - Tasks have titles, descriptions, due dates, and priority levels
    - Users can organize tasks into projects
    - Real-time collaboration with team members
    - Email notifications for task updates
    - Mobile-responsive web interface
    - User authentication and authorization
    - Task search and filtering capabilities
    - Export tasks to CSV/PDF
    - Integration with Google Calendar
    """
    
    # Initialize parser
    parser = AdvancedPRDParser()
    constraints = ProjectConstraints(
        team_size=3,
        available_skills=["Python", "React", "PostgreSQL"],
        technology_constraints=["React", "FastAPI", "PostgreSQL"]
    )
    
    print(f"📋 PRD Content:\n{prd_content}")
    print("\n" + "=" * 60)
    
    try:
        # Generate tasks
        result = await parser.parse_prd_to_tasks(prd_content, constraints)
        
        print(f"✅ Generated {len(result.tasks)} tasks")
        print(f"🎯 Generation confidence: {result.generation_confidence:.2f}")
        print("\n📝 Generated Tasks:")
        print("-" * 40)
        
        for i, task in enumerate(result.tasks[:10], 1):  # Show first 10 tasks
            print(f"\n{i}. Task ID: {task.id}")
            print(f"   Name: {task.name}")
            print(f"   Description: {task.description}")
            print(f"   Labels: {task.labels}")
            print(f"   Estimated Hours: {task.estimated_hours}")
            print(f"   Priority: {task.priority}")
        
        # Analyze task quality
        print("\n" + "=" * 60)
        print("🔍 Task Quality Analysis:")
        print("-" * 40)
        
        # Check for generic names
        generic_names = [task for task in result.tasks if "component for" in task.name or "task_" in task.name.lower()]
        print(f"❌ Generic/Poor names: {len(generic_names)}/{len(result.tasks)}")
        
        # Check for meaningful descriptions
        poor_descriptions = [task for task in result.tasks if not task.description or len(task.description) < 20]
        print(f"❌ Poor descriptions: {len(poor_descriptions)}/{len(result.tasks)}")
        
        # Check for PRD-specific content
        prd_specific_tasks = [task for task in result.tasks if any(keyword in task.name.lower() for keyword in ["task management", "collaboration", "notification", "calendar"])]
        print(f"✅ PRD-specific tasks: {len(prd_specific_tasks)}/{len(result.tasks)}")
        
        # Overall quality assessment
        quality_score = (
            (len(result.tasks) - len(generic_names)) / len(result.tasks) * 0.4 +
            (len(result.tasks) - len(poor_descriptions)) / len(result.tasks) * 0.3 +
            len(prd_specific_tasks) / len(result.tasks) * 0.3
        )
        
        print(f"\n📊 Overall Quality Score: {quality_score:.2f}/1.0")
        
        if quality_score < 0.6:
            print("❌ POOR QUALITY: Task generation needs improvement")
        elif quality_score < 0.8:
            print("⚠️  MODERATE QUALITY: Some improvements needed")
        else:
            print("✅ GOOD QUALITY: Task generation looks good")
        
        # Test AI enhancement method directly
        print("\n" + "=" * 60)
        print("🧪 Testing _enhance_task_with_ai method directly:")
        print("-" * 40)
        
        # Simulate what the method does
        test_task_info = {
            'id': 'task_req_0_implement',
            'epic_id': 'epic_req_0',
            'type': 'development',
            'complexity': 'medium'
        }
        
        enhanced = await parser._enhance_task_with_ai(test_task_info, None, constraints)
        print(f"Input task ID: {test_task_info['id']}")
        print(f"Enhanced name: {enhanced.get('name', 'N/A')}")
        print(f"Enhanced description: {enhanced.get('description', 'N/A')}")
        print(f"This shows the method generates generic names from task IDs")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during task generation: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_llm_abstraction_chat():
    """Test if LLMAbstraction has a chat method"""
    print("\n" + "=" * 60)
    print("🔍 Testing LLMAbstraction for chat method...")
    print("-" * 40)
    
    llm = LLMAbstraction()
    
    if hasattr(llm, 'chat'):
        print("✅ LLMAbstraction has chat method")
        try:
            response = await llm.chat("Test message")
            print(f"✅ Chat method works: {response[:100]}...")
        except Exception as e:
            print(f"❌ Chat method exists but fails: {e}")
    else:
        print("❌ LLMAbstraction does NOT have chat method")
        print("   This means the recent commit did not actually add this method")
    
    # List available methods
    methods = [method for method in dir(llm) if not method.startswith('_') and callable(getattr(llm, method))]
    print(f"\n📋 Available methods: {methods}")


async def main():
    """Main test function"""
    print("🚀 Testing create_project task generation quality")
    print("This will help identify why task output 'stinks'")
    print("=" * 60)
    
    # Test task generation
    result = await test_task_generation_quality()
    
    # Test LLM abstraction
    await test_llm_abstraction_chat()
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSION:")
    print("-" * 40)
    print("The issue is in the _enhance_task_with_ai method in AdvancedPRDParser.")
    print("It generates generic names like 'Implement task_req_0_implement' instead")
    print("of using the actual PRD content to create meaningful task names.")
    print("The method needs to be enhanced to use the PRD content intelligently.")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()