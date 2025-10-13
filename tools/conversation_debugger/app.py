#!/usr/bin/env python3
"""
Marcus Conversation Debugger - Interactive Version 2.

A Flask-based web application for visualizing and debugging
conversations between Marcus and worker agents.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request

# Add Marcus root to path
MARCUS_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(MARCUS_ROOT))

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def get_log_directory() -> Path:
    """Get the conversation log directory."""
    # Use the same path as ConversationLogger
    return MARCUS_ROOT / "logs" / "conversations"


def get_projects() -> List[Dict[str, str]]:
    """
    Get list of available projects from logs.

    Returns
    -------
    List[Dict[str, str]]
        List of dicts with project_id and project_name found in logs
    """
    log_dir = get_log_directory()

    if not log_dir.exists():
        return []

    projects_seen: Dict[str, str] = {}  # project_id -> project_name

    # Read all conversation log files to extract unique projects
    for log_file in sorted(log_dir.glob("conversations_*.jsonl")):
        try:
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        metadata = entry.get("metadata", {})

                        project_id = metadata.get("project_id")
                        project_name = metadata.get("project_name")

                        if project_id and project_name:
                            projects_seen[project_id] = project_name

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error reading log file {log_file}: {e}", file=sys.stderr)
            continue

    # Return as list of dicts
    return [{"id": pid, "name": pname} for pid, pname in sorted(projects_seen.items())]


def load_conversations(
    hours_back: int = 24,
    worker_id: Optional[str] = None,
    filter_type: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: Optional[int] = None,
    page: int = 1,
) -> tuple[List[Dict[str, Any]], int]:
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
    project_id : Optional[str]
        Filter by specific project ID
    limit : Optional[int]
        Maximum number of conversations to return per page
    page : int
        Page number (1-indexed)

    Returns
    -------
    tuple[List[Dict[str, Any]], int]
        Tuple of (conversation entries, total count)
    """
    log_dir = get_log_directory()

    if not log_dir.exists():
        return [], 0

    # Create timezone-aware cutoff to compare with log timestamps
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
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
                        if (
                            filter_type
                            and entry.get("conversation_type") != filter_type
                        ):
                            continue

                        # Filter by project
                        if project_id:
                            metadata = entry.get("metadata", {})
                            entry_project_id = metadata.get("project_id")
                            if entry_project_id != project_id:
                                continue

                        conversations.append(entry)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            print(f"Error reading log file {log_file}: {e}", file=sys.stderr)
            continue

    # Sort by timestamp
    conversations.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Get total count before pagination
    total_count = len(conversations)

    # Apply pagination
    if limit:
        offset = (page - 1) * limit
        conversations = conversations[offset : offset + limit]

    return conversations, total_count


def get_workers() -> List[str]:
    """
    Get list of unique worker IDs from recent conversations.

    Returns
    -------
    List[str]
        List of worker IDs
    """
    conversations, _ = load_conversations(hours_back=168)  # Last week
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


@app.route("/")  # type: ignore[misc]
def index() -> str:
    """Render the main conversation viewer page."""
    projects = get_projects()
    workers = get_workers()
    return render_template(  # type: ignore[no-any-return]
        "index.html", projects=projects, workers=workers
    )


@app.route("/api/conversations")  # type: ignore[misc]
def get_conversations_api() -> Response:
    """
    Return conversation data from logs.

    Query Parameters
    ----------------
    hours : int
        Hours of history to load (default: 24)
    worker_id : str
        Filter by worker ID (optional)
    filter_type : str
        Filter by conversation type (optional)
    project_id : str
        Filter by project ID (optional)
    limit : int
        Maximum results to return per page (optional)
    page : int
        Page number (default: 1)

    Returns
    -------
    Response
        JSON response with conversation entries and pagination info
    """
    hours_back = int(request.args.get("hours", 24))
    worker_id = request.args.get("worker_id")
    filter_type = request.args.get("filter_type")
    project_id = request.args.get("project_id")
    limit_str = request.args.get("limit")
    page_str = request.args.get("page", "1")

    if worker_id == "":
        worker_id = None
    if filter_type == "":
        filter_type = None
    if project_id == "":
        project_id = None

    limit: Optional[int] = None
    if limit_str:
        limit = int(limit_str)

    page = int(page_str)

    conversations, total_count = load_conversations(
        hours_back=hours_back,
        worker_id=worker_id,
        filter_type=filter_type,
        project_id=project_id,
        limit=limit,
        page=page,
    )

    # Calculate pagination info
    total_pages = (total_count + (limit - 1)) // limit if limit else 1

    return jsonify(
        {
            "conversations": conversations,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages,
            },
        }
    )


@app.route("/api/stats")  # type: ignore[misc]
def get_stats() -> Response:
    """
    Return conversation statistics.

    Returns
    -------
    Response
        JSON response with statistics about conversations
    """
    conversations, _ = load_conversations(hours_back=24)

    stats: Dict[str, Any] = {
        "total_conversations": len(conversations),
        "by_type": {},
        "by_worker": {},
        "recent_activity": len(
            [
                c
                for c in conversations
                if format_timestamp(c.get("timestamp", "")) == "Just now"
            ]
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

    # Debug mode is acceptable for this local development/debugging tool
    app.run(debug=True, port=5002, host="127.0.0.1")  # nosec B201
