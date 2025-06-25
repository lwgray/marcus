Monitoring Progress
===================

Learn how to track your project's progress and understand what your AI workers are doing.

Overview
--------

Marcus provides multiple ways to monitor your autonomous development team:

* **Kanban Board** - Real-time task status updates
* **Conversation Logs** - Detailed agent communications
* **Visualization UI** - Interactive data flow visualization
* **Metrics and Analytics** - Project health indicators

Using Your Kanban Board
-----------------------

GitHub Issues
~~~~~~~~~~~~~

When using GitHub as your provider:

1. **Task Movement**
   
   * ``Backlog`` → ``In Progress`` - When agent starts work
   * ``In Progress`` → ``Review`` - When agent completes task
   * ``Review`` → ``Done`` - After human verification

2. **Progress Comments**
   
   Agents automatically add comments::
   
      🤖 Marcus: Task assigned to claude-backend-001
      ⏳ Progress: 25% - Setting up project structure
      ⏳ Progress: 50% - Implementing core functionality
      ⏳ Progress: 75% - Adding tests and documentation
      ✅ Progress: 100% - Task completed successfully

3. **Labels**
   
   * ``assigned`` - Task is assigned to an agent
   * ``in-progress`` - Active work happening
   * ``blocked`` - Agent encountered an issue
   * ``completed`` - Work finished

Linear
~~~~~~

Linear users will see:

* Automatic status updates
* Progress percentage in task metadata
* Comments with detailed progress
* Time tracking information

Planka
~~~~~~

For local Planka boards:

* Cards move between lists automatically
* Progress shown in card description
* Color coding for task status
* Agent assignments visible on cards

Understanding Conversation Logs
-------------------------------

Location
~~~~~~~~

Logs are stored in ``logs/conversations/`` with timestamps:

* ``pm_agent_conversation_YYYYMMDD_HHMMSS.log``
* ``pm_agent_conversation.log`` (latest)

Log Structure
~~~~~~~~~~~~~

Each log entry shows the three-way conversation::

   === Worker → Marcus ===
   🤖 Claude Backend Dev: Requesting next task
   Skills: ['python', 'fastapi', 'postgresql']
   
   === Marcus Processing ===
   🧠 Thinking: Finding best match for agent skills
   📋 Decision: Assign task 'Create user API endpoints'
   Reason: Skill match score: 0.95
   
   === Marcus → Kanban Board ===
   🔌 Query: Get available tasks from backlog
   📋 Response: Found 5 available tasks
   
   === Marcus → Worker ===
   ✅ Task Assignment: Create user API endpoints
   Instructions: [Detailed instructions...]

Reading Progress Updates
~~~~~~~~~~~~~~~~~~~~~~~~

Progress updates show:

* **Percentage** - How much is complete
* **Current Activity** - What the agent is doing
* **Files Modified** - What's being changed
* **Next Steps** - What comes next

Example::

   === Worker → Marcus ===
   📊 Progress Update:
   Task ID: task-123
   Status: in_progress
   Progress: 50%
   Message: Completed database models and migrations.
            Now implementing API endpoints.
   Files created:
   - src/models/user.py
   - migrations/001_create_users_table.sql

Handling Blockers
~~~~~~~~~~~~~~~~~

When agents encounter issues::

   === Worker → Marcus ===
   🚫 Blocker Report:
   Task ID: task-123
   Severity: high
   Issue: Cannot connect to PostgreSQL database
   Tried: Checking connection string, verifying credentials
   
   === Marcus → Worker ===
   💡 Suggested Resolution:
   1. Verify PostgreSQL is running: docker ps
   2. Check DATABASE_URL in .env file
   3. Try connecting manually: psql $DATABASE_URL
   4. Ensure migrations have run

Using the Visualization UI
--------------------------

Starting the Visualization
~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Start Marcus with logging::

      python pm_agent_mcp_server_logged.py

2. Start visualization server::

      python run_visualization.py

3. Open browser to ``http://localhost:8080``

Understanding the Display
~~~~~~~~~~~~~~~~~~~~~~~~~

**Node Types:**

* **Marcus (Purple)** - Central coordinator
* **Workers (Blue)** - Active AI agents
* **Kanban (Green)** - Task board
* **Decisions (Orange)** - Decision points
* **Knowledge (Red)** - Shared knowledge base

**Connection Animation:**

* Solid lines - Established connections
* Dashed animated - Active data flow
* Color intensity - Message frequency

**Metrics Panel:**

* Active workers count
* Tasks in progress
* Decision confidence trends
* System performance metrics

Filtering Events
~~~~~~~~~~~~~~~~

Use the filter panel to focus on:

* Worker registrations
* Task assignments
* Progress updates
* Blocker reports
* Decision making

Metrics and Analytics
---------------------

Project Health Indicators
~~~~~~~~~~~~~~~~~~~~~~~~~

Check project status using the API::

   GET /api/project/status
   
   Response:
   {
     "total_tasks": 45,
     "completed": 30,
     "in_progress": 8,
     "blocked": 2,
     "completion_rate": 66.7,
     "average_task_time": "4.5 hours",
     "blocker_rate": 4.4
   }

Worker Performance
~~~~~~~~~~~~~~~~~~

Monitor individual agent performance::

   GET /api/agent/status?agent_id=claude-backend-001
   
   Response:
   {
     "completed_tasks": 15,
     "average_completion_time": "3.2 hours",
     "blocker_frequency": 0.13,
     "skill_utilization": {
       "python": 0.9,
       "fastapi": 0.7,
       "postgresql": 0.5
     }
   }

Common Patterns to Watch For
----------------------------

Healthy Project Signs
~~~~~~~~~~~~~~~~~~~~~

* Steady task completion rate
* Low blocker frequency (<10%)
* Good skill utilization (>70%)
* Regular progress updates
* Tasks completing within estimates

Warning Signs
~~~~~~~~~~~~~

* High blocker rate (>20%)
* Tasks taking much longer than estimated
* Agents frequently idle
* Same blockers recurring
* Poor skill matches

Debugging Issues
----------------

When Tasks Aren't Progressing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Check Agent Registration**::

      grep "register_agent" logs/conversations/pm_agent_conversation.log

2. **Verify Task Assignment**::

      grep "request_next_task" logs/conversations/pm_agent_conversation.log

3. **Look for Blockers**::

      grep -A5 "blocker" logs/conversations/pm_agent_conversation.log

4. **Check Kanban Connection**::

      grep "Kanban Board" logs/conversations/pm_agent_conversation.log

When Agents Are Idle
~~~~~~~~~~~~~~~~~~~~

* Verify tasks exist in backlog
* Check task labels match agent skills
* Ensure priorities are set
* Look for dependency chains

Best Practices
--------------

1. **Regular Monitoring**
   
   * Check progress every few hours
   * Review blockers promptly
   * Verify task completion quality

2. **Log Analysis**
   
   * Keep recent logs for debugging
   * Archive old logs periodically
   * Use grep for quick searches

3. **Proactive Intervention**
   
   * Add clarification when agents seem stuck
   * Break down tasks that take too long
   * Update task descriptions based on blockers

4. **Performance Optimization**
   
   * Adjust task sizes based on completion times
   * Improve task descriptions for fewer blockers
   * Balance workload across agents

Command Line Monitoring
-----------------------

Quick status check::

   # See active workers
   docker-compose logs pm-agent | grep "Worker registered" | tail -10
   
   # Check recent assignments
   docker-compose logs pm-agent | grep "Task assigned" | tail -10
   
   # Monitor blockers
   docker-compose logs pm-agent | grep -B2 -A2 "blocker" | tail -20
   
   # Watch real-time activity
   docker-compose logs -f pm-agent | grep -E "(assigned|progress|completed)"

Next Steps
----------

* Set up :doc:`/developer/visualization` for advanced monitoring
* Review :doc:`/reference/troubleshooting` for common issues
* Read :doc:`/tutorials/demo_guide` to see monitoring in action