#!/usr/bin/env python3
"""
Demo: Using Marcus with Natural Language

This demonstrates how to use Marcus's natural language capabilities
to create and manage a project from a simple description.
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.ai.enrichment.intelligent_enricher import IntelligentTaskEnricher, ProjectContext
from src.ai.core.ai_engine import MarcusAIEngine
from src.core.models import Task, TaskStatus, Priority
# from src.modes.mode_engine import ModeEngine  # Not needed for demo
from src.detection.board_analyzer import BoardAnalyzer
from src.detection.context_detector import ContextDetector


async def demo_prd_to_tasks():
    """Demo 1: Convert natural language PRD to tasks"""
    print("=== Demo 1: Natural Language PRD to Tasks ===\n")
    
    parser = AdvancedPRDParser()
    
    # Natural language project description
    prd_content = """
    Project: E-commerce Mobile App
    
    We need to build a mobile e-commerce application for selling handmade crafts.
    
    Core Features:
    - Users can browse products by category (pottery, jewelry, textiles)
    - Search products by name, artist, or style
    - View detailed product pages with multiple images
    - Add items to shopping cart
    - Secure checkout with credit card and PayPal
    - Order tracking and history
    - Artist profiles showing all their products
    - Customer reviews and ratings
    
    Technical Requirements:
    - React Native for cross-platform mobile
    - Node.js/Express backend API
    - PostgreSQL database
    - Stripe for payments
    - AWS S3 for image storage
    
    Quality Requirements:
    - App should load in under 3 seconds
    - Support offline browsing of previously viewed items
    - Handle 1000 concurrent users
    - 99.9% uptime
    
    Timeline: Need MVP in 3 months with a team of 4 developers
    """
    
    # Set realistic constraints
    constraints = ProjectConstraints(
        team_size=4,
        available_skills=['React Native', 'Node.js', 'PostgreSQL', 'AWS'],
        technology_constraints=['React Native', 'Node.js', 'PostgreSQL', 'Stripe', 'AWS'],
        quality_requirements={
            'performance': 'Load time < 3s',
            'scalability': '1000 concurrent users',
            'availability': '99.9% uptime'
        }
    )
    
    print("Parsing PRD and generating tasks...\n")
    result = await parser.parse_prd_to_tasks(prd_content, constraints)
    
    print(f"📋 Generated {len(result.tasks)} tasks:\n")
    for i, task in enumerate(result.tasks[:10], 1):  # Show first 10
        print(f"{i}. {task.name}")
        print(f"   Description: {task.description}")
        print(f"   Estimated: {task.estimated_hours} hours")
        print(f"   Labels: {', '.join(task.labels)}")
        print()
    
    print(f"\n🔗 Dependencies: {len(result.dependencies)} identified")
    print(f"📅 Timeline: {result.estimated_timeline['estimated_duration_days']} days")
    print(f"⚠️  Risk Level: {result.risk_assessment['overall_risk_level']}")
    print(f"👥 Optimal Team Size: {result.resource_requirements['estimated_team_size']}")
    
    print("\n✅ Success Criteria:")
    for criteria in result.success_criteria[:5]:
        print(f"   - {criteria}")
    
    return result.tasks


async def demo_task_enhancement():
    """Demo 2: Enhance a simple task with AI"""
    print("\n\n=== Demo 2: Natural Language Task Enhancement ===\n")
    
    enricher = IntelligentTaskEnricher()
    
    # Create a simple task with natural language
    simple_task = Task(
        id="task-payment",
        name="Add payment processing",
        description="Users should be able to pay with credit cards",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=None,
        dependencies=[],
        labels=[]
    )
    
    # Create project context
    context = ProjectContext(
        project_type='ecommerce',
        tech_stack=['react-native', 'nodejs', 'stripe'],
        team_size=4,
        existing_tasks=[],
        project_standards={
            'security': 'PCI compliance required',
            'testing': 'Unit tests required'
        },
        historical_data=[],
        quality_requirements={'security': 'high'}
    )
    
    print(f"Original task: {simple_task.name}")
    print(f"Description: {simple_task.description}\n")
    
    print("Enhancing with AI...\n")
    enhanced = await enricher.enrich_task_with_ai(simple_task, context)
    
    print("Enhanced Task Details:")
    print(f"📝 Enhanced Description:\n{enhanced.enhanced_description}\n")
    
    print("✅ Acceptance Criteria:")
    for criterion in enhanced.acceptance_criteria:
        print(f"   - {criterion}")
    
    print(f"\n🏷️  Suggested Labels: {', '.join(enhanced.suggested_labels)}")
    print(f"⏱️  Estimated Effort: {enhanced.estimated_effort_hours} hours")
    print(f"🎯 Priority: {enhanced.priority_recommendation}")
    
    print("\n⚠️  Technical Considerations:")
    for consideration in enhanced.technical_considerations:
        print(f"   - {consideration}")


async def demo_intelligent_mode_selection():
    """Demo 3: Natural language triggers correct mode"""
    print("\n\n=== Demo 3: Intelligent Mode Selection ===\n")
    
    analyzer = BoardAnalyzer()
    detector = ContextDetector()
    
    # Scenario 1: Empty board - should trigger Creator Mode
    print("Scenario 1: Starting new project")
    print('User says: "I want to build a recipe sharing app"\n')
    
    board_state = analyzer.analyze_board([])  # Empty board
    context = detector.detect_context(
        board_state=board_state,
        tasks=[],
        recent_activity=[],
        team_velocity={'average_completion_time': 0}
    )
    
    print(f"Detected context: {context.primary_mode}")
    print(f"Reasoning: {context.confidence_scores}\n")
    
    # Scenario 2: Existing project - should trigger Adaptive Mode
    existing_tasks = [
        Task(
            id=f"task-{i}",
            name=name,
            description="",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8,
            dependencies=[],
            labels=[]
        )
        for i, name in enumerate([
            "Set up React Native project",
            "Design database schema",
            "Create API endpoints"
        ])
    ]
    
    print("Scenario 2: Adding to existing project")
    print('User says: "Add user authentication feature"\n')
    
    board_state2 = analyzer.analyze_board(existing_tasks)
    context2 = detector.detect_context(
        board_state=board_state2,
        tasks=existing_tasks,
        recent_activity=[],
        team_velocity={'average_completion_time': 2.5}
    )
    
    print(f"Detected context: {context2.primary_mode}")
    print(f"Well-structured score: {board_state2.structure_metrics['well_structured_score']:.2f}")


async def demo_natural_conversation():
    """Demo 4: Natural conversation flow"""
    print("\n\n=== Demo 4: Natural Conversation Examples ===\n")
    
    print("Example conversations you can have with Marcus:\n")
    
    conversations = [
        {
            "context": "Starting a new project",
            "user": "I need to build a fitness tracking app with social features",
            "marcus_action": "Creates complete project structure with phases: Design, Backend, Frontend, Integration, Testing, Deployment"
        },
        {
            "context": "Adding a feature",
            "user": "Add a feature where users can share their workout routines",
            "marcus_action": "Creates task with dependencies on user auth and database, estimates 24 hours, adds labels: feature, social, backend, frontend"
        },
        {
            "context": "Asking for help",
            "user": "What should I work on next?",
            "marcus_action": "Analyzes dependencies and team capacity, suggests: 'Work on API authentication endpoints - it's blocking 3 other tasks'"
        },
        {
            "context": "Project planning",
            "user": "How long will it take to build a MVP with 3 developers?",
            "marcus_action": "Analyzes all tasks and dependencies, responds: 'Estimated 45 days with 3 developers working in parallel. Critical path: Database → API → Frontend → Testing'"
        },
        {
            "context": "Organizing chaos",
            "user": "These tasks are a mess, can you organize them?",
            "marcus_action": "Groups related tasks, adds missing dependencies, suggests phases, enriches descriptions, identifies gaps"
        }
    ]
    
    for conv in conversations:
        print(f"\n💬 {conv['context']}:")
        print(f"   You: \"{conv['user']}\"")
        print(f"   Marcus: {conv['marcus_action']}")


async def demo_safety_check():
    """Demo 5: Natural language with safety checks"""
    print("\n\n=== Demo 5: Safety Intelligence ===\n")
    
    engine = MarcusAIEngine()
    
    print("Marcus prevents illogical requests:\n")
    
    # Create a deployment task
    deploy_task = Task(
        id="deploy-1",
        name="Deploy to production",
        description="Deploy the app to production servers",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=4,
        dependencies=[],
        labels=['deployment']
    )
    
    # Create implementation task (not complete)
    impl_task = Task(
        id="impl-1",
        name="Build core features",
        description="Implement main app functionality",
        status=TaskStatus.TODO,  # Not done yet!
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=None,
        estimated_hours=40,
        dependencies=[],
        labels=['implementation']
    )
    
    from src.ai.types import AnalysisContext
    
    context = AnalysisContext(
        task=deploy_task,
        project_context={
            'available_tasks': [impl_task],
            'assigned_tasks': {},
            'project_type': 'web'
        },
        historical_data=[]
    )
    
    print("Checking: Can we deploy to production?")
    result = await engine.analyze_with_hybrid_intelligence(context)
    
    print(f"\n🚫 Decision: {'Allowed' if result.allow_assignment else 'BLOCKED'}")
    print(f"📊 Confidence: {result.confidence:.0%}")
    print(f"❓ Reason: {result.reason}")
    print(f"⚠️  Safety Critical: {result.safety_critical}")
    
    print("\nMarcus understands natural language but enforces logical constraints!")


async def main():
    """Run all demos"""
    print("🤖 Marcus Natural Language Demo\n")
    print("This demo shows how to use Marcus with natural language input.\n")
    
    # Run demos
    tasks = await demo_prd_to_tasks()
    await demo_task_enhancement()
    await demo_intelligent_mode_selection()
    await demo_natural_conversation()
    await demo_safety_check()
    
    print("\n\n🎉 Demo Complete!")
    print("\nTo use Marcus with natural language:")
    print("1. Start with a PRD or project description")
    print("2. Marcus converts it to structured tasks")
    print("3. Use natural language to add features") 
    print("4. Marcus maintains logical dependencies")
    print("5. Safety checks prevent illogical operations")
    
    print("\n💡 Try it yourself:")
    print("   python marcus_mcp_server.py")
    print("   Then describe your project in plain English!")


if __name__ == "__main__":
    # Set test mode to avoid API calls
    os.environ['MARCUS_AI_ENABLED'] = 'false'
    asyncio.run(main())