"""
Event-Integrated Pipeline Visualizer

Connects the Events system to the visualization pipeline for real-time updates
without polling. This provides instant visualization updates when tasks change.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from src.core.events import Events, EventTypes, Event
from src.core.models import TaskStatus
from src.visualization.shared_pipeline_events import SharedPipelineEvents
from src.visualization.pipeline_flow import PipelineStage

logger = logging.getLogger(__name__)


class EventIntegratedVisualizer:
    """
    Bridges the Events system with the visualization pipeline and enhanced systems.
    
    Instead of polling for updates, this subscribes to events and
    updates the visualization in real-time. Integrates with Context, Memory,
    and Dependency systems to provide comprehensive project intelligence.
    """
    
    def __init__(self, events_system: Optional[Events] = None, 
                 context_system=None, memory_system=None):
        """
        Initialize the event-integrated visualizer.
        
        Args:
            events_system: The Events system to subscribe to
            context_system: The Context system for dependency and decision insights
            memory_system: The Memory system for predictions and learning insights
        """
        self.events = events_system
        self.context = context_system
        self.memory = memory_system
        self.shared_pipeline = SharedPipelineEvents()
        self.active_flows: Dict[str, Dict[str, Any]] = {}
        self._subscribed = False
        
        # Enhanced tracking for integrated systems
        self.context_insights: Dict[str, Any] = {}
        self.memory_predictions: Dict[str, Any] = {}
        self.dependency_analysis: Dict[str, Any] = {}
        self.system_correlations: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """Initialize and subscribe to events"""
        if self.events and not self._subscribed:
            # Subscribe to all relevant events
            event_types = [
                EventTypes.PROJECT_CREATED,
                EventTypes.TASK_REQUESTED,
                EventTypes.TASK_ASSIGNED,
                EventTypes.TASK_STARTED,
                EventTypes.TASK_PROGRESS,
                EventTypes.TASK_COMPLETED,
                EventTypes.TASK_BLOCKED,
                EventTypes.AGENT_REGISTERED,
                EventTypes.AGENT_STATUS_CHANGED,
                EventTypes.CONTEXT_UPDATED,
                EventTypes.DECISION_LOGGED,
            ]
            
            for event_type in event_types:
                self.events.subscribe(event_type, self._handle_event)
                
            # Also subscribe to all events for catch-all
            self.events.subscribe("*", self._handle_any_event)
            
            self._subscribed = True
            logger.info("Visualization subscribed to Events system")
            
    async def _handle_event(self, event: Event):
        """Handle specific events and update visualization"""
        try:
            # Map event types to pipeline stages
            stage_mapping = {
                EventTypes.PROJECT_CREATED: PipelineStage.PRD_ANALYSIS,
                EventTypes.TASK_REQUESTED: PipelineStage.TASK_MATCHING,
                EventTypes.TASK_ASSIGNED: PipelineStage.ASSIGNMENT,
                EventTypes.TASK_STARTED: PipelineStage.EXECUTION,
                EventTypes.TASK_PROGRESS: PipelineStage.EXECUTION,
                EventTypes.TASK_COMPLETED: PipelineStage.COMPLETION,
                EventTypes.TASK_BLOCKED: PipelineStage.EXECUTION,
            }
            
            stage = stage_mapping.get(event.event_type, PipelineStage.ORCHESTRATION)
            
            # Create or get flow ID
            flow_id = self._get_or_create_flow(event)
            
            # Convert event to pipeline format
            pipeline_event = {
                "event_id": event.event_id,
                "stage": stage.value,
                "event_type": event.event_type,
                "actor": event.source,
                "action": self._get_action_from_event(event),
                "details": event.data,
                "metadata": {
                    **event.metadata,
                    "original_event_type": event.event_type,
                    "timestamp": event.timestamp.isoformat()
                }
            }
            
            # Add special handling for different event types
            if event.event_type == EventTypes.TASK_ASSIGNED:
                pipeline_event["task_info"] = {
                    "task_id": event.data.get("task_id"),
                    "task_name": event.data.get("task_name"),
                    "agent_id": event.data.get("agent_id"),
                    "has_context": event.data.get("has_context", False),
                    "has_predictions": event.data.get("has_predictions", False)
                }
                
            elif event.event_type == EventTypes.TASK_PROGRESS:
                pipeline_event["progress_info"] = {
                    "task_id": event.data.get("task_id"),
                    "progress": event.data.get("progress", 0),
                    "status": event.data.get("status"),
                    "message": event.data.get("message")
                }
                
            elif event.event_type == EventTypes.CONTEXT_UPDATED:
                pipeline_event["context_info"] = {
                    "task_id": event.data.get("task_id"),
                    "context_size": event.data.get("context_size", {})
                }
                
            # Add to shared pipeline
            self.shared_pipeline.add_event(flow_id, pipeline_event)
            
            # Update flow status
            if event.event_type == EventTypes.TASK_COMPLETED:
                # Check if all tasks are completed
                if self._check_flow_completion(flow_id):
                    self.shared_pipeline.complete_flow(flow_id)
                    
        except Exception as e:
            logger.error(f"Error handling event {event.event_type}: {e}")
            
    async def _handle_any_event(self, event: Event):
        """Handle any event for logging and monitoring"""
        # Log all events for debugging
        logger.debug(f"Event: {event.event_type} from {event.source}")
        
        # Track event statistics
        if not hasattr(self, "_event_stats"):
            self._event_stats = {}
            
        if event.event_type not in self._event_stats:
            self._event_stats[event.event_type] = 0
        self._event_stats[event.event_type] += 1
        
    def _get_or_create_flow(self, event: Event) -> str:
        """Get or create a flow ID for the event"""
        # Try to extract flow ID from event data
        flow_id = event.data.get("flow_id")
        if flow_id:
            return flow_id
            
        # Try to get project/task context
        project_id = event.data.get("project_id")
        task_id = event.data.get("task_id")
        
        if project_id:
            flow_id = f"project_{project_id}"
        elif task_id:
            # Find flow by task
            for fid, flow in self.active_flows.items():
                if task_id in flow.get("tasks", []):
                    return fid
            # Create new flow for task
            flow_id = f"task_flow_{task_id}"
        else:
            # Default flow
            flow_id = "default_flow"
            
        # Create flow if it doesn't exist
        if flow_id not in self.active_flows:
            self.active_flows[flow_id] = {
                "created_at": datetime.now(),
                "tasks": [],
                "events": []
            }
            
            project_name = event.data.get("project_name", flow_id)
            self.shared_pipeline.add_flow(flow_id, project_name)
            
        # Track task if present
        if task_id and task_id not in self.active_flows[flow_id]["tasks"]:
            self.active_flows[flow_id]["tasks"].append(task_id)
            
        return flow_id
        
    def _get_action_from_event(self, event: Event) -> str:
        """Convert event type to human-readable action"""
        action_map = {
            EventTypes.PROJECT_CREATED: "Project created",
            EventTypes.TASK_REQUESTED: "Task requested",
            EventTypes.TASK_ASSIGNED: "Task assigned",
            EventTypes.TASK_STARTED: "Task started",
            EventTypes.TASK_PROGRESS: "Progress update",
            EventTypes.TASK_COMPLETED: "Task completed",
            EventTypes.TASK_BLOCKED: "Task blocked",
            EventTypes.AGENT_REGISTERED: "Agent registered",
            EventTypes.CONTEXT_UPDATED: "Context prepared",
            EventTypes.DECISION_LOGGED: "Decision logged",
        }
        
        return action_map.get(event.event_type, event.event_type.replace("_", " ").title())
        
    def _check_flow_completion(self, flow_id: str) -> bool:
        """Check if a flow is complete"""
        # Simple heuristic - could be enhanced
        flow = self.active_flows.get(flow_id, {})
        
        # If we have task tracking, check if all are done
        if "tasks" in flow and flow["tasks"]:
            # Would need to query task status
            # For now, return False
            return False
            
        # Otherwise, use event count heuristic
        event_count = len(flow.get("events", []))
        return event_count > 10  # Arbitrary threshold
        
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get statistics about processed events"""
        return {
            "subscribed": self._subscribed,
            "active_flows": len(self.active_flows),
            "event_counts": getattr(self, "_event_stats", {}),
            "total_events": sum(getattr(self, "_event_stats", {}).values())
        }
        
    async def create_context_visualization(self, task_id: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create visualization data for task context.
        
        This formats the context data for display in the UI.
        """
        viz_data = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "dependencies": {
                "explicit": [],
                "inferred": [],
                "dependent_tasks": []
            },
            "implementations": [],
            "decisions": [],
            "patterns": []
        }
        
        # Extract dependency information
        if "previous_implementations" in context_data:
            for impl_id, impl_data in context_data["previous_implementations"].items():
                viz_data["implementations"].append({
                    "task_id": impl_id,
                    "summary": self._summarize_implementation(impl_data),
                    "timestamp": impl_data.get("timestamp")
                })
                
        # Extract decisions
        if "architectural_decisions" in context_data:
            for decision in context_data["architectural_decisions"]:
                viz_data["decisions"].append({
                    "what": decision.get("what"),
                    "why": decision.get("why"),
                    "impact": decision.get("impact"),
                    "agent": decision.get("agent_id"),
                    "timestamp": decision.get("timestamp")
                })
                
        # Extract dependent tasks
        if "dependent_tasks" in context_data:
            for dep in context_data["dependent_tasks"]:
                viz_data["dependencies"]["dependent_tasks"].append({
                    "task_id": dep.get("task_id"),
                    "task_name": dep.get("task_name"),
                    "expected_interface": dep.get("expected_interface")
                })
                
        return viz_data
        
    def _summarize_implementation(self, impl_data: Dict[str, Any]) -> str:
        """Create a summary of implementation details"""
        summary_parts = []
        
        if "apis" in impl_data:
            summary_parts.append(f"{len(impl_data['apis'])} APIs")
        if "models" in impl_data:
            summary_parts.append(f"{len(impl_data['models'])} models")
        if "patterns" in impl_data:
            summary_parts.append(f"{len(impl_data['patterns'])} patterns")
            
        return ", ".join(summary_parts) if summary_parts else "Implementation details available"
    
    # ===== ENHANCED SYSTEM INTEGRATION METHODS =====
    
    async def get_context_insights(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive context insights from the Context system.
        
        Args:
            task_id: Optional specific task to analyze
            
        Returns:
            Context insights including dependencies, decisions, and knowledge flow
        """
        if not self.context:
            return {"error": "Context system not available"}
            
        insights = {
            "timestamp": datetime.now().isoformat(),
            "task_focus": task_id,
            "dependency_analysis": {},
            "decision_tracking": {},
            "knowledge_flow": {},
            "system_health": {}
        }
        
        try:
            # Get implementation summary
            impl_summary = self.context.get_implementation_summary()
            insights["system_health"] = {
                "total_implementations": impl_summary.get("total_implementations", 0),
                "total_decisions": impl_summary.get("total_decisions", 0),
                "pattern_types": impl_summary.get("pattern_types", []),
                "active_contexts": impl_summary.get("tasks_with_dependents", 0)
            }
            
            # Get recent decisions
            if task_id:
                decisions = self.context.get_decisions_for_task(task_id)
                insights["decision_tracking"] = {
                    "task_decisions": len(decisions),
                    "recent_decisions": [
                        {
                            "what": d.what,
                            "why": d.why,
                            "impact": d.impact,
                            "agent": d.agent_id,
                            "timestamp": d.timestamp.isoformat()
                        }
                        for d in decisions[-3:]  # Last 3 decisions
                    ]
                }
            
            # Calculate knowledge flow metrics
            insights["knowledge_flow"] = {
                "active_implementations": len(self.context.implementations),
                "cross_task_references": sum(
                    len(deps) for deps in self.context.dependencies.values()
                ),
                "pattern_reuse": len(self.context.patterns),
                "context_sharing_active": len(self.context.implementations) > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting context insights: {e}")
            insights["error"] = str(e)
            
        return insights
    
    async def get_memory_predictions(self, agent_id: Optional[str] = None, 
                                   task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive memory system predictions and learning insights.
        
        Args:
            agent_id: Optional specific agent to analyze
            task_id: Optional specific task to predict
            
        Returns:
            Memory insights including predictions, confidence, and learning patterns
        """
        if not self.memory:
            return {"error": "Memory system not available"}
            
        insights = {
            "timestamp": datetime.now().isoformat(),
            "agent_focus": agent_id,
            "task_focus": task_id,
            "system_intelligence": {},
            "agent_profiles": {},
            "prediction_accuracy": {},
            "learning_trends": {}
        }
        
        try:
            # Get system-wide intelligence metrics
            insights["system_intelligence"] = {
                "total_outcomes_tracked": len(self.memory.episodic.get("outcomes", [])),
                "total_agents_profiled": len(self.memory.semantic.get("agent_profiles", {})),
                "prediction_confidence_available": hasattr(self.memory, 'predict_task_outcome_v2'),
                "learning_active": len(self.memory.episodic.get("outcomes", [])) > 0
            }
            
            # Get agent profile insights
            if agent_id and agent_id in self.memory.semantic.get("agent_profiles", {}):
                profile = self.memory.semantic["agent_profiles"][agent_id]
                insights["agent_profiles"][agent_id] = {
                    "total_tasks": profile.total_tasks,
                    "success_rate": profile.successful_tasks / max(1, profile.total_tasks),
                    "top_skills": sorted(
                        profile.skill_success_rates.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3],
                    "common_blockers": list(profile.common_blockers.keys())[:3],
                    "estimation_accuracy": profile.average_estimation_accuracy
                }
            else:
                # Get overview of all agents
                for aid, profile in self.memory.semantic.get("agent_profiles", {}).items():
                    insights["agent_profiles"][aid] = {
                        "total_tasks": profile.total_tasks,
                        "success_rate": profile.successful_tasks / max(1, profile.total_tasks),
                        "expertise_areas": len(profile.skill_success_rates)
                    }
            
            # Calculate learning trends
            outcomes = self.memory.episodic.get("outcomes", [])
            if outcomes:
                recent_outcomes = outcomes[-10:]  # Last 10 outcomes
                insights["learning_trends"] = {
                    "recent_success_rate": sum(1 for o in recent_outcomes if o.success) / len(recent_outcomes),
                    "estimation_accuracy_trend": sum(o.estimation_accuracy for o in recent_outcomes) / len(recent_outcomes),
                    "learning_velocity": len(recent_outcomes),
                    "skill_development_active": any(
                        len(profile.skill_success_rates) > 0 
                        for profile in self.memory.semantic.get("agent_profiles", {}).values()
                    )
                }
                
        except Exception as e:
            logger.error(f"Error getting memory predictions: {e}")
            insights["error"] = str(e)
            
        return insights
    
    async def get_dependency_analysis(self, tasks: Optional[List] = None) -> Dict[str, Any]:
        """
        Get comprehensive dependency analysis from the Context system.
        
        Args:
            tasks: Optional list of tasks to analyze
            
        Returns:
            Dependency insights including relationships, ordering, and bottlenecks
        """
        if not self.context:
            return {"error": "Context system not available"}
            
        insights = {
            "timestamp": datetime.now().isoformat(),
            "dependency_health": {},
            "task_relationships": {},
            "optimization_opportunities": {},
            "system_efficiency": {}
        }
        
        try:
            if tasks:
                # Analyze provided tasks
                dependency_map = await self.context.analyze_dependencies(tasks, infer_implicit=True)
                ordered_tasks = await self.context.suggest_task_order(tasks)
                
                insights["task_relationships"] = {
                    "total_tasks": len(tasks),
                    "explicit_dependencies": sum(len(t.dependencies or []) for t in tasks),
                    "inferred_dependencies": sum(len(deps) for deps in dependency_map.values()),
                    "dependency_ratio": sum(len(deps) for deps in dependency_map.values()) / max(1, len(tasks)),
                    "optimization_applied": len(ordered_tasks) == len(tasks)
                }
                
                # Detect potential bottlenecks
                bottlenecks = []
                for task_id, dependents in dependency_map.items():
                    if len(dependents) > 2:  # Task blocks multiple others
                        task_name = next((t.name for t in tasks if t.id == task_id), task_id)
                        bottlenecks.append({
                            "task_id": task_id,
                            "task_name": task_name,
                            "blocks_count": len(dependents)
                        })
                
                insights["optimization_opportunities"] = {
                    "potential_bottlenecks": bottlenecks,
                    "parallelizable_tasks": len(tasks) - len(dependency_map),
                    "critical_path_length": len(ordered_tasks),
                    "dependency_complexity": "high" if len(dependency_map) > len(tasks) * 0.5 else "low"
                }
            
            # System-wide dependency health
            insights["dependency_health"] = {
                "total_tracked_dependencies": len(self.context.dependencies),
                "active_implementations": len(self.context.implementations),
                "decision_context_available": len(self.context.decisions) > 0,
                "hybrid_inference_active": hasattr(self.context, 'hybrid_inferer') and self.context.hybrid_inferer is not None
            }
            
        except Exception as e:
            logger.error(f"Error getting dependency analysis: {e}")
            insights["error"] = str(e)
            
        return insights
    
    async def get_system_correlations(self) -> Dict[str, Any]:
        """
        Get insights into how all enhanced systems work together.
        
        Returns:
            Cross-system correlation insights and integration health
        """
        correlations = {
            "timestamp": datetime.now().isoformat(),
            "integration_health": {},
            "cross_system_insights": {},
            "value_amplification": {},
            "system_synergy": {}
        }
        
        try:
            # Check system availability
            systems_available = {
                "events": self.events is not None,
                "context": self.context is not None,
                "memory": self.memory is not None,
                "visibility": True  # Self
            }
            
            correlations["integration_health"] = {
                "systems_connected": sum(systems_available.values()),
                "total_systems": len(systems_available),
                "integration_completeness": sum(systems_available.values()) / len(systems_available),
                "systems_status": systems_available
            }
            
            # Analyze cross-system data flow
            if self.events and self.context:
                context_events = getattr(self, "_event_stats", {}).get("context_updated", 0)
                decision_events = getattr(self, "_event_stats", {}).get("decision_logged", 0)
                
                correlations["cross_system_insights"]["context_activity"] = {
                    "context_updates": context_events,
                    "decisions_logged": decision_events,
                    "knowledge_flow_active": context_events > 0
                }
            
            if self.events and self.memory:
                prediction_events = getattr(self, "_event_stats", {}).get("prediction_made", 0)
                learning_events = getattr(self, "_event_stats", {}).get("agent_learned", 0)
                
                correlations["cross_system_insights"]["memory_activity"] = {
                    "predictions_made": prediction_events,
                    "learning_events": learning_events,
                    "intelligence_active": prediction_events > 0
                }
            
            # Calculate value amplification
            base_events = getattr(self, "_event_stats", {}).get("task_assigned", 0)
            enhanced_events = sum([
                getattr(self, "_event_stats", {}).get("context_updated", 0),
                getattr(self, "_event_stats", {}).get("prediction_made", 0),
                getattr(self, "_event_stats", {}).get("decision_logged", 0)
            ])
            
            if base_events > 0:
                correlations["value_amplification"] = {
                    "base_task_assignments": base_events,
                    "enhanced_system_events": enhanced_events,
                    "intelligence_multiplier": enhanced_events / base_events,
                    "system_value_add": enhanced_events > base_events * 0.5  # 50% enhancement threshold
                }
            
            # System synergy indicators
            correlations["system_synergy"] = {
                "context_memory_synergy": self.context is not None and self.memory is not None,
                "event_driven_coordination": self.events is not None,
                "real_time_intelligence": all(systems_available.values()),
                "predictive_context_sharing": (
                    self.context is not None and 
                    self.memory is not None and 
                    hasattr(self.context, 'hybrid_inferer')
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting system correlations: {e}")
            correlations["error"] = str(e)
            
        return correlations
    
    def get_enhanced_dashboard_data(self) -> Dict[str, Any]:
        """
        Get comprehensive dashboard data including all enhanced system insights.
        
        Returns:
            Complete dashboard data with integrated insights
        """
        return {
            "basic_stats": self.get_event_statistics(),
            "active_flows": len(self.active_flows),
            "flow_details": self.active_flows,
            "enhanced_integrations": {
                "context_available": self.context is not None,
                "memory_available": self.memory is not None,
                "systems_integrated": self.context is not None and self.memory is not None
            },
            "last_updated": datetime.now().isoformat()
        }