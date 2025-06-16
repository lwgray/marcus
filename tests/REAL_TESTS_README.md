# Real Integration Tests with Task Master Test Project

These tests use a real MCP kanban server and the "Task Master Test" project instead of mocks.

## Prerequisites

1. **MCP Kanban Server Running**
   - Ensure your kanban MCP server is running
   - Update the path in `src/integrations/mcp_kanban_client.py` to point to your server

2. **Task Master Test Project**
   - Create a project named "Task Master Test" on your kanban board
   - Or run the setup script to prepare test data

3. **Environment Variables**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```

## Setup Test Data

Run the setup script to create test tasks:

```bash
python tests/setup_test_project.py
```

This will:
- Connect to your MCP server
- Find the "Task Master Test" project
- Create sample tasks with different priorities
- Set some tasks to different states (IN PROGRESS, BLOCKED)

## Running Real Tests

### Run All Real Integration Tests
```bash
pytest tests/integration/test_real_kanban_integration.py -v -s
```

### Run Individual Tests

1. **Test Real Task Retrieval**
   ```bash
   pytest tests/integration/test_real_kanban_integration.py::TestRealKanbanIntegration::test_real_task_retrieval -v -s
   ```
   
   This will:
   - Connect to your MCP server
   - Fetch tasks from "Task Master Test" 
   - Display all available tasks with details

2. **Test Real Task Assignment**
   ```bash
   pytest tests/integration/test_real_kanban_integration.py::TestRealKanbanIntegration::test_real_task_assignment -v -s
   ```
   
   This will:
   - Request a task for test-agent-001
   - AI will analyze and assign best task
   - Update the real kanban board

3. **Test Real Progress Reporting**
   ```bash
   pytest tests/integration/test_real_kanban_integration.py::TestRealKanbanIntegration::test_real_progress_reporting -v -s
   ```
   
   This will:
   - Report 50% progress on assigned task
   - Add real comment to kanban board
   - Update task status

4. **Test Real Blocker Handling**
   ```bash
   pytest tests/integration/test_real_kanban_integration.py::TestRealKanbanIntegration::test_real_blocker_handling -v -s
   ```
   
   This will:
   - Report a blocker on current task
   - AI analyzes and creates resolution plan
   - Task moves to BLOCKED column

5. **Test Real Board Monitoring**
   ```bash
   pytest tests/integration/test_real_kanban_integration.py::TestRealKanbanIntegration::test_real_board_monitoring -v -s
   ```
   
   This will:
   - Analyze project health metrics
   - Calculate velocity and progress
   - Identify risks and overdue tasks

## Expected Output

When running real tests, you'll see actual data from your board:

```
=== TEST: Real Task Retrieval ===

Fetching tasks from Task Master Test project...
Found 5 available tasks:
  - TASK-123: Implement user authentication (Priority: high)
    Status: todo, Estimated: 16.0h
    Labels: backend, security, oauth
  - TASK-124: Create dashboard UI (Priority: medium)
    Status: todo, Estimated: 24.0h
    Labels: frontend, react, ui/ux
...

✅ Successfully retrieved 5 real tasks
```

## Advantages of Real Tests

1. **True Integration** - Tests the actual MCP connection
2. **Real Data** - Works with your actual task structure
3. **End-to-End** - Verifies the complete workflow
4. **Board Updates** - You can see changes on your kanban board

## Cleanup

After testing, you may want to:
- Move test tasks back to TODO
- Remove test assignments
- Clear test comments

Or keep the "Task Master Test" project as a permanent test environment.

## Troubleshooting

If tests fail:

1. **Connection Error**
   - Check MCP server is running
   - Verify server path in mcp_kanban_client.py
   
2. **Project Not Found**
   - Ensure "Task Master Test" project exists
   - Check project name spelling

3. **No Tasks Available**
   - Run setup_test_project.py
   - Or manually create tasks in TODO column

4. **API Key Error**
   - Set ANTHROPIC_API_KEY environment variable