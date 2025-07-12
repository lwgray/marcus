"""
Assignment persistence layer for Marcus.

This module provides persistent storage for task assignments to prevent
duplicate assignments across Marcus restarts and multiple instances.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles

logger = logging.getLogger(__name__)


class AssignmentPersistence:
    """Handles persistent storage of task assignments."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize the assignment persistence layer.

        Args:
            storage_dir: Directory for storing assignment data.
                        Defaults to ./data/assignments/
        """
        if storage_dir is None:
            # Use absolute path to ensure it works regardless of working directory
            marcus_root = Path(__file__).parent.parent.parent
            storage_dir = marcus_root / "data" / "assignments"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.assignments_file = self.storage_dir / "assignments.json"
        self.lock_file = self.storage_dir / ".assignments.lock"

        # In-memory cache
        self._assignments_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def save_assignment(
        self, worker_id: str, task_id: str, task_data: Dict[str, Any]
    ) -> None:
        """
        Save a task assignment persistently.

        Args:
            worker_id: ID of the worker assigned to the task
            task_id: ID of the task being assigned
            task_data: Additional task information to store
        """
        async with self._lock:
            # Update cache
            self._assignments_cache[worker_id] = {
                "task_id": task_id,
                "assigned_at": datetime.now().isoformat(),
                "task_data": task_data,
            }

            # Persist to disk
            await self._write_assignments()

    async def remove_assignment(self, worker_id: str) -> None:
        """
        Remove a task assignment (e.g., when task is completed).

        Args:
            worker_id: ID of the worker to remove assignment for
        """
        async with self._lock:
            if worker_id in self._assignments_cache:
                del self._assignments_cache[worker_id]
                await self._write_assignments()

    async def get_assignment(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current assignment for a worker.

        Args:
            worker_id: ID of the worker

        Returns:
            Assignment data or None if no assignment exists
        """
        async with self._lock:
            return self._assignments_cache.get(worker_id)

    async def get_all_assigned_task_ids(self) -> set:
        """
        Get all currently assigned task IDs.

        Returns:
            Set of task IDs that are currently assigned
        """
        async with self._lock:
            return {
                assignment["task_id"] for assignment in self._assignments_cache.values()
            }

    async def load_assignments(self) -> Dict[str, Dict[str, Any]]:
        """
        Load assignments from persistent storage.

        Returns:
            Dictionary of worker_id -> assignment data
        """
        async with self._lock:
            if not self.assignments_file.exists():
                return {}

            try:
                async with aiofiles.open(self.assignments_file, "r") as f:
                    content = await f.read()
                    self._assignments_cache = json.loads(content) if content else {}
                    return self._assignments_cache
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading assignments: {e}")
                # Return empty dict on error to allow recovery
                return {}

    async def _write_assignments(self) -> None:
        """Write assignments to disk atomically."""
        temp_file = self.assignments_file.with_suffix(".tmp")

        try:
            async with aiofiles.open(temp_file, "w") as f:
                await f.write(json.dumps(self._assignments_cache, indent=2))

            # Atomic rename
            temp_file.replace(self.assignments_file)

        except Exception as e:
            logger.error(f"Error writing assignments: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    async def is_task_assigned(self, task_id: str) -> bool:
        """
        Check if a task is currently assigned to any worker.

        Args:
            task_id: ID of the task to check

        Returns:
            True if the task is assigned, False otherwise
        """
        async with self._lock:
            for assignment in self._assignments_cache.values():
                if assignment["task_id"] == task_id:
                    return True
            return False

    async def get_worker_for_task(self, task_id: str) -> Optional[str]:
        """
        Get the worker ID assigned to a specific task.

        Args:
            task_id: ID of the task

        Returns:
            Worker ID or None if task is not assigned
        """
        async with self._lock:
            for worker_id, assignment in self._assignments_cache.items():
                if assignment["task_id"] == task_id:
                    return worker_id
            return None
