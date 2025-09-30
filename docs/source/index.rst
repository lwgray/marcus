Marcus AI Documentation
========================

**Intelligent Agent Coordination for Software Development**

Marcus enables AI agents to collaborate autonomously on software development projects,
with context, intelligence, and transparency built-in.

.. grid:: 2
    :gutter: 3

    .. grid-item-card:: 🚀 Quickstart
        :link: getting-started/quickstart
        :link-type: doc

        Get started with Marcus in under 5 minutes

    .. grid-item-card:: 💡 Core Concepts
        :link: getting-started/core-concepts
        :link-type: doc

        Learn about agents, tasks, and projects

    .. grid-item-card:: 📖 API Reference
        :link: api/index
        :link-type: doc

        Explore the complete auto-generated API documentation

    .. grid-item-card:: 🏗️ Systems Architecture
        :link: systems/README
        :link-type: doc

        Dive into Marcus's internal systems


Why Marcus?
-----------

.. tab-set::

    .. tab-item:: Intelligent Coordination

        Context-aware task assignment, predictive analytics, and AI-powered
        blocker resolution enable agents to work efficiently without constant supervision.

    .. tab-item:: Bring Your Own Agent

        Works with Claude, GPT, Gemini, or custom models - Marcus provides the
        coordination layer while you choose the intelligence.

    .. tab-item:: Board-Based Communication

        All coordination happens through Kanban boards - no hidden conversations,
        everything visible and trackable.

    .. tab-item:: Continuous Learning

        Four-tier memory system (Working, Episodic, Semantic, Procedural) learns
        from every project and gets smarter over time.


Quick Example
-------------

Here's how an agent works with Marcus:

.. code-block:: python

    from marcus_mcp import MarcusClient

    # Agent registers and enters work loop
    client = MarcusClient()
    await client.register_agent(
        agent_id="worker-1",
        capabilities=["python", "react"]
    )

    while True:
        # Request optimal task based on capabilities and context
        task = await client.request_next_task("worker-1")

        if task:
            # Get rich context including dependencies
            context = await client.get_task_context(task['id'])

            # Work autonomously with full context
            result = await do_work(task, context)

            # Report completion
            await client.report_task_progress(
                task['id'], "worker-1", 100, result
            )


.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started/introduction
   getting-started/quickstart
   getting-started/core-concepts
   getting-started/setup-local-llm

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guides/index
   guides/agent-workflows/agent-workflow
   guides/agent-workflows/registration
   guides/agent-workflows/requesting-tasks
   guides/agent-workflows/reporting-progress
   guides/agent-workflows/checking-dependencies
   guides/agent-workflows/getting-context
   guides/agent-workflows/handling-blockers
   guides/project-management/creating-projects
   guides/project-management/monitoring-status
   guides/project-management/analyzing-health
   guides/collaboration/communication-hub
   guides/collaboration/logging-decisions
   guides/collaboration/tracking-artifacts
   guides/advanced/memory-system
   guides/advanced/agent-status
   guides/advanced/agent-support-tools
   guides/advanced/ping-system

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api/index
   api/mcp_tools
   api/python_api
   api/data_models
   api/error_handling

.. toctree::
   :maxdepth: 2
   :caption: Systems

   systems/README
   systems/intelligence/index
   systems/coordination/index
   systems/project-management/index
   systems/architecture/index
   systems/infrastructure/index
   systems/quality/index

.. toctree::
   :maxdepth: 1
   :caption: Concepts & Roadmap

   concepts/README
   concepts/philosophy
   concepts/core-values
   roadmap/index
   roadmap/evolution
   roadmap/public-release-roadmap
