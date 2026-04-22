"""
Unit tests for spec coverage check in task decomposition.

Dashboard-v88 post-mortem: Marcus's task decomposer silently dropped the
"5-day forecast" feature from the project spec. No task was generated for
it, so no agent knew it was in scope. UD1 even wrote .forecast-card CSS
as a hint, but with no task, no agent built the component.

Fix: after task decomposition, run a spec coverage check. Extract feature
phrases from the description, verify each has at least one task covering it,
and synthesize gap tasks for any uncovered features before agents start.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.spec_coverage import (
    check_spec_coverage,
    extract_spec_features,
    find_uncovered_features,
)

pytestmark = pytest.mark.unit


def _make_task(
    name: str, description: str = "", labels: list[str] | None = None
) -> Task:
    """Build a minimal Task for testing."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return Task(
        id=f"task_{name.lower().replace(' ', '_')[:20]}",
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        labels=labels or [],
        dependencies=[],
        estimated_hours=2.0,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
    )


NIMBUS_SPEC = """
Build a weather dashboard named Nimbus with:
- Animated digital clock with live seconds using flip animation
- Weather panel showing current temperature, feels like, humidity, wind speed, UV index
- 5-day weather forecast with icons from lucide-react
- Dark glassmorphism theme with gradient card backgrounds
- Smooth fade-in animations on page load
- Hardcoded realistic NYC weather data (no external API calls)
"""

NIMBUS_TASKS_MISSING_FORECAST = [
    _make_task("Tech Foundation Setup", "Set up Vite + React + Tailwind"),
    _make_task("Design System Setup", "glassmorphism theme, CSS tokens"),
    _make_task("Shared Component Foundation", "Card component with animations"),
    _make_task("Design Real-Time Clock", "design the AnimatedClock component"),
    _make_task("Implement Animated Digital Clock", "flip animation, live seconds"),
    _make_task("Implement WeatherPanel", "current conditions, 5 metrics"),
    _make_task("Integration Verification", "smoke test all components"),
    _make_task("README Documentation", "usage docs"),
]

NIMBUS_TASKS_COMPLETE = NIMBUS_TASKS_MISSING_FORECAST + [
    _make_task("Implement 5-Day Forecast", "forecast cards with lucide icons"),
]


class TestExtractSpecFeatures:
    """extract_spec_features pulls feature phrases from a project description."""

    @pytest.mark.asyncio
    async def test_returns_list_of_features(self) -> None:
        """LLM returns JSON list of features."""
        mock_llm_response = (
            '["animated digital clock", "weather panel", '
            '"5-day forecast", "glassmorphism theme", "fade-in animations"]'
        )
        with patch(
            "src.integrations.spec_coverage._llm_extract_features",
            new_callable=AsyncMock,
            return_value=mock_llm_response,
        ):
            features = await extract_spec_features(NIMBUS_SPEC)

        assert isinstance(features, list)
        assert len(features) >= 3
        assert any("forecast" in f.lower() for f in features)
        assert any("clock" in f.lower() for f in features)

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_llm_failure(self) -> None:
        """LLM call failure returns empty list (non-fatal)."""
        with patch(
            "src.integrations.spec_coverage._llm_extract_features",
            new_callable=AsyncMock,
            side_effect=Exception("LLM timeout"),
        ):
            features = await extract_spec_features(NIMBUS_SPEC)

        assert features == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_malformed_json(self) -> None:
        """Malformed LLM JSON returns empty list (non-fatal)."""
        with patch(
            "src.integrations.spec_coverage._llm_extract_features",
            new_callable=AsyncMock,
            return_value="not valid json at all",
        ):
            features = await extract_spec_features(NIMBUS_SPEC)

        assert features == []


class TestFindUncoveredFeatures:
    """find_uncovered_features compares feature list against task list."""

    def test_finds_missing_forecast_feature(self) -> None:
        """5-day forecast in spec but not in tasks → flagged as uncovered."""
        features = [
            "animated digital clock",
            "weather panel",
            "5-day forecast",
            "glassmorphism theme",
        ]
        uncovered = find_uncovered_features(
            features=features,
            tasks=NIMBUS_TASKS_MISSING_FORECAST,
        )

        assert len(uncovered) >= 1
        assert any("forecast" in f.lower() for f in uncovered)

    def test_no_uncovered_when_all_features_present(self) -> None:
        """All features have matching tasks → returns empty list."""
        features = [
            "animated digital clock",
            "weather panel",
            "5-day forecast",
        ]
        uncovered = find_uncovered_features(
            features=features,
            tasks=NIMBUS_TASKS_COMPLETE,
        )

        assert uncovered == []

    def test_coverage_is_case_insensitive(self) -> None:
        """Feature matching ignores case."""
        features = ["Animated Digital Clock", "WEATHER PANEL"]
        uncovered = find_uncovered_features(
            features=features,
            tasks=NIMBUS_TASKS_MISSING_FORECAST,
        )

        assert uncovered == []

    def test_partial_word_match_counts_as_covered(self) -> None:
        """'clock' in feature matches 'AnimatedClock' in task name."""
        features = ["clock animation"]
        uncovered = find_uncovered_features(
            features=features,
            tasks=NIMBUS_TASKS_MISSING_FORECAST,
        )

        assert uncovered == []

    def test_returns_empty_when_no_features(self) -> None:
        """No features extracted → nothing to check."""
        uncovered = find_uncovered_features(
            features=[],
            tasks=NIMBUS_TASKS_MISSING_FORECAST,
        )

        assert uncovered == []

    def test_checks_task_description_not_just_name(self) -> None:
        """Feature word in task description counts as covered."""
        tasks = [
            _make_task(
                "Backend Services",
                description="REST endpoints including forecast data endpoint",
            )
        ]
        uncovered = find_uncovered_features(
            features=["forecast"],
            tasks=tasks,
        )

        assert uncovered == []


class TestCheckSpecCoverage:
    """check_spec_coverage orchestrates extraction + gap task generation."""

    @pytest.mark.asyncio
    async def test_returns_gap_task_for_missing_forecast(self) -> None:
        """Missing 5-day forecast → gap task synthesized."""
        extracted_features = [
            "animated digital clock",
            "weather panel",
            "5-day forecast",
        ]
        with patch(
            "src.integrations.spec_coverage.extract_spec_features",
            new_callable=AsyncMock,
            return_value=extracted_features,
        ):
            gap_tasks = await check_spec_coverage(
                description=NIMBUS_SPEC,
                tasks=NIMBUS_TASKS_MISSING_FORECAST,
                project_name="Nimbus",
            )

        assert len(gap_tasks) >= 1
        gap_names = [t.name.lower() for t in gap_tasks]
        assert any("forecast" in name for name in gap_names)

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_covered(self) -> None:
        """All features covered → no gap tasks."""
        extracted_features = [
            "animated digital clock",
            "weather panel",
            "5-day forecast",
        ]
        with patch(
            "src.integrations.spec_coverage.extract_spec_features",
            new_callable=AsyncMock,
            return_value=extracted_features,
        ):
            gap_tasks = await check_spec_coverage(
                description=NIMBUS_SPEC,
                tasks=NIMBUS_TASKS_COMPLETE,
                project_name="Nimbus",
            )

        assert gap_tasks == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_llm_failure(self) -> None:
        """LLM failure → no gap tasks, no crash (non-fatal)."""
        with patch(
            "src.integrations.spec_coverage.extract_spec_features",
            new_callable=AsyncMock,
            return_value=[],  # empty on LLM failure
        ):
            gap_tasks = await check_spec_coverage(
                description=NIMBUS_SPEC,
                tasks=NIMBUS_TASKS_MISSING_FORECAST,
                project_name="Nimbus",
            )

        assert gap_tasks == []

    @pytest.mark.asyncio
    async def test_gap_task_has_correct_labels(self) -> None:
        """Gap tasks are labeled spec_gap so Cato/agents recognize them."""
        with patch(
            "src.integrations.spec_coverage.extract_spec_features",
            new_callable=AsyncMock,
            return_value=["5-day forecast"],
        ):
            gap_tasks = await check_spec_coverage(
                description=NIMBUS_SPEC,
                tasks=NIMBUS_TASKS_MISSING_FORECAST,
                project_name="Nimbus",
            )

        assert len(gap_tasks) >= 1
        gap_task = gap_tasks[0]
        assert "spec_gap" in gap_task.labels

    @pytest.mark.asyncio
    async def test_gap_task_description_mentions_spec_source(self) -> None:
        """Gap task description explains it was found by spec coverage check."""
        with patch(
            "src.integrations.spec_coverage.extract_spec_features",
            new_callable=AsyncMock,
            return_value=["5-day forecast"],
        ):
            gap_tasks = await check_spec_coverage(
                description=NIMBUS_SPEC,
                tasks=NIMBUS_TASKS_MISSING_FORECAST,
                project_name="Nimbus",
            )

        assert len(gap_tasks) >= 1
        desc = gap_tasks[0].description.lower()
        assert "spec" in desc or "coverage" in desc or "missing" in desc
