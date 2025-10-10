"""
Artifact management tools with prescriptive storage locations.

This module provides tools to help agents store and track design
artifacts in organized locations while allowing flexibility when needed.
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
    project_root: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,  # Optional override
    state: Any = None,
) -> Dict[str, Any]:
    """
    Store an artifact with prescriptive location management.

    By default, artifacts are stored in standard locations based on
    their type. Marcus accepts ANY artifact type, making it domain-agnostic.

    Standard types (with predefined locations):
    - specification → docs/specifications/
    - api → docs/api/
    - design → docs/design/
    - architecture → docs/architecture/
    - documentation → docs/
    - reference → docs/references/
    - temporary → tmp/artifacts/

    Custom types:
    - Any other type → docs/artifacts/ (default fallback)
    - You can use domain-specific types like "podcast-script", "research",
      "video-storyboard", "marketing-copy", etc.

    Parameters
    ----------
    task_id : str
        The current task ID
    filename : str
        Name for the artifact file
    content : str
        The artifact content to store
    artifact_type : str
        Type of artifact (determines default location)
    project_root : Optional[str], optional
        Absolute path to the project root directory where artifacts
        will be created. All agents should use the same path.
    description : Optional[str], optional
        Optional description of the artifact
    location : Optional[str], optional
        Optional override for storage location (relative path)
    state : Any, optional
        MCP state object

    Returns
    -------
    Dict[str, Any]
        Dict with artifact location and storage details
    """
    try:
        # Validate project_root is provided
        if not project_root:
            return {
                "success": False,
                "error": "project_root is required",
                "data": {"task_id": task_id, "filename": filename},
            }

        # Validate project_root is absolute and exists
        project_root_path = Path(project_root)
        if not project_root_path.is_absolute():
            return {
                "success": False,
                "error": "project_root must be an absolute path",
                "data": {"task_id": task_id, "filename": filename},
            }
        if not project_root_path.exists():
            return {
                "success": False,
                "error": f"project_root directory does not exist: {project_root}",
                "data": {"task_id": task_id, "filename": filename},
            }

        # Log info for non-standard artifact types (but still accept them!)
        standard_types = [
            "specification",
            "api",
            "design",
            "architecture",
            "documentation",
            "reference",
            "temporary",
        ]
        if artifact_type not in standard_types:
            logger.info(
                f"Using custom artifact type '{artifact_type}' for {filename}. "
                f"Will store in docs/artifacts/ (use 'location' parameter to override)"
            )

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

        # Create full path using project_root instead of Path.cwd()
        full_path = project_root_path / artifact_path

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
                    comment_text = (
                        f"📄 Created {artifact_type} artifact: {filename}\n"
                        f"Location: {artifact_path} ({location_type})\n\n"
                        f"{description}"
                    )
                    await state.kanban_client.add_comment(
                        task_id=card_id,
                        comment=comment_text,
                    )
            except Exception as e:
                logger.warning(f"Could not add comment: {e}")

        log_msg = (
            f"Stored {artifact_type} artifact {filename} for task "
            f"{task_id} at {artifact_path}"
        )
        logger.info(log_msg)

        # Record in active experiment if one is running
        from src.experiments.live_experiment_monitor import get_active_monitor

        monitor = get_active_monitor()
        if monitor and monitor.is_running:
            monitor.record_artifact(
                task_id=task_id,
                artifact_type=artifact_type,
                filename=filename,
                description=description or "",
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


async def _discover_artifacts_in_standard_locations(
    working_dir: Path,
) -> List[Dict[str, Any]]:
    """
    Scan standard artifact directories for files in project directory.

    Parameters
    ----------
    working_dir : Path
        The project root directory to scan for artifacts

    Returns
    -------
    List[Dict[str, Any]]
        List of discovered artifact dictionaries
    """
    discovered = []

    for artifact_type, base_path in ARTIFACT_PATHS.items():
        # Use working_dir instead of current directory
        path = working_dir / base_path
        if path.exists():
            try:
                for file_path in path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith("."):
                        discovered.append(
                            {
                                "filename": file_path.name,
                                "location": str(file_path.relative_to(working_dir)),
                                "artifact_type": artifact_type,
                                "description": f"Discovered {artifact_type} file",
                                "is_default_location": True,
                            }
                        )
            except Exception as e:
                logger.warning(f"Error scanning {base_path}: {e}")

    return discovered
