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

        # Mock AI response with verifiable file:line citations.
        # The content at line 1 is the validateEmail TODO, which
        # proves the file has placeholder code. Both issues cite
        # that line and quote the actual content — the citation
        # verifier will confirm they match and keep the issues.
        mock_ai_response = (
            "\nVALIDATION RESULT: FAIL\n"
            "\nMissing implementations:\n"
            "\n1. ❌ Password strength validation - No validatePassword() "
            "function found\n"
            "   SEVERITY: CRITICAL\n"
            "   EVIDENCE: src/registration.js:1\n"
            "   QUOTE: `function validateEmail(email) { return true; }  "
            "// TODO: implement proper validation`\n"
            "   REMEDIATION: Add validatePassword() function "
            "(src/registration.js:1)\n"
            "   CRITERION: Password strength validation implemented\n"
            "\n2. ❌ Passwords match validation - No passwordsMatch() "
            "function found\n"
            "   SEVERITY: CRITICAL\n"
            "   EVIDENCE: src/registration.js:1\n"
            "   QUOTE: `function validateEmail(email) { return true; }`\n"
            "   REMEDIATION: Add passwordsMatch(p1, p2) function "
            "(src/registration.js:1)\n"
            "   CRITERION: Passwords match validation implemented\n"
        )

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
        """
        Empty source files fail validation via the structural
        check in _build_validation_prompt, not via LLM review.

        The empty-file case is one of the few structural failure
        modes that can be detected without a verified citation —
        a 0-byte file has nothing to cite. The test now exercises
        this path via a non-empty file with a TODO marker that can
        be quoted, since the LLM path needs citations to survive
        the post-validation check.
        """
        # Mock evidence with a file that has a quotable TODO
        mock_evidence = WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/root/src/validation.js",
                    relative_path="src/validation.js",
                    size_bytes=50,
                    content="// TODO: implement validation functions",
                    has_placeholders=True,
                    extension=".js",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project/root",
        )

        # Mock AI response with a verifiable citation that quotes
        # the TODO line exactly.
        mock_ai_response = (
            "\nVALIDATION RESULT: FAIL\n"
            "\n1. ❌ No validation features implemented\n"
            "   SEVERITY: CRITICAL\n"
            "   EVIDENCE: src/validation.js:1\n"
            "   QUOTE: `// TODO: implement validation functions`\n"
            "   REMEDIATION: Implement all validation functions "
            "(src/validation.js:1)\n"
            "   CRITERION: Email validation implemented\n"
        )

        with patch.object(analyzer, "gather_evidence", return_value=mock_evidence):
            with patch.object(
                analyzer, "_validate_with_ai", return_value=mock_ai_response
            ):
                result = await analyzer.validate_implementation_task(
                    mock_task, mock_state
                )

                assert result.passed is False
                assert len(result.issues) >= 1
                assert (
                    "no validation features" in result.issues[0].issue.lower()
                    or "empty" in result.issues[0].issue.lower()
                )

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


class TestParseValidationResponse:
    """Regression tests for the validation LLM response parser.

    GH-320 Experiment 4 exposed a bug where the LLM emits its
    response in a freeform markdown style (``### CRITERION N:``
    section headers, multi-line evidence prose, occasional JSON
    code fences) that the strict-keyword text parser couldn't
    extract. Every issue fell through to the ``"No evidence
    provided"`` default string and all completion attempts were
    rejected with shifting, meaningless critiques.

    Both agents in Experiment 4 hit this bug ~10 times each before
    giving up. The task's own ``historical_blockers`` field already
    documented the pattern: *"Implementation is 100% complete but
    validator rejects with 'Acceptance Criteria Not Provided'. All
    code working, all 33 tests passing."*

    These tests pin the correct parser behavior against realistic
    LLM outputs captured during Experiment 4.
    """

    @pytest.fixture
    def analyzer(self) -> WorkAnalyzer:
        """Work analyzer with mocked LLM."""
        with patch("src.ai.validation.work_analyzer.LLMAbstraction"):
            return WorkAnalyzer()

    def test_parses_json_response_pass(self, analyzer: WorkAnalyzer) -> None:
        """JSON-formatted PASS response parses cleanly."""
        response = """
        {
            "passed": true,
            "issues": [],
            "reasoning": "All criteria verified in source."
        }
        """
        result = analyzer._parse_validation_response(response)
        assert result.passed is True
        assert result.issues == []

    def test_parses_json_response_fail_with_full_issue_fields(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """JSON FAIL response with all issue fields populated."""
        response = """
{
    "passed": false,
    "issues": [
        {
            "severity": "CRITICAL",
            "issue": "DashboardLayout validation missing",
            "evidence": "src/dashboard-presentation/validation.ts has no DashboardLayout.validate() function",
            "remediation": "Add DashboardLayout.validate() that enforces gridColumns 1-12",
            "criterion": "Criterion 1: DashboardLayout entity"
        }
    ],
    "reasoning": "One critical issue found."
}
"""
        result = analyzer._parse_validation_response(response)
        assert result.passed is False
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert "DashboardLayout validation missing" in issue.issue
        assert "validation.ts" in issue.evidence
        assert "validate()" in issue.remediation
        assert "Criterion 1" in issue.criterion

    def test_text_response_freeform_evidence_after_emoji_regression(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """
        Regression test for GH-320 Experiment 4 validator bug.

        When the LLM emits freeform markdown with ``### CRITERION``
        headers and prose evidence in the lines following each
        ``❌`` symbol (instead of the strict ``EVIDENCE:`` keyword
        format), the parser must still extract the evidence text
        for each issue. Before this fix, the parser would fall
        through to the ``"No evidence provided"`` default for every
        issue because it only matched lines starting with the exact
        keyword ``EVIDENCE:``.
        """
        # Realistic output captured from Experiment 4 validator runs
        response = """VALIDATION RESULT: FAIL

### CRITERION 1: DashboardLayout entity defined and validated

✅ src/dashboard-presentation/types.ts contains the DashboardLayout
type with all required fields.

### CRITERION 2: Widget placement API

❌ Widget placement API incomplete
The src/dashboard-presentation/api.ts file is missing the POST
endpoint for widget registration. Only GET is implemented.
Evidence: grep for "app.post" in api.ts returns 0 matches.
Remediation: add app.post('/widgets', ...) handler following
the contract shape in docs/api/dashboard-presentation-api-contracts.md.
Criterion: CRITERION 2

### CRITERION 3: Responsive breakpoints

❌ Breakpoint resolver has hardcoded thresholds
evidence: src/dashboard-presentation/responsive.ts line 42 uses
literal values 640 and 1024 instead of reading from the
BreakpointConfig entity.
remediation: refactor resolveBreakpoint() to accept a
BreakpointConfig parameter and iterate its breakpoints array.
criterion: CRITERION 3
"""
        result = analyzer._parse_validation_response(response)

        assert result.passed is False, "Should parse as FAIL"
        assert len(result.issues) == 2, (
            f"Should extract 2 issues (CRITERION 2 and 3), got "
            f"{len(result.issues)}: "
            f"{[i.issue for i in result.issues]}"
        )

        # The bug was: every issue fell through to "No evidence provided"
        for issue in result.issues:
            assert issue.evidence != "No evidence provided", (
                f"Issue '{issue.issue}' has no evidence — parser "
                f"failed to extract freeform prose evidence."
            )
            assert issue.remediation != "No remediation provided", (
                f"Issue '{issue.issue}' has no remediation — parser "
                f"failed to extract freeform prose remediation."
            )

        # Check specific content ended up in the right fields
        issue_2 = next(
            (i for i in result.issues if "Widget placement" in i.issue), None
        )
        assert issue_2 is not None
        assert (
            "api.ts" in issue_2.evidence.lower() or "post" in issue_2.evidence.lower()
        ), f"Issue 2 evidence missing context: {issue_2.evidence}"
        assert (
            "app.post" in issue_2.remediation.lower()
            or "handler" in issue_2.remediation.lower()
        ), f"Issue 2 remediation missing context: {issue_2.remediation}"

        issue_3 = next((i for i in result.issues if "Breakpoint" in i.issue), None)
        assert issue_3 is not None
        # Evidence/remediation use lowercase keywords in this example
        assert (
            "responsive.ts" in issue_3.evidence.lower()
            or "hardcoded" in issue_3.evidence.lower()
        )

    def test_text_response_case_insensitive_keywords(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """Parser matches EVIDENCE/evidence/Evidence case-insensitively."""
        response = """VALIDATION RESULT: FAIL

❌ Issue one
Evidence: file X is missing
Remediation: create file X
CRITERION: Criterion 1
"""
        result = analyzer._parse_validation_response(response)
        assert result.passed is False
        assert len(result.issues) == 1
        assert "file X is missing" in result.issues[0].evidence
        assert "create file X" in result.issues[0].remediation

    def test_text_response_multiline_evidence_window(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """
        Parser collects evidence prose across multiple lines until
        the next section marker (another ❌, ### header, EOF, or a
        blank line followed by another keyword).
        """
        response = """VALIDATION RESULT: FAIL

❌ Missing validation layer
The validation.ts file does not export a validate() function.
Without it, callers cannot enforce field constraints at runtime.
Evidence: grep -n "export function validate" validation.ts returns 0 matches.
Remediation: add `export function validate(layout: DashboardLayout): ValidationResult`
that checks each field against the contract constraints.
Criterion: Criterion 1 — DashboardLayout validation
"""
        result = analyzer._parse_validation_response(response)
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert (
            "validate() function" in issue.issue or "Missing validation" in issue.issue
        )
        assert "validation.ts" in issue.evidence
        assert "validate" in issue.remediation
        assert "Criterion 1" in issue.criterion

    def test_text_response_subheading_inside_issue_block_preserved(
        self, analyzer: WorkAnalyzer
    ) -> None:
        """
        Parser must NOT terminate an issue block on generic ``###``
        subheadings like ``### Evidence`` or ``### Remediation``.
        Only ``### CRITERION`` headers delimit separate issues.

        Regression test for Codex P1 on PR #331. The first fix used
        ``stripped.startswith("### ")`` as a block terminator, which
        would close the block on any markdown subheading inside the
        issue and silently drop the metadata that followed it — re-
        introducing the ``"No evidence provided"`` fallback the PR
        was supposed to fix.
        """
        response = """VALIDATION RESULT: FAIL

❌ Missing POST endpoint for widget registration

### Evidence
grep for "app.post" in src/dashboard-presentation/api.ts returns 0
matches. Only GET /widgets is implemented.

### Remediation
Add ``app.post('/widgets', registerWidget)`` wired to the handler
defined in the contract file.

Criterion: CRITERION 2
"""
        result = analyzer._parse_validation_response(response)

        assert result.passed is False
        assert len(result.issues) == 1, (
            f"Expected 1 issue, got {len(result.issues)}: "
            f"{[i.issue for i in result.issues]}"
        )
        issue = result.issues[0]
        assert issue.evidence != "No evidence provided", (
            "Parser closed block on '### Evidence' subheading and "
            "dropped the evidence text."
        )
        assert issue.remediation != "No remediation provided", (
            "Parser closed block on '### Remediation' subheading and "
            "dropped the remediation text."
        )
        assert "app.post" in issue.evidence.lower()
        assert "registerwidget" in issue.remediation.lower()

    def test_text_response_pass_with_no_issues(self, analyzer: WorkAnalyzer) -> None:
        """VALIDATION RESULT: PASS with checkmarks only → no issues."""
        response = """VALIDATION RESULT: PASS

✅ Criterion 1 - VERIFIED in src/dashboard-presentation/types.ts
✅ Criterion 2 - VERIFIED in src/dashboard-presentation/validation.ts
✅ Criterion 3 - VERIFIED in src/dashboard-presentation/api.ts
"""
        result = analyzer._parse_validation_response(response)
        assert result.passed is True
        assert len(result.issues) == 0


class TestCitationVerification:
    """
    Tests for ``_verify_citations`` — the post-validation check
    that drops issues with unverifiable or hallucinated file:line
    citations. This is the ground-truth check on the ground-truth
    checker.
    """

    @pytest.fixture
    def analyzer(self) -> WorkAnalyzer:
        """WorkAnalyzer with LLM stubbed."""
        with patch("src.ai.validation.work_analyzer.LLMAbstraction"):
            return WorkAnalyzer()

    @pytest.fixture
    def evidence_with_file(self) -> WorkEvidence:
        """Evidence containing a single source file for citation lookup."""
        content = (
            "function validateEmail(email) {\n"
            "  return email.includes('@');\n"
            "}\n"
            "function validatePassword(pw) {\n"
            "  return pw.length >= 8;\n"
            "}\n"
        )
        return WorkEvidence(
            source_files=[
                SourceFile(
                    path="/fake/project/src/validation.js",
                    relative_path="src/validation.js",
                    size_bytes=len(content),
                    content=content,
                    has_placeholders=False,
                    extension=".js",
                    modified_time=datetime.utcnow(),
                )
            ],
            design_artifacts=[],
            decisions=[],
            project_root="/fake/project",
        )

    def test_drops_issue_with_no_citation(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """Issue with no file:line citation is dropped as hallucinated."""
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Password validation missing",
                    evidence="The code doesn't check password length",
                    remediation="Add length check",
                    criterion="Password strength",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is True
        assert len(verified.issues) == 0

    def test_drops_issue_with_nonexistent_file_citation(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """Citation to a file not in evidence → dropped."""
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Missing feature",
                    evidence="src/nonexistent.js:5",
                    remediation="Create the file",
                    criterion="Feature X",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is True
        assert len(verified.issues) == 0

    def test_drops_issue_with_out_of_range_line(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """Line number beyond file length → dropped."""
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Missing feature at line 999",
                    evidence="src/validation.js:999",
                    remediation="Add it",
                    criterion="Feature X",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is True

    def test_drops_issue_with_mismatched_quote(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """
        Citation exists but the quote doesn't match the actual
        line content → dropped. This catches the "LLM knows the
        file exists but invents text" failure mode.
        """
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        # Line 1 is "function validateEmail(email) {" but the LLM
        # claims it's something else entirely.
        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Invalid function signature",
                    evidence=(
                        "src/validation.js:1 "
                        "`function loginUser(username, password) {`"
                    ),
                    remediation="Fix signature",
                    criterion="Email validation",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is True
        assert len(verified.issues) == 0

    def test_keeps_issue_with_verified_citation_and_quote(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """
        Valid citation + matching quote → issue is kept.
        """
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        # Line 2 is "  return email.includes('@');"
        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Email validation too permissive",
                    evidence=("src/validation.js:2 " "`return email.includes('@');`"),
                    remediation="Use a proper regex",
                    criterion="Email validation must reject invalid formats",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is False
        assert len(verified.issues) == 1
        assert "email validation" in verified.issues[0].issue.lower()

    def test_keeps_issue_with_quote_whitespace_tolerant(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """
        Quote with different whitespace than the actual line is
        still accepted. LLMs re-indent when quoting.
        """
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        # Line 2 has leading whitespace; LLM drops it in the quote.
        result = ValidationResult(
            passed=False,
            issues=[
                ValidationIssue(
                    severity=ValidationSeverity.MAJOR,
                    issue="Email check too permissive",
                    evidence=("src/validation.js:2 " "`return email.includes('@');`"),
                    remediation="Use regex",
                    criterion="Email validation",
                )
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is False
        assert len(verified.issues) == 1

    def test_mixed_issues_drops_only_hallucinations(
        self, analyzer: WorkAnalyzer, evidence_with_file: WorkEvidence
    ) -> None:
        """
        Multiple issues: verified ones are kept, hallucinated
        ones are dropped. Passed stays False if any verified
        issues remain.
        """
        from src.ai.validation.validation_models import (
            ValidationIssue,
            ValidationResult,
        )

        result = ValidationResult(
            passed=False,
            issues=[
                # Verified
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Real issue",
                    evidence=("src/validation.js:2 " "`return email.includes('@');`"),
                    remediation="Fix it",
                    criterion="Email validation",
                ),
                # Hallucinated — no citation
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Fake issue",
                    evidence="Something vague",
                    remediation="Do something",
                    criterion="Password strength",
                ),
            ],
            ai_reasoning="FAIL",
            validation_time=datetime.utcnow(),
        )

        verified = analyzer._verify_citations(result, evidence_with_file)
        assert verified.passed is False
        assert len(verified.issues) == 1
        assert "real issue" in verified.issues[0].issue.lower()
