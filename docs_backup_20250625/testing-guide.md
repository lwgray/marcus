# Testing Guide

This guide covers all testing approaches for the PM Agent system.

## Test Infrastructure

### Test Organization
```
tests/
├── unit/              # Unit tests for components
├── integration/       # Integration tests with kanban-mcp
├── conftest.py       # Pytest fixtures
└── setup_test_project.py  # Test data setup
```

### Running Tests

```bash
# All tests
pytest

# Specific test category
pytest tests/unit
pytest tests/integration

# With coverage
pytest --cov=src --cov-report=html
```

## Manual Testing Tools

### 1. Setup Verification
```bash
python scripts/utilities/test_setup.py
```
Checks:
- Environment configuration
- Dependencies installed
- Services running

### 2. Interactive Testing
```bash
python scripts/utilities/interactive_test.py
```
Features:
- Create cards interactively
- Add comments
- Move cards between lists
- Test all PM Agent features

### 3. Board Viewer
```bash
python scripts/utilities/quick_board_view.py
```
Shows:
- Current board state
- Card distribution
- Statistics

### 4. End-to-End Simulation
```bash
python scripts/test_pm_agent_end_to_end.py
```
Simulates:
- Worker agent registration
- Task assignment
- Progress tracking
- Time tracking
- High-priority task creation

## Test Scenarios

### Scenario 1: Worker Agent Workflow
1. Worker registers with PM Agent
2. Requests next task
3. Reports progress
4. Completes task
5. Requests new task

### Scenario 2: Blocker Handling
1. Worker encounters blocker
2. Reports to PM Agent
3. PM Agent analyzes with AI
4. Creates resolution task
5. Notifies relevant workers

### Scenario 3: Project Monitoring
1. PM Agent checks project status
2. Identifies bottlenecks
3. Reallocates resources
4. Updates priorities

## Writing New Tests

### Unit Test Example
```python
# tests/unit/test_models.py
def test_agent_registration():
    agent = Agent(
        id="test-1",
        name="Test Agent",
        capabilities=["Python", "Testing"]
    )
    assert agent.id == "test-1"
    assert "Python" in agent.capabilities
```

### Integration Test Example
```python
# tests/integration/test_kanban_integration.py
async def test_create_card():
    client = MCPKanbanClient()
    async with client.connect() as conn:
        result = await conn.call_tool(
            "mcp_kanban_card_manager",
            {"action": "create", "listId": "123", "name": "Test"}
        )
        assert result is not None
```

## Test Data

### Creating Test Projects
```python
python scripts/examples/create_todo_app_tasks.py
```
Creates a full todo app workflow with:
- 4 lists
- 9 cards
- 39 tasks
- 5 labels

### Resetting Test Data
1. Delete cards in Planka UI
2. Or create new board
3. Update `config_pm_agent.json`

## Continuous Integration

### GitHub Actions Example
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pytest
```

## Performance Testing

### Load Testing
```python
# Test multiple workers
async def test_concurrent_workers():
    workers = []
    for i in range(10):
        worker = create_worker(f"worker-{i}")
        workers.append(worker)
    
    # Simulate concurrent requests
    tasks = [w.request_task() for w in workers]
    results = await asyncio.gather(*tasks)
```

### Stress Testing
- Create 100+ cards
- Simulate 50+ workers
- Measure response times
- Check memory usage

## Debugging Tests

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Capture MCP Communication
```python
# In your test
with capture_mcp_traffic() as traffic:
    # Run test
    pass
print(traffic.requests)
print(traffic.responses)
```

### Common Issues
1. **Timeout errors**: Increase timeout in test
2. **Connection failures**: Check kanban-mcp path
3. **Auth errors**: Verify Planka credentials
4. **State conflicts**: Reset test data between runs