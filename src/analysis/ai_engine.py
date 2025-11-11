"""
AI Engine Integration for Phase 2 analysis.

Provides structured LLM interaction for post-project analysis with:
- Analysis-specific prompt templates
- Response parsing and validation
- Caching integration
- Progress reporting
- Citation enforcement

Usage
-----
```python
engine = AnalysisAIEngine()

# Create analysis request
request = AnalysisRequest(
    analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
    project_id="proj-123",
    task_id="task-456",
    context_data={
        "requirement": "User can login with email",
        "implementation": "Built OAuth2 login",
        "conversation": conversation_text,
    },
    prompt_template=REQUIREMENT_DIVERGENCE_PROMPT,
)

# Execute analysis
response = await engine.analyze(request, progress_callback=my_callback)
print(f"Fidelity score: {response.parsed_result['fidelity_score']}")
```
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.analysis.helpers.progress import ProgressCallback, ProgressReporter

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """
    Types of post-project analysis.

    Maps to the four core analyzers plus overall assessment from Phase 2 spec.
    """

    REQUIREMENT_DIVERGENCE = "requirement_divergence"
    DECISION_IMPACT = "decision_impact"
    INSTRUCTION_QUALITY = "instruction_quality"
    FAILURE_DIAGNOSIS = "failure_diagnosis"
    OVERALL_ASSESSMENT = "overall_assessment"


@dataclass
class AnalysisRequest:
    """
    Request for LLM-powered analysis.

    Attributes
    ----------
    analysis_type : AnalysisType
        Type of analysis to perform
    project_id : str
        Project being analyzed
    task_id : Optional[str]
        Specific task (None for project-level analysis)
    context_data : dict
        Data to include in the prompt (requirements, decisions, etc.)
    prompt_template : str
        Template string for the analysis prompt
    max_tokens : int, optional
        Maximum tokens for LLM response (default: 4000)
    temperature : float, optional
        LLM temperature for response randomness (default: 0.0 for consistency)
    """

    analysis_type: AnalysisType
    project_id: str
    task_id: Optional[str]
    context_data: dict[str, Any]
    prompt_template: str
    max_tokens: int = 4000
    temperature: float = 0.0  # Low temperature for consistent analysis


@dataclass
class AnalysisResponse:
    """
    Response from LLM analysis.

    Attributes
    ----------
    analysis_type : AnalysisType
        Type of analysis performed
    raw_response : str
        Raw LLM output text
    parsed_result : dict
        Structured data extracted from response
    confidence : float
        LLM confidence in the analysis (0.0-1.0)
    timestamp : datetime
        When this analysis was performed
    model_used : str
        Which LLM model generated this response
    cached : bool
        Whether this was retrieved from cache
    """

    analysis_type: AnalysisType
    raw_response: str
    parsed_result: dict[str, Any]
    confidence: float
    timestamp: datetime
    model_used: str
    cached: bool = False


class AnalysisAIEngine:
    """
    AI engine for Phase 2 post-project analysis.

    Wraps Marcus's existing LLMAbstraction with analysis-specific functionality:
    - Structured prompts that enforce citations
    - JSON response parsing
    - Request caching via hashmap
    - Progress reporting integration

    Parameters
    ----------
    llm_client : Optional[LLMAbstraction]
        LLM client to use (creates new one if None)

    Examples
    --------
    ```python
    engine = AnalysisAIEngine()

    # Simple analysis
    request = AnalysisRequest(
        analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
        project_id="proj-123",
        task_id="task-456",
        context_data={"requirement": "...", "implementation": "..."},
        prompt_template=template_string,
    )
    response = await engine.analyze(request)

    # With progress reporting
    async def progress_callback(event: ProgressEvent):
        print(f"{event.message} ({event.current}/{event.total})")

    response = await engine.analyze(request, progress_callback=progress_callback)
    ```
    """

    def __init__(self, llm_client: Optional[LLMAbstraction] = None):
        """
        Initialize AI engine.

        Parameters
        ----------
        llm_client : Optional[LLMAbstraction]
            LLM client to use (creates default if None)
        """
        self.llm_client = llm_client or LLMAbstraction()
        self._cache: dict[str, AnalysisResponse] = {}
        logger.info("Analysis AI Engine initialized")

    async def analyze(
        self,
        request: AnalysisRequest,
        progress_callback: Optional[ProgressCallback] = None,
        use_cache: bool = True,
    ) -> AnalysisResponse:
        """
        Perform LLM-powered analysis.

        Parameters
        ----------
        request : AnalysisRequest
            Analysis request with prompt and context
        progress_callback : Optional[Callable]
            Callback for progress updates
        use_cache : bool
            Whether to use cached results (default: True)

        Returns
        -------
        AnalysisResponse
            Structured analysis result

        Examples
        --------
        ```python
        request = AnalysisRequest(
            analysis_type=AnalysisType.REQUIREMENT_DIVERGENCE,
            project_id="proj-123",
            task_id="task-456",
            context_data={"req": "...", "impl": "..."},
            prompt_template="Compare {req} vs {impl}",
        )

        response = await engine.analyze(request)
        print(f"Fidelity: {response.parsed_result['fidelity_score']}")
        ```
        """
        # Check cache first
        if use_cache:
            cache_key = self.get_cache_key(request)
            if cache_key in self._cache:
                logger.debug(f"Using cached analysis for {cache_key[:16]}...")
                return self._cache[cache_key]

        # Set up progress reporting
        reporter = ProgressReporter(callback=progress_callback)

        async with reporter.operation(
            f"analyze_{request.analysis_type.value}", total=100
        ) as progress:
            # Build complete prompt
            await progress.update(10, "Building prompt...")
            full_prompt = self._build_prompt(request)

            # Execute LLM call
            await progress.update(20, "Calling LLM...")
            raw_response = await self.llm_client.analyze(
                prompt=full_prompt,
                context=request,  # Pass request as context
            )

            # Parse response
            await progress.update(80, "Parsing response...")
            try:
                parsed_result = self.parse_json_response(raw_response)
            except ValueError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
                # Fall back to raw response in a structured format
                parsed_result = {
                    "raw_output": raw_response,
                    "parse_error": str(e),
                }

            # Extract confidence if present
            confidence = parsed_result.get("confidence", 0.8)

            # Create response
            await progress.update(100, "Complete")
            response = AnalysisResponse(
                analysis_type=request.analysis_type,
                raw_response=raw_response,
                parsed_result=parsed_result,
                confidence=float(confidence),
                timestamp=datetime.now(timezone.utc),
                model_used="claude-3-sonnet",  # Will be determined by LLM client
                cached=False,
            )

        # Cache the response
        if use_cache:
            cache_key = self.get_cache_key(request)
            self._cache[cache_key] = response

        return response

    def _build_prompt(self, request: AnalysisRequest) -> str:
        """
        Build complete prompt from request.

        Combines system instructions, user template, and context data.

        Parameters
        ----------
        request : AnalysisRequest
            Request with template and context

        Returns
        -------
        str
            Complete formatted prompt
        """
        # Get system instructions for this analysis type
        system_prompt = self.build_system_prompt(request.analysis_type)

        # Format user template with context data
        try:
            user_prompt = request.prompt_template.format(**request.context_data)
        except KeyError as e:
            logger.error(f"Missing context data for prompt template: {e}")
            # Use template as-is if formatting fails
            user_prompt = request.prompt_template

        # Combine system + user prompts
        full_prompt = f"""{system_prompt}

---

{user_prompt}

IMPORTANT: Your response must be valid JSON. Include citations
(task_id, decision_id, timestamp, line numbers) for every claim."""

        return full_prompt

    def build_system_prompt(self, analysis_type: AnalysisType) -> str:
        """
        Build system prompt for a specific analysis type.

        Each analysis type gets specialized instructions that enforce
        the critical principle from Phase 2: always pair raw data with
        LLM interpretation and cite sources.

        Parameters
        ----------
        analysis_type : AnalysisType
            Type of analysis to generate instructions for

        Returns
        -------
        str
            System prompt with analysis-specific instructions

        Examples
        --------
        >>> engine = AnalysisAIEngine()
        >>> prompt = engine.build_system_prompt(
        ...     AnalysisType.REQUIREMENT_DIVERGENCE
        ... )
        >>> assert "cite" in prompt.lower()
        >>> assert "task_id" in prompt.lower()
        """
        base_instructions = """You are analyzing a completed software project
to determine what was built vs. what was intended.

CRITICAL RULES:
1. Always pair raw data with your interpretation
2. Cite sources with task_id, decision_id, timestamp, line numbers
3. Return valid JSON only (no markdown, no explanations outside JSON)
4. Be objective and evidence-based
5. Distinguish between what you observe vs. what you infer"""

        type_specific = {
            AnalysisType.REQUIREMENT_DIVERGENCE: """
ANALYSIS FOCUS: Requirement Fidelity
- Compare stated requirements vs. actual implementation
- Calculate fidelity score (0.0-1.0)
- List specific divergences with evidence
- Include both raw data and your interpretation for each finding""",
            AnalysisType.DECISION_IMPACT: """
ANALYSIS FOCUS: Decision Impact Tracing
- Trace how decisions affected project outcomes
- Identify cascading effects of key choices
- Assess whether decisions achieved intended results
- Cite specific decision_id for each traced impact""",
            AnalysisType.INSTRUCTION_QUALITY: """
ANALYSIS FOCUS: Instruction Quality Assessment
- Evaluate clarity and completeness of task instructions
- Identify ambiguities that led to confusion
- Assess whether agents could reasonably understand requirements
- Include conversation excerpts (with line numbers) as evidence""",
            AnalysisType.FAILURE_DIAGNOSIS: """
ANALYSIS FOCUS: Failure Root Cause Analysis
- Diagnose why specific tasks or features failed
- Distinguish symptoms from root causes
- Trace failure chains (initial cause → effects → outcome)
- Provide actionable remediation suggestions""",
            AnalysisType.OVERALL_ASSESSMENT: """
ANALYSIS FOCUS: Overall Project Assessment
- Synthesize findings from all other analyses
- Calculate aggregate scores (requirement fidelity, user alignment)
- Determine functional status (WORKS/PARTIAL/BROKEN)
- Provide executive summary with key insights""",
        }

        return f"""{base_instructions}

{type_specific.get(analysis_type, "")}

Remember: Every claim needs a citation. Every interpretation needs raw data."""

    def parse_json_response(self, response: str) -> dict[str, Any]:
        r"""
        Parse JSON from LLM response.

        Handles common LLM quirks like markdown code blocks, extra text, etc.

        Parameters
        ----------
        response : str
            Raw LLM response text

        Returns
        -------
        dict
            Parsed JSON data

        Raises
        ------
        ValueError
            If response cannot be parsed as JSON

        Examples
        --------
        >>> engine = AnalysisAIEngine()
        >>> result = engine.parse_json_response('{"score": 0.85}')
        >>> assert result["score"] == 0.85
        >>>
        >>> # Handles markdown
        >>> result = engine.parse_json_response(
        ...     r'```json\n{"score": 0.85}\n```'
        ... )
        >>> assert result["score"] == 0.85
        """
        # Remove markdown code blocks if present
        response = response.strip()

        # Extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            response = json_match.group(1).strip()

        # Try to find JSON object in response
        if not response.startswith("{"):
            # Look for first { to last }
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                response = response[start : end + 1]

        try:
            parsed: dict[str, Any] = json.loads(response)
            return parsed
        except json.JSONDecodeError as e:
            # Try to extract just the first complete JSON object
            # This handles cases where LLM adds explanation after JSON
            try:
                decoder = json.JSONDecoder()
                parsed, idx = decoder.raw_decode(response)
                # Check if there's significant content after the JSON
                remaining = response[idx:].strip()
                if remaining:
                    logger.debug(
                        f"Parsed JSON successfully. "
                        f"Found {len(remaining)} chars of extra content "
                        f"(LLM added explanation despite instructions)"
                    )
                return parsed
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.debug(f"Response was: {response[:500]}...")
                raise ValueError(f"Invalid JSON response from LLM: {e}")

    def get_cache_key(self, request: AnalysisRequest) -> str:
        """
        Generate cache key for a request.

        Uses hash of analysis type, project, task, and context data
        to create a unique key for caching.

        Parameters
        ----------
        request : AnalysisRequest
            Request to generate key for

        Returns
        -------
        str
            Cache key (SHA256 hash)

        Examples
        --------
        >>> engine = AnalysisAIEngine()
        >>> req1 = AnalysisRequest(...)
        >>> req2 = AnalysisRequest(...)  # Different data
        >>> assert engine.get_cache_key(req1) != engine.get_cache_key(req2)
        """
        # Create deterministic string from request
        key_components = [
            request.analysis_type.value,
            request.project_id,
            request.task_id or "project-level",
            json.dumps(request.context_data, sort_keys=True),
            request.prompt_template,
        ]

        key_string = "|".join(key_components)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def clear_cache(self) -> int:
        """
        Clear the analysis cache.

        Returns
        -------
        int
            Number of cached entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cached analysis results")
        return count

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns
        -------
        dict
            Cache stats including size, types cached, etc.
        """
        type_counts: dict[str, int] = {}
        for response in self._cache.values():
            type_name = response.analysis_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_cached": len(self._cache),
            "by_type": type_counts,
        }
