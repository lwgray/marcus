# Building Worker Agents for PM Agent

This guide explains how to build AI worker agents that integrate with PM Agent for autonomous software development.

## Worker Agent Architecture

### Core Requirements
1. **MCP Client**: Ability to connect to PM Agent's MCP server
2. **Autonomous Loop**: Continuous task-seeking behavior
3. **Skill Declaration**: Clear capabilities for task matching
4. **Progress Reporting**: Regular updates on task status

### Basic Worker Structure
```python
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class WorkerAgent:
    def __init__(self, agent_id: str, name: str, role: str, skills: list):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.skills = skills
        self.pm_agent_params = StdioServerParameters(
            command="python",
            args=["pm_agent_mvp_fixed.py"]
        )
    
    async def run(self):
        """Main autonomous loop"""
        async with stdio_client(self.pm_agent_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Check PM Agent health
                await self._check_health(session)
                
                # Register with PM Agent
                await self._register(session)
                
                # Continuous work loop
                while True:
                    await self._work_cycle(session)
                    await asyncio.sleep(30)  # Brief pause between cycles
    
    async def _check_health(self, session):
        """Check PM Agent connectivity and health"""
        result = await session.call_tool("ping", {"echo": f"Hello from {self.agent_id}"})
        response = json.loads(result.content[0].text)
        
        if not response.get("pong"):
            raise ConnectionError("PM Agent not responding to ping")
        
        print(f"✅ Connected to {response.get('service')} v{response.get('version')}")
        print(f"   Uptime: {response.get('uptime')}")
        return response
```

## Example Worker Agents

### 1. Backend Developer Agent
```python
class BackendDeveloperAgent(WorkerAgent):
    def __init__(self):
        super().__init__(
            agent_id="backend_dev_1",
            name="Backend Developer Agent",
            role="Backend Developer",
            skills=["python", "fastapi", "postgresql", "redis", "docker"]
        )
        
    async def _work_cycle(self, session):
        # Request task
        result = await session.call_tool("request_next_task", {
            "agent_id": self.agent_id
        })
        
        if not result.get("has_task"):
            return
            
        task = result["assignment"]
        task_id = task["task_id"]
        
        try:
            # Report starting
            await session.call_tool("report_task_progress", {
                "agent_id": self.agent_id,
                "task_id": task_id,
                "status": "in_progress",
                "progress": 0,
                "message": "Starting backend development task"
            })
            
            # Execute based on task type
            if "api" in task["task_name"].lower():
                await self._implement_api(task, session)
            elif "database" in task["task_name"].lower():
                await self._implement_database(task, session)
            else:
                await self._generic_backend_task(task, session)
                
            # Report completion
            await session.call_tool("report_task_progress", {
                "agent_id": self.agent_id,
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "message": "Backend task completed successfully"
            })
            
        except Exception as e:
            # Report blocker
            await session.call_tool("report_blocker", {
                "agent_id": self.agent_id,
                "task_id": task_id,
                "blocker_description": str(e),
                "severity": "high"
            })
```

### 2. Frontend Developer Agent
```python
class FrontendDeveloperAgent(WorkerAgent):
    def __init__(self):
        super().__init__(
            agent_id="frontend_dev_1",
            name="Frontend Developer Agent",
            role="Frontend Developer",
            skills=["javascript", "react", "typescript", "css", "html"]
        )
    
    async def _implement_ui_component(self, task, session):
        task_id = task["task_id"]
        
        # Parse instructions
        instructions = task["instructions"]
        
        # Step 1: Create component structure
        await session.call_tool("report_task_progress", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "status": "in_progress",
            "progress": 25,
            "message": "Creating React component structure"
        })
        
        # Simulate component creation
        await asyncio.sleep(2)
        
        # Step 2: Implement functionality
        await session.call_tool("report_task_progress", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "status": "in_progress",
            "progress": 50,
            "message": "Implementing component logic and state management"
        })
        
        # Step 3: Add styling
        await session.call_tool("report_task_progress", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "status": "in_progress",
            "progress": 75,
            "message": "Adding responsive styles and animations"
        })
        
        # Step 4: Testing
        await session.call_tool("report_task_progress", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "status": "in_progress",
            "progress": 90,
            "message": "Testing component in different scenarios"
        })
```

### 3. DevOps Agent
```python
class DevOpsAgent(WorkerAgent):
    def __init__(self):
        super().__init__(
            agent_id="devops_1",
            name="DevOps Agent",
            role="DevOps Engineer",
            skills=["docker", "kubernetes", "aws", "terraform", "ci/cd"]
        )
    
    async def _handle_deployment_task(self, task, session):
        # Check for dependencies (e.g., backend must be ready)
        if "deploy" in task["task_name"].lower():
            # Could check if backend/frontend tasks are complete
            project_status = await session.call_tool("get_project_status", {})
            
            # Implement deployment logic
            # ...
```

### 4. Testing Agent
```python
class TestingAgent(WorkerAgent):
    def __init__(self):
        super().__init__(
            agent_id="tester_1",
            name="Testing Agent",
            role="QA Engineer",
            skills=["pytest", "jest", "selenium", "api-testing", "performance-testing"]
        )
    
    async def _run_test_suite(self, task, session):
        task_id = task["task_id"]
        
        # Determine test type from task
        if "unit" in task["task_name"].lower():
            test_type = "unit"
        elif "integration" in task["task_name"].lower():
            test_type = "integration"
        elif "e2e" in task["task_name"].lower():
            test_type = "e2e"
        else:
            test_type = "general"
        
        # Run appropriate tests
        await session.call_tool("report_task_progress", {
            "agent_id": self.agent_id,
            "task_id": task_id,
            "status": "in_progress",
            "progress": 50,
            "message": f"Running {test_type} tests"
        })
```

## Advanced Worker Features

### 1. Intelligent Task Selection
```python
async def _should_accept_task(self, task):
    """Decide if agent should work on this task"""
    # Check skill match
    task_skills = set(word.lower() for word in task["task_name"].split())
    agent_skills = set(skill.lower() for skill in self.skills)
    
    skill_match = len(task_skills.intersection(agent_skills))
    
    # Check current workload
    status = await session.call_tool("get_agent_status", {
        "agent_id": self.agent_id
    })
    
    # Accept if good match and not overloaded
    return skill_match > 0 and not status.get("current_task")
```

### 2. Collaborative Handoffs
```python
async def _check_handoff_needed(self, task, session):
    """Check if task should be handed to another agent"""
    if "frontend" in task["description"] and self.role == "Backend Developer":
        # Find available frontend developer
        agents = await session.call_tool("list_registered_agents", {})
        
        for agent in agents["agents"]:
            if agent["role"] == "Frontend Developer" and not agent["has_current_task"]:
                # In future: handoff_task tool
                await session.call_tool("report_task_progress", {
                    "agent_id": self.agent_id,
                    "task_id": task["task_id"],
                    "status": "completed",
                    "progress": 100,
                    "message": f"Backend complete. Ready for frontend by {agent['id']}"
                })
                return True
    return False
```

### 3. Learning from Blockers
```python
class LearningAgent(WorkerAgent):
    def __init__(self):
        super().__init__(...)
        self.known_solutions = {}
    
    async def _handle_blocker(self, blocker_desc, session):
        # Check if we've seen this before
        for pattern, solution in self.known_solutions.items():
            if pattern in blocker_desc:
                return solution
        
        # Get AI suggestion
        result = await session.call_tool("report_blocker", {
            "agent_id": self.agent_id,
            "task_id": self.current_task_id,
            "blocker_description": blocker_desc,
            "severity": "medium"
        })
        
        # Learn from response
        if result.get("resolution_suggestion"):
            self.known_solutions[blocker_desc[:50]] = result["resolution_suggestion"]
        
        return result.get("resolution_suggestion")
```

## Integration with Claude

### Claude Worker Agent Template
```python
CLAUDE_WORKER_PROMPT = """You are an autonomous software development agent integrated with PM Agent.

Your capabilities:
- Role: {role}
- Skills: {skills}
- Agent ID: {agent_id}

Available PM Agent tools:
- register_agent: Register yourself (do this first)
- request_next_task: Get your next assignment
- report_task_progress: Update task status
- report_blocker: Report issues needing help
- get_project_status: Check overall project health
- get_agent_status: Check your current assignment

Workflow:
1. Register yourself using register_agent
2. Continuously request tasks using request_next_task
3. Work on assigned tasks autonomously
4. Report progress every 10-15 minutes
5. Report blockers when stuck
6. Mark tasks complete when done
7. Immediately request the next task

Important:
- Always include your agent_id in tool calls
- Provide detailed progress messages
- Complete tasks fully before requesting new ones
- Report blockers with clear descriptions
"""

# Usage with Claude
agent_prompt = CLAUDE_WORKER_PROMPT.format(
    role="Full Stack Developer",
    skills=["python", "react", "docker"],
    agent_id="claude_fullstack_1"
)
```

## Best Practices

### 1. Registration
- Use descriptive agent IDs
- Accurate skill declaration improves task matching
- Include version info in agent name

### 2. Task Execution
- Break large tasks into reportable steps
- Report progress at meaningful milestones
- Include specific details in progress messages

### 3. Error Handling
```python
async def safe_work_cycle(self, session):
    try:
        await self._work_cycle(session)
    except McpError as e:
        # MCP-specific errors
        logger.error(f"MCP Error: {e}")
        await asyncio.sleep(60)  # Back off
    except Exception as e:
        # General errors - report as blocker
        if hasattr(self, 'current_task_id'):
            await session.call_tool("report_blocker", {
                "agent_id": self.agent_id,
                "task_id": self.current_task_id,
                "blocker_description": f"Unexpected error: {str(e)}",
                "severity": "high"
            })
```

### 4. Resource Management
- Implement graceful shutdown
- Clean up resources between tasks
- Monitor memory usage for long-running agents

## Testing Your Worker Agent

### Unit Test Example
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_worker_registration():
    # Mock PM Agent session
    mock_session = AsyncMock()
    mock_session.call_tool.return_value = {
        "success": True,
        "message": "Agent registered successfully"
    }
    
    # Create worker
    worker = BackendDeveloperAgent()
    
    # Test registration
    await worker._register(mock_session)
    
    # Verify registration call
    mock_session.call_tool.assert_called_with("register_agent", {
        "agent_id": "backend_dev_1",
        "name": "Backend Developer Agent",
        "role": "Backend Developer",
        "skills": ["python", "fastapi", "postgresql", "redis", "docker"]
    })
```

### Integration Test
```python
async def test_worker_full_cycle():
    # Start PM Agent
    pm_agent = PMAgentMVP()
    pm_agent_task = asyncio.create_task(pm_agent.start())
    
    # Start worker
    worker = TestWorkerAgent()
    worker_task = asyncio.create_task(worker.run())
    
    # Let it run for a bit
    await asyncio.sleep(30)
    
    # Check that worker got and completed a task
    # ...
```

## Deployment Considerations

### 1. Containerization
```dockerfile
# Dockerfile for worker agent
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY worker_agent.py .

ENV AGENT_ID=${AGENT_ID}
ENV PM_AGENT_URL=${PM_AGENT_URL}

CMD ["python", "worker_agent.py"]
```

### 2. Scaling Workers
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend_worker_1:
    build: .
    environment:
      - AGENT_ID=backend_1
      - AGENT_ROLE=Backend Developer
      
  backend_worker_2:
    build: .
    environment:
      - AGENT_ID=backend_2
      - AGENT_ROLE=Backend Developer
      
  frontend_worker:
    build: .
    environment:
      - AGENT_ID=frontend_1
      - AGENT_ROLE=Frontend Developer
```

### 3. Monitoring
- Log all task assignments and completions
- Track success/failure rates
- Monitor agent utilization
- Alert on repeated blockers