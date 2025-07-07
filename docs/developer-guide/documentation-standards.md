# Marcus Documentation Standards

This document defines the documentation standards for the Marcus project. All Python code must follow these standards to ensure consistency and maintainability.

## Type Hints

All functions, methods, and class attributes must include type hints following PEP 484 and PEP 526.

### Basic Type Hints

```python
from typing import List, Dict, Optional, Union, Tuple, Any, Callable, TypeVar, Generic

def process_data(input_data: str, count: int = 10) -> Dict[str, Any]:
    """Process input data and return results."""
    pass

class DataProcessor:
    name: str
    batch_size: int
    
    def __init__(self, name: str, batch_size: int = 100) -> None:
        self.name = name
        self.batch_size = batch_size
```

### Advanced Type Hints

```python
from typing import Protocol, Literal, TypedDict, overload

class ConfigDict(TypedDict):
    """Configuration dictionary type."""
    api_key: str
    timeout: float
    retry_count: int
    debug: bool

TaskStatus = Literal["pending", "in_progress", "completed", "failed"]

T = TypeVar('T')
class Registry(Generic[T]):
    """Generic registry for storing typed items."""
    _items: Dict[str, T]
```

## Numpy-Style Docstrings

All modules, classes, and functions must have numpy-style docstrings. Use Google style for simple cases, but prefer numpy style for complex signatures.

### Module Docstring

```python
"""
AI provider interface module.

This module provides abstract base classes and implementations for various
AI providers including OpenAI, Anthropic, and Groq. It handles API communication,
response parsing, and error handling.

Classes
-------
AIProvider
    Abstract base class for AI providers
OpenAIProvider
    OpenAI API implementation
AnthropicProvider
    Anthropic Claude API implementation

Functions
---------
get_provider
    Factory function to get appropriate provider instance
validate_response
    Validate AI provider responses

Examples
--------
>>> provider = get_provider("openai", api_key="...")
>>> response = await provider.generate("Hello, world!")
>>> print(response.content)
"""
```

### Class Docstring

```python
class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    
    This class defines the interface that all AI providers must implement.
    It handles common functionality like rate limiting, retries, and logging.
    
    Parameters
    ----------
    api_key : str
        API key for authentication
    model : str
        Model identifier to use
    timeout : float, optional
        Request timeout in seconds (default is 30.0)
    max_retries : int, optional
        Maximum number of retry attempts (default is 3)
    
    Attributes
    ----------
    api_key : str
        Stored API key
    model : str
        Active model identifier
    timeout : float
        Request timeout value
    session : aiohttp.ClientSession
        Async HTTP session for API calls
    
    Methods
    -------
    generate(prompt, **kwargs)
        Generate a response from the AI model
    validate_response(response)
        Validate the response format
    
    Raises
    ------
    ValueError
        If api_key is empty or invalid
    ConfigurationError
        If model is not supported
    
    See Also
    --------
    OpenAIProvider : OpenAI specific implementation
    AnthropicProvider : Anthropic specific implementation
    
    Notes
    -----
    All providers use exponential backoff for retries with jitter to avoid
    thundering herd problems.
    
    Examples
    --------
    >>> class CustomProvider(AIProvider):
    ...     async def generate(self, prompt: str, **kwargs) -> AIResponse:
    ...         # Implementation here
    ...         pass
    """
```

### Function/Method Docstring

```python
async def generate(
    self,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stop_sequences: Optional[List[str]] = None,
    **kwargs: Any
) -> AIResponse:
    """
    Generate a response from the AI model.
    
    Sends a prompt to the AI model and returns the generated response.
    Handles rate limiting, retries, and response validation automatically.
    
    Parameters
    ----------
    prompt : str
        The input prompt to send to the model
    temperature : float, optional
        Sampling temperature between 0 and 2 (default is 0.7)
        Higher values make output more random
    max_tokens : int, optional
        Maximum tokens to generate (default is model-specific)
    stop_sequences : list of str, optional
        Sequences where generation should stop
    **kwargs
        Additional provider-specific parameters
    
    Returns
    -------
    AIResponse
        Response object containing:
        - content (str): Generated text
        - usage (dict): Token usage statistics
        - model (str): Model used for generation
        - finish_reason (str): Why generation stopped
    
    Raises
    ------
    APIError
        If the API request fails after retries
    ValidationError
        If the response format is invalid
    RateLimitError
        If rate limit is exceeded and retries exhausted
    
    See Also
    --------
    generate_stream : Streaming version of generate
    generate_batch : Batch processing multiple prompts
    
    Notes
    -----
    The function automatically retries on transient errors with exponential
    backoff. Rate limit errors are handled with longer backoff periods.
    
    Examples
    --------
    >>> provider = OpenAIProvider(api_key="...")
    >>> response = await provider.generate(
    ...     "Explain quantum computing",
    ...     temperature=0.5,
    ...     max_tokens=200
    ... )
    >>> print(response.content)
    
    For streaming responses:
    
    >>> async for chunk in provider.generate_stream("Tell me a story"):
    ...     print(chunk, end="", flush=True)
    """
```

### Property Docstring

```python
@property
def is_connected(self) -> bool:
    """
    Check if provider is connected and authenticated.
    
    Returns
    -------
    bool
        True if connected and authenticated, False otherwise
    
    Notes
    -----
    This property checks both network connectivity and API key validity.
    """
    return self._connected and self._authenticated
```

## Documentation Templates

### Template: Simple Function

```python
def function_name(param1: type1, param2: type2 = default) -> return_type:
    """
    Brief one-line description.
    
    Parameters
    ----------
    param1 : type1
        Description of param1
    param2 : type2, optional
        Description of param2 (default is `default`)
    
    Returns
    -------
    return_type
        Description of return value
    """
```

### Template: Complex Function with Errors

```python
def complex_function(
    data: pd.DataFrame,
    config: Dict[str, Any],
    callback: Optional[Callable[[int], None]] = None
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Brief one-line description.
    
    Longer description explaining the function's purpose,
    algorithm, or important details.
    
    Parameters
    ----------
    data : pd.DataFrame
        Input dataframe with columns ['id', 'value', 'timestamp']
    config : dict
        Configuration dictionary with keys:
        - 'threshold' (float): Processing threshold
        - 'method' (str): Algorithm to use ('fast' or 'accurate')
    callback : callable, optional
        Progress callback function that receives percentage complete
    
    Returns
    -------
    processed_data : pd.DataFrame
        Processed dataframe with additional 'score' column
    metrics : dict
        Processing metrics:
        - 'duration' (float): Processing time in seconds
        - 'rows_processed' (int): Number of rows processed
    
    Raises
    ------
    ValueError
        If data is empty or config is invalid
    ProcessingError
        If processing fails due to data issues
    
    Examples
    --------
    >>> df = pd.DataFrame({'id': [1, 2], 'value': [10, 20]})
    >>> result, metrics = complex_function(df, {'threshold': 15})
    >>> print(metrics['rows_processed'])
    2
    """
```

## Pre-commit Configuration

Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]
        additional_dependencies: [types-all]
        
  - repo: https://github.com/pycqa/pydocstyle
    rev: 6.3.0
    hooks:
      - id: pydocstyle
        args: [--convention=numpy]
        exclude: tests/
```

## Enforcement Tools

### mypy Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

### pydocstyle Configuration (pyproject.toml)

```toml
[tool.pydocstyle]
convention = "numpy"
add-ignore = ["D100", "D104"]  # Module and package docstrings optional
match-dir = "^(?!tests).*"
```

## Best Practices

1. **Be Specific**: Use specific types rather than `Any` when possible
2. **Document Edge Cases**: Explain behavior for None, empty inputs, etc.
3. **Include Examples**: Add doctests or usage examples for complex functions
4. **Cross-Reference**: Use "See Also" section to link related functions
5. **Explain Parameters**: Don't just repeat the type, explain purpose and constraints
6. **Version Notes**: Use "Notes" section for implementation details or version info

## Validation Commands

```bash
# Check type hints
mypy src/

# Check docstrings
pydocstyle src/

# Generate documentation
sphinx-build -b html docs/source docs/build

# Run all checks
pre-commit run --all-files
```