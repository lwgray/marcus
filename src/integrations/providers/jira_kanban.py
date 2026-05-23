"""
Jira kanban provider scaffold for Marcus.

Connects Marcus to a Jira Cloud or Jira Data Center instance via the
Jira REST API v3 so that AI agents can eventually read issues, update
their status, and post progress comments.

Current state: scaffold / proof-of-concept.
- ``connect()`` and ``disconnect()`` are fully implemented.
- ``get_all_tasks()`` and ``get_available_tasks()`` are fully implemented
  as a proof-of-concept that converts Jira issues to Marcus ``Task`` objects.
- All remaining ``KanbanInterface`` methods raise ``NotImplementedError``
  with a clear message pointing back to the tracking issue.

See https://github.com/lwgray/marcus/issues/241 for the full implementation
road-map.

Classes
-------
JiraKanban
    Jira REST API v3 implementation of KanbanInterface.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx

from src.core.models import Priority, Task, TaskStatus
from src.integrations.kanban_interface import KanbanInterface, KanbanProvider

logger = logging.getLogger(__name__)

# Jira status name → Marcus TaskStatus
_STATUS_MAP: Dict[str, TaskStatus] = {
    "to do": TaskStatus.TODO,
    "todo": TaskStatus.TODO,
    "backlog": TaskStatus.TODO,
    "selected for development": TaskStatus.TODO,
    "open": TaskStatus.TODO,
    "in progress": TaskStatus.IN_PROGRESS,
    "in development": TaskStatus.IN_PROGRESS,
    "in review": TaskStatus.IN_PROGRESS,
    "blocked": TaskStatus.BLOCKED,
    "impediment": TaskStatus.BLOCKED,
    "on hold": TaskStatus.BLOCKED,
    "done": TaskStatus.DONE,
    "closed": TaskStatus.DONE,
    "resolved": TaskStatus.DONE,
    "complete": TaskStatus.DONE,
}

# Jira priority name → Marcus Priority
_PRIORITY_MAP: Dict[str, Priority] = {
    "highest": Priority.URGENT,
    "critical": Priority.URGENT,
    "blocker": Priority.URGENT,
    "high": Priority.HIGH,
    "major": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "minor": Priority.LOW,
    "low": Priority.LOW,
    "lowest": Priority.LOW,
    "trivial": Priority.LOW,
}

_NOT_IMPLEMENTED_MSG = (
    "JiraKanban.{method}() is not yet implemented. "
    "Track progress at https://github.com/lwgray/marcus/issues/241"
)


class JiraKanban(KanbanInterface):
    """
    Jira REST API v3 implementation of KanbanInterface (scaffold).

    Authenticates with Jira using email + API token (Basic Auth), which
    is the supported mechanism for both Jira Cloud and Jira Data Center.

    Parameters
    ----------
    config : Dict[str, Any]
        Required keys:

        ``jira_url``
            Base URL of the Jira instance, e.g.
            ``https://yourcompany.atlassian.net``.  Do **not** include
            a trailing slash.
        ``jira_email``
            The email address associated with the Jira account.
        ``jira_api_token``
            API token generated at
            https://id.atlassian.com/manage-profile/security/api-tokens

        Optional keys:

        ``jira_project_key``
            Jira project key (e.g. ``"MARC"``).  When supplied,
            ``get_all_tasks()`` scopes its JQL query to that project.
        ``jira_max_results``
            Maximum number of issues returned per query (default: 100).
    """

    _API_BASE = "/rest/api/3"

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.provider = KanbanProvider.JIRA

        self._jira_url: str = config["jira_url"].rstrip("/")
        self._email: str = config["jira_email"]
        self._api_token: str = config["jira_api_token"]
        self._project_key: Optional[str] = config.get("jira_project_key")
        self._max_results: int = int(config.get("jira_max_results", 100))

        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle — fully implemented
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Open an authenticated HTTP session and verify credentials.

        Calls ``GET /rest/api/3/myself`` as a lightweight credential
        check.  Returns ``True`` on success, ``False`` otherwise.

        Returns
        -------
        bool
            ``True`` if the connection and credential check succeeded.
        """
        self._client = httpx.AsyncClient(
            base_url=self._jira_url,
            auth=(self._email, self._api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=15.0,
        )
        try:
            response = await self._client.get(f"{self._API_BASE}/myself")
            response.raise_for_status()
            account = response.json()
            logger.info(
                "Connected to Jira as '%s' (%s)",
                account.get("displayName", "unknown"),
                self._jira_url,
            )
            return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Jira authentication failed (%s): %s",
                exc.response.status_code,
                exc.response.text[:200],
            )
            await self._client.aclose()
            self._client = None
            return False
        except httpx.HTTPError as exc:
            logger.error("Jira connection error: %s", exc)
            await self._client.aclose()
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Task retrieval — proof-of-concept implementations
    # ------------------------------------------------------------------

    async def get_all_tasks(self) -> List[Task]:
        """
        Fetch all Jira issues and convert them to Marcus ``Task`` objects.

        Uses JQL to query the configured project (if ``jira_project_key``
        is set) or the entire instance.  Handles Jira pagination
        transparently.

        Returns
        -------
        List[Task]
            All issues converted to Marcus ``Task`` objects.

        Raises
        ------
        RuntimeError
            If ``connect()`` has not been called first.
        """
        if self._client is None:
            raise RuntimeError("Call connect() before get_all_tasks()")

        jql = (
            f"project = {self._project_key} ORDER BY created DESC"
            if self._project_key
            else "ORDER BY created DESC"
        )
        tasks: List[Task] = []
        start_at = 0

        while True:
            params: dict[str, str | int] = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": self._max_results,
                "fields": (
                    "summary,description,status,priority,assignee,"
                    "labels,timeoriginalestimate,project,created,updated,duedate"
                ),
            }
            response = await self._client.get(f"{self._API_BASE}/search", params=params)
            response.raise_for_status()
            data = response.json()

            issues = data.get("issues", [])
            for issue in issues:
                tasks.append(self._to_task(issue))

            start_at += len(issues)
            if start_at >= data.get("total", 0) or not issues:
                break

        return tasks

    async def get_available_tasks(self) -> List[Task]:
        """
        Return all unassigned issues in the TODO status.

        Delegates to ``get_all_tasks()`` and filters the result so only
        tasks with ``status == TODO`` and no assignee are returned —
        the set of tasks an agent can claim.

        Returns
        -------
        List[Task]
            Unassigned TODO tasks.
        """
        all_tasks = await self.get_all_tasks()
        return [
            t for t in all_tasks if t.status == TaskStatus.TODO and not t.assigned_to
        ]

    # ------------------------------------------------------------------
    # Unimplemented stubs — raise NotImplementedError with clear messages
    # ------------------------------------------------------------------

    async def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="get_task_by_id"))

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="create_task"))

    async def update_task(
        self, task_id: str, updates: Dict[str, Any]
    ) -> Optional[Task]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="update_task"))

    async def assign_task(self, task_id: str, assignee_id: str) -> bool:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="assign_task"))

    async def move_task_to_column(self, task_id: str, column_name: str) -> bool:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(method="move_task_to_column")
        )

    async def add_comment(self, task_id: str, comment: str) -> bool:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="add_comment"))

    async def get_project_metrics(self) -> Dict[str, Any]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(method="get_project_metrics")
        )

    async def report_blocker(
        self, task_id: str, blocker_description: str, severity: str = "medium"
    ) -> bool:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="report_blocker"))

    async def update_task_progress(
        self, task_id: str, progress_data: Dict[str, Any]
    ) -> bool:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(method="update_task_progress")
        )

    async def upload_attachment(
        self,
        task_id: str,
        filename: str,
        content: Union[str, bytes],
        content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(method="upload_attachment")
        )

    async def get_attachments(self, task_id: str) -> Dict[str, Any]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(method="get_attachments"))

    async def download_attachment(
        self, attachment_id: str, filename: str, task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Not yet implemented. See https://github.com/lwgray/marcus/issues/241"""
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(method="download_attachment")
        )

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------

    def normalize_status(self, provider_status: Any) -> TaskStatus:
        """
        Map a Jira status name to a Marcus ``TaskStatus``.

        Parameters
        ----------
        provider_status : Any
            The value from a Jira issue's ``status.name`` field.

        Returns
        -------
        TaskStatus
            Matching ``TaskStatus``, defaulting to ``TODO`` for unknown names.
        """
        if isinstance(provider_status, str):
            return _STATUS_MAP.get(provider_status.lower(), TaskStatus.TODO)
        return TaskStatus.TODO

    def normalize_priority(self, provider_priority: Any) -> Priority:
        """
        Map a Jira priority name to a Marcus ``Priority``.

        Parameters
        ----------
        provider_priority : Any
            The value from a Jira issue's ``priority.name`` field.

        Returns
        -------
        Priority
            Matching ``Priority``, defaulting to ``MEDIUM`` for unknown names.
        """
        if isinstance(provider_priority, str):
            return _PRIORITY_MAP.get(provider_priority.lower(), Priority.MEDIUM)
        return Priority.MEDIUM

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _to_task(self, issue: Dict[str, Any]) -> Task:
        """
        Convert a raw Jira issue dict to a Marcus ``Task``.

        Parameters
        ----------
        issue : Dict[str, Any]
            A single issue object from the Jira REST API ``/search``
            or ``/issue/{key}`` response.

        Returns
        -------
        Task
            Normalised ``Task`` understood by all Marcus components.
        """
        fields = issue.get("fields", {})

        raw_status = (fields.get("status") or {}).get("name", "")
        raw_priority = (fields.get("priority") or {}).get("name", "")
        assignee_obj = fields.get("assignee") or {}
        project_obj = fields.get("project") or {}
        description_obj = fields.get("description") or {}

        # Jira Cloud stores description as Atlassian Document Format (ADF);
        # extract plain text from the first text node as a best-effort
        # summary.  Data Center may return a plain string instead.
        if isinstance(description_obj, dict):
            description_text = _extract_adf_text(description_obj)
        else:
            description_text = str(description_obj) if description_obj else ""

        # Estimated seconds → hours
        estimate_seconds = fields.get("timeoriginalestimate") or 0
        estimated_hours = float(estimate_seconds) / 3600.0 if estimate_seconds else 0.0

        # Parse ISO-8601 timestamps; fall back to now() if absent
        now = datetime.now(timezone.utc)
        created_at = _parse_jira_datetime(fields.get("created")) or now
        updated_at = _parse_jira_datetime(fields.get("updated")) or now
        due_date = _parse_jira_datetime(fields.get("duedate"))

        return Task(
            id=str(issue.get("key", issue.get("id", ""))),
            name=fields.get("summary", ""),
            description=description_text,
            status=self.normalize_status(raw_status),
            priority=self.normalize_priority(raw_priority),
            assigned_to=assignee_obj.get("accountId") or assignee_obj.get("name"),
            created_at=created_at,
            updated_at=updated_at,
            due_date=due_date,
            project_id=project_obj.get("id", ""),
            project_name=project_obj.get("name", ""),
            labels=fields.get("labels", []),
            estimated_hours=estimated_hours,
        )


def _parse_jira_datetime(value: Optional[str]) -> Optional[datetime]:
    """
    Parse a Jira ISO-8601 timestamp string into a timezone-aware ``datetime``.

    Jira returns timestamps like ``"2024-01-15T10:30:00.000+0000"``.
    Returns ``None`` when the value is absent or cannot be parsed.

    Parameters
    ----------
    value : Optional[str]
        Raw timestamp string from the Jira API, or ``None``.

    Returns
    -------
    Optional[datetime]
        UTC-aware ``datetime``, or ``None``.
    """
    if not value:
        return None
    try:
        # Normalise the timezone suffix before parsing:
        #   "Z"     → "+00:00"  (UTC shorthand)
        #   "+0000" → "+00:00"  (Jira Cloud omits the colon; Python ≤ 3.10
        #                        fromisoformat rejects offsets without it)
        normalised = value.replace("Z", "+00:00")
        if len(normalised) >= 5 and normalised[-5] in ("+", "-"):
            offset = normalised[-5:]
            if ":" not in offset:
                normalised = normalised[:-2] + ":" + normalised[-2:]
        return datetime.fromisoformat(normalised)
    except (ValueError, AttributeError):
        return None


def _extract_adf_text(adf: Dict[str, Any]) -> str:
    """
    Best-effort extraction of plain text from an Atlassian Document Format node.

    Parameters
    ----------
    adf : Dict[str, Any]
        An ADF document or node dict from the Jira Cloud REST API.

    Returns
    -------
    str
        Concatenated text content, with paragraphs separated by spaces.
    """
    parts: List[str] = []
    for node in adf.get("content", []):
        node_type = node.get("type", "")
        if node_type == "text":
            parts.append(node.get("text", ""))
        elif "content" in node:
            parts.append(_extract_adf_text(node))
    return " ".join(p for p in parts if p)
