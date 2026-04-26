"""
Unit tests for clear_validation_retry and the lease-recovery integration.

When a task lease expires and the task is recovered to a new agent, the
validation retry counter must be cleared so the incoming agent is not
penalised for the previous agent's failures.
"""

import pytest

pytestmark = pytest.mark.unit


class TestClearValidationRetry:
    """clear_validation_retry resets retry history for a given task."""

    def test_clears_existing_task_history(self) -> None:
        """After recording an attempt, clear_validation_retry wipes it."""
        from unittest.mock import MagicMock, patch

        mock_tracker = MagicMock()

        with patch("src.marcus_mcp.tools.task._retry_tracker", mock_tracker):
            from src.marcus_mcp.tools.task import clear_validation_retry

            clear_validation_retry("task-abc")

        mock_tracker.clear_task.assert_called_once_with("task-abc")

    def test_no_op_when_tracker_not_initialised(self) -> None:
        """Before the validation system starts, clear_validation_retry is a no-op."""
        from unittest.mock import patch

        with patch("src.marcus_mcp.tools.task._retry_tracker", None):
            from src.marcus_mcp.tools.task import clear_validation_retry

            # Must not raise
            clear_validation_retry("task-xyz")

    def test_different_task_ids_cleared_independently(self) -> None:
        """Each task ID gets its own clear call."""
        from unittest.mock import MagicMock, patch

        mock_tracker = MagicMock()

        with patch("src.marcus_mcp.tools.task._retry_tracker", mock_tracker):
            from src.marcus_mcp.tools.task import clear_validation_retry

            clear_validation_retry("task-1")
            clear_validation_retry("task-2")

        assert mock_tracker.clear_task.call_count == 2
        calls = [c.args[0] for c in mock_tracker.clear_task.call_args_list]
        assert "task-1" in calls
        assert "task-2" in calls


class TestNoneStringFiltering:
    """_generate_wiring_tasks must not treat literal string 'None' as a provider."""

    def _call(self, subtasks: list[dict], parent_task_id: str = "pt-1") -> list[dict]:
        from src.marcus_mcp.coordinator.decomposer import _generate_wiring_tasks

        return _generate_wiring_tasks(subtasks, parent_task_id)

    def test_string_none_provides_does_not_create_wiring_task(self) -> None:
        """LLMs sometimes emit 'None' (string) for optional fields — ignore it."""
        subtasks = [
            {
                "name": "Task A",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": "None",  # LLM literal string
                "requires": None,
                "_idx": 0,
            },
            {
                "name": "Task B",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": None,
                "requires": "None",  # LLM literal string
                "_idx": 1,
            },
        ]
        result = self._call(subtasks)
        assert result == [], "Should not generate wiring tasks for 'None' string values"

    def test_empty_string_provides_does_not_create_wiring_task(self) -> None:
        """Empty string provides/requires should also be ignored."""
        subtasks = [
            {
                "name": "Task A",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": "",
                "requires": None,
                "_idx": 0,
            },
            {
                "name": "Task B",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": None,
                "requires": "",
                "_idx": 1,
            },
        ]
        result = self._call(subtasks)
        assert result == []

    def test_real_provides_still_generates_wiring_task(self) -> None:
        """Non-None, non-empty provides/requires still produce wiring tasks."""
        subtasks = [
            {
                "name": "Build WeatherService",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": "WeatherService API",
                "requires": None,
                "_idx": 0,
            },
            {
                "name": "Build Dashboard",
                "description": "desc",
                "estimated_hours": 1.0,
                "dependencies": [],
                "dependency_types": [],
                "file_artifacts": [],
                "output_paths": [],
                "provides": None,
                "requires": "WeatherService API",
                "_idx": 1,
            },
        ]
        result = self._call(subtasks)
        assert len(result) == 1
        assert "WeatherService" in result[0]["name"]
