"""
Unit tests for progress reporter.

Tests progress event emission during long-running analyses for UI feedback
and monitoring of analysis operations.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, call

import pytest

from src.analysis.helpers.progress import (
    ProgressCallback,
    ProgressEvent,
    ProgressReporter,
)


class TestProgressEvent:
    """Test suite for ProgressEvent dataclass."""

    def test_create_progress_event(self):
        """Test creating a progress event."""
        # Arrange & Act
        event = ProgressEvent(
            operation="analyze_requirements",
            current=45,
            total=100,
            message="Analyzing task 45/100",
            timestamp=datetime.now(timezone.utc),
        )

        # Assert
        assert event.operation == "analyze_requirements"
        assert event.current == 45
        assert event.total == 100
        assert event.message == "Analyzing task 45/100"
        assert event.timestamp.tzinfo == timezone.utc

    def test_progress_event_percentage(self):
        """Test calculating percentage from progress event."""
        # Arrange
        event = ProgressEvent(
            operation="test_op",
            current=45,
            total=100,
            message="Progress",
            timestamp=datetime.now(timezone.utc),
        )

        # Act
        percentage = (event.current / event.total) * 100

        # Assert
        assert percentage == 45.0

    def test_progress_event_completion(self):
        """Test detecting completion from progress event."""
        # Arrange
        event = ProgressEvent(
            operation="test_op",
            current=100,
            total=100,
            message="Complete",
            timestamp=datetime.now(timezone.utc),
        )

        # Act
        is_complete = event.current == event.total

        # Assert
        assert is_complete is True


class TestProgressReporter:
    """Test suite for ProgressReporter."""

    @pytest.fixture
    def mock_callback(self):
        """Create mock progress callback."""
        return AsyncMock()

    @pytest.fixture
    def reporter(self, mock_callback):
        """Create progress reporter with mock callback."""
        return ProgressReporter(callback=mock_callback)

    @pytest.mark.asyncio
    async def test_report_progress_calls_callback(self, reporter, mock_callback):
        """Test that reporting progress calls the callback."""
        # Act
        await reporter.report_progress(
            operation="test_op",
            current=1,
            total=10,
            message="Processing item 1/10",
        )

        # Assert
        assert mock_callback.call_count == 1
        event = mock_callback.call_args[0][0]
        assert isinstance(event, ProgressEvent)
        assert event.operation == "test_op"
        assert event.current == 1
        assert event.total == 10
        assert event.message == "Processing item 1/10"

    @pytest.mark.asyncio
    async def test_report_multiple_progress_updates(self, reporter, mock_callback):
        """Test reporting multiple progress updates."""
        # Act
        for i in range(1, 4):
            await reporter.report_progress(
                operation="batch_process",
                current=i,
                total=3,
                message=f"Processing batch {i}/3",
            )

        # Assert
        assert mock_callback.call_count == 3

        # Verify progression
        calls = mock_callback.call_args_list
        assert calls[0][0][0].current == 1
        assert calls[1][0][0].current == 2
        assert calls[2][0][0].current == 3

    @pytest.mark.asyncio
    async def test_reporter_without_callback(self):
        """Test reporter works without callback (no-op)."""
        # Arrange
        reporter = ProgressReporter()  # No callback

        # Act & Assert - should not raise
        await reporter.report_progress(
            operation="test_op",
            current=1,
            total=10,
            message="Test",
        )

    @pytest.mark.asyncio
    async def test_context_manager_reports_start_and_end(self, mock_callback):
        """Test context manager reports start and completion."""
        # Arrange
        reporter = ProgressReporter(callback=mock_callback)

        # Act
        async with reporter.operation("test_operation", total=100) as progress:
            # Simulate some work
            await progress.update(50, "Halfway done")

        # Assert
        # Should have: start (0/100), update (50/100), end (100/100)
        assert mock_callback.call_count == 3

        calls = mock_callback.call_args_list
        # Start
        assert calls[0][0][0].current == 0
        assert calls[0][0][0].total == 100
        assert calls[0][0][0].operation == "test_operation"

        # Update
        assert calls[1][0][0].current == 50
        assert calls[1][0][0].message == "Halfway done"

        # End
        assert calls[2][0][0].current == 100
        assert calls[2][0][0].total == 100

    @pytest.mark.asyncio
    async def test_context_manager_reports_completion_on_exception(self, mock_callback):
        """Test context manager reports completion even if exception occurs."""
        # Arrange
        reporter = ProgressReporter(callback=mock_callback)

        # Act
        with pytest.raises(ValueError):
            async with reporter.operation("failing_op", total=100) as progress:
                await progress.update(30, "Working...")
                raise ValueError("Test error")

        # Assert
        # Should still report start, update, and completion
        assert mock_callback.call_count == 3
        # Verify completion was reported
        assert mock_callback.call_args_list[2][0][0].current == 100

    @pytest.mark.asyncio
    async def test_auto_increment_progress(self, mock_callback):
        """Test auto-incrementing progress counter."""
        # Arrange
        reporter = ProgressReporter(callback=mock_callback)

        # Act
        async with reporter.operation("auto_increment", total=5) as progress:
            for i in range(3):
                await progress.increment(f"Step {i + 1}")

        # Assert
        # Start (0/5), increment (1/5), increment (2/5), increment (3/5), end (5/5)
        assert mock_callback.call_count == 5

        calls = mock_callback.call_args_list
        assert calls[1][0][0].current == 1  # First increment
        assert calls[2][0][0].current == 2  # Second increment
        assert calls[3][0][0].current == 3  # Third increment

    @pytest.mark.asyncio
    async def test_nested_operations(self, mock_callback):
        """Test nested progress operations."""
        # Arrange
        reporter = ProgressReporter(callback=mock_callback)

        # Act
        async with reporter.operation("outer", total=2) as outer:
            await outer.update(1, "Starting subtask")

            # Nested operation
            async with reporter.operation("inner", total=3) as inner:
                await inner.increment("Inner step 1")
                await inner.increment("Inner step 2")

            await outer.update(2, "Completed")

        # Assert
        # Verify events for both operations were reported
        events = [call[0][0] for call in mock_callback.call_args_list]

        outer_events = [e for e in events if e.operation == "outer"]
        inner_events = [e for e in events if e.operation == "inner"]

        assert len(outer_events) >= 3  # start, update, update, end
        assert len(inner_events) >= 2  # start, increment, increment, end

    @pytest.mark.asyncio
    async def test_progress_with_no_total(self, mock_callback):
        """Test progress reporting for indeterminate operations."""
        # Arrange
        reporter = ProgressReporter(callback=mock_callback)

        # Act
        async with reporter.operation("indeterminate", total=None) as progress:
            await progress.update(message="Processing...")
            await progress.update(message="Still processing...")

        # Assert
        events = [call[0][0] for call in mock_callback.call_args_list]

        # All events should have total=None
        assert all(e.total is None for e in events)
        assert events[1].message == "Processing..."
        assert events[2].message == "Still processing..."


class TestProgressCallbackIntegration:
    """Test integration with different callback patterns."""

    @pytest.mark.asyncio
    async def test_print_callback(self, capsys):
        """Test using print as a callback."""

        # Arrange
        async def print_callback(event: ProgressEvent):
            print(f"{event.operation}: {event.message}")

        reporter = ProgressReporter(callback=print_callback)

        # Act
        await reporter.report_progress(
            operation="test", current=1, total=10, message="Testing"
        )

        # Assert
        captured = capsys.readouterr()
        assert "test: Testing" in captured.out

    @pytest.mark.asyncio
    async def test_logging_callback(self):
        """Test using logger as a callback."""
        # Arrange
        mock_logger = Mock()

        async def log_callback(event: ProgressEvent):
            percentage = (event.current / event.total * 100) if event.total else 0
            mock_logger.info(f"{event.operation}: {percentage:.1f}% - {event.message}")

        reporter = ProgressReporter(callback=log_callback)

        # Act
        await reporter.report_progress(
            operation="logging_test",
            current=45,
            total=100,
            message="Processing",
        )

        # Assert
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "logging_test: 45.0%" in call_args
        assert "Processing" in call_args

    @pytest.mark.asyncio
    async def test_state_tracking_callback(self):
        """Test callback that tracks state across updates."""
        # Arrange
        state = {"events": []}

        async def state_callback(event: ProgressEvent):
            state["events"].append(event)

        reporter = ProgressReporter(callback=state_callback)

        # Act
        async with reporter.operation("stateful", total=3) as progress:
            await progress.increment("Step 1")
            await progress.increment("Step 2")
            await progress.increment("Step 3")

        # Assert
        assert len(state["events"]) == 5  # start + 3 increments + end

        # Verify final state
        final_event = state["events"][-1]
        assert final_event.current == 3
        assert final_event.total == 3
