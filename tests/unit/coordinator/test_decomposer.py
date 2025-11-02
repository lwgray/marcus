"""
Unit tests for Task Decomposer.

Tests the AI-driven task decomposition functionality.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.decomposer import (
    _adjust_subtask_dependencies,
    _analyze_parallelism,
    _calculate_dependency_levels,
    _create_integration_subtask,
    _validate_decomposition,
    decompose_task,
    should_decompose,
)


class TestShouldDecompose:
    """Test suite for should_decompose decision logic."""

    @pytest.fixture
    def base_task(self):
        """Create base task for testing."""
        return Task(
            id="task-1",
            name="Build user management API",
            description="Create REST API for user management",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=6.0,
            labels=["backend", "api"],
        )

    def test_should_decompose_large_task(self, base_task):
        """Test large tasks (>4 hours) are decomposed."""
        # Arrange
        base_task.estimated_hours = 5.0

        # Act
        result = should_decompose(base_task)

        # Assert
        assert result is True

    def test_should_not_decompose_small_task(self, base_task):
        """Test small tasks (<3 hours) are not decomposed."""
        # Arrange
        base_task.estimated_hours = 2.0

        # Act
        result = should_decompose(base_task)

        # Assert
        assert result is False

    def test_should_not_decompose_bugfix(self, base_task):
        """Test bugfix tasks are not decomposed."""
        # Arrange
        base_task.labels = ["bugfix", "backend"]

        # Act
        result = should_decompose(base_task)

        # Assert
        assert result is False

    def test_should_not_decompose_deployment(self, base_task):
        """Test deployment tasks are not decomposed."""
        # Arrange
        base_task.name = "Deploy to production"
        base_task.estimated_hours = 5.0

        # Act
        result = should_decompose(base_task)

        # Assert
        assert result is False

    def test_should_decompose_multi_component_task(self, base_task):
        """Test tasks with multiple components are decomposed."""
        # Arrange
        base_task.estimated_hours = 3.5
        base_task.description = (
            "Build API endpoint with database model and frontend UI components"
        )

        # Act
        result = should_decompose(base_task)

        # Assert
        assert result is True


class TestDecomposeTask:
    """Test suite for decompose_task AI-driven decomposition."""

    @pytest.fixture
    def task(self):
        """Create task for testing."""
        return Task(
            id="task-1",
            name="Build authentication system",
            description="Create user authentication with JWT tokens",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=8.0,
            labels=["backend", "security"],
        )

    @pytest.fixture
    def mock_ai_engine(self):
        """Create mock AI engine."""
        ai_engine = Mock()
        ai_engine.generate_structured_response = AsyncMock()
        return ai_engine

    @pytest.fixture
    def sample_decomposition(self):
        """Sample decomposition response from AI."""
        return {
            "subtasks": [
                {
                    "name": "Create User model",
                    "description": "Define User model with email and password",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                    "dependency_types": [],
                    "file_artifacts": ["src/models/user.py"],
                    "provides": "User model",
                    "requires": "None",
                },
                {
                    "name": "Build login endpoint",
                    "description": "Create POST /api/login",
                    "estimated_hours": 3.0,
                    "dependencies": [0],
                    "dependency_types": ["soft"],
                    "file_artifacts": ["src/api/auth/login.py"],
                    "provides": "Login endpoint",
                    "requires": "User model",
                },
            ],
            "shared_conventions": {
                "base_path": "src/api/",
                "file_structure": "src/{component}/{feature}.py",
                "response_format": {"success": {"status": "success", "data": "..."}},
            },
        }

    @pytest.mark.asyncio
    async def test_decompose_task_success(
        self, task, mock_ai_engine, sample_decomposition
    ):
        """Test successful task decomposition."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = sample_decomposition

        # Act
        result = await decompose_task(task, mock_ai_engine)

        # Assert
        assert result["success"] is True
        assert "subtasks" in result
        # Should have original 2 + 1 integration subtask
        assert len(result["subtasks"]) == 3
        assert "shared_conventions" in result

    @pytest.mark.asyncio
    async def test_decompose_task_adds_integration_subtask(
        self, task, mock_ai_engine, sample_decomposition
    ):
        """Test integration subtask is automatically added."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = sample_decomposition

        # Act
        result = await decompose_task(task, mock_ai_engine)

        # Assert
        integration_subtask = result["subtasks"][-1]
        assert "Integrate and validate" in integration_subtask["name"]
        assert len(integration_subtask["dependencies"]) == 2  # Depends on both previous

    @pytest.mark.asyncio
    async def test_decompose_task_adjusts_dependencies_to_ids(
        self, task, mock_ai_engine, sample_decomposition
    ):
        """Test dependencies converted from indices to subtask IDs."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = sample_decomposition

        # Act
        result = await decompose_task(task, mock_ai_engine)

        # Assert
        # Second subtask depends on first
        second_subtask = result["subtasks"][1]
        assert second_subtask["dependencies"] == ["task-1_sub_1"]

    @pytest.mark.asyncio
    async def test_decompose_task_handles_ai_error(self, task, mock_ai_engine):
        """Test error handling when AI fails."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = Exception(
            "AI service unavailable"
        )

        # Act
        result = await decompose_task(task, mock_ai_engine)

        # Assert
        assert result["success"] is False
        assert "error" in result
        assert "AI service unavailable" in result["error"]

    @pytest.mark.asyncio
    async def test_decompose_task_includes_parallelism_analysis(
        self, task, mock_ai_engine, sample_decomposition
    ):
        """Test decomposition includes parallelism analysis metrics."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = sample_decomposition

        # Act
        result = await decompose_task(task, mock_ai_engine)

        # Assert
        assert result["success"] is True
        assert "parallelism_analysis" in result
        analysis = result["parallelism_analysis"]
        assert "parallelizable_percentage" in analysis
        assert "max_parallel_workers" in analysis
        assert "dependency_chain_depth" in analysis
        assert "soft_dependency_count" in analysis
        assert "hard_dependency_count" in analysis
        assert "parallelism_score" in analysis


class TestCreateIntegrationSubtask:
    """Test suite for integration subtask creation."""

    def test_create_integration_subtask_includes_all_dependencies(self):
        """Test integration subtask depends on all previous subtasks."""
        # Arrange
        task = Task(
            id="task-1",
            name="Test task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=6.0,
        )
        previous_subtasks = [
            {"name": "Subtask 1", "file_artifacts": ["file1.py"]},
            {"name": "Subtask 2", "file_artifacts": ["file2.py"]},
        ]

        # Act
        integration = _create_integration_subtask(task, previous_subtasks)

        # Assert
        assert integration["dependencies"] == [0, 1]

    def test_create_integration_subtask_has_doc_artifacts(self):
        """Test integration subtask creates documentation."""
        # Arrange
        task = Task(
            id="task-1",
            name="Test task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=6.0,
        )
        previous_subtasks = [{"name": "Subtask 1"}]

        # Act
        integration = _create_integration_subtask(task, previous_subtasks)

        # Assert
        assert "docs/integration_report.md" in integration["file_artifacts"]
        assert any("test" in artifact for artifact in integration["file_artifacts"])

    def test_create_integration_subtask_estimates_time(self):
        """Test integration subtask time estimate is reasonable."""
        # Arrange
        task = Task(
            id="task-1",
            name="Test task",
            description="Test",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=10.0,
        )
        previous_subtasks = [{"name": "Subtask 1"}]

        # Act
        integration = _create_integration_subtask(task, previous_subtasks)

        # Assert
        # Should be capped at 1.5 hours even though 20% of 10 = 2
        assert integration["estimated_hours"] == 1.5


class TestValidateDecomposition:
    """Test suite for decomposition validation."""

    def test_validate_decomposition_accepts_valid(self):
        """Test valid decomposition passes validation."""
        # Arrange
        decomposition = {
            "subtasks": [
                {
                    "name": "Task 1",
                    "description": "Do thing 1",
                    "estimated_hours": 2.0,
                    "dependencies": [],
                },
                {
                    "name": "Task 2",
                    "description": "Do thing 2",
                    "estimated_hours": 1.5,
                    "dependencies": [0],
                },
            ],
            "shared_conventions": {"base_path": "src/"},
        }

        # Act
        result = _validate_decomposition(decomposition)

        # Assert
        assert result is True

    def test_validate_decomposition_rejects_missing_subtasks(self):
        """Test validation fails when subtasks are missing."""
        # Arrange
        decomposition = {"shared_conventions": {}}

        # Act
        result = _validate_decomposition(decomposition)

        # Assert
        assert result is False

    def test_validate_decomposition_rejects_invalid_dependencies(self):
        """Test validation fails for forward dependencies."""
        # Arrange
        decomposition = {
            "subtasks": [
                {
                    "name": "Task 1",
                    "description": "Do thing 1",
                    "estimated_hours": 2.0,
                    "dependencies": [1],  # Forward dependency - invalid
                },
                {
                    "name": "Task 2",
                    "description": "Do thing 2",
                    "estimated_hours": 1.5,
                },
            ],
            "shared_conventions": {},
        }

        # Act
        result = _validate_decomposition(decomposition)

        # Assert
        assert result is False


class TestAdjustSubtaskDependencies:
    """Test suite for dependency ID adjustment."""

    def test_adjust_subtask_dependencies_converts_indices_to_ids(self):
        """Test conversion from indices to subtask IDs."""
        # Arrange
        parent_id = "task-1"
        decomposition = {
            "subtasks": [
                {"name": "Sub 1", "dependencies": []},
                {"name": "Sub 2", "dependencies": [0]},
                {"name": "Sub 3", "dependencies": [0, 1]},
            ]
        }

        # Act
        result = _adjust_subtask_dependencies(parent_id, decomposition)

        # Assert
        assert result["subtasks"][1]["dependencies"] == ["task-1_sub_1"]
        assert result["subtasks"][2]["dependencies"] == [
            "task-1_sub_1",
            "task-1_sub_2",
        ]

    def test_adjust_subtask_dependencies_handles_empty_dependencies(self):
        """Test adjustment handles subtasks with no dependencies."""
        # Arrange
        parent_id = "task-1"
        decomposition = {
            "subtasks": [
                {"name": "Sub 1", "dependencies": []},
                {"name": "Sub 2"},  # No dependencies key
            ]
        }

        # Act
        result = _adjust_subtask_dependencies(parent_id, decomposition)

        # Assert
        assert result["subtasks"][0]["dependencies"] == []
        assert "dependencies" not in result["subtasks"][1]

    def test_adjust_subtask_dependencies_rejects_string_dependencies(self, caplog):
        """Test non-integer dependencies are rejected and logged as errors."""
        # Arrange
        parent_id = "task-1"
        decomposition = {
            "subtasks": [
                {"name": "Sub 1", "dependencies": []},
                {
                    "name": "Sub 2",
                    "dependencies": ["task_xxx_sub_1"],  # Invalid string dependency
                },
            ]
        }

        # Act
        result = _adjust_subtask_dependencies(parent_id, decomposition)

        # Assert
        # String dependency should be rejected, leaving empty list
        assert result["subtasks"][1]["dependencies"] == []
        # Should log error about non-integer dependency
        assert "non-integer dependency" in caplog.text.lower()

    def test_adjust_subtask_dependencies_handles_invalid_indices(self, caplog):
        """Test out-of-range dependency indices are rejected with warning."""
        # Arrange
        parent_id = "task-1"
        decomposition = {
            "subtasks": [
                {"name": "Sub 1", "dependencies": []},
                {"name": "Sub 2", "dependencies": [0, 5]},  # Index 5 doesn't exist
            ]
        }

        # Act
        result = _adjust_subtask_dependencies(parent_id, decomposition)

        # Assert
        # Valid dependency should be included, invalid should be skipped
        assert result["subtasks"][1]["dependencies"] == ["task-1_sub_1"]
        # Should log warning about invalid index
        assert "invalid dependency index" in caplog.text.lower()


class TestCalculateDependencyLevels:
    """Test suite for dependency level calculation."""

    def test_calculate_levels_no_dependencies(self):
        """Test all tasks at level 0 when no dependencies."""
        # Arrange
        subtasks = [
            {"name": "Task 1", "dependencies": []},
            {"name": "Task 2", "dependencies": []},
            {"name": "Task 3", "dependencies": []},
        ]

        # Act
        levels = _calculate_dependency_levels(subtasks)

        # Assert
        assert 0 in levels
        assert len(levels[0]) == 3
        assert levels[0] == [0, 1, 2]

    def test_calculate_levels_sequential_chain(self):
        """Test sequential chain creates increasing levels."""
        # Arrange
        subtasks = [
            {"name": "Task 1", "dependencies": []},
            {"name": "Task 2", "dependencies": [0]},
            {"name": "Task 3", "dependencies": [1]},
        ]

        # Act
        levels = _calculate_dependency_levels(subtasks)

        # Assert
        assert len(levels) == 3
        assert levels[0] == [0]
        assert levels[1] == [1]
        assert levels[2] == [2]

    def test_calculate_levels_parallel_branches(self):
        """Test parallel branches at same level."""
        # Arrange
        subtasks = [
            {"name": "Task 1", "dependencies": []},
            {"name": "Task 2", "dependencies": [0]},
            {"name": "Task 3", "dependencies": [0]},
            {"name": "Task 4", "dependencies": [1, 2]},
        ]

        # Act
        levels = _calculate_dependency_levels(subtasks)

        # Assert
        assert levels[0] == [0]  # Root task
        assert set(levels[1]) == {1, 2}  # Parallel branches
        assert levels[2] == [3]  # Joins branches

    def test_calculate_levels_complex_dag(self):
        """Test complex DAG with multiple levels."""
        # Arrange
        subtasks = [
            {"name": "Task 1", "dependencies": []},
            {"name": "Task 2", "dependencies": []},
            {"name": "Task 3", "dependencies": [0]},
            {"name": "Task 4", "dependencies": [0, 1]},
            {"name": "Task 5", "dependencies": [2, 3]},
        ]

        # Act
        levels = _calculate_dependency_levels(subtasks)

        # Assert
        assert set(levels[0]) == {0, 1}  # Two roots
        assert set(levels[1]) == {2, 3}  # Both depend on level 0
        assert levels[2] == [4]  # Depends on level 1


class TestAnalyzeParallelism:
    """Test suite for parallelism analysis."""

    def test_analyze_empty_decomposition(self):
        """Test analysis handles empty decomposition."""
        # Arrange
        decomposition = {"subtasks": []}

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelizable_percentage"] == 0.0
        assert result["max_parallel_workers"] == 0
        assert result["dependency_chain_depth"] == 0

    def test_analyze_fully_parallel_tasks(self):
        """Test analysis of fully parallelizable tasks."""
        # Arrange
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {"name": "Task 2", "dependencies": [], "dependency_types": []},
                {"name": "Task 3", "dependencies": [], "dependency_types": []},
                {"name": "Task 4", "dependencies": [], "dependency_types": []},
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelizable_percentage"] == 100.0  # All have 0 dependencies
        assert result["max_parallel_workers"] == 4  # All can run in parallel
        assert result["dependency_chain_depth"] == 1  # Only one level
        assert result["soft_dependency_count"] == 0
        assert result["hard_dependency_count"] == 0

    def test_analyze_sequential_chain(self):
        """Test analysis of sequential chain."""
        # Arrange
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {"name": "Task 2", "dependencies": [0], "dependency_types": ["hard"]},
                {"name": "Task 3", "dependencies": [1], "dependency_types": ["hard"]},
                {"name": "Task 4", "dependencies": [2], "dependency_types": ["hard"]},
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelizable_percentage"] == 100.0  # All have 0-1 dependencies
        assert result["max_parallel_workers"] == 1  # Only one at each level
        assert result["dependency_chain_depth"] == 4  # Four levels deep
        assert result["soft_dependency_count"] == 0
        assert result["hard_dependency_count"] == 3

    def test_analyze_mixed_dependencies(self):
        """Test analysis with mix of parallel and sequential."""
        # Arrange
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {"name": "Task 2", "dependencies": [0], "dependency_types": ["soft"]},
                {"name": "Task 3", "dependencies": [0], "dependency_types": ["soft"]},
                {"name": "Task 4", "dependencies": [0], "dependency_types": ["soft"]},
                {
                    "name": "Task 5",
                    "dependencies": [1, 2, 3],
                    "dependency_types": ["hard", "hard", "hard"],
                },
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelizable_percentage"] == 80.0  # 4 of 5 have 0-1 deps
        assert result["max_parallel_workers"] == 3  # Tasks 2,3,4 can run in parallel
        assert result["dependency_chain_depth"] == 3  # Three levels (0, 1, 2)
        assert result["soft_dependency_count"] == 3
        assert result["hard_dependency_count"] == 3

    def test_analyze_parallelism_score_high(self):
        """Test high parallelism score for optimal decomposition."""
        # Arrange - Optimal: 80% parallelizable, mostly soft deps
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {"name": "Task 2", "dependencies": [0], "dependency_types": ["soft"]},
                {"name": "Task 3", "dependencies": [0], "dependency_types": ["soft"]},
                {"name": "Task 4", "dependencies": [0], "dependency_types": ["soft"]},
                {"name": "Task 5", "dependencies": [0], "dependency_types": ["soft"]},
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelism_score"] > 80.0  # Should be high score

    def test_analyze_parallelism_score_low(self):
        """Test low parallelism score for sequential decomposition."""
        # Arrange - Poor: sequential chain, all hard deps
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {"name": "Task 2", "dependencies": [0], "dependency_types": ["hard"]},
                {"name": "Task 3", "dependencies": [1], "dependency_types": ["hard"]},
                {
                    "name": "Task 4",
                    "dependencies": [2],
                    "dependency_types": ["hard"],
                },
                {
                    "name": "Task 5",
                    "dependencies": [3],
                    "dependency_types": ["hard"],
                },
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["parallelism_score"] < 55.0  # Should be low score (adjusted)

    def test_analyze_counts_dependency_types_correctly(self):
        """Test accurate counting of soft vs hard dependencies."""
        # Arrange
        decomposition = {
            "subtasks": [
                {"name": "Task 1", "dependencies": [], "dependency_types": []},
                {
                    "name": "Task 2",
                    "dependencies": [0],
                    "dependency_types": ["soft"],
                },
                {
                    "name": "Task 3",
                    "dependencies": [0],
                    "dependency_types": ["hard"],
                },
                {
                    "name": "Task 4",
                    "dependencies": [1, 2],
                    "dependency_types": ["soft", "hard"],
                },
            ]
        }

        # Act
        result = _analyze_parallelism(decomposition)

        # Assert
        assert result["soft_dependency_count"] == 2
        assert result["hard_dependency_count"] == 2
