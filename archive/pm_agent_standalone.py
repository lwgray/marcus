"""
MVP Implementation - Standalone PM Agent MCP Server
Works without direct kanban connection - uses Claude as intermediary
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.config.settings import Settings


class PMAgentStandalone:
    """Standalone PM Agent - works with existing MCP setup"""
    
    def __init__(self):
        self.server = Server("pm-agent-standalone")
        self.settings = Settings()
        
        # State tracking (simplified)
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        
        # Mock task data for demo (normally from kanban)
        self.available_tasks = self._create_demo_tasks()
        
        # Register MVP tools only
        self._register_mvp_tools()
    
    def _create_demo_tasks(self) -> List[Dict]:
        """Create demo tasks for standalone operation"""
        return [
            {
                "id": "task_001",
                "name": "Implement user authentication API",
                "description": "Create FastAPI endpoints for user login, logout, and registration with JWT tokens",
                "priority": "high",
                "estimated_hours": 16,
                "labels": ["backend", "api", "authentication"],
                "status": "todo"
            },
            {
                "id": "task_002", 
                "name": "Design dashboard UI components",
                "description": "Create React components for the main dashboard including calendar view, task list, and navigation",
                "priority": "medium",
                "estimated_hours": 24,
                "labels": ["frontend", "react", "ui"],
                "status": "todo"
            },
            {
                "id": "task_003",
                "name": "Fix payment processing bug",
                "description": "Debug and fix issues with international payment processing in the billing module",
                "priority": "urgent",
                "estimated_hours": 4,
                "labels": ["backend", "bug", "payments"],
                "status": "todo"
            },
            {
                "id": "task_004",
                "name": "Implement smart scheduling algorithm",
                "description": "Develop ML-based algorithm for optimal task scheduling considering user preferences and constraints",
                "priority": "high",
                "estimated_hours": 32,
                "labels": ["ai", "algorithms", "optimization"],
                "status": "todo"
            },
            {
                "id": "task_005",
                "name": "Set up CI/CD pipeline",
                "description": "Configure automated testing and deployment pipeline using GitHub Actions",
                "priority": "medium",
                "estimated_hours": 12,
                "labels": ["devops", "ci_cd", "automation"],
                "status": "todo"
            }
        ]
    
    def _register_mvp_tools(self):
        """Register MVP tools with correct MCP format"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List all available tools"""
            return [
                Tool(
                    name="register_agent",
                    description="Register a new agent with the PM system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Unique agent identifier"},
                            "name": {"type": "string", "description": "Agent's display name"},
                            "role": {"type": "string", "description": "Agent's role (e.g., 'Backend Developer')"},
                            "skills": {
                                "type": "array", 
                                "items": {"type": "string"},
                                "description": "List of agent's skills",
                                "default": []
                            }
                        },
                        "required": ["agent_id", "name", "role"]
                    }
                ),
                Tool(
                    name="request_next_task",
                    description="Request the next optimal task assignment for an agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Agent requesting the task"}
                        },
                        "required": ["agent_id"]
                    }
                ),
                Tool(
                    name="report_task_progress",
                    description="Report progress on a task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Agent reporting progress"},
                            "task_id": {"type": "string", "description": "Task being updated"},
                            "status": {"type": "string", "description": "Task status: in_progress, completed, blocked"},
                            "progress": {"type": "integer", "description": "Progress percentage (0-100)", "default": 0},
                            "message": {"type": "string", "description": "Progress message", "default": ""}
                        },
                        "required": ["agent_id", "task_id", "status"]
                    }
                ),
                Tool(
                    name="report_blocker",
                    description="Report a blocker on a task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Agent reporting the blocker"},
                            "task_id": {"type": "string", "description": "Blocked task ID"},
                            "blocker_description": {"type": "string", "description": "Description of the blocker"},
                            "severity": {"type": "string", "description": "Blocker severity: low, medium, high", "default": "medium"}
                        },
                        "required": ["agent_id", "task_id", "blocker_description"]
                    }
                ),
                Tool(
                    name="get_project_status",
                    description="Get current project status and metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_agent_status",
                    description="Get status and current assignment for an agent",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "description": "Agent to check status for"}
                        },
                        "required": ["agent_id"]
                    }
                ),
                Tool(
                    name="list_registered_agents",
                    description="List all registered agents",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="list_available_tasks",
                    description="List all available tasks for assignment",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls"""
            try:
                if name == "register_agent":
                    result = await self._register_agent(
                        arguments.get("agent_id"),
                        arguments.get("name"),
                        arguments.get("role"),
                        arguments.get("skills", [])
                    )
                    
                elif name == "request_next_task":
                    result = await self._request_next_task(
                        arguments.get("agent_id")
                    )
                    
                elif name == "report_task_progress":
                    result = await self._report_task_progress(
                        arguments.get("agent_id"),
                        arguments.get("task_id"),
                        arguments.get("status"),
                        arguments.get("progress", 0),
                        arguments.get("message", "")
                    )
                    
                elif name == "report_blocker":
                    result = await self._report_blocker(
                        arguments.get("agent_id"),
                        arguments.get("task_id"),
                        arguments.get("blocker_description"),
                        arguments.get("severity", "medium")
                    )
                    
                elif name == "get_project_status":
                    result = await self._get_project_status()
                    
                elif name == "get_agent_status":
                    result = await self._get_agent_status(
                        arguments.get("agent_id")
                    )
                    
                elif name == "list_registered_agents":
                    result = await self._list_registered_agents()
                    
                elif name == "list_available_tasks":
                    result = await self._list_available_tasks()
                    
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                error_result = {
                    "error": str(e),
                    "tool": name,
                    "arguments": arguments
                }
                return [TextContent(
                    type="text", 
                    text=json.dumps(error_result, indent=2)
                )]
    
    async def _register_agent(self, agent_id: str, name: str, role: str, skills: List[str]) -> dict:
        """Register a new agent"""
        try:
            if not agent_id or not name or not role:
                return {
                    "success": False,
                    "error": "agent_id, name, and role are required"
                }
            
            if skills is None:
                skills = []
            
            self.agent_status[agent_id] = WorkerStatus(
                worker_id=agent_id,
                name=name,
                role=role,
                email=f"{agent_id}@company.com",
                current_tasks=[],
                completed_tasks_count=0,
                capacity=40,
                skills=skills,
                availability={
                    "monday": True, "tuesday": True, "wednesday": True,
                    "thursday": True, "friday": True
                },
                performance_score=1.0
            )
            
            return {
                "success": True,
                "message": f"Agent {agent_id} registered successfully",
                "agent_data": {
                    "id": agent_id,
                    "name": name,
                    "role": role,
                    "skills": skills
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _request_next_task(self, agent_id: str) -> dict:
        """Request next optimal task for agent"""
        try:
            # Check if agent is registered
            if agent_id not in self.agent_status:
                return {
                    "has_task": False,
                    "error": f"Agent {agent_id} not registered. Please register first."
                }
            
            # Check if agent already has a task
            if agent_id in self.agent_tasks:
                current_task = self.agent_tasks[agent_id]
                return {
                    "has_task": True,
                    "message": f"Agent already has assigned task: {current_task.task_id}",
                    "current_assignment": {
                        "task_id": current_task.task_id,
                        "task_name": current_task.task_name,
                        "assigned_at": current_task.assigned_at.isoformat()
                    }
                }
            
            # Get available tasks
            available_tasks = [t for t in self.available_tasks if t["status"] == "todo"]
            
            if not available_tasks:
                return {
                    "has_task": False,
                    "message": "No tasks available at this time"
                }
            
            # Simple task selection (highest priority)
            priority_map = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
            optimal_task = max(available_tasks, 
                             key=lambda t: priority_map.get(t["priority"], 1))
            
            # Generate instructions
            instructions = self._generate_instructions(optimal_task, self.agent_status[agent_id])
            
            # Create assignment
            assignment = TaskAssignment(
                task_id=optimal_task["id"],
                task_name=optimal_task["name"],
                description=optimal_task["description"],
                instructions=instructions,
                estimated_hours=optimal_task["estimated_hours"],
                priority=Priority(optimal_task["priority"]),
                dependencies=[],
                assigned_to=agent_id,
                assigned_at=datetime.now(),
                due_date=None
            )
            
            # Track assignment and mark task as assigned
            self.agent_tasks[agent_id] = assignment
            optimal_task["status"] = "assigned"
            optimal_task["assigned_to"] = agent_id
            optimal_task["assigned_at"] = datetime.now().isoformat()
            
            return {
                "has_task": True,
                "assignment": {
                    "task_id": assignment.task_id,
                    "task_name": assignment.task_name,
                    "description": assignment.description,
                    "instructions": assignment.instructions,
                    "priority": assignment.priority.value,
                    "estimated_hours": assignment.estimated_hours,
                    "labels": optimal_task.get("labels", [])
                }
            }
            
        except Exception as e:
            return {
                "has_task": False,
                "error": str(e)
            }
    
    async def _report_task_progress(self, agent_id: str, task_id: str, status: str, progress: int, message: str) -> dict:
        """Report task progress"""
        try:
            # Find the task
            task = None
            for t in self.available_tasks:
                if t["id"] == task_id:
                    task = t
                    break
            
            if not task:
                return {
                    "acknowledged": False,
                    "error": f"Task {task_id} not found"
                }
            
            # Update task status
            timestamp = datetime.now().isoformat()
            
            if status == "completed":
                task["status"] = "completed"
                task["completed_at"] = timestamp
                task["completion_message"] = message
                
                # Clear agent's current task
                if agent_id in self.agent_tasks:
                    del self.agent_tasks[agent_id]
                
                # Update agent's completed count
                if agent_id in self.agent_status:
                    self.agent_status[agent_id].completed_tasks_count += 1
                
            elif status == "blocked":
                task["status"] = "blocked"
                task["blocked_at"] = timestamp
                task["blocked_reason"] = message
                
            elif status == "in_progress":
                task["status"] = "in_progress"
                task["progress"] = progress
                task["last_update"] = timestamp
                task["last_message"] = message
            
            # Add to progress history
            if "progress_history" not in task:
                task["progress_history"] = []
            
            task["progress_history"].append({
                "timestamp": timestamp,
                "agent_id": agent_id,
                "status": status,
                "progress": progress,
                "message": message
            })
            
            return {
                "acknowledged": True,
                "status": "progress_recorded",
                "message": f"Progress updated for task {task_id}",
                "task_status": task["status"]
            }
            
        except Exception as e:
            return {
                "acknowledged": False,
                "error": str(e)
            }
    
    async def _report_blocker(self, agent_id: str, task_id: str, blocker_description: str, severity: str) -> dict:
        """Report a blocker"""
        try:
            # Find the task
            task = None
            for t in self.available_tasks:
                if t["id"] == task_id:
                    task = t
                    break
            
            if not task:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found"
                }
            
            # Update task with blocker info
            task["status"] = "blocked"
            task["blocker"] = {
                "description": blocker_description,
                "severity": severity,
                "reported_by": agent_id,
                "reported_at": datetime.now().isoformat()
            }
            
            # Generate resolution suggestions
            resolution_suggestions = self._generate_resolution_suggestions(blocker_description, severity)
            
            return {
                "success": True,
                "message": "Blocker reported successfully",
                "resolution_suggestions": resolution_suggestions,
                "blocker_id": f"blocker_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_project_status(self) -> dict:
        """Get project status overview"""
        try:
            total_tasks = len(self.available_tasks)
            completed_tasks = len([t for t in self.available_tasks if t["status"] == "completed"])
            in_progress_tasks = len([t for t in self.available_tasks if t["status"] == "in_progress"])
            blocked_tasks = len([t for t in self.available_tasks if t["status"] == "blocked"])
            todo_tasks = len([t for t in self.available_tasks if t["status"] == "todo"])
            
            completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            return {
                "success": True,
                "project_status": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "in_progress_tasks": in_progress_tasks,
                    "blocked_tasks": blocked_tasks,
                    "todo_tasks": todo_tasks,
                    "completion_percentage": round(completion_percentage, 1),
                    "active_agents": len(self.agent_status),
                    "assigned_tasks": len(self.agent_tasks)
                },
                "health_status": "green" if completion_percentage > 70 else "yellow" if completion_percentage > 30 else "red"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_agent_status(self, agent_id: str) -> dict:
        """Get agent status"""
        try:
            if agent_id not in self.agent_status:
                return {
                    "found": False,
                    "message": f"Agent {agent_id} not registered"
                }
            
            agent = self.agent_status[agent_id]
            current_task = self.agent_tasks.get(agent_id)
            
            return {
                "found": True,
                "agent_info": {
                    "id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "skills": agent.skills,
                    "completed_tasks": agent.completed_tasks_count,
                    "current_task": {
                        "task_id": current_task.task_id,
                        "task_name": current_task.task_name,
                        "assigned_at": current_task.assigned_at.isoformat()
                    } if current_task else None
                }
            }
            
        except Exception as e:
            return {
                "found": False,
                "error": str(e)
            }
    
    async def _list_registered_agents(self) -> dict:
        """List all registered agents"""
        try:
            agents = []
            for agent_id, agent in self.agent_status.items():
                current_task = self.agent_tasks.get(agent_id)
                agents.append({
                    "id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "skills": agent.skills,
                    "completed_tasks": agent.completed_tasks_count,
                    "has_current_task": current_task is not None,
                    "current_task_id": current_task.task_id if current_task else None
                })
            
            return {
                "success": True,
                "agent_count": len(agents),
                "agents": agents
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _list_available_tasks(self) -> dict:
        """List all available tasks"""
        try:
            return {
                "success": True,
                "task_count": len(self.available_tasks),
                "tasks": self.available_tasks
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_instructions(self, task: dict, agent: WorkerStatus) -> str:
        """Generate task instructions"""
        agent_skills = ", ".join(agent.skills) if agent.skills else "general development"
        
        return f"""## Task Assignment for {agent.name}

**Task:** {task['name']}

**Description:** {task['description']}

**Priority:** {task['priority'].upper()}

**Estimated Time:** {task['estimated_hours']} hours

**Your Skills:** {agent_skills}

### Objectives:
Complete this task according to the requirements described above.

### Recommended Approach:
1. **Analysis:** Review the task requirements carefully
2. **Planning:** Break down the work into manageable steps  
3. **Implementation:** Execute according to best practices for your role
4. **Testing:** Validate your work thoroughly
5. **Documentation:** Update any necessary documentation

### Definition of Done:
- All requirements in the description are satisfied
- Work is tested and ready for review
- Code follows team standards and best practices
- Any necessary documentation is updated

### Labels/Categories:
{', '.join(task.get('labels', []))}

### Need Help?
- Use `report_blocker` if you encounter any blockers
- Ask for clarification if requirements are unclear
- Report progress regularly using `report_task_progress`

---
*Generated by PM Agent MVP - Standalone Mode*"""
    
    def _generate_resolution_suggestions(self, blocker_description: str, severity: str) -> List[str]:
        """Generate blocker resolution suggestions"""
        suggestions = [
            "Review the blocker description carefully and identify the root cause",
            "Check documentation and existing resources for similar issues",
            "Consult with team lead or subject matter expert",
        ]
        
        if "test" in blocker_description.lower():
            suggestions.extend([
                "Review test configuration and dependencies",
                "Check test data and mock setups",
                "Verify test environment consistency"
            ])
        elif "api" in blocker_description.lower():
            suggestions.extend([
                "Check API documentation and endpoint specifications",
                "Verify authentication and permissions",
                "Test API endpoints with proper tools (Postman, curl)"
            ])
        elif "database" in blocker_description.lower():
            suggestions.extend([
                "Check database connection and credentials",
                "Verify database schema and migrations",
                "Review database permissions and access rights"
            ])
        else:
            suggestions.extend([
                "Break down the problem into smaller components",
                "Research similar issues in documentation or forums",
                "Create a minimal reproduction case"
            ])
        
        if severity in ["high", "urgent"]:
            suggestions.insert(1, "Escalate immediately to team lead due to high severity")
        
        return suggestions
    
    async def start(self):
        """Start the standalone PM Agent server"""
        try:
            print("🚀 Starting PM Agent MVP - Standalone Mode...")
            print("✅ No external dependencies required")
            print("🎯 PM Agent MVP is ready!")
            print("📋 Available tools:")
            print("   - register_agent")
            print("   - request_next_task") 
            print("   - report_task_progress")
            print("   - report_blocker")
            print("   - get_project_status")
            print("   - get_agent_status")
            print("   - list_registered_agents")
            print("   - list_available_tasks")
            print(f"📊 Demo project loaded with {len(self.available_tasks)} tasks")
            print("\n🔗 Add this to your Claude MCP config to connect worker agents!")
            
            # Start MCP server
            await self.server.run()
            
        except Exception as e:
            print(f"❌ Failed to start PM Agent MVP: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    agent = PMAgentStandalone()
    asyncio.run(agent.start())
