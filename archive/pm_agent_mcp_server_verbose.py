import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.logging import RichHandler

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types

from src.core.models import (
    Task, TaskStatus, Priority, RiskLevel,
    ProjectState, WorkerStatus, TaskAssignment
)
from src.integrations.mcp_kanban_client_verbose import VerboseMCPKanbanClient
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings

# Configure rich console for pretty output
console = Console()

# Configure detailed logging with rich handler
logging.basicConfig(
    level=logging.DEBUG,
    format='%(message)s',
    handlers=[
        RichHandler(console=console, rich_tracebacks=True),
        logging.FileHandler('pm_agent_conversation.log')
    ]
)


class VerbosePMAgentServer:
    """AI Project Manager Agent MCP Server with Verbose Logging"""
    
    def __init__(self):
        self.server = Server("pm-agent")
        self.settings = Settings()
        self.logger = logging.getLogger("PM-Agent")
        
        # Core components
        self.kanban_client = VerboseMCPKanbanClient()
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        
        # Register tools
        self._register_tools()
        
        console.print(Panel.fit(
            "[bold green]PM Agent Started[/bold green]\n"
            "Verbose logging enabled - All decisions will be explained",
            title="🤖 PM Agent",
            border_style="green"
        ))
    
    def _log_thinking(self, message: str, context: dict = None):
        """Log PM Agent's thinking process"""
        console.print(f"\n[dim cyan]🧠 PM Agent Thinking:[/dim cyan] {message}")
        if context:
            for key, value in context.items():
                console.print(f"   [dim]• {key}:[/dim] {value}")
    
    def _log_decision(self, decision: str, reason: str):
        """Log PM Agent's decision"""
        console.print(Panel(
            f"[bold yellow]Decision:[/bold yellow] {decision}\n"
            f"[dim]Reason:[/dim] {reason}",
            title="📋 Decision Made",
            border_style="yellow"
        ))
    
    def _log_agent_message(self, agent_id: str, message: str, direction: str = "from"):
        """Log messages to/from agents"""
        icon = "📥" if direction == "from" else "📤"
        console.print(f"\n{icon} [bold blue]Agent {agent_id}[/bold blue] {direction}: {message}")
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.tool()
        async def register_agent(agent_id: str, name: str, role: str, skills: List[str] = None) -> dict:
            """Register a new agent with the PM system"""
            self._log_agent_message(agent_id, f"Registering as {role} with skills: {skills}", "from")
            
            try:
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
                
                self._log_thinking(
                    f"New agent registered successfully",
                    {
                        "Agent": name,
                        "Role": role,
                        "Skills": ", ".join(skills or []),
                        "Initial Status": "available"
                    }
                )
                
                # Show current agent roster
                self._show_agent_roster()
                
                return {
                    "success": True,
                    "message": f"Agent {name} registered successfully",
                    "agent_id": agent_id
                }
                
            except Exception as e:
                self.logger.error(f"Registration failed: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        @self.server.tool()
        async def request_next_task(agent_id: str) -> dict:
            """Agents call this to request their next optimal task"""
            self._log_agent_message(agent_id, "Requesting next task", "from")
            
            try:
                # Get current project state
                self._log_thinking("Refreshing project state from Kanban board")
                await self._refresh_project_state()
                
                # Show current board state
                self._show_board_state()
                
                # Find optimal task for this agent
                self._log_thinking(
                    f"Finding optimal task for agent",
                    {
                        "Agent": agent_id,
                        "Skills": ", ".join(self.agent_status[agent_id].skills),
                        "Current workload": self.agent_status[agent_id].current_task or "None"
                    }
                )
                
                optimal_task = await self._find_optimal_task_for_agent(agent_id)
                
                if optimal_task:
                    self._log_decision(
                        f"Assign task '{optimal_task.name}' to {agent_id}",
                        f"Best match for agent skills and task requirements. "
                        f"Priority: {optimal_task.priority}, "
                        f"Estimated: {optimal_task.estimated_hours}h"
                    )
                    
                    # Generate detailed instructions using AI
                    self._log_thinking("Generating detailed instructions for the task")
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
                    self.agent_status[agent_id].current_task = optimal_task.id
                    self.agent_status[agent_id].status = "working"
                    
                    # Update kanban board
                    self._log_thinking("Moving task to 'In Progress' on Kanban board")
                    await self.kanban_client.assign_task(optimal_task.id, agent_id)
                    
                    # Send notifications
                    await self.comm_hub.notify_task_assignment(agent_id, assignment)
                    
                    self._log_agent_message(
                        agent_id, 
                        f"Task assigned: {optimal_task.name}",
                        "to"
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
                    self._log_decision(
                        f"No task assigned to {agent_id}",
                        "No suitable tasks available matching agent skills or all tasks are assigned"
                    )
                    
                    return {
                        "has_task": False,
                        "message": "No suitable tasks available at this time"
                    }
                    
            except Exception as e:
                self.logger.error(f"Task request failed: {e}")
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
            self._log_agent_message(
                agent_id, 
                f"Progress update - Status: {status}, Progress: {progress}%, Message: {message}",
                "from"
            )
            
            try:
                # Validate task assignment
                if agent_id not in self.agent_tasks:
                    return {"success": False, "error": "No task assigned to agent"}
                
                assignment = self.agent_tasks[agent_id]
                if assignment.task_id != task_id:
                    return {"success": False, "error": "Task ID mismatch"}
                
                # Update kanban board
                self._log_thinking(
                    f"Updating task progress on Kanban board",
                    {
                        "Task": assignment.task_name,
                        "New Status": status,
                        "Progress": f"{progress}%"
                    }
                )
                
                await self.kanban_client.update_task_progress(
                    task_id, 
                    {"status": status, "progress": progress, "message": message}
                )
                
                # Update agent status
                if status == "completed":
                    self._log_decision(
                        f"Task completed by {agent_id}",
                        f"Moving task to 'Done' column and freeing up agent for next task"
                    )
                    
                    self.agent_status[agent_id].status = "available"
                    self.agent_status[agent_id].current_task = None
                    self.agent_status[agent_id].total_completed += 1
                    del self.agent_tasks[agent_id]
                    
                    # AI analysis of completion
                    await self._analyze_task_completion(task_id, agent_id)
                
                # Send notifications
                await self.comm_hub.notify_progress_update(agent_id, task_id, progress, message)
                
                # Show updated board state
                self._show_board_state()
                
                return {"success": True, "message": "Progress updated successfully"}
                
            except Exception as e:
                self.logger.error(f"Progress update failed: {e}")
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def report_blocker(
            agent_id: str, 
            task_id: str, 
            blocker_description: str,
            severity: str = "medium"
        ) -> dict:
            """Report a blocker on current task"""
            self._log_agent_message(
                agent_id,
                f"🚫 BLOCKER reported - Severity: {severity}, Description: {blocker_description}",
                "from"
            )
            
            try:
                # AI analysis for resolution
                self._log_thinking("Analyzing blocker for potential solutions")
                
                suggestions = await self.ai_engine.analyze_blocker(
                    blocker_description,
                    self.agent_tasks.get(agent_id),
                    self.project_state
                )
                
                self._log_decision(
                    "Blocker analysis complete",
                    f"Generated {len(suggestions)} potential solutions"
                )
                
                # Log suggestions
                console.print("\n[bold red]Blocker Resolution Suggestions:[/bold red]")
                for i, suggestion in enumerate(suggestions, 1):
                    console.print(f"  {i}. {suggestion}")
                
                # Update task status
                await self.kanban_client.report_blocker(task_id, blocker_description, severity)
                
                # Send escalation if high severity
                if severity == "high":
                    self._log_thinking("High severity blocker - escalating to stakeholders")
                    await self.comm_hub.escalate_blocker(agent_id, task_id, blocker_description)
                
                return {
                    "success": True,
                    "suggestions": suggestions,
                    "escalated": severity == "high"
                }
                
            except Exception as e:
                self.logger.error(f"Blocker report failed: {e}")
                return {"success": False, "error": str(e)}
        
        @self.server.tool()
        async def get_project_status() -> dict:
            """Get current project status and metrics"""
            self._log_thinking("Generating comprehensive project status report")
            
            try:
                await self._refresh_project_state()
                metrics = await self.monitor.calculate_metrics(self.project_state)
                
                # Display status
                self._show_project_status(metrics)
                
                return {
                    "success": True,
                    "project_state": self.project_state.__dict__ if self.project_state else None,
                    "metrics": metrics,
                    "active_agents": len([a for a in self.agent_status.values() if a.status == "working"]),
                    "total_agents": len(self.agent_status)
                }
                
            except Exception as e:
                self.logger.error(f"Status retrieval failed: {e}")
                return {"success": False, "error": str(e)}
    
    def _show_agent_roster(self):
        """Display current agent roster"""
        table = Table(title="👥 Agent Roster", show_lines=True)
        table.add_column("Agent ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Role", style="yellow")
        table.add_column("Skills", style="blue")
        table.add_column("Status", style="magenta")
        table.add_column("Current Task", style="red")
        
        for agent_id, status in self.agent_status.items():
            table.add_row(
                agent_id,
                status.name,
                status.role,
                ", ".join(status.skills),
                status.status,
                status.current_task or "None"
            )
        
        console.print(table)
    
    def _show_board_state(self):
        """Display current Kanban board state"""
        # This would show a summary of tasks in each column
        console.print("\n[bold]📋 Kanban Board State:[/bold]")
        # Implementation would query kanban board and display summary
    
    def _show_project_status(self, metrics: dict):
        """Display project status with metrics"""
        console.print(Panel(
            f"[bold green]Project Status[/bold green]\n"
            f"Progress: {metrics.get('progress', 0)}%\n"
            f"Velocity: {metrics.get('velocity', 0)} tasks/day\n"
            f"Risk Level: {metrics.get('risk_level', 'Unknown')}",
            title="📊 Project Metrics",
            border_style="green"
        ))
    
    async def _find_optimal_task_for_agent(self, agent_id: str) -> Optional[Task]:
        """Find the best task for an agent based on skills and priority"""
        # Implementation with detailed logging
        agent = self.agent_status.get(agent_id)
        if not agent:
            return None
        
        # Get available tasks
        available_tasks = await self.kanban_client.get_available_tasks()
        
        self._log_thinking(
            f"Evaluating {len(available_tasks)} available tasks",
            {
                "Agent skills": ", ".join(agent.skills),
                "Selection criteria": "Priority, skill match, dependencies"
            }
        )
        
        # Score and rank tasks
        # (Implementation details...)
        
        return None  # Placeholder
    
    async def _analyze_task_completion(self, task_id: str, agent_id: str):
        """Analyze completed task for insights"""
        self._log_thinking("Analyzing task completion for performance insights")
        # Implementation would analyze completion time vs estimate, quality, etc.
    
    async def _refresh_project_state(self):
        """Refresh project state from Kanban board"""
        # Implementation with logging
        pass
    
    async def run(self):
        """Run the PM Agent server"""
        console.print("\n[bold green]PM Agent MCP Server Running...[/bold green]")
        console.print("[dim]Waiting for agent connections...[/dim]\n")
        
        # Start server
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Run the verbose PM Agent server"""
    server = VerbosePMAgentServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())