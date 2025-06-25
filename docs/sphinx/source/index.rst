.. Marcus documentation master file

Marcus Documentation
====================

Marcus is an AI-powered project manager for autonomous development teams using the Model Context Protocol (MCP).

.. toctree::
   :maxdepth: 1
   :caption: 🚀 Getting Started
   
   getting_started
   installation
   quick_start
   tutorials/demo_guide

.. toctree::
   :maxdepth: 2
   :caption: 📚 User Guide
   
   user_guide/index
   user_guide/concepts
   user_guide/providers
   user_guide/creating_tasks
   user_guide/claude_desktop_setup
   user_guide/claude_code_setup
   user_guide/monitoring_progress
   configuration

.. toctree::
   :maxdepth: 2
   :caption: 🔧 Tutorials
   
   tutorials/index
   tutorials/demo_guide
   tutorials/todo_app_example
   tutorials/custom_workers
   tutorials/real_world_examples

.. toctree::
   :maxdepth: 2
   :caption: 📝 Templates & Examples
   
   templates/index
   templates/prd_template
   templates/product_spec_template
   templates/task_writing_guide

.. toctree::
   :maxdepth: 3
   :caption: 📖 API Reference
   
   api/modules
   api/pm_agent
   api/models
   api/integrations
   api/workspace

.. toctree::
   :maxdepth: 2
   :caption: 👩‍💻 Developer Guide
   
   developer/index
   developer/architecture
   developer/worker_agents
   developer/visualization
   developer/testing
   developer/contributing

.. toctree::
   :maxdepth: 1
   :caption: ❓ Help & Reference
   
   reference/index
   reference/troubleshooting
   reference/faq
   reference/glossary
   reference/environment_variables

Overview
--------

Marcus acts as an intelligent project manager that:

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
   await marcus.register_agent(
       agent_id="agent-001",
       name="Alice",
       role="Backend Developer",
       skills=["Python", "Django"]
   )

   # Request a task
   task = await marcus.request_next_task("agent-001")

   # Report progress
   await marcus.report_task_progress(
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