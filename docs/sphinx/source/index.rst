.. PM Agent documentation master file

PM Agent Documentation
======================

PM Agent is an AI-powered project manager for autonomous development teams using the Model Context Protocol (MCP).

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started
   installation
   quick_start
   configuration

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   usage
   mcp_tools
   worker_agents
   security

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/modules
   api/pm_agent
   api/models
   api/integrations

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   development
   architecture
   testing
   contributing

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   troubleshooting
   faq
   changelog
   license

Overview
--------

PM Agent acts as an intelligent project manager that:

* 🤖 Coordinates multiple AI worker agents
* 📋 Manages tasks on Kanban boards (Planka)
* 🧠 Uses AI to resolve blockers and optimize workflows
* ⏱️ Tracks time and progress automatically
* 🔄 Adapts task allocation based on agent capabilities

Key Features
------------

**For Worker Agents:**

* Register & Join: Declare capabilities and join the team
* Request Tasks: Get assigned work matching your skills
* Report Progress: Update task status in real-time
* Handle Blockers: Get AI-powered help when stuck

**For Project Management:**

* Smart Task Distribution: Match tasks to agent capabilities
* Real-time Monitoring: Track progress across all agents
* AI-Powered Resolution: Resolve blockers intelligently
* Automatic Time Tracking: Monitor task duration

Quick Example
-------------

.. code-block:: python

   # Register an agent
   await pm_agent.register_agent(
       agent_id="agent-001",
       name="Alice",
       role="Backend Developer",
       skills=["Python", "Django"]
   )

   # Request a task
   task = await pm_agent.request_next_task("agent-001")

   # Report progress
   await pm_agent.report_task_progress(
       agent_id="agent-001",
       task_id=task.id,
       status="in_progress",
       progress=50
   )

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`