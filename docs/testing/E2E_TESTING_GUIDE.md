# Marcus End-to-End Testing Guide

Complete guide to testing Marcus from development through deployment.

## Overview

Marcus uses a **3-tier testing strategy** to ensure quality at every level:

1. **Smoke Tests** - Fast sanity checks (<30s)
2. **Integration Tests** - Workflow validation (2-5min)
3. **Build Validation** - Full quality checks (5-10min)

## Quick Start

```bash
# Run smoke tests (fastest)
pytest tests/smoke/ -v

# Run all unit tests
pytest tests/unit/ -v

# Run E2E integration tests
pytest tests/integration/e2e/ -v

# Full build validation
./scripts/validate_build.sh

# Quick validation (skip slow tests)
./scripts/validate_build.sh --quick
```

## Testing Tiers

### Tier 1: Smoke Tests

**Location:** `tests/smoke/`

**Purpose:** Catch obvious breakage before running expensive tests

**Duration:** <30 seconds

**What's Tested:**
- Server initialization
- Core MCP tools registered
- Basic connectivity (ping)
- Agent registration works
- Kanban client responsive
- AI engine available

**When to Run:**
- After making changes to core infrastructure
- Before running full test suite
- In CI/CD for fast feedback

**Example:**
```bash
pytest tests/smoke/ -v --tb=short
```

### Tier 2: Integration Tests

**Location:** `tests/integration/e2e/`

**Purpose:** Validate complete workflows and feature integration

**Duration:** 2-5 minutes

**What's Tested:**

#### Complete Agent Lifecycle (`test_complete_agent_lifecycle.py`)
Full workflow including:
1. Server initialization and health check
2. Agent registration with skills
3. Project creation (mocked NLP)
4. Task assignment with dependency handling
5. **Decision logging** - architectural decisions logged to temp directory
6. **Artifact creation** - files written to temp directory
7. Progress reporting at milestones
8. Blocker reporting with AI suggestions
9. Blocker resolution
10. Task completion
11. Final state validation
12. Artifact retrieval via `get_task_context`

**Key Features Tested:**
- `log_decision` - logs architectural decisions that affect other tasks
- `log_artifact` - creates files in organized directory structure
- `get_task_context` - retrieves decisions and artifacts for a task
- Temporary directory management for test isolation

**Artifacts Created:**
All artifacts are written to a temporary directory (`tempfile.mkdtemp()`):
- `docs/specifications/database_schema.sql` - Database schema
- `docs/documentation/run_migration.py` - Migration scripts
- `docs/documentation/.env.example` - Configuration templates

**Example:**
```bash
# Run just the full lifecycle test
pytest tests/integration/e2e/test_complete_agent_lifecycle.py -v

# Run all E2E tests
pytest tests/integration/e2e/ -v
```

#### Other Integration Tests (`test_marcus_workflows.py`)
- Agent registration and task assignment
- Skill-based task matching
- Concurrent assignment (no duplicates)
- Project creation from NLP
- Feature addition to existing projects
- Blocker reporting with AI analysis
- Progress tracking and completion
- Error recovery (Kanban failures)
- Configuration error handling
- Assignment persistence recovery
- System health monitoring

**When to Run:**
- Before committing significant changes
- When adding new features
- Before creating pull requests
- As part of CI/CD pipeline

### Tier 3: Build Validation

**Location:** `scripts/validate_build.sh`

**Purpose:** Ensure Marcus can be built, installed, and deployed

**Duration:** 5-10 minutes (2-3 minutes in quick mode)

**What's Validated:**

1. **Environment Check**
   - Python 3.11+ installed
   - Virtual environment (recommended)

2. **Dependency Check**
   - All dependencies install successfully
   - Marcus installs in development mode

3. **Code Formatting**
   - Black formatting compliance
   - isort import sorting

4. **Linting**
   - Flake8 style checks
   - Pydocstyle docstring validation

5. **Type Checking**
   - Mypy strict type checking on `src/`
   - All type annotations valid

6. **Security**
   - Bandit security scanning
   - No critical vulnerabilities

7. **Smoke Tests**
   - All tier 1 tests pass

8. **Unit Tests**
   - All unit tests pass
   - Coverage ≥80%
   - HTML coverage report generated

9. **Integration Tests** (skipped in quick mode)
   - All E2E workflows pass

10. **Pre-commit Hooks**
    - All hooks install and pass

11. **Build Test**
    - Package builds successfully as wheel

**Usage:**
```bash
# Full validation (recommended before releases)
./scripts/validate_build.sh

# Quick validation (for rapid iteration)
./scripts/validate_build.sh --quick
```

## Test Structure

### Smoke Tests
```python
@pytest.mark.unit
class TestMarcusSmoke(BaseTestCase):
    async def test_server_can_initialize(self):
        """Verify server starts."""
        server = await self._create_test_server()
        assert server is not None
```

### Integration Tests
```python
@pytest.mark.integration
@pytest.mark.e2e
class TestCompleteAgentLifecycle(BaseTestCase):
    def setup_method(self):
        """Create temp directory for artifacts."""
        self.temp_dir = tempfile.mkdtemp(prefix="marcus_e2e_test_")
        self.project_root = self.temp_dir

    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir)

    async def test_full_agent_lifecycle_with_artifacts_and_decisions(self):
        """Complete workflow test."""
        # Test implementation...
```

## Running Tests

### By Type
```bash
# Smoke tests only
pytest tests/smoke/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# E2E tests only
pytest tests/integration/e2e/ -v
```

### By Marker
```bash
# All unit tests
pytest -m unit -v

# All integration tests
pytest -m integration -v

# E2E tests specifically
pytest -m e2e -v

# Skip slow tests
pytest -m "not slow" -v
```

### With Coverage
```bash
# Unit tests with coverage
pytest tests/unit/ --cov=src --cov-report=html --cov-report=term-missing

# View coverage report
open htmlcov/index.html
```

### Specific Tests
```bash
# Run one test file
pytest tests/integration/e2e/test_complete_agent_lifecycle.py -v

# Run one test class
pytest tests/integration/e2e/test_complete_agent_lifecycle.py::TestCompleteAgentLifecycle -v

# Run one test method
pytest tests/integration/e2e/test_complete_agent_lifecycle.py::TestCompleteAgentLifecycle::test_full_agent_lifecycle_with_artifacts_and_decisions -v
```

## Test Markers

Marcus uses pytest markers to categorize tests:

- `@pytest.mark.unit` - Fast, isolated unit test (<100ms)
- `@pytest.mark.integration` - Requires external services/integration
- `@pytest.mark.e2e` - End-to-end workflow test
- `@pytest.mark.slow` - Takes >1 second
- `@pytest.mark.asyncio` - Async test
- `@pytest.mark.kanban` - Requires Kanban server

## CI/CD Integration

### Pre-commit Workflow
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Local Validation Before Push
```bash
# Quick check before commit
./scripts/validate_build.sh --quick

# Full check before PR
./scripts/validate_build.sh
```

### GitHub Actions (Example)
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run validation
        run: |
          ./scripts/validate_build.sh
```

## Debugging Failed Tests

### Verbose Output
```bash
# Show print statements
pytest tests/integration/e2e/ -v -s

# Show full stack traces
pytest tests/integration/e2e/ -v --tb=long

# Stop on first failure
pytest tests/integration/e2e/ -v -x
```

### Test Artifacts

The E2E test creates artifacts in a temporary directory. To inspect them:

```python
# In test, print temp directory location
def test_something(self):
    print(f"\nTemp directory: {self.temp_dir}")
    # Pause to inspect
    import time
    time.sleep(30)  # Inspect files manually
```

Or modify teardown to preserve artifacts:
```python
def teardown_method(self):
    """Preserve temp directory for debugging."""
    if os.environ.get('PRESERVE_TEST_ARTIFACTS'):
        print(f"\nArtifacts preserved at: {self.temp_dir}")
    else:
        shutil.rmtree(self.temp_dir)
```

Then run with:
```bash
PRESERVE_TEST_ARTIFACTS=1 pytest tests/integration/e2e/test_complete_agent_lifecycle.py -v -s
```

### Common Issues

**Import Errors**
```bash
# Ensure Marcus is installed in development mode
pip install -e ".[dev]"
```

**Coverage Below 80%**
```bash
# See which lines are missing coverage
pytest tests/unit/ --cov=src --cov-report=term-missing

# Generate HTML report for detailed view
pytest tests/unit/ --cov=src --cov-report=html
open htmlcov/index.html
```

**Type Errors**
```bash
# Run mypy directly to see details
mypy src
```

**Test Isolation Issues**
```bash
# Ensure factories are reset
from tests.fixtures.factories import reset_all_counters

def setup_method(self):
    super().setup_method()
    reset_all_counters()
```

## Best Practices

### 1. Test Isolation
- Each test should be independent
- Use `setup_method()` and `teardown_method()`
- Reset factory counters
- Clean up temp directories

### 2. Mocking
- Mock external services (Kanban, AI)
- Use `AsyncMock` for async methods
- Verify mock calls when appropriate

### 3. Assertions
- Use descriptive assertion messages
- Test one concept per test method
- Validate both positive and negative cases

### 4. Temp Directories
- Always use `tempfile.mkdtemp()` for artifacts
- Always clean up in `teardown_method()`
- Use unique prefixes for debugging

### 5. Test Naming
- Use descriptive names: `test_[what]_[when]_[expected]`
- Include docstrings explaining the test
- Group related tests in classes

## Performance Benchmarks

Expected test durations:

| Test Suite | Duration | Tests |
|------------|----------|-------|
| Smoke | <30s | ~8 |
| Unit | 1-2min | ~100+ |
| Integration E2E | 2-5min | ~30+ |
| Full Validation | 5-10min | All |
| Quick Validation | 2-3min | All except integration |

## Troubleshooting

### Tests Fail Locally But Pass in CI
- Check Python version (3.11 vs 3.12)
- Check installed dependencies
- Check environment variables

### Tests Pass Locally But Fail in CI
- Check for race conditions
- Check for hardcoded paths
- Check for missing mocks

### Slow Tests
- Profile with `pytest --durations=10`
- Check for unnecessary sleeps
- Check for unmocked network calls

### Flaky Tests
- Look for race conditions in concurrent tests
- Check for insufficient mocking
- Add retries for network-dependent tests

## Contributing

When adding new features:

1. Write smoke test first (if affects core functionality)
2. Write unit tests for new code (TDD)
3. Add integration test for new workflows
4. Run full validation before committing
5. Update this guide if adding new test patterns

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Marcus Test Fixtures](../tests/fixtures/README.md)
- [Marcus Testing Philosophy](../../CLAUDE.md#TEST_WRITING_INSTRUCTIONS)
