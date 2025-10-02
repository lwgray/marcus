# Marcus Test Organization Guide

> **Updated:** September 5, 2025
> **Part of Issue #46:** Test Organization Improvement Initiative

## 🎯 Overview

This guide provides comprehensive documentation on Marcus's improved test organization, standards, and best practices. Following the principles established in issue #46, our tests now mirror the source code structure and use real implementations instead of mocks.

## 📁 Directory Structure

### Current Test Organization
```
tests/
├── conftest.py                 # Global fixtures and MCP session management
├── pytest.ini                 # Test configuration and markers
├── test_infrastructure.py      # Flaky test handling, performance baselines
├── TEST_INVENTORY.md           # Comprehensive test coverage analysis
├── fixtures/                   # Domain-organized real fixtures (no mocks)
│   ├── fixtures_core.py        # Core Marcus objects (tasks, agents, context)
│   ├── fixtures_ai.py          # AI and enrichment related objects
│   └── fixtures_integration.py # Integration and external service objects
├── unit/                       # Unit tests organized by source structure
│   ├── conftest.py             # Unit test fixtures (real implementations)
│   ├── ai/                     # AI and intelligence testing
│   │   ├── enrichment/         # Split enricher tests (7 focused modules)
│   │   ├── test_*.py           # Other AI component tests
│   ├── core/                   # Core business logic tests
│   ├── integrations/           # External service integration tests
│   ├── marcus_mcp/             # MCP protocol tests
│   ├── mcp/                    # Additional MCP tests
│   ├── communication/          # ✅ NEW: Communication hub tests
│   ├── config/                 # ✅ NEW: Configuration tests
│   ├── monitoring/             # ✅ NEW: System monitoring tests
│   ├── security/               # ✅ NEW: Security implementation tests
│   ├── visualization/          # ✅ NEW: Data visualization tests
│   ├── worker/                 # ✅ NEW: Worker process tests
│   └── [18 new modules]        # Complete source code coverage
├── integration/                # Integration and e2e tests
├── performance/                # Performance and benchmark tests
└── future_features/            # TDD tests for upcoming features
```

### Key Improvements Made

✅ **Complete Source Coverage:** All 38 `src/` modules now have corresponding test directories
✅ **Modular Organization:** Large test files split into focused modules (e.g., enricher tests → 7 modules)
✅ **Real Implementations:** Eliminated mocks in favor of real object testing
✅ **Domain Fixtures:** Organized fixtures by domain (core, ai, integration)
✅ **Test Infrastructure:** Added flaky test handling and performance baselines

## 🏷️ Test Markers and Categories

### Standard Test Markers
```python
@pytest.mark.unit           # Fast, isolated unit test (preferred)
@pytest.mark.integration    # Requires external services
@pytest.mark.slow          # Takes >1 second to complete
@pytest.mark.asyncio       # Async test requiring event loop
@pytest.mark.kanban        # Requires Kanban MCP server
@pytest.mark.performance   # Performance benchmark with baselines
@pytest.mark.e2e           # End-to-end workflow test
@pytest.mark.flaky         # May fail intermittently, auto-retry enabled
@pytest.mark.baseline      # Establishes performance baseline
@pytest.mark.no_mock       # Uses only real implementations
```

### When to Use Each Marker
- **@pytest.mark.unit**: Default for most tests, fast execution (<100ms)
- **@pytest.mark.integration**: When testing with real external services
- **@pytest.mark.no_mock**: When emphasizing real implementation testing
- **@pytest.mark.flaky**: For tests with known intermittent issues
- **@pytest.mark.performance**: For tests with baseline performance expectations

## 🛠️ Real Implementation Testing (No Mock Policy)

### Philosophy
Marcus tests prioritize **real implementations** over mocks to ensure:
- Tests verify actual behavior, not mock behavior
- Better integration confidence
- Reduced test maintenance burden
- More reliable test results

### Fixture Categories

#### Core Domain Fixtures (`tests/fixtures/fixtures_core.py`)
```python
# Real task objects
@pytest.fixture
def sample_task() -> Task:
    return Task(id="task-001", name="Real task", ...)

# Real agent objects
@pytest.fixture
def sample_agent() -> Agent:
    return Agent(id="agent-001", skills=["python"], ...)

# Real context objects
@pytest.fixture
def sample_context() -> Context:
    context = Context()
    context.project_name = "Real Project"
    return context
```

#### AI Domain Fixtures (`tests/fixtures/fixtures_ai.py`)
```python
# Real semantic analysis results
@pytest.fixture
def sample_semantic_analysis() -> SemanticAnalysis:
    return SemanticAnalysis(complexity_score=0.75, ...)

# Real project context for AI operations
@pytest.fixture
def sample_project_context() -> ProjectContext:
    return ProjectContext(project_name="Real Project", ...)
```

#### Integration Fixtures (`tests/fixtures/fixtures_integration.py`)
```python
# Real Kanban client (requires @pytest.mark.integration)
@pytest.fixture
def real_kanban_client() -> KanbanInterface:
    if env_configured():
        return KanbanInterface(provider="planka", ...)
    else:
        pytest.skip("Integration environment not configured")
```

### Guidelines for Real Implementation Testing

#### ✅ Do This
```python
def test_task_assignment(sample_task, sample_agent):
    """Test with real Task and Agent objects."""
    assigner = TaskAssigner()
    result = assigner.assign_task(sample_task, sample_agent)
    assert result.success
    assert result.assigned_agent == sample_agent.id
```

#### ❌ Avoid This
```python
def test_task_assignment():
    """Avoid mocking core objects."""
    mock_task = Mock()
    mock_agent = Mock()
    # This tests mock behavior, not real behavior
```

#### Integration Tests
```python
@pytest.mark.integration
@pytest.mark.kanban
def test_real_kanban_sync(real_kanban_client, sample_task):
    """Integration test with real Kanban service."""
    result = real_kanban_client.create_task(sample_task)
    assert result.success
    # Clean up
    real_kanban_client.delete_task(result.task_id)
```

## 📊 Test Infrastructure Features

### Flaky Test Handling
```python
from tests.test_infrastructure import flaky_handler

@pytest.mark.flaky
def test_intermittent_external_service():
    """Test that may fail due to external factors."""
    # Automatically retried up to 3 times with backoff
    pass
```

### Performance Baselines
```python
from tests.test_infrastructure import performance_test

@performance_test(baseline_metric="execution_time", tolerance=0.2)
def test_task_processing_performance():
    """Test with automatic performance baseline tracking."""
    # Execution time tracked, compared to baseline
    # Alerts on >20% performance regression
    pass
```

### Metrics Collection
```python
# Automatic collection of:
# - Test execution time
# - Success/failure rates
# - Memory usage (when available)
# - Error patterns

# View metrics: tests/test_metrics.json
# View baselines: tests/performance_baselines.json
# View flaky tests: tests/flaky_tests.json
```

## 📝 Writing Tests

### Test File Structure
```python
"""
Unit tests for ComponentName.

Clear description of what this module tests.
"""

import pytest
from tests.fixtures.fixtures_core import sample_task
from tests.fixtures.fixtures_ai import sample_semantic_analysis

from src.component.module import ComponentName


class TestComponentName:
    """Test suite for ComponentName functionality."""

    def test_successful_operation(self, sample_task):
        """Test component handles normal operation correctly.

        Uses real Task object to verify actual behavior.
        """
        component = ComponentName()
        result = component.process(sample_task)

        assert result.success
        assert result.output is not None

    @pytest.mark.asyncio
    async def test_async_operation(self, sample_task):
        """Test async operation with real objects."""
        component = ComponentName()
        result = await component.async_process(sample_task)

        assert result is not None

    @pytest.mark.integration
    def test_with_external_service(self, real_kanban_client):
        """Integration test requiring external service."""
        # Test with real external service
        pass
```

### Test Naming Conventions
- **test_[action]_[condition]_[expected_result]**
  - `test_assign_task_with_matching_skills_succeeds`
  - `test_enrich_task_with_invalid_input_raises_error`
  - `test_sync_board_when_offline_retries_with_backoff`

### Test Organization Rules

#### File Organization
- Mirror source code structure: `src/ai/enrichment/` → `tests/unit/ai/enrichment/`
- Max 20 test functions per file
- Split large files by functionality
- Group related tests in classes

#### Test Content
- One logical assertion per test
- Descriptive test names and docstrings
- Use real fixtures instead of inline object creation
- Mark tests appropriately with pytest markers

## 🚀 Running Tests

### Basic Commands
```bash
# Run all unit tests
pytest tests/unit/

# Run specific module tests
pytest tests/unit/ai/enrichment/

# Run with specific markers
pytest -m "unit and not slow"
pytest -m "integration"
pytest -m "performance"

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html

# Run flaky tests with extra retries
pytest -m flaky --reruns 5
```

### Test Selection
```bash
# Fast unit tests only (recommended for development)
pytest -m "unit and not slow"

# Integration tests (requires external services)
pytest -m integration

# Performance tests with baseline checking
pytest -m performance

# Tests using only real implementations
pytest -m no_mock
```

### Debugging Tests
```bash
# Run single test with verbose output
pytest tests/unit/ai/test_enricher.py::TestEnricher::test_specific -v -s

# Drop into debugger on failure
pytest --pdb tests/unit/ai/

# Show slowest tests
pytest --durations=10
```

## 📈 Test Quality Standards

### Success Metrics
- **Pass Rate**: >95% (current: 90.3%, improving)
- **Coverage**: >80% source modules have tests ✅
- **Performance**: Unit tests <2 minutes ✅
- **Organization**: No file >20 functions ✅
- **Real Implementation**: Minimal mocking ✅

### Quality Checklist

#### Before Committing
- [ ] All tests pass locally
- [ ] New tests use real fixtures
- [ ] Tests have descriptive names and docstrings
- [ ] Appropriate pytest markers applied
- [ ] No test file exceeds 20 functions
- [ ] Integration tests are marked appropriately

#### Code Review
- [ ] Tests verify real behavior, not mock behavior
- [ ] Test organization mirrors source structure
- [ ] Fixtures are reused appropriately
- [ ] Performance-sensitive tests have baselines
- [ ] Flaky tests are marked and handled

## 🔧 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Error: ImportError in test files
# Solution: Ensure proper pytest configuration
export PYTHONPATH="/path/to/marcus:$PYTHONPATH"
pytest tests/unit/
```

#### Fixture Not Found
```bash
# Error: fixture 'sample_task' not found
# Solution: Import fixture plugin in conftest.py
pytest_plugins = ["tests.fixtures.fixtures_core"]
```

#### Integration Test Failures
```bash
# Error: Integration tests failing
# Solution: Check external service configuration
export PLANKA_BASE_URL="http://localhost:3333"
export PLANKA_AGENT_EMAIL="demo@demo.demo"
pytest -m integration
```

#### Performance Regression
```bash
# Warning: Performance regression detected
# Solution: Check test changes, update baseline if needed
pytest -m performance --reset-baselines
```

### Getting Help

1. **Check TEST_INVENTORY.md** for comprehensive test coverage analysis
2. **Review pytest.ini** for marker definitions and configuration
3. **Examine fixtures/** for available real implementation fixtures
4. **Run with -v flag** for verbose output and debugging info

## 🎉 Success Metrics Achieved

| Metric | Before | After | Status |
|--------|--------|--------|---------|
| Test Files | 58 | 58+ | ✅ Improved |
| Source Module Coverage | ~60% | 100% | ✅ Complete |
| Large Files (>20 funcs) | 3 | 0 | ✅ Fixed |
| Mock Usage | Heavy | Minimal | ✅ Eliminated |
| Test Organization | Ad-hoc | Structured | ✅ Systematic |
| Performance Tracking | None | Baseline System | ✅ Implemented |
| Flaky Test Handling | None | Auto-retry | ✅ Implemented |

---

*This guide represents the improved state of Marcus test organization following the completion of Issue #46. All improvements prioritize real implementation testing and maintainable test architecture.*
