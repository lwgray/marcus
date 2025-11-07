# Test Classification Guide

## How to Add Markers to Tests

When creating or modifying tests, add appropriate pytest markers to help CI/CD run tests strategically.

## Marker Decision Tree

```
Is this a unit test (all external dependencies mocked)?
├─ YES → @pytest.mark.unit
└─ NO → Is it testing integration between components?
    ├─ YES → @pytest.mark.integration
    │        └─ Does it use REAL external services (AI, Kanban, GitHub)?
    │            ├─ YES → @pytest.mark.external
    │            │        └─ Which services?
    │            │            ├─ Real AI → + @pytest.mark.ai + @pytest.mark.slow
    │            │            ├─ Real Kanban → + @pytest.mark.kanban
    │            │            └─ Real GitHub → + @pytest.mark.github
    │            └─ NO (mocked external) → @pytest.mark.internal + @pytest.mark.fast
    └─ Is it an end-to-end workflow test?
        └─ YES → @pytest.mark.e2e + @pytest.mark.slow + @pytest.mark.external
```

## Marker Combinations

### Unit Tests
```python
# All unit tests - fast, isolated, all mocked
@pytest.mark.unit
@pytest.mark.asyncio  # if async
class TestMyComponent:
    def test_something(self):
        pass
```

### Internal Integration Tests (Mocked External Services)
```python
# Tests internal component integration with mocked external services
# Example: NLP parser → Task creator (mocked AI/Kanban)
@pytest.mark.integration
@pytest.mark.internal
@pytest.mark.fast
@pytest.mark.asyncio  # if async
class TestProjectPipeline:
    def test_project_creation_pipeline(self):
        # Mock AI and Kanban, test internal logic
        pass
```

### External Integration Tests - Kanban Only
```python
# Tests actual Kanban API operations (no AI to save costs)
@pytest.mark.integration
@pytest.mark.external
@pytest.mark.kanban
@pytest.mark.asyncio  # if async
class TestPlankaIntegration:
    def test_create_task_on_board(self):
        # Real Kanban operations
        pass
```

### External Integration Tests - AI (Expensive!)
```python
# Tests actual AI API calls - keep these SIMPLE to minimize costs
@pytest.mark.integration
@pytest.mark.external
@pytest.mark.ai
@pytest.mark.slow
@pytest.mark.asyncio  # if async
class TestAIProvider:
    def test_simple_ai_call(self):
        # Real AI call - keep it short and simple!
        pass
```

### E2E Tests (Full Workflows)
```python
# Tests complete workflows with real everything
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.external
@pytest.mark.slow
@pytest.mark.ai  # if uses AI
@pytest.mark.kanban  # if uses Kanban
@pytest.mark.asyncio  # if async
class TestFullProjectCreation:
    def test_complete_project_lifecycle(self):
        # Real AI + Real Kanban + complete workflow
        pass
```

## Classification Examples

### Example 1: NLP Board Integration
**File:** `tests/integration/test_nlp_board_integration.py`

**Analysis:**
- Uses `create_project_from_natural_language` (real AI)
- Uses `KanbanFactory.create()` (real Kanban)
- Creates tasks on actual board
- Takes 30-120 seconds

**Markers:**
```python
@pytest.mark.integration
@pytest.mark.external
@pytest.mark.slow
@pytest.mark.ai
@pytest.mark.kanban
```

### Example 2: Task Execution Order (Internal)
**File:** `tests/integration/test_task_execution_order_integration.py`

**Analysis:**
- Tests internal task ordering logic
- Uses mocked dependencies
- Fast execution (<5s)
- No real external services

**Markers:**
```python
@pytest.mark.integration
@pytest.mark.internal
@pytest.mark.fast
```

### Example 3: Marcus E2E Workflows
**File:** `tests/integration/e2e/test_marcus_workflows.py`

**Analysis:**
- Tests complete agent workflows
- May use real or mocked services depending on configuration
- End-to-end scenarios
- Slow execution

**Markers:**
```python
@pytest.mark.integration
@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.external
```

## Quick Reference Table

| Test Type | Speed | Markers | When to Run |
|-----------|-------|---------|-------------|
| **Unit** | <100ms | `unit` | Every commit, pre-commit |
| **Internal Integration** | <5s | `integration`, `internal`, `fast` | Every PR |
| **External (Kanban only)** | 5-30s | `integration`, `external`, `kanban` | PR to main, nightly |
| **External (with AI)** | 30-300s | `integration`, `external`, `slow`, `ai` | Manual, nightly only |
| **E2E** | 30-300s | `integration`, `e2e`, `slow`, `external` | Manual, nightly, pre-release |

## How to Run Tests by Category

```bash
# Run only unit tests (fastest)
pytest -m unit

# Run unit + internal integration (fast feedback for PRs)
pytest -m "unit or (integration and internal)"

# Run all tests except AI and slow (for PR checks)
pytest -m "not ai and not slow"

# Run external integration without AI (PR to main)
pytest -m "external and not ai"

# Run only slow/E2E tests (nightly)
pytest -m "slow or e2e"

# Run everything
pytest
```

## Adding Markers to Existing Tests

### Step 1: Analyze the Test
Ask these questions:
1. Does it mock all external services? → `unit`
2. Does it test component integration? → `integration`
3. Does it use real external services? → `external`
4. Which external services? → `ai`, `kanban`, `github`
5. How long does it take? → `fast` (<5s) or `slow` (>30s)
6. Is it end-to-end? → `e2e`

### Step 2: Add Markers to Class
```python
# Add markers ABOVE the class definition
@pytest.mark.integration
@pytest.mark.external
@pytest.mark.kanban
class TestKanbanIntegration:
    pass
```

### Step 3: Keep Method-Level Markers
```python
# Keep asyncio markers on individual test methods
class TestKanbanIntegration:
    @pytest.mark.asyncio
    async def test_create_task(self):
        pass
```

## Guidelines

1. **Be Specific:** Add all relevant markers (integration + external + kanban)
2. **Think About Cost:** AI tests are expensive - mark them clearly
3. **Think About Speed:** Help CI/CD run fast tests first
4. **Think About Requirements:** Mark what external services are needed
5. **Update CI/CD:** When adding new marker patterns, update workflows

## CI/CD Integration

Markers enable strategic test running:

- **Feature Branch Push:** Unit tests only (`-m unit`)
- **PR to Develop:** Unit + Internal Integration (`-m "unit or internal"`)
- **PR to Main:** Unit + Internal + External (no AI) (`-m "not ai and not slow"`)
- **Nightly:** Everything (`pytest`)
- **Pre-Release:** Everything with coverage (`pytest --cov`)

This strategy provides:
- ✅ Fast feedback during development
- ✅ Cost savings (don't run expensive AI tests constantly)
- ✅ Confidence before merge (run external integration)
- ✅ Full validation (nightly runs everything)
