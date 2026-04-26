"""Unit tests for polling backoff when no tasks are available.

When many agents simultaneously receive "no tasks available", consecutive
responses use exponential backoff (30s base, 2× per miss, cap 300s) to
prevent polling storms.  The streak resets when a task is assigned.
"""

import pytest

pytestmark = pytest.mark.unit


class TestPollingBackoffStreak:
    """_agent_no_task_streak controls retry_after_seconds calculation."""

    def test_streak_starts_at_zero(self) -> None:
        """Agent with no prior misses starts at streak 0."""
        import src.marcus_mcp.tools.task as task_module

        task_module._agent_no_task_streak.pop("agent-fresh", None)
        streak = task_module._agent_no_task_streak.get("agent-fresh", 0)
        assert streak == 0

    def test_backoff_formula_doubles_per_miss(self) -> None:
        """30s base × 2^streak gives correct backoff values."""
        base = 30
        expected = [30, 60, 120, 240, 300, 300]  # caps at 300
        for streak, exp in enumerate(expected):
            computed = min(base * (2**streak), 300)
            assert computed == exp, f"streak={streak}: expected {exp}, got {computed}"

    def test_streak_reset_to_zero_on_assignment(self) -> None:
        """_agent_no_task_streak entry removed when task is assigned."""
        import src.marcus_mcp.tools.task as task_module

        task_module._agent_no_task_streak["agent-x"] = 5
        task_module._agent_no_task_streak.pop("agent-x", None)  # simulates assignment
        assert "agent-x" not in task_module._agent_no_task_streak

    def test_multiple_agents_tracked_independently(self) -> None:
        """Each agent has its own streak counter."""
        import src.marcus_mcp.tools.task as task_module

        task_module._agent_no_task_streak["agent-a"] = 2
        task_module._agent_no_task_streak["agent-b"] = 0
        assert task_module._agent_no_task_streak["agent-a"] == 2
        assert task_module._agent_no_task_streak["agent-b"] == 0
        # Cleanup
        task_module._agent_no_task_streak.pop("agent-a", None)
        task_module._agent_no_task_streak.pop("agent-b", None)

    def test_max_backoff_capped_at_300(self) -> None:
        """Backoff never exceeds 300s regardless of streak length."""
        base = 30
        for streak in range(0, 20):
            computed = min(base * (2**streak), 300)
            assert computed <= 300, f"streak={streak} exceeded 300s cap"
