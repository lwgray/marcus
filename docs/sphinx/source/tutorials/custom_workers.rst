Creating Custom Workers
=======================

Learn how to build AI worker agents that integrate with PM Agent.

Overview
--------

This tutorial shows you how to create custom worker agents that can:

* Register with PM Agent
* Request and complete tasks
* Report progress
* Handle blockers
* Collaborate with other workers

Prerequisites
-------------

* Python 3.8+ installed
* PM Agent running and accessible
* Basic Python knowledge
* Understanding of async programming (helpful)

Basic Worker Structure
----------------------

Every worker needs these components:

1. **MCP Client** - Connects to PM Agent
2. **Registration** - Declares capabilities
3. **Work Loop** - Continuously seeks tasks
4. **Task Execution** - Does the actual work
5. **Progress Reporting** - Updates PM Agent

Simple Worker Example
---------------------

Let's create a basic documentation worker:

.. code-block:: python

   import asyncio
   import json
   from datetime import datetime
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client

   class DocumentationWorker:
       def __init__(self):
           self.agent_id = "doc-worker-001"
           self.name = "Documentation Worker"
           self.role = "Documentation Specialist"
           self.skills = ["documentation", "markdown", "api-docs", "tutorials"]
           
       async def start(self):
           """Main entry point for the worker"""
           # Configure connection to PM Agent
           server_params = StdioServerParameters(
               command="python",
               args=["pm_agent_mcp_server.py"]
           )
           
           # Connect to PM Agent
           async with stdio_client(server_params) as (read, write):
               async with ClientSession(read, write) as session:
                   await session.initialize()
                   
                   # Register with PM Agent
                   await self.register(session)
                   
                   # Start work loop
                   while True:
                       await self.work_cycle(session)
                       await asyncio.sleep(30)  # Rest between cycles

       async def register(self, session):
           """Register this worker with PM Agent"""
           result = await session.call_tool("register_agent", {
               "agent_id": self.agent_id,
               "name": self.name,
               "role": self.role,
               "skills": self.skills
           })
           
           response = json.loads(result.content[0].text)
           if response.get("success"):
               print(f"✅ Registered as {self.name}")
           else:
               raise Exception(f"Registration failed: {response}")

       async def work_cycle(self, session):
           """Request and complete a task"""
           # Request next task
           result = await session.call_tool("request_next_task", {
               "agent_id": self.agent_id
           })
           
           response = json.loads(result.content[0].text)
           
           if not response.get("has_task"):
               print("💤 No tasks available, waiting...")
               return
               
           # Extract task information
           task = response["assignment"]
           task_id = task["task_id"]
           
           print(f"📋 Received task: {task['task_name']}")
           
           # Start working
           await self.report_progress(session, task_id, 0, "Starting documentation task")
           
           try:
               # Simulate work
               await self.execute_task(session, task)
               
               # Report completion
               await self.report_progress(session, task_id, 100, "Documentation completed", "completed")
               
           except Exception as e:
               # Report blocker if something goes wrong
               await self.report_blocker(session, task_id, str(e))

       async def execute_task(self, session, task):
           """Execute the documentation task"""
           # Simulate different documentation tasks
           if "api" in task["task_name"].lower():
               await self.document_api(session, task)
           elif "tutorial" in task["task_name"].lower():
               await self.write_tutorial(session, task)
           else:
               await self.general_documentation(session, task)

       async def document_api(self, session, task):
           """Handle API documentation tasks"""
           task_id = task["task_id"]
           
           # Progress: Analyzing code
           await self.report_progress(session, task_id, 25, "Analyzing API endpoints")
           await asyncio.sleep(2)  # Simulate work
           
           # Progress: Generating docs
           await self.report_progress(session, task_id, 50, "Generating OpenAPI documentation")
           await asyncio.sleep(2)
           
           # Progress: Creating examples
           await self.report_progress(session, task_id, 75, "Adding code examples")
           await asyncio.sleep(2)
           
           print("📝 API documentation completed")

       async def report_progress(self, session, task_id, progress, message, status="in_progress"):
           """Report task progress to PM Agent"""
           await session.call_tool("report_task_progress", {
               "agent_id": self.agent_id,
               "task_id": task_id,
               "status": status,
               "progress": progress,
               "message": message
           })

       async def report_blocker(self, session, task_id, description):
           """Report a blocker to PM Agent"""
           result = await session.call_tool("report_blocker", {
               "agent_id": self.agent_id,
               "task_id": task_id,
               "blocker_description": description,
               "severity": "medium"
           })
           
           response = json.loads(result.content[0].text)
           if response.get("resolution_suggestion"):
               print(f"💡 Suggestion: {response['resolution_suggestion']}")

   # Run the worker
   if __name__ == "__main__":
       worker = DocumentationWorker()
       asyncio.run(worker.start())

Advanced Worker Features
------------------------

Skill-Based Task Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~

Make your worker smarter about which tasks to accept:

.. code-block:: python

   async def should_accept_task(self, task):
       """Decide if this worker should handle the task"""
       task_words = set(task["task_name"].lower().split())
       skill_words = set(word.lower() for skill in self.skills for word in skill.split("-"))
       
       # Calculate match score
       match_score = len(task_words.intersection(skill_words))
       
       # Check if we have required skills
       if "required_skills" in task:
           required = set(task["required_skills"])
           our_skills = set(self.skills)
           if not required.issubset(our_skills):
               return False
       
       return match_score > 0

Handling Complex Tasks
~~~~~~~~~~~~~~~~~~~~~~

For tasks that require multiple steps:

.. code-block:: python

   async def execute_complex_task(self, session, task):
       """Execute a multi-step task with checkpoints"""
       task_id = task["task_id"]
       steps = self.plan_task_steps(task)
       
       for i, step in enumerate(steps):
           try:
               # Report step progress
               progress = int((i / len(steps)) * 100)
               await self.report_progress(
                   session, 
                   task_id, 
                   progress, 
                   f"Step {i+1}/{len(steps)}: {step['description']}"
               )
               
               # Execute step
               await step['function'](session, task)
               
               # Checkpoint - save progress
               self.save_checkpoint(task_id, i)
               
           except Exception as e:
               # Try to recover from checkpoint
               if self.can_recover(task_id, i):
                   await self.recover_from_checkpoint(task_id, i)
               else:
                   await self.report_blocker(session, task_id, f"Failed at step {i+1}: {str(e)}")
                   raise

Collaboration Between Workers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Share information between workers:

.. code-block:: python

   async def share_work_artifact(self, session, task_id, artifact_type, data):
       """Share work artifacts for other workers"""
       # This would integrate with a shared storage system
       # For now, we'll add it to our progress message
       
       message = f"Created {artifact_type}: {data['description']}"
       if "location" in data:
           message += f" at {data['location']}"
       
       await self.report_progress(
           session,
           task_id,
           self.current_progress,
           message
       )

   # Example usage:
   await self.share_work_artifact(session, task_id, "api_spec", {
       "description": "OpenAPI specification",
       "location": "docs/api/openapi.yaml",
       "version": "3.0.0"
   })

Error Recovery
~~~~~~~~~~~~~~

Implement robust error handling:

.. code-block:: python

   async def work_cycle_with_recovery(self, session):
       """Work cycle with error recovery"""
       max_retries = 3
       retry_count = 0
       
       while retry_count < max_retries:
           try:
               await self.work_cycle(session)
               retry_count = 0  # Reset on success
               break
               
           except ConnectionError as e:
               retry_count += 1
               wait_time = retry_count * 60  # Exponential backoff
               print(f"⚠️ Connection error, retry {retry_count}/{max_retries} in {wait_time}s")
               await asyncio.sleep(wait_time)
               
           except Exception as e:
               print(f"❌ Unexpected error: {e}")
               await asyncio.sleep(300)  # Wait 5 minutes
               break

Specialized Worker Examples
---------------------------

Testing Worker
~~~~~~~~~~~~~~

.. code-block:: python

   class TestingWorker:
       def __init__(self):
           self.agent_id = "test-worker-001"
           self.name = "Testing Specialist"
           self.role = "QA Engineer"
           self.skills = ["testing", "pytest", "jest", "selenium", "unit-testing", "integration-testing"]
       
       async def run_tests(self, session, task):
           """Execute testing based on task type"""
           task_id = task["task_id"]
           
           if "unit" in task["task_name"].lower():
               await self.run_unit_tests(session, task_id)
           elif "integration" in task["task_name"].lower():
               await self.run_integration_tests(session, task_id)
           elif "e2e" in task["task_name"].lower():
               await self.run_e2e_tests(session, task_id)
               
       async def run_unit_tests(self, session, task_id):
           """Run unit tests and report results"""
           await self.report_progress(session, task_id, 25, "Setting up test environment")
           
           # Simulate running tests
           test_results = {
               "total": 45,
               "passed": 43,
               "failed": 2,
               "skipped": 0
           }
           
           await self.report_progress(
               session, 
               task_id, 
               75, 
               f"Tests complete: {test_results['passed']}/{test_results['total']} passed"
           )
           
           if test_results["failed"] > 0:
               # Report failures as blockers
               await self.report_blocker(
                   session,
                   task_id,
                   f"{test_results['failed']} tests failed. Need fixes before proceeding."
               )

DevOps Worker
~~~~~~~~~~~~~

.. code-block:: python

   class DevOpsWorker:
       def __init__(self):
           self.agent_id = "devops-worker-001"
           self.name = "DevOps Engineer"
           self.role = "DevOps Specialist"
           self.skills = ["docker", "kubernetes", "ci/cd", "aws", "terraform", "monitoring"]
       
       async def handle_deployment(self, session, task):
           """Handle deployment tasks"""
           task_id = task["task_id"]
           
           # Check prerequisites
           if not await self.check_prerequisites(session, task):
               await self.report_blocker(
                   session,
                   task_id,
                   "Prerequisites not met: Tests must pass before deployment"
               )
               return
           
           # Deployment steps
           await self.report_progress(session, task_id, 20, "Building Docker images")
           await asyncio.sleep(3)
           
           await self.report_progress(session, task_id, 40, "Running security scans")
           await asyncio.sleep(2)
           
           await self.report_progress(session, task_id, 60, "Deploying to staging")
           await asyncio.sleep(3)
           
           await self.report_progress(session, task_id, 80, "Running smoke tests")
           await asyncio.sleep(2)
           
           await self.report_progress(session, task_id, 100, "Deployment completed", "completed")

Integration with Claude
-----------------------

Create a Claude-compatible worker:

.. code-block:: python

   CLAUDE_WORKER_SYSTEM_PROMPT = """
   You are an autonomous AI worker connected to PM Agent.
   
   Your identity:
   - Agent ID: {agent_id}
   - Role: {role}
   - Skills: {skills}
   
   Available tools:
   - register_agent: Register with PM Agent (do once)
   - request_next_task: Get assigned work
   - report_task_progress: Update task status
   - report_blocker: Report issues
   
   Workflow:
   1. Register yourself first
   2. Request tasks continuously
   3. Complete work using your skills
   4. Report progress regularly
   5. Handle blockers intelligently
   
   Important: Always include agent_id in all tool calls.
   """

   # Configure Claude with this prompt
   system_prompt = CLAUDE_WORKER_SYSTEM_PROMPT.format(
       agent_id="claude-dev-001",
       role="Full Stack Developer",
       skills=["python", "javascript", "react", "fastapi", "postgresql"]
   )

Testing Your Worker
-------------------

Unit Test Example
~~~~~~~~~~~~~~~~~

.. code-block:: python

   import pytest
   from unittest.mock import AsyncMock, MagicMock
   
   @pytest.mark.asyncio
   async def test_worker_registration():
       # Create mock session
       mock_session = AsyncMock()
       mock_session.call_tool.return_value = MagicMock(
           content=[MagicMock(text='{"success": true, "message": "Registered"}')]
       )
       
       # Create worker
       worker = DocumentationWorker()
       
       # Test registration
       await worker.register(mock_session)
       
       # Verify call
       mock_session.call_tool.assert_called_once_with("register_agent", {
           "agent_id": "doc-worker-001",
           "name": "Documentation Worker",
           "role": "Documentation Specialist",
           "skills": ["documentation", "markdown", "api-docs", "tutorials"]
       })

Integration Test
~~~~~~~~~~~~~~~~

.. code-block:: python

   @pytest.mark.asyncio
   async def test_full_work_cycle():
       # Start PM Agent in test mode
       pm_agent = PMAgent(test_mode=True)
       pm_agent_task = asyncio.create_task(pm_agent.run())
       
       # Create and start worker
       worker = DocumentationWorker()
       worker_task = asyncio.create_task(worker.start())
       
       # Let it run for one cycle
       await asyncio.sleep(60)
       
       # Check that worker completed a task
       assert worker.completed_tasks > 0
       
       # Cleanup
       worker_task.cancel()
       pm_agent_task.cancel()

Deployment
----------

Docker Container
~~~~~~~~~~~~~~~~

.. code-block:: dockerfile

   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   
   COPY worker.py .
   
   ENV AGENT_ID=${AGENT_ID:-worker-001}
   ENV PM_AGENT_URL=${PM_AGENT_URL:-localhost:8000}
   
   CMD ["python", "worker.py"]

Docker Compose
~~~~~~~~~~~~~~

.. code-block:: yaml

   version: '3.8'
   services:
     doc-worker:
       build: ./workers/documentation
       environment:
         - AGENT_ID=doc-worker-001
         - PM_AGENT_URL=pm-agent:8000
       depends_on:
         - pm-agent
         
     test-worker:
       build: ./workers/testing
       environment:
         - AGENT_ID=test-worker-001
         - PM_AGENT_URL=pm-agent:8000
       depends_on:
         - pm-agent

Best Practices
--------------

1. **Clear Identity**
   - Use descriptive agent IDs
   - Accurate skill declarations
   - Specific role definitions

2. **Robust Error Handling**
   - Catch and report all errors
   - Implement retry logic
   - Save progress checkpoints

3. **Regular Reporting**
   - Update progress frequently
   - Include meaningful messages
   - Report completion promptly

4. **Resource Management**
   - Clean up after tasks
   - Monitor memory usage
   - Implement graceful shutdown

5. **Testing**
   - Unit test core functions
   - Integration test with PM Agent
   - Simulate error conditions

Next Steps
----------

* Build a worker for your specific needs
* Deploy multiple workers for parallel execution
* Create specialized workers for your tech stack
* Share your workers with the community!