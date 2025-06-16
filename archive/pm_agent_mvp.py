"""
MVP Implementation - Simplified PM Agent MCP Server
Focuses on core functionality only, removes complex features.
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
from src.integrations.mcp_kanban_client import MCPKanbanClient
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.config.settings import Settings


class PMAgentMVP:
    """MVP Version: AI Project Manager Agent MCP Server - Simplified"""
    
    def __init__(self):
        self.server = Server("pm-agent-mvp")
        self.settings = Settings()
        
        # Core components (simplified)
        self.kanban_client = MCPKanbanClient()
        self.ai_engine = AIAnalysisEngine()
        
        # State tracking (simplified)
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        
        # Register MVP tools only
        self._register_mvp_tools()
    
    def _register_mvp_tools(self):
        """Register MVP tools only - simplified feature set"""
        
        @self.server.tool()
        async def register_agent(
            agent_id: str,
            name: str,
            role: str,
            skills: List[str] = None
        ) -> dict:
            """MVP: Simple agent registration"""
            try:
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
        
        @self.server.tool()
        async def request_next_task(agent_id: str) -> dict:
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
                    due_date=optimal_task.due_date
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
                        "due_date": assignment.due_date.isoformat() if assignment.due_date else None
                    }
                }
                
            except Exception as e:
                return {
                    "has_task": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def report_task_progress(
            agent_id: str,
            task_id: str,
            status: str,
            progress: int = 0,
            message: str = ""
        ) -> dict:
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
        
        @self.server.tool()
        async def report_blocker(
            agent_id: str,
            task_id: str,
            blocker_description: str,
            severity: str = "medium"
        ) -> dict:
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
        
        @self.server.tool()
        async def get_project_status() -> dict:
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
        
        @self.server.tool()
        async def get_agent_status(agent_id: str) -> dict:
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
        
        @self.server.tool()
        async def list_registered_agents() -> dict:
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
    
    async def start(self):
        """Start the MVP PM Agent server"""
        try:
            # Initialize components
            print("🚀 Starting PM Agent MVP...")
            
            # Connect to kanban
            print("🔗 Connecting to kanban MCP server...")
            await self.kanban_client.connect()
            print(f"✅ Connected to board: {self.kanban_client.board_id}")
            
            # Initialize AI engine
            print("🤖 Initializing AI engine...")
            await self.ai_engine.initialize()
            print("✅ AI engine ready")
            
            print("🎯 PM Agent MVP is ready!")
            print("📋 Available tools:")
            print("   - register_agent")
            print("   - request_next_task") 
            print("   - report_task_progress")
            print("   - report_blocker")
            print("   - get_project_status")
            print("   - get_agent_status")
            print("   - list_registered_agents")
            
            # Start MCP server
            await self.server.run()
            
        except Exception as e:
            print(f"❌ Failed to start PM Agent MVP: {e}")
            raise


if __name__ == "__main__":
    agent = PMAgentMVP()
    asyncio.run(agent.start())
