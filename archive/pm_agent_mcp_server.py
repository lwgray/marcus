import asyncio
import json
import logging
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
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pm_agent_conversation.log')
    ]
)


class PMAgentServer:
    """AI Project Manager Agent MCP Server"""
    
    def __init__(self):
        self.server = Server("pm-agent")
        self.settings = Settings()
        
        # Core components
        self.kanban_client = MCPKanbanClient()
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.tool()
        async def request_next_task(agent_id: str) -> dict:
            """Agents call this to request their next optimal task"""
            try:
                # Get current project state
                await self._refresh_project_state()
                
                # Find optimal task for this agent
                optimal_task = await self._find_optimal_task_for_agent(agent_id)
                
                if optimal_task:
                    # Generate detailed instructions using AI
                    instructions = await self.ai_engine.generate_task_instructions(
                        optimal_task, 
                        self.agent_status.get(agent_id)
                    )
                    
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
                    
                    # Send notifications
                    await self.comm_hub.notify_task_assignment(agent_id, assignment)
                    
                    return {
                        "has_task": True,
                        "assignment": assignment.__dict__
                    }
                else:
                    return {
                        "has_task": False,
                        "message": "No suitable tasks available at this time"
                    }
                    
            except Exception as e:
                return {
                    "has_task": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def report_task_progress(
            self,
            agent_id: str,
            task_id: str,
            status: str,
            progress: int,
            message: str
        ) -> dict:
            """Agents report their task progress"""
            try:
                # Add progress update to kanban
                await self.kanban_client.add_comment(
                    task_id,
                    f"🤖 {agent_id}: {message} ({progress}% complete)"
                )
                
                # Handle different statuses
                if status == "completed":
                    await self._handle_task_completion(agent_id, task_id)
                elif status == "blocked":
                    await self._handle_agent_blocked(agent_id, task_id, message)
                elif status == "clarification_needed":
                    await self._handle_clarification_request(agent_id, task_id, message)
                else:
                    # Just a progress update
                    await self.kanban_client.update_task_progress(task_id, progress)
                
                return {"acknowledged": True, "status": "progress_recorded"}
                
            except Exception as e:
                return {"acknowledged": False, "error": str(e)}
        
        @self.server.tool()
        async def get_task_clarification(
            self,
            agent_id: str,
            task_id: str,
            question: str
        ) -> dict:
            """Agents ask questions about their tasks"""
            try:
                # Get task details
                task = await self.kanban_client.get_task_details(task_id)
                
                # Use AI to provide clarification
                clarification = await self.ai_engine.generate_clarification(
                    task, question, agent_id
                )
                
                # Document Q&A in kanban
                await self.kanban_client.add_comment(
                    task_id,
                    f"❓ **Question from {agent_id}:** {question}\n\n"
                    f"💡 **PM Agent Response:** {clarification}"
                )
                
                return {
                    "success": True,
                    "clarification": clarification
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def report_blocker(
            self,
            agent_id: str,
            task_id: str,
            blocker_description: str,
            severity: str = "medium"
        ) -> dict:
            """Agents report blockers they encounter"""
            try:
                # Analyze blocker and determine resolution strategy
                resolution_plan = await self.ai_engine.analyze_blocker(
                    task_id, blocker_description, severity
                )
                
                # Create blocker resolution task if needed
                if resolution_plan.get("needs_coordination"):
                    await self._create_blocker_resolution_task(
                        task_id, blocker_description, resolution_plan
                    )
                
                # Update task status
                await self.kanban_client.update_task_status(task_id, "blocked")
                
                # Notify relevant parties
                await self.comm_hub.notify_blocker(
                    agent_id, task_id, blocker_description, resolution_plan
                )
                
                return {
                    "success": True,
                    "resolution_plan": resolution_plan
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def get_agent_status(self, agent_id: str) -> dict:
            """Get current status and assignments for an agent"""
            try:
                status = self.agent_status.get(agent_id)
                current_task = self.agent_tasks.get(agent_id)
                
                return {
                    "agent_id": agent_id,
                    "status": status.__dict__ if status else "not_registered",
                    "current_task": current_task.__dict__ if current_task else None
                }
                
            except Exception as e:
                return {"error": str(e)}
    
    async def _refresh_project_state(self):
        """Refresh the current project state from kanban board"""
        self.project_state = await self.monitor.get_project_state()
    
    async def _find_optimal_task_for_agent(self, agent_id: str) -> Optional[Task]:
        """Find the best task for an agent based on skills, capacity, and priorities"""
        # Get available tasks
        available_tasks = await self.kanban_client.get_available_tasks()
        
        # Get agent capabilities
        agent = self.agent_status.get(agent_id)
        if not agent:
            return None
        
        # Use AI to find optimal match
        optimal_task = await self.ai_engine.match_task_to_agent(
            available_tasks, agent, self.project_state
        )
        
        return optimal_task
    
    async def _handle_task_completion(self, agent_id: str, task_id: str):
        """Handle when an agent completes a task"""
        # Update task status
        await self.kanban_client.complete_task(task_id)
        
        # Clear agent's current task
        if agent_id in self.agent_tasks:
            del self.agent_tasks[agent_id]
        
        # Update agent's completed count
        if agent_id in self.agent_status:
            self.agent_status[agent_id].completed_tasks_count += 1
        
        # Check for dependent tasks
        await self._check_and_unblock_dependencies(task_id)
    
    async def _handle_agent_blocked(self, agent_id: str, task_id: str, message: str):
        """Handle when an agent is blocked"""
        # Create blocker in tracking system
        blocker = await self.monitor.record_blocker(agent_id, task_id, message)
        
        # Analyze and attempt resolution
        resolution = await self.ai_engine.suggest_blocker_resolution(blocker)
        
        # Notify relevant parties
        await self.comm_hub.escalate_blocker(blocker, resolution)
    
    async def _handle_clarification_request(self, agent_id: str, task_id: str, message: str):
        """Handle clarification requests from agents"""
        # Log the request
        await self.kanban_client.add_comment(
            task_id,
            f"❓ {agent_id} needs clarification: {message}"
        )
        
        # Generate AI response
        clarification = await self.ai_engine.generate_clarification(
            task_id, message, agent_id
        )
        
        # Send response to agent
        await self.comm_hub.send_clarification(agent_id, clarification)
    
    async def _create_blocker_resolution_task(
        self, 
        blocked_task_id: str, 
        blocker_description: str, 
        resolution_plan: dict
    ):
        """Create a new task to resolve a blocker"""
        resolution_task = await self.kanban_client.create_task({
            "name": f"Resolve blocker for {blocked_task_id}",
            "description": blocker_description,
            "priority": "high",
            "labels": ["blocker", "urgent"],
            "estimated_hours": resolution_plan.get("estimated_hours", 2)
        })
        
        # Link to blocked task
        await self.kanban_client.add_dependency(blocked_task_id, resolution_task.id)
    
    async def _check_and_unblock_dependencies(self, completed_task_id: str):
        """Check if any tasks were waiting on this one"""
        dependent_tasks = await self.kanban_client.get_dependent_tasks(completed_task_id)
        
        for task in dependent_tasks:
            # Check if all dependencies are now complete
            if await self._are_all_dependencies_complete(task):
                await self.kanban_client.update_task_status(task.id, "ready")
                await self.comm_hub.notify_task_unblocked(task)
    
    async def _are_all_dependencies_complete(self, task: Task) -> bool:
        """Check if all task dependencies are complete"""
        for dep_id in task.dependencies:
            dep_task = await self.kanban_client.get_task_details(dep_id)
            if dep_task.status != TaskStatus.DONE:
                return False
        return True
    
    async def start(self):
        """Start the PM Agent server"""
        # Initialize components
        await self.kanban_client.connect()
        await self.ai_engine.initialize()
        
        # Start monitoring loop
        asyncio.create_task(self.monitor.start_monitoring())
        
        # Start MCP server
        await self.server.run()


if __name__ == "__main__":
    agent = PMAgentServer()
    asyncio.run(agent.start())
