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
        # 1. Get project_root from workspace manager or artifacts
        project_root = self._get_project_root(task, state)

        # 2. Discover source files by scanning project_root
        source_files = self._discover_source_files(project_root)

        # 3. Get design artifacts from state
        design_artifacts = state.task_artifacts.get(task.id, []).copy()

        # 4. Get decisions from get_task_context
        decisions = await self._get_decisions(task, state)

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
        # Gather evidence
        evidence = await self.gather_evidence(task, state)

        # Check if no source files discovered (immediate failure)
        if not evidence.has_source_files():
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
        ai_response = await self._validate_with_ai(task, evidence)

        # Parse AI response into ValidationResult
        result = self._parse_validation_response(ai_response)

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
        raise ValueError(
            "Cannot determine project_root - no workspace config and no artifacts logged"  # noqa: E501
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

    async def _validate_with_ai(self, task: Any, evidence: WorkEvidence) -> str:
        """Validate implementation using AI analysis.

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

        # Call dedicated validation LLM
        response: str = await self._validation_llm.analyze(
            prompt=full_prompt, context=context
        )

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
