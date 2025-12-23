# Marcus Testing Quick Start

## TL;DR - Run Tests Now

```bash
# Quick smoke tests (<1 second)
pytest tests/smoke/ -v

# Full E2E test with artifacts and decisions (~1-2 minutes)
pytest tests/integration/e2e/test_complete_agent_lifecycle.py -v

# Validate everything before committing (~5-10 minutes)
./scripts/validate_build.sh

# Quick validation (skip slow tests, ~2-3 minutes)
./scripts/validate_build.sh --quick
```

## What You Get

### 1. Smoke Tests (tests/smoke/)
**Duration:** <1 second
**Purpose:** Catch obvious breakage fast

Tests:
- ✓ Server initialization
- ✓ Core tools registered
- ✓ Ping responds
- ✓ Agent registration works
- ✓ Kanban client connected
- ✓ Project status accessible
- ✓ AI engine available

### 2. Full Lifecycle E2E Test
**Duration:** ~1-2 minutes
**File:** `tests/integration/e2e/test_complete_agent_lifecycle.py`

Tests complete agent workflow:
1. Server initialization & health check
2. Agent registration with skills
3. Project creation with tasks
4. Task assignment with dependencies
5. **Decision logging** to temp directory
6. **Artifact creation** (SQL schema, migration scripts, configs)
7. Progress reporting
8. Blocker detection & AI analysis
9. Blocker resolution
10. Task completion
11. Artifact retrieval via `get_task_context`

**Key Features:**
- Logs architectural decisions that affect other tasks
- Creates artifacts in organized temp directory structure
- Validates artifact persistence and retrieval
- Tests blocker workflow with AI suggestions

### 3. Build Validation Script
**Duration:** 5-10 minutes (2-3 in quick mode)
**File:** `scripts/validate_build.sh`

Validates:
- Environment (Python 3.11+)
- Dependencies install
- Code formatting (black, isort)
- Linting (flake8, pydocstyle)
- Type checking (mypy)
- Security (bandit)
- Smoke tests
- Unit tests with 80% coverage
- Integration tests (unless --quick)
- Pre-commit hooks
- Package builds

## When to Run What

**During Development:**
```bash
# After each change
pytest tests/smoke/ -v

# Before committing
pytest tests/integration/e2e/ -v
```

**Before Pull Request:**
```bash
# Full validation
./scripts/validate_build.sh
```

**Rapid Iteration:**
```bash
# Quick check
./scripts/validate_build.sh --quick
```

## What the E2E Test Creates

The full lifecycle test creates artifacts in a temp directory:

```
/tmp/marcus_e2e_test_XXXXXX/
├── docs/
│   ├── specifications/
│   │   └── database_schema.sql
│   └── documentation/
│       ├── run_migration.py
│       └── .env.example
```

All artifacts include:
- Task ID linkage
- Artifact type classification
- Timestamps
- Descriptions

## Common Issues

**Tests fail with "Access denied"**
- Tests must register as admin client type
- Check `_create_test_server()` sets up authentication

**Config errors**
- Tests need proper `MarcusConfig` object, not dict
- Use `self.create_mock_config()` from BaseTestCase

**"No active project" errors**
- Normal behavior when no project loaded
- Tests should handle this gracefully

## More Information

See [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md) for comprehensive documentation.
