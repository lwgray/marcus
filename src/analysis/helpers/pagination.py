"""
Pagination helpers for Phase 2 analysis engine.

Provides async generators that automatically handle pagination when iterating
over large collections (decisions, artifacts, tasks) to work with Phase 1's
10,000 item limit gracefully.

Usage
-----
```python
# Iterate over all decisions without worrying about pagination
async for decision in iter_all_decisions(project_id, persistence):
    await analyze_decision(decision)

# Custom batch size for memory optimization
async for artifact in iter_all_artifacts(project_id, persistence, batch_size=50):
    await process_artifact(artifact)
```
"""

from typing import AsyncIterator

from src.analysis.aggregator import ProjectHistoryAggregator, TaskHistory
from src.core.project_history import (
    ArtifactMetadata,
    Decision,
    ProjectHistoryPersistence,
)


async def iter_all_decisions(
    project_id: str,
    persistence: ProjectHistoryPersistence,
    batch_size: int = 100,
) -> AsyncIterator[Decision]:
    """
    Iterate over all decisions for a project with automatic pagination.

    Handles Phase 1's pagination requirements transparently. Loads decisions
    in batches to avoid loading all data into memory at once.

    Parameters
    ----------
    project_id : str
        Project identifier
    persistence : ProjectHistoryPersistence
        Persistence layer for loading decisions
    batch_size : int, optional
        Number of decisions to load per batch (default: 100)

    Yields
    ------
    Decision
        Each decision in the project, one at a time

    Examples
    --------
    ```python
    persistence = ProjectHistoryPersistence()

    # Analyze all decisions
    async for decision in iter_all_decisions("proj-123", persistence):
        print(f"Decision: {decision.what}")

    # Use smaller batches for memory-constrained environments
    async for decision in iter_all_decisions("proj-123", persistence, batch_size=50):
        await expensive_analysis(decision)
    ```
    """
    offset = 0

    while True:
        # Load next batch
        batch = await persistence.load_decisions(
            project_id, limit=batch_size, offset=offset
        )

        # Stop if no more data
        if not batch:
            break

        # Yield each decision in batch
        for decision in batch:
            yield decision

        # Move to next page
        offset += batch_size


async def iter_all_artifacts(
    project_id: str,
    persistence: ProjectHistoryPersistence,
    batch_size: int = 100,
) -> AsyncIterator[ArtifactMetadata]:
    """
    Iterate over all artifacts for a project with automatic pagination.

    Handles Phase 1's pagination requirements transparently. Loads artifacts
    in batches to avoid loading all data into memory at once.

    Parameters
    ----------
    project_id : str
        Project identifier
    persistence : ProjectHistoryPersistence
        Persistence layer for loading artifacts
    batch_size : int, optional
        Number of artifacts to load per batch (default: 100)

    Yields
    ------
    ArtifactMetadata
        Each artifact in the project, one at a time

    Examples
    --------
    ```python
    persistence = ProjectHistoryPersistence()

    # Process all artifacts
    async for artifact in iter_all_artifacts("proj-123", persistence):
        print(f"Artifact: {artifact.filename}")
    ```
    """
    offset = 0

    while True:
        # Load next batch
        batch = await persistence.load_artifacts(
            project_id, limit=batch_size, offset=offset
        )

        # Stop if no more data
        if not batch:
            break

        # Yield each artifact in batch
        for artifact in batch:
            yield artifact

        # Move to next page
        offset += batch_size


async def iter_all_tasks(
    project_id: str,
    aggregator: ProjectHistoryAggregator,
) -> AsyncIterator[TaskHistory]:
    """
    Iterate over all tasks for a project.

    Tasks are already aggregated from paginated decisions and artifacts,
    so no additional pagination is needed. This generator provides a
    consistent interface with the other iterators.

    Parameters
    ----------
    project_id : str
        Project identifier
    aggregator : ProjectHistoryAggregator
        Aggregator for loading project history

    Yields
    ------
    TaskHistory
        Each task in the project, one at a time

    Examples
    --------
    ```python
    aggregator = ProjectHistoryAggregator()

    # Analyze all tasks
    async for task in iter_all_tasks("proj-123", aggregator):
        print(f"Task: {task.name}")
    ```

    Notes
    -----
    Tasks don't require pagination because they're constructed from
    already-paginated decisions and artifacts. The aggregator handles
    pagination at the decision/artifact level.
    """
    # Load project history (decisions and artifacts are already paginated)
    history = await aggregator.aggregate_project(project_id)

    # Yield each task
    for task in history.tasks:
        yield task


async def iter_tasks_with_pagination(
    project_id: str,
    aggregator: ProjectHistoryAggregator,
    decision_batch_size: int = 100,
    artifact_batch_size: int = 100,
) -> AsyncIterator[TaskHistory]:
    """
    Iterate over tasks with explicit control over decision/artifact pagination.

    Useful when you need fine-grained control over memory usage during
    task aggregation.

    Parameters
    ----------
    project_id : str
        Project identifier
    aggregator : ProjectHistoryAggregator
        Aggregator for loading project history
    decision_batch_size : int, optional
        Batch size for loading decisions (default: 100)
    artifact_batch_size : int, optional
        Batch size for loading artifacts (default: 100)

    Yields
    ------
    TaskHistory
        Each task in the project, one at a time

    Examples
    --------
    ```python
    aggregator = ProjectHistoryAggregator()

    # Use smaller batches for memory optimization
    async for task in iter_tasks_with_pagination(
        "proj-123", aggregator, decision_batch_size=50, artifact_batch_size=50
    ):
        await analyze_task(task)
    ```
    """
    # Load project history with custom pagination
    history = await aggregator.aggregate_project(
        project_id,
        decision_limit=decision_batch_size,
        artifact_limit=artifact_batch_size,
    )

    # Yield each task
    for task in history.tasks:
        yield task
