"""
Enhancements for autonomous worker agent support
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.models import Priority, Task


class AgentState(Enum):
    """Agent operational states"""

    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    WAITING_CLARIFICATION = "waiting_clarification"
    OFFLINE = "offline"


@dataclass
class AgentWorkSession:
    """Track agent work sessions"""

    agent_id: str
    started_at: datetime
    last_activity: datetime
    tasks_completed: int = 0
    current_task_id: Optional[str] = None
    state: AgentState = AgentState.IDLE


@dataclass
class AgentCapabilities:
    """Enhanced agent capability tracking"""

    agent_id: str
    primary_skills: List[str]
    work_standards: Dict[str, Any]
    performance_history: List[float] = field(default_factory=list)
    specialization_prompt: str = ""


class WorkerAgentManager:
    """Enhanced manager for autonomous worker agents"""

    def __init__(self) -> None:
        self.agent_sessions: Dict[str, AgentWorkSession] = {}
        self.agent_capabilities: Dict[str, AgentCapabilities] = {}
        self.agent_prompts = self._load_agent_prompts()

    def _load_agent_prompts(self) -> Dict[str, Dict[str, Any]]:
        """Load specialized prompts for each agent type"""
        return {
            "backend_agent": {
                "system_prompt": """You are a Backend Development Agent...""",
                "capabilities": ["python", "fastapi", "postgresql", "redis"],
                "work_standards": {
                    "async_patterns": True,
                    "error_handling": "comprehensive",
                    "test_coverage": 0.8,
                    "api_documentation": "openapi",
                },
            },
            "frontend_agent": {
                "system_prompt": """You are a Frontend Development Agent...""",
                "capabilities": ["react", "typescript", "css", "redux"],
                "work_standards": {
                    "component_style": "functional_hooks",
                    "typing": "strict",
                    "responsive": True,
                    "accessibility": "wcag_aa",
                },
            },
            "ai_ml_agent": {
                "system_prompt": """You are an AI/ML Development Agent...""",
                "capabilities": ["machine_learning", "optimization", "nlp"],
                "work_standards": {
                    "algorithm_documentation": True,
                    "performance_benchmarks": True,
                    "scalability_testing": True,
                },
            },
            "devops_agent": {
                "system_prompt": """You are a DevOps Agent...""",
                "capabilities": ["docker", "kubernetes", "aws", "ci_cd"],
                "work_standards": {
                    "infrastructure_as_code": True,
                    "security_scanning": True,
                    "monitoring": "comprehensive",
                },
            },
            "testing_agent": {
                "system_prompt": """You are a Testing Agent...""",
                "capabilities": ["testing", "automation", "quality_assurance"],
                "work_standards": {
                    "code_coverage": 0.8,
                    "test_types": ["unit", "integration", "e2e"],
                    "automation": True,
                },
            },
        }

    async def register_autonomous_agent(
        self, agent_id: str, agent_type: str, custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register an autonomous agent with specialized capabilities"""

        # Get agent configuration
        agent_config = self.agent_prompts.get(agent_type, {})

        # Create capability profile
        capabilities = AgentCapabilities(
            agent_id=agent_id,
            primary_skills=agent_config.get("capabilities", []),
            work_standards=agent_config.get("work_standards", {}),
            specialization_prompt=custom_prompt
            or agent_config.get("system_prompt", ""),
        )

        # Create work session
        session = AgentWorkSession(
            agent_id=agent_id, started_at=datetime.now(), last_activity=datetime.now()
        )

        self.agent_capabilities[agent_id] = capabilities
        self.agent_sessions[agent_id] = session

        return {
            "success": True,
            "agent_id": agent_id,
            "type": agent_type,
            "capabilities": capabilities.primary_skills,
            "prompt": capabilities.specialization_prompt[:200] + "...",
        }

    async def get_next_task_for_agent(
        self, agent_id: str, kanban_client: Any, ai_engine: Any
    ) -> Optional[Task]:
        """Get next optimal task for agent based on skills and current workload"""

        # Get agent capabilities
        capabilities = self.agent_capabilities.get(agent_id)
        if not capabilities:
            return None

        # Get available tasks
        available_tasks = await kanban_client.get_available_tasks()
        if not available_tasks:
            return None

        # Score tasks based on agent capabilities
        scored_tasks = []
        for task in available_tasks:
            score = await self._score_task_for_agent(task, capabilities, ai_engine)
            scored_tasks.append((score, task))

        # Sort by score and return best match
        scored_tasks.sort(key=lambda x: x[0], reverse=True)

        if scored_tasks and scored_tasks[0][0] > 0:
            best_task: Task = scored_tasks[0][1]
            return best_task

        return None

    async def _score_task_for_agent(
        self, task: Task, capabilities: AgentCapabilities, ai_engine: Any
    ) -> float:
        """Score a task based on agent capabilities"""

        # Basic scoring based on task labels matching agent skills
        score = 0.0

        # Check skill match
        task_labels_lower = [label.lower() for label in task.labels]
        for skill in capabilities.primary_skills:
            if (
                skill.lower() in task_labels_lower
                or skill.lower() in task.description.lower()
            ):
                score += 1.0

        # Priority boost
        priority_scores = {
            Priority.URGENT: 2.0,
            Priority.HIGH: 1.5,
            Priority.MEDIUM: 1.0,
            Priority.LOW: 0.5,
        }
        score *= priority_scores.get(task.priority, 1.0)

        # Could enhance with AI scoring here
        # ai_score = await ai_engine.score_task_agent_match(task, capabilities)

        return score

    def update_agent_activity(self, agent_id: str) -> None:
        """Update agent's last activity timestamp"""
        if agent_id in self.agent_sessions:
            self.agent_sessions[agent_id].last_activity = datetime.now()

    def set_agent_state(self, agent_id: str, state: AgentState) -> None:
        """Update agent's operational state"""
        if agent_id in self.agent_sessions:
            self.agent_sessions[agent_id].state = state

    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """Get performance metrics for an agent"""
        session = self.agent_sessions.get(agent_id)
        capabilities = self.agent_capabilities.get(agent_id)

        if not session:
            return {}

        uptime = datetime.now() - session.started_at

        average_performance = 0.0
        if capabilities and capabilities.performance_history:
            average_performance = sum(capabilities.performance_history) / len(
                capabilities.performance_history
            )

        return {
            "agent_id": agent_id,
            "uptime_hours": uptime.total_seconds() / 3600,
            "tasks_completed": session.tasks_completed,
            "current_state": session.state.value,
            "last_activity": session.last_activity.isoformat(),
            "average_performance": average_performance,
        }

    def get_all_active_agents(self) -> List[Dict[str, Any]]:
        """Get all active agents and their states"""
        active_agents = []

        for agent_id, session in self.agent_sessions.items():
            # Consider agent active if last activity within 5 minutes
            if (datetime.now() - session.last_activity) < timedelta(minutes=5):
                active_agents.append(
                    {
                        "agent_id": agent_id,
                        "state": session.state.value,
                        "current_task": session.current_task_id,
                        "tasks_completed": session.tasks_completed,
                    }
                )

        return active_agents


# Enhanced Marcus methods to support autonomous workers
class EnhancedPMAgentMethods:
    """Additional methods for Marcus to support autonomous workers"""

    def __init__(self, worker_manager: WorkerAgentManager):
        self.worker_manager = worker_manager

    async def handle_autonomous_agent_registration(
        self, agent_id: str, agent_type: str, custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Enhanced registration for autonomous agents"""

        # Register with worker manager
        result = await self.worker_manager.register_autonomous_agent(
            agent_id, agent_type, custom_prompt
        )

        # Return enhanced registration info including prompt
        return {
            **result,
            "instructions": "Start by calling request_next_task to get your first assignment",
            "available_tools": [
                "request_next_task",
                "report_task_progress",
                "get_task_clarification",
                "report_blocker",
                "get_agent_status",
            ],
        }

    async def get_agent_performance_dashboard(self) -> Dict[str, Any]:
        """Get performance dashboard for all agents"""

        active_agents = self.worker_manager.get_all_active_agents()
        agent_metrics = {}

        for agent in active_agents:
            agent_id = agent["agent_id"]
            metrics = self.worker_manager.get_agent_metrics(agent_id)
            agent_metrics[agent_id] = metrics

        return {
            "active_agents": len(active_agents),
            "total_tasks_completed": sum(a["tasks_completed"] for a in active_agents),
            "agent_details": agent_metrics,
            "timestamp": datetime.now().isoformat(),
        }

    async def broadcast_to_agents(
        self, message: str, agent_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Broadcast message to all or specific agents"""
        target_agents = agent_ids or list(self.worker_manager.agent_sessions.keys())

        # In real implementation, this would send through communication channels
        # For now, we'll store messages for agents to retrieve

        return {
            "broadcast_sent": True,
            "recipients": target_agents,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
