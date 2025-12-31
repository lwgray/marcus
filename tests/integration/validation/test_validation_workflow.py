"""
Integration tests for validation workflow.

Tests the validation workflow helper functions and integration.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import _validate_task_completion


class TestValidationWorkflow:
    """Test validation workflow integration with report_task_progress."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self) -> None:
        """Reset module-level singletons before each test."""
        import src.marcus_mcp.tools.task as task_module

        task_module._work_analyzer = None
        task_module._retry_tracker = None

    @pytest.fixture
    def mock_state(self) -> Mock:
        """Create mock Marcus state."""
        state = Mock()
        state.workspace_manager = Mock()
        state.workspace_manager.project_config = Mock()
        state.workspace_manager.project_config.main_workspace = "/fake/project"
        state.task_artifacts = {}
        state.project_tasks = []
        state.agent_status = {}
        state.agent_tasks = {}
        state.subtask_manager = None  # No subtasks for these tests
        state.lease_manager = None  # No lease management for these tests
        # Mock kanban_client with async methods
        state.kanban_client = AsyncMock()
        state.kanban_client.update_task = AsyncMock(return_value=True)
        state.kanban_client.update_task_progress = AsyncMock(return_value=True)
        state.kanban_client.add_comment = AsyncMock(return_value=True)
        state.kanban_client.get_task_by_id = AsyncMock(return_value=None)
        state.assignment_persistence = AsyncMock()
        state.assignment_persistence.save_task_assignment = AsyncMock()
        state.assignment_persistence.clear_task_assignment = AsyncMock()
        state.assignment_persistence.remove_assignment = AsyncMock()
        # Mock memory
        state.memory = AsyncMock()
        state.memory.record_task_completion = AsyncMock()
        # Mock AI engine for blocker analysis
        state.ai_engine = AsyncMock()
        state.ai_engine.analyze_blocker = AsyncMock(
            return_value="AI generated suggestions"
        )
        # Mock code_analyzer
        state.code_analyzer = None  # Not used in validation tests
        return state

    @pytest.fixture
    def implementation_task(self) -> Task:
        """Create implementation task with acceptance criteria."""
        task = Task(
            id="task-123",
            name="Implement warranty form",
            description="Create HTML form with validation",
            priority=Priority.HIGH,
            status=TaskStatus.IN_PROGRESS,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
            labels=["implement", "frontend"],
        )
        # Add completion_criteria as list (WorkAnalyzer expects list)
        task.completion_criteria = [  # type: ignore[assignment]
            "Form includes fields for name, email, phone",
            "Fields are properly validated",
            "Professional CSS styling applied",
        ]
        return task

    @pytest.fixture
    def design_task(self) -> Task:
        """Create design task (should skip validation)."""
        task = Task(
            id="task-456",
            name="Design API specification",
            description="Create OpenAPI spec",
            priority=Priority.MEDIUM,
            status=TaskStatus.IN_PROGRESS,
            assigned_to="agent-1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=2.0,
            labels=["design", "api"],
        )
        return task

    @pytest.mark.asyncio
    async def test_validation_passes_complete_implementation(
        self, mock_state: Mock, implementation_task: Task, tmp_path: Path
    ) -> None:
        """Test validation passes when implementation is complete."""
        # Create complete implementation
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # warranty-form.html with all fields
        (src_dir / "warranty-form.html").write_text(
            """
        <form id="warranty-form">
            <input name="name" required>
            <input name="email" type="email" required>
            <input name="phone" required>
        </form>
        """
        )

        # validation.js with validation functions
        (src_dir / "validation.js").write_text(
            """
        function validateEmail(email) {
            return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email);
        }
        function validatePhone(phone) {
            return /^\\d{3}-\\d{3}-\\d{4}$/.test(phone);
        }
        """
        )

        # styles.css with professional styling
        (src_dir / "styles.css").write_text(
            """
        .form-container {
            padding: 20px;
            border-radius: 8px;
        }
        input {
            border: 1px solid #ccc;
            padding: 8px;
        }
        """
        )

        mock_state.workspace_manager.project_config.main_workspace = str(tmp_path)
        mock_state.project_tasks = [implementation_task]

        # Mock AI validation to pass
        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            # Mock the LLMAbstraction.analyze method
            with patch("src.ai.validation.work_analyzer.LLMAbstraction") as MockLLM:
                mock_llm_instance = MockLLM.return_value
                mock_llm_instance.analyze = AsyncMock(
                    return_value="""
VALIDATION RESULT: PASS

✅ Form includes all required fields - VERIFIED in warranty-form.html
✅ Fields are properly validated - VERIFIED in validation.js
✅ Professional CSS styling applied - VERIFIED in styles.css

All acceptance criteria have been met with working code.
"""
                )

                # Test the validation helper directly
                validation_result = await _validate_task_completion(
                    implementation_task, "agent-1", mock_state
                )

                # Should pass validation
                assert validation_result.passed is True
                assert len(validation_result.issues) == 0

    @pytest.mark.asyncio
    async def test_validation_fails_missing_features(
        self, mock_state: Mock, implementation_task: Task, tmp_path: Path
    ) -> None:
        """Test validation fails when features are missing."""
        # Create incomplete implementation (missing phone validation)
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # warranty-form.html has phone field
        (src_dir / "warranty-form.html").write_text(
            """
        <form id="warranty-form">
            <input name="name" required>
            <input name="email" type="email" required>
            <input name="phone" required>
        </form>
        """
        )

        # validation.js missing validatePhone function!
        (src_dir / "validation.js").write_text(
            """
        function validateEmail(email) {
            return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email);
        }
        """
        )

        mock_state.workspace_manager.project_config.main_workspace = str(tmp_path)
        mock_state.project_tasks = [implementation_task]

        # Mock AI validation to fail
        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            # Mock the LLMAbstraction.analyze method
            with patch("src.ai.validation.work_analyzer.LLMAbstraction") as MockLLM:
                mock_llm_instance = MockLLM.return_value
                mock_llm_instance.analyze = AsyncMock(
                    return_value="""
VALIDATION RESULT: FAIL

✅ Form includes all required fields - VERIFIED in warranty-form.html
❌ Phone number validation not implemented
   SEVERITY: CRITICAL
   EVIDENCE: Code has <input name='phone'> but no validatePhone()
   REMEDIATION: Add validatePhone() to check format /^\\d{3}-\\d{3}-\\d{4}$/
   CRITERION: Fields are properly validated
"""
                )

                from src.ai.validation.work_analyzer import WorkAnalyzer

                # Test validation directly (without retry tracking)
                analyzer = WorkAnalyzer()
                validation_result = await analyzer.validate_implementation_task(
                    implementation_task, mock_state
                )

                # Should fail validation
                assert validation_result.passed is False
                assert len(validation_result.issues) == 1
                assert (
                    "Phone number validation not implemented"
                    in validation_result.issues[0].issue
                )
                assert validation_result.issues[0].severity.value == "critical"

    @pytest.mark.asyncio
    async def test_validation_skipped_for_design_tasks(
        self, mock_state: Mock, design_task: Task
    ) -> None:
        """Test validation is skipped for non-implementation tasks."""
        from src.ai.validation.task_filter import should_validate_task

        # Design task should not be validated
        assert should_validate_task(design_task) is False

    @pytest.mark.asyncio
    async def test_validation_creates_blocker_on_retry_with_same_issues(
        self, mock_state: Mock, implementation_task: Task, tmp_path: Path
    ) -> None:
        """Test blocker creation when agent retries with same issues."""
        # Create incomplete implementation
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "validation.js").write_text("")  # Empty file

        mock_state.workspace_manager.project_config.main_workspace = str(tmp_path)
        mock_state.project_tasks = [implementation_task]

        # Mock AI to always return same failure
        validation_response = """
VALIDATION RESULT: FAIL

❌ No validation functions implemented
   SEVERITY: CRITICAL
   EVIDENCE: validation.js is empty (0 bytes)
   REMEDIATION: Add validateEmail() and validatePhone() functions
   CRITERION: Fields are properly validated
"""

        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            # Mock the LLMAbstraction.analyze method
            with patch("src.ai.validation.work_analyzer.LLMAbstraction") as MockLLM:
                mock_llm_instance = MockLLM.return_value
                mock_llm_instance.analyze = AsyncMock(return_value=validation_response)

                from src.ai.validation.retry_tracker import RetryTracker
                from src.ai.validation.work_analyzer import WorkAnalyzer

                analyzer = WorkAnalyzer()
                tracker = RetryTracker()

                # First attempt - should fail with remediation
                validation_result1 = await analyzer.validate_implementation_task(
                    implementation_task, mock_state
                )

                # Check retry detection BEFORE recording (should be False - no history)
                is_retry1 = tracker.is_retry_with_same_issues(
                    implementation_task.id, validation_result1
                )
                assert is_retry1 is False

                # Now record first attempt
                tracker.record_attempt(implementation_task.id, validation_result1)

                # Second attempt with SAME issue
                validation_result2 = await analyzer.validate_implementation_task(
                    implementation_task, mock_state
                )

                # Check retry BEFORE recording (True - same as first)
                is_retry2 = tracker.is_retry_with_same_issues(
                    implementation_task.id, validation_result2
                )
                assert is_retry2 is True  # Same issues - blocker should be created

                # Record second attempt
                tracker.record_attempt(implementation_task.id, validation_result2)

                # Verify we have 2 attempts recorded
                assert tracker.get_attempt_count(implementation_task.id) == 2

    @pytest.mark.asyncio
    async def test_validation_no_blocker_on_different_issues(
        self, mock_state: Mock, implementation_task: Task, tmp_path: Path
    ) -> None:
        """Test no blocker when agent fixes some issues and retries."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "validation.js").write_text("")

        mock_state.workspace_manager.project_config.main_workspace = str(tmp_path)
        mock_state.project_tasks = [implementation_task]

        # First validation - missing validateEmail
        first_response = """
VALIDATION RESULT: FAIL

❌ Email validation not implemented
   SEVERITY: CRITICAL
   EVIDENCE: validation.js has no validateEmail() function
   REMEDIATION: Add validateEmail() function
   CRITERION: Fields are properly validated
"""

        # Second validation - missing validatePhone (different issue!)
        second_response = """
VALIDATION RESULT: FAIL

❌ Phone validation not implemented
   SEVERITY: CRITICAL
   EVIDENCE: validation.js has no validatePhone() function
   REMEDIATION: Add validatePhone() function
   CRITERION: Fields are properly validated
"""

        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            # Mock the LLMAbstraction.analyze method
            with patch("src.ai.validation.work_analyzer.LLMAbstraction") as MockLLM:
                mock_llm_instance = MockLLM.return_value

                from src.ai.validation.retry_tracker import RetryTracker
                from src.ai.validation.work_analyzer import WorkAnalyzer

                analyzer = WorkAnalyzer()
                tracker = RetryTracker()

                # First attempt
                mock_llm_instance.analyze = AsyncMock(return_value=first_response)

                validation_result1 = await analyzer.validate_implementation_task(
                    implementation_task, mock_state
                )

                assert validation_result1.passed is False
                assert (
                    "Email validation not implemented"
                    in validation_result1.issues[0].issue
                )

                # Record first attempt
                tracker.record_attempt(implementation_task.id, validation_result1)

                # Second attempt - different issue (email fixed, phone missing)
                mock_llm_instance.analyze = AsyncMock(return_value=second_response)

                validation_result2 = await analyzer.validate_implementation_task(
                    implementation_task, mock_state
                )

                assert validation_result2.passed is False
                assert (
                    "Phone validation not implemented"
                    in validation_result2.issues[0].issue
                )

                # Check that this is NOT detected as retry with same issues
                is_retry = tracker.is_retry_with_same_issues(
                    implementation_task.id, validation_result2
                )
                assert is_retry is False  # Different issues - not a retry
