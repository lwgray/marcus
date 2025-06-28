#!/usr/bin/env python3
"""
Simple Natural Language Demo for Marcus

Shows how to use Marcus with natural language input
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.models import Task, TaskStatus, Priority


async def demo_natural_language():
    """Show how to convert natural language to tasks"""
    
    print("🤖 Marcus Natural Language Demo\n")
    print("=" * 60)
    
    # Create the PRD parser
    parser = AdvancedPRDParser()
    
    # Example 1: Simple project description
    print("\n📝 Example 1: Simple Project Description")
    print("-" * 40)
    
    simple_project = """
    I want to build a todo list app where users can:
    - Create, edit, and delete tasks
    - Mark tasks as complete
    - Set due dates and priorities
    - Get reminders for overdue tasks
    
    Use React for the frontend and Node.js for the backend.
    """
    
    print("Input:", simple_project)
    
    # Parse it
    result = await parser.parse_prd_to_tasks(
        simple_project,
        ProjectConstraints(team_size=2)
    )
    
    print(f"\n✅ Generated {len(result.tasks)} tasks:")
    for task in result.tasks[:5]:  # Show first 5
        print(f"   • {task.name}")
    
    # Example 2: More detailed requirements
    print("\n\n📝 Example 2: Detailed E-commerce Requirements")
    print("-" * 40)
    
    detailed_project = """
    E-commerce Platform Requirements:
    
    Customer Features:
    - Browse products with filters (category, price, brand)
    - Search with autocomplete
    - Product details with images and reviews
    - Shopping cart with save for later
    - Guest checkout or account creation
    - Multiple payment methods (card, PayPal, Apple Pay)
    - Order tracking with email notifications
    
    Admin Features:
    - Product management (CRUD operations)
    - Inventory tracking
    - Order management and fulfillment
    - Sales analytics dashboard
    - Customer support tools
    
    Technical Requirements:
    - Mobile-responsive design
    - Page load time < 2 seconds
    - Handle Black Friday traffic (10x normal)
    - PCI compliant payment processing
    - GDPR compliant data handling
    
    Tech Stack: React, Node.js, PostgreSQL, Redis, AWS
    Team: 4 developers, 3 month deadline
    """
    
    print("Input: [Detailed e-commerce requirements...]")
    
    # Parse with constraints
    constraints = ProjectConstraints(
        team_size=4,
        available_skills=['React', 'Node.js', 'PostgreSQL', 'AWS'],
        deadline=datetime.now().replace(month=datetime.now().month + 3)
    )
    
    result2 = await parser.parse_prd_to_tasks(detailed_project, constraints)
    
    print(f"\n✅ Generated {len(result2.tasks)} tasks")
    print(f"⏱️  Estimated timeline: {result2.estimated_timeline['estimated_duration_days']} days")
    print(f"🔗 Dependencies mapped: {len(result2.dependencies)}")
    print(f"⚠️  Risk level: {result2.risk_assessment['overall_risk_level']}")
    
    # Show task breakdown by phase
    print("\n📊 Task Breakdown by Type:")
    task_types = {}
    for task in result2.tasks:
        task_type = task.labels[0] if task.labels else 'other'
        task_types[task_type] = task_types.get(task_type, 0) + 1
    
    for task_type, count in sorted(task_types.items()):
        print(f"   • {task_type}: {count} tasks")
    
    # Example 3: Natural language commands
    print("\n\n📝 Example 3: Natural Language Commands")
    print("-" * 40)
    
    print("You can use natural language in many ways:\n")
    
    commands = [
        ("Create project", "I need a blog with comments and user accounts"),
        ("Add feature", "Add social login with Google and Facebook"),
        ("Ask for help", "What tasks are blocking deployment?"),
        ("Get estimate", "How long to add payment processing?"),
        ("Organize", "Group these tasks by feature area"),
    ]
    
    for action, command in commands:
        print(f"🗣️  {action}: \"{command}\"")
    
    # Show safety example
    print("\n\n🛡️  Safety Example: Marcus prevents illogical requests")
    print("-" * 40)
    
    print("❌ User: 'Deploy to production'")
    print("   Marcus: 'Cannot deploy - implementation tasks are not complete'")
    print("\n✅ User: 'What needs to be done before deployment?'")
    print("   Marcus: 'Complete: API development (24h), Frontend integration (16h), Testing (8h)'")
    
    # Usage instructions
    print("\n\n💡 How to Use Marcus with Natural Language:")
    print("-" * 40)
    print("1. Start Marcus MCP server: python marcus_mcp_server.py")
    print("2. In Claude Desktop, describe your project naturally")
    print("3. Marcus will create tasks, dependencies, and estimates")
    print("4. Continue adding features with natural language")
    print("5. Marcus maintains logical order and prevents mistakes")
    
    print("\n✨ Marcus understands context and intent, not just keywords!")


async def main():
    """Run the demo"""
    # Set to test mode
    os.environ['MARCUS_AI_ENABLED'] = 'false'
    
    await demo_natural_language()
    
    print("\n\n🎉 Demo complete! Try it with your own project descriptions.")


if __name__ == "__main__":
    asyncio.run(main())