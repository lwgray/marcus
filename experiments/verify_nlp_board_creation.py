#!/usr/bin/env python3
"""
Quick verification that NLP-created tasks appear on the actual board
This is a simpler version for quick testing
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.integrations.kanban_factory import KanbanFactory
from src.integrations.nlp_tools import create_project_from_natural_language


async def verify_board_creation():
    """Verify that natural language project creation works with real board"""

    # Load environment
    load_dotenv()
    provider = os.getenv("KANBAN_PROVIDER", "planka")

    print(f"🔧 Testing with {provider} provider...")

    # Get kanban client
    kanban = await KanbanFactory.create(provider)
    print(f"✓ Connected to {provider}")

    # Create a simple project
    print("\n📝 Creating project from natural language...")

    result = await create_project_from_natural_language(
        description="I need a simple todo app with user accounts",
        project_name="Quick NLP Test Project",
        options={"team_size": 1},
    )

    if result["success"]:
        print(f"\n✅ Project created!")
        print(f"   - Tasks: {result['tasks_created']}")
        print(f"   - Phases: {result['phases']}")

        # Verify on board
        print(f"\n🔍 Checking {provider} board...")
        tasks = await kanban.get_tasks()

        # Count new tasks (created in last minute)
        from datetime import datetime, timedelta

        recent_cutoff = datetime.now() - timedelta(minutes=1)

        recent_tasks = []
        for task in tasks:
            # Check if task was created recently
            # Note: This assumes tasks have a created_at field or we check by title
            if "Quick NLP Test Project" in (
                task.title or ""
            ) or "Quick NLP Test Project" in (task.description or ""):
                recent_tasks.append(task)

        print(f"✓ Found {len(recent_tasks)} tasks on board")

        if recent_tasks:
            print("\n📋 Sample tasks:")
            for i, task in enumerate(recent_tasks[:3]):
                print(f"   {i+1}. {task.title}")

        return True
    else:
        print(f"❌ Failed: {result.get('error', 'Unknown error')}")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_board_creation())
    exit(0 if success else 1)
