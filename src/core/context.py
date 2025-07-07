"""
Context System for Marcus

Provides rich context for task assignments including previous implementations,
dependency awareness, and relevant patterns. Enhances agent effectiveness by
reducing time spent understanding existing code and architectural decisions.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
import logging

from src.core.models import Task, TaskStatus
from src.core.events import Events, EventTypes
from src.core.resilience import with_fallback, resilient_persistence

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """Complete context for a task assignment"""
    task_id: str
    previous_implementations: Dict[str, Any] = field(default_factory=dict)
    dependent_tasks: List[Dict[str, Any]] = field(default_factory=list)
    related_patterns: List[Dict[str, Any]] = field(default_factory=list)
    architectural_decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "task_id": self.task_id,
            "previous_implementations": self.previous_implementations,
            "dependent_tasks": self.dependent_tasks,
            "related_patterns": self.related_patterns,
            "architectural_decisions": self.architectural_decisions
        }


@dataclass
class DependentTask:
    """Information about a task that depends on another"""
    task_id: str
    task_name: str
    expected_interface: str
    dependency_type: str = "functional"  # functional, data, temporal
    

@dataclass
class Decision:
    """An architectural decision made during development"""
    decision_id: str
    task_id: str
    agent_id: str
    timestamp: datetime
    what: str  # What was decided
    why: str   # Why it was decided
    impact: str  # Impact on other components
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "decision_id": self.decision_id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "what": self.what,
            "why": self.why,
            "impact": self.impact
        }


class Context:
    """
    Manages context for task assignments.
    
    Features:
    - Tracks implementations from completed tasks
    - Identifies dependent tasks
    - Stores architectural decisions
    - Provides rich context for new assignments
    - Optional persistence for long-term storage
    """
    
    def __init__(self, events: Optional[Events] = None, persistence=None):
        """
        Initialize the Context system.
        
        Args:
            events: Optional Events system for integration
            persistence: Optional Persistence instance for storing context
        """
        self.events = events
        self.persistence = persistence
        self.implementations: Dict[str, Dict[str, Any]] = {}  # task_id -> implementation details
        self.dependencies: Dict[str, List[DependentTask]] = {}  # task_id -> dependent tasks
        self.decisions: List[Decision] = []
        self.patterns: Dict[str, List[Dict[str, Any]]] = {}  # pattern_type -> examples
        self._decision_counter = 0
        
        # Load persisted data if available
        if self.persistence:
            asyncio.create_task(self._load_persisted_data())
    
    async def _load_persisted_data(self):
        """Load persisted decisions from storage"""
        try:
            # Load recent decisions
            persisted_decisions = await self.persistence.get_decisions(limit=100)
            for decision in persisted_decisions:
                if decision not in self.decisions:
                    self.decisions.append(decision)
                    
            # Update decision counter
            if self.decisions:
                max_id = max(int(d.decision_id.split('_')[1]) for d in self.decisions)
                self._decision_counter = max_id
                
            logger.info(f"Loaded {len(persisted_decisions)} decisions from persistence")
        except Exception as e:
            logger.error(f"Failed to load persisted data: {e}")
        
    async def add_implementation(self, task_id: str, implementation: Dict[str, Any]) -> None:
        """
        Add implementation details from a completed task.
        
        Args:
            task_id: ID of the completed task
            implementation: Details about the implementation (APIs, models, patterns)
        """
        self.implementations[task_id] = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            **implementation
        }
        
        # Persist implementation if available (with graceful degradation)
        if self.persistence:
            await self._persist_implementation_safe(task_id)
        
        # Extract patterns for future use
        if "patterns" in implementation:
            for pattern in implementation["patterns"]:
                pattern_type = pattern.get("type", "general")
                if pattern_type not in self.patterns:
                    self.patterns[pattern_type] = []
                self.patterns[pattern_type].append({
                    "task_id": task_id,
                    "pattern": pattern
                })
                
        # Emit event if events system is available
        if self.events:
            await self.events.publish(
                EventTypes.IMPLEMENTATION_FOUND,
                "context",
                {
                    "task_id": task_id,
                    "implementation": implementation
                }
            )
            
        logger.debug(f"Added implementation context for task {task_id}")
        
    def add_dependency(self, task_id: str, dependent_task: DependentTask) -> None:
        """
        Record that one task depends on another.
        
        Args:
            task_id: The task being depended upon
            dependent_task: Information about the dependent task
        """
        if task_id not in self.dependencies:
            self.dependencies[task_id] = []
        self.dependencies[task_id].append(dependent_task)
        
        logger.debug(f"Added dependency: {dependent_task.task_name} depends on {task_id}")
        
    async def log_decision(self, agent_id: str, task_id: str, 
                          what: str, why: str, impact: str) -> Decision:
        """
        Log an architectural decision made by an agent.
        
        Args:
            agent_id: ID of the agent making the decision
            task_id: Current task ID
            what: What was decided
            why: Reasoning behind the decision
            impact: Expected impact on other components
            
        Returns:
            The logged Decision object
        """
        self._decision_counter += 1
        decision = Decision(
            decision_id=f"dec_{self._decision_counter}_{datetime.now().timestamp()}",
            task_id=task_id,
            agent_id=agent_id,
            timestamp=datetime.now(),
            what=what,
            why=why,
            impact=impact
        )
        
        self.decisions.append(decision)
        
        # Persist decision if persistence is available (with graceful degradation)
        if self.persistence:
            await self._persist_decision_safe(decision)
        
        # Cross-reference to dependent tasks
        if task_id in self.dependencies:
            for dep_task in self.dependencies[task_id]:
                logger.info(f"Decision affects dependent task: {dep_task.task_name}")
                
        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.DECISION_LOGGED,
                agent_id,
                decision.to_dict()
            )
            
        return decision
        
    async def get_context(self, task_id: str, task_dependencies: List[str]) -> TaskContext:
        """
        Get complete context for a task assignment.
        
        Args:
            task_id: The task being assigned
            task_dependencies: IDs of tasks this task depends on
            
        Returns:
            Complete context for the task
        """
        context = TaskContext(task_id=task_id)
        
        # Get implementations from dependencies
        for dep_id in task_dependencies:
            if dep_id in self.implementations:
                context.previous_implementations[dep_id] = self.implementations[dep_id]
                
        # Get tasks that depend on this one
        if task_id in self.dependencies:
            context.dependent_tasks = [
                {
                    "task_id": dep.task_id,
                    "task_name": dep.task_name,
                    "expected_interface": dep.expected_interface,
                    "dependency_type": dep.dependency_type
                }
                for dep in self.dependencies[task_id]
            ]
            
        # Get relevant patterns
        # For now, include all patterns - could be smarter about filtering
        for pattern_type, examples in self.patterns.items():
            context.related_patterns.extend(examples[:3])  # Limit to 3 most recent
            
        # Get relevant architectural decisions
        relevant_decisions = []
        # Include decisions from dependencies
        for dep_id in task_dependencies:
            relevant_decisions.extend([
                d.to_dict() for d in self.decisions 
                if d.task_id == dep_id
            ])
        # Include decisions that might affect this task
        for decision in self.decisions:
            if task_id in decision.impact:
                relevant_decisions.append(decision.to_dict())
                
        context.architectural_decisions = relevant_decisions[-5:]  # Last 5 relevant
        
        # Emit event
        if self.events:
            await self.events.publish(
                EventTypes.CONTEXT_UPDATED,
                "context",
                {
                    "task_id": task_id,
                    "context_size": {
                        "implementations": len(context.previous_implementations),
                        "dependents": len(context.dependent_tasks),
                        "patterns": len(context.related_patterns),
                        "decisions": len(context.architectural_decisions)
                    }
                }
            )
            
        return context
        
    def analyze_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Analyze task list to identify dependencies.
        
        Args:
            tasks: List of all tasks
            
        Returns:
            Mapping of task_id to list of dependent task IDs
        """
        dependency_map: Dict[str, List[str]] = {}
        
        for task in tasks:
            # Direct dependencies from task model
            if task.dependencies:
                for dep_id in task.dependencies:
                    if dep_id not in dependency_map:
                        dependency_map[dep_id] = []
                    dependency_map[dep_id].append(task.id)
                    
            # Infer dependencies from labels/tags
            # For example, "frontend-login" might depend on "backend-auth"
            if task.labels:
                for other_task in tasks:
                    if other_task.id != task.id and self._infer_dependency(task, other_task):
                        if other_task.id not in dependency_map:
                            dependency_map[other_task.id] = []
                        if task.id not in dependency_map[other_task.id]:
                            dependency_map[other_task.id].append(task.id)
                            
        return dependency_map
        
    def _infer_dependency(self, task: Task, potential_dependency: Task) -> bool:
        """
        Infer if task depends on potential_dependency based on labels/names.
        
        Args:
            task: The task to check
            potential_dependency: The potential dependency
            
        Returns:
            True if dependency is likely
        """
        # Simple heuristics - can be enhanced
        inference_rules = [
            # Frontend depends on backend
            (["frontend", "ui", "client"], ["backend", "api", "server"]),
            # Tests depend on implementation
            (["test", "spec"], ["implement", "feature", "api"]),
            # Integration depends on individual components
            (["integration", "e2e"], ["component", "service", "module"]),
            # Documentation depends on implementation
            (["docs", "documentation"], ["implement", "feature"]),
        ]
        
        task_labels = set(label.lower() for label in (task.labels or []))
        task_name_words = set(task.name.lower().split())
        dep_labels = set(label.lower() for label in (potential_dependency.labels or []))
        dep_name_words = set(potential_dependency.name.lower().split())
        
        for dependent_keywords, dependency_keywords in inference_rules:
            if (any(kw in task_labels or kw in task_name_words for kw in dependent_keywords) and
                any(kw in dep_labels or kw in dep_name_words for kw in dependency_keywords)):
                return True
                
        return False
        
    def get_decisions_for_task(self, task_id: str) -> List[Decision]:
        """
        Get all decisions related to a specific task.
        
        Args:
            task_id: The task ID
            
        Returns:
            List of related decisions
        """
        return [d for d in self.decisions if d.task_id == task_id]
        
    @with_fallback(lambda self, task_id: logger.warning(f"Failed to persist implementation for {task_id}"))
    async def _persist_implementation_safe(self, task_id: str):
        """Persist implementation with graceful degradation"""
        await self.persistence.store(
            "implementations",
            task_id,
            self.implementations[task_id]
        )
    
    @with_fallback(lambda self, decision: logger.warning(f"Failed to persist decision {decision.id}"))
    async def _persist_decision_safe(self, decision: Decision):
        """Persist decision with graceful degradation"""
        await self.persistence.store(
            "decisions",
            decision.id,
            decision.__dict__
        )
    
    def get_implementation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all tracked implementations.
        
        Returns:
            Summary statistics and recent implementations
        """
        return {
            "total_implementations": len(self.implementations),
            "total_decisions": len(self.decisions),
            "pattern_types": list(self.patterns.keys()),
            "recent_implementations": list(self.implementations.values())[-5:],
            "tasks_with_dependents": len(self.dependencies)
        }
        
    def clear_old_data(self, days: int = 30) -> None:
        """
        Clear context data older than specified days.
        
        Args:
            days: Number of days to retain
        """
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        # Clear old implementations
        self.implementations = {
            k: v for k, v in self.implementations.items()
            if datetime.fromisoformat(v["timestamp"]).timestamp() > cutoff
        }
        
        # Clear old decisions
        self.decisions = [
            d for d in self.decisions
            if d.timestamp.timestamp() > cutoff
        ]
        
        logger.info(f"Cleared context data older than {days} days")