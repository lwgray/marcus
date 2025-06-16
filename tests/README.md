# PM Agent Test Suite - Detailed Walkthrough

## Overview

This test suite verifies that the AI Project Manager Agent works correctly. We have two types of tests:

1. **Unit Tests** - Test individual components in isolation
2. **Integration Tests** - Test how components work together

## Understanding the Tests

### Unit Tests

#### 1. **Model Tests** (`test_models.py`)
These verify our data structures work correctly:
- Creating tasks with proper fields
- Tracking worker status and capacity  
- Calculating project health metrics

**What happens:**
```python
# We create a task object
task = Task(id="TASK-001", name="Build feature", ...)

# We verify it initialized correctly
assert task.status == TaskStatus.TODO
assert task.dependencies == []  # Empty by default
```

#### 2. **Settings Tests** (`test_settings.py`)
These verify configuration management:
- Loading defaults
- Reading from files
- Environment variable overrides

**What happens:**
```python
# Settings loads from file
settings = Settings("config.json")

# Environment variables override file
os.environ["PM_AGENT_MONITORING_INTERVAL"] = "600"
assert settings.get("monitoring_interval") == 600
```

#### 3. **AI Analysis Tests** (`test_ai_analysis_engine.py`)
These are the most complex, testing our AI decision-making:

**Test 1: Task Assignment**
```
1. AI receives: available tasks + worker profile + project state
2. AI analyzes: skills match, priority, capacity
3. AI returns: best task for that worker
4. Fallback: If API fails, picks highest priority
```

**Test 2: Instruction Generation**
```
1. Senior dev gets: concise, advanced instructions
2. Junior dev gets: detailed, step-by-step guide
3. Both include: relevant technical details
```

**Test 3: Blocker Analysis**
```
1. Critical blocker reported (e.g., database down)
2. AI identifies: root cause, impact, resolution steps
3. AI decides: needs escalation? who to involve?
4. Returns: action plan with time estimates
```

### Integration Tests

These test complete workflows:

#### **Test 1: Task Assignment Flow**
```
Agent requests work → PM finds best task → AI generates instructions 
→ Kanban updated → Notifications sent → Agent receives assignment
```

#### **Test 2: Blocker Escalation**
```
Agent reports blocker → AI analyzes severity → Resolution task created
→ Status updated to blocked → Stakeholders notified → Escalation triggered
```

#### **Test 3: Task Dependencies**
```
Task A completed → System checks dependencies → Task B unblocked
→ Task B owner notified → Board updated → Next work available
```

## Running the Tests

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run All Tests
```bash
# Basic run
pytest

# With output (see what's happening)
pytest -v -s

# Specific test file
pytest tests/unit/test_ai_analysis_engine.py -v
```

### Run with Coverage
```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html
```

### Run Specific Test
```bash
# Run one test method
pytest tests/unit/test_ai_analysis_engine.py::TestAIAnalysisEngine::test_match_task_to_agent_urgent_priority -v -s
```

## What the Tests Verify

### 1. **Correctness**
- Right task goes to right person
- Blockers escalate when critical
- Dependencies unblock properly

### 2. **Resilience**
- System handles API failures gracefully
- Falls back to reasonable defaults
- Doesn't crash on bad input

### 3. **Integration**
- Components communicate properly
- Data flows correctly between systems
- Notifications reach right channels

### 4. **Business Logic**
- Urgent tasks prioritized
- Skills matched appropriately
- Capacity limits respected

## Interpreting Test Output

### Success Output
```
tests/unit/test_ai_analysis_engine.py::TestAIAnalysisEngine::test_match_task_to_agent_urgent_priority PASSED
```

### Failure Output
```
FAILED tests/unit/test_ai_analysis_engine.py::TestAIAnalysisEngine::test_match_task_to_agent_urgent_priority
    AssertionError: assert 'TASK-002' == 'TASK-003'
```
This means the AI didn't pick the expected task.

### With -s Flag (Shows Prints)
```
=== TEST: Complete Task Assignment Flow ===

STEP 1: Setting up test data...
STEP 2: Configuring AI responses...
STEP 3: Agent requesting next task...
Result: {'has_task': True, 'assignment': {...}}

STEP 4: Verifying integration points...
✅ All integration points verified successfully!
```

## Common Test Patterns

### 1. **Mocking External Services**
We mock Claude API and Kanban to test without dependencies:
```python
ai_engine._call_claude = AsyncMock(return_value=json.dumps({...}))
```

### 2. **Fixtures**
Reusable test data:
```python
@pytest.fixture
def sample_tasks(self):
    return [Task(...), Task(...)]
```

### 3. **Async Testing**
Many operations are async:
```python
@pytest.mark.asyncio
async def test_something(self):
    result = await async_function()
```

## Adding New Tests

When adding features, add tests:

1. **Unit test** for the new component
2. **Integration test** for how it fits in
3. **Edge cases** (errors, limits, etc.)

Example:
```python
async def test_new_feature(self):
    # Arrange - Set up test data
    
    # Act - Call the feature
    
    # Assert - Verify results
```

## Debugging Failed Tests

1. Run with `-s` to see print statements
2. Add more prints to understand flow
3. Check mock configurations
4. Verify test data is realistic

Remember: Tests are documentation! They show how the system should work.