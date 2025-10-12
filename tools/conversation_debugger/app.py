#!/usr/bin/env python3
"""
Marcus Conversation Debugger - Interactive Version 2.

A Flask-based web application for visualizing and debugging
conversations between Marcus and worker agents.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request

# Add Marcus root to path
MARCUS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MARCUS_ROOT))

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def get_log_directory() -> Path:
    """Get the conversation log directory."""
    # Use the same path as ConversationLogger
    return MARCUS_ROOT / "logs" / "conversations"


def get_projects() -> List[str]:
    """
    Get list of available projects from logs.

    Returns
    -------
    List[str]
        List of project names found in logs
    """
    # For now, return a placeholder - could be enhanced to parse from logs
    return ["Task Master Test", "All Projects"]


def load_conversations(
    hours_back: int = 24,
    worker_id: Optional[str] = None,
    filter_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load conversations from log files.

    Parameters
    ----------
    hours_back : int
        How many hours of history to load
    worker_id : Optional[str]
        Filter by specific worker ID
    filter_type : Optional[str]
        Filter by conversation type (worker_to_pm, pm_to_worker, etc.)
    limit : Optional[int]
        Maximum number of conversations to return

    Returns
    -------
    List[Dict[str, Any]]
        List of conversation entries sorted by timestamp
    """
    log_dir = get_log_directory()

    if not log_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(hours=hours_back)
    conversations = []

    # Read all conversation log files
    for log_file in sorted(log_dir.glob("conversations_*.jsonl")):
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # Parse timestamp
                        timestamp_str = entry.get("timestamp", "")
                        if not timestamp_str:
                            continue

                        try:
                            timestamp = datetime.fromisoformat(
                                timestamp_str.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            continue

                        # Filter by time
                        if timestamp < cutoff:
                            continue

                        # Filter by worker
                        if worker_id and entry.get("worker_id") != worker_id:
                            continue

                        # Filter by conversation type
                        if filter_type and entry.get("conversation_type") != filter_type:
                            continue

                        conversations.append(entry)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error reading log file {log_file}: {e}", file=sys.stderr)
            continue

    # Sort by timestamp
    conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Apply limit
    if limit:
        conversations = conversations[:limit]

    return conversations


def get_workers() -> List[str]:
    """
    Get list of unique worker IDs from recent conversations.

    Returns
    -------
    List[str]
        List of worker IDs
    """
    conversations = load_conversations(hours_back=168)  # Last week
    workers = set()

    for conv in conversations:
        worker_id = conv.get("worker_id")
        if worker_id:
            workers.add(worker_id)

    return sorted(list(workers))


def format_timestamp(timestamp_str: str) -> str:
    """
    Format timestamp for display.

    Parameters
    ----------
    timestamp_str : str
        ISO format timestamp string

    Returns
    -------
    str
        Human-readable timestamp
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        delta = now - dt

        if delta.total_seconds() < 60:
            return "Just now"
        elif delta.total_seconds() < 3600:
            mins = int(delta.total_seconds() / 60)
            return f"{mins} min{'s' if mins != 1 else ''} ago"
        elif delta.total_seconds() < 86400:
            hours = int(delta.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp_str


# Jinja2 filter
app.jinja_env.filters["format_timestamp"] = format_timestamp


@app.route("/")
def index():
    """Main conversation viewer page."""
    projects = get_projects()
    workers = get_workers()
    return render_template("index.html", projects=projects, workers=workers)


@app.route("/api/conversations")
def get_conversations_api():
    """
    API endpoint for conversation data.

    Query Parameters
    ----------------
    hours : int
        Hours of history to load (default: 24)
    worker_id : str
        Filter by worker ID (optional)
    filter_type : str
        Filter by conversation type (optional)
    limit : int
        Maximum results to return (optional)

    Returns
    -------
    JSON
        List of conversation entries
    """
    hours_back = int(request.args.get("hours", 24))
    worker_id = request.args.get("worker_id")
    filter_type = request.args.get("filter_type")
    limit = request.args.get("limit")

    if worker_id == "":
        worker_id = None
    if filter_type == "":
        filter_type = None
    if limit:
        limit = int(limit)

    conversations = load_conversations(
        hours_back=hours_back,
        worker_id=worker_id,
        filter_type=filter_type,
        limit=limit,
    )

    return jsonify(conversations)


@app.route("/api/stats")
def get_stats():
    """
    Get conversation statistics.

    Returns
    -------
    JSON
        Statistics about conversations
    """
    conversations = load_conversations(hours_back=24)

    stats = {
        "total_conversations": len(conversations),
        "by_type": {},
        "by_worker": {},
        "recent_activity": len(
            [c for c in conversations if format_timestamp(c.get("timestamp", "")) == "Just now"]
        ),
    }

    for conv in conversations:
        conv_type = conv.get("conversation_type", "unknown")
        stats["by_type"][conv_type] = stats["by_type"].get(conv_type, 0) + 1

        worker_id = conv.get("worker_id")
        if worker_id:
            stats["by_worker"][worker_id] = stats["by_worker"].get(worker_id, 0) + 1

    return jsonify(stats)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("    🤖 Marcus Conversation Debugger (Interactive)")
    print("=" * 70)
    print("\n[I] Starting server at http://127.0.0.1:5001")
    print("[I] Log directory:", get_log_directory())
    print("[I] Press Ctrl+C to stop\n")

    app.run(debug=True, port=5002, host="127.0.0.1")
