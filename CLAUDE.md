FILE_MANAGEMENT:
  - Don't ever version files...just change the original file.  No "_fixed", "_v2", "_patched", etc.
  - When modifying files, always overwrite the original file. Never create new versions with suffixes like _fixed, _v2, _new, _updated, _patched, or similar naming patterns.

  COMMUNICATION_GUIDELINES:
  - Always tell me what you are going to do and why

  CODE_DOCUMENTATION:
  - Always document code with numpy-style docstrings

  DEVELOPMENT_BEST_PRACTICES:
  - Always use TDD when developing - no exceptions
  - Always Make sure all tests pass and you have 80% coverage

  DOCUMENTATION_PLACEMENT_RULES:
  When creating or updating documentation:
  1. Determine audience FIRST:
     - End users → /docs/user-guide/
     - Developers → /docs/developer-guide/
     - DevOps/Operations → /docs/operations-guide/
     - Internal only → /docs/archive/

  2. Choose correct subdirectory:
     - Step-by-step guides → how-to/
     - Concepts/explanations → concepts/
     - Reference/config → reference/
     - Technical architecture → developer-guide/sphinx/

  3. Follow patterns:
     - Check if docs already exist (update rather than duplicate)
     - Use kebab-case filenames: feature-name.md
     - Be descriptive: setup-github-integration.md not github.md
     - Match style of existing docs in that section

  4. Examples:
     - "How to use X" → /docs/user-guide/how-to/use-x.md
     - "X API Reference" → /docs/developer-guide/x-api.md
     - "Deploy on Y" → /docs/operations-guide/setup/deploy-y.md
     - "X Architecture" → /docs/developer-guide/sphinx/source/developer/x-architecture.md

  Each directory has a README.md explaining what belongs there. When in doubt, check /docs/README.md for structure.

  TEST_WRITING_INSTRUCTIONS:
  When writing tests for Marcus, follow this systematic approach:

  1. Test Placement Decision:
     ```
     Does the test require external services (DB, API, network, files)?
     → NO: Write a UNIT test in tests/unit/
     → YES: Is this testing unimplemented/future features (TDD)?
            → YES: Place in tests/future_features/
            → NO: Write INTEGRATION test in tests/integration/
     ```

  2. Unit Test Placement:
     - AI/ML logic → tests/unit/ai/test_*.py
     - Core models/logic → tests/unit/core/test_*.py
     - MCP protocol → tests/unit/mcp/test_*.py
     - UI/Visualization → tests/unit/visualization/test_*.py

  3. Integration Test Placement:
     - End-to-end workflow → tests/integration/e2e/test_*.py
     - API endpoints → tests/integration/api/test_*.py
     - External services → tests/integration/external/test_*.py
     - Debugging/diagnostics → tests/integration/diagnostics/test_*.py
     - Performance → tests/performance/test_*.py

  4. Test Writing Rules:
     ALWAYS:
     - Mock ALL external dependencies in unit tests
     - Use descriptive test names: test_[what]_[when]_[expected]
     - Include docstrings explaining what each test verifies
     - Follow Arrange-Act-Assert pattern
     - One logical assertion per test
     - Unit tests must run in < 100ms

     NEVER:
     - Use real services in unit tests
     - Test implementation details
     - Create test files in root tests/ directory
     - Mix unit and integration tests
     - Leave hardcoded values - use fixtures

  5. Test Structure:
     ```python
     """
     [Unit/Integration] tests for [ComponentName]
     """
     import pytest
     from unittest.mock import Mock, AsyncMock, patch

     class TestComponentName:
         """Test suite for ComponentName"""

         @pytest.fixture
         def mock_dependency(self):
             """Create mock for dependency"""
             mock = Mock()
             mock.method = AsyncMock(return_value="expected")
             return mock

         def test_successful_operation(self, component):
             """Test component handles normal operation"""
             # Arrange
             # Act
             # Assert
     ```

  6. Test Markers:
     - @pytest.mark.unit - Fast, isolated unit test
     - @pytest.mark.integration - Requires external services
     - @pytest.mark.asyncio - Async test
     - @pytest.mark.slow - Takes > 1 second
     - @pytest.mark.kanban - Requires Kanban server

  7. Response Format:
     - State test location and reasoning
     - Explain test strategy and what will be tested
     - Show complete test file with all imports
     - Explain key decisions (mocking strategy, assertions)

  ERROR_HANDLING_FRAMEWORK:
  Use Marcus Error Framework for ALL user/agent-facing errors. Use regular Python exceptions only for internal programming errors.

  WHEN TO USE MARCUS ERRORS:
  ✅ External service calls (Kanban, AI providers, APIs)
  ✅ Agent task operations (assignment, execution, progress)
  ✅ Configuration issues (missing credentials, invalid config)
  ✅ Security violations (unauthorized access, permission denied)
  ✅ Resource problems (memory exhaustion, database failures)
  ✅ Business logic violations (workflow errors, validation failures)

  WHEN TO USE REGULAR EXCEPTIONS:
  ✅ Programming errors (ValueError, TypeError for internal validation)
  ✅ Library-specific exceptions (let them bubble up)
  ✅ Internal logic errors (KeyError for missing dict keys)

  ERROR CREATION PATTERNS:
  ```python
  # External service errors
  from src.core.error_framework import KanbanIntegrationError, ErrorContext

  try:
      await kanban_client.create_task(data)
  except httpx.TimeoutException:
      raise KanbanIntegrationError(
          board_name="project_board",
          operation="create_task",
          context=ErrorContext(
              operation="task_creation",
              agent_id=agent_id,
              task_id=task_id
          )
      )

  # Use error context manager for automatic context injection
  from src.core.error_framework import error_context

  with error_context("sync_tasks", agent_id=agent_id):
      await sync_with_kanban()  # Errors automatically get context

  # Configuration errors
  from src.core.error_framework import MissingCredentialsError

  if not os.getenv('API_KEY'):
      raise MissingCredentialsError(
          service_name="kanban",
          credential_type="API key"
      )
  ```

  RETRY AND RESILIENCE PATTERNS:
  ```python
  # Add retries for network operations
  from src.core.error_strategies import with_retry, RetryConfig

  @with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
  async def call_external_service():
      return await service.call()

  # Add circuit breakers for external dependencies
  from src.core.error_strategies import with_circuit_breaker

  @with_circuit_breaker("kanban_service")
  async def sync_with_kanban():
      return await kanban.sync()

  # Add fallbacks for critical operations
  from src.core.error_strategies import with_fallback

  async def use_cached_data():
      return load_from_cache()

  @with_fallback(use_cached_data)
  async def get_live_data():
      return await fetch_from_api()
  ```

  ERROR RESPONSE PATTERNS:
  ```python
  # For MCP tool responses
  from src.core.error_responses import handle_mcp_tool_error

  async def mcp_tool_function(arguments):
      try:
          result = await operation(arguments)
          return {"success": True, "result": result}
      except Exception as e:
          return handle_mcp_tool_error(e, "tool_name", arguments)

  # For API responses
  from src.core.error_responses import create_error_response, ResponseFormat

  try:
      result = await api_operation()
      return {"success": True, "data": result}
  except Exception as e:
      return create_error_response(e, ResponseFormat.JSON_API)
  ```

  ERROR MONITORING:
  ```python
  # Record errors for monitoring and pattern detection
  from src.core.error_monitoring import record_error_for_monitoring

  try:
      await critical_operation()
  except MarcusBaseError as e:
      record_error_for_monitoring(e)
      raise
  ```

  QUICK DECISION TREE:
  - External service call → Use Marcus Integration Error + Circuit Breaker + Retry
  - Agent operation → Use Marcus Business Logic Error + Context
  - Configuration issue → Use Marcus Configuration Error (no retry)
  - Security violation → Use Marcus Security Error (no retry, alert)
  - Programming error → Use regular Python exception (ValueError, TypeError)
  - Library error → Let bubble up, convert to Marcus if user-facing

  NEVER:
  - Use generic Exception() for anything user/agent-facing
  - Retry authentication failures or validation errors
  - Skip error context for agent operations
  - Use regular exceptions for external service failures

  ITERATIVE_TESTING_APPROACH:
  1. Write ONE simple test first to understand actual behavior
  2. Run it and fix any issues before expanding
  3. Use findings to inform remaining test design
  4. Don't assume error message formats - discover them

  DISCOVERY_OVER_ASSUMPTION:
  - Run simple tests to discover actual error behavior
  - Check inheritance chains and constructor patterns
  - Verify message formats and context structure
  - Test framework quirks before building complex scenarios
