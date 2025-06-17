"""
MVP Implementation - Fixed PM Agent MCP Server
Corrected MCP tool registration and error handling.
"""

import asyncio
import json
import os
import psutil
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import mcp.types as types

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.integrations.mcp_kanban_client_simple import SimpleMCPKanbanClient as MCPKanbanClient
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.config.settings import Settings
from src.core.workspace_manager import WorkspaceManager


class PMAgentMVP:
    """MVP Version: AI Project Manager Agent MCP Server - Fixed"""
    
    def __init__(self):
        self.server = Server("pm-agent-mvp")
        self.settings = Settings()
        
        # Core components (simplified)
        self.kanban_client = MCPKanbanClient()
        self.ai_engine = AIAnalysisEngine()
        self.workspace_manager = WorkspaceManager()
        
        # State tracking (simplified)
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        
        # Track start time for uptime calculation
        self._start_time = time.time()
        
        # Register MVP tools only
        self._register_mvp_tools()
    
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
                    name="ping",
                    description="Check PM Agent status and connectivity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "echo": {"type": "string", "description": "Optional message to echo back", "default": ""}
                        },
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
                    
                elif name == "ping":
                    result = await self._ping(
                        arguments.get("echo", "")
                    )
                    
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
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
        """MVP: Simple agent registration"""
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
                capacity=40,  # Default 40 hours/week
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
        """MVP: Simplified task assignment"""
        try:
            # Check if agent is registered
            if agent_id not in self.agent_status:
                return {
                    "has_task": False,
                    "error": f"Agent {agent_id} not registered. Please register first."
                }
            
            # Get available tasks (simplified)
            available_tasks = await self.kanban_client.get_available_tasks()
            
            if not available_tasks:
                return {
                    "has_task": False,
                    "message": "No tasks available at this time"
                }
            
            # MVP: Simple task selection (highest priority)
            priority_map = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
            optimal_task = max(available_tasks, 
                             key=lambda t: priority_map.get(t.priority.value, 1))
            
            # Generate basic instructions
            instructions = await self._generate_basic_instructions(optimal_task)
            
            # Get workspace assignment data
            workspace_data = self.workspace_manager.get_task_assignment_data(agent_id)
            
            # Create assignment
            assignment = TaskAssignment(
                task_id=optimal_task.id,
                task_name=optimal_task.name,
                description=optimal_task.description,
                instructions=instructions,
                estimated_hours=optimal_task.estimated_hours,
                priority=optimal_task.priority,
                dependencies=optimal_task.dependencies,
                assigned_to=agent_id,
                assigned_at=datetime.now(),
                due_date=optimal_task.due_date,
                workspace_path=workspace_data['workspace_path'],
                forbidden_paths=workspace_data['forbidden_paths']
            )
            
            # Track assignment
            self.agent_tasks[agent_id] = assignment
            
            # Update kanban board
            await self.kanban_client.assign_task(optimal_task.id, agent_id)
            
            return {
                "has_task": True,
                "assignment": {
                    "task_id": assignment.task_id,
                    "task_name": assignment.task_name,
                    "description": assignment.description,
                    "instructions": assignment.instructions,
                    "priority": assignment.priority.value,
                    "estimated_hours": assignment.estimated_hours,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "workspace_path": assignment.workspace_path,
                    "forbidden_paths": assignment.forbidden_paths
                }
            }
            
        except Exception as e:
            return {
                "has_task": False,
                "error": str(e)
            }
    
    async def _report_task_progress(self, agent_id: str, task_id: str, status: str, progress: int, message: str) -> dict:
        """MVP: Simple progress reporting"""
        try:
            # Add progress comment to kanban
            progress_comment = f"🤖 {agent_id}: {message}"
            if progress > 0:
                progress_comment += f" ({progress}% complete)"
            
            await self.kanban_client.add_comment(task_id, progress_comment)
            
            # Handle completion
            if status == "completed":
                await self.kanban_client.complete_task(task_id)
                
                # Clear agent's current task
                if agent_id in self.agent_tasks:
                    del self.agent_tasks[agent_id]
                
                # Update agent's completed count
                if agent_id in self.agent_status:
                    self.agent_status[agent_id].completed_tasks_count += 1
            
            # Handle blocked status
            elif status == "blocked":
                await self.kanban_client.update_task_status(task_id, "blocked")
            
            return {
                "acknowledged": True,
                "status": "progress_recorded",
                "message": f"Progress updated for task {task_id}"
            }
            
        except Exception as e:
            return {
                "acknowledged": False,
                "error": str(e)
            }
    
    async def _report_blocker(self, agent_id: str, task_id: str, blocker_description: str, severity: str) -> dict:
        """MVP: Simple blocker reporting"""
        try:
            # Add blocker comment to kanban
            blocker_comment = f"""🚧 BLOCKER reported by {agent_id}
            
**Description:** {blocker_description}
**Severity:** {severity}
**Reported:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

This task is now blocked and requires attention."""
            
            await self.kanban_client.add_comment(task_id, blocker_comment)
            
            # Update task status to blocked
            await self.kanban_client.update_task_status(task_id, "blocked")
            
            # Simple AI analysis (basic)
            resolution_suggestion = await self._get_basic_resolution(blocker_description)
            
            return {
                "success": True,
                "message": "Blocker reported successfully",
                "resolution_suggestion": resolution_suggestion
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_project_status(self) -> dict:
        """MVP: Basic project overview"""
        try:
            # Get board summary
            summary = await self.kanban_client.get_board_summary()
            
            # Basic statistics
            stats = summary.get("stats", {})
            
            return {
                "success": True,
                "project_status": {
                    "total_cards": stats.get("totalCards", 0),
                    "completion_percentage": stats.get("completionPercentage", 0),
                    "in_progress_count": stats.get("inProgressCount", 0),
                    "done_count": stats.get("doneCount", 0),
                    "urgent_count": stats.get("urgentCount", 0),
                    "bug_count": stats.get("bugCount", 0)
                },
                "board_info": {
                    "board_id": self.kanban_client.board_id,
                    "project_id": self.kanban_client.project_id
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_agent_status(self, agent_id: str) -> dict:
        """MVP: Get agent information"""
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
        """MVP: List all registered agents"""
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
    
    async def _generate_basic_instructions(self, task: Task) -> str:
        """MVP: Generate simple instructions using AI"""
        try:
            basic_prompt = f"""Generate clear, actionable instructions for this task:

Task: {task.name}
Description: {task.description}
Priority: {task.priority.value}
Labels: {', '.join(task.labels) if task.labels else 'None'}

Provide:
1. Clear objective
2. Key steps to complete the task
3. Definition of done
4. Any important considerations

Keep it concise and practical."""
            
            instructions = await self.ai_engine._call_claude(basic_prompt)
            return instructions
            
        except Exception as e:
            # Fallback instructions
            return f"""Task: {task.name}

Description: {task.description}

Priority: {task.priority.value}

Please complete this task according to the description. If you need clarification or encounter any blockers, please report them immediately.

Definition of Done: Task is complete when all requirements in the description are satisfied and the work is ready for review."""
    
    async def _get_basic_resolution(self, blocker_description: str) -> str:
        """MVP: Get basic blocker resolution suggestion"""
        try:
            prompt = f"""A team member has reported this blocker:

"{blocker_description}"

Provide 3-5 concrete steps to resolve this blocker. Be specific and actionable."""
            
            resolution = await self.ai_engine._call_claude(prompt)
            return resolution
            
        except Exception as e:
            return """Basic resolution steps:
1. Review the blocker description carefully
2. Identify who can help resolve this issue
3. Gather any necessary information or resources
4. Escalate to team lead if needed
5. Document the resolution once complete"""
    
    def _get_uptime(self) -> str:
        """Calculate uptime since PM Agent started"""
        if hasattr(self, '_start_time'):
            uptime_seconds = int(time.time() - self._start_time)
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            return f"{hours}h {minutes}m {seconds}s"
        return "unknown"
    
    def _get_memory_usage(self) -> dict:
        """Get current memory usage of the PM Agent process"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return {
                "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                "percent": round(process.memory_percent(), 2)
            }
        except:
            return {"rss_mb": 0, "percent": 0}
    
    async def _ping(self, echo: str = "") -> dict:
        """Handle ping requests to check PM Agent status"""
        try:
            # Basic PM Agent health status
            status = {
                "status": "online",
                "service": "PM Agent MVP",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "uptime": self._get_uptime() if hasattr(self, '_start_time') else "unknown",
                "health": {
                    "status": "healthy",
                    "ai_engine": "available" if self.ai_engine else "unavailable",
                    "memory_usage": self._get_memory_usage()
                },
                "capabilities": {
                    "agent_registration": True,
                    "task_assignment": True,
                    "progress_tracking": True,
                    "blocker_resolution": True,
                    "ai_assistance": bool(self.ai_engine)
                },
                "workload": {
                    "registered_agents": len(self.agent_status),
                    "active_assignments": len(self.agent_tasks),
                    "total_completed_tasks": sum(agent.completed_tasks_count for agent in self.agent_status.values()),
                    "agents_available": len([a for a in self.agent_status.values() if a.worker_id not in self.agent_tasks])
                }
            }
            
            # Add echo message if provided
            if echo:
                status["echo"] = echo
                status["echo_received"] = True
            
            return {
                "success": True,
                "pong": True,
                **status
            }
            
        except Exception as e:
            return {
                "success": False,
                "pong": False,
                "error": str(e),
                "status": "error",
                "service": "PM Agent MVP"
            }
    
    async def initialize(self):
        """Initialize PM Agent components"""
        try:
            # Initialize components
            print("🚀 Starting PM Agent MVP...", file=sys.stderr)
            
            # Note: With the refactored client, we don't keep a persistent connection
            # Each operation will create its own connection context
            print("✅ PM Agent ready to connect to Kanban on demand", file=sys.stderr)
            
            # Initialize AI engine
            print("🤖 Initializing AI engine...", file=sys.stderr)
            await self.ai_engine.initialize()
            print("✅ AI engine ready", file=sys.stderr)
            
            print("🎯 PM Agent MVP is ready!", file=sys.stderr)
            print("📋 Available tools:", file=sys.stderr)
            print("   - ping", file=sys.stderr)
            print("   - register_agent", file=sys.stderr)
            print("   - request_next_task", file=sys.stderr) 
            print("   - report_task_progress", file=sys.stderr)
            print("   - report_blocker", file=sys.stderr)
            print("   - get_project_status", file=sys.stderr)
            print("   - get_agent_status", file=sys.stderr)
            print("   - list_registered_agents", file=sys.stderr)
            
        except Exception as e:
            print(f"❌ Failed to initialize PM Agent MVP: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise


async def main():
    """Main entry point for stdio server"""
    agent = PMAgentMVP()
    await agent.initialize()
    
    # Run as stdio server
    async with stdio_server() as (read_stream, write_stream):
        await agent.server.run(
            read_stream,
            write_stream,
            agent.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
