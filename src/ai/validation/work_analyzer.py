"""Core validation engine for implementation task completeness.

This module provides the WorkAnalyzer class which:
1. Discovers source files by scanning project_root directory
2. Gathers design artifacts and architectural decisions
3. Validates implementations against acceptance criteria using AI
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.validation.validation_models import (
    SourceFile,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    WorkEvidence,
)
from src.core.error_framework import ErrorContext, ProjectRootNotFoundError
from src.core.resilience import RetryConfig, with_retry
from src.marcus_mcp.tools.context import get_task_context

logger = logging.getLogger(__name__)


class WorkAnalyzer:
    """Core validation engine with isolated LLM instance.

    Validates implementation tasks by:
    - Discovering source files from project_root
    - Reading complete file contents
    - Analyzing code against acceptance criteria using AI
    - Detecting empty files and placeholder code

    Attributes
    ----------
    _validation_llm : LLMAbstraction
        Dedicated LLM instance for validation (isolated from Marcus's context)
    """

    # Source file extensions to include in validation
    SOURCE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".html",
        ".css",
        ".scss",
        ".less",
    }

    # Directories to exclude from source file discovery
    EXCLUDE_DIRS = {
        "docs",  # Design artifacts (not implementation)
        "node_modules",  # Dependencies
        ".git",  # Version control
        "__pycache__",  # Python cache
        "venv",
        ".venv",  # Python virtual environments
        "build",
        "dist",  # Build artifacts
        ".pytest_cache",  # Test cache
        "coverage",  # Coverage reports
        ".next",  # Next.js build
        ".nuxt",  # Nuxt.js build
        "target",  # Rust/Java build
        "bin",
        "obj",  # C#/.NET build
    }

    # Placeholder patterns indicating incomplete implementation
    PLACEHOLDER_PATTERNS = {
        "TODO",
        "FIXME",
        "HACK",
        "XXX",
        "NotImplementedError",
        "pass  # TODO",
        "throw new Error('Not implemented')",
        "unimplemented!()",  # Rust
    }

    def __init__(self) -> None:
        """Initialize WorkAnalyzer with dedicated LLM instance."""
        # Dedicated LLM instance - does NOT share context with Marcus
        self._validation_llm = LLMAbstraction()

    async def gather_evidence(self, task: Any, state: Any) -> WorkEvidence:
        """Gather evidence for validation by discovering source files.

        Parameters
        ----------
        task : Any
            Task to gather evidence for
        state : Any
            Marcus server state

        Returns
        -------
        WorkEvidence
            Bundle of source files + design artifacts + decisions
        """
        logger.info(f"Gathering validation evidence for task {task.id} ({task.name})")

        # 1. Get project_root from workspace manager or artifacts
        project_root = self._get_project_root(task, state)
        logger.debug(f"Project root: {project_root}")

        # 2. Discover source files by scanning project_root
        source_files = self._discover_source_files(project_root)
        logger.info(
            f"Discovered {len(source_files)} source files "
            f"({sum(f.size_bytes for f in source_files)} total bytes)"
        )

        # 3. Get design artifacts from state
        design_artifacts = state.task_artifacts.get(task.id, []).copy()
        logger.debug(f"Found {len(design_artifacts)} design artifacts")

        # 4. Get decisions from get_task_context
        decisions = await self._get_decisions(task, state)
        logger.debug(f"Retrieved {len(decisions)} architectural decisions")

        return WorkEvidence(
            source_files=source_files,
            design_artifacts=design_artifacts,
            decisions=decisions,
            project_root=project_root,
            collection_time=datetime.utcnow(),
        )

    async def validate_implementation_task(
        self, task: Any, state: Any
    ) -> ValidationResult:
        """Validate implementation task against acceptance criteria.

        Parameters
        ----------
        task : Any
            Task to validate (must have completion_criteria)
        state : Any
            Marcus server state

        Returns
        -------
        ValidationResult
            Pass/fail result with issues and remediation
        """
        logger.info(f"Starting validation for task {task.id} ({task.name})")

        # Gather evidence
        evidence = await self.gather_evidence(task, state)

        # Check if no source files discovered (immediate failure)
        if not evidence.has_source_files():
            logger.warning(
                f"No source files found for task {task.id} in {evidence.project_root}"
            )
            return ValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        issue="No source files discovered in project directory",
                        evidence=f"Scanned {evidence.project_root} but found no implementation files",  # noqa: E501
                        remediation="Create source code files to implement the task requirements",  # noqa: E501
                        criterion="Implementation exists",
                    )
                ],
                ai_reasoning="Cannot validate - no source code found",
                validation_time=datetime.utcnow(),
            )

        # Validate with AI
        logger.debug(f"Calling AI validator for task {task.id}")
        ai_response = await self._validate_with_ai(task, evidence)

        # Parse AI response into ValidationResult
        result = self._parse_validation_response(ai_response)

        # Run runtime validation if source code validation passed
        if result.passed:
            runtime_result = await self._validate_runtime(task, evidence)
            if not runtime_result.passed:
                # Merge runtime issues with source validation
                logger.warning(
                    f"Runtime validation FAILED for task {task.id} - "
                    f"{len(runtime_result.issues)} issue(s)"
                )
                return ValidationResult(
                    passed=False,
                    issues=result.issues + runtime_result.issues,
                    ai_reasoning=f"Source code complete but runtime validation failed: {runtime_result.ai_reasoning}",  # noqa: E501
                    validation_time=datetime.utcnow(),
                )

        if result.passed:
            logger.info(f"Validation PASSED for task {task.id} ({task.name})")
        else:
            logger.warning(
                f"Validation FAILED for task {task.id} ({task.name}) "
                f"- {len(result.issues)} issue(s) found"
            )

        return result

    def _get_project_root(self, task: Any, state: Any) -> str:
        """Get project_root from workspace manager or artifacts.

        Parameters
        ----------
        task : Any
            Task being validated
        state : Any
            Marcus server state

        Returns
        -------
        str
            Absolute path to project root

        Raises
        ------
        ValueError
            If project_root cannot be determined
        """
        # Try workspace manager first
        if (
            hasattr(state, "workspace_manager")
            and state.workspace_manager
            and hasattr(state.workspace_manager, "project_config")
            and state.workspace_manager.project_config
        ):
            main_workspace = state.workspace_manager.project_config.main_workspace
            if main_workspace:
                return str(main_workspace)

        # Fallback: extract from logged artifacts
        artifacts = state.task_artifacts.get(task.id, [])
        if artifacts and "project_root" in artifacts[0]:
            return str(artifacts[0]["project_root"])

        # Cannot determine project location
        logger.error(
            f"Cannot determine project_root for task {task.id} - "
            "no workspace config and no artifacts logged"
        )
        raise ProjectRootNotFoundError(
            task_id=task.id,
            context=ErrorContext(
                operation="get_project_root",
                task_id=task.id,
            ),
        )

    def _discover_source_files(self, project_root: str) -> list[SourceFile]:
        """Discover source files by scanning project_root directory.

        Parameters
        ----------
        project_root : str
            Root directory to scan

        Returns
        -------
        list[SourceFile]
            Discovered source files with content
        """
        logger.debug(
            f"Scanning {project_root} for source files (excluding {self.EXCLUDE_DIRS})"
        )
        source_files: list[SourceFile] = []
        project_path = Path(project_root)

        for root, dirs, files in os.walk(project_root):
            # Filter out excluded directories (in-place modification)
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]

            for file in files:
                file_path = Path(root) / file

                # Filter by extension
                if file_path.suffix not in self.SOURCE_EXTENSIONS:
                    continue

                try:
                    # Get file metadata
                    stat = file_path.stat()
                    size_bytes = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime)

                    # Read content
                    if size_bytes == 0:
                        content = ""
                    elif size_bytes > 1_000_000:  # 1MB safety limit
                        # File too large - read first 100KB and flag
                        content = file_path.read_text(errors="ignore")[:100000]
                        content += "\n\n[FILE TRUNCATED - Too large for validation]"
                    else:
                        # Read complete file
                        content = file_path.read_text(errors="ignore")

                    # Detect placeholders
                    has_placeholders = any(
                        pattern in content for pattern in self.PLACEHOLDER_PATTERNS
                    )

                    source_files.append(
                        SourceFile(
                            path=str(file_path),
                            relative_path=str(file_path.relative_to(project_path)),
                            size_bytes=size_bytes,
                            content=content,
                            has_placeholders=has_placeholders,
                            extension=file_path.suffix,
                            modified_time=modified_time,
                        )
                    )

                except Exception as e:
                    # Don't fail entire discovery if one file has issues
                    logger.warning(f"Failed to read {file_path}: {e}")
                    continue

        return source_files

    async def _get_decisions(self, task: Any, state: Any) -> list[dict[str, Any]]:
        """Get architectural decisions from get_task_context.

        Parameters
        ----------
        task : Any
            Task to get decisions for
        state : Any
            Marcus server state

        Returns
        -------
        list[dict[str, Any]]
            Decisions from this task + dependencies + siblings
        """
        try:
            context_result = await get_task_context(task.id, state)
            if context_result.get("success"):
                context = context_result.get("context", {})
                decisions: list[dict[str, Any]] = context.get("decisions", [])
                return decisions
        except Exception as e:
            logger.warning(f"Failed to get task context for decisions: {e}")

        return []

    async def _validate_runtime(
        self, task: Any, evidence: WorkEvidence
    ) -> ValidationResult:
        """Validate runtime behavior by running task-scoped tests.

        Parameters
        ----------
        task : Any
            Task being validated
        evidence : WorkEvidence
            Gathered evidence with source files

        Returns
        -------
        ValidationResult
            Pass/fail result from test execution
        """
        import asyncio
        import subprocess

        project_root = Path(evidence.project_root)

        # Detect project type
        project_type = self._detect_project_type(project_root)
        if not project_type:
            # No test runner detected - skip runtime validation
            logger.info(
                f"No test runner detected in {project_root} - "
                "skipping runtime validation"
            )
            return ValidationResult(passed=True, issues=[], ai_reasoning="")

        # Find test files related to task's source files
        test_files = self._discover_task_tests(evidence.source_files, project_root)
        if not test_files:
            # No tests for this task - skip runtime validation
            logger.info(
                f"No tests found for task {task.id} - skipping runtime validation"
            )
            return ValidationResult(passed=True, issues=[], ai_reasoning="")

        # Build test command (task-scoped, not full suite)
        test_command = self._build_test_command(project_type, test_files, project_root)
        logger.info(f"Running task-scoped tests: {test_command}")

        # Run tests with timeout
        try:
            proc = await asyncio.create_subprocess_shell(
                test_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(project_root),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                # Test failed - parse error
                error_output = stderr.decode("utf-8", errors="ignore")
                issues = self._parse_test_failure(error_output, project_type)
                return ValidationResult(
                    passed=False,
                    issues=issues,
                    ai_reasoning=f"Tests failed: {error_output[:500]}",
                    validation_time=datetime.utcnow(),
                )

            # Tests passed
            logger.info(f"Runtime validation PASSED for task {task.id}")
            return ValidationResult(passed=True, issues=[], ai_reasoning="")

        except asyncio.TimeoutError:
            logger.warning(f"Test execution timed out after 30s for task {task.id}")
            return ValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        issue="Test execution timed out after 30 seconds",
                        evidence="Tests did not complete in time",
                        remediation="Optimize tests or check for infinite loops",
                        criterion="All tests run successfully without errors",
                    )
                ],
                ai_reasoning="Test timeout",
                validation_time=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Runtime validation failed with error: {e}")
            return ValidationResult(
                passed=False,
                issues=[
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        issue=f"Runtime validation error: {str(e)}",
                        evidence=str(e),
                        remediation="Check test configuration and environment",
                        criterion="All tests run successfully without errors",
                    )
                ],
                ai_reasoning=f"Validation error: {str(e)}",
                validation_time=datetime.utcnow(),
            )

    def _detect_project_type(self, project_root: Path) -> dict[str, str] | None:
        """Detect project type and test runner.

        Parameters
        ----------
        project_root : Path
            Project root directory

        Returns
        -------
        dict[str, str] | None
            Project type info or None if no test runner detected
        """
        # Node.js project
        if (project_root / "package.json").exists():
            return {"type": "nodejs", "test_runner": "npm"}

        # Python project
        if (project_root / "pyproject.toml").exists() or (
            project_root / "setup.py"
        ).exists():
            return {"type": "python", "test_runner": "pytest"}

        # Java project
        if (project_root / "pom.xml").exists():
            return {"type": "java", "test_runner": "maven"}

        return None

    def _discover_task_tests(
        self, source_files: list[SourceFile], project_root: Path
    ) -> list[str]:
        """Find test files related to source files using hybrid strategy.

        Strategy:
        1. Look for co-located tests (fast, specific)
        2. Search common test directories (comprehensive)
        3. Use naming patterns to match tests to source files

        Parameters
        ----------
        source_files : list[SourceFile]
            Source files from task
        project_root : Path
            Project root directory

        Returns
        -------
        list[str]
            Test file paths
        """
        test_files: set[str] = set()  # Use set to avoid duplicates

        # PHASE 1: Co-located tests (original approach - still valuable)
        for source_file in source_files:
            file_path = Path(source_file.path)

            # Co-located test patterns
            colocated_patterns = [
                # JavaScript/TypeScript (same directory)
                file_path.with_suffix(".test.js"),
                file_path.with_suffix(".spec.js"),
                file_path.with_suffix(".test.ts"),
                file_path.with_suffix(".spec.ts"),
                file_path.with_suffix(".test.jsx"),
                file_path.with_suffix(".test.tsx"),
                # Python (same directory)
                file_path.with_name(f"test_{file_path.stem}.py"),
                # React __tests__ convention
                file_path.parent / "__tests__" / f"{file_path.stem}.test.js",
                file_path.parent / "__tests__" / f"{file_path.stem}.test.tsx",
            ]

            for pattern in colocated_patterns:
                if pattern.exists():
                    try:
                        test_files.add(str(pattern.relative_to(project_root)))
                    except ValueError:
                        # Pattern not relative to project_root - skip
                        pass

        # PHASE 2: Common test directories (comprehensive search)
        # Search standard test directory locations
        common_test_dirs = [
            project_root / "tests",  # Python standard
            project_root / "test",  # Alternative
            project_root / "__tests__",  # Jest standard
            project_root / "spec",  # RSpec/Jasmine style
            project_root / "implementation" / "tests",  # Marcus structure
        ]

        for test_dir in common_test_dirs:
            if not test_dir.exists():
                continue

            # Find all test files in this directory
            for source_file in source_files:
                source_path = Path(source_file.path)
                source_name = source_path.stem  # e.g., "calculator"
                source_ext = source_path.suffix  # e.g., ".py"

                # Python test naming patterns
                if source_ext == ".py":
                    # Look for test_<name>.py in test directory
                    test_patterns = [
                        test_dir / f"test_{source_name}.py",
                        test_dir / f"{source_name}_test.py",
                    ]

                    # Also check subdirectories that mirror source structure
                    # e.g., app/models/user.py -> tests/models/test_user.py
                    try:
                        rel_to_project = source_path.relative_to(project_root)
                        source_parent = rel_to_project.parent

                        # Try different mirroring strategies:
                        # 1. Full path: app/models/ -> tests/app/models/
                        # 2. Skip root: app/models/ -> tests/models/
                        # 3. Each subdirectory level
                        parts = source_parent.parts
                        for i in range(len(parts)):
                            # Try each suffix of the path
                            # e.g., for app/models: try models, then app/models
                            subpath = Path(*parts[i:]) if i < len(parts) else Path()
                            mirrored_test_dir = test_dir / subpath
                            if mirrored_test_dir.exists():
                                test_patterns.extend(
                                    [
                                        mirrored_test_dir / f"test_{source_name}.py",
                                        mirrored_test_dir / f"{source_name}_test.py",
                                    ]
                                )
                    except ValueError:
                        pass  # source_path not relative to project_root

                    for pattern in test_patterns:
                        if pattern.exists():
                            try:
                                test_files.add(str(pattern.relative_to(project_root)))
                            except ValueError:
                                pass

                # JavaScript/TypeScript test naming patterns
                elif source_ext in {".js", ".jsx", ".ts", ".tsx"}:
                    test_patterns = [
                        test_dir / f"{source_name}.test.js",
                        test_dir / f"{source_name}.spec.js",
                        test_dir / f"{source_name}.test.ts",
                        test_dir / f"{source_name}.spec.ts",
                        test_dir / f"{source_name}.test.tsx",
                    ]

                    for pattern in test_patterns:
                        if pattern.exists():
                            try:
                                test_files.add(str(pattern.relative_to(project_root)))
                            except ValueError:
                                pass

        return list(test_files)

    def _build_test_command(
        self, project_type: dict[str, str], test_files: list[str], project_root: Path
    ) -> str:
        """Build test command for specific files.

        Automatically detects the test framework and builds appropriate command.

        Parameters
        ----------
        project_type : dict[str, str]
            Project type info
        test_files : list[str]
            Test files to run
        project_root : Path
            Project root directory

        Returns
        -------
        str
            Test command to execute
        """
        files_arg = " ".join(test_files)

        if project_type["type"] == "nodejs":
            # Read test script from package.json
            package_json_path = project_root / "package.json"
            if package_json_path.exists():
                import json

                try:
                    package_data = json.loads(package_json_path.read_text())
                    test_script = package_data.get("scripts", {}).get("test", "")

                    # Map common test frameworks
                    if "jest" in test_script:
                        return f"npx jest {files_arg}"
                    elif "mocha" in test_script:
                        return f"npx mocha {files_arg}"
                    elif "vitest" in test_script:
                        return f"npx vitest run {files_arg}"
                    elif "ava" in test_script:
                        return f"npx ava {files_arg}"
                    elif "tap" in test_script:
                        return f"npx tap {files_arg}"
                    else:
                        # Use npm test if we can't detect framework
                        return "npm test"
                except Exception:
                    pass

            # Default fallback
            return f"npx jest {files_arg}"

        elif project_type["type"] == "python":
            # Detect Python test framework
            # Check for pytest.ini, pyproject.toml [tool.pytest], or tox.ini
            if (project_root / "pytest.ini").exists() or (
                project_root / "pyproject.toml"
            ).exists():
                return f"pytest {files_arg}"
            # Check for unittest
            elif (project_root / "setup.py").exists():
                return f"python -m unittest {files_arg}"
            # Default to pytest
            return f"pytest {files_arg}"

        elif project_type["type"] == "java":
            # Maven or Gradle
            if (project_root / "pom.xml").exists():
                return "mvn test"
            elif (project_root / "build.gradle").exists() or (
                project_root / "build.gradle.kts"
            ).exists():
                return "./gradlew test"
            return "mvn test"

        return "echo 'No test command configured'"

    def _parse_test_failure(
        self, error_output: str, project_type: dict[str, str]
    ) -> list[ValidationIssue]:
        """Parse test failure output to extract issues.

        Parameters
        ----------
        error_output : str
            Test stderr output
        project_type : dict[str, str]
            Project type info

        Returns
        -------
        list[ValidationIssue]
            Extracted issues from test failure
        """
        issues = []

        # Generic patterns that work across test frameworks
        if (
            "Cannot find module" in error_output
            or "ModuleNotFoundError" in error_output
        ):
            # Missing dependency
            match = None
            if "Cannot find module '" in error_output:
                # Node.js error
                start_idx = error_output.find("Cannot find module '") + 20
                end_idx = error_output.find("'", start_idx)
                if end_idx > start_idx:
                    match = error_output[start_idx:end_idx]
            elif "ModuleNotFoundError: No module named" in error_output:
                # Python error - find the module name after the text
                prefix = "ModuleNotFoundError: No module named '"
                start_idx = error_output.find(prefix)
                if start_idx != -1:
                    start_idx += len(prefix)
                    end_idx = error_output.find("'", start_idx)
                    if end_idx > start_idx:
                        match = error_output[start_idx:end_idx]

            if match:
                remediation = ""
                if project_type["type"] == "nodejs":
                    remediation = f"Run: npm install --save-dev {match}"
                elif project_type["type"] == "python":
                    remediation = f"Run: pip install {match}"

                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        issue=f"Missing dependency: {match}",
                        evidence=f"Test failed with module not found error: {match}",
                        remediation=remediation,
                        criterion="All tests run successfully without errors",
                    )
                )

        # Generic test failure (no specific dependency issue)
        if not issues:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    issue="Tests failed",
                    evidence=error_output[:500],  # First 500 chars
                    remediation="Fix failing tests before marking task complete",
                    criterion="All tests run successfully without errors",
                )
            )

        return issues

    @with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
    async def _validate_with_ai(self, task: Any, evidence: WorkEvidence) -> str:
        """Validate implementation using AI analysis with retry logic.

        Parameters
        ----------
        task : Any
            Task with completion_criteria
        evidence : WorkEvidence
            Gathered evidence bundle

        Returns
        -------
        str
            AI's validation analysis

        Notes
        -----
        Uses retry logic (3 attempts, 1s base delay) to handle transient
        network failures when calling the AI provider.
        """
        # Build validation prompt
        task_prompt = self._build_validation_prompt(task, evidence)

        # System instructions for validation
        system_instructions = """You are a code validation expert analyzing implementation completeness.  # noqa: E501
Your job is to verify that source code fully implements acceptance criteria.
You do NOT make task assignment decisions or coordinate agents.
Focus purely on: Does the code work? Are features complete?

CRITICAL RULES:
1. Check EACH acceptance criterion has code evidence in source files
2. FAIL if ANY criterion lacks implementation
3. FAIL if source code contains placeholder/TODO comments for required features
4. FAIL if source files are empty (0 bytes) when they should have implementation
5. FAIL if obvious integrations missing (e.g., form has inputs but validation.js has no functions)  # noqa: E501
6. PASS only if ALL criteria have working implementation

Focus on FUNCTIONALITY, not understanding. Code must WORK, not just exist.

---

"""

        # Combine system instructions with task prompt
        full_prompt = system_instructions + task_prompt

        # Create simple context object
        context = type("ValidationContext", (), {"max_tokens": 4000})()

        # Call dedicated validation LLM with retry support
        logger.debug("Calling AI provider for validation analysis")
        response: str = await self._validation_llm.analyze(
            prompt=full_prompt, context=context
        )
        logger.debug("Received AI validation response")

        return response

    def _build_validation_prompt(self, task: Any, evidence: WorkEvidence) -> str:
        """Build AI prompt for validation.

        Parameters
        ----------
        task : Any
            Task with completion_criteria
        evidence : WorkEvidence
            Evidence bundle

        Returns
        -------
        str
            Formatted validation prompt
        """
        prompt_parts = [
            f"TASK: {task.name}",
            f"DESCRIPTION: {task.description}",
            "\nACCEPTANCE CRITERIA (ALL must be met):",
        ]

        # Add criteria
        criteria = getattr(task, "completion_criteria", [])
        for i, criterion in enumerate(criteria, 1):
            prompt_parts.append(f"{i}. {criterion}")

        # Add discovered source files with content
        prompt_parts.append("\n\nEVIDENCE - DISCOVERED SOURCE FILES:")
        for source_file in evidence.source_files:
            file_info = f"\nSource File: {source_file.relative_path} ({source_file.size_bytes} bytes)"  # noqa: E501
            if source_file.has_placeholders:
                file_info += " [CONTAINS PLACEHOLDERS]"
            if source_file.is_empty():
                file_info += " [EMPTY FILE]"

            prompt_parts.append(file_info)
            prompt_parts.append(
                f"  Content:\n{source_file.content[:2000]}"
            )  # First 2KB
            if len(source_file.content) > 2000:
                prompt_parts.append("  [... content truncated for display ...]")

        # Add design artifacts (for context)
        if evidence.design_artifacts:
            prompt_parts.append("\n\nDESIGN ARTIFACTS (what SHOULD be built):")
            for artifact in evidence.design_artifacts:
                prompt_parts.append(
                    f"  - {artifact.get('filename')}: {artifact.get('description', '')}"
                )

        # Add decisions (for context)
        if evidence.decisions:
            prompt_parts.append("\n\nDECISIONS LOGGED:")
            for decision in evidence.decisions:
                prompt_parts.append(f"  - {decision.get('what')}")
                if decision.get("why"):
                    prompt_parts.append(f"    Why: {decision.get('why')}")

        # Add validation instructions
        prompt_parts.append(
            """

YOUR JOB: For EACH acceptance criterion, verify it was FULLY implemented in SOURCE CODE.

For each criterion:
1. Check source code content for evidence of implementation
2. If criterion is missing or incomplete → FAIL with specific issue
3. If all criteria have working code → PASS

OUTPUT FORMAT:
VALIDATION RESULT: PASS or FAIL

For each criterion:
✅ [Criterion] - VERIFIED in [file]
OR
❌ [Issue description]
   SEVERITY: CRITICAL/MAJOR/MINOR
   EVIDENCE: [What's wrong in source code]
   REMEDIATION: [Specific fix]
   CRITERION: [Which criterion this relates to]

ANALYSIS RULES:
✅ PASS only if ALL criteria have code evidence
❌ FAIL if ANY criterion lacks implementation
❌ FAIL if source code contains TODO/FIXME for required features
❌ FAIL if source files are empty (0 bytes)
❌ FAIL if obvious integrations missing

Focus on FUNCTIONALITY - code must WORK."""
        )

        return "\n".join(prompt_parts)

    def _parse_validation_response(self, ai_response: str) -> ValidationResult:
        """Parse AI validation response into ValidationResult.

        Parameters
        ----------
        ai_response : str
            AI's validation analysis

        Returns
        -------
        ValidationResult
            Parsed validation result
        """
        # Check if validation passed
        passed = "VALIDATION RESULT: PASS" in ai_response

        # Extract issues (lines containing ❌)
        issues: list[ValidationIssue] = []
        lines = ai_response.split("\n")

        current_issue: dict[str, str] = {}
        for line in lines:
            line = line.strip()

            if "❌" in line:
                # Start of new issue
                if current_issue:
                    # Save previous issue
                    issues.append(self._create_issue_from_dict(current_issue))

                # Extract issue text (remove number prefix and ❌)
                issue_text = line
                # Remove number prefix like "1. " or "2. "
                if ". " in issue_text:
                    issue_text = (
                        issue_text.split(". ", 1)[1]
                        if len(issue_text.split(". ", 1)) > 1
                        else issue_text
                    )
                # Remove ❌ emoji
                issue_text = issue_text.replace("❌", "").strip()
                # Remove trailing " - " if present (some formats have "❌ Issue - Description")  # noqa: E501
                if " - " in issue_text:
                    issue_text = issue_text.split(" - ")[0].strip()

                current_issue = {"issue": issue_text}

            elif line.startswith("SEVERITY:"):
                current_issue["severity"] = (
                    line.replace("SEVERITY:", "").strip().lower()
                )

            elif line.startswith("EVIDENCE:"):
                current_issue["evidence"] = line.replace("EVIDENCE:", "").strip()

            elif line.startswith("REMEDIATION:"):
                current_issue["remediation"] = line.replace("REMEDIATION:", "").strip()

            elif line.startswith("CRITERION:"):
                current_issue["criterion"] = line.replace("CRITERION:", "").strip()

        # Save last issue
        if current_issue:
            issues.append(self._create_issue_from_dict(current_issue))

        return ValidationResult(
            passed=passed,
            issues=issues,
            ai_reasoning=ai_response,
            validation_time=datetime.utcnow(),
        )

    def _create_issue_from_dict(self, issue_dict: dict[str, str]) -> ValidationIssue:
        """Create ValidationIssue from parsed dictionary.

        Parameters
        ----------
        issue_dict : dict[str, str]
            Parsed issue data

        Returns
        -------
        ValidationIssue
            Created validation issue
        """
        # Map severity string to enum
        severity_str = issue_dict.get("severity", "critical")
        severity_map = {
            "critical": ValidationSeverity.CRITICAL,
            "major": ValidationSeverity.MAJOR,
            "minor": ValidationSeverity.MINOR,
        }
        severity = severity_map.get(severity_str, ValidationSeverity.CRITICAL)

        return ValidationIssue(
            severity=severity,
            issue=issue_dict.get("issue", "Unknown issue"),
            evidence=issue_dict.get("evidence", "No evidence provided"),
            remediation=issue_dict.get("remediation", "No remediation provided"),
            criterion=issue_dict.get("criterion", "Unknown criterion"),
        )
