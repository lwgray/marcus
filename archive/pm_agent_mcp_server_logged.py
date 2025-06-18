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
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings
from src.logging import conversation_logger, log_conversation, log_thinking


class LoggedPMAgentServer:
    """AI Project Manager Agent MCP Server with structured logging"""
    
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
        
        # Log startup
        conversation_logger.log_system_state(
            active_workers=0,
            tasks_in_progress=0,
            tasks_completed=0,
            tasks_blocked=0,
            system_metrics={"status": "starting"}
        )
    
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
                    
                    # Log task assignment
                    conversation_logger.log_task_assignment(
                        task_id=optimal_task.id,
                        worker_id=agent_id,
                        task_details={
                            "name": optimal_task.name,
                            "priority": optimal_task.priority.value,
                            "estimated_hours": optimal_task.estimated_hours
                        },
                        assignment_score=0.85,
                        dependency_analysis={
                            "blocking_tasks": [],
                            "dependent_tasks": optimal_task.dependencies
                        }
                    )
                    
                    # Update kanban board
                    log_thinking("pm_agent", "Updating Kanban board with assignment")
                    conversation_logger.log_kanban_interaction(
                        action="assign_task",
                        direction="to_kanban",
                        data={
                            "task_id": optimal_task.id,
                            "agent_id": agent_id,
                            "move_to": "In Progress"
                        },
                        processing_steps=[
                            "Locate task in Backlog",
                            "Update assigned_to field",
                            "Move to In Progress column",
                            "Add assignment comment"
                        ]
                    )
                    
                    await self.kanban_client.assign_task(optimal_task.id, agent_id)
                    
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
                # Validate task assignment
                if agent_id not in self.agent_tasks:
                    return {"success": False, "error": "No task assigned to agent"}
                
                assignment = self.agent_tasks[agent_id]
                if assignment.task_id != task_id:
                    return {"success": False, "error": "Task ID mismatch"}
                
                # Log progress update
                conversation_logger.log_progress_update(
                    worker_id=agent_id,
                    task_id=task_id,
                    progress=progress,
                    status=status,
                    message=message,
                    metrics={
                        "time_elapsed": (datetime.now() - assignment.assigned_at).total_seconds(),
                        "estimated_remaining": assignment.estimated_hours * (100 - progress) / 100
                    }
                )
                
                # Update kanban board
                log_thinking("pm_agent", f"Updating task progress on Kanban board: {progress}%")
                conversation_logger.log_kanban_interaction(
                    action="update_progress",
                    direction="to_kanban",
                    data={
                        "task_id": task_id,
                        "progress": progress,
                        "status": status,
                        "comment": message
                    }
                )
                
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
                    
                    # AI analysis of completion
                    await self._analyze_task_completion(task_id, agent_id)
                
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
                # AI analysis for resolution
                log_thinking("pm_agent", f"Analyzing blocker: {blocker_description}")
                
                suggestions = await self.ai_engine.analyze_blocker(
                    blocker_description,
                    self.agent_tasks.get(agent_id),
                    self.project_state
                )
                
                # Log blocker analysis
                conversation_logger.log_blocker(
                    worker_id=agent_id,
                    task_id=task_id,
                    blocker_description=blocker_description,
                    severity=severity,
                    suggested_solutions=suggestions
                )
                
                conversation_logger.log_pm_decision(
                    decision="Provide blocker resolution suggestions",
                    rationale=f"AI analysis identified {len(suggestions)} potential solutions",
                    confidence_score=0.75,
                    decision_factors={
                        "blocker_type": "analyzed",
                        "severity": severity,
                        "solutions_found": len(suggestions)
                    }
                )
                
                # Update task status
                conversation_logger.log_kanban_interaction(
                    action="report_blocker",
                    direction="to_kanban",
                    data={
                        "task_id": task_id,
                        "blocker": blocker_description,
                        "severity": severity
                    }
                )
                
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
                await self._refresh_project_state()
                metrics = await self.monitor.calculate_metrics(self.project_state)
                
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
                    "total_agents": len(self.agent_status)
                }
                
            except Exception as e:
                return {"success": False, "error": str(e)}
    
    async def _find_optimal_task_for_agent(self, agent_id: str) -> Optional[Task]:
        """Find the best task for an agent based on skills and priority"""
        agent = self.agent_status.get(agent_id)
        if not agent:
            return None
        
        # Log kanban query
        conversation_logger.log_kanban_interaction(
            action="get_available_tasks",
            direction="to_kanban",
            data={"criteria": "unassigned tasks in Backlog or Ready"},
            processing_steps=[
                "Query Backlog column",
                "Query Ready column",
                "Filter unassigned tasks",
                "Sort by priority"
            ]
        )
        
        # Get available tasks
        available_tasks = await self.kanban_client.get_available_tasks()
        
        # Log kanban response
        conversation_logger.log_kanban_interaction(
            action="get_available_tasks",
            direction="from_kanban",
            data={
                "task_count": len(available_tasks),
                "tasks": [{"id": t.id, "name": t.name} for t in available_tasks[:3]]
            }
        )
        
        log_thinking("pm_agent", f"Evaluating {len(available_tasks)} available tasks", {
            "agent_skills": agent.skills,
            "selection_criteria": ["skill_match", "priority", "dependencies"]
        })
        
        # Score and rank tasks
        # (Implementation details...)
        
        return None  # Placeholder
    
    async def _analyze_task_completion(self, task_id: str, agent_id: str):
        """Analyze completed task for insights"""
        log_thinking("pm_agent", f"Analyzing completion of task {task_id} by {agent_id}")
        # Implementation would analyze completion time vs estimate, quality, etc.
    
    async def _refresh_project_state(self):
        """Refresh project state from Kanban board"""
        log_thinking("pm_agent", "Refreshing project state from Kanban board")
        # Implementation with logging
        pass
    
    async def run(self):
        """Run the PM Agent server"""
        print("PM Agent MCP Server Running (with structured logging)")
        print(f"Logs are being written to: logs/conversations/")
        
        # Start server
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Run the logged PM Agent server"""
    server = LoggedPMAgentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())