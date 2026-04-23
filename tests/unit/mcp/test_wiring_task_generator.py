"""
Unit tests for _generate_wiring_tasks in decomposer.

Verifies that post-decomposition wiring tasks are generated when
provides/requires pairs are detected between subtasks.
"""

import pytest

pytestmark = pytest.mark.unit


def _make_subtask(
    idx: int,
    name: str,
    provides: str | None = None,
    requires: str | None = None,
    file_artifacts: list[str] | None = None,
) -> dict:
    """Build a minimal subtask dict as the decomposer produces."""
    return {
        "name": name,
        "description": f"desc for {name}",
        "estimated_hours": 1.0,
        "dependencies": [],
        "dependency_types": [],
        "file_artifacts": file_artifacts or [],
        "output_paths": [],
        "provides": provides,
        "requires": requires,
        "_idx": idx,  # index used by _generate_wiring_tasks to build dep IDs
    }


class TestGenerateWiringTasks:
    """_generate_wiring_tasks produces wiring tasks for provides/requires pairs."""

    def _call(self, subtasks: list[dict], parent_task_id: str = "pt-1") -> list[dict]:
        from src.marcus_mcp.coordinator.decomposer import _generate_wiring_tasks

        return _generate_wiring_tasks(subtasks, parent_task_id)

    def test_no_wiring_when_no_provides_or_requires(self) -> None:
        """If no subtask declares provides/requires, return empty list."""
        subtasks = [
            _make_subtask(0, "Task A"),
            _make_subtask(1, "Task B"),
        ]
        result = self._call(subtasks)
        assert result == []

    def test_no_wiring_when_provides_but_no_requires(self) -> None:
        """Provider alone, no consumer → no wiring needed."""
        subtasks = [
            _make_subtask(0, "Build service", provides="WeatherService interface"),
            _make_subtask(1, "Build util", provides="Utility helpers"),
        ]
        result = self._call(subtasks)
        assert result == []

    def test_wiring_task_created_for_provides_requires_pair(self) -> None:
        """One provider + one consumer → one wiring task."""
        subtasks = [
            _make_subtask(0, "Build WeatherService", provides="WeatherService"),
            _make_subtask(1, "Build Dashboard", requires="WeatherService"),
        ]
        result = self._call(subtasks, "pt-1")
        assert len(result) == 1
        wiring = result[0]
        assert "Wire" in wiring["name"]
        assert "WeatherService" in wiring["name"]
        assert "Dashboard" in wiring["name"]

    def test_wiring_task_has_hard_deps_on_provider_and_consumer(self) -> None:
        """Wiring task must depend on both provider subtask ID and consumer subtask ID."""
        subtasks = [
            _make_subtask(0, "Build WeatherService", provides="WeatherService"),
            _make_subtask(1, "Build Dashboard", requires="WeatherService"),
        ]
        result = self._call(subtasks, "pt-1")
        wiring = result[0]
        # Dependencies reference the subtask IDs (pt-1_sub_1 and pt-1_sub_2, 1-indexed)
        assert "pt-1_sub_1" in wiring["dependencies"]
        assert "pt-1_sub_2" in wiring["dependencies"]
        assert all(dt == "hard" for dt in wiring["dependency_types"])

    def test_wiring_task_is_last_in_chain(self) -> None:
        """Wiring task fields: estimated_hours, description, provides=None."""
        subtasks = [
            _make_subtask(0, "Build WeatherService", provides="WeatherService"),
            _make_subtask(1, "Build Dashboard", requires="WeatherService"),
        ]
        result = self._call(subtasks, "pt-1")
        wiring = result[0]
        assert wiring["estimated_hours"] > 0
        assert wiring.get("provides") is None
        assert "description" in wiring

    def test_multiple_consumers_get_separate_wiring_tasks(self) -> None:
        """One provider + two consumers → two wiring tasks."""
        subtasks = [
            _make_subtask(0, "Build WeatherService", provides="WeatherService"),
            _make_subtask(1, "Build Dashboard", requires="WeatherService"),
            _make_subtask(2, "Build Widget", requires="WeatherService"),
        ]
        result = self._call(subtasks, "pt-1")
        assert len(result) == 2

    def test_wiring_task_output_paths_from_consumer_file_artifacts(self) -> None:
        """Wiring task inherits output_paths from the consumer's file_artifacts."""
        subtasks = [
            _make_subtask(
                0,
                "Build WeatherService",
                provides="WeatherService",
                file_artifacts=["src/services/weather.ts"],
            ),
            _make_subtask(
                1,
                "Build Dashboard",
                requires="WeatherService",
                file_artifacts=["src/pages/Dashboard.tsx"],
            ),
        ]
        result = self._call(subtasks, "pt-1")
        wiring = result[0]
        # Output paths should reference the consumer's files (where wiring happens)
        assert "src/pages/Dashboard.tsx" in wiring.get("output_paths", [])

    def test_subtasks_without_provides_are_not_providers(self) -> None:
        """Subtasks with requires but no matching provider are ignored."""
        subtasks = [
            _make_subtask(0, "Build Dashboard", requires="SomeUnprovidedService"),
        ]
        result = self._call(subtasks, "pt-1")
        assert result == []
