Marcus MCP Server
=================

.. automodule:: marcus_mcp.server
   :no-members:

MarcusServer Class
------------------

.. autoclass:: marcus_mcp.server.MarcusServer
   :members:
   :private-members:
   :special-members: __init__
   :undoc-members:
   :show-inheritance:
   :no-index:

Key Methods
-----------

.. automethod:: marcus_mcp.server.MarcusServer.initialize_kanban
   :no-index:

.. automethod:: marcus_mcp.server.MarcusServer.refresh_project_state
   :no-index:

.. automethod:: marcus_mcp.server.MarcusServer.log_event
   :no-index:

.. automethod:: marcus_mcp.server.MarcusServer.run
   :no-index:

MCP Tool Handlers
-----------------

The MCP tools are handled through the handler system. Tools are defined in:

- ``src/marcus_mcp/handlers.py`` - Tool definitions and handlers
- ``src/marcus_mcp/tools/`` - Individual tool implementations

Available tools include:

- **register_agent** - Register a new agent with Marcus
- **request_next_task** - Request the next available task
- **report_task_progress** - Report progress on current task
- **report_blocker** - Report a blocking issue
- **get_project_status** - Get current project status
- **get_agent_status** - Get status of a specific agent
- **create_project_from_natural_language** - Create project from description
- **add_feature_natural_language** - Add feature using natural language