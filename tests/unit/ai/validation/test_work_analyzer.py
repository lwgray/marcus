"""Unit tests for WorkAnalyzer validation engine.

Tests the core validation engine that:
1. Discovers source files from project_root
2. Gathers design artifacts and decisions
3. Validates implementations against acceptance criteria using AI
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.validation.validation_models import (
    SourceFile,
    ValidationSeverity,
    WorkEvidence,
)
from src.ai.validation.work_analyzer import WorkAnalyzer


class TestWorkAnalyzer:
    """Test suite for WorkAnalyzer."""

    @pytest.fixture
    def analyzer(self) -> WorkAnalyzer:
        """Create WorkAnalyzer instance for testing."""
        with patch("src.ai.validation.work_analyzer.LLMAbstraction"):
            return WorkAnalyzer()

    @pytest.fixture
    def mock_task(self) -> Mock:
        """Create a mock task with completion criteria.

        ``assigned_to`` is explicitly ``None`` so that
        ``WorkAnalyzer._get_project_root`` skips the worktree branch
        (added for GH-250 isolated agent worktrees). Without this,
        ``getattr(task, "assigned_to", None)`` on a vanilla ``Mock``
        returns a new ``Mock`` (Mock auto-generates attributes on
        access), which is truthy, so the worktree branch fires and
        ``main_repo.parent / "worktrees" / agent_id`` raises
        ``TypeError: unsupported operand type(s) for /: 'PosixPath'
        and 'Mock'``. Setting the attribute explicitly makes the
        mock behave like a task with no assigned agent.
        """
        task = Mock()
        task.id = "task-123"
        task.name = "Implement user registration"
        task.description = "Create user registration with email validation"
        task.type = "implementation"
        task.completion_criteria = [
            "Form includes email, password, confirm password fields",
            "Email validation implemented",
            "Password strength validation implemented",
            "Passwords match validation implemented",
        ]
        task.dependencies = []
        task.assigned_to = None
        return task

    @pytest.fixture
    def mock_state(self) -> Mock:
        """Create mock Marcus state."""
        state = Mock()
        state.task_artifacts = {}
        state.workspace_manager = Mock()
        state.workspace_manager.project_config = Mock()
        state.workspace_manager.project_config.main_workspace = "/fake/project/root"
        # Mock kanban_client._load_workspace_state() to return None
        # so code falls through to workspace_manager (which tests can update)
        state.kanban_client = Mock()
        state.kanban_client._load_workspace_state.return_value = None
        return state

    @pytest.mark.asyncio
    async def test_gather_evidence_gets_project_root_from_workspace(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test gathering evidence retrieves project_root from workspace manager."""
        # Mock os.walk to return empty (no files)
        with patch("src.ai.validation.work_analyzer.os.walk", return_value=[]):
            # Mock get_task_context
            with patch(
                "src.ai.validation.work_analyzer.get_task_context",
                new_callable=AsyncMock,
            ) as mock_context:
                mock_context.return_value = {
                    "success": True,
                    "context": {"decisions": []},
                }

                evidence = await analyzer.gather_evidence(mock_task, mock_state)

                assert evidence.project_root == "/fake/project/root"

    @pytest.mark.asyncio
    async def test_gather_evidence_discovers_source_files(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock, tmp_path: Path
    ) -> None:
        """Test source file discovery via directory scanning."""
        # Create temporary directory structure with real files
        src_dir = tmp_path / "src"
        src_dir.mkdir()

        # Create source files
        (src_dir / "app.py").write_text("print('hello')")
        (src_dir / "utils.js").write_text("console.log('hello');")
        (src_dir / "README.md").write_text("# README")  # Should be excluded

        # Update mock_state to use tmp_path
        mock_state.kanban_client._load_workspace_state.return_value = {
            "project_root": str(tmp_path)
        }

        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            evidence = await analyzer.gather_evidence(mock_task, mock_state)

            # Should find 2 source files (.py and .js), skip .md
            assert len(evidence.source_files) == 2
            assert any(f.extension == ".py" for f in evidence.source_files)
            assert any(f.extension == ".js" for f in evidence.source_files)
            # Verify content was read
            py_file = next(f for f in evidence.source_files if f.extension == ".py")
            assert "print('hello')" in py_file.content

    @pytest.mark.asyncio
    async def test_gather_evidence_detects_empty_files(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock, tmp_path: Path
    ) -> None:
        """Test empty file detection (0 bytes)."""
        # Create empty file
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "empty.py").write_text("")

        mock_state.kanban_client._load_workspace_state.return_value = {
            "project_root": str(tmp_path)
        }

        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            evidence = await analyzer.gather_evidence(mock_task, mock_state)

            assert len(evidence.source_files) == 1
            assert evidence.source_files[0].is_empty()
            assert evidence.source_files[0].size_bytes == 0

    @pytest.mark.asyncio
    async def test_gather_evidence_detects_placeholders(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock, tmp_path: Path
    ) -> None:
        """Test placeholder detection (TODO, FIXME, NotImplementedError)."""
        # Create file with placeholder
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "incomplete.py").write_text(
            "def foo():\n    # TODO: implement this\n    pass"
        )

        mock_state.kanban_client._load_workspace_state.return_value = {
            "project_root": str(tmp_path)
        }

        with patch(
            "src.ai.validation.work_analyzer.get_task_context",
            new_callable=AsyncMock,
        ) as mock_context:
            mock_context.return_value = {"success": True, "context": {"decisions": []}}

            evidence = await analyzer.gather_evidence(mock_task, mock_state)

            assert len(evidence.source_files) == 1
            assert evidence.source_files[0].has_placeholders is True

    @pytest.mark.asyncio
    async def test_gather_evidence_gets_design_artifacts(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test retrieval of design artifacts from state."""
        # Add artifacts to state
        mock_state.task_artifacts = {
            "task-123": [
                {
                    "filename": "api-spec.yaml",
                    "location": "docs/api/api-spec.yaml",
                    "artifact_type": "api",
                }
            ]
        }

        with patch("src.ai.validation.work_analyzer.os.walk", return_value=[]):
            with patch(
                "src.ai.validation.work_analyzer.get_task_context",
                new_callable=AsyncMock,
            ) as mock_context:
                mock_context.return_value = {
                    "success": True,
                    "context": {"decisions": []},
                }

                evidence = await analyzer.gather_evidence(mock_task, mock_state)

                assert len(evidence.design_artifacts) == 1
                assert evidence.design_artifacts[0]["filename"] == "api-spec.yaml"

    @pytest.mark.asyncio
    async def test_gather_evidence_gets_decisions_from_context(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test retrieval of decisions via get_task_context."""
        with patch("src.ai.validation.work_analyzer.os.walk", return_value=[]):
            with patch(
                "src.ai.validation.work_analyzer.get_task_context",
                new_callable=AsyncMock,
            ) as mock_context:
                mock_context.return_value = {
                    "success": True,
                    "context": {
                        "decisions": [
                            {
                                "what": "Use bcrypt for passwords",
                                "why": "Industry standard",
                                "impact": "All password fields",
                            }
                        ]
                    },
                }

                evidence = await analyzer.gather_evidence(mock_task, mock_state)

                assert len(evidence.decisions) == 1
                assert evidence.decisions[0]["what"] == "Use bcrypt for passwords"

    @pytest.mark.asyncio
    async def test_validate_implementation_task_passes_complete_implementation(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test validation passes when all criteria are met."""
        # Mock evidence with complete source code
        mock_evidence = WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/root/src/registration.js",
                    relative_path="src/registration.js",
                    size_bytes=2000,
                    content=(
                        "function validateEmail(email) { "
                        "return /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(email); }"
                        "\nfunction validatePassword(pwd) { "
                        "return pwd.length >= 8; }\n"
                        "function passwordsMatch(p1, p2) { "
                        "return p1 === p2; }"
                    ),
                    has_placeholders=False,
                    extension=".js",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        # Mock AI response (validation passes)
        mock_ai_response = """
VALIDATION RESULT: PASS

All acceptance criteria have been fully implemented:

1. ✅ Form includes email, password, confirm - VERIFIED in registration.js
2. ✅ Email validation implemented - validateEmail() function found
3. ✅ Password strength validation implemented - validatePassword() function found
4. ✅ Passwords match validation implemented - passwordsMatch() function found

The implementation is complete and functional.
"""

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            with patch.object(
                analyzer, "_validate_with_ai", return_value=mock_ai_response
            ):
                result = await analyzer.validate_implementation_task(
                    mock_task, mock_state
                )

                assert result.passed is True
                assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_validate_implementation_task_fails_missing_features(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test validation fails when features are missing."""
        # Mock evidence with incomplete implementation
        mock_evidence = WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/root/src/registration.js",
                    relative_path="src/registration.js",
                    size_bytes=500,
                    content=(
                        "function validateEmail(email) { return true; }  "
                        "// TODO: implement proper validation"
                    ),
                    has_placeholders=True,
                    extension=".js",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        # Mock AI response (validation fails)
        mock_ai_response = """
VALIDATION RESULT: FAIL

Missing implementations:

1. ❌ Password strength validation - No validatePassword() function found
   SEVERITY: CRITICAL
   EVIDENCE: Source code has no password validation logic
   REMEDIATION: Add validatePassword() function to check minimum 8 chars
   CRITERION: Password strength validation implemented

2. ❌ Passwords match validation - No passwordsMatch() function found
   SEVERITY: CRITICAL
   EVIDENCE: Source code has no password matching logic
   REMEDIATION: Add passwordsMatch(p1, p2) function to compare passwords
   CRITERION: Passwords match validation implemented
"""

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            with patch.object(
                analyzer, "_validate_with_ai", return_value=mock_ai_response
            ):
                result = await analyzer.validate_implementation_task(
                    mock_task, mock_state
                )

                assert result.passed is False
                assert len(result.issues) == 2
                assert result.issues[0].severity == ValidationSeverity.CRITICAL
                assert "password strength" in result.issues[0].issue.lower()

    @pytest.mark.asyncio
    async def test_validate_implementation_task_fails_empty_files(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test validation fails for empty source files."""
        # Mock evidence with empty file
        mock_evidence = WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/root/src/validation.js",
                    relative_path="src/validation.js",
                    size_bytes=0,
                    content="",
                    has_placeholders=False,
                    extension=".js",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        # Mock AI response (validation fails - empty file)
        mock_ai_response = """
VALIDATION RESULT: FAIL

1. ❌ Empty validation file - no features implemented
   SEVERITY: CRITICAL
   EVIDENCE: validation.js is 0 bytes
   REMEDIATION: Implement all validation functions
   CRITERION: Email validation implemented
"""

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            with patch.object(
                analyzer, "_validate_with_ai", return_value=mock_ai_response
            ):
                result = await analyzer.validate_implementation_task(
                    mock_task, mock_state
                )

                assert result.passed is False
                assert len(result.issues) >= 1
                assert "empty" in result.issues[0].issue.lower()

    @pytest.mark.asyncio
    async def test_validate_treats_fail_with_zero_issues_as_pass(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test that LLM returning fail with no issues is treated as pass.

        When the LLM says 'fail' but provides zero specific issues,
        there's nothing actionable — so we treat it as a pass.
        """
        mock_evidence = WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/root/src/app.py",
                    relative_path="src/app.py",
                    size_bytes=500,
                    content="def main(): pass",
                    has_placeholders=False,
                    extension=".py",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        # LLM returns fail with empty issues array
        mock_ai_response = '{"passed": false, "issues": []}'

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            with patch.object(
                analyzer,
                "_validate_with_ai",
                return_value=mock_ai_response,
            ):
                result = await analyzer.validate_implementation_task(
                    mock_task, mock_state
                )

                assert result.passed is True
                assert len(result.issues) == 0
                assert "Auto-passed" in result.ai_reasoning

    @pytest.mark.asyncio
    async def test_validate_implementation_task_no_source_files(
        self, analyzer: WorkAnalyzer, mock_task: Mock, mock_state: Mock
    ) -> None:
        """Test validation fails when no source files discovered."""
        # Mock evidence with NO source files
        mock_evidence = WorkEvidence(
            source_files=[],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            result = await analyzer.validate_implementation_task(mock_task, mock_state)

            assert result.passed is False
            assert len(result.issues) >= 1
            assert "no source files" in result.issues[0].issue.lower()
            # Should fail immediately without calling AI
