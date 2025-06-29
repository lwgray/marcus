MCP Tools Reference
===================

This page provides detailed information about all MCP tools available in Marcus.

Overview
--------

Marcus exposes 8 MCP tools that agents can use to interact with the project management system:

* **register_agent** - Register a new agent with the system
* **request_next_task** - Get the next optimal task assignment
* **report_task_progress** - Update progress on a task
* **report_blocker** - Report blockers and get AI assistance
* **get_project_status** - View overall project metrics
* **get_agent_status** - Check status of a specific agent
* **list_registered_agents** - List all registered agents
* **ping** - Health check and system status

Tool Details
------------

register_agent
~~~~~~~~~~~~~~

Register a new agent with Marcus.

**Parameters:**

.. list-table::
   :widths: 20 20 20 40
   :header-rows: 1

   * - Name
     - Type
     - Required
     - Description
   * - agent_id
     - string
     - Yes
     - Unique identifier for the agent
   * - name
     - string
     - Yes
     - Display name of the agent
   * - role
     - string
     - Yes
     - Agent's role (e.g., "Backend Developer")
   * - skills
     - array[string]
     - No
     - List of agent's technical skills

**Example:**

.. code-block:: json

   {
     "agent_id": "agent-001",
     "name": "Alice Smith",
     "role": "Backend Developer",
     "skills": ["Python", "Django", "PostgreSQL"]
   }

request_next_task
~~~~~~~~~~~~~~~~~

Request the next optimal task assignment for an agent.

**Parameters:**

.. list-table::
   :widths: 20 20 20 40
   :header-rows: 1

   * - Name
     - Type
     - Required
     - Description
   * - agent_id
     - string
     - Yes
     - ID of the agent requesting a task

**Response includes:**

* Task details (ID, name, description)
* AI-generated instructions
* Priority and estimated hours
* Workspace path and security boundaries

report_task_progress
~~~~~~~~~~~~~~~~~~~~

Report progress on an assigned task.

**Parameters:**

.. list-table::
   :widths: 20 20 20 40
   :header-rows: 1

   * - Name
     - Type
     - Required
     - Description
   * - agent_id
     - string
     - Yes
     - ID of the reporting agent
   * - task_id
     - string
     - Yes
     - ID of the task being updated
   * - status
     - string
     - Yes
     - Status: "in_progress", "completed", or "blocked"
   * - progress
     - integer
     - No
     - Completion percentage (0-100)
   * - message
     - string
     - No
     - Progress update message

report_blocker
~~~~~~~~~~~~~~

Report a blocker preventing task completion.

**Parameters:**

.. list-table::
   :widths: 20 20 20 40
   :header-rows: 1

   * - Name
     - Type
     - Required
     - Description
   * - agent_id
     - string
     - Yes
     - ID of the agent reporting the blocker
   * - task_id
     - string
     - Yes
     - ID of the blocked task
   * - blocker_description
     - string
     - Yes
     - Detailed description of the blocker
   * - severity
     - string
     - No
     - Severity: "low", "medium", or "high"

**Response includes:**

* AI-generated resolution suggestions
* Estimated time to resolve
* Required resources
* Escalation recommendations

Best Practices
--------------

1. **Registration First**: Always register agents before requesting tasks
2. **Regular Updates**: Report progress at 25%, 50%, 75%, and completion
3. **Detailed Blockers**: Provide comprehensive blocker descriptions
4. **Task Completion**: Always report "completed" status when done
5. **Error Handling**: Check response success/error fields

Error Responses
---------------

All tools return structured error responses on failure:

.. code-block:: json

   {
     "success": false,
     "error": "Detailed error message",
     "tool": "tool_name",
     "arguments": {}
   }

Common errors:

* Agent not registered
* Board ID not configured
* Task not found
* AI service unavailable (falls back gracefully)