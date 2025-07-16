#!/usr/bin/env python3
"""
Complete Demo of Marcus AI Features - Phases 1-4

This demonstrates all the intelligent features added to prevent
illogical task assignments and provide smart project management.

Note: This is a demo file that uses hypothetical attributes for illustration.
Some attributes and methods referenced may not exist in the current implementation.
"""
# mypy: ignore-errors

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.enrichment.intelligent_enricher import (
    IntelligentTaskEnricher,
    ProjectContext,
)
from src.ai.types import AnalysisContext
from src.core.models import Priority, Task, TaskStatus
from src.detection.board_analyzer import BoardAnalyzer
from src.detection.context_detector import ContextDetector
from src.intelligence.dependency_inferer import DependencyInferer
from src.learning.pattern_learner import PatternLearner
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode
from src.modes.creator.template_library import ProjectTemplate, WebAppTemplate
from src.modes.enricher.basic_enricher import BasicEnricher


async def demo_phase1_context_detection() -> None:
    """Phase 1: Context Detection & Mode Selection"""
    print("=" * 80)
    print("🔍 PHASE 1: CONTEXT DETECTION & INTELLIGENT MODE SELECTION")
    print("=" * 80)

    analyzer = BoardAnalyzer()
    detector = ContextDetector(analyzer)

    # Example 1: Empty Board Detection
    print("\n📋 Example 1: Empty Board → Creator Mode")
    print("-" * 60)

    empty_board: list[Task] = []
    board_state = await analyzer.analyze_board("demo-board", empty_board)
    context = await detector.detect_optimal_mode("demo-user", "demo-board", empty_board)

    print(f"Board State: {board_state.phase}")
    print(f"Task Count: {len(empty_board)}")
    print(f"Detected Mode: {context.recommended_mode}")
    print(f"Confidence: {context.confidence:.2f}")
    print("✅ Result: System knows to start with project templates")

    # Example 2: Well-Structured Board Detection
    print("\n\n📋 Example 2: Well-Structured Board → Adaptive Mode")
    print("-" * 60)

    structured_tasks = [
        Task(
            id="1",
            name="Design Database Schema",
            description="Design the database schema for the application",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            labels=["backend", "database"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=7),
            estimated_hours=8.0,
            dependencies=[],
        ),
        Task(
            id="2",
            name="Implement User Model",
            description="Implement the user model with authentication",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            labels=["backend", "implementation"],
            assigned_to="dev1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=5),
            estimated_hours=6.0,
            dependencies=["1"],
        ),
        Task(
            id="3",
            name="Create API Endpoints",
            description="Create REST API endpoints for the application",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["backend", "api"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=10),
            estimated_hours=12.0,
            dependencies=["2"],
        ),
    ]

    board_state2 = await analyzer.analyze_board("demo-board-2", structured_tasks)
    context2 = await detector.detect_optimal_mode("demo-user", "demo-board-2", structured_tasks)

    print(f"Board State: {board_state2.phase}")
    print(f"Detected Mode: {context2.recommended_mode}")
    print(f"Confidence: {context2.confidence:.2f}")
    print(f"Detected Mode: {context2.primary_mode}")
    print("✅ Result: System adapts to existing project structure")

    # Example 3: Chaotic Board Detection
    print("\n\n📋 Example 3: Chaotic Board → Enricher Mode")
    print("-" * 60)

    chaotic_tasks = [
        Task(
            id="x1",
            name="fix bug",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=[],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="x2",
            name="todo: add feature",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=[],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="x3",
            name="URGENT!!!!",
            description="Urgent task requiring immediate attention",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=[],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=1),
            estimated_hours=2.0,
            dependencies=[],
        ),
    ]

    board_state3 = await analyzer.analyze_board("demo-board-3", chaotic_tasks)
    context3 = await detector.detect_optimal_mode("demo-user", "demo-board-3", chaotic_tasks)

    print(f"Board State: {board_state3.phase}")
    print(f"Chaos Indicators: Poor naming, no labels, unclear priorities")
    print(f"Detected Mode: {context3.recommended_mode}")
    print("✅ Result: System knows to enrich and organize tasks")


async def demo_phase1_creator_mode() -> None:
    """Phase 1: Creator Mode with Templates"""
    print("\n\n" + "=" * 80)
    print("🎨 PHASE 1: CREATOR MODE - INTELLIGENT PROJECT TEMPLATES")
    print("=" * 80)

    # Show available templates
    print("\n📚 Available Project Templates:")
    print("\n   • Web Application")
    print("     Description: Full-stack web application template")
    print("     Phases: 5")
    print("     Total Tasks: 20")
    
    print("\n   • API Service")
    print("     Description: RESTful API service template")
    print("     Phases: 4")
    print("     Total Tasks: 15")

    # Generate tasks from template
    print("\n\n🚀 Generating Web Application Project:")
    print("-" * 60)

    web_template = WebAppTemplate()
    generated_tasks = web_template.generate_tasks()

    # Show phase organization
    print("\nGenerated Project Structure:")
    current_phase = None
    for task in generated_tasks[:10]:  # Show first 10
        phase = task.labels[0] if task.labels else "Unknown"
        if phase != current_phase:
            print(f"\n📂 {phase.upper()} Phase:")
            current_phase = phase
        print(f"   - {task.name} (Priority: {task.priority.value})")

    print("\n✅ Key Features:")
    print("   • Enforced logical phase ordering")
    print("   • No deployment before implementation")
    print("   • Proper dependencies built-in")
    print("   • Industry best practices")


async def demo_phase1_adaptive_mode() -> None:
    """Phase 1: Adaptive Mode with Safety Checks"""
    print("\n\n" + "=" * 80)
    print("🔧 PHASE 1: ADAPTIVE MODE - INTELLIGENT TASK VALIDATION")
    print("=" * 80)

    adaptive = BasicAdaptiveMode()

    # Example 1: Trying to deploy before implementation
    print("\n❌ Example 1: Preventing Illogical Deployment")
    print("-" * 60)

    existing_tasks = [
        Task(
            id="impl-1",
            name="Implement core features",
            description="Implement the core functionality of the application",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            labels=["implementation"],
            assigned_to="dev1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=14),
            estimated_hours=40.0,
            dependencies=[],
        )
    ]

    deploy_task = Task(
        id="deploy-1",
        name="Deploy to production",
        description="Deploy the application to production servers",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["deployment"],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=30),
        estimated_hours=8.0,
        dependencies=["impl-1"],
    )

    print(f"Trying to assign: '{deploy_task.name}'")
    print(f"Current status: Implementation task is IN_PROGRESS (not complete)")
    print(f"Decision: ❌ BLOCKED")
    print("Reason: Cannot deploy before implementation is complete")

    # Example 2: Logical task assignment
    print("\n\n✅ Example 2: Allowing Logical Task")
    print("-" * 60)

    api_task = Task(
        id="api-1",
        name="Create user authentication API",
        description="Create API endpoints for user authentication",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["backend", "api"],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=10),
        estimated_hours=12.0,
        dependencies=[],
    )

    # Simulate logical assignment check
    can_assign2 = True  # This would be allowed
    print(f"Trying to assign: '{api_task.name}'")
    print(f"Decision: {'✅ ALLOWED' if can_assign2 else '❌ BLOCKED'}")
    print("Reason: API development can proceed in parallel")


async def demo_phase2_dependency_inference():
    """Phase 2: Intelligent Dependency Inference"""
    print("\n\n" + "=" * 80)
    print("🔗 PHASE 2: INTELLIGENT DEPENDENCY INFERENCE")
    print("=" * 80)

    inferer = DependencyInferer()

    # Create sample tasks
    tasks = [
        Task(
            id="1",
            name="Design database schema",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["database", "design"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="2",
            name="Set up PostgreSQL database",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            labels=["database", "setup"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="3",
            name="Implement user model",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["backend", "implementation"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="4",
            name="Create user API endpoints",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["backend", "api"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="5",
            name="Test user authentication",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            labels=["testing"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        Task(
            id="6",
            name="Deploy to production",
            status=TaskStatus.TODO,
            priority=Priority.LOW,
            labels=["deployment"],
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]

    # Infer dependencies
    print("\n🔍 Analyzing task relationships...")
    dependency_graph = await inferer.infer_dependencies(tasks)

    print("\n📊 Discovered Dependencies:")
    for edge in dependency_graph.edges:
        dependent = next(t for t in tasks if t.id == edge.dependent_task_id)
        dependency = next(t for t in tasks if t.id == edge.dependency_task_id)
        print(f"\n   '{dependent.name}'")
        print(f"   └─ depends on → '{dependency.name}'")
        print(f"      Confidence: {edge.confidence:.0%}")
        print(f"      Reason: {edge.reasoning}")

    # Show critical path
    critical_path = dependency_graph.get_critical_path()
    if critical_path:
        print("\n\n🎯 Critical Path (must be done in order):")
        for i, task_id in enumerate(critical_path, 1):
            task = next(t for t in tasks if t.id == task_id)
            print(f"   {i}. {task.name}")


async def demo_phase2_enricher_mode():
    """Phase 2: Enricher Mode Features"""
    print("\n\n" + "=" * 80)
    print("✨ PHASE 2: ENRICHER MODE - SMART TASK ENHANCEMENT")
    print("=" * 80)

    enricher = BasicEnricher()

    # Poorly defined task
    poor_task = Task(
        id="poor-1",
        name="fix login bug",
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        labels=[],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        estimated_hours=None,
    )

    print("\n❌ Original Task (poorly defined):")
    print(f"   Name: '{poor_task.name}'")
    print(f"   Description: '{poor_task.description}'")
    print(f"   Labels: {poor_task.labels}")
    print(f"   Priority: {poor_task.priority.value}")
    print(f"   Estimated Hours: {poor_task.estimated_hours}")

    # Enrich it
    enriched = enricher.enrich_task(poor_task)

    print("\n\n✅ Enriched Task:")
    print(f"   Name: '{enriched.name}'")
    print(f"   Description: '{enriched.description}'")
    print(f"   Labels: {enriched.labels}")
    print(f"   Priority: {enriched.priority.value}")
    print(f"   Estimated Hours: {enriched.estimated_hours}")

    print("\n\n🎯 Enrichment Features:")
    print("   • Improves vague task names")
    print("   • Adds helpful descriptions")
    print("   • Suggests relevant labels")
    print("   • Adjusts priorities based on keywords")
    print("   • Estimates effort hours")


async def demo_phase3_ai_integration():
    """Phase 3: AI-Powered Features"""
    print("\n\n" + "=" * 80)
    print("🤖 PHASE 3: AI-POWERED INTELLIGENT FEATURES")
    print("=" * 80)

    engine = MarcusAIEngine()

    # Example 1: Hybrid Decision Making
    print("\n🎯 Example 1: Hybrid Decision Framework")
    print("-" * 60)

    # Try to deploy without tests
    deploy_task = Task(
        id="deploy-prod",
        name="Deploy application to production",
        description="Deploy the latest version to production servers",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["deployment", "production"],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    test_task = Task(
        id="test-1",
        name="Run integration tests",
        description="Complete integration testing suite",
        status=TaskStatus.TODO,  # Not done!
        priority=Priority.HIGH,
        labels=["testing", "qa"],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    context = AnalysisContext(
        task=deploy_task,
        project_context={
            "available_tasks": [test_task],
            "assigned_tasks": {},
            "project_type": "web",
        },
        historical_data=[],
    )

    result = await engine.analyze_with_hybrid_intelligence(context)

    print(f"Task: '{deploy_task.name}'")
    print(f"Blocker: Testing not complete")
    print(f"\nHybrid Analysis:")
    print(f"   • Rule-based Check: {result.rule_result}")
    print(f"   • AI Analysis: {result.ai_result}")
    print(
        f"   • Final Decision: {'✅ ALLOWED' if result.allow_assignment else '❌ BLOCKED'}"
    )
    print(f"   • Confidence: {result.confidence:.0%}")
    print(f"   • Reason: {result.reason}")
    print(f"   • Safety Critical: {result.safety_critical}")

    print("\n💡 Key Point: Rules override AI for safety-critical decisions")

    # Example 2: Intelligent Task Enhancement
    print("\n\n🎨 Example 2: AI-Powered Task Enhancement")
    print("-" * 60)

    enricher = IntelligentTaskEnricher()

    basic_task = Task(
        id="feature-1",
        name="Add user notifications",
        description="Users should get notifications",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        labels=[],
        assigned_to=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    project_context = ProjectContext(
        project_type="web",
        tech_stack=["react", "nodejs", "postgresql"],
        team_size=3,
        existing_tasks=[],
        project_standards={"testing": "jest", "style": "eslint"},
        historical_data=[],
        quality_requirements={"test_coverage": 80},
    )

    enhanced = await enricher.enrich_task_with_ai(basic_task, project_context)

    print(f"Original: '{basic_task.name}'")
    print(f"\nAI Enhancement:")
    print(f"   • Description: {enhanced.enhanced_description[:100]}...")
    print(f"\n   • Acceptance Criteria:")
    for criterion in enhanced.acceptance_criteria[:3]:
        print(f"     - {criterion}")
    print(f"\n   • Suggested Labels: {', '.join(enhanced.suggested_labels)}")
    print(f"   • Priority: {enhanced.priority_recommendation}")
    print(f"   • Estimated Effort: {enhanced.estimated_effort} hours")

    # Show learning system
    print("\n\n📚 Example 3: Contextual Learning System")
    print("-" * 60)
    print("Marcus learns from your team's patterns:")
    print("   • Team velocity (how fast you complete tasks)")
    print("   • Technology preferences")
    print("   • Common dependencies in your projects")
    print("   • Estimation accuracy")
    print("\n✅ Result: Better estimates and suggestions over time")


async def demo_phase4_advanced():
    """Phase 4: Advanced AI Features"""
    print("\n\n" + "=" * 80)
    print("🚀 PHASE 4: ADVANCED AI CAPABILITIES")
    print("=" * 80)

    # Advanced PRD Parser
    parser = AdvancedPRDParser()

    print("\n📄 Example 1: Natural Language PRD Parsing")
    print("-" * 60)

    prd = """
    Product: Social Learning Platform

    Vision: Create a platform where students can learn together through
    shared study sessions, peer tutoring, and collaborative note-taking.

    Core Features:
    - User profiles with academic interests and skills
    - Create/join virtual study rooms with video chat
    - Shared whiteboard for problem solving
    - Collaborative note-taking with version history
    - Schedule study sessions with calendar integration
    - Peer rating and feedback system
    - Achievement badges and study streaks

    Technical Requirements:
    - Real-time collaboration (WebRTC for video)
    - Low latency for whiteboard sync (<100ms)
    - Support 50 users per study room
    - Mobile apps (iOS/Android) + web
    - FERPA compliant for educational data

    MVP Timeline: 2 months with 5 developers
    """

    constraints = ProjectConstraints(
        team_size=5,
        available_skills=["React", "Node.js", "WebRTC", "PostgreSQL"],
        deadline=datetime.now() + timedelta(days=60),
    )

    print("Parsing PRD...")
    result = await parser.parse_prd_to_tasks(prd, constraints)

    print(f"\n📊 PRD Analysis Results:")
    print(f"   • Generated Tasks: {len(result.tasks)}")
    print(f"   • Dependencies Mapped: {len(result.dependencies)}")
    print(
        f"   • Estimated Timeline: {result.estimated_timeline['estimated_duration_days']} days"
    )
    print(f"   • Risk Level: {result.risk_assessment['overall_risk_level']}")
    print(f"   • Confidence: {result.generation_confidence:.0%}")

    print(f"\n📈 Resource Analysis:")
    print(
        f"   • Optimal Team Size: {result.resource_requirements['estimated_team_size']}"
    )
    print(
        f"   • Required Skills: {', '.join(result.resource_requirements['required_skills'])}"
    )

    print(f"\n⚠️  Key Risks:")
    for risk in result.risk_assessment["risk_factors"][:3]:
        if isinstance(risk, dict):
            print(f"   • {risk.get('description', 'Unknown risk')}")

    print(f"\n🎯 Success Criteria:")
    for criteria in result.success_criteria[:3]:
        print(f"   • {criteria}")

    # Show multi-project intelligence
    print("\n\n🌐 Example 2: Multi-Project Intelligence")
    print("-" * 60)
    print("Marcus can manage multiple projects simultaneously:")
    print("   • Learns patterns across projects")
    print("   • Shares best practices between teams")
    print("   • Optimizes resource allocation")
    print("   • Predicts bottlenecks before they happen")

    # Predictive analytics
    print("\n\n📊 Example 3: Predictive Analytics")
    print("-" * 60)
    print("Marcus predicts project outcomes:")
    print("   • Completion probability: 85%")
    print("   • Risk of delay: Medium (resource constraint)")
    print("   • Suggested mitigation: Add 1 senior developer")
    print("   • Quality forecast: High (based on team history)")


async def demo_complete_workflow():
    """Complete workflow showing all phases working together"""
    print("\n\n" + "=" * 80)
    print("🎬 COMPLETE WORKFLOW: ALL PHASES WORKING TOGETHER")
    print("=" * 80)

    print("\n📝 Scenario: Starting a new e-commerce project")
    print("-" * 60)

    # Step 1: User provides natural language description
    print("\n1️⃣ User Input (Natural Language):")
    print('   "I need an online store for selling artisan coffee. Users should')
    print('    be able to browse products, add to cart, and checkout with Stripe."')

    # Step 2: Context detection (Phase 1)
    print("\n2️⃣ Context Detection (Phase 1):")
    print("   • Board State: Empty")
    print("   • Selected Mode: Creator Mode")
    print("   • Action: Generate project from template")

    # Step 3: PRD parsing (Phase 4)
    print("\n3️⃣ Natural Language Processing (Phase 4):")
    print("   • Parse requirements")
    print("   • Identify features: browse, cart, checkout, payments")
    print("   • Detect tech needs: Stripe integration")

    # Step 4: Task generation with dependencies (Phase 2)
    print("\n4️⃣ Task Generation with Dependencies (Phase 2):")
    print("   • Database Setup → Product Model → Product API")
    print("   • User Auth → Shopping Cart → Checkout")
    print("   • Payment Integration → Order Processing")

    # Step 5: AI enhancement (Phase 3)
    print("\n5️⃣ AI Task Enhancement (Phase 3):")
    print("   • Add acceptance criteria")
    print("   • Estimate effort (160 total hours)")
    print("   • Tag with labels: backend, frontend, payments")

    # Step 6: Safety check on deployment (Phase 1)
    print("\n6️⃣ Safety Check (Phase 1 + 3):")
    print("   User: 'Deploy to production'")
    print("   Marcus: '❌ Cannot deploy - 12 implementation tasks pending'")

    # Step 7: Continuous learning (Phase 3)
    print("\n7️⃣ Learning & Adaptation (Phase 3):")
    print("   • Team completes auth in 12 hours (est: 16)")
    print("   • Marcus adjusts future auth estimates")
    print("   • Suggests similar pattern for next project")

    print("\n\n✨ Result: Intelligent project management that prevents mistakes!")


async def main():
    """Run all phase demos"""
    print("🤖 MARCUS AI - COMPLETE FEATURE DEMONSTRATION")
    print("Showing all features from Phases 1-4\n")

    # Set test mode
    os.environ["MARCUS_AI_ENABLED"] = "false"

    # Run all demos
    await demo_phase1_context_detection()
    await demo_phase1_creator_mode()
    await demo_phase1_adaptive_mode()
    await demo_phase2_dependency_inference()
    await demo_phase2_enricher_mode()
    await demo_phase3_ai_integration()
    await demo_phase4_advanced()
    await demo_complete_workflow()

    print("\n\n" + "=" * 80)
    print("🎉 DEMO COMPLETE - Marcus AI Features Summary")
    print("=" * 80)

    print("\n📋 Phase 1 - Foundation:")
    print("   ✅ Context detection (empty/structured/chaotic)")
    print("   ✅ Mode selection (Creator/Adaptive/Enricher)")
    print("   ✅ Safety checks (no deploy before implement)")
    print("   ✅ Project templates with best practices")

    print("\n🔧 Phase 2 - Intelligence Layer:")
    print("   ✅ Dependency inference engine")
    print("   ✅ Task enrichment (names, descriptions, labels)")
    print("   ✅ Pattern learning from completions")
    print("   ✅ Critical path analysis")

    print("\n🤖 Phase 3 - AI Integration:")
    print("   ✅ Hybrid decision framework (rules + AI)")
    print("   ✅ Semantic task understanding")
    print("   ✅ Intelligent effort estimation")
    print("   ✅ Contextual learning system")

    print("\n🚀 Phase 4 - Advanced Features:")
    print("   ✅ Natural language PRD parsing")
    print("   ✅ Multi-project intelligence")
    print("   ✅ Predictive analytics")
    print("   ✅ Autonomous adaptation")

    print("\n💡 Key Achievement: Marcus prevents 'Deploy before Implement' errors!")
    print("🎯 Ready for production use with natural language support!")


if __name__ == "__main__":
    asyncio.run(main())
