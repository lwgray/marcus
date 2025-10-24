"""
Unit tests for learned task duration functionality.

Tests the median-based learning loop where AdvancedPRDParser queries
the Memory system for historical task completion times.
"""

from unittest.mock import Mock

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.core.memory import TaskPattern


class TestLearnedDurations:
    """Test suite for learned task duration functionality."""

    @pytest.fixture
    def mock_memory_with_data(self):
        """Create mock memory system with learned task patterns."""
        memory = Mock()

        # Mock get_median_duration_by_type to return learned values
        learned_durations = {
            "design": 0.12,  # 7.2 minutes
            "implement": 0.15,  # 9 minutes
            "test": 0.10,  # 6 minutes
        }
        memory.get_median_duration_by_type = Mock(
            side_effect=lambda task_type: learned_durations.get(task_type)
        )
        return memory

    @pytest.fixture
    def mock_memory_without_data(self):
        """Create mock memory system without learned data."""
        memory = Mock()
        memory.get_median_duration_by_type = Mock(return_value=None)
        return memory

    def test_parser_uses_learned_duration(self, mock_memory_with_data):
        """Test parser queries memory and uses learned durations."""
        parser = AdvancedPRDParser(memory=mock_memory_with_data)

        # Query for design tasks
        minutes = parser._get_learned_task_duration("design", default_minutes=6.0)

        # Should use learned value (7.2 minutes) not default (6.0)
        assert minutes == pytest.approx(7.2, abs=0.1)

        # Verify memory was queried
        mock_memory_with_data.get_median_duration_by_type.assert_called_with("design")

    def test_parser_uses_learned_duration_for_implement(self, mock_memory_with_data):
        """Test parser uses learned duration for implement tasks."""
        parser = AdvancedPRDParser(memory=mock_memory_with_data)

        minutes = parser._get_learned_task_duration("implement", default_minutes=8.0)

        # Should use learned value (9.0 minutes) not default (8.0)
        assert minutes == pytest.approx(9.0, abs=0.1)

    def test_parser_fallback_when_no_learned_data(self, mock_memory_without_data):
        """Test parser falls back to default when no learned data."""
        parser = AdvancedPRDParser(memory=mock_memory_without_data)

        minutes = parser._get_learned_task_duration("design", default_minutes=6.0)

        # Should use default since no learned data
        assert minutes == pytest.approx(6.0, abs=0.01)

        # Verify memory was queried
        mock_memory_without_data.get_median_duration_by_type.assert_called_with(
            "design"
        )

    def test_parser_fallback_when_no_memory_system(self):
        """Test parser works without memory system (fallback mode)."""
        parser = AdvancedPRDParser(memory=None)

        minutes = parser._get_learned_task_duration("design", default_minutes=6.0)

        # Should use default since no memory system
        assert minutes == pytest.approx(6.0, abs=0.01)

    def test_parser_fallback_on_memory_error(self, mock_memory_with_data):
        """Test parser handles memory query errors gracefully."""
        # Make memory raise an exception
        mock_memory_with_data.get_median_duration_by_type = Mock(
            side_effect=Exception("Database error")
        )

        parser = AdvancedPRDParser(memory=mock_memory_with_data)

        # Should fall back to default on error
        minutes = parser._get_learned_task_duration("design", default_minutes=6.0)
        assert minutes == pytest.approx(6.0, abs=0.01)

    def test_parser_handles_all_task_types(self, mock_memory_with_data):
        """Test parser can query learned durations for all task types."""
        parser = AdvancedPRDParser(memory=mock_memory_with_data)

        # Test all common task types
        design_min = parser._get_learned_task_duration("design", default_minutes=6.0)
        implement_min = parser._get_learned_task_duration(
            "implement", default_minutes=8.0
        )
        test_min = parser._get_learned_task_duration("test", default_minutes=6.0)

        # All should return learned values
        assert design_min == pytest.approx(7.2, abs=0.1)
        assert implement_min == pytest.approx(9.0, abs=0.1)
        assert test_min == pytest.approx(6.0, abs=0.1)

    def test_parser_handles_unknown_task_types(self, mock_memory_with_data):
        """Test parser handles unknown task types with default."""
        parser = AdvancedPRDParser(memory=mock_memory_with_data)

        # Query for unknown task type
        minutes = parser._get_learned_task_duration("nonexistent", default_minutes=10.0)

        # Should use default since task type not in learned data
        assert minutes == pytest.approx(10.0, abs=0.01)


class TestTaskPatternMedian:
    """Test TaskPattern median calculation."""

    def test_median_with_odd_number_of_samples(self):
        """Test median calculation with odd number of samples."""
        pattern = TaskPattern(
            pattern_type="design",
            task_labels=["design"],
            recent_durations=[0.1, 0.15, 0.12],  # Median = 0.12
            success_rate=1.0,
            common_blockers=[],
            prerequisites=[],
            best_agents=[],
        )

        assert pattern.median_duration == pytest.approx(0.12, abs=0.001)

    def test_median_with_even_number_of_samples(self):
        """Test median calculation with even number of samples."""
        pattern = TaskPattern(
            pattern_type="implement",
            task_labels=["implement"],
            recent_durations=[0.1, 0.2, 0.15, 0.25],  # Median = (0.15 + 0.2) / 2
            success_rate=1.0,
            common_blockers=[],
            prerequisites=[],
            best_agents=[],
        )

        assert pattern.median_duration == pytest.approx(0.175, abs=0.001)

    def test_median_with_single_sample(self):
        """Test median with only one sample."""
        pattern = TaskPattern(
            pattern_type="test",
            task_labels=["test"],
            recent_durations=[0.1],
            success_rate=1.0,
            common_blockers=[],
            prerequisites=[],
            best_agents=[],
        )

        assert pattern.median_duration == pytest.approx(0.1, abs=0.001)

    def test_median_with_empty_samples(self):
        """Test median returns 0.0 when no samples."""
        pattern = TaskPattern(
            pattern_type="design",
            task_labels=["design"],
            recent_durations=[],
            success_rate=0.0,
            common_blockers=[],
            prerequisites=[],
            best_agents=[],
        )

        assert pattern.median_duration == 0.0

    def test_median_robust_to_outliers(self):
        """Test median is robust to outlier values."""
        # With outlier (100.0 hours = task waiting for user)
        pattern = TaskPattern(
            pattern_type="design",
            task_labels=["design"],
            recent_durations=[0.1, 0.12, 0.11, 100.0],  # Median = (0.11 + 0.12) / 2
            success_rate=1.0,
            common_blockers=[],
            prerequisites=[],
            best_agents=[],
        )

        # Median is not affected by the 100.0 outlier
        assert pattern.median_duration == pytest.approx(0.115, abs=0.001)

        # Compare to average which would be skewed
        assert pattern.average_duration == pytest.approx(25.0825, abs=0.1)
        assert pattern.median_duration < pattern.average_duration
