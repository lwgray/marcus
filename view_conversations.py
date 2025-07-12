#!/usr/bin/env python3
"""
Simple conversation viewer - just run and watch

Usage: python view_conversations.py
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

# Find log directory
LOG_DIR = Path("logs/conversations")
if not LOG_DIR.exists():
    LOG_DIR = Path("marcus_logs")
    if not LOG_DIR.exists():
        print("No conversation logs found. Run Marcus first.")
        exit(1)


def tail_logs():
    """Simple tail -f for conversation logs"""
    print("=== Marcus Conversations ===\n")

    # Track processed lines
    seen = set()

    while True:
        # Get all log files
        log_files = list(LOG_DIR.glob("*.jsonl"))

        for log_file in sorted(log_files):
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        if line.strip() and line not in seen:
                            seen.add(line)
                            try:
                                data = json.loads(line)

                                # Simple formatting
                                timestamp = data.get("timestamp", "")[
                                    :19
                                ]  # Just date/time
                                source = data.get("source", data.get("worker_id", "?"))
                                target = data.get("target", "marcus")
                                message = data.get("message", data.get("thought", ""))

                                # Color coding
                                if "decision" in data.get("event", ""):
                                    prefix = "🧠"  # Brain for decisions
                                elif "blocker" in str(data):
                                    prefix = "🚫"  # Block for blockers
                                elif source == "marcus":
                                    prefix = "🤖"  # Robot for Marcus
                                else:
                                    prefix = "👤"  # Person for agents

                                # Print simple format
                                print(f"{timestamp} {prefix} {source} → {target}")
                                if message:
                                    print(
                                        f"   {message[:100]}{'...' if len(message) > 100 else ''}"
                                    )
                                print()

                            except:
                                pass
            except:
                pass

        time.sleep(1)  # Check for new logs every second


if __name__ == "__main__":
    try:
        tail_logs()
    except KeyboardInterrupt:
        print("\nStopped watching conversations.")
