# Test Placement Decision Flowchart

## 🎯 Quick Decision Path

```
┌─────────────────────────────────────────────────────────────┐
│                    START: New Test Needed                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────┐
        │  Q1: Does it need external services?     │
        │  (Database, API, Network, File System)   │
        └────────────┬─────────────────┬───────────┘
                     │ NO              │ YES
                     ▼                 ▼
         ┌───────────────────┐   ┌────────────────────────┐
         │ Q2: Single unit?  │   │ Q3: Future feature?    │
         │ (class/function)  │   │ (TDD/unimplemented)    │
         └──┬──────────┬─────┘   └──┬───────────────┬────┘
            │ YES      │ NO         │ YES           │ NO
            ▼          ▼            ▼               ▼
     ┌─────────────┐  tests/    tests/         ┌────────────────┐
     │ Which type? │  unit/     future_        │ Q4: Test type? │
     └──────┬──────┘  test_*.py features/      └───────┬────────┘
            │                                            │
     ┌──────┴───────┐                          ┌────────┴────────┐
     ▼      ▼       ▼                          ▼        ▼        ▼
   AI    Core    MCP/Viz                    E2E      API    Performance
   │       │        │                        │        │         │
tests/  tests/   tests/                  tests/   tests/    tests/
unit/   unit/    unit/                   integ/   integ/    performance/
ai/     core/    mcp/ or                 e2e/     api/
                 visualization/
```

## 📊 Detailed Decision Matrix

| Question | Answer | Next Step | Final Location |
|----------|---------|-----------|----------------|
| **Needs external services?** | No | Check if single unit | → Unit tests |
| | Yes | Check if future feature | → Integration or Future |
| **Single unit test?** | Yes | Identify component type | → Specific unit folder |
| | No | General unit test | → `tests/unit/test_*.py` |
| **Future/TDD feature?** | Yes | Unimplemented code | → `tests/future_features/` |
| | No | Check integration type | → Integration tests |
| **Component type?** | AI/ML | AI logic | → `tests/unit/ai/` |
| | Core | Models, managers | → `tests/unit/core/` |
| | MCP | Protocol handling | → `tests/unit/mcp/` |
| | UI | Visualization | → `tests/unit/visualization/` |
| **Integration type?** | E2E | Full workflow | → `tests/integration/e2e/` |
| | API | Service integration | → `tests/integration/api/` |
| | External | 3rd party services | → `tests/integration/external/` |
| | Diagnostic | Debug/connection | → `tests/integration/diagnostics/` |
| | Performance | Speed/load | → `tests/performance/` |

## 🚦 Quick Rules

### ✅ **Unit Test** (`tests/unit/`)
- No external dependencies
- All I/O is mocked
- Runs in < 100ms
- Tests single component
- No real network calls
- No real file system access

### 🔶 **Integration Test** (`tests/integration/`)
- Uses real services
- Tests component interactions
- May access network/filesystem
- Slower execution (> 100ms)
- Requires service setup
- Tests real workflows

### 🚧 **Future Features** (`tests/future_features/`)
- TDD tests written first
- Code doesn't exist yet
- May have import errors
- Not run by default
- Documents intended API
- Guides implementation

### 📊 **Performance Test** (`tests/performance/`)
- Measures execution time
- Tests scalability
- Benchmarks operations
- Load testing
- Memory profiling
- Not run by default

## 🎯 Examples by Scenario

### Example 1: Testing Task Assignment Logic
```
Q1: External services? → NO (pure logic)
Q2: Single unit? → YES (AssignmentManager class)
Component: Core logic
→ Place in: tests/unit/core/test_assignment_manager.py
```

### Example 2: Testing GitHub Integration
```
Q1: External services? → YES (GitHub API)
Q3: Future feature? → NO (exists)
Q4: Integration type? → External service
→ Place in: tests/integration/external/test_github_integration.py
```

### Example 3: Testing New AI Decision Engine
```
Q1: External services? → YES (LLM API)
Q3: Future feature? → YES (not implemented)
→ Place in: tests/future_features/ai/test_decision_engine.py
```

### Example 4: Testing UI Response Time
```
Q1: External services? → NO/YES (depends)
Q4: Performance test? → YES
→ Place in: tests/performance/test_ui_response_time.py
```

## 🏗️ Test File Structure

```
tests/
├── unit/                        # 🟢 Fast, isolated (default pytest)
│   ├── ai/                     # AI component tests
│   ├── core/                   # Core logic tests
│   ├── mcp/                    # MCP protocol tests
│   └── visualization/          # UI component tests
│
├── integration/                 # 🟡 Slower, real services
│   ├── e2e/                   # End-to-end workflows
│   ├── api/                   # API integrations
│   ├── external/              # 3rd party services
│   └── diagnostics/           # Connection/debug tests
│
├── performance/                 # 🔵 Benchmarks and load tests
│   ├── benchmarks/            # Speed benchmarks
│   └── load/                  # Concurrent load tests
│
├── future_features/            # 🟣 TDD for unimplemented
│   └── [mirrors src structure]
│
└── archive/                    # 🔴 Old/deprecated tests
```

## 💡 Pro Tips

1. **When in doubt, start with a unit test** - You can always move it later
2. **Use mocks aggressively in unit tests** - Real services = integration test
3. **Name tests descriptively** - `test_assignment_manager_handles_priority_conflicts.py`
4. **One test file per component** - Don't mix unrelated tests
5. **Mark your tests** - Use `@pytest.mark.unit`, `@pytest.mark.integration`, etc.

## 🔍 Final Checklist

Before placing your test:

- [ ] Have I identified all external dependencies?
- [ ] Is this testing current or future code?
- [ ] Am I testing one thing or a workflow?
- [ ] Will this test run quickly (< 100ms)?
- [ ] Have I chosen the most specific directory?
- [ ] Does my test name clearly indicate what it tests?