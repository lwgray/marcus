"""
Unit tests for the JiraKanban provider scaffold.

JiraKanban is a scaffold implementation of KanbanInterface that connects
Marcus (an AI-agent coordination system) to Jira via its REST API v3.
These tests exercise the class without making any real HTTP calls — all
network I/O is intercepted with unittest.mock.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus

_NOW = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
from src.integrations.kanban_interface import KanbanProvider
from src.integrations.providers.jira_kanban import (
    JiraKanban,
    _extract_adf_text,
    _parse_jira_datetime,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> dict:
    """Minimal valid config dict for JiraKanban."""
    return {
        "jira_url": "https://example.atlassian.net",
        "jira_email": "bot@example.com",
        "jira_api_token": "test-token-abc",
        "jira_project_key": "MARC",
    }


@pytest.fixture
def kanban(config) -> JiraKanban:
    """Unconnected JiraKanban instance."""
    return JiraKanban(config)


def _make_jira_issue(
    key: str = "MARC-1",
    summary: str = "Do something",
    status: str = "To Do",
    priority: str = "Medium",
    assignee_id: str | None = None,
    labels: list | None = None,
    estimate_seconds: int | None = None,
    project_id: str = "10001",
    project_name: str = "Marcus",
) -> dict:
    """Build a minimal Jira issue dict resembling the REST API response."""
    return {
        "id": "100001",
        "key": key,
        "fields": {
            "summary": summary,
            "description": None,
            "status": {"name": status},
            "priority": {"name": priority},
            "assignee": {"accountId": assignee_id} if assignee_id else None,
            "labels": labels or [],
            "timeoriginalestimate": estimate_seconds,
            "project": {"id": project_id, "name": project_name},
            "created": "2024-01-15T10:00:00.000+0000",
            "updated": "2024-01-15T10:00:00.000+0000",
            "duedate": None,
        },
    }


def _make_task(**overrides) -> Task:
    """Build a minimal Task for use in test assertions."""
    defaults = dict(
        id="1",
        name="Task",
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=_NOW,
        updated_at=_NOW,
        due_date=None,
        estimated_hours=0.0,
    )
    defaults.update(overrides)
    return Task(**defaults)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestJiraKanbanInit:
    """Verify construction stores config and sets the provider enum."""

    def test_stores_jira_url(self, kanban):
        """jira_url is stored without trailing slash."""
        assert kanban._jira_url == "https://example.atlassian.net"

    def test_trailing_slash_stripped(self, config):
        """Constructor strips a trailing slash from jira_url."""
        config["jira_url"] = "https://example.atlassian.net/"
        k = JiraKanban(config)
        assert k._jira_url == "https://example.atlassian.net"

    def test_stores_email(self, kanban):
        """jira_email is stored on the instance."""
        assert kanban._email == "bot@example.com"

    def test_stores_api_token(self, kanban):
        """jira_api_token is stored on the instance."""
        assert kanban._api_token == "test-token-abc"

    def test_stores_project_key(self, kanban):
        """jira_project_key is stored on the instance."""
        assert kanban._project_key == "MARC"

    def test_provider_enum_is_jira(self, kanban):
        """provider attribute is set to KanbanProvider.JIRA."""
        assert kanban.provider == KanbanProvider.JIRA

    def test_client_is_none_before_connect(self, kanban):
        """HTTP client is None until connect() is called."""
        assert kanban._client is None

    def test_default_max_results(self, config):
        """max_results defaults to 100 when not supplied."""
        del config["jira_project_key"]
        k = JiraKanban(
            {
                "jira_url": "https://x.atlassian.net",
                "jira_email": "a@b.com",
                "jira_api_token": "tok",
            }
        )
        assert k._max_results == 100

    def test_custom_max_results(self, config):
        """jira_max_results config value is respected."""
        config["jira_max_results"] = 50
        k = JiraKanban(config)
        assert k._max_results == 50


# ---------------------------------------------------------------------------
# connect() / disconnect()
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    """Lifecycle tests for connect() and disconnect()."""

    @pytest.mark.asyncio
    async def test_connect_returns_true_on_200(self, kanban):
        """connect() returns True when /myself responds 200."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(return_value={"displayName": "Marcus Bot"})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await kanban.connect()

        assert result is True
        assert kanban._client is mock_client

    @pytest.mark.asyncio
    async def test_connect_returns_false_on_401(self, kanban):
        """connect() returns False and clears _client when credentials are wrong."""
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "401", request=MagicMock(), response=mock_response
            )
        )
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await kanban.connect()

        assert result is False
        assert kanban._client is None

    @pytest.mark.asyncio
    async def test_connect_returns_false_on_network_error(self, kanban):
        """connect() returns False on generic network failures."""
        import httpx

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("no route"))
        mock_client.aclose = AsyncMock()

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await kanban.connect()

        assert result is False
        assert kanban._client is None

    @pytest.mark.asyncio
    async def test_disconnect_closes_client(self, kanban):
        """disconnect() calls aclose() and sets _client to None."""
        mock_client = AsyncMock()
        kanban._client = mock_client

        await kanban.disconnect()

        mock_client.aclose.assert_called_once()
        assert kanban._client is None

    @pytest.mark.asyncio
    async def test_disconnect_is_safe_without_connect(self, kanban):
        """disconnect() does nothing when _client is already None."""
        await kanban.disconnect()  # must not raise


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


class TestNormalizeStatus:
    """Test Jira status → Marcus TaskStatus mapping."""

    @pytest.mark.parametrize(
        "jira_status,expected",
        [
            ("To Do", TaskStatus.TODO),
            ("todo", TaskStatus.TODO),
            ("Backlog", TaskStatus.TODO),
            ("In Progress", TaskStatus.IN_PROGRESS),
            ("In Review", TaskStatus.IN_PROGRESS),
            ("Blocked", TaskStatus.BLOCKED),
            ("On Hold", TaskStatus.BLOCKED),
            ("Done", TaskStatus.DONE),
            ("Closed", TaskStatus.DONE),
            ("Resolved", TaskStatus.DONE),
            ("Unknown Status XYZ", TaskStatus.TODO),
        ],
    )
    def test_status_mapping(self, kanban, jira_status, expected):
        """Known Jira statuses map to the correct Marcus TaskStatus."""
        assert kanban.normalize_status(jira_status) == expected

    def test_non_string_defaults_to_todo(self, kanban):
        """Non-string input defaults to TODO."""
        assert kanban.normalize_status(None) == TaskStatus.TODO
        assert kanban.normalize_status(42) == TaskStatus.TODO


class TestNormalizePriority:
    """Test Jira priority → Marcus Priority mapping."""

    @pytest.mark.parametrize(
        "jira_priority,expected",
        [
            ("Highest", Priority.URGENT),
            ("Critical", Priority.URGENT),
            ("High", Priority.HIGH),
            ("Major", Priority.HIGH),
            ("Medium", Priority.MEDIUM),
            ("Low", Priority.LOW),
            ("Lowest", Priority.LOW),
            ("Trivial", Priority.LOW),
            ("Unknown", Priority.MEDIUM),
        ],
    )
    def test_priority_mapping(self, kanban, jira_priority, expected):
        """Known Jira priorities map to the correct Marcus Priority."""
        assert kanban.normalize_priority(jira_priority) == expected

    def test_non_string_defaults_to_medium(self, kanban):
        """Non-string input defaults to MEDIUM."""
        assert kanban.normalize_priority(None) == Priority.MEDIUM


# ---------------------------------------------------------------------------
# _to_task() conversion
# ---------------------------------------------------------------------------


class TestToTask:
    """Test raw Jira issue → Marcus Task conversion."""

    def test_id_uses_issue_key(self, kanban):
        """Task.id is the Jira issue key (e.g. MARC-42), not the numeric id."""
        issue = _make_jira_issue(key="MARC-42")
        task = kanban._to_task(issue)
        assert task.id == "MARC-42"

    def test_name_from_summary(self, kanban):
        """Task.name comes from the Jira 'summary' field."""
        issue = _make_jira_issue(summary="Implement login flow")
        task = kanban._to_task(issue)
        assert task.name == "Implement login flow"

    def test_status_normalised(self, kanban):
        """Task.status is normalised from the Jira status name."""
        task = kanban._to_task(_make_jira_issue(status="In Progress"))
        assert task.status == TaskStatus.IN_PROGRESS

    def test_priority_normalised(self, kanban):
        """Task.priority is normalised from the Jira priority name."""
        task = kanban._to_task(_make_jira_issue(priority="High"))
        assert task.priority == Priority.HIGH

    def test_assigned_to_account_id(self, kanban):
        """Task.assigned_to holds the Jira accountId string."""
        task = kanban._to_task(_make_jira_issue(assignee_id="5db0f4e4abc"))
        assert task.assigned_to == "5db0f4e4abc"

    def test_unassigned_task_has_none_assignee(self, kanban):
        """Task.assigned_to is None for issues with no assignee."""
        task = kanban._to_task(_make_jira_issue(assignee_id=None))
        assert task.assigned_to is None

    def test_labels_preserved(self, kanban):
        """Task.labels is a copy of the Jira labels list."""
        task = kanban._to_task(_make_jira_issue(labels=["backend", "sprint-1"]))
        assert task.labels == ["backend", "sprint-1"]

    def test_empty_labels(self, kanban):
        """Task.labels is an empty list when the issue has no labels."""
        task = kanban._to_task(_make_jira_issue(labels=[]))
        assert task.labels == []

    def test_estimated_hours_conversion(self, kanban):
        """timeoriginalestimate seconds are converted to hours."""
        # 7200 seconds = 2.0 hours
        task = kanban._to_task(_make_jira_issue(estimate_seconds=7200))
        assert task.estimated_hours == pytest.approx(2.0)

    def test_missing_estimate_is_zero(self, kanban):
        """Absent or null estimate results in 0.0 hours."""
        task = kanban._to_task(_make_jira_issue(estimate_seconds=None))
        assert task.estimated_hours == 0.0

    def test_project_id_and_name(self, kanban):
        """Task.project_id and project_name come from the Jira project object."""
        task = kanban._to_task(
            _make_jira_issue(project_id="10005", project_name="Acme")
        )
        assert task.project_id == "10005"
        assert task.project_name == "Acme"

    def test_plain_string_description(self, kanban):
        """Plain-string description (Data Center format) is stored directly."""
        issue = _make_jira_issue()
        issue["fields"]["description"] = "A plain description"
        task = kanban._to_task(issue)
        assert task.description == "A plain description"

    def test_adf_description_extracted(self, kanban):
        """Atlassian Document Format description is converted to plain text."""
        issue = _make_jira_issue()
        issue["fields"]["description"] = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}],
                }
            ],
        }
        task = kanban._to_task(issue)
        assert "Hello world" in task.description

    def test_null_description_is_empty_string(self, kanban):
        """None description produces an empty string, not an error."""
        issue = _make_jira_issue()
        issue["fields"]["description"] = None
        task = kanban._to_task(issue)
        assert task.description == ""


# ---------------------------------------------------------------------------
# get_all_tasks() — proof-of-concept
# ---------------------------------------------------------------------------


class TestGetAllTasks:
    """Test the get_all_tasks() implementation against mocked HTTP responses."""

    def _mock_search_response(
        self, issues: list, total: int | None = None
    ) -> MagicMock:
        """Build a mock httpx Response for the /search endpoint."""
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(
            return_value={
                "issues": issues,
                "total": total if total is not None else len(issues),
            }
        )
        return resp

    @pytest.mark.asyncio
    async def test_returns_list_of_tasks(self, kanban):
        """get_all_tasks() returns a list of Task objects."""
        kanban._client = AsyncMock()
        kanban._client.get = AsyncMock(
            return_value=self._mock_search_response([_make_jira_issue()])
        )
        tasks = await kanban.get_all_tasks()
        assert isinstance(tasks, list)
        assert len(tasks) == 1
        assert isinstance(tasks[0], Task)

    @pytest.mark.asyncio
    async def test_scopes_jql_to_project_key(self, kanban):
        """JQL query includes the configured project key."""
        kanban._client = AsyncMock()
        kanban._client.get = AsyncMock(return_value=self._mock_search_response([]))
        await kanban.get_all_tasks()
        call_kwargs = kanban._client.get.call_args
        params = call_kwargs[1].get(
            "params", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {}
        )
        assert "MARC" in params.get("jql", "")

    @pytest.mark.asyncio
    async def test_no_project_key_omits_project_filter(self, config):
        """When no project_key is set, JQL falls back to ORDER BY created DESC."""
        config.pop("jira_project_key", None)
        k = JiraKanban(config)
        k._client = AsyncMock()
        k._client.get = AsyncMock(return_value=self._mock_search_response([]))
        await k.get_all_tasks()
        call_kwargs = k._client.get.call_args
        params = call_kwargs[1].get("params", {})
        assert "ORDER BY" in params.get("jql", "")

    @pytest.mark.asyncio
    async def test_raises_if_not_connected(self, kanban):
        """get_all_tasks() raises RuntimeError when connect() was not called."""
        with pytest.raises(RuntimeError, match="connect()"):
            await kanban.get_all_tasks()

    @pytest.mark.asyncio
    async def test_pagination_fetches_all_pages(self, kanban):
        """When total > page size, multiple GET requests are made."""
        page1 = self._mock_search_response([_make_jira_issue("MARC-1")], total=2)
        page2 = self._mock_search_response([_make_jira_issue("MARC-2")], total=2)
        kanban._client = AsyncMock()
        kanban._max_results = 1
        kanban._client.get = AsyncMock(side_effect=[page1, page2])
        tasks = await kanban.get_all_tasks()
        assert len(tasks) == 2
        assert kanban._client.get.call_count == 2


# ---------------------------------------------------------------------------
# get_available_tasks() — proof-of-concept
# ---------------------------------------------------------------------------


class TestGetAvailableTasks:
    """Test that get_available_tasks() filters to unassigned TODO tasks only."""

    @pytest.mark.asyncio
    async def test_returns_only_todo_unassigned(self, kanban):
        """Only TODO + unassigned tasks are returned as available."""
        all_tasks = [
            _make_task(id="1", name="Open", status=TaskStatus.TODO, assigned_to=None),
            _make_task(
                id="2", name="Taken", status=TaskStatus.TODO, assigned_to="agent-1"
            ),
            _make_task(
                id="3", name="WIP", status=TaskStatus.IN_PROGRESS, assigned_to=None
            ),
            _make_task(id="4", name="Done", status=TaskStatus.DONE, assigned_to=None),
        ]
        kanban.get_all_tasks = AsyncMock(return_value=all_tasks)
        available = await kanban.get_available_tasks()
        assert len(available) == 1
        assert available[0].id == "1"

    @pytest.mark.asyncio
    async def test_empty_board_returns_empty_list(self, kanban):
        """Empty task list returns empty available list."""
        kanban.get_all_tasks = AsyncMock(return_value=[])
        available = await kanban.get_available_tasks()
        assert available == []


# ---------------------------------------------------------------------------
# NotImplementedError stubs
# ---------------------------------------------------------------------------


class TestNotImplementedStubs:
    """Every unimplemented method raises NotImplementedError with a useful message."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,args",
        [
            ("get_task_by_id", ("MARC-1",)),
            ("create_task", ({"name": "x"},)),
            ("update_task", ("MARC-1", {})),
            ("assign_task", ("MARC-1", "agent-1")),
            ("move_task_to_column", ("MARC-1", "In Progress")),
            ("add_comment", ("MARC-1", "hello")),
            ("get_project_metrics", ()),
            ("report_blocker", ("MARC-1", "broken")),
            ("update_task_progress", ("MARC-1", {})),
            ("upload_attachment", ("MARC-1", "f.txt", b"data")),
            ("get_attachments", ("MARC-1",)),
            ("download_attachment", ("att-1", "f.txt")),
        ],
    )
    async def test_raises_not_implemented(self, kanban, method, args):
        """Stub method raises NotImplementedError with the issue URL."""
        with pytest.raises(NotImplementedError) as exc_info:
            await getattr(kanban, method)(*args)
        assert "issues/241" in str(exc_info.value)
        assert method in str(exc_info.value)


# ---------------------------------------------------------------------------
# _extract_adf_text helper
# ---------------------------------------------------------------------------


class TestExtractAdfText:
    """Test the Atlassian Document Format text extractor."""

    def test_extracts_text_from_paragraph(self):
        """Text inside a paragraph node is returned."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello"}],
                }
            ],
        }
        assert _extract_adf_text(adf) == "Hello"

    def test_joins_multiple_paragraphs(self):
        """Text from multiple paragraphs is joined with spaces."""
        adf = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "First"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": "Second"}]},
            ],
        }
        result = _extract_adf_text(adf)
        assert "First" in result
        assert "Second" in result

    def test_empty_document_returns_empty_string(self):
        """Empty ADF document produces an empty string."""
        assert _extract_adf_text({"type": "doc", "content": []}) == ""

    def test_deeply_nested_text_extracted(self):
        """Text nested several levels deep is still extracted."""
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": "Deep"}],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        assert "Deep" in _extract_adf_text(adf)


# ---------------------------------------------------------------------------
# _parse_jira_datetime helper
# ---------------------------------------------------------------------------


class TestParseJiraDatetime:
    """Test timestamp parsing for all formats Jira Cloud and Data Center emit."""

    def test_parses_plus0000_format(self):
        """Jira Cloud emits +0000 (no colon); must parse correctly."""
        result = _parse_jira_datetime("2024-01-15T10:30:00.000+0000")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.tzinfo is not None

    def test_parses_z_suffix(self):
        """UTC 'Z' suffix is accepted."""
        result = _parse_jira_datetime("2024-06-01T08:00:00.000Z")
        assert result is not None
        assert result.year == 2024

    def test_parses_colon_offset(self):
        """Offset with colon (+05:30) is accepted."""
        result = _parse_jira_datetime("2024-03-10T14:00:00.000+05:30")
        assert result is not None
        assert result.tzinfo is not None

    def test_returns_none_for_none_input(self):
        """None input returns None without raising."""
        assert _parse_jira_datetime(None) is None

    def test_returns_none_for_empty_string(self):
        """Empty string returns None without raising."""
        assert _parse_jira_datetime("") is None

    def test_returns_none_for_garbage(self):
        """Unparseable string returns None without raising."""
        assert _parse_jira_datetime("not-a-date") is None

    def test_result_is_timezone_aware(self):
        """Parsed datetime is always timezone-aware."""
        result = _parse_jira_datetime("2024-01-15T10:00:00.000+0000")
        assert result is not None
        assert result.tzinfo is not None


# ---------------------------------------------------------------------------
# Bug-fix regression tests
# ---------------------------------------------------------------------------


class TestBugFixes:
    """Regression tests for bugs fixed after initial scaffold."""

    @pytest.mark.asyncio
    async def test_duedate_field_requested_in_search(self, kanban):
        """Bug fix: duedate must be in the fields param so _to_task() receives it."""
        kanban._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"issues": [], "total": 0})
        kanban._client.get = AsyncMock(return_value=mock_resp)

        await kanban.get_all_tasks()

        call_kwargs = kanban._client.get.call_args
        params = call_kwargs[1].get("params", {})
        assert "duedate" in params.get("fields", "")

    @pytest.mark.asyncio
    async def test_project_jql_includes_order_by(self, kanban):
        """Bug fix: project-scoped JQL must include ORDER BY for stable ordering."""
        kanban._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"issues": [], "total": 0})
        kanban._client.get = AsyncMock(return_value=mock_resp)

        await kanban.get_all_tasks()

        call_kwargs = kanban._client.get.call_args
        params = call_kwargs[1].get("params", {})
        assert "ORDER BY" in params.get("jql", "")

    def test_duedate_populated_when_present(self, kanban):
        """Bug fix: _to_task() reads duedate from fields and stores it on Task."""
        issue = _make_jira_issue()
        issue["fields"]["duedate"] = "2024-12-31T00:00:00.000+0000"
        task = kanban._to_task(issue)
        assert task.due_date is not None
        assert task.due_date.year == 2024
        assert task.due_date.month == 12
