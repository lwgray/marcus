#!/usr/bin/env python3
"""
Example: How to interact with Marcus directly via Python
"""

import asyncio

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.ai.core.ai_engine import MarcusAIEngine
from src.ai.types import AnalysisContext
from src.core.models import Priority, Task, TaskStatus
from src.modes.adaptive.basic_adaptive import BasicAdaptiveMode


async def example_interactions():

    # ==============================================
    # INTERACTION 1: Natural Language to Tasks
    # ==============================================
    print("📝 INTERACTION 1: Natural Language Project Description")
    print("-" * 50)

    parser = AdvancedPRDParser()

    # User provides natural language description
    user_input = """
    I want to build a fitness tracking app where users can:
    - Log their workouts with exercises, sets, and reps
    - Track progress over time with charts
    - Share workouts with friends
    - Get AI-powered workout recommendations

    Should work on iPhone and Android, use Firebase for backend.
    """

    print("User says:", user_input)
    print("\nMarcus responds by creating tasks...")

    # Marcus converts to tasks
    result = await parser.parse_prd_to_tasks(
        user_input, ProjectConstraints(team_size=3)
    )

    print(f"\n✅ Created {len(result.tasks)} tasks")
    print("First few tasks:")
    for task in result.tasks[:5]:
        print(f"  - {task.name}")

    # ==============================================
    # INTERACTION 2: Asking for Task Assignment
    # ==============================================
    print("\n\n🎯 INTERACTION 2: Can I Deploy?")
    print("-" * 50)

    # User wants to deploy but hasn't implemented yet
    adaptive = BasicAdaptiveMode()

    # Existing tasks (not complete)
    existing_tasks = [
        Task(
            id="1",
            name="Implement workout logging API",
            status=TaskStatus.TODO,  # Not done!
            priority=Priority.HIGH,
            labels=["backend"],
            assigned_to=None,
            created_at=None,
            updated_at=None,
        )
    ]

    # User tries to create deployment task
    deploy_task = Task(
        id="2",
        name="Deploy to production",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["deployment"],
        assigned_to=None,
        created_at=None,
        updated_at=None,
    )

    print('User: "Deploy the app to production"')

    # Marcus checks if this is allowed
    can_deploy = adaptive.can_assign_task(deploy_task, existing_tasks, {})

    if not can_deploy:
        print('Marcus: "❌ Cannot deploy - implementation tasks are not complete"')
        print('        "Complete these first: Implement workout logging API"')

    # ==============================================
    # INTERACTION 3: Getting Intelligent Suggestions
    # ==============================================
    print("\n\n💡 INTERACTION 3: What Should I Work On?")
    print("-" * 50)

    print('User: "What task should I work on next?"')
    print("\nMarcus analyzes dependencies and suggests:")
    print("  \"Work on 'Design database schema' - it's blocking 5 other tasks\"")
    print("  \"After that: 'Set up Firebase project' (2 hours)\"")
    print("  \"Then: 'Implement user authentication' (8 hours)\"")

    # ==============================================
    # INTERACTION 4: Natural Language Feature Request
    # ==============================================
    print("\n\n➕ INTERACTION 4: Adding Features Naturally")
    print("-" * 50)

    print('User: "Add social features so users can follow each other"')
    print("\nMarcus creates these tasks:")
    print("  1. Design social features database schema")
    print("  2. Implement follow/unfollow API endpoints")
    print("  3. Create follower/following lists UI")
    print("  4. Add activity feed for followed users")
    print("  5. Implement privacy settings")
    print("  6. Test social features")

    # ==============================================
    # INTERACTION 5: AI-Powered Analysis
    # ==============================================
    print("\n\n🤖 INTERACTION 5: Getting AI Analysis")
    print("-" * 50)

    engine = MarcusAIEngine()

    print('User: "How risky is deploying the payment system?"')

    payment_task = Task(
        id="pay-1",
        name="Deploy payment processing",
        description="Deploy Stripe integration to production",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        labels=["payment", "deployment"],
        assigned_to=None,
        created_at=None,
        updated_at=None,
    )

    # Marcus analyzes with AI
    context = AnalysisContext(
        task=payment_task,
        project_context={"project_type": "ecommerce"},
        historical_data=[],
    )

    analysis = await engine.analyze_with_hybrid_intelligence(context)

    print(f'\nMarcus: "Risk Level: HIGH"')
    print(f'        "Confidence: {analysis.confidence:.0%}"')
    print(f'        "Reason: {analysis.reason}"')
    print('        "Required: Payment testing, PCI compliance check, rollback plan"')


async def show_mcp_interaction():
    """Show how MCP interaction would look"""
    print("\n\n" + "=" * 70)
    print("🔌 MCP SERVER INTERACTION (Claude Desktop)")
    print("=" * 70)

    print("\nIn Claude Desktop, after connecting to Marcus MCP server:")

    print("\n1️⃣ Starting a Project:")
    print("   You: 'I need a blog platform with comments and user accounts'")
    print("   Claude: [Uses Marcus to create 28 tasks across 5 phases]")

    print("\n2️⃣ Adding Features:")
    print("   You: 'Add email notifications when someone comments'")
    print("   Claude: [Marcus adds notification tasks with dependencies]")

    print("\n3️⃣ Checking Status:")
    print("   You: 'What percentage of the project is complete?'")
    print("   Claude: '35% complete (10/28 tasks). Currently working on: User auth'")

    print("\n4️⃣ Getting Recommendations:")
    print("   You: 'What should the team focus on today?'")
    print("   Claude: 'Focus on completing authentication - it's blocking 8 tasks'")

    print("\n5️⃣ Safety Checks:")
    print("   You: 'Let's deploy this to production'")
    print("   Claude: 'Cannot deploy yet. Missing: tests (12h), security review (4h)'")


async def show_web_ui_interaction():
    """Show potential web UI interaction"""
    print("\n\n" + "=" * 70)
    print("🌐 POTENTIAL WEB UI INTERACTION")
    print("=" * 70)

    print("\nIf Marcus had a web interface:")

    print("\n📝 Natural Language Input Box:")
    print("┌─────────────────────────────────────────────┐")
    print("│ 'Build a todo app with reminders'           │")
    print("│ [Generate Project]                          │")
    print("└─────────────────────────────────────────────┘")

    print("\n📋 Generated Task Board:")
    print("┌─────────────────────────────────────────────┐")
    print("│ TODO          IN PROGRESS      DONE         │")
    print("│ ─────         ───────────      ────         │")
    print("│ □ Setup DB    ▶ User Model     ✓ Setup Env │")
    print("│ □ Todo API                     ✓ Design DB  │")
    print("│ □ Reminders                                 │")
    print("│ ⚠️ Deploy                                    │")
    print("└─────────────────────────────────────────────┘")

    print("\n💬 Chat Interface:")
    print("You: 'Why can't I deploy?'")
    print("Marcus: 'Deploy is blocked until Todo API and Reminders are complete'")


def main():
    print("🤖 MARCUS INTERACTION EXAMPLES")
    print("=" * 70)
    print("\nMarcus can be used in several ways:\n")

    print("1. MCP Server + Claude Desktop (Recommended)")
    print("   - Start server: python marcus_mcp_server.py")
    print("   - Use natural language in Claude Desktop")
    print("   - Marcus operates as Claude's project management tool")

    print("\n2. Direct Python API")
    print("   - Import Marcus modules")
    print("   - Call functions programmatically")
    print("   - Build your own integrations")

    print("\n3. Future: Web UI or CLI")
    print("   - Not implemented yet")
    print("   - Could provide visual task board")
    print("   - Direct natural language interface")

    # Run async examples
    import asyncio
    import os

    os.environ["MARCUS_AI_ENABLED"] = "false"  # Test mode

    asyncio.run(example_interactions())
    asyncio.run(show_mcp_interaction())
    asyncio.run(show_web_ui_interaction())

    print("\n\n✨ The key is: Marcus understands natural language at every step!")


if __name__ == "__main__":
    main()
