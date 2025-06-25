# Visualization System Test Plan - 80% Coverage Target

## Current State Analysis

### Components to Test
1. **conversation_stream.py** - Processes structured logs into events
2. **decision_visualizer.py** - Tracks and visualizes decisions
3. **knowledge_graph.py** - Builds relationship graphs
4. **health_monitor.py** - Monitors project health
5. **ui_server.py** - Web server and API endpoints

### Current Coverage
- Only 1 integration test exists: `test_health_visualization_integration.py`
- No unit tests for individual components
- Estimated current coverage: ~10%

## Test Strategy

### 1. Unit Tests (60% of coverage)
Test each component in isolation with mocked dependencies.

### 2. Integration Tests (15% of coverage)
Test component interactions and data flow.

### 3. API Tests (5% of coverage)
Test HTTP endpoints and WebSocket events.

## Detailed Test Plan

### A. ConversationStreamProcessor Tests
**File**: `test_conversation_stream.py`
- [ ] Test event parsing from structured logs
- [ ] Test file watching functionality
- [ ] Test event handler registration
- [ ] Test different event types (worker_event, pm_event, etc.)
- [ ] Test error handling for malformed logs
- [ ] Test event filtering
- [ ] Test stream starting/stopping

### B. DecisionVisualizer Tests
**File**: `test_decision_visualizer.py`
- [ ] Test decision recording
- [ ] Test decision tree building
- [ ] Test confidence score tracking
- [ ] Test outcome updates
- [ ] Test analytics generation
- [ ] Test visualization export (HTML/JSON)
- [ ] Test decision history queries

### C. KnowledgeGraphBuilder Tests
**File**: `test_knowledge_graph.py`
- [ ] Test node creation (workers, tasks, skills)
- [ ] Test edge creation (relationships)
- [ ] Test graph statistics calculation
- [ ] Test graph export to different formats
- [ ] Test graph querying
- [ ] Test incremental updates
- [ ] Test graph pruning/cleanup

### D. HealthMonitor Tests
**File**: `test_health_monitor.py`
- [ ] Test health analysis calculation
- [ ] Test risk assessment
- [ ] Test velocity calculation
- [ ] Test alert generation
- [ ] Test health history tracking
- [ ] Test summary statistics
- [ ] Test monitoring loop

### E. UIServer Tests
**File**: `test_ui_server.py`
- [ ] Test server initialization
- [ ] Test route registration
- [ ] Test WebSocket connection handling
- [ ] Test API endpoint responses
- [ ] Test CORS configuration
- [ ] Test template rendering
- [ ] Test error handling

### F. Integration Tests
**File**: `test_visualization_integration.py`
- [ ] Test end-to-end event flow
- [ ] Test real-time updates via WebSocket
- [ ] Test multiple client connections
- [ ] Test data persistence across restarts
- [ ] Test performance with high event volume

### G. Frontend Tests (Vue.js)
**Directory**: `visualization-ui/tests/`
- [ ] Component tests for WorkflowCanvas
- [ ] Component tests for node types
- [ ] Store tests (Pinia)
- [ ] WebSocket client tests
- [ ] Event handling tests
- [ ] UI interaction tests

## Implementation Priority

### Phase 1: Core Backend Tests (Week 1)
1. ConversationStreamProcessor (most critical)
2. UIServer (API endpoints)
3. HealthMonitor

### Phase 2: Visualization Components (Week 2)
4. DecisionVisualizer
5. KnowledgeGraphBuilder
6. Integration tests

### Phase 3: Frontend Tests (Week 3)
7. Vue component tests
8. Store tests
9. E2E tests

## Test Utilities Needed

### Mock Factories
```python
# tests/visualization/factories.py
- create_mock_conversation_event()
- create_mock_decision()
- create_mock_worker_status()
- create_mock_project_state()
- create_mock_health_data()
```

### Test Fixtures
```python
# tests/visualization/conftest.py
- sample_log_file
- temp_log_directory
- mock_socketio_server
- test_client
- event_samples
```

## Coverage Targets by Component

| Component | Target | Priority |
|-----------|--------|----------|
| conversation_stream.py | 85% | High |
| ui_server.py | 80% | High |
| health_monitor.py | 85% | High |
| decision_visualizer.py | 75% | Medium |
| knowledge_graph.py | 75% | Medium |
| Frontend (Vue) | 70% | Medium |

## Success Metrics

1. **Overall Coverage**: ≥80% for visualization package
2. **Critical Path Coverage**: 95% for event processing
3. **API Coverage**: 100% for public endpoints
4. **Error Handling**: 90% coverage of error paths
5. **Performance**: Tests complete in <30 seconds

## Testing Tools

### Backend
- pytest
- pytest-asyncio
- pytest-cov
- pytest-mock
- aiohttp testing utilities
- python-socketio testing client

### Frontend
- Vitest
- @vue/test-utils
- @pinia/testing
- Coverage with c8

## CI/CD Integration

```yaml
# .github/workflows/test-visualization.yml
- Run backend tests with coverage
- Run frontend tests with coverage
- Merge coverage reports
- Fail if below 80%
- Generate coverage badge
```

## Next Steps

1. Set up test infrastructure
2. Create mock factories and fixtures
3. Implement tests in priority order
4. Run coverage reports after each phase
5. Iterate to reach 80% target