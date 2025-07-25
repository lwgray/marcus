"""
Event loop utilities for handling asyncio locks across different contexts.

This module provides utilities to ensure asyncio locks work correctly
across different event loop contexts, particularly important for HTTP
transport where each request might have its own event loop.
"""

import asyncio
import threading
from weakref import WeakKeyDictionary


class EventLoopLockManager:
    """
    Manages asyncio locks across different event loops.

    This class ensures that locks are created in the correct event loop
    context, preventing "bound to a different event loop" errors.
    """

    def __init__(self) -> None:
        """Initialize the lock manager."""
        # Use weak references to avoid keeping event loops alive
        self._locks: WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
            WeakKeyDictionary()
        )
        self._thread_lock = threading.Lock()

    def get_lock(self) -> asyncio.Lock:
        """
        Get or create a lock for the current event loop.

        Returns
        -------
        asyncio.Lock
            A lock bound to the current event loop
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new lock that will bind when used
            return asyncio.Lock()

        with self._thread_lock:
            if loop not in self._locks:
                self._locks[loop] = asyncio.Lock()
            return self._locks[loop]

    def clear(self) -> None:
        """Clear all locks (useful for testing)."""
        with self._thread_lock:
            self._locks.clear()


class ThreadLocalLockManager:
    """
    Thread-local lock manager for simpler cases.

    Each thread gets its own lock, avoiding event loop binding issues.
    """

    def __init__(self) -> None:
        """Initialize the thread-local storage."""
        self._local = threading.local()

    def get_lock(self) -> asyncio.Lock:
        """
        Get or create a lock for the current thread.

        Returns
        -------
        asyncio.Lock
            A lock for the current thread
        """
        if not hasattr(self._local, "lock"):
            self._local.lock = asyncio.Lock()
        lock: asyncio.Lock = self._local.lock
        return lock


def create_event_loop_safe_lock() -> asyncio.Lock:
    """
    Create a lock that's safe to use across event loops.

    This is a simple factory function that creates a new lock
    in the current event loop context.

    Returns
    -------
    asyncio.Lock
        A new lock bound to the current event loop
    """
    return asyncio.Lock()
