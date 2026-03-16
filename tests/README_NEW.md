# Marcus Test Suite

Comprehensive testing strategy for the Marcus multi-agent coordination system.

## Quick Start

```bash
# Run unit tests (fastest - recommended during development)
pytest -m unit

# Run unit + internal integration tests (before committing)
pytest -m "unit or (integration and internal)"

# Run all tests except slow/expensive ones (before PR)
pytest -m "not slow and not ai"

# Run everything (nightly/pre-release)
pytest
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Speed:** <100ms per test
- **Dependencies:** All mocked
- **Purpose:** Test individual components in isolation
- **Run:** Every commit, pre-commit hooks

### Internal Integration Tests (`@pytest.mark.internal`)
- **Speed:** 1-5 seconds per test
- **Dependencies:** External services MOCKED
- **Purpose:** Test internal component integration
- **Run:** Every PR

### External Integration Tests (`@pytest.mark.external`)
- **Speed:** 5-30 seconds per test
- **Dependencies:** Real external services (Kanban, GitHub)
- **Purpose:** Test actual API communication
- **Run:** PR to main, nightly

### E2E Tests (`@pytest.mark.e2e`)
- **Speed:** 30-300 seconds per test
- **Dependencies:** Real everything (including AI)
- **Purpose:** Test complete workflows
- **Run:** Nightly, manual, pre-release

## Development Workflow

### During Development
```bash
pytest tests/unit/ai/ -v
```

### Before Committing
```bash
pytest -m "unit or internal" -v
pre-commit run
```

### Before Creating PR
```bash
pytest -m "not slow and not ai" -v
```

## CI/CD Integration

| Trigger | Tests Run | Duration |
|---------|-----------|----------|
| **Push to feature branch** | Unit only | <2 min |
| **PR to develop** | Unit + Internal Integration | <5 min |
| **PR to main** | Unit + Internal + External (no AI) | <10 min |
| **Nightly** | Full suite including E2E + AI | <45 min |

## Further Reading

- [TEST_CLASSIFICATION_GUIDE.md](../docs/TEST_CLASSIFICATION_GUIDE.md) - How to classify and mark tests
- [CLAUDE.md](../CLAUDE.md) - Project coding standards
