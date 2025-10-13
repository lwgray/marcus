"""
Unit tests for subtask instruction generation.

Tests that subtasks inherit the correct task type from their parent task
when generating instructions.
"""

import pytest
from unittest.mock import AsyncMock, Mock

from src.core.models import Priority, Task, TaskStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.marcus_mcp.coordinator.subtask_assignment import convert_subtask_to_task
from src.marcus_mcp.coordinator.subtask_manager import Subtask


class TestSubtaskInstructionType:
    """Test suite for subtask instruction type inheritance."""

    @pytest.fixture
    def parent_design_task(self) -> Task:
        """Create a parent design task."""
        return Task(
            id="parent_123",
            name="Design Get Current Time",
            description="Design the API endpoint for getting current time",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=["api", "design"],
            project_id="project_1",
            project_name="Test Project",
        )

    @pytest.fixture
    def design_subtask(self) -> Subtask:
        """Create a design subtask."""
        return Subtask(
            id="parent_123_sub_2",
            parent_task_id="parent_123",
            name="Define the API endpoint specification",
            description="Specify the HTTP method, URL path, request/response format, and error handling for the current time API endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            estimated_hours=2.0,
            dependencies=["parent_123_sub_1"],
        )

    @pytest.fixture
    def ai_engine_mock(self) -> AIAnalysisEngine:
        """Create a mocked AI engine."""
        engine = AIAnalysisEngine()
        # Mock the client to prevent actual API calls
        engine.client = None
        return engine

    def test_convert_subtask_preserves_parent_labels(
        self, design_subtask: Subtask, parent_design_task: Task
    ) -> None:
        """Test that subtask conversion preserves parent labels."""
        # Act
        task = convert_subtask_to_task(design_subtask, parent_design_task)

        # Assert
        assert task.labels == parent_design_task.labels
        assert "design" in task.labels

    async def test_design_subtask_gets_design_instructions(
        self,
        design_subtask: Subtask,
        parent_design_task: Task,
        ai_engine_mock: AIAnalysisEngine,
    ) -> None:
        """
        Test that a design subtask receives design-focused instructions.

        BUG: Currently fails because subtask name "Define the API endpoint
        specification" doesn't contain "design", so it defaults to
        implementation instructions.
        """
        # Arrange
        task = convert_subtask_to_task(design_subtask, parent_design_task)

        # Mock agent
        agent_mock = Mock()
        agent_mock.name = "TestAgent"
        agent_mock.role = "Developer"
        agent_mock.skills = ["api", "design"]

        # Act
        instructions = await ai_engine_mock.generate_task_instructions(
            task, agent_mock
        )

        # Assert - Design instructions should focus on planning, not coding
        instructions_lower = instructions.lower()

        # Should contain design-related keywords
        design_keywords = ["design", "specification", "document", "plan", "architecture"]
        has_design_keyword = any(keyword in instructions_lower for keyword in design_keywords)

        # Should NOT contain implementation-related keywords
        impl_keywords = ["implement", "write code", "build", "coding"]
        has_impl_keyword = any(keyword in instructions_lower for keyword in impl_keywords)

        assert has_design_keyword, (
            f"Design subtask should have design-focused instructions. "
            f"Instructions: {instructions}"
        )
        assert not has_impl_keyword, (
            f"Design subtask should NOT have implementation instructions. "
            f"Instructions: {instructions}"
        )

    async def test_implementation_subtask_gets_implementation_instructions(
        self, parent_design_task: Task, ai_engine_mock: AIAnalysisEngine
    ) -> None:
        """
        Test that an implementation subtask receives implementation instructions.
        """
        # Arrange - Create an implementation task
        impl_task = Task(
            id="parent_456",
            name="Implement Get Current Time",
            description="Build the API endpoint for getting current time",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            due_date=None,
            estimated_hours=8.0,
            dependencies=[],
            labels=["api", "implementation"],
            project_id="project_1",
            project_name="Test Project",
        )

        # Create implementation subtask
        impl_subtask = Subtask(
            id="parent_456_sub_1",
            parent_task_id="parent_456",
            name="Create endpoint handler",
            description="Build the FastAPI endpoint handler",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            estimated_hours=2.0,
            dependencies=[],
        )

        task = convert_subtask_to_task(impl_subtask, impl_task)

        # Mock agent
        agent_mock = Mock()
        agent_mock.name = "TestAgent"
        agent_mock.role = "Developer"
        agent_mock.skills = ["api", "python"]

        # Act
        instructions = await ai_engine_mock.generate_task_instructions(
            task, agent_mock
        )

        # Assert - Implementation instructions should focus on coding
        instructions_lower = instructions.lower()

        # Should contain implementation-related keywords
        impl_keywords = ["implement", "code", "build", "create"]
        has_impl_keyword = any(keyword in instructions_lower for keyword in impl_keywords)

        assert has_impl_keyword, (
            f"Implementation subtask should have implementation instructions. "
            f"Instructions: {instructions}"
        )

    async def test_testing_subtask_gets_testing_instructions(
        self, parent_design_task: Task, ai_engine_mock: AIAnalysisEngine
    ) -> None:
        """
        Test that a testing subtask receives testing-focused instructions.
        """
        # Arrange - Create a testing task
        test_task = Task(
            id="parent_789",
            name="Test Get Current Time",
            description="Write tests for the current time API endpoint",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            due_date=None,
            estimated_hours=4.0,
            dependencies=[],
            labels=["api", "testing"],
            project_id="project_1",
            project_name="Test Project",
        )

        # Create testing subtask
        test_subtask = Subtask(
            id="parent_789_sub_1",
            parent_task_id="parent_789",
            name="Write unit tests for time formatting",
            description="Create unit tests for the time formatting logic",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at="2024-01-01T00:00:00",
            estimated_hours=1.5,
            dependencies=[],
        )

        task = convert_subtask_to_task(test_subtask, test_task)

        # Mock agent
        agent_mock = Mock()
        agent_mock.name = "TestAgent"
        agent_mock.role = "Developer"
        agent_mock.skills = ["testing", "pytest"]

        # Act
        instructions = await ai_engine_mock.generate_task_instructions(
            task, agent_mock
        )

        # Assert - Testing instructions should focus on writing tests
        instructions_lower = instructions.lower()

        # Should contain testing-related keywords
        test_keywords = ["test", "coverage", "unit", "integration"]
        has_test_keyword = any(keyword in instructions_lower for keyword in test_keywords)

        assert has_test_keyword, (
            f"Testing subtask should have testing instructions. "
            f"Instructions: {instructions}"
        )
