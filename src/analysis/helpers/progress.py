"""
Progress reporting for Phase 2 analysis engine.

Provides progress event emission during long-running analyses so that:
- Users see "Analyzing task 45/247..." instead of frozen screen
- Cato UI can show progress bars (Phase 3 requirement)
- Analysis operations can report percentage complete

Usage
-----
```python
# Simple progress reporting
reporter = ProgressReporter(callback=my_callback)
await reporter.report_progress(
    operation="analyze_tasks",
    current=45,
    total=247,
    message="Analyzing task 45/247"
)

# Using context manager for automatic start/end reporting
async with reporter.operation("analyze_project", total=100) as progress:
    for i, task in enumerate(tasks):
        await analyze_task(task)
        await progress.increment(f"Analyzed {task.name}")

# Indeterminate progress (no total)
async with reporter.operation("loading_data", total=None) as progress:
    await progress.update(message="Loading decisions...")
    decisions = await load_decisions()
    await progress.update(message="Loading artifacts...")
    artifacts = await load_artifacts()
```
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import AsyncIterator, Optional, Protocol


@dataclass
class ProgressEvent:
    """
    Progress event emitted during long-running operations.

    Attributes
    ----------
    operation : str
        Name of the operation being performed
    current : int
        Current progress value (e.g., number of items processed)
    total : Optional[int]
        Total expected value (None for indeterminate progress)
    message : str
        Human-readable progress message
    timestamp : datetime
        When this progress event was emitted
    """

    operation: str
    current: int
    total: Optional[int]
    message: str
    timestamp: datetime

    def percentage(self) -> Optional[float]:
        """
        Calculate percentage complete.

        Returns
        -------
        Optional[float]
            Percentage (0-100), or None if total is not set
        """
        if self.total is None or self.total == 0:
            return None
        return (self.current / self.total) * 100

    def is_complete(self) -> bool:
        """
        Check if operation is complete.

        Returns
        -------
        bool
            True if current == total, False otherwise
        """
        if self.total is None:
            return False
        return self.current >= self.total


class ProgressCallback(Protocol):
    """Protocol for progress callbacks."""

    async def __call__(self, event: ProgressEvent) -> None:
        """
        Handle a progress event.

        Parameters
        ----------
        event : ProgressEvent
            The progress event to handle
        """
        ...


class ProgressContext:
    """
    Context for managing progress within an operation.

    Provides convenience methods for updating progress without
    repeating operation name and total.
    """

    def __init__(
        self,
        reporter: "ProgressReporter",
        operation: str,
        total: Optional[int],
    ):
        """
        Initialize progress context.

        Parameters
        ----------
        reporter : ProgressReporter
            The reporter to emit events through
        operation : str
            Name of the operation
        total : Optional[int]
            Total expected value (None for indeterminate)
        """
        self.reporter = reporter
        self.operation = operation
        self.total = total
        self._current = 0

    async def update(self, current: Optional[int] = None, message: str = "") -> None:
        """
        Update progress to a specific value.

        Parameters
        ----------
        current : Optional[int]
            New current value (uses internal counter if None)
        message : str
            Progress message
        """
        if current is not None:
            self._current = current

        await self.reporter.report_progress(
            operation=self.operation,
            current=self._current,
            total=self.total,
            message=message,
        )

    async def increment(self, message: str = "") -> None:
        """
        Increment progress by 1.

        Parameters
        ----------
        message : str
            Progress message
        """
        self._current += 1
        await self.reporter.report_progress(
            operation=self.operation,
            current=self._current,
            total=self.total,
            message=message,
        )

    async def complete(self, message: str = "Complete") -> None:
        """
        Mark operation as complete.

        Parameters
        ----------
        message : str
            Completion message
        """
        if self.total is not None:
            self._current = self.total

        await self.reporter.report_progress(
            operation=self.operation,
            current=self._current,
            total=self.total,
            message=message,
        )


class ProgressReporter:
    """
    Progress reporter for long-running analysis operations.

    Emits progress events that can be consumed by UI layers (like Cato)
    or logging systems to provide feedback during expensive LLM analyses.

    Parameters
    ----------
    callback : Optional[ProgressCallback]
        Async function to call with progress events. If None, progress
        reporting is a no-op (useful for testing).

    Examples
    --------
    ```python
    # Basic usage with callback
    async def progress_callback(event: ProgressEvent):
        print(f"{event.operation}: {event.current}/{event.total}")

    reporter = ProgressReporter(callback=progress_callback)

    # Manual progress reporting
    await reporter.report_progress(
        operation="analyze_tasks",
        current=10,
        total=100,
        message="Analyzing task 10/100"
    )

    # Context manager for automatic start/end
    async with reporter.operation("process_batch", total=50) as progress:
        for i in range(50):
            await process_item(i)
            await progress.increment(f"Processed item {i+1}")
    ```
    """

    def __init__(self, callback: Optional[ProgressCallback] = None):
        """
        Initialize progress reporter.

        Parameters
        ----------
        callback : Optional[ProgressCallback]
            Function to call with progress events
        """
        self.callback = callback

    async def report_progress(
        self,
        operation: str,
        current: int,
        total: Optional[int],
        message: str = "",
    ) -> None:
        """
        Report progress for an operation.

        Parameters
        ----------
        operation : str
            Name of the operation
        current : int
            Current progress value
        total : Optional[int]
            Total expected value (None for indeterminate)
        message : str
            Human-readable progress message

        Examples
        --------
        ```python
        await reporter.report_progress(
            operation="load_decisions",
            current=500,
            total=1000,
            message="Loaded 500/1000 decisions"
        )
        ```
        """
        if self.callback is None:
            return

        event = ProgressEvent(
            operation=operation,
            current=current,
            total=total,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )

        await self.callback(event)

    @asynccontextmanager
    async def operation(
        self, operation: str, total: Optional[int]
    ) -> AsyncIterator[ProgressContext]:
        """
        Context manager for tracking progress of an operation.

        Automatically reports start (0/total) and completion (total/total)
        events. Provides a context object for reporting intermediate progress.

        Parameters
        ----------
        operation : str
            Name of the operation
        total : Optional[int]
            Total expected value (None for indeterminate progress)

        Yields
        ------
        ProgressContext
            Context for updating progress

        Examples
        --------
        ```python
        # Determinate progress
        async with reporter.operation("analyze_tasks", total=100) as progress:
            for i in range(100):
                await analyze_task(i)
                await progress.increment(f"Analyzed task {i+1}")

        # Indeterminate progress
        async with reporter.operation("loading", total=None) as progress:
            await progress.update(message="Loading decisions...")
            decisions = await load_decisions()
            await progress.update(message="Loading artifacts...")
            artifacts = await load_artifacts()
        ```
        """
        context = ProgressContext(self, operation, total)

        # Report start
        await self.report_progress(
            operation=operation,
            current=0,
            total=total,
            message="Starting...",
        )

        try:
            yield context
        finally:
            # Always report completion, even if exception occurred
            await context.complete()
