"""
Subtask Manager for Marcus.

This module handles hierarchical task decomposition, tracking subtasks
and their relationship to parent tasks.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.models import Priority, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class Subtask:
    """
    Represents a subtask decomposed from a parent task.

    Parameters
    ----------
    id : str
        Unique identifier for the subtask
    parent_task_id : str
        ID of the parent task this subtask belongs to
    name : str
        Short descriptive name of the subtask
    description : str
        Detailed description of what needs to be done
    status : TaskStatus
        Current state of the subtask
    priority : Priority
        Urgency level inherited from parent or adjusted
    assigned_to : Optional[str]
        ID of the worker assigned to this subtask
    created_at : datetime
        Timestamp when subtask was created
    estimated_hours : float
        Estimated time to complete in hours
    dependencies : List[str], optional
        List of other subtask IDs that must be completed first
    dependency_types : List[str], optional
        Type of each dependency: "hard" (blocks start) or "soft" (can use mock/contract)
        Must match length of dependencies list
    file_artifacts : List[str], optional
        Expected file outputs from this subtask
    provides : Optional[str]
        What this subtask provides for dependent subtasks
    requires : Optional[str]
        What this subtask requires from dependencies
    """

    id: str
    parent_task_id: str
    name: str
    description: str
    status: TaskStatus
    priority: Priority
    assigned_to: Optional[str]
    created_at: datetime
    estimated_hours: float
    dependencies: List[str] = field(default_factory=list)
    dependency_types: List[str] = field(default_factory=list)
    file_artifacts: List[str] = field(default_factory=list)
    provides: Optional[str] = None
    requires: Optional[str] = None
    order: int = 0  # Execution order within parent


@dataclass
class SubtaskMetadata:
    """
    Metadata about decomposed tasks.

    Parameters
    ----------
    shared_conventions : Dict[str, Any]
        Shared file structure and naming conventions
    decomposed_at : datetime
        When the parent task was decomposed
    decomposed_by : str
        What triggered decomposition (ai, manual, etc.)
    """

    shared_conventions: Dict[str, Any] = field(default_factory=dict)
    decomposed_at: datetime = field(default_factory=datetime.now)
    decomposed_by: str = "ai"


class SubtaskManager:
    """
    Manages hierarchical task decomposition and subtask tracking.

    This class handles:
    - Creating subtasks from parent tasks
    - Tracking subtask-to-parent relationships
    - Managing subtask completion and parent auto-completion
    - Persisting subtask state for recovery
    """

    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize the subtask manager.

        Parameters
        ----------
        state_file : Optional[Path]
            Path to JSON file for persisting subtask state.
            Defaults to data/marcus_state/subtasks.json
        """
        if state_file is None:
            state_file = Path("data/marcus_state/subtasks.json")

        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory tracking
        self.subtasks: Dict[str, Subtask] = {}  # subtask_id -> Subtask
        self.parent_to_subtasks: Dict[str, List[str]] = {}  # parent_id -> [subtask_ids]
        self.metadata: Dict[str, SubtaskMetadata] = {}  # parent_id -> metadata

        # Load existing state
        self._load_state()

    def add_subtasks(
        self,
        parent_task_id: str,
        subtasks: List[Dict[str, Any]],
        metadata: Optional[SubtaskMetadata] = None,
    ) -> List[Subtask]:
        """
        Add subtasks for a parent task.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task
        subtasks : List[Dict[str, Any]]
            List of subtask dictionaries with fields:
            - name, description, estimated_hours, dependencies, etc.
        metadata : Optional[SubtaskMetadata]
            Metadata about the decomposition

        Returns
        -------
        List[Subtask]
            Created Subtask objects
        """
        created_subtasks = []

        for idx, subtask_data in enumerate(subtasks):
            # Generate unique subtask ID
            subtask_id = f"{parent_task_id}_sub_{idx + 1}"

            # Get dependencies and dependency_types with migration fallback
            dependencies = subtask_data.get("dependencies", [])
            dependency_types = subtask_data.get("dependency_types", [])

            # Migration: if dependency_types not provided, default all to "hard"
            if not dependency_types and dependencies:
                dependency_types = ["hard"] * len(dependencies)
                logger.debug(
                    f"Migration: defaulting all dependencies to 'hard' for {subtask_id}"
                )

            subtask = Subtask(
                id=subtask_id,
                parent_task_id=parent_task_id,
                name=subtask_data["name"],
                description=subtask_data["description"],
                status=TaskStatus.TODO,
                priority=subtask_data.get("priority", Priority.MEDIUM),
                assigned_to=None,
                created_at=datetime.now(),
                estimated_hours=subtask_data.get("estimated_hours", 1.0),
                dependencies=dependencies,
                dependency_types=dependency_types,
                file_artifacts=subtask_data.get("file_artifacts", []),
                provides=subtask_data.get("provides"),
                requires=subtask_data.get("requires"),
                order=idx,
            )

            self.subtasks[subtask_id] = subtask
            created_subtasks.append(subtask)

        # Track parent relationship
        self.parent_to_subtasks[parent_task_id] = [s.id for s in created_subtasks]

        # Store metadata
        if metadata is None:
            metadata = SubtaskMetadata()
        self.metadata[parent_task_id] = metadata

        # Persist state
        self._save_state()

        logger.info(
            f"Created {len(created_subtasks)} subtasks for parent task {parent_task_id}"
        )

        return created_subtasks

    def get_subtasks(self, parent_task_id: str) -> List[Subtask]:
        """
        Get all subtasks for a parent task.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task

        Returns
        -------
        List[Subtask]
            List of Subtask objects ordered by execution order
        """
        subtask_ids = self.parent_to_subtasks.get(parent_task_id, [])
        subtasks = [self.subtasks[sid] for sid in subtask_ids if sid in self.subtasks]
        return sorted(subtasks, key=lambda s: s.order)

    def get_next_available_subtask(
        self, parent_task_id: str, completed_subtask_ids: set[str]
    ) -> Optional[Subtask]:
        """
        Get the next available subtask that has all dependencies completed.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task
        completed_subtask_ids : set
            Set of completed subtask IDs

        Returns
        -------
        Optional[Subtask]
            Next available subtask or None if all complete or blocked
        """
        subtasks = self.get_subtasks(parent_task_id)

        for subtask in subtasks:
            # Skip if already completed or in progress
            if subtask.status in [TaskStatus.DONE, TaskStatus.IN_PROGRESS]:
                continue

            # Check if all dependencies are completed
            deps_complete = all(
                dep_id in completed_subtask_ids for dep_id in subtask.dependencies
            )

            if deps_complete:
                return subtask

        return None

    def update_subtask_status(
        self, subtask_id: str, status: TaskStatus, assigned_to: Optional[str] = None
    ) -> bool:
        """
        Update the status of a subtask.

        Parameters
        ----------
        subtask_id : str
            ID of the subtask
        status : TaskStatus
            New status
        assigned_to : Optional[str]
            Agent assigned to the subtask

        Returns
        -------
        bool
            True if update successful
        """
        if subtask_id not in self.subtasks:
            logger.warning(f"Subtask {subtask_id} not found")
            return False

        subtask = self.subtasks[subtask_id]
        subtask.status = status
        if assigned_to:
            subtask.assigned_to = assigned_to

        self._save_state()
        return True

    def is_parent_complete(self, parent_task_id: str) -> bool:
        """
        Check if all subtasks of a parent are complete.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task

        Returns
        -------
        bool
            True if all subtasks are complete
        """
        subtasks = self.get_subtasks(parent_task_id)
        if not subtasks:
            return False

        return all(s.status == TaskStatus.DONE for s in subtasks)

    def get_completion_percentage(self, parent_task_id: str) -> float:
        """
        Get completion percentage for a parent task based on subtasks.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task

        Returns
        -------
        float
            Completion percentage (0-100)
        """
        subtasks = self.get_subtasks(parent_task_id)
        if not subtasks:
            return 0.0

        completed = sum(1 for s in subtasks if s.status == TaskStatus.DONE)
        return (completed / len(subtasks)) * 100

    def get_subtask_context(self, subtask_id: str) -> Dict[str, Any]:
        """
        Get full context for a subtask including parent and dependencies.

        Parameters
        ----------
        subtask_id : str
            ID of the subtask

        Returns
        -------
        Dict[str, Any]
            Context dictionary with parent info, shared conventions, and dependencies
        """
        if subtask_id not in self.subtasks:
            return {}

        subtask = self.subtasks[subtask_id]
        parent_id = subtask.parent_task_id

        # Get metadata
        metadata = self.metadata.get(parent_id, SubtaskMetadata())

        # Get dependency artifacts
        dependency_artifacts = {}
        for dep_id in subtask.dependencies:
            if dep_id in self.subtasks:
                dep = self.subtasks[dep_id]
                dependency_artifacts[dep_id] = {
                    "name": dep.name,
                    "provides": dep.provides,
                    "file_artifacts": dep.file_artifacts,
                    "status": dep.status.value,
                }

        return {
            "subtask": asdict(subtask),
            "parent_task_id": parent_id,
            "shared_conventions": metadata.shared_conventions,
            "dependency_artifacts": dependency_artifacts,
            "sibling_subtasks": [
                {"id": s.id, "name": s.name, "status": s.status.value}
                for s in self.get_subtasks(parent_id)
                if s.id != subtask_id
            ],
        }

    def has_subtasks(self, task_id: str) -> bool:
        """
        Check if a task has been decomposed into subtasks.

        Parameters
        ----------
        task_id : str
            ID of the task to check

        Returns
        -------
        bool
            True if task has subtasks
        """
        return task_id in self.parent_to_subtasks

    def remove_subtasks(self, parent_task_id: str) -> bool:
        """
        Remove all subtasks for a parent task.

        Parameters
        ----------
        parent_task_id : str
            ID of the parent task

        Returns
        -------
        bool
            True if removal successful
        """
        if parent_task_id not in self.parent_to_subtasks:
            return False

        # Remove all subtasks
        subtask_ids = self.parent_to_subtasks[parent_task_id]
        for sid in subtask_ids:
            if sid in self.subtasks:
                del self.subtasks[sid]

        del self.parent_to_subtasks[parent_task_id]

        if parent_task_id in self.metadata:
            del self.metadata[parent_task_id]

        self._save_state()
        return True

    def _save_state(self) -> None:
        """Persist subtask state to JSON file."""
        try:
            state = {
                "subtasks": {
                    sid: {
                        **asdict(subtask),
                        "status": subtask.status.value,
                        "priority": subtask.priority.value,
                        "created_at": subtask.created_at.isoformat(),
                    }
                    for sid, subtask in self.subtasks.items()
                },
                "parent_to_subtasks": self.parent_to_subtasks,
                "metadata": {
                    pid: {
                        "shared_conventions": meta.shared_conventions,
                        "decomposed_at": meta.decomposed_at.isoformat(),
                        "decomposed_by": meta.decomposed_by,
                    }
                    for pid, meta in self.metadata.items()
                },
            }

            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving subtask state: {e}")

    def _load_state(self) -> None:
        """Load subtask state from JSON file."""
        if not self.state_file.exists():
            logger.info("No existing subtask state file found")
            return

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)

            # Load subtasks
            for sid, data in state.get("subtasks", {}).items():
                # Migration: add dependency_types if not present
                if "dependency_types" not in data:
                    dependencies = data.get("dependencies", [])
                    if dependencies:
                        data["dependency_types"] = ["hard"] * len(dependencies)
                        logger.debug(
                            f"Migration: adding dependency_types for "
                            f"loaded subtask {sid}"
                        )
                    else:
                        data["dependency_types"] = []

                self.subtasks[sid] = Subtask(
                    **{
                        **data,
                        "status": TaskStatus(data["status"]),
                        "priority": Priority(data["priority"]),
                        "created_at": datetime.fromisoformat(data["created_at"]),
                    }
                )

            # Load parent relationships
            self.parent_to_subtasks = state.get("parent_to_subtasks", {})

            # Load metadata
            for pid, meta_data in state.get("metadata", {}).items():
                self.metadata[pid] = SubtaskMetadata(
                    shared_conventions=meta_data["shared_conventions"],
                    decomposed_at=datetime.fromisoformat(meta_data["decomposed_at"]),
                    decomposed_by=meta_data["decomposed_by"],
                )

            logger.info(f"Loaded {len(self.subtasks)} subtasks from state file")

        except Exception as e:
            logger.error(f"Error loading subtask state: {e}")
