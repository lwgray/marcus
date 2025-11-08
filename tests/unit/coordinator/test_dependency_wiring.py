"""
Unit tests for cross-parent dependency wiring.

Tests the hybrid approach combining embeddings, LLM reasoning, and sanity checks
to automatically create dependencies between subtasks of different parent tasks.
"""

from datetime import datetime, timezone
from typing import List
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.coordinator.dependency_wiring import (
    filter_candidates_by_embeddings,
    hybrid_dependency_resolution,
    resolve_dependencies_with_llm,
    validate_phase_order,
    wire_cross_parent_dependencies,
    would_create_cycle,
)


class TestFilterCandidatesByEmbeddings:
    """Test suite for embedding-based candidate filtering."""

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        mock = Mock()
        # Mock encode to return normalized vectors
        mock.encode = Mock(side_effect=lambda text: self._get_mock_embedding(text))
        return mock

    def _get_mock_embedding(self, text: str) -> np.ndarray:
        """Generate mock embeddings with controlled similarity."""
        # Use simple heuristic: similar words → similar embeddings
        if "user" in text.lower() and "schema" in text.lower():
            return np.array([0.9, 0.1, 0.0])  # High similarity
        elif "api" in text.lower() and "specification" in text.lower():
            return np.array([0.1, 0.9, 0.0])  # Different but valid
        elif "product" in text.lower():
            return np.array([0.0, 0.1, 0.9])  # Low similarity to user/api
        else:
            return np.array([0.5, 0.5, 0.0])  # Moderate similarity

    @pytest.fixture
    def sample_subtask(self) -> Task:
        """Create a sample subtask requiring user schema."""
        return Task(
            id="impl_user_1",
            name="Implement User API",
            description="Build user CRUD endpoints",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=["backend"],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
            requires="User model schema from Design phase",
            provides="User API endpoints",
        )

    @pytest.fixture
    def candidate_tasks(self) -> List[Task]:
        """Create candidate provider tasks."""
        return [
            Task(
                id="design_user_1",
                name="Design User Schema",
                description="Define user data model",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Complete user data schema with field definitions",
            ),
            Task(
                id="design_product_1",
                name="Design Product Schema",
                description="Define product data model",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Product schema with inventory tracking",
            ),
            Task(
                id="impl_user_2",
                name="Implement User Tests",
                description="Write user API tests",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=3.0,
                dependencies=[],
                labels=["testing"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_impl",  # Same parent - should be filtered
                requires="User API implementation",
                provides="User API test coverage",
            ),
        ]

    def test_filter_returns_high_similarity_candidates(
        self, sample_subtask, candidate_tasks, mock_embedding_model
    ):
        """Test that filtering returns candidates with high semantic similarity."""
        # Arrange
        all_tasks = candidate_tasks + [sample_subtask]

        # Act
        candidates = filter_candidates_by_embeddings(
            sample_subtask, all_tasks, mock_embedding_model, similarity_threshold=0.6
        )

        # Assert
        assert len(candidates) == 1, "Should return 1 high-similarity candidate"
        assert candidates[0][0].id == "design_user_1", "Should match user schema design"
        assert candidates[0][1] > 0.6, "Similarity score should exceed threshold"

    def test_filter_excludes_same_parent_subtasks(
        self, sample_subtask, candidate_tasks, mock_embedding_model
    ):
        """Test that filtering excludes subtasks from the same parent task."""
        # Arrange
        all_tasks = candidate_tasks + [sample_subtask]

        # Act
        candidates = filter_candidates_by_embeddings(
            sample_subtask, all_tasks, mock_embedding_model, similarity_threshold=0.0
        )

        # Assert
        candidate_ids = [c[0].id for c in candidates]
        assert "impl_user_2" not in candidate_ids, "Should exclude same-parent subtask"

    def test_filter_excludes_subtask_self(
        self, sample_subtask, candidate_tasks, mock_embedding_model
    ):
        """Test that filtering excludes the subtask itself."""
        # Arrange
        all_tasks = candidate_tasks + [sample_subtask]

        # Act
        candidates = filter_candidates_by_embeddings(
            sample_subtask, all_tasks, mock_embedding_model, similarity_threshold=0.0
        )

        # Assert
        candidate_ids = [c[0].id for c in candidates]
        assert "impl_user_1" not in candidate_ids, "Should exclude self"

    def test_filter_respects_max_candidates_limit(
        self, sample_subtask, mock_embedding_model
    ):
        """Test that filtering limits results to max_candidates."""
        # Arrange - Create many high-similarity candidates
        many_tasks = [
            Task(
                id=f"design_{i}",
                name=f"Design Task {i}",
                description="Design task",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id=f"parent_{i}",
                requires=None,
                provides="User schema design",  # High similarity to sample_subtask
            )
            for i in range(20)
        ]

        # Act
        candidates = filter_candidates_by_embeddings(
            sample_subtask, many_tasks, mock_embedding_model, max_candidates=5
        )

        # Assert
        assert len(candidates) <= 5, "Should limit to max_candidates"

    def test_filter_returns_empty_when_no_requires(
        self, candidate_tasks, mock_embedding_model
    ):
        """Test that filtering returns empty list when subtask has no requires field."""
        # Arrange
        subtask_no_requires = Task(
            id="task_1",
            name="Task",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_1",
            requires=None,  # No requires field
            provides="Something",
        )

        # Act
        candidates = filter_candidates_by_embeddings(
            subtask_no_requires, candidate_tasks, mock_embedding_model
        )

        # Assert
        assert len(candidates) == 0, "Should return empty list when no requires"

    def test_filter_handles_missing_embedding_model_gracefully(
        self, sample_subtask, candidate_tasks
    ):
        """Test that filtering gracefully handles missing embedding model."""
        # Act
        candidates = filter_candidates_by_embeddings(
            sample_subtask, candidate_tasks, embedding_model=None
        )

        # Assert - Should return all valid candidates when model unavailable
        assert len(candidates) <= 10, "Should return limited candidates as fallback"


class TestResolveDependenciesWithLLM:
    """Test suite for LLM-based dependency resolution."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine."""
        mock = Mock()
        mock.generate_structured_response = AsyncMock()
        return mock

    @pytest.fixture
    def sample_subtask(self) -> Task:
        """Create a sample subtask."""
        return Task(
            id="impl_user_1",
            name="Implement User API",
            description="Build user CRUD endpoints",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=["backend"],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
            requires="User model schema from Design phase",
            provides="User API endpoints",
        )

    @pytest.fixture
    def candidate_tasks(self) -> List[Task]:
        """Create candidate tasks for LLM analysis."""
        return [
            Task(
                id="design_user_1",
                name="Design User Schema",
                description="Define user data model",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Complete user data schema with field definitions",
            ),
            Task(
                id="research_api_1",
                name="Research API Best Practices",
                description="Study REST API design patterns",
                status=TaskStatus.DONE,
                priority=Priority.LOW,
                estimated_hours=1.0,
                dependencies=[],
                labels=["research"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_research",
                requires=None,
                provides="Research findings on API design patterns",
            ),
        ]

    @pytest.mark.asyncio
    async def test_llm_correctly_identifies_valid_dependency(
        self, sample_subtask, candidate_tasks, mock_ai_engine
    ):
        """Test that LLM correctly identifies a valid dependency."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = {
            "dependencies": ["design_user_1"],
            "reasoning": {
                "design_user_1": "Implementation needs the user schema from design phase",
                "rejected_research_api_1": "Research findings are not the actual schema required",
            },
        }

        # Act
        result = await resolve_dependencies_with_llm(
            sample_subtask, candidate_tasks, mock_ai_engine
        )

        # Assert
        assert (
            "design_user_1" in result["dependencies"]
        ), "Should identify valid dependency"
        assert (
            "design_user_1" in result["reasoning"]
        ), "Should provide reasoning for decision"

    @pytest.mark.asyncio
    async def test_llm_rejects_invalid_dependency(
        self, sample_subtask, candidate_tasks, mock_ai_engine
    ):
        """Test that LLM rejects invalid dependencies."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = {
            "dependencies": ["design_user_1"],  # Only valid one
            "reasoning": {
                "design_user_1": "Direct match for user schema",
                "rejected_research_api_1": "Research is not the specification itself",
            },
        }

        # Act
        result = await resolve_dependencies_with_llm(
            sample_subtask, candidate_tasks, mock_ai_engine
        )

        # Assert
        assert (
            "research_api_1" not in result["dependencies"]
        ), "Should reject research as dependency"
        assert (
            "rejected_research_api_1" in result["reasoning"]
        ), "Should explain rejection"

    @pytest.mark.asyncio
    async def test_llm_returns_empty_when_no_candidates(
        self, sample_subtask, mock_ai_engine
    ):
        """Test that LLM returns empty result when no candidates provided."""
        # Act
        result = await resolve_dependencies_with_llm(sample_subtask, [], mock_ai_engine)

        # Assert
        assert result["dependencies"] == [], "Should return empty dependencies"
        assert result["reasoning"] == {}, "Should return empty reasoning"

    @pytest.mark.asyncio
    async def test_llm_handles_ai_engine_errors_gracefully(
        self, sample_subtask, candidate_tasks, mock_ai_engine
    ):
        """Test that LLM resolution handles AI engine errors gracefully."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = Exception(
            "API timeout"
        )

        # Act
        result = await resolve_dependencies_with_llm(
            sample_subtask, candidate_tasks, mock_ai_engine
        )

        # Assert
        assert result["dependencies"] == [], "Should return empty on error"
        assert "error" in result["reasoning"], "Should include error in reasoning"


class TestWouldCreateCycle:
    """Test suite for cycle detection."""

    @pytest.fixture
    def linear_tasks(self) -> List[Task]:
        """Create tasks with linear dependency chain: A → B → C."""
        return [
            Task(
                id="task_a",
                name="Task A",
                description="First task",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=1.0,
                dependencies=[],
                labels=[],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            ),
            Task(
                id="task_b",
                name="Task B",
                description="Second task",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                estimated_hours=1.0,
                dependencies=["task_a"],
                labels=[],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            ),
            Task(
                id="task_c",
                name="Task C",
                description="Third task",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                estimated_hours=1.0,
                dependencies=["task_b"],
                labels=[],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            ),
        ]

    def test_detects_simple_cycle(self, linear_tasks):
        """Test detection of simple 2-node cycle."""
        # Act - Try to add A → B (would create A → B → A cycle since B already depends on A)
        # Note: Linear tasks has B depends on A, so adding A depends on B creates cycle
        creates_cycle = would_create_cycle("task_a", "task_b", linear_tasks)

        # Assert
        assert creates_cycle is True, "Should detect simple 2-node cycle"

    def test_detects_long_cycle(self, linear_tasks):
        """Test detection of longer cycle chain."""
        # Act - Try to add A → C (would create A → B → C → A cycle)
        # Current: A→[], B→[A], C→[B]
        # Adding A→C creates: C→B→A→C (cycle!)
        creates_cycle = would_create_cycle("task_a", "task_c", linear_tasks)

        # Assert
        assert creates_cycle is True, "Should detect long cycle chain"

    def test_allows_valid_dependency(self, linear_tasks):
        """Test that valid dependencies are allowed."""
        # Arrange - Create a new independent task
        new_task = Task(
            id="task_d",
            name="Task D",
            description="Independent task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=False,
        )
        all_tasks = linear_tasks + [new_task]

        # Act - Try to add D → C (valid, no cycle)
        creates_cycle = would_create_cycle("task_d", "task_c", all_tasks)

        # Assert
        assert creates_cycle is False, "Should allow valid dependency"

    def test_handles_self_dependency(self):
        """Test that self-dependency is detected as cycle."""
        # Arrange
        task = Task(
            id="task_1",
            name="Task",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=False,
        )

        # Act - Try to add task_1 → task_1 (self-dependency)
        creates_cycle = would_create_cycle("task_1", "task_1", [task])

        # Assert
        assert creates_cycle is True, "Should detect self-dependency as cycle"


class TestValidatePhaseOrder:
    """Test suite for phase ordering validation."""

    def test_allows_implement_depending_on_design(self):
        """Test that Implementation can depend on Design."""
        # Arrange
        design_task = Task(
            id="design_1",
            name="Design User API",
            description="Design API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            estimated_hours=2.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_design",
        )

        implement_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
        )

        # Act
        is_valid = validate_phase_order(implement_task, design_task)

        # Assert
        assert is_valid is True, "Implementation should be able to depend on Design"

    def test_rejects_design_depending_on_implement(self):
        """Test that Design cannot depend on Implementation."""
        # Arrange
        design_task = Task(
            id="design_1",
            name="Design User API",
            description="Design API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=2.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_design",
        )

        implement_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
        )

        # Act
        is_valid = validate_phase_order(design_task, implement_task)

        # Assert
        assert is_valid is False, "Design should NOT depend on Implementation"

    def test_allows_test_depending_on_implement(self):
        """Test that Test can depend on Implementation."""
        # Arrange
        implement_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
        )

        test_task = Task(
            id="test_1",
            name="Test User API",
            description="Test API",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=3.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_test",
        )

        # Act
        is_valid = validate_phase_order(test_task, implement_task)

        # Assert
        assert is_valid is True, "Test should be able to depend on Implementation"

    def test_allows_unknown_phases(self):
        """Test that tasks with unknown phases are allowed."""
        # Arrange
        task_1 = Task(
            id="task_1",
            name="Random Task",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_1",
        )

        task_2 = Task(
            id="task_2",
            name="Another Task",
            description="Task",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_2",
        )

        # Act
        is_valid = validate_phase_order(task_1, task_2)

        # Assert
        assert (
            is_valid is True
        ), "Should allow dependencies when phases can't be determined"


class TestHybridDependencyResolution:
    """Test suite for hybrid dependency resolution (integration of all stages)."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine."""
        mock = Mock()
        mock.generate_structured_response = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        mock = Mock()
        mock.encode = Mock(
            side_effect=lambda text: np.array([0.9, 0.1, 0.0])
        )  # High similarity
        return mock

    @pytest.fixture
    def subtask_needing_schema(self) -> Task:
        """Create a subtask that needs user schema."""
        return Task(
            id="impl_user_1",
            name="Implement User API",
            description="Build user CRUD endpoints",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=["backend"],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
            requires="User model schema from Design phase",
            provides="User API endpoints",
        )

    @pytest.fixture
    def all_project_tasks(self) -> List[Task]:
        """Create a full project task list."""
        return [
            Task(
                id="design_user_1",
                name="Design User Schema",
                description="Define user data model",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Complete user data schema with field definitions",
            ),
            Task(
                id="design_product_1",
                name="Design Product Schema",
                description="Define product data model",
                status=TaskStatus.DONE,
                priority=Priority.MEDIUM,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Product schema with inventory tracking",
            ),
        ]

    @pytest.mark.asyncio
    async def test_hybrid_resolution_finds_correct_dependency(
        self,
        subtask_needing_schema,
        all_project_tasks,
        mock_ai_engine,
        mock_embedding_model,
    ):
        """Test that hybrid resolution finds the correct dependency."""
        # Arrange
        mock_ai_engine.generate_structured_response.return_value = {
            "dependencies": ["design_user_1"],
            "reasoning": {
                "design_user_1": "Provides the exact user schema required",
            },
        }

        # Act
        dependencies = await hybrid_dependency_resolution(
            subtask_needing_schema,
            all_project_tasks,
            mock_ai_engine,
            mock_embedding_model,
        )

        # Assert
        assert (
            "design_user_1" in dependencies
        ), "Should find design_user_1 as dependency"
        assert len(dependencies) == 1, "Should find exactly 1 dependency"

    @pytest.mark.asyncio
    async def test_hybrid_resolution_rejects_cycle_creating_dependency(
        self, mock_ai_engine, mock_embedding_model
    ):
        """Test that hybrid resolution rejects dependencies that would create cycles."""
        # Arrange - Create circular dependency scenario
        task_a = Task(
            id="task_a",
            name="Design Task A",
            description="Task A",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=1.0,
            dependencies=["task_b"],  # A depends on B
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_1",
            requires="Something from B",
            provides="Output A",
        )

        task_b = Task(
            id="task_b",
            name="Design Task B",
            description="Task B",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=1.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_2",
            requires="Something from A",  # B wants to depend on A
            provides="Output B",
        )

        # LLM suggests B → A (would create cycle since A → B exists)
        mock_ai_engine.generate_structured_response.return_value = {
            "dependencies": ["task_a"],
            "reasoning": {"task_a": "Provides required output"},
        }

        # Act
        dependencies = await hybrid_dependency_resolution(
            task_b, [task_a, task_b], mock_ai_engine, mock_embedding_model
        )

        # Assert
        assert (
            "task_a" not in dependencies
        ), "Should reject dependency that creates cycle"

    @pytest.mark.asyncio
    async def test_hybrid_resolution_rejects_invalid_phase_order(
        self, mock_ai_engine, mock_embedding_model
    ):
        """Test that hybrid resolution rejects dependencies with invalid phase order."""
        # Arrange - Design task trying to depend on Implementation
        design_task = Task(
            id="design_1",
            name="Design User API",
            description="Design API",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            estimated_hours=2.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_design",
            requires="Implementation details",
            provides="API specification",
        )

        impl_task = Task(
            id="impl_1",
            name="Implement User API",
            description="Implement API",
            status=TaskStatus.DONE,
            priority=Priority.HIGH,
            estimated_hours=5.0,
            dependencies=[],
            labels=[],
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            is_subtask=True,
            parent_task_id="parent_impl",
            requires=None,
            provides="Working user API",
        )

        # LLM suggests design → implement (invalid phase order)
        mock_ai_engine.generate_structured_response.return_value = {
            "dependencies": ["impl_1"],
            "reasoning": {"impl_1": "Provides API details"},
        }

        # Act
        dependencies = await hybrid_dependency_resolution(
            design_task, [design_task, impl_task], mock_ai_engine, mock_embedding_model
        )

        # Assert
        assert (
            "impl_1" not in dependencies
        ), "Should reject dependency with invalid phase order"


class TestWireCrossParentDependencies:
    """Test suite for main orchestration function."""

    @pytest.fixture
    def mock_ai_engine(self):
        """Create a mock AI engine."""
        mock = Mock()
        mock.generate_structured_response = AsyncMock()
        return mock

    @pytest.fixture
    def mock_embedding_model(self):
        """Create a mock embedding model."""
        mock = Mock()
        mock.encode = Mock(
            side_effect=lambda text: np.array([0.9, 0.1, 0.0])
        )  # High similarity
        return mock

    @pytest.fixture
    def complete_project_tasks(self) -> List[Task]:
        """Create a complete project with parent tasks and subtasks."""
        return [
            # Parent tasks
            Task(
                id="parent_design",
                name="Design Phase",
                description="Design all schemas",
                status=TaskStatus.IN_PROGRESS,
                priority=Priority.HIGH,
                estimated_hours=10.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            ),
            Task(
                id="parent_impl",
                name="Implementation Phase",
                description="Implement all features",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=20.0,
                dependencies=["parent_design"],
                labels=["backend"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=False,
            ),
            # Design subtasks
            Task(
                id="design_user_1",
                name="Design User Schema",
                description="Define user data model",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Complete user data schema with field definitions",
            ),
            Task(
                id="design_product_1",
                name="Design Product Schema",
                description="Define product data model",
                status=TaskStatus.DONE,
                priority=Priority.HIGH,
                estimated_hours=2.0,
                dependencies=[],
                labels=["design"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_design",
                requires=None,
                provides="Product schema with inventory tracking",
            ),
            # Implementation subtasks
            Task(
                id="impl_user_1",
                name="Implement User API",
                description="Build user CRUD endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=5.0,
                dependencies=[],
                labels=["backend"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_impl",
                requires="User model schema from Design phase",
                provides="User API endpoints",
            ),
            Task(
                id="impl_product_1",
                name="Implement Product API",
                description="Build product CRUD endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=5.0,
                dependencies=[],
                labels=["backend"],
                assigned_to=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                due_date=None,
                is_subtask=True,
                parent_task_id="parent_impl",
                requires="Product schema from Design phase",
                provides="Product API endpoints",
            ),
        ]

    @pytest.mark.asyncio
    async def test_wiring_creates_correct_cross_parent_dependencies(
        self, complete_project_tasks, mock_ai_engine, mock_embedding_model
    ):
        """Test that wiring creates correct cross-parent dependencies."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = [
            # First call for impl_user_1
            {
                "dependencies": ["design_user_1"],
                "reasoning": {"design_user_1": "Provides user schema"},
            },
            # Second call for impl_product_1
            {
                "dependencies": ["design_product_1"],
                "reasoning": {"design_product_1": "Provides product schema"},
            },
        ]

        # Act
        stats = await wire_cross_parent_dependencies(
            complete_project_tasks, mock_ai_engine, mock_embedding_model
        )

        # Assert
        assert (
            stats["dependencies_created"] == 2
        ), "Should create 2 cross-parent dependencies"
        assert (
            stats["subtasks_analyzed"] == 2
        ), "Should analyze 2 subtasks with requires"

        # Verify dependencies were added
        impl_user = next(t for t in complete_project_tasks if t.id == "impl_user_1")
        assert (
            "design_user_1" in impl_user.dependencies
        ), "impl_user should depend on design_user"

        impl_product = next(
            t for t in complete_project_tasks if t.id == "impl_product_1"
        )
        assert (
            "design_product_1" in impl_product.dependencies
        ), "impl_product should depend on design_product"

    @pytest.mark.asyncio
    async def test_wiring_skips_subtasks_without_requires(
        self, complete_project_tasks, mock_ai_engine, mock_embedding_model
    ):
        """Test that wiring skips subtasks without requires field."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = [
            {"dependencies": ["design_user_1"], "reasoning": {}},
            {"dependencies": ["design_product_1"], "reasoning": {}},
        ]

        # Act
        stats = await wire_cross_parent_dependencies(
            complete_project_tasks, mock_ai_engine, mock_embedding_model
        )

        # Assert
        # Should skip design_user_1 and design_product_1 (no requires field)
        assert (
            stats["skipped_no_requires"] == 2
        ), "Should skip 2 design subtasks without requires"

    @pytest.mark.asyncio
    async def test_wiring_skips_parent_tasks(
        self, complete_project_tasks, mock_ai_engine, mock_embedding_model
    ):
        """Test that wiring only analyzes subtasks, not parent tasks."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = [
            {"dependencies": ["design_user_1"], "reasoning": {}},
            {"dependencies": ["design_product_1"], "reasoning": {}},
        ]

        # Act
        stats = await wire_cross_parent_dependencies(
            complete_project_tasks, mock_ai_engine, mock_embedding_model
        )

        # Assert
        # Should only analyze 2 impl subtasks (not parent_design, parent_impl)
        subtasks_analyzed = stats["subtasks_analyzed"]
        assert subtasks_analyzed == 2, "Should only analyze subtasks, not parent tasks"

    @pytest.mark.asyncio
    async def test_wiring_reports_statistics(
        self, complete_project_tasks, mock_ai_engine, mock_embedding_model
    ):
        """Test that wiring returns detailed statistics."""
        # Arrange
        mock_ai_engine.generate_structured_response.side_effect = [
            {"dependencies": ["design_user_1"], "reasoning": {}},
            {"dependencies": ["design_product_1"], "reasoning": {}},
        ]

        # Act
        stats = await wire_cross_parent_dependencies(
            complete_project_tasks, mock_ai_engine, mock_embedding_model
        )

        # Assert
        assert "subtasks_analyzed" in stats, "Should report subtasks analyzed"
        assert "dependencies_created" in stats, "Should report dependencies created"
        assert "llm_calls" in stats, "Should report LLM calls made"
        assert "skipped_no_requires" in stats, "Should report skipped tasks"
        assert "total_time_seconds" in stats, "Should report total time"
