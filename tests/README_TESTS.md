# PM Agent Test Suite

This directory contains comprehensive tests for the PM Agent system, including both unit and integration tests.

## Test Structure

```
tests/
├── unit/                      # Unit tests (no external dependencies)
│   ├── test_kanban_client_unit.py
│   ├── test_models.py
│   ├── test_settings.py
│   └── test_ai_analysis_engine.py
├── integration/               # Integration tests (require external services)
│   ├── test_mcp_kanban_client.py
│   ├── test_kanban_mcp_all_commands.py
│   ├── test_pm_agent_integration.py
│   └── test_real_kanban_integration.py
├── conftest.py               # Shared pytest fixtures
└── README_TESTS.md           # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with our test runner
python run_tests.py

# Run only unit tests (fast, no external dependencies)
python run_tests.py --type unit

# Run integration tests
python run_tests.py --type integration

# Run with coverage
python run_tests.py --coverage
```

### Detailed Options

```bash
# Run specific test file
pytest tests/unit/test_kanban_client_unit.py

# Run specific test class
pytest tests/integration/test_mcp_kanban_client.py::TestMCPKanbanClientIntegration

# Run specific test method
pytest tests/integration/test_mcp_kanban_client.py::TestMCPKanbanClientIntegration::test_connection_context_manager

# Run with verbose output
pytest -vv

# Stop on first failure
pytest -x

# Run tests matching a pattern
pytest -k "test_create"

# Run only marked tests
pytest -m unit
pytest -m integration
pytest -m kanban
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- No external dependencies
- Test individual components in isolation
- Use mocks for external services

### Integration Tests (`@pytest.mark.integration`)
- Test component interactions
- May require external services
- Test real workflows

### Kanban Tests (`@pytest.mark.kanban`)
- Require Kanban MCP server running
- Test actual Kanban operations
- Create/delete real resources

## Prerequisites

### For All Tests
```bash
pip install -r requirements.txt
```

### For Integration Tests
1. Planka running at http://localhost:3333
2. Kanban MCP server available
3. Valid test project (Task Master Test)

## Writing New Tests

### Unit Test Example
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.unit
class TestMyComponent:
    def test_something(self):
        # Arrange
        component = MyComponent()
        
        # Act
        result = component.do_something()
        
        # Assert
        assert result == expected_value
```

### Integration Test Example
```python
import pytest

@pytest.mark.integration
@pytest.mark.kanban
class TestKanbanIntegration:
    @pytest.mark.asyncio
    async def test_real_operation(self, mcp_session, test_board):
        # Use fixtures for setup
        result = await mcp_session.call_tool("tool_name", {...})
        
        # Assert real results
        assert result is not None
```

## Fixtures

Key fixtures provided in `conftest.py`:

- `mcp_session`: Connected MCP session to Kanban server
- `test_project_id`: The test project ID
- `test_board`: Creates a test board (with cleanup)
- `test_board_name`: Generates unique board names
- `mock_task_data`: Sample task data

## Coverage

To generate coverage reports:

```bash
# Terminal report
python run_tests.py --coverage

# HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## CI/CD Integration

For GitHub Actions or other CI systems:

```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=src --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests Hanging
- Check if Kanban MCP server is responsive
- Ensure Planka is running
- Check for async timeout issues

### Import Errors
- Ensure you're in the project root
- Check PYTHONPATH includes src/

### Connection Errors
- Verify Node.js path is correct
- Check Planka credentials
- Ensure kanban-mcp is at expected path

## Best Practices

1. **Isolation**: Unit tests should not depend on external services
2. **Cleanup**: Integration tests must clean up created resources
3. **Naming**: Use descriptive test names that explain what's being tested
4. **Markers**: Use appropriate pytest markers for test organization
5. **Fixtures**: Reuse fixtures for common setup/teardown
6. **Async**: Use `@pytest.mark.asyncio` for async tests
7. **Assertions**: Use specific assertions with helpful messages