Testing Guide
=============

Comprehensive guide to testing PM Agent components.

Test Structure
--------------

PM Agent uses pytest for all testing:

::

   tests/
   ├── unit/                    # Unit tests
   │   ├── test_models.py
   │   ├── test_task_assignment.py
   │   └── test_ai_engine.py
   ├── integration/             # Integration tests
   │   ├── test_mcp_server.py
   │   ├── test_kanban_integration.py
   │   └── test_worker_flow.py
   ├── e2e/                     # End-to-end tests
   │   ├── test_full_workflow.py
   │   └── test_multi_worker.py
   ├── fixtures/                # Test fixtures
   │   ├── mock_workers.py
   │   └── sample_tasks.py
   └── conftest.py             # Pytest configuration

Running Tests
-------------

Basic Commands
~~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov=src --cov-report=html

   # Run specific test file
   pytest tests/unit/test_models.py

   # Run tests matching pattern
   pytest -k "test_task_assignment"

   # Run with verbose output
   pytest -v

   # Run in parallel
   pytest -n auto

Test Categories
~~~~~~~~~~~~~~~

.. code-block:: bash

   # Unit tests only
   pytest tests/unit/

   # Integration tests
   pytest tests/integration/

   # E2E tests (requires full setup)
   pytest tests/e2e/

   # Quick tests (marked as fast)
   pytest -m fast

   # Slow tests
   pytest -m slow

Writing Tests
-------------

Unit Test Example
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   from src.models import Task, WorkerStatus, Priority
   from src.pm_agent_mvp_fixed import PMAgentMVP

   class TestTaskAssignment:
       """Test task assignment logic"""
       
       @pytest.fixture
       def pm_agent(self):
           """Create PM Agent instance for testing"""
           return PMAgentMVP()
       
       @pytest.fixture
       def sample_worker(self):
           """Create a sample worker"""
           return WorkerStatus(
               worker_id="test-worker-001",
               name="Test Worker",
               role="Backend Developer",
               skills=["python", "fastapi", "postgresql"]
           )
       
       @pytest.fixture
       def sample_tasks(self):
           """Create sample tasks"""
           return [
               Task(
                   id="task-1",
                   name="Create API endpoint",
                   description="Build user API",
                   priority=Priority.HIGH,
                   labels=["backend", "api", "python"]
               ),
               Task(
                   id="task-2",
                   name="Design UI component",
                   description="Create button component",
                   priority=Priority.MEDIUM,
                   labels=["frontend", "react"]
               )
           ]
       
       def test_skill_matching(self, pm_agent, sample_worker, sample_tasks):
           """Test that tasks are matched based on skills"""
           # Find best match
           best_task = pm_agent._find_best_task_match(
               sample_tasks, 
               sample_worker
           )
           
           # Should match the backend task
           assert best_task is not None
           assert best_task.id == "task-1"
           assert "python" in best_task.labels
       
       def test_no_skill_match(self, pm_agent, sample_worker):
           """Test behavior when no tasks match worker skills"""
           frontend_tasks = [
               Task(
                   id="task-3",
                   name="Style component",
                   labels=["frontend", "css"]
               )
           ]
           
           best_task = pm_agent._find_best_task_match(
               frontend_tasks,
               sample_worker
           )
           
           # Should return None when no match
           assert best_task is None
       
       @pytest.mark.parametrize("priority,expected_order", [
           (Priority.URGENT, ["urgent", "high", "medium", "low"]),
           (Priority.HIGH, ["high", "medium", "low"]),
       ])
       def test_priority_ordering(self, pm_agent, priority, expected_order):
           """Test tasks are assigned by priority"""
           # Test implementation
           pass

Integration Test Example
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   import asyncio
   from unittest.mock import AsyncMock, patch
   from src.pm_agent_mvp_fixed import PMAgentMVP

   @pytest.mark.asyncio
   class TestKanbanIntegration:
       """Test PM Agent integration with Kanban board"""
       
       @pytest.fixture
       async def pm_agent_with_mocks(self):
           """Create PM Agent with mocked Kanban client"""
           pm_agent = PMAgentMVP()
           
           # Mock Kanban client
           mock_kanban = AsyncMock()
           pm_agent.kanban_client = mock_kanban
           
           # Mock AI engine
           mock_ai = AsyncMock()
           pm_agent.ai_engine = mock_ai
           
           return pm_agent, mock_kanban, mock_ai
       
       async def test_task_assignment_flow(self, pm_agent_with_mocks):
           """Test complete task assignment flow"""
           pm_agent, mock_kanban, mock_ai = pm_agent_with_mocks
           
           # Setup mocks
           mock_kanban.get_available_tasks.return_value = [
               {
                   "id": "card-123",
                   "name": "Test task",
                   "description": "Test description",
                   "labels": ["backend"]
               }
           ]
           
           mock_ai.generate_task_instructions.return_value = "Test instructions"
           
           # Register worker
           await pm_agent.register_agent(
               agent_id="test-001",
               name="Test Worker",
               role="Developer",
               skills=["python"]
           )
           
           # Request task
           result = await pm_agent.request_next_task("test-001")
           
           # Verify flow
           assert result["has_task"] is True
           assert result["assignment"]["task_id"] == "card-123"
           mock_kanban.get_available_tasks.assert_called_once()
           mock_kanban.assign_task.assert_called_once_with("card-123", "test-001")
           mock_ai.generate_task_instructions.assert_called_once()
       
       async def test_progress_reporting(self, pm_agent_with_mocks):
           """Test progress reporting to Kanban"""
           pm_agent, mock_kanban, mock_ai = pm_agent_with_mocks
           
           # Report progress
           await pm_agent.report_task_progress(
               agent_id="test-001",
               task_id="card-123",
               status="in_progress",
               progress=50,
               message="Halfway done"
           )
           
           # Verify Kanban update
           mock_kanban.add_comment.assert_called_with(
               "card-123",
               "Progress: 50% - Halfway done"
           )

E2E Test Example
~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   import asyncio
   from src.pm_agent_mvp_fixed import PMAgentMVP
   from scripts.mock_claude_worker import MockClaudeWorker

   @pytest.mark.e2e
   @pytest.mark.slow
   class TestEndToEnd:
       """Full system integration tests"""
       
       @pytest.fixture
       async def running_system(self):
           """Start PM Agent and workers"""
           # Start PM Agent
           pm_agent = PMAgentMVP()
           pm_task = asyncio.create_task(pm_agent.run())
           
           # Wait for startup
           await asyncio.sleep(2)
           
           yield pm_agent
           
           # Cleanup
           pm_task.cancel()
           try:
               await pm_task
           except asyncio.CancelledError:
               pass
       
       async def test_multiple_workers_complete_tasks(self, running_system):
           """Test multiple workers completing tasks"""
           # Create workers
           workers = []
           for i in range(3):
               worker = MockClaudeWorker(
                   worker_id=f"worker-{i}",
                   worker_type=i % 3  # backend, frontend, qa
               )
               workers.append(worker)
           
           # Start workers
           worker_tasks = []
           for worker in workers:
               task = asyncio.create_task(worker.run())
               worker_tasks.append(task)
           
           # Let them work
           await asyncio.sleep(30)
           
           # Check results
           total_completed = sum(w.completed_tasks for w in workers)
           assert total_completed > 0
           
           # Cleanup
           for task in worker_tasks:
               task.cancel()

Test Fixtures
-------------

Common Fixtures
~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/conftest.py
   import pytest
   import tempfile
   import os
   from pathlib import Path

   @pytest.fixture
   def temp_config():
       """Create temporary configuration"""
       with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
           f.write('''{
               "project_id": "test-project",
               "board_id": "test-board"
           }''')
           temp_path = f.name
       
       yield temp_path
       
       # Cleanup
       os.unlink(temp_path)

   @pytest.fixture
   def mock_env(monkeypatch):
       """Set test environment variables"""
       monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
       monkeypatch.setenv("PLANKA_BASE_URL", "http://localhost:3333")
       monkeypatch.setenv("LOG_LEVEL", "DEBUG")

   @pytest.fixture
   async def clean_workspace():
       """Provide clean workspace for tests"""
       workspace = Path("/tmp/test-workspace")
       workspace.mkdir(exist_ok=True)
       
       yield workspace
       
       # Cleanup
       import shutil
       shutil.rmtree(workspace)

Mock Objects
~~~~~~~~~~~~

.. code-block:: python

   # tests/fixtures/mock_workers.py
   from dataclasses import dataclass
   from typing import List, Optional
   import asyncio

   @dataclass
   class MockWorker:
       """Mock worker for testing"""
       worker_id: str
       name: str
       skills: List[str]
       completed_tasks: int = 0
       current_task: Optional[str] = None
       
       async def work_on_task(self, task_id: str, duration: float = 0.1):
           """Simulate working on a task"""
           self.current_task = task_id
           await asyncio.sleep(duration)
           self.completed_tasks += 1
           self.current_task = None

   def create_mock_worker_team():
       """Create a team of mock workers"""
       return [
           MockWorker("backend-1", "Backend Dev", ["python", "api"]),
           MockWorker("frontend-1", "Frontend Dev", ["react", "css"]),
           MockWorker("qa-1", "QA Engineer", ["testing", "automation"])
       ]

Testing Best Practices
----------------------

1. **Test Isolation**
   
   * Each test should be independent
   * Use fixtures for setup/teardown
   * Mock external dependencies

2. **Test Coverage**
   
   * Aim for 80% code coverage
   * Focus on critical paths
   * Test edge cases and errors

3. **Test Organization**
   
   * One test class per component
   * Descriptive test names
   * Group related tests

4. **Async Testing**
   
   .. code-block:: python
   
      @pytest.mark.asyncio
      async def test_async_operation():
          result = await async_function()
          assert result == expected

5. **Mocking**
   
   .. code-block:: python
   
      from unittest.mock import patch, AsyncMock
      
      @patch('src.integrations.kanban.KanbanClient')
      async def test_with_mock(mock_kanban):
          mock_kanban.return_value.get_tasks = AsyncMock(return_value=[])

6. **Parametrized Tests**
   
   .. code-block:: python
   
      @pytest.mark.parametrize("input,expected", [
          ("test1", "result1"),
          ("test2", "result2"),
      ])
      def test_multiple_cases(input, expected):
          assert process(input) == expected

Performance Testing
-------------------

Load Testing
~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.performance
   async def test_concurrent_workers():
       """Test system with many concurrent workers"""
       workers = []
       for i in range(50):
           worker = create_mock_worker(f"worker-{i}")
           workers.append(worker)
       
       start_time = time.time()
       
       # Run all workers
       tasks = [worker.run() for worker in workers]
       await asyncio.gather(*tasks)
       
       duration = time.time() - start_time
       
       # Should handle 50 workers in under 60 seconds
       assert duration < 60
       
       # Check throughput
       total_tasks = sum(w.completed_tasks for w in workers)
       tasks_per_second = total_tasks / duration
       assert tasks_per_second > 1.0

Memory Testing
~~~~~~~~~~~~~~

.. code-block:: python

   import tracemalloc

   @pytest.mark.memory
   def test_memory_usage():
       """Test memory usage doesn't grow unbounded"""
       tracemalloc.start()
       
       # Run operations
       for i in range(1000):
           create_large_task()
           process_task()
       
       current, peak = tracemalloc.get_traced_memory()
       tracemalloc.stop()
       
       # Memory should stay under 100MB
       assert peak / 1024 / 1024 < 100

Debugging Failed Tests
----------------------

1. **Verbose Output**::

      pytest -vv tests/failing_test.py

2. **Print Debugging**::

      pytest -s  # Don't capture stdout

3. **Drop to Debugger**::

      pytest --pdb  # Drop to pdb on failure

4. **Last Failed**::

      pytest --lf  # Run last failed tests only

5. **Step Through**::

      import pdb; pdb.set_trace()

Continuous Integration
----------------------

GitHub Actions Example
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   # .github/workflows/tests.yml
   name: Tests
   
   on: [push, pull_request]
   
   jobs:
     test:
       runs-on: ubuntu-latest
       
       steps:
       - uses: actions/checkout@v2
       
       - name: Set up Python
         uses: actions/setup-python@v2
         with:
           python-version: 3.11
       
       - name: Install dependencies
         run: |
           pip install -r requirements.txt
           pip install -r requirements-dev.txt
       
       - name: Run tests
         run: |
           pytest --cov=src --cov-report=xml
       
       - name: Upload coverage
         uses: codecov/codecov-action@v1

Next Steps
----------

* Write tests for new features
* Improve test coverage
* Add performance benchmarks
* Set up CI/CD pipeline