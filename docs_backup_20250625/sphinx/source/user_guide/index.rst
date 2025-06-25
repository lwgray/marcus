User Guide
==========

This guide covers everything you need to know to use PM Agent effectively.

.. toctree::
   :maxdepth: 2
   :caption: Contents
   
   concepts
   providers
   claude_desktop_setup
   claude_code_setup
   creating_tasks
   monitoring_progress

Overview
--------

PM Agent is designed to coordinate autonomous AI workers to complete software development tasks. This guide will help you:

* Understand how PM Agent works
* Set up your preferred task management provider
* Configure Claude Desktop or Claude Code for worker agents
* Create effective tasks that AI agents can complete
* Monitor progress and handle blockers

Getting Started
---------------

If you're new to PM Agent, we recommend reading these sections in order:

1. :doc:`concepts` - Understand the core concepts and workflow
2. :doc:`providers` - Choose your task management system (GitHub, Linear, or Planka)
3. :doc:`claude_desktop_setup` or :doc:`claude_code_setup` - Set up your AI workers
4. :doc:`creating_tasks` - Learn to write tasks AI agents can understand

Key Concepts
------------

**Worker Agents**
   AI agents (like Claude) that register with PM Agent and complete tasks

**Task Assignment**
   PM Agent intelligently matches tasks to workers based on skills and priorities

**Progress Tracking**
   Real-time updates as workers complete tasks, visible on your kanban board

**Blocker Resolution**
   When workers get stuck, PM Agent provides AI-powered assistance

Next Steps
----------

* Follow the :doc:`/tutorials/demo_guide` to see PM Agent in action
* Check out :doc:`/templates/index` for project templates
* Read :doc:`/reference/troubleshooting` if you encounter issues