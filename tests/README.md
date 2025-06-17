# PM Agent Test Suite Documentation

## Overview

The PM Agent test suite is organized into three main categories:

1. **Unit Tests** (`tests/unit/`) - Test individual components in isolation
2. **Integration Tests** (`tests/integration/`) - Test component interactions
3. **Diagnostic Tests** (`tests/diagnostics/`) - Quick scripts for troubleshooting

## Test Structure

### Unit Tests (`tests/unit/`)

Tests that run without external dependencies:

- **`test_simple_client_unit.py`** ✅ CURRENT
  - Tests SimpleMCPKanbanClient internal methods
  - Tests card-to-task conversion, status mapping, error handling
  - No MCP connection required
  
- **`test_workspace_manager.py`** ✅ CURRENT
  - Tests workspace security and path validation
  - Tests configuration loading
  
- **`test_models.py`** ✅ CURRENT
  - Tests data models (Task, Worker, etc.)
  
- **`test_settings.py`** ✅ CURRENT
  - Tests configuration management

- **`test_ai_analysis_engine.py`** ✅ CURRENT
  - Tests AI engine initialization and prompts

- **`test_kanban_client_unit.py`** ❌ OUTDATED
  - Tests old refactored client (should be removed)

### Integration Tests (`tests/integration/`)

Tests that require external services:

- **`test_simple_client_comprehensive.py`** ✅ CURRENT
  - Comprehensive test suite for SimpleMCPKanbanClient
  - Tests all board operations: tasks, assignments, summaries
  - Requires running kanban-mcp server
  
- **`test_pm_agent_integration.py`** ✅ CURRENT
  - Tests PM Agent MCP server integration
  - Tests agent registration, task assignment, progress reporting

- **`test_kanban_mcp_all_commands.py`** ⚠️ LEGACY
  - Tests all 8 MCP tools comprehensively
  - Uses old refactored client (has timeout issues)
  - Keep for reference but don't rely on it

- **`test_mcp_kanban_client.py`** ❌ OUTDATED
  - Tests old refactored client (should be removed)

- **`test_real_kanban_integration.py`** ❌ OUTDATED
  - Old integration test (should be removed)

### Diagnostic Tests (`tests/diagnostics/`)

Quick scripts for troubleshooting issues:

- **`test_board_id.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_board_id.py
  ```
  - Verifies board_id and project_id are loaded from config
  - Quick check for configuration issues

- **`test_simple_client.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_simple_client.py
  ```
  - Tests SimpleMCPKanbanClient basic operations
  - Shows board statistics and available tasks
  - Can test task assignment

- **`test_direct_mcp.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_direct_mcp.py
  ```
  - Tests raw MCP connection bypassing all wrappers
  - Useful for isolating connection issues
  - Tries multiple node and kanban-mcp paths

- **`test_minimal_mcp.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_minimal_mcp.py
  ```
  - Minimal test matching the working pattern
  - Good baseline for troubleshooting

- **`test_stdio_protocol.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_stdio_protocol.py
  ```
  - Low-level stdio protocol testing
  - Shows raw JSON-RPC communication
  - Useful for protocol-level debugging

- **`test_workspace_integration.py`** ✅ DIAGNOSTIC
  ```bash
  python tests/diagnostics/test_workspace_integration.py
  ```
  - Tests workspace security features
  - Verifies PM Agent source protection
  - Shows workspace assignments

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Unit Tests Only
```bash
pytest tests/unit/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run Specific Test
```bash
pytest tests/unit/test_simple_client_unit.py -v
```

### Run Diagnostic Scripts
```bash
# Quick config check
python tests/diagnostics/test_board_id.py

# Test client functionality
python tests/diagnostics/test_simple_client.py

# Debug connection issues
python tests/diagnostics/test_direct_mcp.py
```

## Test Requirements

### For Unit Tests
- No external requirements
- Mock objects used for external dependencies

### For Integration Tests
- kanban-mcp server must be accessible
- Planka must be running on localhost:3333
- Valid `config_pm_agent.json` with board_id and project_id

### For Diagnostic Tests
- Same as integration tests
- Designed to help troubleshoot when things aren't working

## Continuous Integration

Tests marked as ✅ CURRENT should be included in CI/CD pipelines.
Tests marked as ⚠️ LEGACY or ❌ OUTDATED should be excluded or removed.

## Adding New Tests

1. **Unit Tests**: Add to `tests/unit/` if testing internal logic without external dependencies
2. **Integration Tests**: Add to `tests/integration/` if testing with real services
3. **Diagnostic Tests**: Add to `tests/diagnostics/` if creating troubleshooting tools

Always use SimpleMCPKanbanClient for new kanban-related tests, not the old refactored client.