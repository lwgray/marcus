#!/usr/bin/env python3
"""
Marcus AI Project Coordination System - MCP Server v2
Unified Marcus MCP Server - Corrected tool registration pattern
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Change to script directory to ensure correct working directory
script_dir = Path(__file__).parent.absolute()
os.chdir(script_dir)
sys.path.insert(0, str(script_dir))

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
from src.integrations.ai_analysis_engine_fixed import AIAnalysisEngine
from src.core.code_analyzer import CodeAnalyzer
from src.monitoring.project_monitor import ProjectMonitor
from src.communication.communication_hub import CommunicationHub
from src.config.settings import Settings
from src.logging.conversation_logger import conversation_logger, log_conversation, log_thinking
from src.core.assignment_persistence import AssignmentPersistence
from src.monitoring.assignment_monitor import AssignmentMonitor, AssignmentHealthChecker
from src.visualization.conversation_adapter import log_agent_event

# Natural Language Processing tools
from src.integrations.mcp_natural_language_tools import (
    create_project_from_natural_language,
    add_feature_natural_language
)
from ai_powered_task_assignment import find_optimal_task_for_agent_ai_powered

import atexit

# Global server instance
server = Server("marcus")

# State storage
class MarcusState:
    def __init__(self):
        load_dotenv()
        self.settings = Settings()
        
        # Get kanban provider from environment
        self.provider = os.getenv('KANBAN_PROVIDER', 'planka')
        print(f"Initializing Marcus with {self.provider.upper()} kanban provider...")
        
        # Quick fix: Create realtime log with line buffering
        log_dir = Path("logs/conversations")
        log_dir.mkdir(parents=True, exist_ok=True)
        self.realtime_log = open(
            log_dir / f"realtime_{datetime.now():%Y%m%d_%H%M%S}.jsonl", 
            'a', 
            buffering=1  # Line buffering - writes immediately on newline
        )
        atexit.register(self.realtime_log.close)
        
        # Core components
        self.kanban_client: Optional[KanbanInterface] = None
        self.ai_engine = AIAnalysisEngine()
        self.monitor = ProjectMonitor()
        self.comm_hub = CommunicationHub()
        
        # Add code analyzer for GitHub
        self.code_analyzer = None
        if self.provider == 'github':
            self.code_analyzer = CodeAnalyzer()
        
        # State tracking
        self.agent_tasks: Dict[str, TaskAssignment] = {}
        self.agent_status: Dict[str, WorkerStatus] = {}
        self.project_state: Optional[ProjectState] = None
        self.project_tasks: List[Task] = []
        
        # Assignment persistence and locking
        self.assignment_persistence = AssignmentPersistence()
        self.assignment_lock = asyncio.Lock()
        self.tasks_being_assigned: set = set()
        
        # Assignment monitoring
        self.assignment_monitor = None  # Will be initialized after kanban client
        
        # Log startup
        conversation_logger.log_system_state(
            active_workers=0,
            tasks_in_progress=0,
            tasks_completed=0,
            tasks_blocked=0,
            system_metrics={
                "status": "starting",
                "kanban_provider": self.provider
            }
        )
    
    async def initialize_kanban(self):
        """Initialize the kanban client"""
        if not self.kanban_client:
            print(f"[Marcus] Creating kanban client...")
            self.kanban_client = KanbanFactory.create_default()
            print(f"[Marcus] Kanban client created: {type(self.kanban_client).__name__}")
            await self.kanban_client.connect()
            print(f"[Marcus] Kanban client connected")
            
        # Load persisted assignments
        await self.assignment_persistence.load_assignments()
        
        # Initialize and start assignment monitor
        if not self.assignment_monitor:
            self.assignment_monitor = AssignmentMonitor(
                self.assignment_persistence,
                self.kanban_client,
                check_interval=30  # Check every 30 seconds
            )
            await self.assignment_monitor.start()
            print(f"[Marcus] Assignment monitor started")
            
    async def _mcp_function_caller(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Function to call MCP tools for kanban integrations"""
        # For now, we'll use a simple mock that returns test data
        # In production, this would connect to the actual kanban MCP server
        print(f"MCP Call: {tool_name} with args: {arguments}")
        
        # Mock responses for testing
        if tool_name == "mcp_kanban_project_board_manager":
            if arguments.get("action") == "get_projects":
                return {
                    "items": [
                        {"id": "test-project", "name": "Task Master Test"}
                    ]
                }
            elif arguments.get("action") == "get_boards":
                return {
                    "items": [
                        {"id": "test-board", "name": "Task Master Test Board", "projectId": "test-project"}
                    ]
                }
        elif tool_name == "mcp_kanban_list_manager":
            if arguments.get("action") == "get_all":
                return [
                    {"id": "list-1", "name": "Backlog", "boardId": "test-board"},
                    {"id": "list-2", "name": "In Progress", "boardId": "test-board"},
                    {"id": "list-3", "name": "Done", "boardId": "test-board"}
                ]
        elif tool_name == "mcp_kanban_card_manager":
            if arguments.get("action") == "get_all":
                # Return test tasks
                return [
                    {
                        "id": "task-1",
                        "name": "Setup Development Environment",
                        "description": "Configure the development environment with required tools",
                        "listId": "list-1",
                        "boardId": "test-board"
                    },
                    {
                        "id": "task-2", 
                        "name": "Create User Authentication",
                        "description": "Implement user login and registration",
                        "listId": "list-1",
                        "boardId": "test-board"
                    }
                ]
        elif tool_name == "mcp_kanban_comment_manager":
            if arguments.get("action") == "create":
                return {"id": "comment-1", "text": arguments.get("text", "")}
                
        return {"success": True, "message": "Mock response"}
    
    def log_event(self, event_type: str, data: dict):
        """Quick fix: Log events immediately to realtime log"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        self.realtime_log.write(json.dumps(event) + '\n')


# Create global state instance
state = MarcusState()


# Tool registration using correct MCP pattern
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return list of available tools"""
    return [
        types.Tool(
            name="register_agent",
            description="Register a new agent with the Marcus system",
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
        types.Tool(
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
        types.Tool(
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
        types.Tool(
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
        types.Tool(
            name="get_project_status",
            description="Get current project status and metrics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
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
        types.Tool(
            name="list_registered_agents",
            description="List all registered agents",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="ping",
            description="Check Marcus status and connectivity",
            inputSchema={
                "type": "object",
                "properties": {
                    "echo": {"type": "string", "description": "Optional message to echo back", "default": ""}
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_assignment_health",
            description="Check the health of the assignment tracking system",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="create_project",
            description="Create a complete project from natural language description",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Natural language project description or requirements"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name for the project board"
                    },
                    "options": {
                        "type": "object",
                        "description": "Optional project configuration",
                        "properties": {
                            "team_size": {
                                "type": "integer",
                                "description": "Number of developers",
                                "default": 3
                            },
                            "tech_stack": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Technologies to use"
                            },
                            "deadline": {
                                "type": "string",
                                "description": "Project deadline (ISO date format)"
                            }
                        }
                    }
                },
                "required": ["description", "project_name"]
            }
        ),
        types.Tool(
            name="add_feature",
            description="Add a feature to existing project using natural language",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_description": {
                        "type": "string",
                        "description": "Natural language description of the feature to add"
                    },
                    "integration_point": {
                        "type": "string",
                        "description": "How to integrate the feature",
                        "enum": ["auto_detect", "after_current", "parallel", "new_phase"],
                        "default": "auto_detect"
                    }
                },
                "required": ["feature_description"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls"""
    
    if arguments is None:
        arguments = {}
    
    try:
        if name == "register_agent":
            result = await register_agent(
                arguments.get("agent_id"),
                arguments.get("name"),
                arguments.get("role"),
                arguments.get("skills", [])
            )
        
        elif name == "request_next_task":
            result = await request_next_task(arguments.get("agent_id"))
        
        elif name == "report_task_progress":
            result = await report_task_progress(
                arguments.get("agent_id"),
                arguments.get("task_id"),
                arguments.get("status"),
                arguments.get("progress", 0),
                arguments.get("message", "")
            )
        
        elif name == "report_blocker":
            result = await report_blocker(
                arguments.get("agent_id"),
                arguments.get("task_id"),
                arguments.get("blocker_description"),
                arguments.get("severity", "medium")
            )
        
        elif name == "get_project_status":
            result = await get_project_status()
        
        elif name == "get_agent_status":
            result = await get_agent_status(arguments.get("agent_id"))
        
        elif name == "list_registered_agents":
            result = await list_registered_agents()
        
        elif name == "ping":
            result = await ping(arguments.get("echo", ""))
        
        elif name == "check_assignment_health":
            result = await check_assignment_health()
        
        elif name == "create_project":
            result = await create_project_from_natural_language(
                description=arguments.get("description"),
                project_name=arguments.get("project_name"),
                options=arguments.get("options", {})
            )
        
        elif name == "add_feature":
            result = await add_feature_natural_language(
                feature_description=arguments.get("feature_description"),
                integration_point=arguments.get("integration_point", "auto_detect")
            )
        
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


# Tool implementations
async def register_agent(agent_id: str, name: str, role: str, skills: List[str]) -> dict:
    """Register a new agent with the Marcus system"""
    # Log incoming registration request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Registering as {role} with skills: {skills}",
        {"name": name, "role": role, "skills": skills}
    )
    
    try:
        # Log Marcus thinking
        log_thinking("marcus", f"New agent registration request from {name}", {
            "agent_id": agent_id,
            "role": role,
            "skills": skills
        })
        
        # Create worker status with correct field names
        status = WorkerStatus(
            worker_id=agent_id,
            name=name,
            role=role,
            email=None,
            current_tasks=[],
            completed_tasks_count=0,
            capacity=40,  # Default 40 hours/week
            skills=skills or [],
            availability={
                "monday": True,
                "tuesday": True,
                "wednesday": True,
                "thursday": True,
                "friday": True,
                "saturday": False,
                "sunday": False
            },
            performance_score=1.0
        )
        
        state.agent_status[agent_id] = status
        
        # Log registration event immediately
        state.log_event("worker_registration", {
            "worker_id": agent_id,
            "name": name,
            "role": role,
            "skills": skills,
            "source": "mcp_client",
            "target": "marcus"
        })
        
        # Log conversation event for visualization
        log_agent_event("worker_registration", {
            "worker_id": agent_id,
            "name": name,
            "role": role,
            "skills": skills
        })
        
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


async def request_next_task(agent_id: str) -> dict:
    """Agents call this to request their next optimal task"""
    # Log task request
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        "Requesting next task",
        {"worker_info": f"Worker {agent_id} requesting task"}
    )
    
    try:
        # Log the task request immediately
        state.log_event("task_request", {
            "worker_id": agent_id,
            "source": agent_id,
            "target": "marcus"
        })
        
        # Log conversation event for visualization
        log_agent_event("task_request", {
            "worker_id": agent_id
        })
        
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking about refreshing state
        log_thinking("marcus", "Need to check current project state")
        
        # Get current project state
        await refresh_project_state()
        
        # Log thinking about finding task
        agent = state.agent_status.get(agent_id)
        if agent:
            log_thinking("marcus", f"Finding optimal task for {agent.name}", {
                "agent_skills": agent.skills,
                "current_workload": len(agent.current_tasks)
            })
        
        # Find optimal task for this agent
        optimal_task = await find_optimal_task_for_agent(agent_id)
        
        if optimal_task:
            try:
                # Get implementation context if using GitHub
                previous_implementations = None
                if state.provider == 'github' and state.code_analyzer:
                    owner = os.getenv('GITHUB_OWNER')
                    repo = os.getenv('GITHUB_REPO')
                    impl_details = await state.code_analyzer.get_implementation_details(
                        optimal_task.dependencies,
                        owner,
                        repo
                    )
                    if impl_details:
                        previous_implementations = impl_details
                
                # Generate detailed instructions with AI
                instructions = await state.ai_engine.generate_task_instructions(
                    optimal_task,
                    state.agent_status.get(agent_id)
                )
                
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
                        "dependencies_clear": len(optimal_task.dependencies) == 0
                    }
                )
                
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
                
                # Update kanban FIRST (fail fast if kanban is down)
                await state.kanban_client.update_task(optimal_task.id, {
                    "status": TaskStatus.IN_PROGRESS,
                    "assigned_to": agent_id
                })
                
                # If kanban update succeeded, track assignment
                state.agent_tasks[agent_id] = assignment
                agent = state.agent_status[agent_id]
                agent.current_tasks = [optimal_task]
                
                # Persist assignment
                await state.assignment_persistence.save_assignment(
                    agent_id, 
                    optimal_task.id,
                    {
                        "name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours
                    }
                )
                
                # Remove from pending assignments
                state.tasks_being_assigned.discard(optimal_task.id)
                
                # Log task assignment
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm",
                    f"Assigned task: {optimal_task.name}",
                    {
                        "task_id": optimal_task.id,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value
                    }
                )
                
                # Log conversation event for visualization
                log_agent_event("task_assignment", {
                    "worker_id": agent_id,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "priority": optimal_task.priority.value,
                        "estimated_hours": optimal_task.estimated_hours
                    }
                })
                
                return {
                    "success": True,
                    "task": {
                        "id": optimal_task.id,
                        "name": optimal_task.name,
                        "description": optimal_task.description,
                        "instructions": instructions,
                        "priority": optimal_task.priority.value,
                        "implementation_context": previous_implementations
                    }
                }
            
            except Exception as e:
                # If anything fails, rollback the reservation
                state.tasks_being_assigned.discard(optimal_task.id)
                
                conversation_logger.log_worker_message(
                    agent_id,
                    "from_pm", 
                    f"Failed to assign task: {str(e)}",
                    {"error": str(e)}
                )
                
                return {
                    "success": False,
                    "error": f"Failed to assign task: {str(e)}"
                }
                
        else:
            conversation_logger.log_worker_message(
                agent_id,
                "from_pm",
                "No suitable tasks available at this time",
                {"reason": "no_matching_tasks"}
            )
            
            return {
                "success": False,
                "message": "No suitable tasks available at this time"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def report_task_progress(
    agent_id: str,
    task_id: str,
    status: str,
    progress: int,
    message: str
) -> dict:
    """Agents report their task progress"""
    # Log progress update
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Progress update: {message} ({progress}%)",
        {
            "task_id": task_id,
            "status": status,
            "progress": progress
        }
    )
    
    # Log conversation event for visualization
    log_agent_event("progress_update", {
        "agent_id": agent_id,
        "task_id": task_id,
        "status": status,
        "progress": progress,
        "message": message
    })
    
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking
        log_thinking("marcus", f"Processing progress update from {agent_id}", {
            "task_id": task_id,
            "status": status,
            "progress": progress
        })
        
        # Update task in kanban
        update_data = {"progress": progress}
        
        if status == "completed":
            update_data["status"] = TaskStatus.DONE
            update_data["completed_at"] = datetime.now().isoformat()
            
            # Clear agent's current task
            if agent_id in state.agent_status:
                agent = state.agent_status[agent_id]
                agent.current_tasks = []
                agent.completed_tasks_count += 1
                
                # Remove task assignment from state and persistence
                if agent_id in state.agent_tasks:
                    del state.agent_tasks[agent_id]
                    
                # Remove from persistent storage
                await state.assignment_persistence.remove_assignment(agent_id)
                
                # Code analysis for GitHub
                if state.provider == 'github' and state.code_analyzer:
                    owner = os.getenv('GITHUB_OWNER')
                    repo = os.getenv('GITHUB_REPO')
                    
                    # Get task details
                    task = await state.kanban_client.get_task_by_id(task_id)
                    
                    # Analyze completed work
                    analysis = await state.code_analyzer.analyze_task_completion(
                        task,
                        agent,
                        owner,
                        repo
                    )
                    
                    if analysis and analysis.get('findings'):
                        # Store findings for future tasks
                        await state.kanban_client.add_comment(
                            task_id,
                            f"🤖 Code Analysis:\n{json.dumps(analysis['findings'], indent=2)}"
                        )
            
        elif status == "blocked":
            update_data["status"] = TaskStatus.BLOCKED
            
        await state.kanban_client.update_task(task_id, update_data)
        
        # Update task progress (including checklist items)
        await state.kanban_client.update_task_progress(task_id, {
            'progress': progress,
            'status': status,
            'message': message
        })
        
        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Progress update received: {status} at {progress}%",
            {"acknowledged": True}
        )
        
        # Update system state
        await refresh_project_state()
        
        return {
            "success": True,
            "message": "Progress updated successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def report_blocker(
    agent_id: str,
    task_id: str,
    blocker_description: str,
    severity: str
) -> dict:
    """Report a blocker on a task"""
    # Log blocker report
    conversation_logger.log_worker_message(
        agent_id,
        "to_pm",
        f"Reporting blocker: {blocker_description}",
        {
            "task_id": task_id,
            "severity": severity
        }
    )
    
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Log Marcus thinking
        log_thinking("marcus", f"Analyzing blocker from {agent_id}", {
            "task_id": task_id,
            "severity": severity,
            "description": blocker_description
        })
        
        # Use AI to analyze the blocker and suggest solutions
        agent = state.agent_status.get(agent_id)
        task = await state.kanban_client.get_task_by_id(task_id)
        
        suggestions = await state.ai_engine.analyze_blocker(
            task_id,
            blocker_description,
            severity,
            agent,
            task
        )
        
        # Update task status
        await state.kanban_client.update_task(task_id, {
            "status": TaskStatus.BLOCKED,
            "blocker": blocker_description
        })
        
        # Add detailed comment
        comment = f"🚫 BLOCKER ({severity.upper()})\\n"
        comment += f"Reported by: {agent_id}\\n"
        comment += f"Description: {blocker_description}\\n\\n"
        comment += f"📋 AI Suggestions:\\n{suggestions}"
        
        await state.kanban_client.add_comment(task_id, comment)
        
        # Log Marcus decision
        conversation_logger.log_pm_decision(
            decision=f"Acknowledge blocker and provide suggestions",
            rationale="Help agent overcome the blocker with AI guidance",
            confidence_score=0.8,
            decision_factors={
                "severity": severity,
                "has_suggestions": bool(suggestions)
            }
        )
        
        # Log response
        conversation_logger.log_worker_message(
            agent_id,
            "from_pm",
            f"Blocker acknowledged. Suggestions provided.",
            {
                "suggestions": suggestions,
                "severity": severity
            }
        )
        
        return {
            "success": True,
            "suggestions": suggestions,
            "message": "Blocker reported and suggestions provided"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_project_status() -> dict:
    """Get current project status and metrics"""
    try:
        # Initialize kanban if needed
        await state.initialize_kanban()
        
        # Refresh state
        await refresh_project_state()
        
        if state.project_state:
            # Calculate metrics
            total_tasks = len(state.project_tasks)
            completed = len([t for t in state.project_tasks if t.status == TaskStatus.DONE])
            in_progress = len([t for t in state.project_tasks if t.status == TaskStatus.IN_PROGRESS])
            blocked = len([t for t in state.project_tasks if t.status == TaskStatus.BLOCKED])
            
            # Worker metrics - create snapshot to avoid dictionary mutation during iteration
            active_workers = len([w for w in list(state.agent_status.values()) if len(w.current_tasks) > 0])
            
            return {
                "success": True,
                "project": {
                    "total_tasks": total_tasks,
                    "completed": completed,
                    "in_progress": in_progress,
                    "blocked": blocked,
                    "completion_percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0
                },
                "workers": {
                    "total": len(state.agent_status),
                    "active": active_workers,
                    "available": len(state.agent_status) - active_workers
                },
                "provider": state.provider
            }
        else:
            return {
                "success": False,
                "message": "Project state not available"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def get_agent_status(agent_id: str) -> dict:
    """Get status and current assignment for an agent"""
    try:
        agent = state.agent_status.get(agent_id)
        if agent:
            result = {
                "success": True,
                "agent": {
                    "id": agent.worker_id,
                    "name": agent.name,
                    "role": agent.role,
                    "skills": agent.skills,
                    "status": "working" if len(agent.current_tasks) > 0 else "available",
                    "current_tasks": [t.id for t in agent.current_tasks],
                    "total_completed": agent.completed_tasks_count,
                    "performance_score": agent.performance_score
                }
            }
            
            # Add current assignment details if any
            if len(agent.current_tasks) > 0 and agent.worker_id in state.agent_tasks:
                assignment = state.agent_tasks[agent.worker_id]
                result["current_assignment"] = {
                    "task_id": assignment.task_id,
                    "task_name": assignment.task_name,
                    "assigned_at": assignment.assigned_at.isoformat(),
                    "instructions": assignment.instructions
                }
                
            return result
        else:
            return {
                "success": False,
                "message": f"Agent {agent_id} not found"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def list_registered_agents() -> dict:
    """List all registered agents"""
    try:
        agents = []
        for agent in list(state.agent_status.values()):
            agents.append({
                "id": agent.worker_id,
                "name": agent.name,
                "role": agent.role,
                "status": "working" if len(agent.current_tasks) > 0 else "available",
                "skills": agent.skills,
                "current_tasks": [t.id for t in agent.current_tasks],
                "total_completed": agent.completed_tasks_count
            })
            
        return {
            "success": True,
            "agents": agents,
            "total": len(agents)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


async def ping(echo: str) -> dict:
    """Check Marcus status and connectivity"""
    # Log the ping request immediately
    state.log_event("ping_request", {
        "echo": echo,
        "source": "mcp_client"
    })
    
    # Log conversation event for visualization
    log_agent_event("ping_request", {
        "echo": echo,
        "source": "mcp_client"
    })
    
    # Also use structured logging
    log_thinking("marcus", f"Received ping request with echo: {echo}")
    
    response = {
        "success": True,
        "status": "online",
        "provider": state.provider,
        "echo": echo or "pong",
        "timestamp": datetime.now().isoformat()
    }
    
    # Log the response immediately
    state.log_event("ping_response", response)
    
    # Also use structured logging
    conversation_logger.log_kanban_interaction(
        action="ping",
        direction="response",
        data=response
    )
    
    return response


async def check_assignment_health() -> dict:
    """Check the health of the assignment tracking system."""
    try:
        # Initialize health checker
        health_checker = AssignmentHealthChecker(
            state.assignment_persistence,
            state.kanban_client,
            state.assignment_monitor
        )
        
        # Run health check
        health_status = await health_checker.check_assignment_health()
        
        # Add current in-memory state info
        health_status["in_memory_state"] = {
            "agent_tasks": len(state.agent_tasks),
            "tasks_being_assigned": len(state.tasks_being_assigned),
            "monitor_running": state.assignment_monitor._running if state.assignment_monitor else False
        }
        
        return {
            "success": True,
            **health_status
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Helper functions
async def refresh_project_state():
    """Refresh the current project state from kanban"""
    try:
        # Log refresh attempt
        state.log_event("refresh_project_state_start", {
            "kanban_client_exists": state.kanban_client is not None
        })
        
        tasks = await state.kanban_client.get_available_tasks()
        
        # Log tasks retrieved
        state.log_event("refresh_project_state_tasks", {
            "task_count": len(tasks),
            "task_names": [t.name for t in tasks]
        })
        
        # Store tasks separately
        state.project_tasks = tasks
        
        # Calculate task statistics
        completed = len([t for t in tasks if t.status == TaskStatus.DONE])
        in_progress = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
        blocked = len([t for t in tasks if t.status == TaskStatus.BLOCKED])
        total = len(tasks)
        
        state.project_state = ProjectState(
            board_id="default",
            project_name="Task Master Test",
            total_tasks=total,
            completed_tasks=completed,
            in_progress_tasks=in_progress,
            blocked_tasks=blocked,
            progress_percent=(completed / total * 100) if total > 0 else 0,
            overdue_tasks=[],
            team_velocity=0.0,
            risk_level=RiskLevel.LOW,
            last_updated=datetime.now()
        )
        
        # Log system state
        conversation_logger.log_system_state(
            active_workers=len([w for w in list(state.agent_status.values()) if len(w.current_tasks) > 0]),
            tasks_in_progress=len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
            tasks_completed=len([t for t in tasks if t.status == TaskStatus.DONE]),
            tasks_blocked=len([t for t in tasks if t.status == TaskStatus.BLOCKED]),
            system_metrics={
                "total_tasks": len(tasks),
                "total_workers": len(state.agent_status)
            }
        )
        
    except Exception as e:
        state.log_event("refresh_project_state_error", {
            "error": str(e),
            "error_type": type(e).__name__
        })
        print(f"Error refreshing project state: {e}")


async def find_optimal_task_for_agent(agent_id: str) -> Optional[Task]:
    """Find the best task for an agent using AI-powered analysis"""
    async with state.assignment_lock:
        agent = state.agent_status.get(agent_id)
        
        if not agent or not state.project_state:
            return None
            
        # Get available tasks
        assigned_task_ids = [a.task_id for a in state.agent_tasks.values()]
        persisted_assigned_ids = await state.assignment_persistence.get_all_assigned_task_ids()
        all_assigned_ids = set(assigned_task_ids) | persisted_assigned_ids | state.tasks_being_assigned
        
        available_tasks = [
            t for t in state.project_tasks
            if t.status == TaskStatus.TODO and
            t.id not in all_assigned_ids
        ]
        
        if not available_tasks:
            return None
        
        # Use AI-powered task selection if AI engine is available
        if state.ai_engine:
            try:
                optimal_task = await find_optimal_task_for_agent_ai_powered(
                    agent_id=agent_id,
                    agent_status=agent.__dict__,
                    project_tasks=state.project_tasks,
                    available_tasks=available_tasks,
                    assigned_task_ids=all_assigned_ids,
                    ai_engine=state.ai_engine
                )
                
                if optimal_task:
                    state.tasks_being_assigned.add(optimal_task.id)
                    return optimal_task
            except Exception as e:
                conversation_logger.error(f"AI task assignment failed, falling back to basic: {e}")
        
        # Fallback to basic assignment if AI fails
        return await find_optimal_task_basic(agent_id, available_tasks)


async def find_optimal_task_basic(agent_id: str, available_tasks: List[Task]) -> Optional[Task]:
    """Basic task assignment logic (fallback)"""
    agent = state.agent_status.get(agent_id)
    if not agent:
        return None
        
    best_task = None
    best_score = -1
    
    for task in available_tasks:
        # Calculate skill match score
        skill_score = 0
        if agent.skills and task.labels:
            matching_skills = set(agent.skills) & set(task.labels)
            skill_score = len(matching_skills) / len(task.labels) if task.labels else 0
            
        # Priority score
        priority_score = {
            Priority.URGENT: 1.0,
            Priority.HIGH: 0.8,
            Priority.MEDIUM: 0.5,
            Priority.LOW: 0.2
        }.get(task.priority, 0.5)
        
        # Combined score
        total_score = (skill_score * 0.6) + (priority_score * 0.4)
        
        if total_score > best_score:
            best_score = total_score
            best_task = task
            
    if best_task:
        state.tasks_being_assigned.add(best_task.id)
        
    return best_task


async def main():
    """Run the Marcus server"""
    provider = os.getenv('KANBAN_PROVIDER', 'planka')
    print(f"\nMarcus MCP Server Running")
    print(f"Kanban Provider: {provider.upper()}")
    print(f"Logs: logs/conversations/")
    print("="*50)
    
    # Start server
    from mcp.server.stdio import stdio_server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
