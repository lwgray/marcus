"""Context Tools for Marcus MCP.

This module contains tools for context management:
- log_decision: Log architectural decisions
- get_task_context: Get context for a specific task
"""

from pathlib import Path
from typing import Any, Dict, List


async def log_decision(
    agent_id: str, task_id: str, decision: str, state: Any
) -> Dict[str, Any]:
    """
    Log an architectural decision made during task implementation.

    Agents use this to document important technical choices that might
    affect other tasks. Decisions are automatically cross-referenced
    to dependent tasks.

    Parameters
    ----------
    agent_id : str
        The agent making the decision
    task_id : str
        Current task ID
    decision : str
        Natural language description of the decision
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with success status and decision details
    """
    try:
        # Check if Context system is available
        if not hasattr(state, "context") or not state.context:
            return {"success": False, "error": "Context system not enabled"}

        # Parse decision from natural language
        # Expected format: "I chose X because Y. This affects Z."
        parts = decision.split(".", 2)

        what = decision  # Default to full decision
        why = "Not specified"
        impact = "May affect dependent tasks"

        # Try to parse structured format
        if len(parts) >= 1 and "because" in parts[0]:
            what_parts = parts[0].split("because", 1)
            what = what_parts[0].strip()
            if len(what_parts) > 1:
                why = what_parts[1].strip()

        if len(parts) >= 2 and any(
            word in parts[1].lower() for word in ["affect", "impact", "require"]
        ):
            impact = parts[1].strip()

        # Log the decision
        logged_decision = await state.context.log_decision(
            agent_id=agent_id, task_id=task_id, what=what, why=why, impact=impact
        )

        # Add comment to task if kanban is available
        if state.kanban_client:
            comment = f"🏗️ ARCHITECTURAL DECISION by {agent_id}\\n"
            comment += f"Decision: {what}\\n"
            comment += f"Reasoning: {why}\\n"
            comment += f"Impact: {impact}"

            await state.kanban_client.add_comment(task_id, comment)

        # Log event (non-blocking)
        if hasattr(state, "events") and state.events:
            await state.events.publish_nowait(
                "decision_logged", agent_id, logged_decision.to_dict()
            )

        # Record in active experiment if one is running
        from src.experiments.live_experiment_monitor import get_active_monitor

        monitor = get_active_monitor()
        if monitor and monitor.is_running:
            monitor.record_decision(
                agent_id=agent_id, task_id=task_id, decision=decision
            )

        return {
            "success": True,
            "decision_id": logged_decision.decision_id,
            "message": "Decision logged and cross-referenced to dependent tasks",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def get_task_context(task_id: str, state: Any) -> Dict[str, Any]:
    """
    Get the full context for a specific task.

    This is useful for agents who want to understand the broader
    context of their work or review decisions made on dependencies.

    For subtasks, includes parent task context and shared conventions.

    Parameters
    ----------
    task_id : str
        The task to get context for (can be regular task or subtask ID)
    state : Any
        Marcus server state instance

    Returns
    -------
    Dict[str, Any]
        Dict with task context including implementations, dependencies, and
        decisions. For subtasks, includes parent_task, shared_conventions,
        and dependency_artifacts.
    """
    try:
        # Check if this is a subtask
        if hasattr(state, "subtask_manager") and state.subtask_manager:
            # Check if task_id is a subtask
            if task_id in state.subtask_manager.subtasks:
                # Get subtask context
                subtask_context = state.subtask_manager.get_subtask_context(task_id)

                # Get parent task context
                parent_task_id = subtask_context["parent_task_id"]
                parent_task = None
                for t in state.project_tasks:
                    if t.id == parent_task_id:
                        parent_task = t
                        break

                # Build enriched context
                context_dict = {
                    "is_subtask": True,
                    "subtask_info": subtask_context["subtask"],
                    "parent_task": (
                        {
                            "id": parent_task_id,
                            "name": parent_task.name if parent_task else "Unknown",
                            "description": (
                                parent_task.description if parent_task else ""
                            ),
                            "labels": parent_task.labels if parent_task else [],
                        }
                        if parent_task
                        else {"id": parent_task_id}
                    ),
                    "shared_conventions": subtask_context["shared_conventions"],
                    "dependency_artifacts": subtask_context["dependency_artifacts"],
                    "sibling_subtasks": subtask_context["sibling_subtasks"],
                }

                # Add parent task's context if Context system is available
                if hasattr(state, "context") and state.context and parent_task:
                    parent_context = await state.context.get_context(
                        parent_task_id, parent_task.dependencies or []
                    )
                    context_dict["parent_context"] = parent_context.to_dict()

                return {"success": True, "context": context_dict}

        # Standard task context (not a subtask)
        # Check if Context system is available
        if not hasattr(state, "context") or not state.context:
            return {"success": False, "error": "Context system not enabled"}

        # Find the task
        task = None
        for t in state.project_tasks:
            if t.id == task_id:
                task = t
                break

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Get context
        context = await state.context.get_context(task_id, task.dependencies or [])
        context_dict = context.to_dict()
        context_dict["is_subtask"] = False

        # Add artifact information
        artifacts = await _collect_task_artifacts(task_id, task, state)
        context_dict["artifacts"] = artifacts

        return {"success": True, "context": context_dict}

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _collect_task_artifacts(
    task_id: str, task: Any, state: Any
) -> List[Dict[str, Any]]:
    """
    Collect all artifacts available for this task from multiple sources.

    Returns artifacts from:
    1. Repository-based artifacts (docs/ directory)
    2. Kanban attachments for this task
    3. Artifacts from dependency tasks
    """
    artifacts = []

    try:
        # 1. Collect repository-based artifacts
        repo_artifacts = _scan_repository_artifacts(task_id)
        artifacts.extend(repo_artifacts)

        # 2. Collect kanban attachments for this task
        if state.kanban_client:
            try:
                card_id = getattr(task, "kanban_card_id", None) or task.id
                result = await state.kanban_client.get_attachments(card_id=card_id)
                if result.get("success", False):
                    attachments = result.get("data", [])
                    for attachment in attachments:
                        artifacts.append(
                            {
                                "filename": attachment.get("name"),
                                "location": (
                                    f"./attachments/{attachment.get('id')}/"
                                    f"{attachment.get('name')}"
                                ),
                                "storage_type": "attachment",
                                "artifact_type": "reference",  # Default for attachments
                                "created_by": attachment.get("userId"),
                                "created_at": attachment.get("createdAt"),
                                "description": f"Attachment from task {task_id}",
                            }
                        )
            except Exception as e:
                # Don't fail the whole operation if kanban is unavailable
                # Log the error for debugging but continue with artifact collection
                print(
                    f"Warning: Failed to get kanban attachments for task {task_id}: {e}"
                )

        # 3. Collect artifacts from dependency tasks
        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = next(
                    (t for t in state.project_tasks if t.id == dep_id), None
                )
                if dep_task:
                    # Repository artifacts from dependency
                    dep_repo_artifacts = _scan_repository_artifacts(dep_id)
                    for artifact in dep_repo_artifacts:
                        artifact["dependency_task_id"] = dep_id
                        artifact["dependency_task_name"] = dep_task.name
                        artifact["description"] = (
                            f"{artifact['description']} "
                            f"(from dependency: {dep_task.name})"
                        )
                    artifacts.extend(dep_repo_artifacts)

                    # Kanban attachments from dependency
                    if state.kanban_client:
                        try:
                            dep_card_id = (
                                getattr(dep_task, "kanban_card_id", None) or dep_task.id
                            )
                            result = await state.kanban_client.get_attachments(
                                card_id=dep_card_id
                            )
                            if result.get("success", False):
                                attachments = result.get("data", [])
                                for attachment in attachments:
                                    artifacts.append(
                                        {
                                            "filename": attachment.get("name"),
                                            "location": (
                                                f"./attachments/{attachment.get('id')}/"
                                                f"{attachment.get('name')}"
                                            ),
                                            "storage_type": "attachment",
                                            "artifact_type": "reference",
                                            "created_by": attachment.get("userId"),
                                            "created_at": attachment.get("createdAt"),
                                            "dependency_task_id": dep_id,
                                            "dependency_task_name": dep_task.name,
                                            "description": (
                                                f"Attachment from dependency: "
                                                f"{dep_task.name}"
                                            ),
                                        }
                                    )
                        except Exception as e:
                            # Don't fail if kanban is unavailable
                            # Log the error for debugging but continue
                            # with artifact collection
                            print(
                                f"Warning: Failed to get kanban attachments "
                                f"for dependency {dep_id}: {e}"
                            )

    except Exception as e:
        # Don't fail the whole context operation if artifact collection fails
        # Log the error for debugging but return partial results
        print(f"Warning: Artifact collection encountered an error: {e}")

    return artifacts


def _scan_repository_artifacts(task_id: str) -> List[Dict[str, Any]]:
    """
    Scan repository for artifacts that might be relevant to this task.

    Looks in docs/ directories for specifications, documentation, etc.
    """
    artifacts = []
    docs_paths = [
        "docs/api",
        "docs/schema",
        "docs/specifications",
        "docs/architecture",
        "docs/setup",
        "docs",
    ]

    for docs_path in docs_paths:
        path = Path(docs_path)
        if path.exists() and path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith("."):
                    # Determine artifact type based on location and content
                    artifact_type = _determine_artifact_type(file_path)

                    artifacts.append(
                        {
                            "filename": file_path.name,
                            "location": str(file_path),
                            "storage_type": "repository",
                            "artifact_type": artifact_type,
                            "description": (
                                f"{artifact_type.title()} file in repository"
                            ),
                        }
                    )

    return artifacts


def _determine_artifact_type(file_path: Path) -> str:
    """Determine artifact type based on file path and extension."""
    file_str = str(file_path).lower()

    if "api" in file_str or file_path.suffix in [".yaml", ".yml", ".json"]:
        if "schema" in file_str or "database" in file_str:
            return "specification"
        return "specification"
    elif file_path.suffix == ".md":
        if "architecture" in file_str or "design" in file_str:
            return "documentation"
        return "documentation"
    else:
        return "documentation"
