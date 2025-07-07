"""
Pipeline Conversation Bridge - Integrates conversation logger with pipeline visualization

This module bridges the gap between the conversation logger and pipeline visualization,
enriching pipeline events with conversation context and AI reasoning data.
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..logging.conversation_logger import ConversationLogger, ConversationType
from .shared_pipeline_events import SharedPipelineVisualizer, PipelineStage


class PipelineConversationBridge:
    """
    Bridges conversation logger data with pipeline visualization events.
    
    This class integrates conversation logs with pipeline events to provide
    rich insights into the decision-making process, AI reasoning, and
    task generation rationale.
    """
    
    def __init__(self, conversation_logger: Optional[ConversationLogger] = None,
                 pipeline_visualizer: Optional[SharedPipelineVisualizer] = None):
        """
        Initialize the bridge with logger and visualizer instances.
        
        Parameters
        ----------
        conversation_logger : Optional[ConversationLogger]
            Conversation logger instance. If None, creates a new instance.
        pipeline_visualizer : Optional[SharedPipelineVisualizer]
            Pipeline visualizer instance. If None, creates a new instance.
        """
        self.conversation_logger = conversation_logger or ConversationLogger()
        self.pipeline_visualizer = pipeline_visualizer or SharedPipelineVisualizer()
        
    def log_pipeline_decision(
        self,
        flow_id: str,
        stage: PipelineStage,
        decision: str,
        reasoning: str,
        confidence: float = 0.0,
        alternatives_considered: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Log a decision point in both conversation logger and pipeline events.
        
        Parameters
        ----------
        flow_id : str
            Pipeline flow identifier
        stage : PipelineStage
            Current pipeline stage
        decision : str
            The decision made
        reasoning : str
            Reasoning behind the decision
        confidence : float
            Confidence score (0.0-1.0)
        alternatives_considered : Optional[List[Dict[str, Any]]]
            Alternative options that were evaluated
        """
        # Log to conversation logger for detailed tracking
        self.conversation_logger.log_pm_decision(
            decision=decision,
            rationale=reasoning,
            confidence_score=confidence,
            alternatives_considered=alternatives_considered,
            decision_factors={
                "pipeline_stage": stage.value,
                "flow_id": flow_id
            }
        )
        
        # Log to pipeline events for visualization
        self.pipeline_visualizer.track_decision_point(
            flow_id=flow_id,
            stage=stage,
            decision=decision,
            rationale=reasoning,
            confidence=confidence,
            alternatives=alternatives_considered or []
        )
    
    def log_ai_analysis_with_context(
        self,
        flow_id: str,
        prd_text: str,
        analysis_result: Dict[str, Any],
        duration_ms: int,
        ai_provider: str = "unknown",
        model: str = "unknown",
        tokens_used: int = 0
    ):
        """
        Log AI analysis with full context and insights.
        
        Parameters
        ----------
        flow_id : str
            Pipeline flow identifier
        prd_text : str
            Original PRD text analyzed
        analysis_result : Dict[str, Any]
            AI analysis results
        duration_ms : int
            Time taken for analysis
        ai_provider : str
            AI provider used (e.g., "openai", "anthropic")
        model : str
            Model used for analysis
        tokens_used : int
            Number of tokens consumed
        """
        # Extract insights from analysis
        extracted_requirements = []
        ambiguities = []
        assumptions = []
        
        # Parse functional requirements
        for req in analysis_result.get("functionalRequirements", []):
            extracted_requirements.append({
                "requirement": req.get("description", ""),
                "confidence": req.get("confidence", 0.8),
                "source_text": req.get("source", ""),
                "category": "functional"
            })
        
        # Parse non-functional requirements
        for req in analysis_result.get("nonFunctionalRequirements", []):
            extracted_requirements.append({
                "requirement": req.get("description", ""),
                "confidence": req.get("confidence", 0.7),
                "source_text": req.get("source", ""),
                "category": "non-functional"
            })
        
        # Identify ambiguities
        if "ambiguities" in analysis_result:
            ambiguities = analysis_result["ambiguities"]
        else:
            # Infer ambiguities from low confidence items
            low_confidence_items = [r for r in extracted_requirements if r["confidence"] < 0.7]
            for item in low_confidence_items:
                ambiguities.append({
                    "text": item["requirement"],
                    "interpretation": "Unclear requirement specification",
                    "alternatives": ["Needs clarification from stakeholder"],
                    "reasoning": f"Low confidence score: {item['confidence']}"
                })
        
        # Log thinking process
        self.conversation_logger.log_pm_thinking(
            thought=f"Analyzing PRD with {len(prd_text)} characters",
            context={
                "prd_preview": prd_text[:200] + "..." if len(prd_text) > 200 else prd_text,
                "ai_provider": ai_provider,
                "model": model,
                "analysis_approach": "requirement_extraction"
            }
        )
        
        # Enhanced analysis result
        enhanced_result = {
            **analysis_result,
            "extractedRequirements": extracted_requirements,
            "ambiguities": ambiguities,
            "assumptions": assumptions,
            "similarProjects": [],  # Could be populated from historical data
            "model": model,
            "tokensUsed": tokens_used,
            "confidence": analysis_result.get("confidence", 0.8)
        }
        
        # Track in pipeline with enhanced data
        self.pipeline_visualizer.track_ai_analysis(
            flow_id=flow_id,
            prd_text=prd_text,
            analysis_result=enhanced_result,
            duration_ms=duration_ms
        )
        
        # Track performance metrics
        self.pipeline_visualizer.track_performance_metrics(
            flow_id=flow_id,
            stage=PipelineStage.AI_ANALYSIS,
            metrics={
                "tokens": tokens_used,
                "response_time": duration_ms,
                "retries": 0,
                "cost": self._estimate_cost(tokens_used, ai_provider),
                "provider": ai_provider
            }
        )
    
    def log_task_generation_with_reasoning(
        self,
        flow_id: str,
        requirements: List[Dict[str, Any]],
        generated_tasks: List[Dict[str, Any]],
        duration_ms: int,
        generation_strategy: str = "requirement_based"
    ):
        """
        Log task generation with detailed reasoning and dependency analysis.
        
        Parameters
        ----------
        flow_id : str
            Pipeline flow identifier
        requirements : List[Dict[str, Any]]
            Requirements that led to task generation
        generated_tasks : List[Dict[str, Any]]
            Tasks that were generated
        duration_ms : int
            Time taken for generation
        generation_strategy : str
            Strategy used for task generation
        """
        # Analyze task breakdown reasoning
        task_breakdown_reasoning = (
            f"Generated {len(generated_tasks)} tasks from {len(requirements)} requirements "
            f"using {generation_strategy} strategy"
        )
        
        # Build dependency graph
        dependency_graph = {}
        for i, task in enumerate(generated_tasks):
            task_id = task.get("id", f"task_{i}")
            dependencies = task.get("dependencies", [])
            dependency_graph[task_id] = dependencies
        
        # Estimate effort
        effort_estimates = {}
        for task in generated_tasks:
            task_id = task.get("id", task.get("name", "unknown"))
            effort_estimates[task_id] = task.get("estimatedHours", 8)
        
        # Identify risks
        risk_factors = []
        if len(generated_tasks) > 20:
            risk_factors.append({
                "risk": "high_task_count",
                "description": "Large number of tasks may lead to coordination overhead",
                "mitigation": "Consider grouping related tasks"
            })
        
        # Log thinking about task generation
        self.conversation_logger.log_pm_thinking(
            thought="Analyzing requirements to generate optimal task breakdown",
            context={
                "requirement_count": len(requirements),
                "generation_strategy": generation_strategy,
                "complexity_factors": {
                    "total_tasks": len(generated_tasks),
                    "max_dependency_depth": self._calculate_dependency_depth(dependency_graph),
                    "parallel_work_possible": self._calculate_parallelism(dependency_graph)
                }
            }
        )
        
        # Track task generation with context
        generation_context = {
            "reasoning": task_breakdown_reasoning,
            "dependencies": dependency_graph,
            "effort_estimates": effort_estimates,
            "risk_factors": risk_factors,
            "alternatives_considered": [
                {
                    "approach": "fine_grained_tasks",
                    "task_count": len(generated_tasks) * 2,
                    "reason_rejected": "Too granular, would increase management overhead"
                }
            ],
            "complexity_score": len(generated_tasks) / 10.0  # Simple complexity metric
        }
        
        self.pipeline_visualizer.track_task_generation(
            flow_id=flow_id,
            task_count=len(generated_tasks),
            tasks=generated_tasks,
            duration_ms=duration_ms,
            generation_context=generation_context
        )
        
        # Log decision about task structure
        self.log_pipeline_decision(
            flow_id=flow_id,
            stage=PipelineStage.TASK_GENERATION,
            decision=f"Use {generation_strategy} strategy with {len(generated_tasks)} tasks",
            reasoning=task_breakdown_reasoning,
            confidence=0.85,
            alternatives_considered=[
                {
                    "option": "fine_grained_approach",
                    "score": 0.6,
                    "pros": ["More detailed tracking", "Easier individual tasks"],
                    "cons": ["Management overhead", "Too many dependencies"],
                    "reason_rejected": "Would create too many inter-dependencies"
                }
            ]
        )
    
    def log_quality_assessment(
        self,
        flow_id: str,
        requirements: List[Dict[str, Any]],
        tasks: List[Dict[str, Any]]
    ):
        """
        Log quality metrics for the pipeline execution.
        
        Parameters
        ----------
        flow_id : str
            Pipeline flow identifier
        requirements : List[Dict[str, Any]]
            Original requirements
        tasks : List[Dict[str, Any]]
            Generated tasks
        """
        # Calculate requirement coverage
        requirement_coverage = {}
        covered_requirements = set()
        
        for task in tasks:
            task_requirements = task.get("addresses_requirements", [])
            for req_id in task_requirements:
                covered_requirements.add(req_id)
                requirement_coverage[req_id] = requirement_coverage.get(req_id, 0) + 1
        
        total_requirements = len(requirements)
        covered_count = len(covered_requirements)
        coverage_percentage = (covered_count / total_requirements * 100) if total_requirements > 0 else 0
        
        # Identify missing considerations
        missing_considerations = []
        
        # Check for testing tasks
        has_testing = any("test" in task.get("name", "").lower() for task in tasks)
        if not has_testing:
            missing_considerations.append("No explicit testing tasks found")
        
        # Check for documentation tasks
        has_docs = any("doc" in task.get("name", "").lower() for task in tasks)
        if not has_docs:
            missing_considerations.append("No documentation tasks found")
        
        # Check for security considerations
        has_security = any("security" in task.get("name", "").lower() or 
                          "auth" in task.get("name", "").lower() for task in tasks)
        if not has_security and any("auth" in str(req).lower() or "security" in str(req).lower() 
                                   for req in requirements):
            missing_considerations.append("Security requirements may need explicit tasks")
        
        # Calculate complexity
        avg_dependencies = sum(len(task.get("dependencies", [])) for task in tasks) / len(tasks) if tasks else 0
        complexity_score = min(1.0, (len(tasks) * 0.05 + avg_dependencies * 0.1))
        
        quality_metrics = {
            "task_completeness": coverage_percentage / 100,
            "requirement_coverage": requirement_coverage,
            "complexity_analysis": {
                "task_count": len(tasks),
                "avg_dependencies": avg_dependencies,
                "complexity_score": complexity_score
            },
            "missing_considerations": missing_considerations,
            "overall_quality": 0.8 if coverage_percentage > 80 and len(missing_considerations) < 2 else 0.6
        }
        
        self.pipeline_visualizer.track_quality_metrics(
            flow_id=flow_id,
            metrics=quality_metrics
        )
        
        # Log thinking about quality
        self.conversation_logger.log_pm_thinking(
            thought="Assessing quality of task generation",
            context={
                "coverage_percentage": coverage_percentage,
                "missing_aspects": missing_considerations,
                "quality_score": quality_metrics["overall_quality"]
            }
        )
    
    def _estimate_cost(self, tokens: int, provider: str) -> float:
        """Estimate cost based on token usage and provider."""
        # Rough estimates per 1K tokens
        cost_per_1k = {
            "openai": 0.002,
            "anthropic": 0.003,
            "local": 0.0
        }
        
        rate = cost_per_1k.get(provider.lower(), 0.002)
        return (tokens / 1000) * rate
    
    def _calculate_dependency_depth(self, dependency_graph: Dict[str, List[str]]) -> int:
        """Calculate maximum dependency depth in task graph."""
        if not dependency_graph:
            return 0
        
        def get_depth(task_id: str, visited: set) -> int:
            if task_id in visited:
                return 0
            visited.add(task_id)
            
            deps = dependency_graph.get(task_id, [])
            if not deps:
                return 1
            
            return 1 + max(get_depth(dep, visited) for dep in deps)
        
        max_depth = 0
        for task_id in dependency_graph:
            depth = get_depth(task_id, set())
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_parallelism(self, dependency_graph: Dict[str, List[str]]) -> float:
        """Calculate potential for parallel work (0.0-1.0)."""
        if not dependency_graph:
            return 1.0
        
        # Tasks with no dependencies can be done in parallel
        independent_tasks = sum(1 for deps in dependency_graph.values() if not deps)
        total_tasks = len(dependency_graph)
        
        return independent_tasks / total_tasks if total_tasks > 0 else 0.0