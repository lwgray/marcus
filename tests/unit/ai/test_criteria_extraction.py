"""Unit tests for WorkAnalyzer._extract_criteria and empty-criteria auto-pass.

Validates:
1. dict-form completion_criteria extracts the list, not the keys
2. list-form acceptance_criteria returned as-is
3. nested dict with 'criteria' key extracted correctly
4. empty / None criteria → empty list (triggers auto-pass)
5. _validate_with_ai returns auto-pass JSON when criteria is empty
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.validation.work_analyzer import WorkAnalyzer
from src.core.models import Priority, Task, TaskStatus

pytestmark = pytest.mark.unit


def _make_task(
    task_id: str = "task-1",
    completion_criteria: object = None,
    acceptance_criteria: list | None = None,
) -> Task:
    """Build a minimal task fixture."""
    now = datetime.now(timezone.utc)
    t = Task(
        id=task_id,
        name="Test task",
        description="Build a widget",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.MEDIUM,
        assigned_to="agent-1",
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        dependencies=[],
        labels=[],
    )
    t.completion_criteria = completion_criteria  # type: ignore[assignment]
    if acceptance_criteria is not None:
        t.acceptance_criteria = acceptance_criteria
    return t


class TestExtractCriteria:
    """Tests for WorkAnalyzer._extract_criteria()."""

    @pytest.fixture
    def analyzer(self) -> WorkAnalyzer:
        """WorkAnalyzer instance with LLM mocked (pure method tests)."""
        with patch("src.ai.validation.work_analyzer.LLMAbstraction"):
            return WorkAnalyzer()

    def test_dict_with_criteria_key_extracts_list(self, analyzer: WorkAnalyzer) -> None:
        """Dict completion_criteria with 'criteria' key returns the list, not keys."""
        task = _make_task(
            completion_criteria={
                "criteria": ["Feature A implemented", "Feature B implemented"],
                "type": "contract_first",
            }
        )
        result = analyzer._extract_criteria(task)
        assert result == [
            "Feature A implemented",
            "Feature B implemented",
        ], "_extract_criteria must return list values, not dict keys"

    def test_dict_with_items_key_extracts_list(self, analyzer: WorkAnalyzer) -> None:
        """Dict with 'items' key also supported."""
        task = _make_task(completion_criteria={"items": ["Criterion 1", "Criterion 2"]})
        result = analyzer._extract_criteria(task)
        assert result == ["Criterion 1", "Criterion 2"]

    def test_dict_without_known_key_extracts_first_list_value(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """Unknown dict key — extract first list-typed value."""
        task = _make_task(
            completion_criteria={"custom_key": ["A", "B"], "string_key": "ignored"}
        )
        result = analyzer._extract_criteria(task)
        assert result == ["A", "B"]

    def test_list_completion_criteria_returned_as_is(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """List-form completion_criteria (unusual but valid) returned directly."""
        task = _make_task(completion_criteria=["Criterion X", "Criterion Y"])
        result = analyzer._extract_criteria(task)
        assert result == ["Criterion X", "Criterion Y"]

    def test_none_completion_criteria_falls_back_to_acceptance_criteria(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """None completion_criteria → fallback to acceptance_criteria."""
        task = _make_task(
            completion_criteria=None,
            acceptance_criteria=["AC 1", "AC 2"],
        )
        result = analyzer._extract_criteria(task)
        assert result == ["AC 1", "AC 2"]

    def test_empty_dict_falls_back_to_acceptance_criteria(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """Empty dict (falsy) → fallback to acceptance_criteria."""
        task = _make_task(
            completion_criteria={},
            acceptance_criteria=["AC fallback"],
        )
        result = analyzer._extract_criteria(task)
        assert result == ["AC fallback"]

    def test_none_both_returns_empty_list(self, analyzer: WorkAnalyzer) -> None:
        """No criteria anywhere → empty list."""
        task = _make_task(completion_criteria=None, acceptance_criteria=[])
        result = analyzer._extract_criteria(task)
        assert result == []

    def test_iterating_dict_keys_was_the_bug(self, analyzer: WorkAnalyzer) -> None:
        """Regression: old code did enumerate(criteria) where criteria was a dict.

        That gives dict KEYS ('criteria', 'type'), not the criterion strings.
        The fixed _extract_criteria must NOT return the keys.
        """
        task = _make_task(
            completion_criteria={
                "criteria": ["Real criterion"],
                "type": "contract_first",
            }
        )
        result = analyzer._extract_criteria(task)
        assert "criteria" not in result, "Must not return dict keys"
        assert "type" not in result, "Must not return dict keys"
        assert "Real criterion" in result


class TestValidateWithAIEmptyCriteria:
    """_validate_with_ai auto-passes when criteria is empty (no LLM call)."""

    @pytest.fixture
    def analyzer(self) -> WorkAnalyzer:
        """WorkAnalyzer with mocked LLM."""
        with patch("src.ai.validation.work_analyzer.LLMAbstraction"):
            return WorkAnalyzer()

    @pytest.mark.asyncio
    async def test_empty_criteria_auto_passes_without_llm_call(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """When criteria is empty, _validate_with_ai returns pass JSON immediately."""
        from src.ai.validation.validation_models import WorkEvidence

        task = _make_task(completion_criteria=None, acceptance_criteria=[])
        evidence = WorkEvidence(
            source_files=[],
            design_artifacts=[],
            decisions=[],
            project_root="/tmp/test",  # nosec B108
        )

        # Patch LLM so any call would fail — auto-pass must NOT call it
        analyzer._validation_llm = MagicMock()
        analyzer._validation_llm.analyze = AsyncMock(
            side_effect=RuntimeError("LLM called")
        )

        response = await analyzer._validate_with_ai(task, evidence)

        import json

        parsed = json.loads(response)
        assert parsed["passed"] is True, (
            "_validate_with_ai must auto-pass when criteria is empty, "
            "not call the LLM (which would hallucinate issues)"
        )
        assert parsed["issues"] == []

    @pytest.mark.asyncio
    async def test_with_criteria_calls_llm(self, analyzer: WorkAnalyzer) -> None:
        """Non-empty criteria → LLM is called (normal path)."""
        from src.ai.validation.validation_models import WorkEvidence

        task = _make_task(acceptance_criteria=["Feature X must work"])
        evidence = WorkEvidence(
            source_files=[],
            design_artifacts=[],
            decisions=[],
            project_root="/tmp/test",  # nosec B108
        )

        llm_response = '{"passed": true, "issues": [], "reasoning": "ok"}'
        analyzer._validation_llm = MagicMock()
        analyzer._validation_llm.analyze = AsyncMock(return_value=llm_response)

        response = await analyzer._validate_with_ai(task, evidence)

        analyzer._validation_llm.analyze.assert_called_once()
        assert response == llm_response
