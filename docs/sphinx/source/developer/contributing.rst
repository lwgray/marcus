Contributing to Marcus
========================

Thank you for your interest in contributing to Marcus! This guide will help you get started.

Getting Started
---------------

1. **Fork the Repository**
   
   Visit https://github.com/lwgray/pm-agent and click "Fork"

2. **Clone Your Fork**
   
   .. code-block:: bash
   
      git clone https://github.com/YOUR-USERNAME/pm-agent.git
      cd pm-agent
      git remote add upstream https://github.com/lwgray/pm-agent.git

3. **Set Up Development Environment**
   
   .. code-block:: bash
   
      # Create virtual environment
      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate
      
      # Install dependencies
      pip install -r requirements.txt
      pip install -r requirements-dev.txt
      
      # Install pre-commit hooks
      pre-commit install

4. **Create a Branch**
   
   .. code-block:: bash
   
      git checkout -b feature/your-feature-name

Development Workflow
--------------------

1. **Make Your Changes**
   
   * Write clean, documented code
   * Follow the coding standards
   * Add tests for new features

2. **Run Tests**
   
   .. code-block:: bash
   
      # Run all tests
      pytest
      
      # Run specific tests
      pytest tests/unit/test_your_feature.py
      
      # Check coverage
      pytest --cov=src --cov-report=html

3. **Check Code Quality**
   
   .. code-block:: bash
   
      # Run linting
      flake8 src/ tests/
      
      # Check type hints
      mypy src/
      
      # Format code
      black src/ tests/
      
      # Sort imports
      isort src/ tests/

4. **Commit Changes**
   
   .. code-block:: bash
   
      git add .
      git commit -m "feat: add amazing new feature"

Coding Standards
----------------

Python Style
~~~~~~~~~~~~

We follow PEP 8 with some modifications:

* Line length: 88 characters (Black default)
* Use type hints for all functions
* Use docstrings for all public functions

.. code-block:: python

   from typing import List, Optional, Dict, Any
   from dataclasses import dataclass
   import logging

   logger = logging.getLogger(__name__)


   @dataclass
   class TaskResult:
       """Result of task execution.
       
       Attributes
       ----------
       task_id : str
           Unique identifier for the task
       success : bool
           Whether task completed successfully
       message : str
           Human-readable result message
       data : Dict[str, Any], optional
           Additional result data
       """
       task_id: str
       success: bool
       message: str
       data: Optional[Dict[str, Any]] = None


   async def process_task(
       task_id: str,
       worker_id: str,
       timeout: float = 300.0
   ) -> TaskResult:
       """Process a task with the given worker.
       
       Parameters
       ----------
       task_id : str
           The task to process
       worker_id : str
           The worker assigned to the task
       timeout : float, optional
           Maximum time to wait in seconds (default: 300.0)
       
       Returns
       -------
       TaskResult
           Result of task processing
       
       Raises
       ------
       TaskTimeout
           If task exceeds timeout
       WorkerNotFound
           If worker doesn't exist
       
       Examples
       --------
       >>> result = await process_task("task-123", "worker-001")
       >>> print(result.success)
       True
       """
       logger.info(f"Processing task {task_id} with worker {worker_id}")
       
       try:
           # Implementation here
           pass
       except Exception as e:
           logger.error(f"Task {task_id} failed: {e}")
           return TaskResult(
               task_id=task_id,
               success=False,
               message=str(e)
           )

Docstring Style
~~~~~~~~~~~~~~~

We use NumPy-style docstrings:

.. code-block:: python

   def complex_function(
       param1: str,
       param2: List[int],
       param3: Optional[float] = None
   ) -> Dict[str, Any]:
       """Brief description of function.
       
       Longer description that explains what the function
       does in more detail. Can span multiple lines.
       
       Parameters
       ----------
       param1 : str
           Description of param1
       param2 : List[int]
           Description of param2
       param3 : float, optional
           Description of param3 (default: None)
       
       Returns
       -------
       Dict[str, Any]
           Description of return value
       
       Raises
       ------
       ValueError
           When param1 is empty
       TypeError
           When param2 contains non-integers
       
       See Also
       --------
       related_function : Does something related
       
       Notes
       -----
       Additional implementation notes go here.
       
       Examples
       --------
       >>> result = complex_function("test", [1, 2, 3])
       >>> print(result["status"])
       'success'
       """

Commit Messages
~~~~~~~~~~~~~~~

Follow the Conventional Commits specification:

* ``feat:`` New feature
* ``fix:`` Bug fix
* ``docs:`` Documentation changes
* ``style:`` Code style changes (formatting, etc.)
* ``refactor:`` Code refactoring
* ``test:`` Adding or updating tests
* ``chore:`` Maintenance tasks

Examples::

   feat: add worker retry mechanism
   fix: resolve task assignment race condition
   docs: update API reference for new endpoints
   test: add integration tests for kanban client

Testing Guidelines
------------------

1. **Write Tests First** (TDD)
   
   * Write failing test
   * Implement feature
   * Make test pass

2. **Test Coverage**
   
   * New features need tests
   * Aim for 80% coverage
   * Test edge cases

3. **Test Organization**
   
   .. code-block:: python
   
      class TestFeatureName:
          """Tests for FeatureName"""
          
          def test_normal_operation(self):
              """Test feature works normally"""
              
          def test_edge_case(self):
              """Test feature handles edge case"""
              
          def test_error_handling(self):
              """Test feature handles errors gracefully"""

Documentation
-------------

1. **Update Documentation**
   
   * Add docstrings to new functions
   * Update RST files if needed
   * Add examples for new features

2. **API Documentation**
   
   If adding new MCP tools, update:
   
   * ``docs/sphinx/source/reference/api_reference.rst``
   * Add examples of usage
   * Document all parameters

3. **User Guides**
   
   For user-facing features:
   
   * Update relevant guides
   * Add to tutorials if appropriate
   * Include in quickstart if essential

Pull Request Process
--------------------

1. **Before Submitting**
   
   .. code-block:: bash
   
      # Update from upstream
      git fetch upstream
      git rebase upstream/main
      
      # Run all checks
      pytest
      flake8 src/ tests/
      mypy src/
      black --check src/ tests/

2. **Create Pull Request**
   
   * Use descriptive title
   * Reference related issues
   * Describe changes made
   * Include test results

3. **PR Template**
   
   .. code-block:: markdown
   
      ## Description
      Brief description of changes
      
      ## Type of Change
      - [ ] Bug fix
      - [ ] New feature
      - [ ] Breaking change
      - [ ] Documentation update
      
      ## Testing
      - [ ] Unit tests pass
      - [ ] Integration tests pass
      - [ ] Manual testing completed
      
      ## Checklist
      - [ ] Code follows style guidelines
      - [ ] Self-review completed
      - [ ] Documentation updated
      - [ ] Tests added/updated
      
      Fixes #(issue)

4. **Review Process**
   
   * Address review comments
   * Keep PR focused and small
   * Be responsive to feedback

Areas for Contribution
----------------------

Current Priorities
~~~~~~~~~~~~~~~~~~

1. **Worker Agent Examples**
   
   * Create specialized workers
   * Improve existing examples
   * Add language diversity

2. **Visualization Enhancements**
   
   * New visualization types
   * Performance improvements
   * Mobile responsiveness

3. **Integration Additions**
   
   * New kanban providers
   * Additional AI providers
   * Third-party service integrations

4. **Documentation**
   
   * Improve user guides
   * Add video tutorials
   * Translate to other languages

5. **Testing**
   
   * Increase test coverage
   * Add performance tests
   * Create test utilities

Good First Issues
~~~~~~~~~~~~~~~~~

Look for issues labeled:

* ``good first issue``
* ``help wanted``
* ``documentation``
* ``enhancement``

Feature Ideas
~~~~~~~~~~~~~

Before implementing major features:

1. Open an issue to discuss
2. Get feedback from maintainers
3. Create design document if complex

Development Tips
----------------

1. **Local Testing**
   
   .. code-block:: bash
   
      # Test with local Planka
      docker-compose up -d planka
      
      # Run Marcus locally
      python pm_agent_mcp_server_logged.py
      
      # Test with mock workers
      python scripts/mock_claude_worker.py

2. **Debugging**
   
   .. code-block:: python
   
      # Add debug logging
      import logging
      logger = logging.getLogger(__name__)
      logger.debug(f"Processing: {data}")
      
      # Use breakpoints
      import pdb; pdb.set_trace()

3. **Performance**
   
   * Profile before optimizing
   * Use async operations
   * Minimize blocking calls

Community
---------

1. **Getting Help**
   
   * Open an issue for bugs
   * Use discussions for questions
   * Join our Discord (if available)

2. **Code of Conduct**
   
   * Be respectful
   * Welcome newcomers
   * Provide constructive feedback

3. **Recognition**
   
   * Contributors added to AUTHORS
   * Significant contributions highlighted
   * Regular contributors get write access

License
-------

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT).

Thank You!
----------

Your contributions make Marcus better for everyone. We appreciate your time and effort!