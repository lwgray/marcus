"""
Dynamic Context Injection System

Provides runtime context updates for agents based on:
- Task changes
- Capability updates  
- Project evolution
- Performance feedback
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import json

from .tools.handshake import IntegrationContract, AgentType
from .protocol_extensions import ContextInjection, protocol_handler


class ContextTrigger(Enum):
    """Triggers for context injection."""
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    CAPABILITY_ADDED = "capability_added"
    ERROR_PATTERN = "error_pattern"
    PERFORMANCE_ISSUE = "performance_issue"
    PROJECT_PHASE_CHANGE = "project_phase_change"
    DEPENDENCY_AVAILABLE = "dependency_available"
    SCHEDULE_PRESSURE = "schedule_pressure"


@dataclass
class ContextRule:
    """Rule for dynamic context injection."""
    trigger: ContextTrigger
    condition: Callable[[Dict[str, Any]], bool]
    context_type: str
    context_generator: Callable[[Dict[str, Any]], Dict[str, Any]]
    priority: str = "normal"
    agent_types: List[AgentType] = field(default_factory=lambda: list(AgentType))
    expiry: Optional[datetime] = None
    
    def matches(self, trigger_data: Dict[str, Any]) -> bool:
        """Check if this rule matches the trigger data."""
        return self.condition(trigger_data)
    
    def generate_context(self, trigger_data: Dict[str, Any]) -> ContextInjection:
        """Generate context injection from trigger data."""
        context_data = self.context_generator(trigger_data)
        
        return ContextInjection(
            agent_id=trigger_data.get("agent_id", ""),
            context_type=self.context_type,
            context_data=context_data,
            action="add",
            priority=self.priority
        )


class DynamicContextManager:
    """Manages dynamic context injection for agents."""
    
    def __init__(self):
        self.injection_rules: List[ContextRule] = []
        self.active_contexts: Dict[str, List[ContextInjection]] = {}  # agent_id -> injections
        self.injection_history: Dict[str, List[Dict[str, Any]]] = {}
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default context injection rules."""
        
        # Task assignment context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.TASK_ASSIGNED,
                condition=lambda data: data.get("task_type") == "backend",
                context_type="behavioral_rules",
                context_generator=lambda data: {
                    "rules": [
                        "Focus on API design and database optimization",
                        "Implement comprehensive error handling",
                        "Write integration tests for all endpoints"
                    ]
                },
                agent_types=[AgentType.BACKEND, AgentType.FULLSTACK]
            )
        )
        
        # Frontend task context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.TASK_ASSIGNED,
                condition=lambda data: data.get("task_type") == "frontend",
                context_type="behavioral_rules",
                context_generator=lambda data: {
                    "rules": [
                        "Prioritize user experience and accessibility",
                        "Implement responsive design patterns",
                        "Optimize for performance and loading times"
                    ]
                },
                agent_types=[AgentType.FRONTEND, AgentType.FULLSTACK]
            )
        )
        
        # Testing capability context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.CAPABILITY_ADDED,
                condition=lambda data: "testing" in data.get("capabilities", []),
                context_type="system_prompt",
                context_generator=lambda data: {
                    "content": """
## Enhanced Testing Context

You now have enhanced testing capabilities. Follow these patterns:
- Write tests before implementation (TDD)
- Aim for 80%+ test coverage
- Include unit, integration, and e2e tests
- Mock external dependencies appropriately
- Use descriptive test names and assertions
"""
                },
                priority="high"
            )
        )
        
        # Error pattern context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.ERROR_PATTERN,
                condition=lambda data: data.get("error_type") == "authentication",
                context_type="behavioral_rules",
                context_generator=lambda data: {
                    "rules": [
                        "Always validate authentication tokens",
                        "Implement proper session management",
                        "Use secure authentication patterns (JWT, OAuth)",
                        "Handle authentication failures gracefully"
                    ]
                },
                priority="high"
            )
        )
        
        # Performance issue context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.PERFORMANCE_ISSUE,
                condition=lambda data: data.get("issue_type") == "database",
                context_type="behavioral_rules",
                context_generator=lambda data: {
                    "rules": [
                        "Optimize database queries and use indexes",
                        "Implement query result caching where appropriate",
                        "Use database connection pooling",
                        "Monitor query performance and execution plans"
                    ]
                },
                priority="high",
                expiry=datetime.utcnow() + timedelta(hours=4)
            )
        )
        
        # Schedule pressure context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.SCHEDULE_PRESSURE,
                condition=lambda data: data.get("time_remaining_hours", 999) < 8,
                context_type="behavioral_rules",
                context_generator=lambda data: {
                    "rules": [
                        "Focus on MVP features and core functionality",
                        "Defer non-critical optimizations",
                        "Increase progress reporting frequency",
                        "Highlight any blockers immediately"
                    ]
                },
                priority="critical",
                expiry=datetime.utcnow() + timedelta(hours=8)
            )
        )
        
        # Dependency available context
        self.injection_rules.append(
            ContextRule(
                trigger=ContextTrigger.DEPENDENCY_AVAILABLE,
                condition=lambda data: data.get("dependency_type") == "api",
                context_type="system_prompt",
                context_generator=lambda data: {
                    "content": f"""
## Dependency Now Available

The {data.get('dependency_name', 'external API')} is now available for integration.
You can proceed with implementation that was previously blocked.

Integration endpoint: {data.get('endpoint', 'check documentation')}
Expected response format: {data.get('response_format', 'JSON')}
"""
                },
                priority="high"
            )
        )
    
    async def process_trigger(
        self, trigger: ContextTrigger, trigger_data: Dict[str, Any]
    ) -> List[ContextInjection]:
        """Process a trigger and generate context injections."""
        
        injections = []
        agent_id = trigger_data.get("agent_id")
        
        if not agent_id:
            return injections
        
        # Find matching rules
        for rule in self.injection_rules:
            if rule.trigger == trigger and rule.matches(trigger_data):
                
                # Check agent type compatibility if specified
                if rule.agent_types:
                    agent_contract = protocol_handler.agent_contracts.get(agent_id)
                    if agent_contract and agent_contract.agent_type not in rule.agent_types:
                        continue
                
                # Check if rule has expired
                if rule.expiry and datetime.utcnow() > rule.expiry:
                    continue
                
                # Generate injection
                injection = rule.generate_context(trigger_data)
                injections.append(injection)
        
        # Apply injections
        for injection in injections:
            await self._apply_injection(injection)
        
        return injections
    
    async def _apply_injection(self, injection: ContextInjection) -> None:
        """Apply context injection to agent."""
        
        # Store injection
        if injection.agent_id not in self.active_contexts:
            self.active_contexts[injection.agent_id] = []
        
        self.active_contexts[injection.agent_id].append(injection)
        
        # Apply through protocol handler
        try:
            result = await protocol_handler.inject_context(injection)
            
            # Log to history
            if injection.agent_id not in self.injection_history:
                self.injection_history[injection.agent_id] = []
            
            self.injection_history[injection.agent_id].append({
                "injection": injection.__dict__,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            print(f"Failed to apply context injection: {e}")
    
    async def trigger_task_assignment(
        self, agent_id: str, task_data: Dict[str, Any]
    ) -> List[ContextInjection]:
        """Trigger context injection for task assignment."""
        trigger_data = {
            "agent_id": agent_id,
            "task_type": task_data.get("task_type"),
            "task_complexity": task_data.get("complexity", "medium"),
            "task_priority": task_data.get("priority", "normal"),
            "estimated_hours": task_data.get("estimated_hours", 8)
        }
        
        return await self.process_trigger(ContextTrigger.TASK_ASSIGNED, trigger_data)
    
    async def trigger_capability_update(
        self, agent_id: str, added_capabilities: List[str]
    ) -> List[ContextInjection]:
        """Trigger context injection for capability updates."""
        trigger_data = {
            "agent_id": agent_id,
            "capabilities": added_capabilities
        }
        
        return await self.process_trigger(ContextTrigger.CAPABILITY_ADDED, trigger_data)
    
    async def trigger_error_pattern(
        self, agent_id: str, error_type: str, error_details: Dict[str, Any]
    ) -> List[ContextInjection]:
        """Trigger context injection for error patterns."""
        trigger_data = {
            "agent_id": agent_id,
            "error_type": error_type,
            "error_frequency": error_details.get("frequency", 1),
            "error_impact": error_details.get("impact", "medium")
        }
        
        return await self.process_trigger(ContextTrigger.ERROR_PATTERN, trigger_data)
    
    async def trigger_performance_issue(
        self, agent_id: str, issue_type: str, metrics: Dict[str, Any]
    ) -> List[ContextInjection]:
        """Trigger context injection for performance issues."""
        trigger_data = {
            "agent_id": agent_id,
            "issue_type": issue_type,
            "response_time": metrics.get("response_time", 0),
            "cpu_usage": metrics.get("cpu_usage", 0),
            "memory_usage": metrics.get("memory_usage", 0)
        }
        
        return await self.process_trigger(ContextTrigger.PERFORMANCE_ISSUE, trigger_data)
    
    async def trigger_dependency_available(
        self, agent_id: str, dependency_name: str, integration_info: Dict[str, Any]
    ) -> List[ContextInjection]:
        """Trigger context injection when dependency becomes available."""
        trigger_data = {
            "agent_id": agent_id,
            "dependency_name": dependency_name,
            "dependency_type": integration_info.get("type", "api"),
            "endpoint": integration_info.get("endpoint"),
            "response_format": integration_info.get("response_format", "JSON")
        }
        
        return await self.process_trigger(ContextTrigger.DEPENDENCY_AVAILABLE, trigger_data)
    
    def add_custom_rule(self, rule: ContextRule) -> None:
        """Add a custom context injection rule."""
        self.injection_rules.append(rule)
    
    def get_agent_context_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get context injection history for an agent."""
        return self.injection_history.get(agent_id, [])
    
    def get_active_contexts(self, agent_id: str) -> List[ContextInjection]:
        """Get active context injections for an agent."""
        return self.active_contexts.get(agent_id, [])
    
    async def cleanup_expired_contexts(self) -> None:
        """Clean up expired context injections."""
        current_time = datetime.utcnow()
        
        for agent_id, contexts in self.active_contexts.items():
            # Remove expired contexts
            active_contexts = [
                ctx for ctx in contexts 
                if not hasattr(ctx, 'expiry') or not ctx.expiry or ctx.expiry > current_time
            ]
            self.active_contexts[agent_id] = active_contexts


# Global context manager instance
context_manager = DynamicContextManager()


# Convenience functions for common triggers
async def inject_task_context(agent_id: str, task_data: Dict[str, Any]) -> List[ContextInjection]:
    """Inject context for task assignment."""
    return await context_manager.trigger_task_assignment(agent_id, task_data)


async def inject_capability_context(agent_id: str, capabilities: List[str]) -> List[ContextInjection]:
    """Inject context for capability updates."""
    return await context_manager.trigger_capability_update(agent_id, capabilities)


async def inject_error_context(agent_id: str, error_type: str, error_details: Dict[str, Any]) -> List[ContextInjection]:
    """Inject context for error patterns.""" 
    return await context_manager.trigger_error_pattern(agent_id, error_type, error_details)


async def inject_dependency_context(agent_id: str, dependency: str, info: Dict[str, Any]) -> List[ContextInjection]:
    """Inject context when dependency becomes available."""
    return await context_manager.trigger_dependency_available(agent_id, dependency, info)