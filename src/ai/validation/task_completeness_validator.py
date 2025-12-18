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
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.core.error_framework import BusinessLogicError, ErrorContext
from src.core.models import Task

logger = logging.getLogger(__name__)


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

    Attributes
    ----------
    MAX_ATTEMPTS : int
        Maximum validation attempts before failing (class constant = 3)
    ai_client : LLMAbstraction
        AI client for intent extraction and validation
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
        ai_client: LLMAbstraction,
        prd_parser: AdvancedPRDParser,
    ) -> None:
        """
        Initialize validator with dependencies.

        Parameters
        ----------
        ai_client : LLMAbstraction
            AI client for intent extraction and validation
        prd_parser : AdvancedPRDParser
            Parser for regenerating tasks on retry
        """
        self.ai_client = ai_client
        self.prd_parser = prd_parser
        self.logger = logging.getLogger(__name__)

    async def extract_intents(self, description: str, project_name: str) -> list[str]:
        """
        Extract core user intents from project description.

        Uses AI to identify what the user fundamentally wants to build.

        Parameters
        ----------
        description : str
            Project description from user
        project_name : str
            Name of the project

        Returns
        -------
        list[str]
            List of intent strings (e.g., ["MCP server", "API wrapper"])

        Examples
        --------
        >>> intents = await validator.extract_intents(
        ...     "Build an MCP server that wraps the Deck API",
        ...     "deck-mcp"
        ... )
        >>> assert "MCP server" in intents
        """
        prompt = f"""Extract what the user wants to build from this description:

PROJECT: {project_name}
DESCRIPTION: {description}

Return JSON with simple list of intents:
{{
  "intents": ["intent 1", "intent 2", "intent 3"]
}}

Example:
Description: "Build an MCP server that wraps the Deck of Cards API"
Intents: ["MCP server", "Deck of Cards API wrapper", "MCP tools for deck operations"]

Focus on core deliverables - what must exist for this project to work.
Be concise. Return only valid JSON."""

        try:
            # Use the provider's complete method for simple prompts
            response_text = await self._call_ai(prompt)
            response_data = json.loads(response_text)
            intents: list[str] = response_data["intents"]
            return intents

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse intent extraction response: {e}",
                extra={"response": response_text},
            )
            # Fallback: try to extract reasonable intents from description
            return [description[:100]]  # Use truncated description as fallback

    async def validate_coverage(
        self, intents: list[str], tasks: list[Task]
    ) -> dict[str, Any]:
        """
        Validate if tasks semantically cover all intents.

        Uses AI for semantic matching - not exact phrase matching.

        Parameters
        ----------
        intents : list[str]
            Core user intents to verify
        tasks : list[Task]
            Generated tasks to check against

        Returns
        -------
        dict
            {"complete": bool, "missing": list[str]}

        Examples
        --------
        >>> result = await validator.validate_coverage(
        ...     ["MCP server", "API wrapper"],
        ...     [Task(name="Create MCP tools", description="..."), ...]
        ... )
        >>> if not result["complete"]:
        ...     print(f"Missing: {result['missing']}")
        """
        # Format tasks with name and description
        task_list = "\n".join([f"- {task.name}: {task.description}" for task in tasks])

        intent_list = "\n".join([f"- {intent}" for intent in intents])

        prompt = f"""Does this task list cover all the intents?

INTENTS:
{intent_list}

TASKS:
{task_list}

Return JSON:
{{
  "complete": true|false,
  "missing": ["missing intent 1", "missing intent 2"]
}}

If ALL intents are covered (semantically, not word-for-word), return complete=true.
If ANY intent is missing, return complete=false with the missing ones.
Return only valid JSON."""

        try:
            response_text = await self._call_ai(prompt)
            response_data = json.loads(response_text)

            return {
                "complete": response_data.get("complete", False),
                "missing": response_data.get("missing", []),
            }

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error(
                f"Failed to parse validation response: {e}",
                extra={"response": response_text},
            )
            # Fallback: assume incomplete to be safe
            return {"complete": False, "missing": intents}

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
        # Extract intents once at the start
        intents = await self.extract_intents(description, project_name)

        self.logger.info(
            f"Extracted {len(intents)} intents for validation",
            extra={
                "correlation_id": context.correlation_id,
                "intents": intents,
            },
        )

        attempts: list[ValidationAttempt] = []
        current_description = description
        current_tasks = tasks

        for attempt_num in range(1, self.MAX_ATTEMPTS + 1):
            # Validate current tasks
            validation_result = await self.validate_coverage(intents, current_tasks)

            is_complete = validation_result["complete"]
            missing = validation_result["missing"]

            # Record attempt
            attempt = ValidationAttempt(
                attempt_number=attempt_num,
                is_complete=is_complete,
                missing_intents=missing,
                timestamp=datetime.now(timezone.utc),
                correlation_id=context.correlation_id,
                emphasis_added=(
                    None if attempt_num == 1 else self._create_emphasis_text(missing)
                ),
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

            # Retry with emphasis on missing intents
            emphasis = self._create_emphasis_text(missing)
            current_description = f"{description}\n\n{emphasis}"

            self.logger.info(
                "Retrying task decomposition with emphasis",
                extra={
                    "correlation_id": context.correlation_id,
                    "attempt": attempt_num + 1,
                    "emphasis": emphasis,
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
        raise BusinessLogicError(
            f"Task validation failed after {self.MAX_ATTEMPTS} attempts. "
            f"Missing {len(final_attempt.missing_intents)} intents: {missing_str}",
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

    def _create_emphasis_text(self, missing_intents: list[str]) -> str:
        """
        Create emphasis text from missing intents for retry.

        Parameters
        ----------
        missing_intents : list[str]
            Intents that were not covered

        Returns
        -------
        str
            Emphasis text to append to description

        Examples
        --------
        >>> emphasis = validator._create_emphasis_text(["MCP server", "docs"])
        >>> assert "IMPORTANT" in emphasis
        >>> assert "MCP server" in emphasis
        """
        if not missing_intents:
            return ""

        parts = ["IMPORTANT: Must include the following:"]
        for intent in missing_intents:
            parts.append(f"  - {intent}")

        return "\n".join(parts)

    async def _call_ai(self, prompt: str) -> str:
        """
        Make AI call with proper provider handling.

        Parameters
        ----------
        prompt : str
            Prompt to send to AI

        Returns
        -------
        str
            AI response text

        Raises
        ------
        Exception
            If AI call fails
        """
        # Initialize providers if needed
        if not self.ai_client._providers_initialized:
            self.ai_client._initialize_providers()

        # Use the current provider's complete method
        provider = self.ai_client.providers.get(self.ai_client.current_provider)
        if provider and hasattr(provider, "complete"):
            result: str = await provider.complete(prompt, max_tokens=2000)
            return result

        # Fallback: try anthropic directly
        from src.ai.providers.anthropic_provider import AnthropicProvider

        fallback_provider = AnthropicProvider()
        fallback_result: str = await fallback_provider.complete(prompt, max_tokens=2000)
        return fallback_result
