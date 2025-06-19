Reference
=========

Complete reference documentation for PM Agent.

.. toctree::
   :maxdepth: 2
   :caption: Contents
   
   api_reference
   mcp_tools
   troubleshooting
   faq
   glossary
   environment_variables

Quick Links
-----------

* :doc:`api_reference` - Complete API documentation
* :doc:`mcp_tools` - Available MCP tools for workers
* :doc:`troubleshooting` - Common issues and solutions
* :doc:`faq` - Frequently asked questions
* :doc:`glossary` - Terms and definitions
* :doc:`environment_variables` - Configuration options

API Overview
------------

PM Agent provides 8 MCP tools for worker agents:

1. **register_agent** - Register a new worker
2. **request_next_task** - Get task assignment
3. **report_task_progress** - Update progress
4. **report_blocker** - Report blockers
5. **get_project_status** - Project metrics
6. **get_agent_status** - Agent information
7. **list_registered_agents** - List all workers
8. **ping** - Health check

See :doc:`mcp_tools` for detailed usage.

Common Tasks
------------

**Registering a Worker**::

   await session.call_tool("register_agent", {
       "agent_id": "worker-001",
       "name": "Backend Developer",
       "role": "Developer",
       "skills": ["python", "fastapi"]
   })

**Requesting Work**::

   result = await session.call_tool("request_next_task", {
       "agent_id": "worker-001"
   })

**Reporting Progress**::

   await session.call_tool("report_task_progress", {
       "agent_id": "worker-001",
       "task_id": "task-123",
       "status": "in_progress",
       "progress": 50,
       "message": "Halfway complete"
   })

Configuration Reference
-----------------------

Key configuration files:

* ``.env`` - Environment variables
* ``config_pm_agent.json`` - Project configuration
* ``prompts/system_prompts.md`` - Worker behavior
* ``docker-compose.yml`` - Service configuration

Error Codes
-----------

Common error responses:

* ``AGENT_NOT_FOUND`` - Agent not registered
* ``TASK_NOT_FOUND`` - Invalid task ID
* ``BOARD_NOT_CONFIGURED`` - Missing board setup
* ``AI_SERVICE_UNAVAILABLE`` - AI provider error
* ``INVALID_PARAMETERS`` - Bad request format

Next Steps
----------

* Review :doc:`api_reference` for detailed API docs
* Check :doc:`troubleshooting` for issue resolution
* See :doc:`glossary` for term definitions