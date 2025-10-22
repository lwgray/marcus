#!/usr/bin/env python3
"""Query Marcus Memory system to see actual task completion data."""

import asyncio
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.persistence import Persistence, SQLitePersistence


async def main():
    """Query memory data and show statistics."""
    # Use SQLite persistence (default location)
    db_path = Path(__file__).parent.parent / "data" / "marcus.db"

    if not db_path.exists():
        print(f"❌ No database found at {db_path}")
        print("\nTrying JSON file persistence...")
        persistence = Persistence()
    else:
        print(f"✅ Found database at {db_path}")
        persistence = Persistence(backend=SQLitePersistence(db_path))

    # Query task outcomes
    outcomes_data = await persistence.query("task_outcomes", limit=1000)

    print(f"\n📊 Memory Statistics")
    print("=" * 70)
    print(f"Total task outcomes: {len(outcomes_data)}")

    if not outcomes_data:
        print("\n⚠️  No task outcome data found!")
        print("The Memory system hasn't recorded any completed tasks yet.")
        return

    # Group by task labels to see patterns
    pattern_durations = defaultdict(list)
    all_durations = []

    for outcome in outcomes_data:
        actual_hours = outcome.get("actual_hours", 0)
        estimated_hours = outcome.get("estimated_hours", 0)
        task_name = outcome.get("task_name", "Unknown")

        all_durations.append(actual_hours)

        # Try to extract pattern from task name (simplified)
        # In real data, we'd use task.labels but that's not stored in outcome
        pattern_key = "general"
        pattern_durations[pattern_key].append(actual_hours)

        print(f"\nTask: {task_name}")
        print(f"  Estimated: {estimated_hours:.2f}h ({estimated_hours * 60:.1f} min)")
        print(f"  Actual:    {actual_hours:.2f}h ({actual_hours * 60:.1f} min)")
        print(f"  Ratio:     {actual_hours / estimated_hours * 100:.1f}% of estimate")

    # Overall statistics
    if all_durations:
        print(f"\n📈 Overall Statistics")
        print("=" * 70)
        avg_duration = mean(all_durations)
        median_duration = median(all_durations)

        print(
            f"Average actual duration: {avg_duration:.4f}h ({avg_duration * 60:.2f} min)"
        )
        print(
            f"Median actual duration:  {median_duration:.4f}h ({median_duration * 60:.2f} min)"
        )
        if len(all_durations) > 1:
            print(
                f"Std deviation:           {stdev(all_durations):.4f}h ({stdev(all_durations) * 60:.2f} min)"
            )
        print(
            f"Min duration:            {min(all_durations):.4f}h ({min(all_durations) * 60:.2f} min)"
        )
        print(
            f"Max duration:            {max(all_durations):.4f}h ({max(all_durations) * 60:.2f} min)"
        )

        # Show what the current default should be (using median as more robust)
        median_minutes = median_duration * 60
        avg_minutes = avg_duration * 60
        print(
            f"\n💡 Recommended default (median): {median_duration:.4f}h ({median_minutes:.2f} min)"
        )
        print(
            f"   Alternative (mean):           {avg_duration:.4f}h ({avg_minutes:.2f} min)"
        )

    # Query agent profiles (to see if they exist)
    profiles_data = await persistence.query("agent_profiles", limit=100)
    print(f"\n👥 Agent Profiles: {len(profiles_data)}")

    # Query task patterns (the important one!)
    # Note: task_patterns aren't persisted separately in current implementation
    # They're only in memory.semantic["task_patterns"]
    print(f"\n⚠️  Note: TaskPattern data is not persisted to database")
    print("   (only TaskOutcome records are persisted)")


if __name__ == "__main__":
    asyncio.run(main())
