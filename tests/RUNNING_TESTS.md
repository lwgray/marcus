# Running Tests in Marcus

## Quick Start

```bash
# Run all unit tests (default - recommended)
pytest

# Run unit tests with coverage
pytest --cov=src --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/unit/core/test_models.py

# Run tests matching a pattern
pytest -k "test_health"
```

## Test Organization

```
tests/
├── unit/                   # ✅ Unit tests (181 tests) - Run by default
│   ├── ai/                # AI components
│   ├── core/              # Core functionality
│   ├── mcp/               # MCP protocol
│   └── visualization/     # UI components
├── integration/           # 🔶 Integration tests (require services)
├── performance/           # 📊 Performance benchmarks
├── future_features/       # 🚧 TDD tests for unimplemented features
└── archive/              # 📦 Archived/obsolete tests
```

## Running Different Test Suites

### Unit Tests (Fast, Isolated)
```bash
pytest                                    # All unit tests
pytest tests/unit/                       # Explicit path
pytest tests/unit/core/                  # Core module only
pytest tests/unit/ai/                    # AI modules only
```

### Integration Tests (Slower, Require Services)
```bash
pytest tests/integration/                # All integration tests
pytest tests/integration/e2e/            # End-to-end tests only
pytest -m integration                    # Tests marked as integration
```

### Performance Tests
```bash
pytest tests/performance/                # Performance benchmarks
pytest -m performance                    # Tests marked as performance
```

### Future Features (TDD - May Fail)
```bash
pytest tests/future_features/            # Unimplemented features
```

## Test Markers

Mark your tests with these markers:

```python
@pytest.mark.unit         # Fast, isolated unit test
@pytest.mark.integration  # Requires external services
@pytest.mark.slow         # Takes a long time to run
@pytest.mark.performance  # Performance benchmark
@pytest.mark.kanban       # Requires Kanban MCP server
@pytest.mark.e2e          # End-to-end workflow test
```

## Common Options

```bash
# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run last failed tests only
pytest --lf

# Run tests in parallel (if pytest-xdist installed)
pytest -n 4

# Generate coverage report
pytest --cov=src --cov-report=html

# Run with debugging
pytest -s --pdb
```

## Continuous Integration

The default `pytest` command runs unit tests only, ensuring fast and reliable CI builds:

- ✅ **181 unit tests** - Fast, isolated, always pass
- 🔶 **Integration tests** - Run separately when needed
- 📊 **Performance tests** - Run on schedule
- 🚧 **Future features** - Run during development

## Current Status

```
✅ Unit Tests: 181/181 passing (100%)
🔶 Integration Tests: Available separately
📊 Performance Tests: Available separately
🚧 Future Features: TDD tests for development
```
