Developer Guide
===============

Technical documentation for developers working on or extending PM Agent.

.. toctree::
   :maxdepth: 2
   :caption: Contents
   
   architecture
   system_architecture
   ai_engine_guide
   worker_agents
   visualization
   testing
   contributing

Overview
--------

This guide provides in-depth technical information for:

* Understanding PM Agent's architecture
* Building custom worker agents
* Extending the visualization system
* Contributing to PM Agent development
* Running tests and ensuring quality

For Developers
--------------

**Architecture**
   Deep dive into PM Agent's dual MCP architecture, data flow, and design decisions.

**Worker Agents**
   Complete guide to building AI agents that integrate with PM Agent, including examples and best practices.

**Visualization System**
   Technical details of the real-time visualization system, including extending and customizing it.

**Testing**
   How to test PM Agent components, write new tests, and ensure code quality.

**Contributing**
   Guidelines for contributing to PM Agent, including code style, PR process, and development setup.

Key Concepts
------------

**MCP (Model Context Protocol)**
   PM Agent uses MCP for both server (worker interface) and client (kanban interface) roles.

**Worker Registration**
   Agents declare their capabilities when joining the system.

**Task Assignment**
   Intelligent matching based on skills, priority, and availability.

**Progress Tracking**
   Real-time updates from workers to kanban board.

**Blocker Resolution**
   AI-powered assistance when workers encounter issues.

Development Setup
-----------------

1. **Clone the repository**::

      git clone https://github.com/lwgray/pm-agent.git
      cd pm-agent

2. **Create virtual environment**::

      python -m venv venv
      source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**::

      pip install -r requirements.txt
      pip install -r requirements-dev.txt

4. **Run tests**::

      pytest tests/

5. **Start development server**::

      python pm_agent_mcp_server.py

Code Organization
-----------------

::

   pm-agent/
   ├── src/
   │   ├── pm_agent_mvp_fixed.py      # Main PM Agent server
   │   ├── models/                    # Data models
   │   ├── integrations/              # External integrations
   │   ├── visualization/             # Visualization system
   │   └── utils/                     # Utility functions
   ├── tests/                         # Test suite
   ├── scripts/                       # Utility scripts
   └── docs/                          # Documentation

API Development
---------------

PM Agent exposes MCP tools for worker agents:

* ``register_agent`` - Worker registration
* ``request_next_task`` - Task assignment
* ``report_task_progress`` - Progress updates
* ``report_blocker`` - Blocker reporting
* ``get_project_status`` - Project metrics
* ``get_agent_status`` - Agent information
* ``list_registered_agents`` - Active workers
* ``ping`` - Health check

See :doc:`/reference/api_reference` for complete details.

Debugging Tips
--------------

1. **Enable debug logging**::

      export LOG_LEVEL=DEBUG
      python pm_agent_mcp_server_logged.py

2. **Monitor conversations**::

      tail -f logs/conversations/pm_agent_conversation.log

3. **Test individual components**::

      python -m pytest tests/test_component.py -v

4. **Use interactive debugger**::

      import pdb; pdb.set_trace()

Performance Considerations
--------------------------

* Use async operations throughout
* Implement connection pooling
* Cache frequently accessed data
* Batch kanban operations
* Monitor memory usage

Security Best Practices
-----------------------

* Validate all inputs
* Use environment variables for secrets
* Implement rate limiting
* Log security events
* Regular dependency updates

Next Steps
----------

* Read the :doc:`architecture` guide
* Explore :doc:`worker_agents` implementation
* Check :doc:`visualization` for UI development
* Review :doc:`contributing` before submitting PRs