"""
Unit tests for enhanced MLflow tracker metrics.

Tests the new metrics methods added for experiment comparison:
- Code quality metrics
- Dependency metrics
- Agent idle time
- Coordination overhead
- Resource usage
- Throughput
- Parallel efficiency
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.experiments.mlflow_tracker import MarcusExperiment


class TestCodeQualityMetrics:
    """Test code quality metric logging."""

    @pytest.fixture
    def experiment(self):
        """Create experiment with temp tracking URI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp = MarcusExperiment(
                experiment_name="test_code_quality",
                tracking_uri=tmpdir,
            )
            yield exp

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_code_quality_all_metrics(self, mock_mlflow, experiment):
        """Test logging all code quality metrics."""
        # Arrange
        test_coverage = 85.5
        linting_errors = 3
        type_errors = 1
        complexity = 4.2

        # Act
        experiment.log_code_quality(
            test_coverage=test_coverage,
            linting_errors=linting_errors,
            type_errors=type_errors,
            cyclomatic_complexity=complexity,
        )

        # Assert
        mock_mlflow.log_metrics.assert_called_once()
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["test_coverage"] == test_coverage
        assert metrics["linting_errors"] == linting_errors
        assert metrics["type_errors"] == type_errors
        assert metrics["cyclomatic_complexity"] == complexity

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_code_quality_without_complexity(self, mock_mlflow, experiment):
        """Test logging code quality without cyclomatic complexity."""
        # Act
        experiment.log_code_quality(
            test_coverage=90.0,
            linting_errors=0,
            type_errors=0,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert "cyclomatic_complexity" not in metrics
        assert metrics["test_coverage"] == 90.0


class TestDependencyMetrics:
    """Test dependency structure metrics."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_deps", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_dependency_metrics(self, mock_mlflow, experiment):
        """Test logging dependency structure metrics."""
        # Act
        experiment.log_dependency_metrics(
            critical_path_length=5,
            avg_dependency_depth=2.8,
            parallelizable_fraction=0.65,
            max_parallel_tasks=8,
        )

        # Assert
        mock_mlflow.log_metrics.assert_called_once()
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["critical_path_length"] == 5
        assert metrics["avg_dependency_depth"] == 2.8
        assert metrics["parallelizable_fraction"] == 0.65
        assert metrics["max_parallel_tasks"] == 8


class TestAgentIdleTime:
    """Test agent idle time tracking."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_idle", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_agent_idle_time(self, mock_mlflow, experiment):
        """Test logging agent idle time."""
        # Act
        experiment.log_agent_idle_time(
            agent_id="agent_123",
            idle_seconds=45.5,
        )

        # Assert
        mock_mlflow.log_metric.assert_called_once_with(
            "agent_agent_123_idle_time", 45.5, step=None
        )


class TestCoordinationOverhead:
    """Test coordination overhead metrics."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_coordination", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_coordination_overhead_with_conflicts(self, mock_mlflow, experiment):
        """Test logging coordination overhead with merge conflicts."""
        # Act
        experiment.log_coordination_overhead(
            context_requests=25,
            blockers=3,
            avg_blocker_resolution_time=120.5,
            merge_conflicts=2,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["coordination_context_requests"] == 25
        assert metrics["coordination_blockers"] == 3
        assert metrics["coordination_avg_blocker_resolution"] == 120.5
        assert metrics["coordination_merge_conflicts"] == 2

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_coordination_overhead_without_conflicts(self, mock_mlflow, experiment):
        """Test logging coordination overhead without merge conflicts."""
        # Act
        experiment.log_coordination_overhead(
            context_requests=15,
            blockers=1,
            avg_blocker_resolution_time=60.0,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert "coordination_merge_conflicts" not in metrics


class TestResourceUsage:
    """Test resource usage and cost tracking."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_resources", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_resource_usage_full(self, mock_mlflow, experiment):
        """Test logging complete resource usage metrics."""
        # Act
        experiment.log_resource_usage(
            total_tokens=50000,
            api_cost_usd=0.75,
            tokens_per_task=2500.0,
            cost_per_task=0.0375,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["total_tokens"] == 50000.0
        assert metrics["api_cost_usd"] == 0.75
        assert metrics["tokens_per_task"] == 2500.0
        assert metrics["cost_per_task"] == 0.0375

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_resource_usage_minimal(self, mock_mlflow, experiment):
        """Test logging minimal resource usage (only totals)."""
        # Act
        experiment.log_resource_usage(
            total_tokens=30000,
            api_cost_usd=0.45,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert "tokens_per_task" not in metrics
        assert "cost_per_task" not in metrics


class TestThroughput:
    """Test throughput metrics."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_throughput", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_throughput_calculated(self, mock_mlflow, experiment):
        """Test throughput calculation when not provided."""
        # Act
        experiment.log_throughput(
            tasks_completed=20,
            elapsed_hours=4.0,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["throughput_tasks_completed"] == 20.0
        assert metrics["throughput_elapsed_hours"] == 4.0
        assert metrics["throughput_tasks_per_hour"] == 5.0

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_throughput_explicit(self, mock_mlflow, experiment):
        """Test throughput with explicit tasks_per_hour."""
        # Act
        experiment.log_throughput(
            tasks_completed=15,
            elapsed_hours=3.0,
            tasks_per_hour=5.5,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["throughput_tasks_per_hour"] == 5.5


class TestParallelEfficiency:
    """Test parallel efficiency metrics."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_parallel", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_parallel_efficiency_calculated(self, mock_mlflow, experiment):
        """Test parallel efficiency with calculations."""
        # Arrange
        single_agent_time = 8.0  # hours
        multi_agent_time = 2.5  # hours
        num_agents = 4

        # Expected: speedup = 8.0 / 2.5 = 3.2
        # Expected: efficiency = 3.2 / 4 = 0.8 (80%)

        # Act
        experiment.log_parallel_efficiency(
            num_agents=num_agents,
            single_agent_time=single_agent_time,
            multi_agent_time=multi_agent_time,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["parallel_num_agents"] == 4.0
        assert metrics["parallel_single_agent_time"] == 8.0
        assert metrics["parallel_multi_agent_time"] == 2.5
        assert metrics["parallel_speedup_factor"] == pytest.approx(3.2)
        assert metrics["parallel_efficiency"] == pytest.approx(0.8)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_parallel_efficiency_explicit(self, mock_mlflow, experiment):
        """Test parallel efficiency with explicit values."""
        # Act
        experiment.log_parallel_efficiency(
            num_agents=8,
            single_agent_time=10.0,
            multi_agent_time=2.0,
            speedup_factor=5.0,
            efficiency=0.625,
        )

        # Assert
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert metrics["parallel_speedup_factor"] == 5.0
        assert metrics["parallel_efficiency"] == 0.625

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_parallel_efficiency_zero_time(self, mock_mlflow, experiment):
        """Test parallel efficiency handles zero multi-agent time."""
        # Act
        experiment.log_parallel_efficiency(
            num_agents=4,
            single_agent_time=8.0,
            multi_agent_time=0.0,
        )

        # Assert - should not raise error
        metrics = mock_mlflow.log_metrics.call_args[0][0]
        assert "parallel_speedup_factor" not in metrics


class TestIntegration:
    """Integration tests for multiple metrics."""

    @pytest.fixture
    def experiment(self):
        """Create experiment instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield MarcusExperiment("test_integration", tmpdir)

    @patch("src.experiments.mlflow_tracker.mlflow")
    def test_log_multiple_new_metrics(self, mock_mlflow, experiment):
        """Test logging multiple enhanced metrics together."""
        # Act - Log various metrics
        experiment.log_code_quality(
            test_coverage=80.0,
            linting_errors=0,
            type_errors=0,
        )

        experiment.log_dependency_metrics(
            critical_path_length=4,
            avg_dependency_depth=2.5,
            parallelizable_fraction=0.7,
            max_parallel_tasks=6,
        )

        experiment.log_agent_idle_time("agent_1", 30.0)
        experiment.log_agent_idle_time("agent_2", 15.0)

        experiment.log_throughput(
            tasks_completed=12,
            elapsed_hours=2.0,
        )

        experiment.log_parallel_efficiency(
            num_agents=4,
            single_agent_time=6.0,
            multi_agent_time=2.0,
        )

        # Assert - All metrics logged successfully
        assert mock_mlflow.log_metrics.call_count >= 4
        assert mock_mlflow.log_metric.call_count == 2  # idle times
