"""
General persistence layer for Marcus systems

Provides a unified storage interface for Events, Context, Memory, and other
systems that need persistent data. Supports multiple backends starting with
file-based storage and ready for database backends.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from src.core.context import Decision
from src.core.event_loop_utils import EventLoopLockManager
from src.core.events import Event

logger = logging.getLogger(__name__)


class PersistenceBackend:
    """Base class for persistence backends"""

    async def store(self, collection: str, key: str, data: Dict[str, Any]) -> None:
        """Store data in a collection"""
        raise NotImplementedError

    async def retrieve(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from a collection"""
        raise NotImplementedError

    async def query(
        self, collection: str, filter_func: Optional[Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query data from a collection with optional filtering"""
        raise NotImplementedError

    async def delete(self, collection: str, key: str) -> None:
        """Delete data from a collection"""
        raise NotImplementedError

    async def clear_old(self, collection: str, days: int) -> int:
        """Clear data older than specified days"""
        raise NotImplementedError


class FilePersistence(PersistenceBackend):
    """File-based persistence using JSON files"""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        """Initialize file persistence"""
        if storage_dir is None:
            # Use absolute path to ensure it works regardless of working directory
            marcus_root = Path(__file__).parent.parent.parent
            storage_dir = marcus_root / "data" / "marcus_state"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._lock_managers: Dict[str, EventLoopLockManager] = {}

    def _get_lock(self, collection: str) -> asyncio.Lock:
        """Get or create a lock for a collection, ensuring correct event loop binding"""
        if collection not in self._lock_managers:
            self._lock_managers[collection] = EventLoopLockManager()
        return self._lock_managers[collection].get_lock()

    def _get_collection_file(self, collection: str) -> Path:
        """Get the file path for a collection"""
        return self.storage_dir / f"{collection}.json"

    async def store(self, collection: str, key: str, data: Dict[str, Any]) -> None:
        """Store data in a collection"""
        lock = self._get_lock(collection)
        async with lock:
            # Load existing data
            file_path = self._get_collection_file(collection)
            existing_data: Dict[str, Any] = {}

            if file_path.exists():
                try:
                    async with aiofiles.open(file_path, "r") as f:
                        content = await f.read()
                        existing_data = json.loads(content) if content else {}
                except Exception as e:
                    logger.error(f"Error loading {collection}: {e}")

            # Update with new data
            existing_data[key] = {**data, "_stored_at": datetime.now().isoformat()}

            # Write back atomically
            temp_file = file_path.with_suffix(".tmp")
            try:
                async with aiofiles.open(temp_file, "w") as f:
                    await f.write(json.dumps(existing_data, indent=2, default=str))
                temp_file.replace(file_path)
            except Exception as e:
                logger.error(f"Error writing {collection}: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise

    async def retrieve(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from a collection"""
        lock = self._get_lock(collection)
        async with lock:
            file_path = self._get_collection_file(collection)

            if not file_path.exists():
                return None

            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content) if content else {}
                    return data.get(key)
            except Exception as e:
                logger.error(f"Error reading {collection}: {e}")
                return None

    async def query(
        self, collection: str, filter_func: Optional[Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query data from a collection"""
        lock = self._get_lock(collection)
        async with lock:
            file_path = self._get_collection_file(collection)

            if not file_path.exists():
                return []

            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content) if content else {}

                # Convert to list of items
                items = [{"_key": k, **v} for k, v in data.items()]

                # Apply filter if provided
                if filter_func:
                    items = [item for item in items if filter_func(item)]

                # Sort by stored time (newest first) and limit
                items.sort(key=lambda x: x.get("_stored_at", ""), reverse=True)

                return items[:limit]

            except Exception as e:
                logger.error(f"Error querying {collection}: {e}")
                return []

    async def delete(self, collection: str, key: str) -> None:
        """Delete data from a collection"""
        lock = self._get_lock(collection)
        async with lock:
            file_path = self._get_collection_file(collection)

            if not file_path.exists():
                return

            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content) if content else {}

                if key in data:
                    del data[key]

                    # Write back
                    temp_file = file_path.with_suffix(".tmp")
                    async with aiofiles.open(temp_file, "w") as f:
                        await f.write(json.dumps(data, indent=2, default=str))
                    temp_file.replace(file_path)

            except Exception as e:
                logger.error(f"Error deleting from {collection}: {e}")

    async def clear_old(self, collection: str, days: int) -> int:
        """Clear data older than specified days"""
        lock = self._get_lock(collection)
        async with lock:
            file_path = self._get_collection_file(collection)

            if not file_path.exists():
                return 0

            cutoff = datetime.now() - timedelta(days=days)
            removed_count = 0

            try:
                async with aiofiles.open(file_path, "r") as f:
                    content = await f.read()
                    data = json.loads(content) if content else {}

                # Filter out old entries
                new_data = {}
                for key, value in data.items():
                    stored_at_str = value.get("_stored_at")
                    if stored_at_str:
                        stored_at = datetime.fromisoformat(stored_at_str)
                        if stored_at >= cutoff:
                            new_data[key] = value
                        else:
                            removed_count += 1
                    else:
                        # Keep entries without timestamp
                        new_data[key] = value

                # Write back if anything was removed
                if removed_count > 0:
                    temp_file = file_path.with_suffix(".tmp")
                    async with aiofiles.open(temp_file, "w") as f:
                        await f.write(json.dumps(new_data, indent=2, default=str))
                    temp_file.replace(file_path)

                return removed_count

            except Exception as e:
                logger.error(f"Error clearing old data from {collection}: {e}")
                return 0


class SQLitePersistence(PersistenceBackend):
    """SQLite-based persistence for better performance and queries"""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize SQLite persistence"""
        self.db_path = db_path or Path("./data/marcus_state.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS persistence (
                    collection TEXT NOT NULL,
                    key TEXT NOT NULL,
                    data TEXT NOT NULL,
                    stored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (collection, key)
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_stored_at
                ON persistence(stored_at)
            """
            )
            conn.commit()

    async def store(self, collection: str, key: str, data: Dict[str, Any]) -> None:
        """Store data in SQLite"""

        def _store() -> None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO persistence (collection, key, data)
                    VALUES (?, ?, ?)
                """,
                    (collection, key, json.dumps(data, default=str)),
                )
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _store)

    async def retrieve(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from SQLite"""

        def _retrieve() -> Optional[Dict[str, Any]]:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT data FROM persistence
                    WHERE collection = ? AND key = ?
                """,
                    (collection, key),
                )
                row = cursor.fetchone()
                return json.loads(row[0]) if row else None

        return await asyncio.get_event_loop().run_in_executor(None, _retrieve)

    async def query(
        self, collection: str, filter_func: Optional[Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query data from SQLite"""

        def _query() -> List[Dict[str, Any]]:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT key, data FROM persistence
                    WHERE collection = ?
                    ORDER BY stored_at DESC
                    LIMIT ?
                """,
                    (collection, limit * 2),
                )  # Get extra for filtering

                items = []
                for row in cursor:
                    item = json.loads(row[1])
                    item["_key"] = row[0]

                    if not filter_func or filter_func(item):
                        items.append(item)
                        if len(items) >= limit:
                            break

                return items

        return await asyncio.get_event_loop().run_in_executor(None, _query)

    async def delete(self, collection: str, key: str) -> None:
        """Delete data from SQLite"""

        def _delete() -> None:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM persistence
                    WHERE collection = ? AND key = ?
                """,
                    (collection, key),
                )
                conn.commit()

        await asyncio.get_event_loop().run_in_executor(None, _delete)

    async def clear_old(self, collection: str, days: int) -> int:
        """Clear old data from SQLite"""

        def _clear() -> int:
            cutoff = datetime.now() - timedelta(days=days)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM persistence
                    WHERE collection = ? AND stored_at < ?
                """,
                    (collection, cutoff.isoformat()),
                )
                conn.commit()
                return cursor.rowcount

        return await asyncio.get_event_loop().run_in_executor(None, _clear)


class Persistence:
    """
    Main persistence interface for Marcus systems.

    Provides a unified way to store and retrieve data for Events,
    Context, Memory, and other systems.
    """

    def __init__(self, backend: Optional[PersistenceBackend] = None) -> None:
        """
        Initialize persistence layer.

        Args:
            backend: Storage backend to use. Defaults to FilePersistence.
        """
        self.backend = backend or FilePersistence()

    # Event-specific methods
    async def store_event(self, event: Event) -> None:
        """Store an event"""
        await self.backend.store("events", event.event_id, event.to_dict())

    async def get_events(
        self,
        event_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Retrieve events with optional filtering"""

        def filter_func(item: Dict[str, Any]) -> bool:
            if event_type and item.get("event_type") != event_type:
                return False
            if source and item.get("source") != source:
                return False
            return True

        items = await self.backend.query("events", filter_func, limit)

        # Convert back to Event objects
        events = []
        for item in items:
            try:
                # Remove internal fields
                item.pop("_key", None)
                item.pop("_stored_at", None)

                # Reconstruct Event
                event = Event(
                    event_id=item["event_id"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    event_type=item["event_type"],
                    source=item["source"],
                    data=item["data"],
                    metadata=item.get("metadata"),
                )
                events.append(event)
            except Exception as e:
                logger.error(f"Error reconstructing event: {e}")

        return events

    # Context-specific methods
    async def store_decision(self, decision: Decision) -> None:
        """Store an architectural decision"""
        await self.backend.store("decisions", decision.decision_id, decision.to_dict())

    async def get_decisions(
        self,
        task_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Decision]:
        """Retrieve decisions with optional filtering"""

        def filter_func(item: Dict[str, Any]) -> bool:
            if task_id and item.get("task_id") != task_id:
                return False
            if agent_id and item.get("agent_id") != agent_id:
                return False
            return True

        items = await self.backend.query("decisions", filter_func, limit)

        # Convert back to Decision objects
        decisions = []
        for item in items:
            try:
                decision = Decision(
                    decision_id=item["decision_id"],
                    task_id=item["task_id"],
                    agent_id=item["agent_id"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    what=item["what"],
                    why=item["why"],
                    impact=item["impact"],
                )
                decisions.append(decision)
            except Exception as e:
                logger.error(f"Error reconstructing decision: {e}")

        return decisions

    # General methods
    async def store(self, collection: str, key: str, data: Dict[str, Any]) -> None:
        """Store arbitrary data in a collection"""
        await self.backend.store(collection, key, data)

    async def retrieve(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve arbitrary data from a collection"""
        return await self.backend.retrieve(collection, key)

    async def query(
        self, collection: str, filter_func: Optional[Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query a collection"""
        return await self.backend.query(collection, filter_func, limit)

    async def delete(self, collection: str, key: str) -> None:
        """Delete data from a collection"""
        await self.backend.delete(collection, key)

    async def cleanup(self, days: int = 30) -> Dict[str, int]:
        """Clean up old data from all collections"""
        collections = ["events", "decisions", "implementations", "patterns"]
        results = {}

        for collection in collections:
            count = await self.backend.clear_old(collection, days)
            if count > 0:
                results[collection] = count
                logger.info(f"Cleaned up {count} old items from {collection}")

        return results


class MemoryPersistence(PersistenceBackend):
    """In-memory persistence for testing and temporary storage"""

    def __init__(self) -> None:
        """Initialize memory persistence"""
        self.data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock_managers: Dict[str, EventLoopLockManager] = {}

    def _get_lock(self, collection: str) -> asyncio.Lock:
        """Get or create a lock for a collection, ensuring correct event loop binding"""
        if collection not in self._lock_managers:
            self._lock_managers[collection] = EventLoopLockManager()
        return self._lock_managers[collection].get_lock()

    async def store(self, collection: str, key: str, data: Dict[str, Any]) -> None:
        """Store data in memory"""
        lock = self._get_lock(collection)
        async with lock:
            if collection not in self.data:
                self.data[collection] = {}

            self.data[collection][key] = {
                **data,
                "_stored_at": datetime.now().isoformat(),
            }

    async def retrieve(self, collection: str, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from memory"""
        lock = self._get_lock(collection)
        async with lock:
            if collection not in self.data:
                return None

            return self.data[collection].get(key)

    async def query(
        self, collection: str, filter_func: Optional[Any] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query data from memory"""
        lock = self._get_lock(collection)
        async with lock:
            if collection not in self.data:
                return []

            # Convert to list of items
            items = [{"_key": k, **v} for k, v in self.data[collection].items()]

            # Apply filter if provided
            if filter_func:
                items = [item for item in items if filter_func(item)]

            # Sort by stored time (newest first) and limit
            items.sort(key=lambda x: x.get("_stored_at", ""), reverse=True)

            return items[:limit]

    async def delete(self, collection: str, key: str) -> None:
        """Delete data from memory"""
        lock = self._get_lock(collection)
        async with lock:
            if collection in self.data and key in self.data[collection]:
                del self.data[collection][key]

    async def clear_old(self, collection: str, days: int) -> int:
        """Clear old data from memory"""
        lock = self._get_lock(collection)
        async with lock:
            if collection not in self.data:
                return 0

            cutoff = datetime.now() - timedelta(days=days)
            removed_count = 0

            # Create new dict with non-old entries
            new_data = {}
            for key, value in self.data[collection].items():
                stored_at_str = value.get("_stored_at")
                if stored_at_str:
                    stored_at = datetime.fromisoformat(stored_at_str)
                    if stored_at >= cutoff:
                        new_data[key] = value
                    else:
                        removed_count += 1
                else:
                    # Keep entries without timestamp
                    new_data[key] = value

            self.data[collection] = new_data
            return removed_count
