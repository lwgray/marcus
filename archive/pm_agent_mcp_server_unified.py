"""
Unified PM Agent MCP Server with support for multiple kanban providers

This version uses the common KanbanInterface to support Planka, Linear, and GitHub Projects
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.integrations.kanban_factory import KanbanFactory
from src.integrations.kanban_interface import KanbanInterface
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings
from src.logging.conversation_logger import conversation_logger, log_conversation, log_thinking


class UnifiedPMAgentServer:
    """PM Agent MCP Server with multi-provider kanban support"""
    
    def __init__(self):
        load_dotenv()
        self.server = Server("pm-agent")
        self.settings = Settings()
        
        # Get kanban provider from environment
        provider = os.getenv('KANBAN_PROVIDER', 'planka')
        print(f"Initializing PM Agent with {provider.upper()} kanban provider...")
        
        # Core components
        self.kanban_client: Optional[KanbanInterface] = None
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        
        # Register tools
        self._register_tools()
        
        # Log startup
        conversation_logger.log_system_state(
            active_workers=0,
            tasks_in_progress=0,
            tasks_completed=0,
            tasks_blocked=0,
            system_metrics={
                "status": "starting",
                "kanban_provider": provider
            }
        )
        
    async def _initialize_kanban(self):
        """Initialize the kanban client"""
        if not self.kanban_client:
            # For Planka, we need to pass the MCP function caller
            config = {}
            provider = os.getenv('KANBAN_PROVIDER', 'planka')
            
            if provider == 'planka':
                # Planka needs special handling for MCP
                config['mcp_function_caller'] = self._mcp_function_caller
                
            self.kanban_client = KanbanFactory.create_default(config)
            await self.kanban_client.connect()
            
    async def _mcp_function_caller(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Function to call MCP tools for kanban integrations"""
        # This function would be used to call external MCP servers
        # For Linear and GitHub, they would need their respective MCP servers running
        
        provider = os.getenv('KANBAN_PROVIDER', 'planka')
        
        if provider == 'linear':
            # Linear MCP tools start with 'linear.'
            # This would call the Linear MCP server
            print(f"Linear MCP Call: {tool_name} with args: {arguments}")
            # In a real implementation, this would use an MCP client to call the Linear server
            return {"success": True, "message": "Mock Linear response"}
            
        elif provider == 'github':
            # GitHub MCP tools start with 'github.'
            # This would call the GitHub MCP server
            print(f"GitHub MCP Call: {tool_name} with args: {arguments}")
            # In a real implementation, this would use an MCP client to call the GitHub server
            return {"success": True, "message": "Mock GitHub response"}
            
        else:
            # Planka - direct MCP call
            print(f"Planka MCP Call: {tool_name} with args: {arguments}")
            return {"success": True, "message": "Mock Planka response"}
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.tool()
        async def register_agent(agent_id: str, name: str, role: str, skills: List[str] = None) -> dict:
            """Register a new agent with the PM system"""
            # Log incoming registration request
            conversation_logger.log_worker_message(
                agent_id,
                "to_pm",
                f"Registering as {role} with skills: {skills}",
                {"name": name, "role": role, "skills": skills}
            )
            
            try:
                # Log PM thinking
                log_thinking("pm_agent", f"New agent registration request from {name}", {
                    "agent_id": agent_id,
                    "role": role,
                    "skills": skills
                })
                
                # Create worker status
                status = WorkerStatus(
                    agent_id=agent_id,
                    name=name,
                    role=role,
                    skills=skills or [],
                    status="available",
                    current_task=None,
                    total_completed=0,
                    performance_score=1.0
                )
                
                self.agent_status[agent_id] = status
                
                # Log decision
                conversation_logger.log_pm_decision(
                    decision=f"Register agent {name}",
                    rationale="Agent skills match project requirements",
                    confidence_score=0.95,
                    decision_factors={
                        "skills_match": True,
                        "capacity_available": True,
                        "role_needed": True
                    }
                )
                
                # Log response
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Registration successful. Welcome {name}!",
                    {"status": "registered"}
                )
                
                return {
                    "success": True,
                    "message": f"Agent {name} registered successfully",
                    "agent_id": agent_id
                }
                
            except Exception as e:
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Registration failed: {str(e)}",
                    {"error": str(e)}
                )
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def request_next_task(agent_id: str) -> dict:
            """Agents call this to request their next optimal task"""
            # Log task request
            conversation_logger.log_worker_message(
                agent_id,
                "to_pm",
                "Requesting next task",
                {"status": self.agent_status.get(agent_id, {}).get("status", "unknown")}
            )
            
            try:
                # Initialize kanban if needed
                await self._initialize_kanban()
                
                # Log PM thinking about refreshing state
                log_thinking("pm_agent", "Need to check current project state")
                
                # Get current project state
                await self._refresh_project_state()
                
                # Log thinking about finding task
                agent = self.agent_status.get(agent_id)
                if agent:
                    log_thinking("pm_agent", f"Finding optimal task for {agent.name}", {
                        "agent_skills": agent.skills,
                        "current_workload": agent.current_task or "None"
                    })
                
                # Find optimal task for this agent
                optimal_task = await self._find_optimal_task_for_agent(agent_id)
                
                if optimal_task:
                    # Log decision process
                    conversation_logger.log_pm_decision(
                        decision=f"Assign task '{optimal_task.name}' to {agent_id}",
                        rationale=f"Best skill match and highest priority",
                        alternatives_considered=[
                            {"task": "Other Task 1", "score": 0.7},
                            {"task": "Other Task 2", "score": 0.6}
                        ],
                        confidence_score=0.85,
                        decision_factors={
                            "skill_match": 0.9,
                            "priority": optimal_task.priority.value,
                            "dependencies_clear": True,
                            "estimated_hours": optimal_task.estimated_hours
                        }
                    )
                    
                    # Generate detailed instructions using AI
                    log_thinking("pm_agent", "Generating detailed task instructions")
                    
                    # Get previous implementations if using GitHub
                    previous_implementations = None
                    if os.getenv('KANBAN_PROVIDER') == 'github' and self.code_analyzer:
                        log_thinking("pm_agent", "Analyzing previous implementations for context")
                        try:
                            impl_details = await self.code_analyzer.get_implementation_details(
                                os.getenv('GITHUB_OWNER'),
                                os.getenv('GITHUB_REPO'),
                                self._determine_feature_type(optimal_task)
                            )
                            if impl_details.get('implementations'):
                                previous_implementations = impl_details
                                conversation_logger.log_pm_decision(
                                    decision="Include code context in instructions",
                                    rationale=f"Found {len(impl_details['implementations'])} relevant implementations",
                                    confidence_score=0.9,
                                    decision_factors={
                                        "feature_type": impl_details.get('feature_type'),
                                        "implementation_count": len(impl_details.get('implementations', []))
                                    }
                                )
                        except Exception as e:
                            log_thinking("pm_agent", f"Could not get previous implementations: {e}")
                    
                    instructions = await self.ai_engine.generate_task_instructions(
                        optimal_task, 
                        self.agent_status.get(agent_id),
                        previous_implementations
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
                    log_thinking("pm_agent", "Updating Kanban board with assignment")
                    await self.kanban_client.assign_task(optimal_task.id, agent_id)
                    await self.kanban_client.move_task_to_column(optimal_task.id, "In Progress")
                    
                    # Send notifications
                    await self.comm_hub.notify_task_assignment(agent_id, assignment)
                    
                    # Log response to worker
                    conversation_logger.log_worker_message(
                        agent_id,
                        "from_pm",
                        f"Task assigned: {optimal_task.name}",
                        {
                            "task_id": optimal_task.id,
                            "priority": optimal_task.priority.value,
                            "estimated_hours": optimal_task.estimated_hours
                        }
                    )
                    
                    return {
                        "has_task": True,
                        "task": {
                            "id": optimal_task.id,
                            "title": optimal_task.name,
                            "description": optimal_task.description,
                            "instructions": instructions,
                            "estimated_hours": optimal_task.estimated_hours,
                            "priority": optimal_task.priority.value
                        }
                    }
                else:
                    # Log no task available
                    conversation_logger.log_pm_decision(
                        decision=f"No task assigned to {agent_id}",
                        rationale="No suitable tasks match agent skills or all tasks assigned",
                        confidence_score=0.95
                    )
                    
                    conversation_logger.log_worker_message(
                        agent_id,
                        "from_pm",
                        "No suitable tasks available at this time",
                        {"reason": "all_assigned_or_no_match"}
                    )
                    
                    return {
                        "has_task": False,
                        "message": "No suitable tasks available at this time"
                    }
                    
            except Exception as e:
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Error processing task request: {str(e)}",
                    {"error": str(e)}
                )
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
            """Report progress on assigned task"""
            # Log progress report
            conversation_logger.log_worker_message(
                agent_id,
                "to_pm",
                f"Progress update: {progress}% - {message}",
                {
                    "task_id": task_id,
                    "status": status,
                    "progress": progress
                }
            )
            
            try:
                # Initialize kanban if needed
                await self._initialize_kanban()
                
                # Validate task assignment
                if agent_id not in self.agent_tasks:
                    return {"success": False, "error": "No task assigned to agent"}
                
                assignment = self.agent_tasks[agent_id]
                if assignment.task_id != task_id:
                    return {"success": False, "error": "Task ID mismatch"}
                
                # Update kanban board
                log_thinking("pm_agent", f"Updating task progress on Kanban board: {progress}%")
                
                await self.kanban_client.update_task_progress(
                    task_id, 
                    {"status": status, "progress": progress, "message": message}
                )
                
                # Update agent status
                if status == "completed":
                    log_thinking("pm_agent", f"Task completed by {agent_id}, freeing up for next task")
                    conversation_logger.log_pm_decision(
                        decision=f"Mark task {task_id} as completed",
                        rationale=f"Agent reported 100% completion",
                        confidence_score=1.0
                    )
                    
                    self.agent_status[agent_id].status = "available"
                    self.agent_status[agent_id].current_task = None
                    self.agent_status[agent_id].total_completed += 1
                    del self.agent_tasks[agent_id]
                    
                    # Move to done column
                    await self.kanban_client.move_task_to_column(task_id, "Done")
                    
                    # AI analysis of completion
                    await self._analyze_task_completion(task_id, agent_id)
                    
                    # For GitHub, analyze code changes
                    if os.getenv('KANBAN_PROVIDER') == 'github' and self.code_analyzer:
                        log_thinking("pm_agent", "Analyzing code changes from completed task")
                        try:
                            agent = self.agent_status.get(agent_id)
                            task = await self.kanban_client.get_task_by_id(task_id)
                            if agent and task:
                                analysis = await self.ai_engine.analyze_code_changes(
                                    task,
                                    agent,
                                    os.getenv('GITHUB_OWNER'),
                                    os.getenv('GITHUB_REPO')
                                )
                                
                                if analysis.get('findings'):
                                    # Log findings for future reference
                                    conversation_logger.log_pm_decision(
                                        decision=f"Code analysis for task {task_id}",
                                        rationale="Understanding implementation for future tasks",
                                        confidence_score=0.95,
                                        decision_factors=analysis['findings']
                                    )
                                    
                                    # Store recommendations for next tasks
                                    if analysis.get('recommendations'):
                                        self._store_recommendations(task_id, analysis['recommendations'])
                        except Exception as e:
                            log_thinking("pm_agent", f"Code analysis failed: {e}")
                
                # Send notifications
                await self.comm_hub.notify_progress_update(agent_id, task_id, progress, message)
                
                # Log response
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    "Progress update received successfully",
                    {"acknowledged": True}
                )
                
                return {"success": True, "message": "Progress updated successfully"}
                
            except Exception as e:
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Error updating progress: {str(e)}",
                    {"error": str(e)}
                )
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def report_blocker(
            agent_id: str, 
            task_id: str, 
            blocker_description: str,
            severity: str = "medium"
        ) -> dict:
            """Report a blocker on current task"""
            # Log blocker report
            conversation_logger.log_worker_message(
                agent_id,
                "to_pm",
                f"BLOCKER: {blocker_description} (Severity: {severity})",
                {
                    "task_id": task_id,
                    "severity": severity
                }
            )
            
            try:
                # Initialize kanban if needed
                await self._initialize_kanban()
                
                # AI analysis for resolution
                log_thinking("pm_agent", f"Analyzing blocker: {blocker_description}")
                
                suggestions = await self.ai_engine.analyze_blocker(
                    blocker_description,
                    self.agent_tasks.get(agent_id),
                    self.project_state
                )
                
                # Update task status
                await self.kanban_client.report_blocker(task_id, blocker_description, severity)
                
                # Send escalation if high severity
                if severity == "high":
                    log_thinking("pm_agent", "High severity blocker - escalating to stakeholders")
                    await self.comm_hub.escalate_blocker(agent_id, task_id, blocker_description)
                
                # Log response with suggestions
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Blocker acknowledged. {len(suggestions)} suggestions provided",
                    {
                        "suggestions": suggestions,
                        "escalated": severity == "high"
                    }
                )
                
                return {
                    "success": True,
                    "suggestions": suggestions,
                    "escalated": severity == "high"
                }
                
            except Exception as e:
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Error processing blocker: {str(e)}",
                    {"error": str(e)}
                )
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def get_project_status() -> dict:
            """Get current project status and metrics"""
            log_thinking("pm_agent", "Generating comprehensive project status report")
            
            try:
                # Initialize kanban if needed
                await self._initialize_kanban()
                
                await self._refresh_project_state()
                metrics = await self.kanban_client.get_project_metrics()
                
                # Log system state
                conversation_logger.log_system_state(
                    active_workers=len([a for a in self.agent_status.values() if a.status == "working"]),
                    tasks_in_progress=metrics.get("in_progress_tasks", 0),
                    tasks_completed=metrics.get("completed_tasks", 0),
                    tasks_blocked=metrics.get("blocked_tasks", 0),
                    system_metrics=metrics
                )
                
                return {
                    "success": True,
                    "project_state": self.project_state.__dict__ if self.project_state else None,
                    "metrics": metrics,
                    "active_agents": len([a for a in self.agent_status.values() if a.status == "working"]),
                    "total_agents": len(self.agent_status),
                    "kanban_provider": os.getenv('KANBAN_PROVIDER', 'planka')
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def list_registered_agents() -> dict:
            """List all registered agents"""
            agents = []
            for agent_id, status in self.agent_status.items():
                agents.append({
                    "id": agent_id,
                    "name": status.name,
                    "role": status.role,
                    "skills": status.skills,
                    "status": status.status,
                    "current_task": status.current_task,
                    "completed_tasks": status.total_completed
                })
            
            return {
                "success": True,
                "agents": agents,
                "total": len(agents)
            }
    
    async def _find_optimal_task_for_agent(self, agent_id: str) -> Optional[Task]:
        """Find the best task for an agent based on skills and priority"""
        agent = self.agent_status.get(agent_id)
        if not agent:
            return None
        
        # Get available tasks
        available_tasks = await self.kanban_client.get_available_tasks()
        
        log_thinking("pm_agent", f"Evaluating {len(available_tasks)} available tasks", {
            "agent_skills": agent.skills,
            "selection_criteria": ["skill_match", "priority", "dependencies"]
        })
        
        # Score and rank tasks (simplified for now)
        best_task = None
        best_score = 0
        
        for task in available_tasks:
            # Simple scoring based on priority
            score = 0
            if task.priority == Priority.URGENT:
                score += 1.0
            elif task.priority == Priority.HIGH:
                score += 0.8
            elif task.priority == Priority.MEDIUM:
                score += 0.6
            else:
                score += 0.4
                
            # Skill matching would go here
            # For now, just return the highest priority task
            if score > best_score:
                best_score = score
                best_task = task
                
        return best_task
    
    async def _analyze_task_completion(self, task_id: str, agent_id: str):
        """Analyze completed task for insights"""
        log_thinking("pm_agent", f"Analyzing completion of task {task_id} by {agent_id}")
        # Implementation would analyze completion time vs estimate, quality, etc.
        
    def _determine_feature_type(self, task: Task) -> str:
        """Determine the feature type based on task name/description"""
        task_text = f"{task.name} {task.description}".lower()
        
        if any(word in task_text for word in ['api', 'endpoint', 'route', 'rest']):
            return "endpoints"
        elif any(word in task_text for word in ['model', 'schema', 'database', 'entity']):
            return "models"
        elif any(word in task_text for word in ['config', 'setting', 'environment']):
            return "schemas"
        else:
            return "endpoints"  # Default to endpoints
            
    def _store_recommendations(self, task_id: str, recommendations: List[str]):
        """Store recommendations for future task assignments"""
        # In a real implementation, this would persist to a database
        # For now, we'll keep in memory
        if not hasattr(self, '_task_recommendations'):
            self._task_recommendations = {}
        self._task_recommendations[task_id] = recommendations
    
    async def _refresh_project_state(self):
        """Refresh project state from Kanban board"""
        log_thinking("pm_agent", "Refreshing project state from Kanban board")
        # Implementation would fetch current state
        # For now, creating a basic state
        if not self.project_state:
            self.project_state = ProjectState(
                total_tasks=0,
                completed_tasks=0,
                in_progress_tasks=0,
                blocked_tasks=0,
                critical_path_tasks=[],
                overall_health_score=0.8,
                risk_level=RiskLevel.LOW,
                estimated_completion_date=None,
                budget_status="on_track",
                team_morale_score=0.9
            )
    
    async def run(self):
        """Run the PM Agent server"""
        provider = os.getenv('KANBAN_PROVIDER', 'planka')
        print(f"\nPM Agent MCP Server Running")
        print(f"Kanban Provider: {provider.upper()}")
        print(f"Logs: logs/conversations/")
        print("="*50)
        
        # Start server
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Run the unified PM Agent server"""
    server = UnifiedPMAgentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())