"""
Artifact management tools with prescriptive storage locations.

These tools help agents store and track design artifacts in organized
locations while allowing flexibility when needed.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default artifact storage paths by type
ARTIFACT_PATHS = {
    "specification": "docs/specifications",
    "api": "docs/api",
    "design": "docs/design",
    "architecture": "docs/architecture",
    "documentation": "docs",
    "reference": "docs/references",
    "temporary": "tmp/artifacts",  # Should be .gitignored
}


async def log_artifact(
    task_id: str,
    filename: str,
    content: str,
    artifact_type: str,
    description: Optional[str] = None,
    location: Optional[str] = None,  # Optional override
    state: Any = None,
) -> Dict[str, Any]:
    """
    Store an artifact with prescriptive location management.

    By default, artifacts are stored in standard locations based on their type:
    - specifications → docs/specifications/
    - api → docs/api/
    - design → docs/design/
    - architecture → docs/architecture/
    - documentation → docs/
    - reference → docs/references/
    - temporary → tmp/artifacts/

    Args:
        task_id: The current task ID
        filename: Name for the artifact file
        content: The artifact content to store
        artifact_type: Type of artifact (determines default location)
        description: Optional description of the artifact
        location: Optional override for storage location (relative path)
        state: MCP state object

    Returns:
        Dict with artifact location and storage details
    """
    try:
        # Validate artifact type
        valid_types = [
            "specification",
            "api",
            "design",
            "architecture",
            "documentation",
            "reference",
            "temporary",
        ]
        if artifact_type not in valid_types:
            return {
                "success": False,
                "error": (
                    f"Invalid artifact_type '{artifact_type}'. "
                    f"Must be one of: {', '.join(valid_types)}"
                ),
                "data": {"task_id": task_id, "filename": filename},
            }

        # Determine storage location
        if location:
            # Use provided location (but ensure it's relative)
            artifact_path = Path(location)
            if artifact_path.is_absolute():
                return {
                    "success": False,
                    "error": "Location must be a relative path",
                    "data": {"task_id": task_id, "filename": filename},
                }
        else:
            # Use default location based on type
            base_dir = ARTIFACT_PATHS.get(artifact_type, "docs/artifacts")
            artifact_path = Path(base_dir) / filename

        # Create full path
        full_path = Path.cwd() / artifact_path

        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        full_path.write_text(content, encoding="utf-8")

        # Initialize task_artifacts if not exists
        if not hasattr(state, "task_artifacts"):
            state.task_artifacts = {}

        if task_id not in state.task_artifacts:
            state.task_artifacts[task_id] = []

        # Log the artifact
        artifact_entry = {
            "filename": filename,
            "location": str(artifact_path),
            "artifact_type": artifact_type,
            "description": description,
            "is_default_location": location is None,
        }

        state.task_artifacts[task_id].append(artifact_entry)

        # Add a comment to the task if kanban is available
        if state.kanban_client and description:
            try:
                # Find the task
                task = next((t for t in state.project_tasks if t.id == task_id), None)
                if task:
                    card_id = getattr(task, "kanban_card_id", None) or task.id
                    location_type = "default" if location is None else "custom"
                    await state.kanban_client.add_comment(
                        task_id=card_id,
                        comment=(
                            f"📄 Created {artifact_type} artifact: {filename}\n"
                            f"Location: {artifact_path} ({location_type})\n\n{description}"
                        ),
                    )
            except Exception as e:
                logger.warning(f"Could not add comment: {e}")

        logger.info(
            f"Stored {artifact_type} artifact {filename} for task {task_id} at {artifact_path}"
        )

        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "filename": filename,
                "location": str(artifact_path),
                "full_path": str(full_path),
                "artifact_type": artifact_type,
                "is_default_location": location is None,
                "description": description,
            },
        }

    except Exception as e:
        logger.error(f"Error storing artifact: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to store artifact: {str(e)}",
            "data": {"task_id": task_id, "filename": filename},
        }


async def get_task_context(
    task_id: str,
    include_dependencies: bool = True,
    include_blockers: bool = True,
    include_artifacts: bool = True,
    state: Any = None,
) -> Dict[str, Any]:
    """
    Get comprehensive context for a task including dependencies and artifacts.

    This tool provides agents with all relevant context about a task including:
    - Task details and current status
    - Dependencies (tasks that must be completed before this one)
    - Blockers (current issues preventing progress)
    - Artifacts (design documents with their storage locations)

    Args:
        task_id: The task ID to get context for
        include_dependencies: Whether to include dependency information
        include_blockers: Whether to include blocker information
        include_artifacts: Whether to include artifact information
        state: MCP state object

    Returns:
        Dict with comprehensive task context
    """
    try:
        # Find the task
        task = next((t for t in state.project_tasks if t.id == task_id), None)
        if not task:
            return {
                "success": False,
                "error": f"Task {task_id} not found",
                "data": {"task_id": task_id},
            }

        # Build context object
        context: Dict[str, Any] = {
            "task": {
                "id": task.id,
                "name": task.name,
                "description": task.description,
                "status": task.status.value if task.status else None,
                "priority": task.priority.value if task.priority else None,
                "assigned_to": task.assigned_to,
                "labels": task.labels,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
        }

        # Add dependencies if requested
        if include_dependencies:
            dependencies = []
            if hasattr(task, "dependencies") and task.dependencies:
                for dep_id in task.dependencies:
                    dep_task = next(
                        (t for t in state.project_tasks if t.id == dep_id), None
                    )
                    if dep_task:
                        dependencies.append(
                            {
                                "id": dep_task.id,
                                "title": dep_task.title,
                                "status": (
                                    dep_task.status.value if dep_task.status else None
                                ),
                                "completed": dep_task.status
                                and dep_task.status.value
                                in ["completed", "done", "closed"],
                            }
                        )
            context["dependencies"] = dependencies

        # Add blockers if requested
        if include_blockers:
            blockers = []
            if hasattr(state, "task_blockers") and task_id in state.task_blockers:
                blockers = state.task_blockers[task_id]
            context["blockers"] = blockers

        # Add artifacts if requested
        if include_artifacts:
            artifacts = []
            if hasattr(state, "task_artifacts") and task_id in state.task_artifacts:
                artifacts = state.task_artifacts[task_id]

            # Also scan filesystem for artifacts in standard locations
            # This helps discover artifacts created outside of log_artifact
            discovered = await _discover_artifacts_in_standard_locations()

            # Merge discovered artifacts (avoiding duplicates)
            existing_locations = {a["location"] for a in artifacts}
            for artifact in discovered:
                if artifact["location"] not in existing_locations:
                    artifact["discovered"] = True
                    artifacts.append(artifact)

            context["artifacts"] = artifacts

        # Add any logged decisions
        decisions = []
        if hasattr(state, "task_decisions") and task_id in state.task_decisions:
            decisions = state.task_decisions[task_id]
        context["decisions"] = decisions

        logger.info(f"Retrieved context for task {task_id}")

        return {"success": True, "context": context}

    except Exception as e:
        logger.error(f"Error getting task context: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get task context: {str(e)}",
            "data": {"task_id": task_id},
        }


async def _discover_artifacts_in_standard_locations() -> List[Dict[str, Any]]:
    """Scan standard artifact directories for files."""
    discovered = []

    for artifact_type, base_path in ARTIFACT_PATHS.items():
        path = Path(base_path)
        if path.exists():
            try:
                for file_path in path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        discovered.append(
                            {
                                "filename": file_path.name,
                                "location": str(file_path.relative_to(Path.cwd())),
                                "artifact_type": artifact_type,
                                "description": f"Discovered {artifact_type} file",
                                "is_default_location": True,
                            }
                        )
            except Exception as e:
                logger.warning(f"Error scanning {base_path}: {e}")

    return discovered
