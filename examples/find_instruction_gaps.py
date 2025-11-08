"""
Find Instruction Gaps: Did agents get the right instructions?

This script compares task descriptions with actual instructions given to agents
to find WHERE the breakdown happened.

The Critical Question:
- Task description says: "Create blog post with title, content, tags"
- Agent instruction says: "Implement BlogPost model" (missing index.html!)
- Result: Agent did what they were told, but it wasn't complete

This finds those gaps.

Usage:
    python examples/find_instruction_gaps.py <project_id>
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path so we can import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.aggregator import ProjectHistoryAggregator  # noqa: E402
from src.analysis.query_api import ProjectHistoryQuery  # noqa: E402


async def find_instruction_gaps(project_id: str) -> None:
    """
    Find where task descriptions and agent instructions diverged.

    Parameters
    ----------
    project_id : str
        The project to analyze
    """
    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    print("=" * 80)
    print(f"INSTRUCTION GAP ANALYSIS: {project_id}")
    print("=" * 80)
    print("\nFinding where agent instructions didn't match task descriptions...")

    try:
        history = await query.get_project_history(
            project_id, include_conversations=True
        )
    except Exception as e:
        print(f"❌ Error loading project: {e}")
        return

    print(f"\nAnalyzing {len(history.tasks)} tasks...\n")

    gaps_found = 0
    missing_instructions = 0

    for task in history.tasks:
        print("-" * 80)
        print(f"\n📋 Task: {task.name}")
        print(f"   Status: {task.status}")
        print(f"   Agent: {task.assigned_to or 'Not assigned'}")

        # Show the original task description
        print("\n   Original Description:")
        desc_lines = task.description.split("\n")
        for line in desc_lines[:3]:  # Show first 3 lines
            print(f"      {line}")
        if len(desc_lines) > 3:
            print(f"      ... ({len(desc_lines) - 3} more lines)")

        # Show what instructions the agent actually received
        if task.instructions_received:
            print("\n   ✅ Instructions Given to Agent:")
            inst_lines = task.instructions_received.split("\n")
            for line in inst_lines[:3]:
                print(f"      {line}")
            if len(inst_lines) > 3:
                print(f"      ... ({len(inst_lines) - 3} more lines)")

            # Simple heuristic: check if instruction is much shorter than description
            desc_len = len(task.description)
            inst_len = len(task.instructions_received)

            if inst_len < desc_len * 0.5:  # Instruction < 50% of description
                print("\n   ⚠️  POTENTIAL GAP DETECTED!")
                print(f"      Description: {desc_len} chars")
                print(f"      Instructions: {inst_len} chars")
                print(f"      Coverage: {inst_len/desc_len*100:.1f}%")
                gaps_found += 1

        else:
            print("\n   ❌ NO INSTRUCTIONS RECORDED!")
            print("      Agent worked without explicit instructions from Marcus")
            missing_instructions += 1

        # Show the outcome
        if task.outcome:
            print("\n   Outcome:")
            print(f"      Success: {task.outcome.success}")
            if task.outcome.blockers:
                print(f"      Blockers: {', '.join(task.outcome.blockers)}")

        # Show conversations to see what was actually discussed
        if task.conversations:
            print(f"\n   Conversations: {len(task.conversations)} messages")
            # Show first message from Marcus to agent
            for msg in task.conversations[:1]:
                if msg.direction == "to_pm":  # Message TO the agent
                    preview = msg.content[:200]
                    print(f"      Marcus told agent: '{preview}...'")

        print()

    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"\nTotal Tasks Analyzed: {len(history.tasks)}")
    print(f"Tasks with Instruction Gaps: {gaps_found}")
    print(f"Tasks Missing Instructions: {missing_instructions}")

    if gaps_found > 0 or missing_instructions > 0:
        print("\n⚠️  PROBLEM DETECTED!")
        print("\nPossible causes:")
        print("  1. Marcus is not giving complete instructions to agents")
        print("  2. Task descriptions are more detailed than instructions")
        print("  3. Critical requirements are being lost in translation")
        print("\nAction items:")
        print("  - Review how Marcus generates agent instructions")
        print("  - Check if task decomposition is losing details")
        print("  - Verify agents are getting full context")
    else:
        print("\n✅ No obvious gaps found")
        print("   All tasks have instructions matching descriptions")

    print("\n" + "=" * 80)


async def show_specific_task(project_id: str, task_name: str) -> None:
    """
    Deep dive into a specific task to see instruction gap.

    Parameters
    ----------
    project_id : str
        Project ID
    task_name : str
        Name of task to examine (partial match ok)
    """
    aggregator = ProjectHistoryAggregator()
    query = ProjectHistoryQuery(aggregator)

    print("=" * 80)
    print(f"DEEP DIVE: {task_name}")
    print("=" * 80)

    history = await query.get_project_history(project_id, include_conversations=True)

    # Find matching task
    task = None
    for t in history.tasks:
        if task_name.lower() in t.name.lower():
            task = t
            break

    if not task:
        print(f"❌ Task not found: {task_name}")
        print("\nAvailable tasks:")
        for t in history.tasks[:10]:
            print(f"  - {t.name}")
        return

    print(f"\n📋 Task: {task.name}")
    print(f"   Status: {task.status}")
    print(f"   Agent: {task.assigned_to}")

    print("\n1️⃣  WHAT THE TASK DESCRIPTION SAID:")
    print("-" * 80)
    print(task.description)

    print("\n2️⃣  WHAT MARCUS TOLD THE AGENT:")
    print("-" * 80)
    if task.instructions_received:
        print(task.instructions_received)
    else:
        print("❌ NO INSTRUCTIONS FOUND!")

    print("\n3️⃣  WHAT THE AGENT ACTUALLY DID:")
    print("-" * 80)

    # Show conversations
    if task.conversations:
        print(f"Conversations: {len(task.conversations)} messages\n")
        for msg in task.conversations[:5]:
            direction = "Agent" if msg.direction == "from_pm" else "Marcus"
            content_preview = msg.content[:150]
            print(f"{direction}: {content_preview}...")
            print()
    else:
        print("No conversation logs found")

    # Show outcome
    if task.outcome:
        print("\n4️⃣  OUTCOME:")
        print("-" * 80)
        print(f"Success: {task.outcome.success}")
        if task.outcome.blockers:
            print(f"Blockers: {', '.join(task.outcome.blockers)}")
        if task.outcome.actual_hours:
            print(f"Actual Hours: {task.outcome.actual_hours:.1f}")

    # Show artifacts
    if task.artifacts_produced:
        print("\n5️⃣  ARTIFACTS PRODUCED:")
        print("-" * 80)
        for artifact in task.artifacts_produced:
            print(f"  - {artifact.filename}")
            print(f"    Type: {artifact.artifact_type}")
            print(f"    Path: {artifact.relative_path}")

    print("\n" + "=" * 80)
    print("🔍 GAP ANALYSIS")
    print("=" * 80)

    # Simple comparison
    desc_lower = task.description.lower()
    inst_lower = (task.instructions_received or "").lower()

    # Check for key terms in description but not in instructions
    important_terms = [
        "index.html",
        "frontend",
        "ui",
        "interface",
        "html",
        "css",
        "form",
        "button",
        "page",
    ]

    missing_terms = []
    for term in important_terms:
        if term in desc_lower and term not in inst_lower:
            missing_terms.append(term)

    if missing_terms:
        print("\n⚠️  Terms in description but NOT in instructions:")
        for term in missing_terms:
            print(f"   - '{term}'")

    if not task.instructions_received:
        print("\n❌ CRITICAL: Agent received NO instructions from Marcus!")
        print("   This is why implementation doesn't match description.")

    elif len(inst_lower) < len(desc_lower) * 0.5:
        print("\n⚠️  Instructions are much shorter than description")
        print(f"   Description: {len(task.description)} chars")
        print(f"   Instructions: {len(task.instructions_received)} chars")
        print(f"   Coverage: {len(inst_lower)/len(desc_lower)*100:.1f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python find_instruction_gaps.py <project_id>")
        print("  python find_instruction_gaps.py <project_id> <task_name>")
        print("\nExamples:")
        print("  python find_instruction_gaps.py proj123")
        print('  python find_instruction_gaps.py proj123 "Create Blog Post"')
        sys.exit(1)

    project_id = sys.argv[1]

    if len(sys.argv) >= 3:
        # Deep dive into specific task
        task_name = " ".join(sys.argv[2:])
        asyncio.run(show_specific_task(project_id, task_name))
    else:
        # Analyze all tasks
        asyncio.run(find_instruction_gaps(project_id))
