# How to Add a New Kanban Provider

Marcus is an AI-powered project management system that orchestrates multiple AI agents to work on software projects in parallel. At its core, Marcus uses a **kanban board** (a visual task board with columns like "To Do", "In Progress", and "Done") as the shared workspace where agents pick up tasks, update their status, and post progress notes. All of this coordination happens through a standard interface so that the kanban board can be backed by different services — Planka, GitHub Projects, Linear, or a local SQLite database — without changing any agent code.

This guide walks you through adding a brand-new kanban backend (called a **provider**) so that Marcus can talk to a service of your choice.

---

## Glossary

| Term | Meaning |
|---|---|
| **Provider** | A class that connects Marcus to one specific kanban service (e.g., Trello, Jira, Asana) |
| **KanbanInterface** | The Python abstract base class all providers must implement (like a contract) |
| **KanbanFactory** | The factory class that reads the config and returns the right provider instance |
| **KanbanProvider enum** | An enum that lists the short string names for all supported providers |
| **Task** | A single unit of work (one "card" on the board), represented by the `Task` model |
| **TaskStatus** | An enum with four values: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE` |
| **Priority** | An enum with four values: `LOW`, `MEDIUM`, `HIGH`, `URGENT` |
| **config_marcus.json** | The JSON file where users set which provider to use and supply credentials |
| **Abstract method** | A method marked `@abstractmethod` that every subclass **must** implement; skipping one causes `TypeError` at import time |

---

## Prerequisites

- Python 3.10+
- A working Marcus checkout (see `docs/source/developer/local-development.md`)
- Access to the external service you want to integrate (account, API key, etc.)

---

## Overview: What You Will Touch

Five things need to change when adding a provider:

1. **Create** `src/integrations/providers/myservice_kanban.py` — your provider class
2. **Update** `src/integrations/providers/__init__.py` — export your class
3. **Update** `src/integrations/kanban_interface.py` — add a value to `KanbanProvider`
4. **Update** `src/integrations/kanban_factory.py` — wire the provider into the factory
5. **Update** `src/config/marcus_config.py` — add any new credential fields to `KanbanSettings`

Then write tests (covered in [Step 6](#step-6-write-tests)).

---

## Step 1: Create Your Provider Class

Create a new file at `src/integrations/providers/myservice_kanban.py`.

Replace `MyService` and `myservice` with the actual service name throughout.

```python
"""
MyService kanban provider for Marcus.

Connects Marcus to MyService's task management API so that AI agents can
read tasks, update their status, and post progress notes.
"""

import logging
from typing import Any, Dict, List, Optional, Union

import httpx  # or whatever HTTP client your service needs

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider

logger = logging.getLogger(__name__)


class MyServiceKanban(KanbanInterface):
    """
    MyService implementation of KanbanInterface.

    Parameters
    ----------
    config : Dict[str, Any]
        Required keys:
            - api_key: MyService API key
            - workspace_id: MyService workspace identifier
        Optional keys:
            - base_url: Override the default API endpoint
    """

    _BASE_URL = "https://api.myservice.example/v1"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.provider = KanbanProvider.MYSERVICE
        self._api_key: str = config["api_key"]
        self._workspace_id: str = config["workspace_id"]
        self._base_url: str = config.get("base_url", self._BASE_URL)
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Open an HTTP session and verify credentials with a lightweight ping.

        Returns
        -------
        bool
            True if the connection and credential check succeeded.
        """
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )
        try:
            response = await self._client.get("/me")
            response.raise_for_status()
            logger.info("Connected to MyService workspace %s", self._workspace_id)
            return True
        except httpx.HTTPError as exc:
            logger.error("MyService connection failed: %s", exc)
            await self._client.aclose()
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Task retrieval
    # ------------------------------------------------------------------

    async def get_available_tasks(self) -> List[Task]:
        """
        Return all unassigned tasks in the TODO column.

        Marcus agents call this to find work they can claim.

        Returns
        -------
        List[Task]
            Tasks with status TODO and no assignee.
        """
        all_tasks = await self.get_all_tasks()
        return [t for t in all_tasks if t.status == TaskStatus.TODO and not t.assigned_to]

    async def get_all_tasks(self) -> List[Task]:
        """
        Fetch every task in the workspace regardless of status.

        Returns
        -------
        List[Task]
            All tasks on the board.
        """
        assert self._client is not None, "Call connect() first"
        response = await self._client.get(f"/workspaces/{self._workspace_id}/tasks")
        response.raise_for_status()
        raw_tasks = response.json().get("tasks", [])
        return [self._to_task(raw) for raw in raw_tasks]

    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Fetch a single task by its ID.

        Parameters
        ----------
        task_id : str
            The MyService task identifier.

        Returns
        -------
        Optional[Task]
            The task, or None if not found.
        """
        assert self._client is not None, "Call connect() first"
        try:
            response = await self._client.get(f"/tasks/{task_id}")
            response.raise_for_status()
            return self._to_task(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    # ------------------------------------------------------------------
    # Task mutation
    # ------------------------------------------------------------------

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """
        Create a new task on the board.

        Parameters
        ----------
        task_data : Dict[str, Any]
            Expected keys: name, description, priority, labels, estimated_hours.

        Returns
        -------
        Task
            The newly created task.
        """
        assert self._client is not None, "Call connect() first"
        payload = {
            "title": task_data.get("name", "Untitled"),
            "description": task_data.get("description", ""),
            "priority": task_data.get("priority", "medium"),
            "workspace_id": self._workspace_id,
        }
        response = await self._client.post("/tasks", json=payload)
        response.raise_for_status()
        return self._to_task(response.json())

    async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """
        Update fields on an existing task.

        Parameters
        ----------
        task_id : str
            The MyService task identifier.
        updates : Dict[str, Any]
            Fields to update (name, description, priority, status, etc.).

        Returns
        -------
        Optional[Task]
            The updated task, or None if not found.
        """
        assert self._client is not None, "Call connect() first"
        try:
            response = await self._client.patch(f"/tasks/{task_id}", json=updates)
            response.raise_for_status()
            return self._to_task(response.json())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """
        Assign a task to an agent (or any user ID).

        Parameters
        ----------
        task_id : str
            The task to assign.
        assignee_id : str
            The agent/user identifier.

        Returns
        -------
        bool
            True if the assignment succeeded.
        """
        result = await self.update_task(task_id, {"assignee_id": assignee_id})
        return result is not None

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """
        Change the status/column of a task.

        Marcus passes human-readable column names such as "In Progress" or
        "Done". Map these to whatever your API expects.

        Parameters
        ----------
        task_id : str
            The task to move.
        column_name : str
            Human-readable column name.

        Returns
        -------
        bool
            True if the move succeeded.
        """
        # Map Marcus column names to MyService status values
        status_map = {
            "todo": "open",
            "in progress": "active",
            "blocked": "on_hold",
            "done": "closed",
        }
        api_status = status_map.get(column_name.lower(), column_name.lower())
        result = await self.update_task(task_id, {"status": api_status})
        return result is not None

    async def add_comment(self, task_id: str, comment: str) -> bool:
        """
        Post a comment on a task.

        Agents use this to report progress and blockers.

        Parameters
        ----------
        task_id : str
            The task to comment on.
        comment : str
            Comment text (plain or Markdown).

        Returns
        -------
        bool
            True if the comment was posted.
        """
        assert self._client is not None, "Call connect() first"
        try:
            response = await self._client.post(
                f"/tasks/{task_id}/comments",
                json={"body": comment},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    # ------------------------------------------------------------------
    # Metrics and agent-coordination methods
    # ------------------------------------------------------------------

    async def get_project_metrics(self) -> Dict[str, Any]:
        """
        Return a summary of task counts by status.

        Returns
        -------
        Dict[str, Any]
            Keys: total_tasks, backlog_tasks, in_progress_tasks,
            completed_tasks, blocked_tasks.
        """
        all_tasks = await self.get_all_tasks()
        return {
            "total_tasks": len(all_tasks),
            "backlog_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.TODO),
            "in_progress_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS),
            "completed_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.DONE),
            "blocked_tasks": sum(1 for t in all_tasks if t.status == TaskStatus.BLOCKED),
        }

    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """
        Mark a task as blocked and add a comment explaining why.

        Parameters
        ----------
        task_id : str
            The blocked task.
        blocker_description : str
            Human-readable explanation of what is blocking the task.
        severity : str
            One of "low", "medium", "high".

        Returns
        -------
        bool
            True if the blocker was recorded.
        """
        moved = await self.move_task_to_column(task_id, "blocked")
        commented = await self.add_comment(
            task_id, f"🚧 **Blocker ({severity}):** {blocker_description}"
        )
        return moved and commented

    async def update_task_progress(self, task_id: str, progress_data: Dict[str, Any]) -> bool:
        """
        Post a progress update on a task.

        Parameters
        ----------
        task_id : str
            The task being worked on.
        progress_data : Dict[str, Any]
            Expected keys: progress (0–100), status, message.

        Returns
        -------
        bool
            True if the update was recorded.
        """
        pct = progress_data.get("progress", 0)
        msg = progress_data.get("message", "")
        comment = f"Progress: {pct}% — {msg}" if msg else f"Progress: {pct}%"
        return await self.add_comment(task_id, comment)

    # ------------------------------------------------------------------
    # Attachments
    # ------------------------------------------------------------------

    async def upload_attachment(
        self,
        task_id: str,
        filename: str,
        content: Union[str, bytes],
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Attach a file to a task.

        Parameters
        ----------
        task_id : str
            The task to attach to.
        filename : str
            Name of the file.
        content : Union[str, bytes]
            File content as bytes or a base64-encoded string.
        content_type : Optional[str]
            MIME type, e.g. ``"application/json"``.

        Returns
        -------
        Dict[str, Any]
            ``{"success": True, "data": {"id": ..., "filename": ..., "url": ...}}``
            or ``{"success": False, "error": "..."}``.
        """
        assert self._client is not None, "Call connect() first"
        if isinstance(content, str):
            import base64
            content = base64.b64decode(content)
        try:
            response = await self._client.post(
                f"/tasks/{task_id}/attachments",
                files={"file": (filename, content, content_type or "application/octet-stream")},
            )
            response.raise_for_status()
            data = response.json()
            return {"success": True, "data": {"id": data["id"], "filename": filename, "url": data.get("url", "")}}
        except httpx.HTTPError as exc:
            return {"success": False, "error": str(exc)}

    async def get_attachments(self, task_id: str) -> Dict[str, Any]:
        """
        List all attachments on a task.

        Parameters
        ----------
        task_id : str
            The task identifier.

        Returns
        -------
        Dict[str, Any]
            ``{"success": True, "data": [{"id": ..., "filename": ..., "url": ...}]}``
            or ``{"success": False, "error": "..."}``.
        """
        assert self._client is not None, "Call connect() first"
        try:
            response = await self._client.get(f"/tasks/{task_id}/attachments")
            response.raise_for_status()
            return {"success": True, "data": response.json().get("attachments", [])}
        except httpx.HTTPError as exc:
            return {"success": False, "error": str(exc)}

    async def download_attachment(
        self, attachment_id: str, filename: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Download an attachment by ID.

        Parameters
        ----------
        attachment_id : str
            The attachment identifier.
        filename : str
            The filename (used as a fallback label).
        task_id : Optional[str]
            Required by some providers; optional here.

        Returns
        -------
        Dict[str, Any]
            ``{"success": True, "data": {"content": "<base64>", "filename": ..., "content_type": ...}}``
            or ``{"success": False, "error": "..."}``.
        """
        assert self._client is not None, "Call connect() first"
        import base64
        try:
            response = await self._client.get(f"/attachments/{attachment_id}/download")
            response.raise_for_status()
            encoded = base64.b64encode(response.content).decode("ascii")
            content_type = response.headers.get("content-type", "application/octet-stream")
            return {"success": True, "data": {"content": encoded, "filename": filename, "content_type": content_type}}
        except httpx.HTTPError as exc:
            return {"success": False, "error": str(exc)}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_task(self, raw: Dict[str, Any]) -> Task:
        """
        Convert a raw MyService API response dict into a Marcus Task object.

        Parameters
        ----------
        raw : Dict[str, Any]
            JSON object returned by the MyService API.

        Returns
        -------
        Task
            Normalized Task model understood by all Marcus components.
        """
        return Task(
            id=str(raw["id"]),
            name=raw.get("title", ""),
            description=raw.get("description", ""),
            status=self.normalize_status(raw.get("status", "open")),
            priority=self.normalize_priority(raw.get("priority", "medium")),
            assigned_to=raw.get("assignee_id"),
            project_id=str(raw.get("workspace_id", "")),
            project_name=raw.get("workspace_name", ""),
            labels=raw.get("tags", []),
            estimated_hours=float(raw.get("estimated_hours", 0)),
        )

    def normalize_status(self, provider_status: Any) -> TaskStatus:
        """
        Map MyService status strings to Marcus TaskStatus values.

        Parameters
        ----------
        provider_status : Any
            A status string from the MyService API.

        Returns
        -------
        TaskStatus
            The equivalent Marcus status.
        """
        status_map = {
            "open": TaskStatus.TODO,
            "active": TaskStatus.IN_PROGRESS,
            "on_hold": TaskStatus.BLOCKED,
            "closed": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
        }
        if isinstance(provider_status, str):
            return status_map.get(provider_status.lower(), TaskStatus.TODO)
        return TaskStatus.TODO

    def normalize_priority(self, provider_priority: Any) -> Priority:
        """
        Map MyService priority strings to Marcus Priority values.

        Parameters
        ----------
        provider_priority : Any
            A priority string from the MyService API.

        Returns
        -------
        Priority
            The equivalent Marcus priority level.
        """
        priority_map = {
            "critical": Priority.URGENT,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "low": Priority.LOW,
        }
        if isinstance(provider_priority, str):
            return priority_map.get(provider_priority.lower(), Priority.MEDIUM)
        return Priority.MEDIUM
```

> **Key rule:** The `_to_task()` helper is the most important method in your class. Every public method that returns a `Task` should go through it to ensure Marcus always receives a normalized model, regardless of what the external API returns.

---

## Step 2: Export Your Class

Open `src/integrations/providers/__init__.py` and add your new class:

```python
# src/integrations/providers/__init__.py

from .github_kanban import GitHubKanban
from .linear_kanban import LinearKanban
from .myservice_kanban import MyServiceKanban   # ← add this line
from .planka import Planka
from .planka_kanban import PlankaKanban
from .sqlite_kanban import SQLiteKanban

__all__ = [
    "Planka",
    "PlankaKanban",
    "LinearKanban",
    "GitHubKanban",
    "MyServiceKanban",   # ← add this line
    "SQLiteKanban",
]
```

---

## Step 3: Register the Provider Name

Open `src/integrations/kanban_interface.py` and add a value to the `KanbanProvider` enum:

```python
class KanbanProvider(Enum):
    """Supported kanban providers."""

    PLANKA = "planka"
    LINEAR = "linear"
    GITHUB = "github"
    SQLITE = "sqlite"
    MYSERVICE = "myservice"   # ← add this line
```

The string value (`"myservice"`) is what users will write in `config_marcus.json` and what the factory matches against. Use all lowercase, no spaces.

---

## Step 4: Wire Up the Factory

Open `src/integrations/kanban_factory.py`. Add an `elif` block inside `KanbanFactory.create()` for your provider, following the exact same pattern as the existing ones:

```python
# src/integrations/kanban_factory.py

from src.integrations.providers import (
    GitHubKanban,
    LinearKanban,
    MyServiceKanban,   # ← add this import
    Planka,
    SQLiteKanban,
)

# Inside KanbanFactory.create():
elif provider_lower == KanbanProvider.MYSERVICE.value:
    if not config:
        config = {
            "api_key": (
                marcus_config.kanban.myservice_api_key        # config field (Step 5)
                or os.getenv("MYSERVICE_API_KEY")             # env-var fallback
            ),
            "workspace_id": (
                marcus_config.kanban.myservice_workspace_id
                or os.getenv("MYSERVICE_WORKSPACE_ID")
            ),
        }
    return MyServiceKanban(config)
```

Place the new `elif` block **before** the final `else` that raises `ValueError`.

---

## Step 5: Add Configuration Fields

Open `src/config/marcus_config.py` and add your credential fields to the `KanbanSettings` dataclass:

```python
@dataclass
class KanbanSettings:
    """Kanban provider configuration."""

    provider: str = "sqlite"
    board_name: Optional[str] = None
    # ... existing fields ...

    # MyService credentials
    myservice_api_key: Optional[str] = None        # ← add these
    myservice_workspace_id: Optional[str] = None   # ← add these
```

Then tell users to add a `kanban` block to their `config_marcus.json`:

```json
{
  "kanban": {
    "provider": "myservice",
    "myservice_api_key": "sk-your-key-here",
    "myservice_workspace_id": "ws_abc123"
  }
}
```

### Environment variable fallback

If users prefer not to put secrets in `config_marcus.json`, they can set these instead:

```bash
export MYSERVICE_API_KEY="sk-your-key-here"
export MYSERVICE_WORKSPACE_ID="ws_abc123"
```

The factory reads the config field first, then falls back to the environment variable.

---

## Step 6: Write Tests

Marcus requires **80% test coverage** and tests that run in under 100 ms. Put unit tests in `tests/unit/`. Here is a minimal test file to get started:

```python
# tests/unit/test_myservice_kanban.py
"""Unit tests for MyServiceKanban."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.models import Priority, Task, TaskStatus
from src.integrations.providers.myservice_kanban import MyServiceKanban


@pytest.fixture
def config() -> dict:
    return {"api_key": "test-key", "workspace_id": "ws_test"}


@pytest.fixture
def kanban(config) -> MyServiceKanban:
    return MyServiceKanban(config)


class TestMyServiceKanbanInit:
    """Test constructor and provider identity."""

    def test_stores_api_key(self, kanban):
        """Provider stores the API key from config."""
        assert kanban._api_key == "test-key"

    def test_stores_workspace_id(self, kanban):
        """Provider stores the workspace ID from config."""
        assert kanban._workspace_id == "ws_test"

    def test_provider_enum_set(self, kanban):
        """Provider enum is MYSERVICE after construction."""
        from src.integrations.kanban_interface import KanbanProvider
        assert kanban.provider == KanbanProvider.MYSERVICE


class TestNormalization:
    """Test status and priority mapping helpers."""

    def test_normalize_status_open_is_todo(self, kanban):
        """MyService 'open' maps to TODO."""
        assert kanban.normalize_status("open") == TaskStatus.TODO

    def test_normalize_status_active_is_in_progress(self, kanban):
        """MyService 'active' maps to IN_PROGRESS."""
        assert kanban.normalize_status("active") == TaskStatus.IN_PROGRESS

    def test_normalize_status_closed_is_done(self, kanban):
        """MyService 'closed' maps to DONE."""
        assert kanban.normalize_status("closed") == TaskStatus.DONE

    def test_normalize_priority_high(self, kanban):
        """MyService 'high' maps to Priority.HIGH."""
        assert kanban.normalize_priority("high") == Priority.HIGH

    def test_normalize_priority_unknown_defaults_to_medium(self, kanban):
        """Unknown priority strings default to MEDIUM."""
        assert kanban.normalize_priority("unknown_level") == Priority.MEDIUM


class TestToTask:
    """Test the _to_task conversion helper."""

    def test_converts_id_to_string(self, kanban):
        """Task id is always a string even if the API returns an integer."""
        raw = {"id": 42, "title": "Build feature", "status": "open", "priority": "high"}
        task = kanban._to_task(raw)
        assert task.id == "42"
        assert isinstance(task.id, str)

    def test_maps_title_to_name(self, kanban):
        """API 'title' field becomes Task.name."""
        raw = {"id": "1", "title": "My Task", "status": "open", "priority": "medium"}
        task = kanban._to_task(raw)
        assert task.name == "My Task"

    def test_missing_optional_fields_do_not_raise(self, kanban):
        """_to_task should not raise when optional fields are absent."""
        raw = {"id": "1", "title": "Minimal"}
        task = kanban._to_task(raw)
        assert task.id == "1"


class TestGetAvailableTasks:
    """Test that get_available_tasks filters correctly."""

    @pytest.mark.asyncio
    async def test_returns_only_todo_and_unassigned(self, kanban):
        """get_available_tasks filters to TODO + unassigned tasks only."""
        tasks = [
            Task(id="1", name="Open", status=TaskStatus.TODO, assigned_to=None, priority=Priority.MEDIUM),
            Task(id="2", name="Assigned", status=TaskStatus.TODO, assigned_to="agent-1", priority=Priority.MEDIUM),
            Task(id="3", name="WIP", status=TaskStatus.IN_PROGRESS, assigned_to=None, priority=Priority.MEDIUM),
        ]
        kanban.get_all_tasks = AsyncMock(return_value=tasks)
        available = await kanban.get_available_tasks()
        assert len(available) == 1
        assert available[0].id == "1"


class TestConnect:
    """Test connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_returns_true_on_success(self, kanban):
        """connect() returns True when the /me endpoint responds 200."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await kanban.connect()

        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, kanban):
        """disconnect() calls aclose() on the HTTP client."""
        mock_client = AsyncMock()
        kanban._client = mock_client
        await kanban.disconnect()
        mock_client.aclose.assert_called_once()
        assert kanban._client is None
```

Run the tests:

```bash
# Run just your new tests
pytest tests/unit/test_myservice_kanban.py -v

# Run with coverage for your file
pytest tests/unit/test_myservice_kanban.py --cov=src/integrations/providers/myservice_kanban --cov-report=term-missing
```

You need at least **80% line coverage** before submitting a pull request.

---

## Step 7: Verify End-to-End

1. Create `config_marcus.json` with your provider:

   ```json
   {
     "kanban": {
       "provider": "myservice",
       "myservice_api_key": "sk-test",
       "myservice_workspace_id": "ws_test"
     }
   }
   ```

2. Run the board command (a quick sanity check that the factory can create your class):

   ```bash
   ./marcus board --list
   ```

   Expected output: a table listing projects from your workspace.

3. Run the live view:

   ```bash
   ./marcus board --watch
   ```

   Expected: a live-updating board in the terminal. Press Ctrl+C to exit.

4. Check that Marcus can start without errors:

   ```bash
   ./marcus start --dry-run
   ```

---

## Complete Method Reference

The table below lists every method in `KanbanInterface`. Methods marked **Required** will cause `TypeError` at startup if not implemented; **Optional** methods have default implementations you can override.

| Method | Required? | What it does |
|---|---|---|
| `connect() → bool` | Required | Open connection to the service; return True on success |
| `disconnect() → None` | Required | Close connection and release resources |
| `get_available_tasks() → List[Task]` | Required | Return TODO tasks with no assignee (agents look here for work) |
| `get_all_tasks() → List[Task]` | Required | Return every task regardless of status |
| `get_task_by_id(task_id) → Optional[Task]` | Required | Return one task by ID, or None if not found |
| `create_task(task_data) → Task` | Required | Create a new task and return it |
| `update_task(task_id, updates) → Optional[Task]` | Required | Update task fields; return updated task or None |
| `assign_task(task_id, assignee_id) → bool` | Required | Assign task to an agent; return True on success |
| `move_task_to_column(task_id, column_name) → bool` | Required | Move task to a column by name ("In Progress", "Done", etc.) |
| `add_comment(task_id, comment) → bool` | Required | Post a comment on a task |
| `get_project_metrics() → Dict[str, Any]` | Required | Return task counts by status |
| `report_blocker(task_id, description, severity) → bool` | Required | Mark task blocked and record why |
| `update_task_progress(task_id, progress_data) → bool` | Required | Post a progress update |
| `upload_attachment(task_id, filename, content, content_type) → Dict` | Required | Upload a file to a task |
| `get_attachments(task_id) → Dict` | Required | List all attachments on a task |
| `download_attachment(attachment_id, filename, task_id) → Dict` | Required | Download an attachment by ID |
| `delete_attachment(attachment_id, task_id) → Dict` | Optional | Delete an attachment (defaults to "not supported") |
| `update_attachment(attachment_id, filename, task_id) → Dict` | Optional | Update attachment metadata (defaults to "not supported") |
| `normalize_status(provider_status) → TaskStatus` | Optional | Map service status strings to `TaskStatus` enum |
| `normalize_priority(provider_priority) → Priority` | Optional | Map service priority strings to `Priority` enum |

---

## Where to Look in the Code First

| File | Purpose |
|---|---|
| `src/integrations/kanban_interface.py` | The full abstract base class and `KanbanProvider` enum |
| `src/integrations/kanban_factory.py` | Factory that instantiates the right provider from config |
| `src/integrations/providers/sqlite_kanban.py` | Simplest full reference implementation |
| `src/integrations/providers/linear_kanban.py` | REST API example (similar to most web services) |
| `src/integrations/providers/__init__.py` | Export list for all providers |
| `src/config/marcus_config.py` | `KanbanSettings` dataclass where you add credential fields |
| `src/core/models.py` | `Task`, `TaskStatus`, and `Priority` model definitions |
| `tests/unit/` | Existing provider unit tests to use as patterns |

---

## Common Mistakes

**1. Forgetting to implement an abstract method**

If you skip any of the 16 required methods, Python raises `TypeError: Can't instantiate abstract class MyServiceKanban` the moment the factory tries to create an instance. Check that every `@abstractmethod` in `KanbanInterface` has a matching method in your class.

**2. Returning a raw dict instead of a `Task`**

Methods like `get_all_tasks()` and `get_task_by_id()` must return `Task` objects (from `src.core.models`), not raw dicts. Route all return values through `_to_task()`.

**3. Hardcoding the status map instead of calling `normalize_status()`**

If the same string appears in multiple methods, extract the mapping into `normalize_status()` and call that helper everywhere. It keeps the mapping in one place.

**4. Not handling the "not found" case in `get_task_by_id()`**

Catch the 404 response from your API and return `None`. Marcus callers always check for `None`.

**5. Opening network connections in `__init__`**

Keep `__init__` free of I/O. Move all network calls to `connect()`. This lets Marcus create provider instances cheaply for configuration validation without hitting the network.

---

## Related

- Issue [#240](https://github.com/lwgray/marcus/issues/240) — "Add developer guide: How to add a new kanban provider"
- `src/integrations/kanban_interface.py` — the contract your provider must satisfy
- `src/integrations/providers/sqlite_kanban.py` — the reference implementation
- `docs/source/developer/contributing.md` — general contribution guidelines
- `docs/source/developer/local-development.md` — setting up a local Marcus environment
