"""
Unit tests for mandatory workflow enforcement (Issue #168).

This module tests the mandatory workflow prompt that ensures agents
follow the proper workflow steps when receiving task assignments.
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import (
    _build_mandatory_workflow_prompt,
    _get_task_type,
    build_tiered_instructions,
)


def create_test_task(
    task_id: str = "task-123",
    name: str = "Sample Task",  # Changed from "Test Task" to avoid "test" keyword
    description: str = "Task description",
    status: TaskStatus = TaskStatus.TODO,
    labels: Optional[list[str]] = None,
    dependencies: Optional[list[str]] = None,
    estimated_hours: float = 4.0,
) -> Task:
    """
    Create a test task with minimal required fields.

    Parameters
    ----------
    task_id : str
        Task ID
    name : str
        Task name
    description : str
        Task description
    status : TaskStatus
        Task status
    labels : Optional[list[str]]
        Task labels
    dependencies : Optional[list[str]]
        Task dependencies
    estimated_hours : float
        Estimated hours

    Returns
    -------
    Task
        A test task instance
    """
    now = datetime.now(timezone.utc)
    task = Task(
        id=task_id,
        name=name,
        description=description,
        status=status,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=estimated_hours,
        labels=labels or [],
        dependencies=dependencies or [],
    )
    return task


class TestMandatoryWorkflowPrompt:
    """Test suite for mandatory workflow prompt generation."""

    def test_workflow_prompt_includes_all_steps(self) -> None:
        """Test workflow prompt includes all 9 required steps."""
        task = create_test_task()

        prompt = _build_mandatory_workflow_prompt(task)

        # Verify all steps present
        assert "1. Call get_task_context" in prompt
        assert "2. Read artifacts" in prompt
        assert "3. [TASK WORK:" in prompt
        assert "4. Report progress at 25%, 50%, 75%" in prompt
        assert "5. Log decisions" in prompt
        assert '6. BEFORE reporting "completed", verify:' in prompt
        assert "7. Report completion" in prompt
        assert "8. Be prepared for remediation" in prompt
        assert "9. Immediately request next task" in prompt

    def test_workflow_prompt_embeds_task_info(self) -> None:
        """Test workflow prompt embeds task name and description."""
        task = create_test_task(
            name="Implement User API",
            description="Build REST endpoints for user management",
        )

        prompt = _build_mandatory_workflow_prompt(task)

        assert "Implement User API" in prompt
        assert "Build REST endpoints for user management" in prompt

    def test_workflow_prompt_marked_mandatory(self) -> None:
        """Test workflow prompt clearly marked as mandatory."""
        task = create_test_task(name="Sample", description="Sample work")

        prompt = _build_mandatory_workflow_prompt(task)

        assert "MANDATORY" in prompt
        assert "CRITICAL BEHAVIORS" in prompt
        assert "must write a todo list" in prompt.lower()

    def test_workflow_prompt_includes_critical_behaviors(self) -> None:
        """Test workflow prompt includes all critical behavior guidelines."""
        task = create_test_task(name="Sample", description="Sample work")

        prompt = _build_mandatory_workflow_prompt(task)

        # Check for specific critical behaviors
        assert "Check dependencies with get_task_context BEFORE" in prompt
        assert "Read artifacts from dependency tasks" in prompt
        assert "Report progress at each milestone" in prompt
        assert "Log decisions as they're made" in prompt
        assert "Be ready to address validation feedback" in prompt

    def test_workflow_prompt_requires_todo_list(self) -> None:
        """Test workflow prompt explicitly requires a todo list."""
        task = create_test_task(name="Sample", description="Sample work")

        prompt = _build_mandatory_workflow_prompt(task)

        assert "write a todo list" in prompt.lower()

    def test_workflow_prompt_with_long_task_description(self) -> None:
        """Test workflow prompt handles long task descriptions."""
        long_description = (
            "This is a very long description " * 20
        )  # ~140 chars * 20 = 2800 chars
        task = create_test_task(
            name="Complex Task",
            description=long_description,
        )

        prompt = _build_mandatory_workflow_prompt(task)

        # Prompt should include the full description
        assert long_description in prompt
        assert "Complex Task" in prompt


class TestGetTaskType:
    """Test suite for _get_task_type() helper function."""

    def test_defaults_to_implementation(self) -> None:
        """Test defaults to implementation type."""
        task = create_test_task(
            name="Generic Task",
            description="Do something",
            labels=[],
        )
        assert _get_task_type(task) == "implementation"

    def test_detects_design_from_name(self) -> None:
        """Test detects design tasks from name."""
        task = create_test_task(
            name="Design user interface",
            description="Create UI mockups",
            labels=[],
        )
        assert _get_task_type(task) == "design"

    def test_detects_design_from_label(self) -> None:
        """Test detects design tasks from type:design label."""
        task = create_test_task(
            name="UI Mockups",
            description="Create mockups",
            labels=["type:design"],
        )
        assert _get_task_type(task) == "design"

    def test_detects_testing_from_name(self) -> None:
        """Test detects testing tasks from name."""
        task = create_test_task(
            name="Test authentication flow",
            description="Write unit tests",
            labels=[],
        )
        assert _get_task_type(task) == "testing"

    def test_detects_testing_from_label(self) -> None:
        """Test detects testing tasks from type:testing label."""
        task = create_test_task(
            name="Unit Tests",
            description="Add test coverage",
            labels=["type:testing"],
        )
        assert _get_task_type(task) == "testing"

    def test_parent_task_type_takes_precedence(self) -> None:
        """Test _parent_task_type attribute overrides inference."""
        task = create_test_task(
            name="Design something",  # Would infer as "design"
            description="Create design",
            labels=[],
        )
        # Simulate subtask with parent task type
        task._parent_task_type = "implementation"  # type: ignore[attr-defined]

        assert _get_task_type(task) == "implementation"

    def test_case_insensitive_name_matching(self) -> None:
        """Test name matching is case-insensitive."""
        task = create_test_task(
            name="DESIGN User Flow",
            description="Flow diagrams",
            labels=[],
        )
        assert _get_task_type(task) == "design"


class TestTieredInstructionsWithWorkflow:
    """Test suite for workflow integration into tiered instructions."""

    def test_workflow_is_first_layer(self) -> None:
        """Test workflow prompt appears before base instructions for implementation tasks."""
        task = create_test_task()  # Defaults to implementation type
        base = "Base instructions here"

        instructions = build_tiered_instructions(
            base_instructions=base,
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # Workflow should appear before base instructions
        workflow_pos = instructions.find("MANDATORY WORKFLOW")
        base_pos = instructions.find("Base instructions here")

        assert workflow_pos < base_pos
        assert workflow_pos >= 0
        assert base_pos > 0

    def test_workflow_only_for_implementation_tasks(self) -> None:
        """Test workflow included only for implementation tasks."""
        # Implementation tasks should get workflow (default type)
        implementation_tasks = [
            create_test_task(
                task_id="1",
                name="Implement user auth",
                description="Code authentication",
            ),
            create_test_task(
                task_id="2",
                name="Build API",
                description="Create endpoints",
            ),
            create_test_task(
                task_id="3",
                name="Fix Bug",
                description="Fix authentication bug",
            ),
        ]

        for task in implementation_tasks:
            instructions = build_tiered_instructions(
                base_instructions="Base",
                task=task,
                context_data=None,
                dependency_awareness=None,
                predictions=None,
            )

            assert "MANDATORY WORKFLOW" in instructions
            assert "write a todo list" in instructions.lower()

        # Non-implementation tasks should NOT get workflow
        non_implementation_tasks = [
            create_test_task(
                task_id="4",
                name="Design UI mockups",
                description="Create wireframes",
            ),
            create_test_task(
                task_id="5",
                name="Task with design label",
                description="Design work",
                labels=["type:design"],
            ),
            create_test_task(
                task_id="6",
                name="Test authentication",
                description="Write unit tests",
            ),
        ]

        for task in non_implementation_tasks:
            instructions = build_tiered_instructions(
                base_instructions="Base",
                task=task,
                context_data=None,
                dependency_awareness=None,
                predictions=None,
            )

            assert "MANDATORY WORKFLOW" not in instructions

    def test_workflow_with_all_instruction_layers(self) -> None:
        """Test workflow coexists with all other instruction layers."""
        task = create_test_task(
            name="API Task",
            description="Build API",
            labels=["api", "backend"],
            dependencies=["task-100"],
            estimated_hours=4.0,
        )
        # Set subtask attributes
        task._is_subtask = True  # type: ignore[attr-defined]
        task._parent_task_name = "Parent Task"  # type: ignore[attr-defined]
        task._complexity = "standard"  # type: ignore[attr-defined]

        context_data = {
            "previous_implementations": [{"file": "test.py"}],
            "dependent_tasks": ["task-200", "task-201", "task-202"],
        }

        dependency_awareness = "3 tasks depend on your work"

        predictions = {
            "success_probability": 0.5,
            "completion_time": {
                "expected_hours": 4.0,
                "confidence_interval": {"lower": 3.0, "upper": 5.0},
            },
        }

        instructions = build_tiered_instructions(
            base_instructions="Base instructions",
            task=task,
            context_data=context_data,
            dependency_awareness=dependency_awareness,
            predictions=predictions,
        )

        # All layers should be present
        assert "MANDATORY WORKFLOW" in instructions  # Layer 0
        assert "Base instructions" in instructions  # Layer 1
        assert "TIME BUDGET" in instructions  # Layer 1.5 (subtask)
        assert "IMPLEMENTATION CONTEXT" in instructions  # Layer 2
        assert "DEPENDENCY AWARENESS" in instructions  # Layer 3
        assert "ARCHITECTURAL DECISIONS" in instructions  # Layer 4
        assert "PREDICTIONS & INSIGHTS" in instructions  # Layer 5
        assert "API Guidelines" in instructions  # Layer 6

    def test_workflow_layer_zero_position(self) -> None:
        """Test workflow is truly Layer 0 (appears first) for implementation tasks."""
        task = create_test_task()  # Defaults to implementation type

        instructions = build_tiered_instructions(
            base_instructions="Base instructions",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # Split into lines and find first substantial content
        lines = [line.strip() for line in instructions.split("\n") if line.strip()]

        # First non-empty line should contain workflow marker
        assert "MANDATORY WORKFLOW" in lines[0]

    def test_workflow_with_minimal_task(self) -> None:
        """Test workflow works with minimal task information for implementation tasks."""
        task = create_test_task(
            task_id="1",
            name="Minimal",
            description="",
        )  # Defaults to implementation type

        instructions = build_tiered_instructions(
            base_instructions="Base",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # Workflow should still be present even with minimal task info
        assert "MANDATORY WORKFLOW" in instructions
        assert "Minimal" in instructions

    def test_workflow_with_special_characters_in_task(self) -> None:
        """Test workflow handles special characters in task name/description."""
        task = create_test_task(
            name="Fix bug in user's API endpoint",
            description='Handle "quoted" text & special <chars>',
        )

        prompt = _build_mandatory_workflow_prompt(task)

        # Should preserve special characters
        assert "Fix bug in user's API endpoint" in prompt
        assert 'Handle "quoted" text & special <chars>' in prompt
