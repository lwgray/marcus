# Claude Test Writing Instructions for Marcus

## System Instructions for Test Creation

When writing tests for the Marcus project, follow this systematic approach:

### 1. Test Placement Decision

```
DECISION FLOW:
1. Does the test require external services (DB, API, network, files)?
   → NO: Write a UNIT test in tests/unit/
   → YES: Continue to step 2

2. Is this testing unimplemented/future features (TDD)?
   → YES: Place in tests/future_features/
   → NO: Write INTEGRATION test in tests/integration/

3. For UNIT tests, which component?
   → AI/ML logic: tests/unit/ai/
   → Core models/logic: tests/unit/core/
   → MCP protocol: tests/unit/mcp/
   → UI/Visualization: tests/unit/visualization/

4. For INTEGRATION tests, what type?
   → End-to-end workflow: tests/integration/e2e/
   → API endpoints: tests/integration/api/
   → External services: tests/integration/external/
   → Debugging/diagnostics: tests/integration/diagnostics/
   → Performance: tests/performance/
```

### 2. Test Writing Rules

**ALWAYS:**
- Mock ALL external dependencies in unit tests
- Use descriptive test names: `test_[what]_[when]_[expected]`
- Include docstrings explaining what each test verifies
- Follow Arrange-Act-Assert pattern
- One logical assertion per test
- Unit tests must run in < 100ms

**NEVER:**
- Use real services in unit tests
- Test implementation details
- Create test files in the root tests/ directory
- Mix unit and integration tests in the same file
- Leave hardcoded values - use fixtures

### 3. Test Structure Template

```python
"""
[Unit/Integration] tests for [ComponentName]
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Import what you're testing
from src.module.component import ComponentToTest


class TestComponentName:
    """Test suite for ComponentName"""
    
    @pytest.fixture
    def mock_dependency(self):
        """Create mock for [dependency]"""
        mock = Mock()
        mock.some_method.return_value = "expected_value"
        return mock
    
    @pytest.fixture
    def component(self, mock_dependency):
        """Create component instance with mocked dependencies"""
        return ComponentToTest(dependency=mock_dependency)
    
    def test_successful_operation(self, component, mock_dependency):
        """Test component handles normal operation correctly"""
        # Arrange
        input_data = {"key": "value"}
        expected_result = {"status": "success"}
        
        # Act
        result = component.process(input_data)
        
        # Assert
        assert result == expected_result
        mock_dependency.some_method.assert_called_once_with(input_data)
    
    def test_handles_invalid_input(self, component):
        """Test component raises appropriate error for invalid input"""
        # Arrange
        invalid_input = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Input cannot be None"):
            component.process(invalid_input)
    
    @pytest.mark.asyncio
    async def test_async_operation(self, component):
        """Test async method works correctly"""
        # Arrange
        expected = "async_result"
        
        # Act
        result = await component.async_method()
        
        # Assert
        assert result == expected
```

### 4. Mocking Guidelines

**For Unit Tests:**
```python
# Mock at point of use, not at import
@patch('src.module.ComponentClass.external_method')
def test_something(self, mock_method):
    mock_method.return_value = "mocked_response"

# Or use fixtures for reusable mocks
@pytest.fixture
def mock_kanban_client(self):
    """Mock the Kanban client"""
    client = Mock()
    client.get_all_tasks = AsyncMock(return_value=[])
    client.assign_task = AsyncMock(return_value={"success": True})
    return client

# Mock async methods
mock.some_async_method = AsyncMock(return_value="result")

# Mock properties
type(mock).some_property = PropertyMock(return_value="value")
```

### 5. Common Test Scenarios

**API Endpoint Test (Unit):**
- Mock all database/external calls
- Test request validation
- Test response format
- Test error handling
- Place in: `tests/unit/api/`

**Service Integration Test:**
- Use real service connections
- Mark with `@pytest.mark.integration`
- May be slower
- Place in: `tests/integration/`

**Model Test (Unit):**
- Test data validation
- Test model methods
- Test serialization
- Place in: `tests/unit/core/`

**Async Worker Test:**
- Use `pytest.mark.asyncio`
- Mock async dependencies with `AsyncMock`
- Test concurrent scenarios
- Place in: `tests/unit/` (if mocked) or `tests/integration/` (if real)

### 6. Test Markers to Use

```python
@pytest.mark.unit          # Fast, isolated unit test
@pytest.mark.integration   # Requires external services
@pytest.mark.asyncio       # Async test
@pytest.mark.slow          # Takes > 1 second
@pytest.mark.kanban        # Requires Kanban server
@pytest.mark.skip("Reason") # Temporarily skip
@pytest.mark.xfail         # Expected to fail
```

### 7. Response Format

When creating tests, always:

1. **State the test location:**
   "I'll create this test in `tests/unit/core/test_feature.py` because..."

2. **Explain the test strategy:**
   "This will be a unit test that mocks the database and tests..."

3. **List what will be tested:**
   - Success cases
   - Error cases  
   - Edge cases

4. **Show the complete test file:**
   Including imports, fixtures, and all test methods

5. **Explain key decisions:**
   Why certain mocks were used, why specific assertions were chosen

### Example Response:

"I'll create a unit test for the new TaskPrioritizer class. Since this tests business logic without external dependencies, it belongs in `tests/unit/core/test_task_prioritizer.py`.

This test will verify:
- Tasks are sorted by priority correctly
- Urgent tasks always come first
- Equal priority tasks maintain order
- Empty list handling

Here's the complete test:

```python
[full test code]
```

Key decisions:
- Mocked the database since we're testing logic, not persistence
- Used parametrize for multiple priority scenarios
- Separated success and edge cases into different test methods"

### Remember:
- Unit tests = Fast, isolated, mocked
- Integration tests = Real services, slower, marked
- Always explain placement and approach
- Follow existing patterns in the codebase