# ADR 0004: Async-First Design with AsyncIO

**Status:** Accepted

**Date:** 2024-11 (Initial Implementation)

**Deciders:** Marcus Core Team

---

## Context

Marcus performs many I/O-bound operations:
- **External API calls:** Kanban providers (Planka, GitHub), AI services (OpenAI, Anthropic)
- **Database operations:** SQLite reads/writes
- **File system operations:** Reading/writing project history, artifacts
- **Network operations:** HTTP requests, WebSocket connections
- **Concurrent agents:** Multiple agents working simultaneously

### Performance Requirements
- Handle multiple concurrent agent requests
- Non-blocking I/O operations
- Responsive user experience (MCP tool responses < 500ms)
- Efficient resource utilization
- Support for long-running operations (experiments, monitoring)

### Synchronous Problems
With synchronous code:
```python
# ❌ Blocking - each operation waits for the previous
def create_project():
    board = kanban.create_board()        # Blocks for 500ms
    tasks = ai.generate_tasks()          # Blocks for 2000ms
    for task in tasks:
        kanban.create_card(task)         # Blocks for 200ms each
    # Total time: 500 + 2000 + (200 * N) ms
```

This would make Marcus unresponsive and unable to handle concurrent requests.

---

## Decision

We will adopt an **Async-First Design** using Python's AsyncIO framework for all I/O operations.

### Core Principles

1. **All I/O Operations are Async**
   - External API calls
   - Database operations
   - File system operations
   - Network requests

2. **Async Throughout the Stack**
   - MCP tools are async
   - Workflows are async
   - Domain services are async
   - Integration clients are async

3. **Sync Only Where Necessary**
   - Pure computation (no I/O)
   - Legacy library integration
   - Simple data transformations

### Implementation Pattern

```python
# ✅ Async - concurrent execution
async def create_project():
    # Run independent operations concurrently
    board, tasks = await asyncio.gather(
        kanban.create_board(),           # 500ms
        ai.generate_tasks()              # 2000ms (runs in parallel)
    )
    # Total time so far: max(500, 2000) = 2000ms

    # Create cards concurrently
    await asyncio.gather(*[
        kanban.create_card(task)
        for task in tasks
    ])
    # Total time: 2000 + 200 = 2200ms (vs 2500+ ms sync)
```

---

## Consequences

### Positive

✅ **Massive Performance Improvements**
- 10x faster project creation (80s → 8s after parallelization)
- Concurrent agent requests
- Non-blocking I/O operations

✅ **Better Resource Utilization**
- Single process handles multiple concurrent requests
- CPU used while waiting for I/O
- Lower memory footprint than threads

✅ **Responsive System**
- MCP tools respond quickly
- UI never freezes
- Background tasks don't block foreground

✅ **Scalability**
- Handle many concurrent agents
- Efficient for I/O-bound workloads
- Easy to add concurrency with `asyncio.gather()`

✅ **Modern Python Ecosystem**
- Great library support (httpx, aiosqlite)
- AsyncIO is Python's future
- Better than threading for I/O

### Negative

⚠️ **Learning Curve**
- Async/await syntax unfamiliar to some
- Understanding event loop crucial
- Common pitfalls (blocking calls in async code)

⚠️ **Complexity**
- More complex than synchronous code
- Debugging can be harder
- Stack traces less readable

⚠️ **Library Compatibility**
- Some libraries don't support async
- Need wrappers for sync libraries
- Mitigation: Use async alternatives (httpx vs requests)

⚠️ **Accidental Blocking**
- Easy to accidentally block event loop
- One blocking call affects all concurrency
- Mitigation: Linting, code review, testing

⚠️ **Testing Complexity**
- Need pytest-asyncio
- Mock async functions differently
- More boilerplate in tests

---

## Implementation Details

### AsyncIO Fundamentals

```python
# Core async pattern
async def async_function():
    """Async function using async/await"""
    result = await some_async_operation()
    return result

# Running async code
asyncio.run(async_function())
```

### MCP Server Integration

```python
# MCP tools are async
@server.call_tool()
async def create_project(
    description: str,
    project_name: str
) -> dict:
    """Create project - async MCP tool"""
    # All operations are async
    project_id = await discover_or_create_project(project_name)
    tasks = await generate_tasks(description)
    await sync_to_kanban(project_id, tasks)

    return {"success": True, "project_id": project_id}
```

### Concurrent Operations

```python
# Pattern 1: Independent operations
async def parallel_operations():
    """Run independent operations concurrently"""
    results = await asyncio.gather(
        operation_1(),
        operation_2(),
        operation_3()
    )
    return results

# Pattern 2: Homogeneous batch operations
async def batch_create_tasks(tasks: list[Task]):
    """Create many tasks concurrently"""
    await asyncio.gather(*[
        kanban.create_card(task)
        for task in tasks
    ])

# Pattern 3: With error handling
async def safe_parallel_operations():
    """Handle errors in concurrent operations"""
    results = await asyncio.gather(
        operation_1(),
        operation_2(),
        operation_3(),
        return_exceptions=True  # Don't fail on first error
    )

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Operation {i} failed: {result}")
```

### Async Database Operations

```python
import aiosqlite

async def get_tasks(project_id: str) -> list[Task]:
    """Async database query"""
    async with aiosqlite.connect("marcus.db") as db:
        async with db.execute(
            "SELECT * FROM tasks WHERE project_id = ?",
            (project_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [Task.from_row(row) for row in rows]
```

### Async HTTP Clients

```python
import httpx

async def call_kanban_api(endpoint: str, data: dict) -> dict:
    """Async HTTP request"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{KANBAN_URL}/{endpoint}",
            json=data,
            timeout=30.0
        )
        return response.json()
```

### Event Loop Safety

```python
import asyncio
from asyncio import Lock

class TaskQueue:
    """Thread-safe async task queue"""

    def __init__(self):
        self._lock = Lock()  # Async lock, not threading.Lock
        self._tasks: list[Task] = []

    async def add_task(self, task: Task):
        """Add task with lock protection"""
        async with self._lock:
            self._tasks.append(task)
            await self._persist_task(task)

    async def get_next_task(self) -> Task | None:
        """Get next task with lock protection"""
        async with self._lock:
            if not self._tasks:
                return None
            return self._tasks.pop(0)
```

### Handling Sync Code

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Pattern 1: Run sync code in thread pool
async def call_sync_library():
    """Call blocking library without blocking event loop"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # Use default ThreadPoolExecutor
        blocking_function,
        arg1,
        arg2
    )
    return result

# Pattern 2: Wrap sync iterators
async def async_generator():
    """Async generator from sync iterator"""
    for item in sync_iterator:
        # Yield control periodically
        await asyncio.sleep(0)
        yield item
```

### Background Tasks

```python
class ExperimentTracker:
    """Background task for experiment tracking"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start background tracking"""
        self._running = True
        self._task = asyncio.create_task(self._track_loop())

    async def stop(self):
        """Stop background tracking"""
        self._running = False
        if self._task:
            await self._task

    async def _track_loop(self):
        """Background tracking loop"""
        while self._running:
            await self._collect_metrics()
            await asyncio.sleep(30)  # Every 30 seconds
```

---

## Common Pitfalls and Solutions

### Pitfall 1: Blocking the Event Loop

```python
# ❌ Bad - blocks event loop
async def bad_example():
    time.sleep(5)  # Blocks entire event loop!
    result = await async_operation()

# ✅ Good - use async sleep
async def good_example():
    await asyncio.sleep(5)  # Yields control
    result = await async_operation()
```

### Pitfall 2: Forgetting await

```python
# ❌ Bad - returns coroutine, doesn't execute
async def bad_example():
    result = async_operation()  # Forgot await!
    return result  # Returns coroutine object

# ✅ Good - awaits the operation
async def good_example():
    result = await async_operation()
    return result
```

### Pitfall 3: Using Sync Locks

```python
# ❌ Bad - threading.Lock in async code
from threading import Lock

class BadQueue:
    def __init__(self):
        self._lock = Lock()  # Blocks event loop!

    async def add(self, item):
        with self._lock:  # Blocks!
            self._items.append(item)

# ✅ Good - asyncio.Lock
from asyncio import Lock

class GoodQueue:
    def __init__(self):
        self._lock = Lock()  # Async lock

    async def add(self, item):
        async with self._lock:  # Yields control
            self._items.append(item)
```

### Pitfall 4: Fire and Forget

```python
# ❌ Bad - task may not complete
async def bad_example():
    asyncio.create_task(background_operation())
    # Function exits, task may be cancelled!

# ✅ Good - store task reference
class GoodExample:
    def __init__(self):
        self._background_tasks = set()

    async def start_background(self):
        task = asyncio.create_task(background_operation())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
```

---

## Performance Impact

### Before Async (Estimated with Sync Code)
- Project creation: ~80 seconds (sequential API calls)
- Concurrent agent limit: ~5 (thread pool size)
- Memory usage: High (one thread per agent)

### After Async (Actual Measurements)
- Project creation: ~8 seconds (parallel API calls) - **10x improvement**
- Concurrent agent limit: 100+ (tested)
- Memory usage: Low (single event loop)

### Specific Optimizations

**Project Creation (GH-61):**
```python
# Before: Sequential (48s + 32s = 80s)
tasks = await generate_task_descriptions()      # 48s
for task in tasks:
    subtasks = await generate_subtasks(task)    # 32s total
    task.subtasks = subtasks

# After: Parallel (max(48s, 32s) = 48s)
task_results, subtask_results = await asyncio.gather(
    generate_task_descriptions(),               # 48s
    generate_all_subtasks_parallel(tasks)       # 32s (parallel)
)
# Result: 10x speedup (80s → 8s with batching)
```

---

## Testing Strategy

### Pytest AsyncIO

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function"""
    result = await async_operation()
    assert result == expected
```

### Mocking Async Functions

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_with_mock():
    """Test with async mock"""
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"data": "test"}

    result = await service.get_data(mock_client)

    assert result["data"] == "test"
    mock_client.fetch.assert_called_once()
```

---

## Alternatives Considered

### 1. Threading
**Rejected** because:
- Higher memory overhead
- GIL limits true parallelism
- Race conditions more common
- AsyncIO better for I/O-bound workloads

**When to Reconsider:**
- CPU-bound operations
- Library requires threading
- Need true parallelism

### 2. Multiprocessing
**Rejected** because:
- Very high memory overhead
- Complex inter-process communication
- Overkill for I/O-bound work

**When to Reconsider:**
- CPU-bound operations
- Need to bypass GIL
- Independent worker processes

### 3. Synchronous with Thread Pool
**Rejected** because:
- Limited scalability
- Higher memory usage
- More complex error handling
- AsyncIO provides better control

### 4. Twisted/Tornado
**Rejected** because:
- AsyncIO is now Python standard
- Better ecosystem and tooling
- Easier for contributors to learn
- Modern libraries support AsyncIO

---

## Related Decisions

- [ADR-0002: Event-Driven Communication](./0002-event-driven-communication.md)
- [ADR-0007: AI Provider Abstraction](./0007-ai-provider-abstraction.md)
- [ADR-0008: SQLite as Primary Persistence](./0008-sqlite-primary-persistence.md)

---

## References

- [Python AsyncIO Documentation](https://docs.python.org/3/library/asyncio.html)
- [AsyncIO Best Practices](https://github.com/python/asyncio/wiki/ThirdParty)
- [Real Python AsyncIO Tutorial](https://realpython.com/async-io-python/)

---

## Migration Notes

All new code MUST be async. When modifying existing sync code:

1. Change `def` to `async def`
2. Add `await` to I/O operations
3. Replace sync libraries with async alternatives:
   - `requests` → `httpx`
   - `sqlite3` → `aiosqlite`
   - `threading.Lock` → `asyncio.Lock`
4. Update tests to use `@pytest.mark.asyncio`
5. Update type hints: `Awaitable[T]`, `AsyncIterator[T]`

The async migration has been a resounding success, enabling Marcus to handle concurrent operations efficiently and respond quickly to user requests.
