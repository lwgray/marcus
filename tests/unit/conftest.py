"""
Common test fixtures for unit tests using real implementations.
"""

import inspect
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional, Union
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.context import Context
from src.marcus_mcp.server import MarcusServer


def make_analyze_mock(
    side_effect: Optional[Callable[..., Union[str, Awaitable[str]]]] = None,
    return_value: Optional[str] = None,
) -> AsyncMock:
    """Build an AsyncMock that satisfies :class:`LLMAnalyzeClient`.

    The Protocol defined in ``src.ai.providers.protocols`` exposes the
    ``async def analyze(prompt, context, *, operation)`` signature.
    Production code may add new keyword arguments to ``analyze`` over
    time; tests historically broke whenever this happened because each
    bespoke mock had a pinned signature.

    This helper centralizes the workaround: it returns an AsyncMock
    whose ``side_effect`` absorbs any extra kwargs (``operation`` and
    anything added later) and forwards just ``(prompt, context)`` to
    the caller-provided function. Test authors keep their fakes
    minimal and don't need to chase signature evolution per-mock.

    Parameters
    ----------
    side_effect : callable, optional
        Sync or async function ``(prompt, context) -> str``. When
        provided, the mock invokes it (awaiting if needed) and returns
        the result. Extra kwargs are silently discarded.
    return_value : str, optional
        Constant return value. Mutually exclusive with ``side_effect``
        — pass one or the other.

    Returns
    -------
    AsyncMock
        Configured async mock. Wire onto a fake LLM client with
        ``client.analyze = make_analyze_mock(side_effect=fn)``.

    Examples
    --------
    >>> mock = make_analyze_mock(side_effect=lambda p, c: f"echo:{p}")
    >>> # Internally Marcus calls: await mock(prompt="hi", context=ctx,
    >>> #                                       operation="decompose_prd")
    >>> # The ``operation`` kwarg is dropped before reaching ``side_effect``.
    """
    if side_effect is not None and return_value is not None:
        raise ValueError("Pass either side_effect or return_value, not both")

    if side_effect is not None:

        async def _absorb_kwargs(prompt: Any, context: Any, **_kwargs: Any) -> str:
            result = side_effect(prompt, context)
            if inspect.isawaitable(result):
                return await result
            return result

        return AsyncMock(side_effect=_absorb_kwargs)

    return AsyncMock(return_value=return_value or "")


# Domain-specific fixtures are now imported in the root conftest.py


@pytest.fixture
def test_env_vars(monkeypatch):
    """Set up test environment variables with real values."""
    monkeypatch.setenv("KANBAN_PROVIDER", "planka")
    monkeypatch.setenv("GITHUB_OWNER", "test-owner")
    monkeypatch.setenv("GITHUB_REPO", "test-repo")
    monkeypatch.setenv("MARCUS_TEST_MODE", "true")
    monkeypatch.setenv("LOG_LEVEL", "INFO")


@pytest.fixture
def test_marcus_server(test_env_vars):
    """Create a Marcus server instance for testing.

    Uses real implementations but with test configuration.
    For tests requiring external services, use @pytest.mark.integration
    """
    server = MarcusServer()
    # Configure for testing but use real implementations
    server.test_mode = True
    # Don't start background services in unit tests.
    # Suppress assignment_monitor AND events to prevent
    # asyncio.create_task calls that outlive the test's event
    # loop and produce "Task was destroyed but it is pending"
    # warnings at teardown. The events system is only needed for
    # integration tests that verify end-to-end event flow.
    server.assignment_monitor = None
    server.events = None
    return server


@pytest.fixture
def test_context():
    """Create a real test context for Marcus operations."""
    context = Context()
    context.test_mode = True
    context.project_name = "Unit Test Project"
    return context
