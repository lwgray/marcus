"""
Task Completeness Validator.

Validates that generated tasks fully cover user intents from project description.
Uses AI-powered semantic matching with retry mechanism.

Classes
-------
ValidationAttempt
    Record of a single validation attempt
CompletenessResult
    Final result of completeness validation
TaskCompletenessValidator
    Validates tasks cover user intents with retry capability

Examples
--------
>>> validator = TaskCompletenessValidator(ai_client, prd_parser)
>>> result = await validator.validate_with_retry(
...     description, project_name, tasks, constraints, context
... )
>>> if result.is_complete:
...     print(f"Validation passed on attempt {result.passed_on_attempt}")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.core.error_framework import BusinessLogicError, ErrorContext
from src.core.models import Task

logger = logging.getLogger(__name__)


@dataclass
class StructuredIntents:
    """
    Two-tier intent structure for composition-aware validation.

    This class is backwards compatible with code expecting a list:
    - len(intents) returns len(all_intents)
    - Iteration yields items from all_intents
    - Can still access component_intents and integration_intents explicitly

    Attributes
    ----------
    component_intents : list[str]
        Individual features/capabilities to build (what to build)
    integration_intents : list[str]
        Assembly/wiring/packaging tasks (how to deliver)
    all_intents : list[str]
        Flat list combining both tiers (for backwards compatibility)

    Examples
    --------
    >>> intents = StructuredIntents(
    ...     component_intents=["Deck operations", "Card management"],
    ...     integration_intents=["MCP server setup", "Tool registration"],
    ...     all_intents=["Deck operations", "Card management",
    ...                  "MCP server setup", "Tool registration"]
    ... )
    >>> len(intents)  # Backwards compatible
    4
    >>> list(intents)  # Backwards compatible
    ["Deck operations", "Card management", "MCP server setup",
     "Tool registration"]
    >>> intents.component_intents  # New tier-specific access
    ["Deck operations", "Card management"]
    """

    component_intents: list[str]
    integration_intents: list[str]
    all_intents: list[str]

    def __len__(self) -> int:
        """Return total number of intents (backwards compatible)."""
        return len(self.all_intents)

    def __iter__(self) -> "Iterator[str]":
        """Iterate over all intents (backwards compatible)."""
        return iter(self.all_intents)


@dataclass
class ValidationAttempt:
    """
    Record of a single validation attempt.

    Attributes
    ----------
    attempt_number : int
        Which attempt this was (1, 2, 3)
    is_complete : bool
        Whether validation passed
    missing_intents : list[str]
        List of intents that were not covered
    missing_component_intents : list[str]
        Component intents that were not covered
    missing_integration_intents : list[str]
        Integration intents that were not covered
    timestamp : datetime
        When this attempt was made
    correlation_id : str
        Correlation ID for tracing
    emphasis_added : Optional[str]
        Emphasis text added for retry (None for first attempt)
    """

    attempt_number: int
    is_complete: bool
    missing_intents: list[str]
    timestamp: datetime
    correlation_id: str
    missing_component_intents: list[str] = field(default_factory=list)
    missing_integration_intents: list[str] = field(default_factory=list)
    emphasis_added: Optional[str] = None


@dataclass
class CompletenessResult:
    """
    Final result of completeness validation.

    Attributes
    ----------
    is_complete : bool
        Whether validation ultimately passed
    attempts : list[ValidationAttempt]
        Record of all validation attempts
    final_tasks : list[Task]
        The final task list (potentially updated through retries)
    total_attempts : int
        Total number of attempts made
    passed_on_attempt : Optional[int]
        Which attempt succeeded (None if all failed)
    """

    is_complete: bool
    attempts: list[ValidationAttempt]
    final_tasks: list[Task]
    total_attempts: int
    passed_on_attempt: Optional[int] = None


class TaskCompletenessValidator:
    """
    Validate tasks cover user intents with retry capability.

    Uses AI to extract intents from description and validate semantic coverage
    in generated tasks. Retries with emphasis on missing intents up to MAX_ATTEMPTS.

    Provider-agnostic design supports any AI client with compatible interface.

    Attributes
    ----------
    MAX_ATTEMPTS : int
        Maximum validation attempts before failing (class constant = 3)
    ai_client : Any
        AI client for intent extraction and validation
        Must support either:
        - _call_claude() method (AIAnalysisEngine)
        - providers with complete() method (LLMAbstraction)
    prd_parser : AdvancedPRDParser
        Parser for regenerating tasks on retry

    Methods
    -------
    extract_intents(description, project_name)
        Extract core user intents from description
    validate_coverage(intents, tasks)
        Check if tasks semantically cover all intents
    validate_with_retry(description, project_name, tasks, constraints, context)
        Validate with retry on missing intents

    Examples
    --------
    >>> validator = TaskCompletenessValidator(ai_client, prd_parser)
    >>> result = await validator.validate_with_retry(
    ...     description="Build MCP server",
    ...     project_name="deck-mcp",
    ...     tasks=initial_tasks,
    ...     constraints=constraints,
    ...     context=error_context
    ... )
    >>> assert result.is_complete
    """

    MAX_ATTEMPTS = 3

    def __init__(
        self,
        ai_client: Any,
        prd_parser: AdvancedPRDParser,
    ) -> None:
        """
        Initialize validator with dependencies.

        Parameters
        ----------
        ai_client : Any
            AI client for intent extraction and validation
            Must support either AIAnalysisEngine or LLMAbstraction interface
        prd_parser : AdvancedPRDParser
            Parser for regenerating tasks on retry
        """
        self.ai_client = ai_client
        self.prd_parser = prd_parser
        self.logger = logging.getLogger(__name__)

    async def extract_intents(
        self, description: str, project_name: str
    ) -> StructuredIntents:
        """
        Extract core user intents from project description.

        Uses AI to identify component and integration intents separately
        for composition-aware validation.

        Parameters
        ----------
        description : str
            Project description from user
        project_name : str
            Name of the project

        Returns
        -------
        StructuredIntents
            Structured intents with component and integration tiers

        Examples
        --------
        >>> intents = await validator.extract_intents(
        ...     "Build an MCP server that wraps the Deck API",
        ...     "deck-mcp"
        ... )
        >>> assert "MCP server infrastructure" in intents.integration_intents
        """
        prompt = f"""Extract what the user wants to build from this description.
Identify BOTH component intents (individual features) AND integration intents
(how components are assembled/delivered).

PROJECT: {project_name}
DESCRIPTION: {description}

Return JSON with two-tier structure:
{{
  "component_intents": ["intent 1", "intent 2"],
  "integration_intents": ["assembly intent 1", "delivery intent 2"]
}}

COMPONENT INTENTS: Individual features/capabilities to build
INTEGRATION INTENTS: How components are wired together, packaged, or delivered

Examples:

Description: "Build an MCP server for deck operations"
Component intents: ["Deck creation", "Card drawing", "Status checking"]
Integration intents: ["MCP server infrastructure", "Tool registration",
                     "Server entry point"]

Description: "Write a research paper on AI coordination"
Component intents: ["Literature review", "Experiments", "Data analysis"]
Integration intents: ["Paper compilation", "Results synthesis",
                     "Publication formatting"]

Description: "Create a web API for user management"
Component intents: ["User CRUD operations", "Authentication", "Authorization"]
Integration intents: ["API server setup", "Routing configuration", "Deployment"]

Focus on deliverables that must exist for the project to work.
Return only valid JSON."""

        try:
            response_text = await self._call_ai(prompt)
            response_data = json.loads(response_text)

            # Try new structured format first
            if "component_intents" in response_data:
                component_intents = response_data.get("component_intents", [])
                integration_intents = response_data.get("integration_intents", [])

                return StructuredIntents(
                    component_intents=component_intents,
                    integration_intents=integration_intents,
                    all_intents=component_intents + integration_intents,
                )
            # Backwards compatibility: handle old flat format
            elif "intents" in response_data:
                flat_intents = response_data["intents"]
                self.logger.warning(
                    "AI returned flat intent format, treating as components"
                )
                return StructuredIntents(
                    component_intents=flat_intents,
                    integration_intents=[],
                    all_intents=flat_intents,
                )
            else:
                raise KeyError("No intents found in response")

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse intent extraction response: {e}",
                extra={
                    "response": response_text if "response_text" in locals() else "N/A"
                },
            )
            # Fallback: treat entire description as component intent
            return StructuredIntents(
                component_intents=[description[:100]],
                integration_intents=[],
                all_intents=[description[:100]],
            )

    async def validate_coverage(
        self, structured_intents: StructuredIntents, tasks: list[Task]
    ) -> dict[str, Any]:
        """
        Validate if tasks semantically cover all intents across both tiers.

        Uses AI for semantic matching - not exact phrase matching.
        Validates both component intents (features) and integration intents
        (assembly/delivery) separately to detect composition gaps.

        Parameters
        ----------
        structured_intents : StructuredIntents
            Two-tier intents to verify (component + integration)
        tasks : list[Task]
            Generated tasks to check against

        Returns
        -------
        dict
            {
                "complete": bool,
                "missing": list[str],
                "missing_component_intents": list[str],
                "missing_integration_intents": list[str]
            }

        Examples
        --------
        >>> intents = StructuredIntents(
        ...     component_intents=["Deck operations", "Card management"],
        ...     integration_intents=["MCP server setup"],
        ...     all_intents=["Deck operations", "Card management", "MCP server setup"]
        ... )
        >>> result = await validator.validate_coverage(intents, tasks)
        >>> if not result["complete"]:
        ...     print(f"Missing components: {result['missing_component_intents']}")
        ...     print(f"Missing integration: {result['missing_integration_intents']}")
        """
        # Format tasks with name and description
        task_list = "\n".join([f"- {task.name}: {task.description}" for task in tasks])

        component_list = "\n".join(
            [f"- {intent}" for intent in structured_intents.component_intents]
        )
        integration_list = "\n".join(
            [f"- {intent}" for intent in structured_intents.integration_intents]
        )

        prompt = f"""Does this task list cover ALL intents across BOTH tiers?

COMPONENT INTENTS (features to build):
{component_list}

INTEGRATION INTENTS (assembly/delivery):
{integration_list}

TASKS:
{task_list}

Return JSON:
{{
  "complete": true|false,
  "missing_component_intents": ["missing component 1"],
  "missing_integration_intents": ["missing integration 1"],
  "missing": ["all missing intents combined"]
}}

Validation rules:
1. Component intents must be covered by implementation/feature tasks
2. Integration intents must be covered by assembly/wiring/infrastructure tasks
3. If ANY intent (component OR integration) is missing, return complete=false
4. Check semantically, not word-for-word

Common integration gaps to watch for:
- "Server" intent needs a server setup/entry point task, not just tool implementations
- "API" intent needs routing/server task, not just endpoint implementations
- "Book" intent needs compilation task, not just chapter writing
- "Pipeline" intent needs orchestration task, not just ETL steps
- "Application" intent needs packaging/deployment task, not just features

Return only valid JSON."""

        try:
            response_text = await self._call_ai(prompt)
            response_data = json.loads(response_text)

            missing_components = response_data.get("missing_component_intents", [])
            missing_integration = response_data.get("missing_integration_intents", [])
            missing = response_data.get("missing", [])

            # Legacy format fallback: if AI returns old format without tiers,
            # distribute missing intents to tiers by matching against originals
            if missing and not missing_components and not missing_integration:
                missing_components = [
                    intent
                    for intent in missing
                    if intent in structured_intents.component_intents
                ]
                missing_integration = [
                    intent
                    for intent in missing
                    if intent in structured_intents.integration_intents
                ]
                # If no matches (AI rephrased), treat all as components
                # to preserve retry emphasis behavior
                if not missing_components and not missing_integration:
                    missing_components = missing

            return {
                "complete": response_data.get("complete", False),
                "missing": missing,
                "missing_component_intents": missing_components,
                "missing_integration_intents": missing_integration,
            }

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse validation response: {e}",
                extra={
                    "response": response_text if "response_text" in locals() else "N/A"
                },
            )
            # Fallback: assume incomplete to be safe
            return {
                "complete": False,
                "missing": structured_intents.all_intents,
                "missing_component_intents": structured_intents.component_intents,
                "missing_integration_intents": structured_intents.integration_intents,
            }

    async def validate_with_retry(
        self,
        description: str,
        project_name: str,
        tasks: list[Task],
        constraints: Any,
        context: ErrorContext,
    ) -> CompletenessResult:
        """
        Validate tasks with retry on missing intents.

        Extracts intents once, then validates. On failure, retries with emphasis
        on missing intents up to MAX_ATTEMPTS.

        Parameters
        ----------
        description : str
            Original project description
        project_name : str
            Project name
        tasks : list[Task]
            Initial generated tasks
        constraints : Any
            Project constraints for re-parsing
        context : ErrorContext
            Error context for logging

        Returns
        -------
        CompletenessResult
            Final validation result with attempts and final tasks

        Raises
        ------
        BusinessLogicError
            If validation fails after MAX_ATTEMPTS

        Examples
        --------
        >>> result = await validator.validate_with_retry(...)
        >>> print(f"Passed on attempt {result.passed_on_attempt}")
        >>> for task in result.final_tasks:
        ...     print(task.name)
        """
        # Extract intents once at the start (now returns StructuredIntents)
        structured_intents = await self.extract_intents(description, project_name)

        self.logger.info(
            f"Extracted {len(structured_intents.all_intents)} intents for validation "
            f"({len(structured_intents.component_intents)} component, "
            f"{len(structured_intents.integration_intents)} integration)",
            extra={
                "correlation_id": context.correlation_id,
                "component_intents": structured_intents.component_intents,
                "integration_intents": structured_intents.integration_intents,
            },
        )

        attempts: list[ValidationAttempt] = []
        current_description = description
        current_tasks = tasks
        emphasis = None

        for attempt_num in range(1, self.MAX_ATTEMPTS + 1):
            # Validate current tasks with structured intents
            validation_result = await self.validate_coverage(
                structured_intents, current_tasks
            )

            is_complete = validation_result["complete"]
            missing = validation_result["missing"]
            missing_components = validation_result.get("missing_component_intents", [])
            missing_integration = validation_result.get(
                "missing_integration_intents", []
            )

            # Record attempt
            attempt = ValidationAttempt(
                attempt_number=attempt_num,
                is_complete=is_complete,
                missing_intents=missing,
                missing_component_intents=missing_components,
                missing_integration_intents=missing_integration,
                timestamp=datetime.now(timezone.utc),
                correlation_id=context.correlation_id,
                emphasis_added=emphasis,
            )
            attempts.append(attempt)

            # Log structured attempt
            self.logger.info(
                f"Validation attempt {attempt_num}/{self.MAX_ATTEMPTS}: "
                f"complete={is_complete}",
                extra={
                    "correlation_id": context.correlation_id,
                    "attempt": attempt_num,
                    "is_complete": is_complete,
                    "missing": missing,
                    "missing_components": missing_components,
                    "missing_integration": missing_integration,
                },
            )

            # Success - return immediately
            if is_complete:
                return CompletenessResult(
                    is_complete=True,
                    attempts=attempts,
                    final_tasks=current_tasks,
                    total_attempts=attempt_num,
                    passed_on_attempt=attempt_num,
                )

            # No more retries
            if attempt_num >= self.MAX_ATTEMPTS:
                break

            # Retry with tier-specific emphasis
            emphasis = self._create_composition_emphasis(
                missing_components=missing_components,
                missing_integration=missing_integration,
            )
            current_description = f"{description}\n\n{emphasis}"

            self.logger.info(
                "Retrying task decomposition with composition-aware emphasis",
                extra={
                    "correlation_id": context.correlation_id,
                    "attempt": attempt_num + 1,
                    "emphasis": emphasis,
                    "missing_components": missing_components,
                    "missing_integration": missing_integration,
                },
            )

            # Re-parse with emphasis
            prd_result = await self.prd_parser.parse_prd_to_tasks(
                current_description, constraints
            )
            current_tasks = prd_result.tasks

        # All attempts failed
        final_attempt = attempts[-1]
        missing_str = ", ".join(final_attempt.missing_intents)
        component_str = ", ".join(final_attempt.missing_component_intents)
        integration_str = ", ".join(final_attempt.missing_integration_intents)

        raise BusinessLogicError(
            f"Task validation failed after {self.MAX_ATTEMPTS} attempts. "
            f"Missing {len(final_attempt.missing_intents)} intents: {missing_str}. "
            f"Components: {component_str}. Integration: {integration_str}",
            context=context,
            remediation={
                "immediate_action": (
                    f"Review project tasks and manually add: {missing_str}"
                ),
                "long_term_solution": (
                    "Improve task decomposition prompts or validation thresholds"
                ),
                "retry_strategy": f"Already retried {self.MAX_ATTEMPTS} times",
            },
        )

    def _create_composition_emphasis(
        self,
        missing_components: list[str],
        missing_integration: list[str],
    ) -> str:
        """
        Create composition-aware emphasis text for retry.

        Distinguishes between missing component intents and missing integration
        intents to guide task regeneration more precisely.

        Parameters
        ----------
        missing_components : list[str]
            Component intents that were not covered
        missing_integration : list[str]
            Integration intents that were not covered

        Returns
        -------
        str
            Emphasis text to append to description

        Examples
        --------
        >>> emphasis = validator._create_composition_emphasis(
        ...     missing_components=["Card drawing"],
        ...     missing_integration=["MCP server setup"]
        ... )
        >>> assert "COMPONENTS" in emphasis
        >>> assert "INTEGRATION" in emphasis
        >>> assert "Card drawing" in emphasis
        >>> assert "MCP server setup" in emphasis
        """
        sections = []

        if missing_components:
            component_text = "\n".join(
                [f"  - {intent}" for intent in missing_components]
            )
            sections.append(
                f"IMPORTANT: Must include tasks for these COMPONENTS:\n{component_text}"
            )

        if missing_integration:
            integration_text = "\n".join(
                [f"  - {intent}" for intent in missing_integration]
            )
            sections.append(
                f"CRITICAL: Must include tasks for INTEGRATION/ASSEMBLY:\n"
                f"{integration_text}\n\n"
                f"Note: Individual component implementations are not enough. "
                f"You must include tasks that wire components together, "
                f"set up infrastructure, or create the delivery mechanism "
                f"(e.g., server.py for servers, main.py for applications, "
                f"compilation for documents)."
            )

        return "\n\n".join(sections)

    async def _call_ai(self, prompt: str) -> str:
        """
        Make AI call using provider-agnostic interface.

        Uses generate_structured_response() if available (AIAnalysisEngine),
        which internally uses LLMAbstraction to support all configured providers.

        Parameters
        ----------
        prompt : str
            Prompt to send to AI

        Returns
        -------
        str
            AI response text (JSON string)

        Raises
        ------
        ValueError
            If AI client doesn't support a compatible interface
        Exception
            If AI call fails
        """
        # Check for AIAnalysisEngine interface (has generate_structured_response)
        if hasattr(self.ai_client, "generate_structured_response"):
            # Use the provider-agnostic method that supports all AI providers
            response_dict: dict[str, Any] = (
                await self.ai_client.generate_structured_response(
                    prompt=prompt,
                    system_prompt="You are a helpful AI assistant. "
                    "Respond with valid JSON only.",
                )
            )
            # Convert dict back to JSON string for compatibility
            result: str = json.dumps(response_dict)
            return result

        # Fallback: check for deprecated _call_claude method
        if hasattr(self.ai_client, "_call_claude"):
            result = await self.ai_client._call_claude(prompt)
            return result

        # No compatible interface found
        raise ValueError(
            f"AI client {type(self.ai_client).__name__} does not support "
            "a compatible interface. Expected:\n"
            "  - generate_structured_response() method (preferred)\n"
            "  - _call_claude() method (deprecated)"
        )
