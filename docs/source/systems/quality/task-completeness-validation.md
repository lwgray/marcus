# Task Completeness Validation

## Overview

The Task Completeness Validation system ensures that Marcus's task decomposition fully covers all user intents from the project description. It uses AI-powered semantic matching to catch incomplete task generation **before** work begins.

### Motivation

Out of 100+ projects, Marcus once created MCP tools for a blackjack server but completely missed creating the actual `server.py` file - the MCP server entry point. This validation system prevents such gaps by validating task coverage immediately after decomposition.

### Key Features

- **AI-powered intent extraction**: Identifies core user intents from project description
- **Semantic coverage validation**: Validates tasks cover intents semantically (not keyword matching)
- **Automatic retry**: Retries decomposition with emphasis on missing intents (max 3 attempts)
- **Front-end validation**: Catches gaps before work starts, not after implementation
- **Structured logging**: Full traceability with correlation IDs

## How It Works

### Workflow

```
1. User creates project with description
   ↓
2. Marcus decomposes into tasks (PRD parser)
   ↓
3. TaskCompletenessValidator extracts intents
   ↓
4. Validator checks if tasks cover all intents
   ↓
5a. Complete → Continue to Kanban persistence
5b. Incomplete → Retry with emphasis (max 3 attempts)
   ↓
6. Success or BusinessLogicError after 3 failures
```

### Integration Point

Validation runs in `nlp_tools.py` → `process_natural_language()` method:

```python
# Location: src/integrations/nlp_tools.py, lines 92-129

# After task decomposition
prd_result = await self.prd_parser.parse_prd_to_tasks(description, constraints)

# NEW: Validate completeness with retry
validator = TaskCompletenessValidator(
    ai_client=self.ai_engine,
    prd_parser=self.prd_parser,
)

validation_result = await validator.validate_with_retry(
    description=description,
    project_name=project_name,
    tasks=prd_result.tasks,
    constraints=constraints,
    context=validation_context,
)

# Use validated tasks
prd_result.tasks = validation_result.final_tasks

# Continue to Kanban persistence...
```

## Components

### TaskCompletenessValidator

**Location**: [src/ai/validation/task_completeness_validator.py](../../src/ai/validation/task_completeness_validator.py)

#### Class Overview

```python
class TaskCompletenessValidator:
    """
    Validate tasks cover user intents with retry capability.

    Attributes
    ----------
    MAX_ATTEMPTS : int
        Maximum validation attempts before failing (3)
    ai_client : LLMAbstraction
        AI client for intent extraction and validation
    prd_parser : AdvancedPRDParser
        Parser for regenerating tasks on retry
    """
```

#### Key Methods

##### 1. extract_intents()

Extracts core user intents from project description using AI.

```python
async def extract_intents(
    self,
    description: str,
    project_name: str
) -> list[str]:
    """
    Extract core user intents from project description.

    Returns
    -------
    list[str]
        Simple list of intents (e.g., ["MCP server", "API wrapper"])

    Examples
    --------
    >>> intents = await validator.extract_intents(
    ...     "Build an MCP server that wraps the Deck of Cards API",
    ...     "deck-mcp"
    ... )
    >>> # Returns: ["MCP server", "Deck of Cards API wrapper", "MCP tools"]
    """
```

**AI Prompt Structure**:

```
Extract what the user wants to build from this description:

PROJECT: {project_name}
DESCRIPTION: {description}

Return JSON with simple list of intents:
{
  "intents": ["intent 1", "intent 2", "intent 3"]
}

Focus on core deliverables - what must exist for this project to work.
```

**Example Response**:

```json
{
  "intents": [
    "MCP server",
    "Deck of Cards API wrapper",
    "MCP tools for deck operations"
  ]
}
```

##### 2. validate_coverage()

Validates if tasks semantically cover all intents.

```python
async def validate_coverage(
    self,
    intents: list[str],
    tasks: list[Task]
) -> dict[str, Any]:
    """
    Validate if tasks semantically cover all intents.

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
    >>> # Returns: {"complete": False, "missing": ["MCP server"]}
    """
```

**AI Prompt Structure**:

```
Does this task list cover all the intents?

INTENTS:
- MCP server
- Deck of Cards API wrapper
- MCP tools for deck operations

TASKS:
- Create MCP tools: Implement MCP tools for deck operations
- Build API client: Create client to wrap Deck of Cards API

Return JSON:
{
  "complete": true|false,
  "missing": ["missing intent 1", "missing intent 2"]
}

If ALL intents are covered (semantically, not word-for-word), return complete=true.
If ANY intent is missing, return complete=false with the missing ones.
```

**Important**: Validation uses **both task name and description** for semantic matching.

##### 3. validate_with_retry()

Validates tasks with retry on missing intents.

```python
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

    Workflow:
    1. Extract intents once at start
    2. Validate current tasks
    3. If incomplete: retry with emphasis (max 3 attempts)
    4. Raise BusinessLogicError after 3 failures

    Returns
    -------
    CompletenessResult
        Final validation result with attempts and final tasks

    Raises
    ------
    BusinessLogicError
        If validation fails after MAX_ATTEMPTS
    """
```

**Retry Mechanism**:

```python
# Attempt 1: Validate original tasks
validation_result = await self.validate_coverage(intents, tasks)
# Result: {"complete": False, "missing": ["MCP server"]}

# Attempt 2: Retry with emphasis
emphasis = "IMPORTANT: Must include the following:\n  - MCP server"
current_description = f"{description}\n\n{emphasis}"
prd_result = await self.prd_parser.parse_prd_to_tasks(
    current_description, constraints
)
# Validate again with new tasks...

# Attempt 3: Final retry if still incomplete
# ...

# After 3 attempts: Raise BusinessLogicError
```

### Data Models

#### ValidationAttempt

```python
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
```

#### CompletenessResult

```python
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
```

## Configuration

### Environment Variables

No specific environment variables required. Uses existing AI provider configuration from `LLMAbstraction`.

### Settings

```python
# Maximum validation attempts before failure
TaskCompletenessValidator.MAX_ATTEMPTS = 3  # Default

# AI token limits for validation prompts
max_tokens = 2000  # Used for intent extraction and validation
```

## Usage Examples

### Successful Validation (First Attempt)

```python
from src.ai.validation import TaskCompletenessValidator
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser

# Initialize
ai_client = LLMAbstraction()
prd_parser = AdvancedPRDParser()
validator = TaskCompletenessValidator(ai_client, prd_parser)

# Validate
result = await validator.validate_with_retry(
    description="Build an MCP server that wraps the Deck of Cards API",
    project_name="deck-mcp",
    tasks=initial_tasks,
    constraints=constraints,
    context=error_context,
)

# Check result
assert result.is_complete is True
assert result.passed_on_attempt == 1
print(f"Validation passed on first attempt with {len(result.final_tasks)} tasks")
```

### Validation with Retry

```python
# Initial tasks missing "MCP server" creation
initial_tasks = [
    Task(name="Create MCP tools", description="..."),
    Task(name="Build API client", description="..."),
]

# Validate - will retry with emphasis
result = await validator.validate_with_retry(
    description="Build an MCP server that wraps the Deck of Cards API",
    project_name="deck-mcp",
    tasks=initial_tasks,
    constraints=constraints,
    context=error_context,
)

# Result after retry
assert result.is_complete is True
assert result.passed_on_attempt == 2
assert len(result.final_tasks) > len(initial_tasks)  # New tasks added

# Check retry history
for attempt in result.attempts:
    print(f"Attempt {attempt.attempt_number}: {attempt.is_complete}")
    if attempt.emphasis_added:
        print(f"  Emphasis: {attempt.emphasis_added}")
```

### Handling Validation Failure

```python
from src.core.error_framework import BusinessLogicError

try:
    result = await validator.validate_with_retry(
        description="Complex project description",
        project_name="my-project",
        tasks=initial_tasks,
        constraints=constraints,
        context=error_context,
    )
except BusinessLogicError as e:
    # After 3 failed attempts
    print(f"Validation failed: {e.message}")
    print(f"Missing intents: {e.context.custom_context.get('missing_intents')}")
    print(f"Remediation: {e.remediation.immediate_action}")
    # User must manually review and add missing tasks
```

## Logging and Debugging

### Structured Logging

All validation attempts are logged with correlation IDs for tracing:

```python
logger.info(
    f"Validation attempt {attempt_num}/{MAX_ATTEMPTS}: complete={is_complete}",
    extra={
        "correlation_id": context.correlation_id,
        "attempt": attempt_num,
        "is_complete": is_complete,
        "missing": missing_intents,
    },
)
```

### Log Examples

**Successful first attempt**:

```
INFO: Extracted 3 intents for validation
  correlation_id=proj-123-abc
  intents=["MCP server", "API wrapper", "MCP tools"]

INFO: Validation attempt 1/3: complete=True
  correlation_id=proj-123-abc
  attempt=1
  is_complete=True
  missing=[]

INFO: Validation passed on attempt 1
  correlation_id=proj-123-abc
  attempts=1
  passed_on_attempt=1
```

**Retry with emphasis**:

```
INFO: Extracted 3 intents for validation
  correlation_id=proj-456-def
  intents=["MCP server", "API wrapper", "MCP tools"]

INFO: Validation attempt 1/3: complete=False
  correlation_id=proj-456-def
  attempt=1
  is_complete=False
  missing=["MCP server"]

INFO: Retrying task decomposition with emphasis
  correlation_id=proj-456-def
  attempt=2
  emphasis="IMPORTANT: Must include the following:\n  - MCP server"

INFO: Validation attempt 2/3: complete=True
  correlation_id=proj-456-def
  attempt=2
  is_complete=True
  missing=[]

INFO: Validation passed on attempt 2
  correlation_id=proj-456-def
  attempts=2
  passed_on_attempt=2
```

### Debugging Failed Validation

To debug validation failures:

1. **Find correlation ID** from error message or logs
2. **Search logs** for all entries with that correlation ID
3. **Review validation attempts**:
   ```bash
   grep "correlation_id=proj-789-ghi" marcus.log | grep "Validation attempt"
   ```
4. **Check missing intents** in each attempt
5. **Review emphasis text** added in retries
6. **Examine final error** with remediation suggestions

### Correlation ID Tracing

```python
# Error context automatically creates correlation ID
with error_context(
    "task_completeness_validation",
    custom_context={
        "project_name": "deck-mcp",
        "initial_task_count": 5,
    },
) as validation_context:
    # All logs and errors will include validation_context.correlation_id
    result = await validator.validate_with_retry(...)
```

## Error Handling

### BusinessLogicError After 3 Attempts

```python
raise BusinessLogicError(
    f"Task validation failed after {MAX_ATTEMPTS} attempts. "
    f"Missing {len(missing_intents)} intents: {missing_str}",
    context=context,
    remediation={
        "immediate_action": f"Review project tasks and manually add: {missing_str}",
        "long_term_solution": "Improve task decomposition prompts or validation thresholds",
        "retry_strategy": f"Already retried {MAX_ATTEMPTS} times",
    },
)
```

### Fallback Behavior

- **AI provider failures**: Handled by `LLMAbstraction` with retry and circuit breaker
- **Invalid JSON responses**: Falls back to treating description as single intent
- **Empty task list**: Validation will fail (missing all intents)
- **Network errors**: Retried automatically via error strategies

## Performance Characteristics

### Typical Performance

- **First attempt validation**: ~2-4 seconds (2 AI calls: extract_intents + validate_coverage)
- **Retry with re-parsing**: ~10-15 seconds (full task decomposition + validation)
- **Total with 2 retries**: ~25-30 seconds maximum

### Token Usage

- **Intent extraction**: ~500-1000 tokens per call
- **Coverage validation**: ~1000-2000 tokens per call (includes all task descriptions)
- **Total per validation**: ~3000-6000 tokens (more with retries)

### Optimization Tips

- Validation runs **once per project creation** (front-end check)
- No ongoing performance impact after validation passes
- Token usage scales with number of tasks and description length

## Testing

### Unit Tests

**Location**: [tests/unit/ai/validation/test_task_completeness_validator.py](../../../tests/unit/ai/validation/test_task_completeness_validator.py)

**Coverage**: 83.5%

**Key test scenarios**:
- Intent extraction success
- Coverage validation (complete and incomplete)
- Retry passes on first attempt
- Retry passes on second attempt with emphasis
- Failure after max attempts (raises BusinessLogicError)
- Emphasis text generation

**Running unit tests**:

```bash
pytest tests/unit/ai/validation/ -v
```

### Integration Tests

**Location**: [tests/integration/ai/test_task_validation_e2e.py](../../../tests/integration/ai/test_task_validation_e2e.py)

**Purpose**: Test with real AI provider using MCP server scenario

**Running integration tests**:

```bash
pytest tests/integration/ai/test_task_validation_e2e.py -v --tb=short
```

## Troubleshooting

### Validation Always Fails

**Symptoms**: Validation fails after 3 attempts even for simple projects

**Possible causes**:
1. AI provider not responding correctly
2. Task descriptions too vague for semantic matching
3. Intents extracted don't match task granularity

**Solutions**:
- Check AI provider logs for errors
- Review extracted intents in logs (look for correlation_id)
- Ensure task descriptions are detailed enough
- Consider adjusting intent extraction prompt if intents are too granular

### False Positives (Missing Tasks Not Caught)

**Symptoms**: Validation passes but tasks are still incomplete

**Possible causes**:
1. Intents extracted are too high-level
2. Task descriptions match intents semantically but implementation is wrong
3. AI provider being too lenient in coverage validation

**Solutions**:
- Review intent extraction prompt to be more specific
- Add more detail to project description
- Consider adjusting validation prompt to be stricter

### Excessive Retries

**Symptoms**: Validation always takes 2-3 attempts even when tasks seem complete

**Possible causes**:
1. Task decomposition prompts inconsistent with validation prompts
2. Missing intents are actually covered but named differently
3. AI provider variance in responses

**Solutions**:
- Review retry logs to see which intents are "missing"
- Align task decomposition prompts with intent extraction
- Consider adding examples to validation prompts

## Future Enhancements

### Potential Improvements

1. **Configurable retry limit**: Allow users to adjust `MAX_ATTEMPTS`
2. **Validation metrics**: Track validation success rate, retry frequency
3. **Custom intent extraction**: Allow domain-specific intent templates
4. **Validation caching**: Cache intents for similar project descriptions
5. **Human-in-the-loop**: Option to pause and ask user to confirm missing intents
6. **Severity scoring**: Differentiate critical vs. nice-to-have missing intents

### Related Systems

- **Task Decomposition** ([src/ai/advanced/prd/advanced_parser.py](../../src/ai/advanced/prd/advanced_parser.py))
- **Error Framework** ([src/core/error_framework.py](../../src/core/error_framework.py))
- **AI Providers** ([src/ai/providers/llm_abstraction.py](../../src/ai/providers/llm_abstraction.py))
- **NLP Tools** ([src/integrations/nlp_tools.py](../../src/integrations/nlp_tools.py))

## See Also

- [Quality Assurance System](../quality/README.md)
- [AI Intelligence System](../intelligence/README.md)
- [Error Handling Framework](../../core/error-framework.md)
- [Project Management](../project-management/README.md)
