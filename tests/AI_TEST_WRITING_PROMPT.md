# AI Assistant Test Writing Prompt

## System Prompt for Writing Tests in Marcus

When asked to write tests for the Marcus project, follow these guidelines:

### Test Writing Process

1. **First, determine the test type:**
   - Ask: "Does this test require external services (database, API, network, file system)?"
   - If NO → Write a unit test with all dependencies mocked
   - If YES → Determine if it's a future feature (TDD) or integration test

2. **Choose the correct location:**
   ```
   Unit Tests (no external dependencies):
   - AI/ML logic → tests/unit/ai/test_*.py
   - Core models/logic → tests/unit/core/test_*.py
   - MCP protocol → tests/unit/mcp/test_*.py
   - UI → tests/unit/ui/test_*.py

   Integration Tests (require services):
   - End-to-end workflows → tests/integration/e2e/test_*.py
   - API testing → tests/integration/api/test_*.py
   - External services → tests/integration/external/test_*.py
   - Diagnostics → tests/integration/diagnostics/test_*.py

   Other:
   - Performance tests → tests/performance/test_*.py
   - Future/TDD features → tests/future_features/*/test_*.py
   ```

3. **Follow the test structure:**
   ```python
   """
   [Unit/Integration] tests for [Component Name]

   Tests [specific functionality] with [mocked dependencies/real services].
   """

   import pytest
   from unittest.mock import Mock, AsyncMock, patch

   class Test[ComponentName]:
       """Test suite for [ComponentName]"""

       @pytest.fixture
       def [mock_dependency](self):
           """Mock [dependency name]"""
           # Create mocks for unit tests

       @pytest.fixture
       def [component](self, [dependencies]):
           """Create instance with [mocked/real] dependencies"""
           # Setup component

       def test_[specific_behavior](self, [fixtures]):
           """Test [what you're testing]"""
           # Arrange
           # Act
           # Assert
   ```

4. **Apply these principles:**
   - **Unit tests**: Mock ALL external dependencies, should run in < 100ms
   - **Integration tests**: Use real services, mark with `@pytest.mark.integration`
   - **Async tests**: Use `@pytest.mark.asyncio` or `pytest-anyio`
   - **Test naming**: `test_[what]_[condition]_[expected_result]`
   - **One assertion focus**: Each test should verify one specific behavior

5. **Use appropriate fixtures:**
   - Create fixtures for repeated setup
   - Use `mock_*` prefix for mocked dependencies
   - Scope fixtures appropriately (`function`, `class`, `module`, `session`)
   - Clean up resources in fixture teardown

6. **Mock correctly for unit tests:**
   ```python
   # Mock at the usage point, not definition
   @patch('src.module.where_used.ExternalService')
   def test_something(self, mock_service):
       mock_service.return_value.method.return_value = "expected"

   # Or use fixture
   @pytest.fixture
   def mock_kanban_client(self):
       with patch('src.marcus_mcp.server.KanbanFactory') as mock:
           client = Mock()
           mock.create.return_value = client
           yield client
   ```

7. **Test categories to consider:**
   - **Happy path**: Normal expected behavior
   - **Edge cases**: Boundaries, empty inputs, maximum values
   - **Error cases**: Invalid inputs, service failures, timeouts
   - **State changes**: Verify side effects occurred
   - **Async behavior**: Concurrent operations, race conditions

8. **Documentation requirements:**
   - Docstring explaining what the test verifies
   - Comments for complex setup or assertions
   - Mark tests appropriately (`@pytest.mark.unit`, `@pytest.mark.slow`, etc.)

9. **Coverage goals:**
   - Aim for 80% code coverage minimum
   - 100% coverage for critical paths
   - Test both success and failure scenarios
   - Don't test implementation details, test behavior

10. **When NOT to write unit tests:**
    - Testing framework functionality
    - Testing language features
    - Trivial getters/setters with no logic
    - Configuration loading (use integration tests)

### Example Test Creation Response:

"I'll write a unit test for the TaskAssignmentManager. Since this is testing business logic without external dependencies, I'll place it in `tests/unit/core/test_task_assignment_manager.py` and mock all dependencies.

The test will verify that tasks are assigned based on priority, with all database and API calls mocked. Here's the test:

[test code following the structure above]

This test is placed in the unit tests because:
- It doesn't require external services (database is mocked)
- It tests a single component in isolation
- It will run quickly (< 100ms)
- All dependencies are injected and mocked"

### Decision Tree Summary:
1. External services needed? → NO = Unit test, YES = Continue
2. Testing future features? → YES = future_features/, NO = Continue
3. What type of integration? → Choose appropriate subfolder
4. Write test following the structure and principles above

Always explain your test placement decision and what the test verifies.
