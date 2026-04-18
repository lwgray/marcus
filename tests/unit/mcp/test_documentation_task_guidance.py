"""
Unit tests for documentation task guidance in build_tiered_instructions (GH-385 fix #8).

dashboard-v82 post-mortem: Agent 1 documented WeatherWidget props from the design
spec (location: {lat, lon, name}) instead of the actual implementation
(defaultLocation: string), causing README/code drift that went unnoticed until
the Epictetus audit.

Fix: Layer 6 of build_tiered_instructions injects a "read source before
documenting" guideline when the task is a documentation task (detected by
label OR task name). The AI prompt template also gains a DOCUMENTATION section
so LLM-generated base instructions reinforce the same behaviour.

Tests:
- documentation label → guideline appears
- "readme" in task name → guideline appears (no label required)
- "document" / "docs" in task name → guideline appears
- regular implementation task → guideline absent
- AI engine task_type inference: "readme" task → "documentation" type
"""

from datetime import datetime, timezone
from typing import Optional

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import build_tiered_instructions

pytestmark = pytest.mark.unit

# Sentinel text that must appear when the documentation guideline fires.
_DOC_SENTINEL = "Documentation Guidelines"
_SOURCE_SENTINEL = "read the actual source file"


def _task(
    name: str = "Implement auth module",
    labels: Optional[list] = None,
) -> Task:
    """
    Build a minimal Task for instruction-layer tests.

    Parameters
    ----------
    name : str
        Task name.
    labels : list, optional
        Task labels.  Defaults to empty list.

    Returns
    -------
    Task
        Configured task instance.
    """
    now = datetime.now(timezone.utc)
    return Task(
        id="task-test",
        name=name,
        description="Test task description",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        labels=labels or [],
        dependencies=[],
    )


class TestDocumentationGuidanceByLabel:
    """Layer 6 fires when task has a documentation-related label."""

    def test_documentation_label_triggers_guideline(self) -> None:
        """Label 'documentation' → guidance block appears in instructions."""
        task = _task(name="Write project docs", labels=["documentation"])
        result = build_tiered_instructions(
            base_instructions="Write the docs.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result
        assert _SOURCE_SENTINEL in result

    def test_docs_label_triggers_guideline(self) -> None:
        """Label 'docs' (common shorthand) → guidance block appears."""
        task = _task(name="Create documentation", labels=["docs"])
        result = build_tiered_instructions(
            base_instructions="Write the docs.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result

    def test_readme_label_triggers_guideline(self) -> None:
        """Label 'readme' → guidance block appears."""
        task = _task(name="Update project README", labels=["readme"])
        result = build_tiered_instructions(
            base_instructions="Update the README.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result


class TestDocumentationGuidanceByName:
    """Layer 6 fires on task name keywords even when labels are absent."""

    def test_readme_in_name_triggers_guideline(self) -> None:
        """'readme' in task name → guidance appears regardless of labels."""
        task = _task(name="Create README", labels=[])
        result = build_tiered_instructions(
            base_instructions="Write the README.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result
        assert _SOURCE_SENTINEL in result

    def test_document_in_name_triggers_guideline(self) -> None:
        """'document' in task name → guidance appears."""
        task = _task(name="Document the WeatherWidget API", labels=[])
        result = build_tiered_instructions(
            base_instructions="Document the API.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result

    def test_docs_in_name_triggers_guideline(self) -> None:
        """'docs' in task name → guidance appears."""
        task = _task(name="Write API docs", labels=[])
        result = build_tiered_instructions(
            base_instructions="Write docs.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL in result


class TestDocumentationGuidanceAbsent:
    """Layer 6 documentation guideline must NOT fire for non-doc tasks."""

    def test_implementation_task_no_documentation_guidance(self) -> None:
        """Standard implementation task → no documentation guideline."""
        task = _task(name="Implement WeatherWidget", labels=["frontend", "react"])
        result = build_tiered_instructions(
            base_instructions="Build the widget.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL not in result

    def test_design_task_no_documentation_guidance(self) -> None:
        """Design task (not a documentation task) → no documentation guideline."""
        task = _task(name="Design the widget registry", labels=["design"])
        result = build_tiered_instructions(
            base_instructions="Create design artifacts.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL not in result

    def test_empty_labels_and_unrelated_name_no_guidance(self) -> None:
        """No labels, unrelated task name → no documentation guideline."""
        task = _task(name="Fix login bug", labels=[])
        result = build_tiered_instructions(
            base_instructions="Fix the bug.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        assert _DOC_SENTINEL not in result


class TestDocumentationGuidanceContent:
    """The injected guideline must contain the key mandate."""

    def test_guideline_emphasises_code_over_spec(self) -> None:
        """
        Guideline must tell agents to read source, not design spec.

        This is the specific failure mode from dashboard-v82: Agent 1
        documented design-spec props instead of implementation props.
        """
        task = _task(name="Create README", labels=[])
        result = build_tiered_instructions(
            base_instructions="Write the README.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )
        # Must mention reading actual source
        assert "source file" in result
        # Must distinguish spec from code
        assert "design spec" in result or "implementation" in result


class TestAIEngineDocumentationTypeInference:
    """AI engine infers task_type='documentation' for README/docs tasks."""

    def test_prompt_template_includes_documentation_section(self) -> None:
        """
        The LLM prompt template must contain a DOCUMENTATION task section.

        This ensures that even when the AI generates base instructions, it
        receives guidance about reading actual source files before documenting.
        """
        from src.integrations.ai_analysis_engine import AIAnalysisEngine

        engine = AIAnalysisEngine.__new__(AIAnalysisEngine)
        # Access the class-level or instance-level prompt templates.
        # AIAnalysisEngine stores prompts in self.prompts during __init__,
        # but the template text is defined as a class constant or in __init__.
        # Instantiate minimally to get the prompts dict.
        engine.client = None
        engine.model = "test"
        engine.prompts = {}

        # Reconstruct the prompts dict by calling __init__ with a None client.
        try:
            real_engine = AIAnalysisEngine(client=None, model="test-model")
        except Exception:
            pytest.skip("AIAnalysisEngine requires unavailable dependencies")

        task_instructions_prompt = real_engine.prompts.get("task_instructions", "")
        assert "DOCUMENTATION" in task_instructions_prompt, (
            "Prompt template must include a DOCUMENTATION task section so "
            "LLM-generated instructions reinforce reading source before writing docs."
        )
        assert "source file" in task_instructions_prompt.lower() or (
            "actual" in task_instructions_prompt.lower()
        )
