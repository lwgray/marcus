"""
Show exactly what the AI sees when generating task instructions.

This reveals how agents get correct context despite generic descriptions.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.models import WorkerStatus


async def show_ai_input():
    """Show what AI receives for instruction generation."""
    # Generate a project
    parser = AdvancedPRDParser()
    constraints = ProjectConstraints(team_size=1, deployment_target="local")

    result = await parser.parse_prd_to_tasks(
        "Build a todo app with user authentication, CRUD operations for todos, and filtering by status",
        constraints,
    )

    print("=" * 70)
    print("WHAT THE AI SEES WHEN GENERATING INSTRUCTIONS")
    print("=" * 70)

    # Simulate what gets passed to generate_task_instructions
    # From ai_analysis_engine.py line 470-478
    task = result.tasks[0]  # First task

    task_data = {
        "name": task.name,  # ✅ SPECIFIC FEATURE NAME
        "description": task.description,  # ❌ GENERIC TEMPLATE
        "priority": task.priority.value,
        "estimated_hours": task.estimated_hours,
        "dependencies": task.dependencies,
        "labels": getattr(task, "labels", []) or [],
        "type": "design",
    }

    mock_agent = {
        "name": "TestAgent",
        "role": "Developer",
        "skills": ["python", "javascript"],
    }

    print("\n📋 TASK DATA (sent to AI):\n")
    print(json.dumps(task_data, indent=2))

    print("\n👤 AGENT DATA (sent to AI):\n")
    print(json.dumps(mock_agent, indent=2))

    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print(
        f"""
✅ Task NAME is specific: "{task_data['name']}"
   - Contains: "User Authentication"
   - AI can infer from this!

❌ Task DESCRIPTION is generic:
   - Says: "Create detailed UI/UX design for frontend application..."
   - Doesn't mention authentication

🔑 THE SECRET: The AI infers context from the TASK NAME!
   - Sees "Design User Authentication"
   - Knows this is about auth, not generic frontend
   - Generates auth-specific instructions

PLUS: When agent is working, they can see ALL tasks:
   - "Implement User Authentication"
   - "Test User Authentication"
   - "Design CRUD Operations for Todos"
   - This provides PROJECT CONTEXT

So the AI pieces together:
   1. Task name → Feature context
   2. All task names → Project scope
   3. Generic description → Task type (design/implement/test)
"""
    )

    print("\n" + "=" * 70)
    print("ALL TASKS IN PROJECT (visible to agent)")
    print("=" * 70)
    for idx, t in enumerate(result.tasks, 1):
        print(f"{idx:2}. {t.name}")

    print(f"\n✅ Agent sees {len(result.tasks)} tasks with specific names")
    print("✅ AI can infer 'todo app' from task names like 'CRUD Operations for Todos'")
    print("✅ Task clustering reveals project structure")


if __name__ == "__main__":
    asyncio.run(show_ai_input())
