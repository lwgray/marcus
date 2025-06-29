# Marcus Test Suite Documentation

## Overview

The Marcus test suite is organized to provide comprehensive coverage of all components while maintaining clarity and ease of maintenance. We follow Test-Driven Development (TDD) practices and maintain a minimum of 80% code coverage.

## Test Organization

```
tests/
├── unit/                    # Isolated unit tests
│   ├── core/               # Core functionality tests
│   ├── ai/                 # AI components tests
│   ├── mcp/                # MCP protocol tests
│   └── visualization/      # UI/visualization tests
├── integration/            # Integration tests
│   ├── e2e/               # End-to-end tests
│   ├── api/               # API integration tests
│   └── external/          # External service tests
├── performance/           # Performance tests
│   ├── benchmarks/        # Performance benchmarks
│   └── load/              # Load testing
├── diagnostics/           # Diagnostic and debugging tests
├── fixtures/              # Shared test data and fixtures
├── utils/                 # Test utilities and helpers
└── archive/               # Archived/deprecated tests
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest -m unit
pytest -m integration

# Run without pytest-asyncio (to avoid introspection issues)
pytest -p no:asyncio tests/unit/test_marcus_server_complete.py
```

### Using the Test Runner Script

```bash
# Run all tests with coverage
python scripts/run_tests.py

# Run specific test types
python scripts/run_tests.py --type unit
python scripts/run_tests.py --type integration
python scripts/run_tests.py --type performance

# Run with verbose output
python scripts/run_tests.py -v

# Run with parallel execution
python scripts/run_tests.py -n auto
```

## Test Categories

### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Mock all external dependencies
- Should run quickly (< 100ms per test)
- No network calls or file I/O

Current unit tests:
- **`test_marcus_server_complete.py`** ✅ - Comprehensive Marcus server tests using anyio
- **`test_simple_client_unit.py`** ✅ - SimpleMCPKanbanClient internal methods
- **`test_workspace_manager.py`** ✅ - Workspace security and path validation
- **`test_models.py`** ✅ - Data models (Task, Worker, etc.)
- **`test_settings.py`** ✅ - Configuration management
- **`test_ai_analysis_engine.py`** ✅ - AI engine initialization and prompts

### Integration Tests (`tests/integration/`)
- Test interactions between components
- May use real services with test configurations
- Test API endpoints and service integrations
- Requires running kanban-mcp server

Current integration tests:
- **`test_simple_client_comprehensive.py`** ✅ - Comprehensive SimpleMCPKanbanClient tests
- **`test_marcus_integration.py`** ✅ - Marcus MCP server integration tests

### Performance Tests (`tests/performance/`)
- Benchmark critical operations
- Memory usage profiling
- Response time measurements
- Load testing for concurrent operations

### Diagnostic Tests (`tests/diagnostics/`)
Quick scripts for troubleshooting:
- **`test_board_id.py`** - Verifies board_id and project_id configuration
- **`test_simple_client.py`** - Tests SimpleMCPKanbanClient basic operations
- **`test_direct_mcp.py`** - Tests raw MCP connection
- **`test_workspace_integration.py`** - Tests workspace security features

## Writing Tests

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<specific_behavior>`

Example:
```python
# test_task_manager.py
class TestTaskManager:
    def test_create_task_with_valid_data(self):
        """Test that task creation works with valid input data."""
        pass
```

### Using Fixtures

Common fixtures are defined in `conftest.py` files:

```python
# conftest.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_kanban_client():
    """Provides a mock kanban client for testing."""
    client = AsyncMock()
    client.get_tasks = AsyncMock(return_value=[])
    return client
```

### Async Tests

Due to pytest-asyncio introspection issues, we use `pytest-anyio`:

```python
import pytest

@pytest.mark.anyio
@pytest.mark.parametrize("anyio_backend", ["asyncio"])
async def test_async_operation():
    """Test asynchronous operations."""
    result = await some_async_function()
    assert result == expected_value
```

### Test Markers

Available pytest markers (defined in `pytest.ini`):

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Tests that take > 1 second
- `@pytest.mark.kanban` - Tests requiring kanban server
- `@pytest.mark.visualization` - Visualization tests
- `@pytest.mark.asyncio` - Async tests (use with caution)

## Coverage Requirements

- Minimum coverage: **80%**
- Coverage reports: `htmlcov/index.html` after running with `--cov`
- Critical paths must have 100% coverage

### Checking Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Check coverage meets threshold
coverage report --fail-under=80
```

## Test Requirements

### For Unit Tests
- No external requirements
- Mock objects used for external dependencies

### For Integration Tests
- kanban-mcp server must be accessible
- Planka must be running (if using Planka provider)
- Valid `config_marcus.json` with board_id and project_id

### For Diagnostic Tests
- Same as integration tests
- Designed to help troubleshoot when things aren't working

## Best Practices

1. **Keep Tests Fast**: Unit tests should complete in milliseconds
2. **Test One Thing**: Each test should verify a single behavior
3. **Use Descriptive Names**: Test names should explain what they test
4. **Arrange-Act-Assert**: Follow the AAA pattern
5. **Mock External Dependencies**: Unit tests should not make network calls
6. **Use Fixtures**: Reuse common test setup via fixtures
7. **Test Edge Cases**: Include tests for error conditions and boundaries
8. **Document Complex Tests**: Add docstrings explaining complex test scenarios

## Common Test Utilities

### Base Test Classes

```python
from tests.utils.base import BaseTestCase

class TestMyComponent(BaseTestCase):
    """Inherits common test utilities."""
    
    def test_something(self):
        # Use inherited helper methods
        task = self.create_sample_task()
        self.assert_task_valid(task)
```

### Test Data Factories

```python
from tests.fixtures.factories import TaskFactory, AgentFactory

def test_task_assignment():
    task = TaskFactory.create(priority="high")
    agent = AgentFactory.create(skills=["python"])
    # ... test logic
```

## Troubleshooting

### Common Issues

1. **"OSError: could not get source code"**
   - Run tests with `-p no:asyncio` flag
   - Use `pytest-anyio` for async tests

2. **"RuntimeWarning: coroutine was never awaited"**
   - Ensure async fixtures use proper decorators
   - Check that test methods are properly marked as async

3. **Import Errors**
   - Ensure PYTHONPATH includes project root
   - Check that `__init__.py` files exist in all packages

### Debug Mode

```bash
# Run tests with debugging output
pytest -vvs --log-cli-level=DEBUG

# Run specific test with pdb
pytest -k test_name --pdb

# Show local variables on failure
pytest -l
```

### Running Diagnostic Scripts

```bash
# Quick config check
python tests/diagnostics/test_board_id.py

# Test client functionality
python tests/diagnostics/test_simple_client.py

# Debug connection issues
python tests/diagnostics/test_direct_mcp.py
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- All pull requests
- Nightly scheduled runs

See `.github/workflows/tests.yml` for CI configuration.

## Contributing

When adding new tests:
1. Place them in the appropriate directory
2. Use existing fixtures when possible
3. Ensure tests pass locally before pushing
4. Maintain or improve code coverage
5. Update this documentation if adding new test categories

For more information, see the [Contributing Guide](../docs/developer-guide/contributing.md).