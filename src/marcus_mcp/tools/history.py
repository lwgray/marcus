"""
Project History Query Tools for Marcus MCP.

Exposes ProjectHistoryQuery API to agents via MCP protocol,
enabling agents to:
- Query task execution history
- Search decisions and their impact
- Find artifacts produced during execution
- Analyze agent performance
- Search conversations and timeline events
- Generate project summaries
"""

import logging
from typing import Any, Optional

from src.analysis.aggregator import ProjectHistoryAggregator
from src.analysis.query_api import ProjectHistoryQuery

logger = logging.getLogger(__name__)


async def query_project_history(
    project_id: str,
    query_type: str,
    state: Any,
    **filters: Any,
) -> dict[str, Any]:
    """
    Query project history with flexible filtering.

    This unified MCP tool provides access to all project history queries.
    Agents can query tasks, decisions, artifacts, agents, timeline, and
    conversations.

    Parameters
    ----------
    project_id : str
        Project to query
    query_type : str
        Type of query to perform:
        - "summary": Get project summary statistics
        - "tasks": Find tasks (filters: status, agent_id, start_time, end_time)
        - "blocked_tasks": Find tasks with blockers
        - "task_dependencies": Get dependency chain (requires: task_id)
        - "decisions": Find decisions (filters: task_id, agent_id, affecting_task_id)  # noqa: E501
        - "artifacts": Find artifacts (filters: task_id, artifact_type, agent_id)
        - "agent_history": Get agent history (requires: agent_id)
        - "agent_metrics": Get agent performance metrics (requires: agent_id)
        - "timeline": Search timeline (filters: event_type, agent_id, task_id,
          start_time, end_time)
        - "conversations": Search conversations (filters: keyword, agent_id, task_id)  # noqa: E501
    state : Any
        Marcus server state
    **filters : Any
        Additional filters specific to query_type

    Returns
    -------
    dict[str, Any]
        Query results with success status and data

    Examples
    --------
    Get project summary:
    >>> await query_project_history("proj123", "summary", state)

    Find completed tasks:
    >>> await query_project_history("proj123", "tasks", state, status="completed")

    Find decisions by agent:
    >>> await query_project_history("proj123", "decisions", state, agent_id="agent1")  # noqa: E501

    Search conversations for keyword:
    >>> await query_project_history("proj123", "conversations", state, keyword="API")  # noqa: E501
    """
    try:
        # Initialize aggregator and query API
        aggregator = ProjectHistoryAggregator()
        query_api = ProjectHistoryQuery(aggregator)

        # Route to appropriate query method
        if query_type == "summary":
            summary = await query_api.get_project_summary(project_id)
            return {"success": True, "data": summary}

        elif query_type == "tasks":
            # Check which filter is provided
            if "status" in filters:
                tasks = await query_api.find_tasks_by_status(
                    project_id, filters["status"]
                )
            elif "agent_id" in filters:
                tasks = await query_api.find_tasks_by_agent(
                    project_id, filters["agent_id"]
                )
            elif "start_time" in filters:
                # Parse datetime if needed
                from datetime import datetime, timezone

                start_time_raw = filters.get("start_time")
                if isinstance(start_time_raw, str):
                    start_time = datetime.fromisoformat(start_time_raw)
                elif isinstance(start_time_raw, datetime):
                    start_time = start_time_raw
                else:
                    return {
                        "success": False,
                        "error": "start_time required for timerange query",
                    }

                end_time_raw = filters.get("end_time")
                if isinstance(end_time_raw, str):
                    end_time = datetime.fromisoformat(end_time_raw)
                elif isinstance(end_time_raw, datetime):
                    end_time = end_time_raw
                else:
                    end_time = datetime.now(timezone.utc)

                tasks = await query_api.find_tasks_in_timerange(
                    project_id, start_time, end_time
                )
            else:
                # No filter - get all tasks
                history = await query_api.get_project_history(project_id)
                tasks = history.tasks

            # Convert to dict for serialization
            return {
                "success": True,
                "data": [t.to_dict() for t in tasks],
                "count": len(tasks),
            }

        elif query_type == "blocked_tasks":
            tasks = await query_api.find_blocked_tasks(project_id)
            return {
                "success": True,
                "data": [t.to_dict() for t in tasks],
                "count": len(tasks),
            }

        elif query_type == "task_dependencies":
            task_id = filters.get("task_id")
            if not task_id:
                return {
                    "success": False,
                    "error": "task_id required for task_dependencies query",
                }

            chain = await query_api.get_task_dependency_chain(project_id, task_id)
            return {
                "success": True,
                "data": [t.to_dict() for t in chain],
                "count": len(chain),
            }

        elif query_type == "decisions":
            # Check which filter is provided
            if "task_id" in filters:
                decisions = await query_api.find_decisions_by_task(
                    project_id, filters["task_id"]
                )
            elif "agent_id" in filters:
                decisions = await query_api.find_decisions_by_agent(
                    project_id, filters["agent_id"]
                )
            elif "affecting_task_id" in filters:
                decisions = await query_api.find_decisions_affecting_task(
                    project_id, filters["affecting_task_id"]
                )
            else:
                # No filter - get all decisions
                history = await query_api.get_project_history(project_id)
                decisions = history.decisions

            return {
                "success": True,
                "data": [d.to_dict() for d in decisions],
                "count": len(decisions),
            }

        elif query_type == "artifacts":
            # Check which filter is provided
            if "task_id" in filters:
                artifacts = await query_api.find_artifacts_by_task(
                    project_id, filters["task_id"]
                )
            elif "artifact_type" in filters:
                artifacts = await query_api.find_artifacts_by_type(
                    project_id, filters["artifact_type"]
                )
            elif "agent_id" in filters:
                artifacts = await query_api.find_artifacts_by_agent(
                    project_id, filters["agent_id"]
                )
            else:
                # No filter - get all artifacts
                history = await query_api.get_project_history(project_id)
                artifacts = history.artifacts

            return {
                "success": True,
                "data": [a.to_dict() for a in artifacts],
                "count": len(artifacts),
            }

        elif query_type == "agent_history":
            agent_id = filters.get("agent_id")
            if not agent_id:
                return {
                    "success": False,
                    "error": "agent_id required for agent_history query",
                }

            agent = await query_api.get_agent_history(project_id, agent_id)
            if not agent:
                return {
                    "success": False,
                    "error": f"Agent {agent_id} not found in project {project_id}",
                }

            return {"success": True, "data": agent.to_dict()}

        elif query_type == "agent_metrics":
            agent_id = filters.get("agent_id")
            if not agent_id:
                return {
                    "success": False,
                    "error": "agent_id required for agent_metrics query",
                }

            metrics = await query_api.get_agent_performance_metrics(
                project_id, agent_id
            )
            return {"success": True, "data": metrics}

        elif query_type == "timeline":
            # Parse optional filters
            from datetime import datetime

            event_type_str = filters.get("event_type")
            event_type = event_type_str if isinstance(event_type_str, str) else None

            agent_id_str = filters.get("agent_id")
            agent_id = agent_id_str if isinstance(agent_id_str, str) else None

            task_id_str = filters.get("task_id")
            task_id = task_id_str if isinstance(task_id_str, str) else None

            timeline_start_raw = filters.get("start_time")
            timeline_start: Optional[datetime] = None
            if isinstance(timeline_start_raw, str):
                timeline_start = datetime.fromisoformat(timeline_start_raw)

            timeline_end_raw = filters.get("end_time")
            timeline_end: Optional[datetime] = None
            if isinstance(timeline_end_raw, str):
                timeline_end = datetime.fromisoformat(timeline_end_raw)

            events = await query_api.search_timeline(
                project_id,
                event_type=event_type,
                agent_id=agent_id,
                task_id=task_id,
                start_time=timeline_start,
                end_time=timeline_end,
            )

            # Convert events to dict manually
            event_dicts = []
            for event in events:
                event_dicts.append(
                    {
                        "timestamp": event.timestamp.isoformat(),
                        "event_type": event.event_type,
                        "agent_id": event.agent_id,
                        "task_id": event.task_id,
                        "description": event.description,
                        "details": event.details,
                    }
                )

            return {
                "success": True,
                "data": event_dicts,
                "count": len(event_dicts),
            }

        elif query_type == "conversations":
            keyword_raw = filters.get("keyword")
            keyword = keyword_raw if isinstance(keyword_raw, str) else None

            agent_id_raw = filters.get("agent_id")
            agent_id = agent_id_raw if isinstance(agent_id_raw, str) else None

            task_id_raw = filters.get("task_id")
            task_id = task_id_raw if isinstance(task_id_raw, str) else None

            messages = await query_api.search_conversations(
                project_id,
                keyword=keyword,
                agent_id=agent_id,
                task_id=task_id,
            )

            # Convert messages to dict
            message_dicts = []
            for msg in messages:
                message_dicts.append(
                    {
                        "timestamp": msg.timestamp.isoformat(),
                        "direction": msg.direction,
                        "agent_id": msg.agent_id,
                        "content": msg.content,
                        "metadata": msg.metadata,
                    }
                )

            return {
                "success": True,
                "data": message_dicts,
                "count": len(message_dicts),
            }

        else:
            return {
                "success": False,
                "error": f"Unknown query_type: {query_type}",
                "supported_types": [
                    "summary",
                    "tasks",
                    "blocked_tasks",
                    "task_dependencies",
                    "decisions",
                    "artifacts",
                    "agent_history",
                    "agent_metrics",
                    "timeline",
                    "conversations",
                ],
            }

    except Exception as e:
        logger.error(f"Error querying project history: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "query_type": query_type,
            "project_id": project_id,
        }


async def list_project_history_files(state: Any) -> dict[str, Any]:
    """
    List all projects with available history data.

    Scans the project history storage directory to find all projects
    that have recorded history data (decisions, artifacts, snapshots).

    Parameters
    ----------
    state : Any
        Marcus server state

    Returns
    -------
    dict[str, Any]
        Dict with success status and list of project IDs with history

    Examples
    --------
    >>> await list_project_history_files(state)
    {
        "success": True,
        "projects": [
            {
                "project_id": "proj123",
                "project_name": "My App",
                "has_decisions": True,
                "has_artifacts": True,
                "has_snapshot": False,
                "last_updated": "2025-11-07T12:00:00Z"
            }
        ],
        "count": 1
    }
    """
    try:
        from src.core.project_history import ProjectHistoryPersistence

        persistence = ProjectHistoryPersistence()
        history_root = persistence.history_dir

        projects = []

        # Scan for project directories
        if history_root.exists():
            for project_dir in history_root.iterdir():
                if not project_dir.is_dir():
                    continue

                project_id = project_dir.name

                # Check what data exists
                decisions_file = project_dir / "decisions.jsonl"
                artifacts_file = project_dir / "artifacts.jsonl"
                snapshot_file = project_dir / "snapshot.json"

                has_decisions = decisions_file.exists()
                has_artifacts = artifacts_file.exists()
                has_snapshot = snapshot_file.exists()

                # Get project name from snapshot if available
                project_name = project_id
                if has_snapshot:
                    import json

                    try:
                        snapshot_data = json.loads(snapshot_file.read_text())
                        project_name = snapshot_data.get("project_name", project_id)
                    except Exception:
                        pass

                # Get last modified time
                timestamps = []
                if has_decisions:
                    timestamps.append(decisions_file.stat().st_mtime)
                if has_artifacts:
                    timestamps.append(artifacts_file.stat().st_mtime)
                if has_snapshot:
                    timestamps.append(snapshot_file.stat().st_mtime)

                last_updated = None
                if timestamps:
                    from datetime import datetime, timezone

                    last_updated = datetime.fromtimestamp(
                        max(timestamps), tz=timezone.utc
                    ).isoformat()

                projects.append(
                    {
                        "project_id": project_id,
                        "project_name": project_name,
                        "has_decisions": has_decisions,
                        "has_artifacts": has_artifacts,
                        "has_snapshot": has_snapshot,
                        "last_updated": last_updated,
                    }
                )

        return {"success": True, "projects": projects, "count": len(projects)}

    except Exception as e:
        logger.error(f"Error listing project history files: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
