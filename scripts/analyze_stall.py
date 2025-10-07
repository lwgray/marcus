#!/usr/bin/env python3
"""
Command-line utility to analyze project stalls.

Usage:
    # Capture a snapshot when development stalls
    python scripts/analyze_stall.py capture

    # Replay a specific snapshot
    python scripts/analyze_stall.py replay logs/stall_snapshots/stall_snapshot_20251006_220000.json

    # List all snapshots
    python scripts/analyze_stall.py list
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def capture_snapshot():
    """Capture a stall snapshot from the current Marcus instance."""
    from src.config.config_loader import get_config
    from src.core.project_context_manager import ProjectContextManager
    from src.core.project_registry import ProjectRegistry
    from src.integrations.ai_analysis_engine import AIAnalysisEngine
    from src.integrations.kanban_factory import KanbanFactory
    from src.marcus_mcp.tools.project_stall_analyzer import (
        capture_project_stall_snapshot,
    )

    print("🔍 Capturing project stall snapshot...")

    # Create minimal state object
    class MockState:
        def __init__(self):
            self.config = get_config()
            self.project_registry = ProjectRegistry()
            self.project_manager = ProjectContextManager(self.project_registry)
            self.ai_engine = AIAnalysisEngine()
            self.kanban_client = None
            self.agent_tasks = {}
            self.project_tasks = []

        async def initialize_kanban(self):
            if not self.kanban_client:
                provider = self.config.get("kanban.provider", "planka")
                self.kanban_client = KanbanFactory.create(provider)
                if hasattr(self.kanban_client, "connect"):
                    await self.kanban_client.connect()

    state = MockState()

    # Initialize
    await state.project_registry.initialize()
    await state.project_manager.initialize()

    # Capture snapshot
    result = await capture_project_stall_snapshot(state, include_conversation_hours=48)

    if result["success"]:
        print(f"\n✅ Snapshot captured successfully!")
        print(f"📁 Saved to: {result['snapshot_file']}")
        print(f"\n📊 Summary:")
        print(f"   Stall Reason: {result['summary']['stall_reason']}")
        print(f"   Total Issues: {result['summary']['total_issues']}")
        print(f"   Dependency Locks: {result['summary']['dependency_locks']}")
        print(f"   Early Completions: {result['summary']['early_completions']}")
        print(f"   Conversation Events: {result['summary']['conversation_events']}")
        print(f"\n💡 Recommendations: {result['summary']['recommendations_count']}")

        # Show dependency locks if any
        if result["summary"]["dependency_locks"] > 0:
            print(f"\n🔒 Dependency Locks Detected:")
            locks = result["snapshot"]["dependency_locks"]
            print(locks["ascii_visualization"])

        # Show early completions if any
        if result["summary"]["early_completions"] > 0:
            print(f"\n⚠️  Early/Anomalous Task Completions:")
            for completion in result["snapshot"]["early_completions"]:
                print(f"   • {completion['task_name']}")
                print(
                    f"     Completed at {completion['completion_percentage']}% progress"
                )
                print(f"     Issue: {completion['issue']}")

        return result["snapshot_file"]
    else:
        print(f"\n❌ Failed to capture snapshot: {result.get('error')}")
        return None


async def replay_snapshot(snapshot_file: str):
    """Replay conversations from a snapshot file."""
    from src.marcus_mcp.tools.project_stall_analyzer import replay_stall_conversations

    if not Path(snapshot_file).exists():
        print(f"❌ Snapshot file not found: {snapshot_file}")
        return

    print(f"🎬 Replaying conversations from: {snapshot_file}\n")

    # Load snapshot
    with open(snapshot_file, "r") as f:
        snapshot = json.load(f)

    # Show basic info
    print(f"📸 Snapshot Info:")
    print(f"   Timestamp: {snapshot['timestamp']}")
    print(f"   Project: {snapshot['project_name']}")
    print(f"   Stall Reason: {snapshot['stall_reason']}\n")

    # Show diagnostic report
    print("=" * 70)
    print(snapshot["diagnostic_report"]["formatted_report"])
    print("=" * 70)

    # Replay conversations
    result = await replay_stall_conversations(snapshot_file)

    if result["success"]:
        analysis = result["analysis"]
        print(f"\n🗣️  Conversation Analysis:")
        print(f"   Total Events: {analysis['total_events']}")
        print(f"\n   Events by Type:")
        for event_type, count in sorted(
            analysis["events_by_type"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"      {event_type}: {count}")

        if analysis["key_events"]:
            print(f"\n   🔑 Key Events (errors, blockers, failures):")
            for event in analysis["key_events"][:10]:
                print(f"      [{event['timestamp']}] {event['type']}")
                if len(event["summary"]) > 0:
                    print(f"         {event['summary'][:100]}...")

        # Show early completions again
        if snapshot["early_completions"]:
            print(f"\n⚠️  Tasks Completed Too Early:")
            for ec in snapshot["early_completions"]:
                print(
                    f"   • '{ec['task_name']}' at {ec['completion_percentage']}% progress"
                )

        # Show recommendations
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(snapshot["recommendations"][:10], 1):
            print(f"   {i}. {rec}")
    else:
        print(f"❌ Failed to replay: {result.get('error')}")


def list_snapshots():
    """List all available snapshots."""
    snapshot_dir = Path("logs/stall_snapshots")

    if not snapshot_dir.exists():
        print("No snapshots found. Run 'capture' first.")
        return

    snapshots = sorted(snapshot_dir.glob("stall_snapshot_*.json"), reverse=True)

    if not snapshots:
        print("No snapshots found.")
        return

    print(f"📁 Available Snapshots ({len(snapshots)}):\n")

    for snapshot_file in snapshots:
        try:
            with open(snapshot_file, "r") as f:
                snapshot = json.load(f)

            timestamp = snapshot["timestamp"]
            project = snapshot.get("project_name", "Unknown")
            stall_reason = snapshot.get("stall_reason", "Unknown")[:60]

            print(f"   {snapshot_file.name}")
            print(f"      Time: {timestamp}")
            print(f"      Project: {project}")
            print(f"      Reason: {stall_reason}")
            print()
        except Exception as e:
            print(f"   {snapshot_file.name} (error reading: {e})")


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "capture":
        await capture_snapshot()
    elif command == "replay":
        if len(sys.argv) < 3:
            print("Usage: analyze_stall.py replay <snapshot_file>")
            list_snapshots()
            return
        await replay_snapshot(sys.argv[2])
    elif command == "list":
        list_snapshots()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
