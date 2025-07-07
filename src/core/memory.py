"""
Memory System for Marcus

Multi-tier memory system that enables learning from past experiences and
predictive task assignment. Inspired by cognitive memory models with working,
episodic, semantic, and procedural memory layers.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import logging

from src.core.models import Task, TaskStatus, Priority, WorkerStatus
from src.core.events import Events, EventTypes
from src.core.persistence import Persistence

logger = logging.getLogger(__name__)


@dataclass
class TaskOutcome:
    """Record of a task execution outcome"""
    task_id: str
    agent_id: str
    task_name: str
    estimated_hours: float
    actual_hours: float
    success: bool
    blockers: List[str] = field(default_factory=list)
    started_at: datetime = None
    completed_at: datetime = None
    
    @property
    def estimation_accuracy(self) -> float:
        """Calculate how accurate the time estimate was"""
        if self.estimated_hours == 0:
            return 0.0
        return min(self.estimated_hours, self.actual_hours) / max(self.estimated_hours, self.actual_hours)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "task_name": self.task_name,
            "estimated_hours": self.estimated_hours,
            "actual_hours": self.actual_hours,
            "success": self.success,
            "blockers": self.blockers,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimation_accuracy": self.estimation_accuracy
        }


@dataclass
class AgentProfile:
    """Learned profile of an agent's capabilities"""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    blocked_tasks: int = 0
    skill_success_rates: Dict[str, float] = field(default_factory=dict)
    average_estimation_accuracy: float = 0.0
    common_blockers: Dict[str, int] = field(default_factory=dict)
    peak_performance_hours: List[int] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Overall success rate"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
        
    @property
    def blockage_rate(self) -> float:
        """Rate of encountering blockers"""
        if self.total_tasks == 0:
            return 0.0
        return self.blocked_tasks / self.total_tasks


@dataclass
class TaskPattern:
    """Learned pattern about task types"""
    pattern_type: str
    task_labels: List[str]
    average_duration: float
    success_rate: float
    common_blockers: List[str]
    prerequisites: List[str]
    best_agents: List[str]


class Memory:
    """
    Multi-tier memory system for Marcus.
    
    Tiers:
    - Working Memory: Current state and active tasks
    - Episodic Memory: Specific task execution records
    - Semantic Memory: Extracted facts and patterns
    - Procedural Memory: Learned workflows and strategies
    """
    
    def __init__(self, events: Optional[Events] = None, persistence: Optional[Persistence] = None):
        """
        Initialize the Memory system.
        
        Args:
            events: Optional Events system for integration
            persistence: Optional Persistence for long-term storage
        """
        self.events = events
        self.persistence = persistence
        
        # Working Memory (volatile, current state)
        self.working = {
            "active_tasks": {},  # agent_id -> current task
            "recent_events": [],  # last N events
            "system_state": {}    # current system metrics
        }
        
        # Episodic Memory (task execution history)
        self.episodic = {
            "outcomes": [],  # List of TaskOutcome
            "timeline": defaultdict(list)  # date -> events
        }
        
        # Semantic Memory (learned facts)
        self.semantic = {
            "agent_profiles": {},  # agent_id -> AgentProfile
            "task_patterns": {},   # pattern_id -> TaskPattern
            "success_factors": {}  # factor -> impact
        }
        
        # Procedural Memory (workflows and strategies)
        self.procedural = {
            "workflows": {},      # workflow_id -> steps
            "strategies": {},     # situation -> strategy
            "optimizations": {}   # pattern -> optimization
        }
        
        # Learning parameters
        self.learning_rate = 0.1
        self.memory_decay = 0.95  # How much to weight recent vs old experiences
        
        # Load persisted memory if available
        if self.persistence:
            asyncio.create_task(self._load_persisted_memory())
            
    async def _load_persisted_memory(self):
        """Load memory from persistence"""
        try:
            # Load recent outcomes
            outcomes_data = await self.persistence.query("task_outcomes", limit=500)
            for data in outcomes_data:
                # Reconstruct TaskOutcome
                outcome = TaskOutcome(
                    task_id=data["task_id"],
                    agent_id=data["agent_id"],
                    task_name=data["task_name"],
                    estimated_hours=data["estimated_hours"],
                    actual_hours=data["actual_hours"],
                    success=data["success"],
                    blockers=data.get("blockers", []),
                    started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
                    completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
                )
                self.episodic["outcomes"].append(outcome)
                
            # Load agent profiles
            profiles_data = await self.persistence.query("agent_profiles", limit=100)
            for data in profiles_data:
                self.semantic["agent_profiles"][data["agent_id"]] = AgentProfile(**data)
                
            logger.info(f"Loaded {len(self.episodic['outcomes'])} outcomes and {len(self.semantic['agent_profiles'])} profiles from memory")
            
        except Exception as e:
            logger.error(f"Failed to load persisted memory: {e}")
            
    async def record_task_start(self, agent_id: str, task: Task) -> None:
        """Record that an agent started a task"""
        # Update working memory
        self.working["active_tasks"][agent_id] = {
            "task": task,
            "started_at": datetime.now(),
            "events": []
        }
        
        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.TASK_STARTED,
                agent_id,
                {
                    "task_id": task.id,
                    "task_name": task.name,
                    "estimated_hours": task.estimated_hours
                }
            )
            
    async def record_task_completion(self, agent_id: str, task_id: str, 
                                   success: bool, actual_hours: float,
                                   blockers: List[str] = None) -> TaskOutcome:
        """Record task completion and learn from it"""
        # Get task info from working memory
        active_task = self.working["active_tasks"].get(agent_id, {})
        if not active_task or active_task["task"].id != task_id:
            logger.warning(f"No active task found for agent {agent_id}")
            return None
            
        task = active_task["task"]
        started_at = active_task["started_at"]
        
        # Create outcome record
        outcome = TaskOutcome(
            task_id=task_id,
            agent_id=agent_id,
            task_name=task.name,
            estimated_hours=task.estimated_hours,
            actual_hours=actual_hours,
            success=success,
            blockers=blockers or [],
            started_at=started_at,
            completed_at=datetime.now()
        )
        
        # Store in episodic memory
        self.episodic["outcomes"].append(outcome)
        self.episodic["timeline"][datetime.now().date()].append(outcome)
        
        # Update semantic memory (agent profile)
        await self._update_agent_profile(agent_id, outcome, task)
        
        # Learn patterns
        await self._learn_task_patterns(outcome, task)
        
        # Persist if available
        if self.persistence:
            await self.persistence.store(
                "task_outcomes",
                f"{task_id}_{agent_id}_{datetime.now().timestamp()}",
                outcome.to_dict()
            )
            
        # Clear from working memory
        del self.working["active_tasks"][agent_id]
        
        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.TASK_COMPLETED,
                agent_id,
                outcome.to_dict()
            )
            
        return outcome
        
    async def _update_agent_profile(self, agent_id: str, outcome: TaskOutcome, task: Task) -> None:
        """Update agent's learned profile"""
        if agent_id not in self.semantic["agent_profiles"]:
            self.semantic["agent_profiles"][agent_id] = AgentProfile(agent_id=agent_id)
            
        profile = self.semantic["agent_profiles"][agent_id]
        
        # Update basic stats
        profile.total_tasks += 1
        if outcome.success:
            profile.successful_tasks += 1
        else:
            profile.failed_tasks += 1
            
        if outcome.blockers:
            profile.blocked_tasks += 1
            for blocker in outcome.blockers:
                profile.common_blockers[blocker] = profile.common_blockers.get(blocker, 0) + 1
                
        # Update skill success rates
        if task.labels:
            for label in task.labels:
                if label not in profile.skill_success_rates:
                    profile.skill_success_rates[label] = 0.0
                    
                # Exponential moving average
                old_rate = profile.skill_success_rates[label]
                new_value = 1.0 if outcome.success else 0.0
                profile.skill_success_rates[label] = (
                    old_rate * (1 - self.learning_rate) + new_value * self.learning_rate
                )
                
        # Update estimation accuracy
        old_accuracy = profile.average_estimation_accuracy
        profile.average_estimation_accuracy = (
            old_accuracy * (1 - self.learning_rate) + 
            outcome.estimation_accuracy * self.learning_rate
        )
        
        # Persist profile
        if self.persistence:
            await self.persistence.store(
                "agent_profiles",
                agent_id,
                profile.__dict__
            )
            
    async def _learn_task_patterns(self, outcome: TaskOutcome, task: Task) -> None:
        """Learn patterns from task execution"""
        # Pattern key based on task labels
        if task.labels:
            pattern_key = "_".join(sorted(task.labels))
            
            if pattern_key not in self.semantic["task_patterns"]:
                self.semantic["task_patterns"][pattern_key] = TaskPattern(
                    pattern_type=pattern_key,
                    task_labels=task.labels,
                    average_duration=outcome.actual_hours,
                    success_rate=1.0 if outcome.success else 0.0,
                    common_blockers=outcome.blockers,
                    prerequisites=[],
                    best_agents=[outcome.agent_id] if outcome.success else []
                )
            else:
                pattern = self.semantic["task_patterns"][pattern_key]
                
                # Update average duration
                pattern.average_duration = (
                    pattern.average_duration * 0.9 + outcome.actual_hours * 0.1
                )
                
                # Update success rate
                pattern.success_rate = (
                    pattern.success_rate * 0.9 + (1.0 if outcome.success else 0.0) * 0.1
                )
                
                # Track successful agents
                if outcome.success and outcome.agent_id not in pattern.best_agents:
                    pattern.best_agents.append(outcome.agent_id)
                    
    async def predict_task_outcome(self, agent_id: str, task: Task) -> Dict[str, Any]:
        """
        Predict likely outcome for agent-task combination.
        
        Returns:
            Dictionary with predictions:
            - success_probability: 0-1
            - estimated_duration: hours
            - blockage_risk: 0-1
            - risk_factors: list of potential issues
        """
        predictions = {
            "success_probability": 0.5,  # Default
            "estimated_duration": task.estimated_hours,
            "blockage_risk": 0.3,
            "risk_factors": []
        }
        
        # Get agent profile
        if agent_id in self.semantic["agent_profiles"]:
            profile = self.semantic["agent_profiles"][agent_id]
            
            # Base success probability on agent's overall rate
            predictions["success_probability"] = profile.success_rate
            
            # Adjust based on skill match
            if task.labels:
                skill_matches = [
                    profile.skill_success_rates.get(label, 0.5)
                    for label in task.labels
                ]
                if skill_matches:
                    predictions["success_probability"] = sum(skill_matches) / len(skill_matches)
                    
            # Predict blockage risk
            predictions["blockage_risk"] = profile.blockage_rate
            
            # Duration adjustment based on estimation accuracy
            if profile.average_estimation_accuracy > 0:
                predictions["estimated_duration"] = (
                    task.estimated_hours / profile.average_estimation_accuracy
                )
                
        # Check task patterns
        if task.labels:
            pattern_key = "_".join(sorted(task.labels))
            if pattern_key in self.semantic["task_patterns"]:
                pattern = self.semantic["task_patterns"][pattern_key]
                
                # Use pattern data if more reliable
                predictions["estimated_duration"] = pattern.average_duration
                predictions["risk_factors"].extend(pattern.common_blockers)
                
        return predictions
        
    async def find_similar_outcomes(self, task: Task, limit: int = 5) -> List[TaskOutcome]:
        """Find similar past task executions"""
        similar = []
        
        for outcome in reversed(self.episodic["outcomes"]):  # Recent first
            # Simple similarity based on task name and labels
            similarity = 0.0
            
            # Name similarity (simple word overlap)
            task_words = set(task.name.lower().split())
            outcome_words = set(outcome.task_name.lower().split())
            if task_words and outcome_words:
                similarity += len(task_words & outcome_words) / len(task_words | outcome_words)
                
            similar.append((similarity, outcome))
            
        # Sort by similarity and return top N
        similar.sort(key=lambda x: x[0], reverse=True)
        return [outcome for _, outcome in similar[:limit]]
        
    def get_working_memory_summary(self) -> Dict[str, Any]:
        """Get current working memory state"""
        return {
            "active_agents": len(self.working["active_tasks"]),
            "active_tasks": [
                {
                    "agent_id": agent_id,
                    "task_name": info["task"].name,
                    "duration": (datetime.now() - info["started_at"]).total_seconds() / 3600
                }
                for agent_id, info in self.working["active_tasks"].items()
            ]
        }
        
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "working_memory": {
                "active_tasks": len(self.working["active_tasks"]),
                "recent_events": len(self.working["recent_events"])
            },
            "episodic_memory": {
                "total_outcomes": len(self.episodic["outcomes"]),
                "days_tracked": len(self.episodic["timeline"])
            },
            "semantic_memory": {
                "agent_profiles": len(self.semantic["agent_profiles"]),
                "task_patterns": len(self.semantic["task_patterns"])
            },
            "procedural_memory": {
                "workflows": len(self.procedural["workflows"]),
                "strategies": len(self.procedural["strategies"])
            }
        }