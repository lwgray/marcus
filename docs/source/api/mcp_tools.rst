MCP Tools Reference
===================

Marcus implements MCP (Model Context Protocol) server tools that AI agents
use to coordinate and execute tasks.

Agent Tools
-----------

.. currentmodule:: marcus_mcp.tools.agent

.. autofunction:: register_agent

.. autofunction:: get_agent_status

.. autofunction:: list_agents


Task Tools
----------

.. currentmodule:: marcus_mcp.tools.task

.. autofunction:: request_next_task

.. autofunction:: report_task_progress

.. autofunction:: report_blocker

.. autofunction:: get_task_context

.. autofunction:: check_dependencies


Project Tools
-------------

.. currentmodule:: marcus_mcp.tools.project

.. autofunction:: create_project

.. autofunction:: get_project_status

.. autofunction:: list_projects


Project Management Tools
------------------------

.. currentmodule:: marcus_mcp.tools.project_management

.. autofunction:: analyze_project_health

.. autofunction:: get_project_analytics


System Tools
------------

.. currentmodule:: marcus_mcp.tools.system

.. autofunction:: ping

.. autofunction:: get_system_health


Analytics Tools
---------------

.. currentmodule:: marcus_mcp.tools.analytics

.. autofunction:: get_task_analytics

.. autofunction:: get_agent_performance

.. autofunction:: get_project_metrics


Context Tools
-------------

.. currentmodule:: marcus_mcp.tools.context

.. autofunction:: log_decision

.. autofunction:: track_artifact

.. autofunction:: get_implementation_context


NLP Tools
---------

.. currentmodule:: marcus_mcp.tools.nlp

.. autofunction:: parse_natural_language_project


Predictions Tools
-----------------

.. currentmodule:: marcus_mcp.tools.predictions

.. autofunction:: predict_completion_time

.. autofunction:: predict_task_complexity

.. autofunction:: predict_resource_needs
