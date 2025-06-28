"""
Intelligent Task Enricher for Marcus Phase 3

AI-powered task enrichment that goes beyond pattern matching to provide
semantic understanding and intelligent enhancement of task metadata.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.core.models import Task, Priority
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.providers.base_provider import SemanticAnalysis, EffortEstimate

logger = logging.getLogger(__name__)


@dataclass
class EnhancementResult:
    """Result of AI-powered task enrichment"""
    original_task: Task
    enhanced_description: str
    suggested_labels: List[str]
    estimated_hours: Optional[float]
    suggested_dependencies: List[str]
    acceptance_criteria: List[str]
    risk_factors: List[str]
    confidence: float
    reasoning: str
    
    # Change tracking
    changes_made: Dict[str, Any]
    enhancement_timestamp: datetime
    
    def __post_init__(self):
        if not hasattr(self, 'enhancement_timestamp') or self.enhancement_timestamp is None:
            self.enhancement_timestamp = datetime.now()


@dataclass
class ProjectContext:
    """Extended project context for intelligent enrichment"""
    project_type: str
    tech_stack: List[str]
    team_size: int
    existing_tasks: List[Task]
    project_standards: Dict[str, Any]
    historical_data: List[Dict[str, Any]]
    quality_requirements: Dict[str, Any]


class IntelligentTaskEnricher:
    """
    AI-enhanced task enricher that provides semantic understanding
    
    Goes beyond the pattern-based enrichment from Phase 2 to use
    AI for semantic understanding and intelligent enhancement.
    """
    
    def __init__(self):
        self.llm_client = LLMAbstraction()
        
        # Enhancement settings
        self.enhancement_confidence_threshold = 0.7
        self.max_description_length = 500
        self.max_acceptance_criteria = 5
        
        # Standard label categories
        self.standard_labels = {
            'component': ['frontend', 'backend', 'database', 'api', 'ui', 'infrastructure'],
            'type': ['feature', 'bugfix', 'enhancement', 'refactor', 'test', 'documentation'],
            'priority': ['urgent', 'high', 'medium', 'low'],
            'complexity': ['simple', 'moderate', 'complex'],
            'phase': ['design', 'implementation', 'testing', 'deployment', 'maintenance']
        }
        
        logger.info("Intelligent task enricher initialized")
    
    async def enrich_task_with_ai(
        self, 
        task: Task, 
        project_context: ProjectContext
    ) -> EnhancementResult:
        """
        Enrich a task using AI-powered semantic analysis
        
        Args:
            task: Task to enrich
            project_context: Project context for intelligent enhancement
            
        Returns:
            Enhanced task with AI-generated improvements
        """
        logger.debug(f"Enriching task with AI: {task.name}")
        
        # Get AI semantic analysis
        semantic_analysis = await self._get_semantic_analysis(task, project_context)
        
        # Generate enhanced description
        enhanced_description = await self._generate_enhanced_description(
            task, project_context, semantic_analysis
        )
        
        # Generate intelligent labels
        suggested_labels = await self._generate_intelligent_labels(
            task, project_context, semantic_analysis
        )
        
        # AI-powered effort estimation
        effort_estimate = await self._estimate_effort_with_ai(
            task, project_context, semantic_analysis
        )
        
        # Generate acceptance criteria
        acceptance_criteria = await self._generate_acceptance_criteria(
            task, project_context, semantic_analysis
        )
        
        # Suggest dependencies
        suggested_dependencies = await self._suggest_dependencies(
            task, project_context, semantic_analysis
        )
        
        # Track changes made
        changes_made = self._track_changes(
            task, enhanced_description, suggested_labels, 
            effort_estimate.estimated_hours if effort_estimate else None,
            acceptance_criteria
        )
        
        return EnhancementResult(
            original_task=task,
            enhanced_description=enhanced_description,
            suggested_labels=suggested_labels,
            estimated_hours=effort_estimate.estimated_hours if effort_estimate else None,
            suggested_dependencies=suggested_dependencies,
            acceptance_criteria=acceptance_criteria,
            risk_factors=semantic_analysis.risk_factors,
            confidence=semantic_analysis.confidence,
            reasoning=semantic_analysis.reasoning,
            changes_made=changes_made,
            enhancement_timestamp=datetime.now()
        )
    
    async def enrich_task_batch(
        self, 
        tasks: List[Task], 
        project_context: ProjectContext
    ) -> List[EnhancementResult]:
        """
        Enrich multiple tasks with intelligent batching
        
        Args:
            tasks: List of tasks to enrich
            project_context: Project context
            
        Returns:
            List of enrichment results
        """
        logger.info(f"Enriching batch of {len(tasks)} tasks")
        
        results = []
        
        # Enrich tasks with context awareness
        for i, task in enumerate(tasks):
            # Add previously enriched tasks to context for better coherence
            enriched_context = project_context
            if results:
                enriched_context.existing_tasks.extend([r.original_task for r in results])
            
            try:
                result = await self.enrich_task_with_ai(task, enriched_context)
                results.append(result)
                
                logger.debug(f"Enriched task {i+1}/{len(tasks)}: {task.name}")
                
            except Exception as e:
                logger.warning(f"Failed to enrich task {task.name}: {e}")
                # Create minimal result
                results.append(self._create_fallback_result(task))
        
        logger.info(f"Successfully enriched {len(results)} tasks")
        return results
    
    async def _get_semantic_analysis(
        self, 
        task: Task, 
        project_context: ProjectContext
    ) -> SemanticAnalysis:
        """Get AI semantic analysis of the task"""
        context_dict = {
            'project_type': project_context.project_type,
            'tech_stack': project_context.tech_stack,
            'team_size': project_context.team_size,
            'existing_tasks': [
                {'name': t.name, 'description': t.description} 
                for t in project_context.existing_tasks
            ]
        }
        
        return await self.llm_client.analyze_task_semantics(task, context_dict)
    
    async def _generate_enhanced_description(
        self, 
        task: Task, 
        project_context: ProjectContext,
        semantic_analysis: SemanticAnalysis
    ) -> str:
        """Generate AI-enhanced task description"""
        context_dict = {
            'project_type': project_context.project_type,
            'tech_stack': project_context.tech_stack,
            'quality_standards': project_context.quality_requirements,
            'semantic_intent': semantic_analysis.task_intent
        }
        
        try:
            enhanced = await self.llm_client.generate_enhanced_description(task, context_dict)
            
            # Ensure description isn't too long
            if len(enhanced) > self.max_description_length:
                enhanced = enhanced[:self.max_description_length] + "..."
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"Failed to generate enhanced description: {e}")
            return task.description or task.name
    
    async def _generate_intelligent_labels(
        self, 
        task: Task, 
        project_context: ProjectContext,
        semantic_analysis: SemanticAnalysis
    ) -> List[str]:
        """Generate intelligent labels using AI understanding"""
        labels = set(task.labels)  # Start with existing labels
        
        # Add labels based on semantic analysis
        task_intent = semantic_analysis.task_intent.lower()
        
        # Component labels
        for component in self.standard_labels['component']:
            if component in task_intent or component in f"{task.name} {task.description or ''}".lower():
                labels.add(component)
        
        # Type labels based on intent
        if any(word in task_intent for word in ['fix', 'bug', 'error', 'issue']):
            labels.add('bugfix')
        elif any(word in task_intent for word in ['test', 'verify', 'validate']):
            labels.add('test')
        elif any(word in task_intent for word in ['document', 'doc', 'readme']):
            labels.add('documentation')
        elif any(word in task_intent for word in ['refactor', 'cleanup', 'optimize']):
            labels.add('refactor')
        else:
            labels.add('feature')
        
        # Complexity based on risk factors
        if semantic_analysis.risk_factors:
            if len(semantic_analysis.risk_factors) > 2:
                labels.add('complex')
            elif len(semantic_analysis.risk_factors) > 1:
                labels.add('moderate')
            else:
                labels.add('simple')
        
        # Priority labels (if not already set)
        if task.priority == Priority.URGENT:
            labels.add('urgent')
        elif task.priority == Priority.HIGH:
            labels.add('high')
        elif task.priority == Priority.LOW:
            labels.add('low')
        else:
            labels.add('medium')
        
        return list(labels)
    
    async def _estimate_effort_with_ai(
        self, 
        task: Task, 
        project_context: ProjectContext,
        semantic_analysis: SemanticAnalysis
    ) -> Optional[EffortEstimate]:
        """Use AI to estimate task effort"""
        context_dict = {
            'project_type': project_context.project_type,
            'tech_stack': project_context.tech_stack,
            'historical_data': project_context.historical_data,
            'semantic_analysis': {
                'intent': semantic_analysis.task_intent,
                'risk_factors': semantic_analysis.risk_factors,
                'complexity': len(semantic_analysis.risk_factors)
            }
        }
        
        try:
            return await self.llm_client.estimate_effort_intelligently(task, context_dict)
        except Exception as e:
            logger.warning(f"AI effort estimation failed: {e}")
            return None
    
    async def _generate_acceptance_criteria(
        self, 
        task: Task, 
        project_context: ProjectContext,
        semantic_analysis: SemanticAnalysis
    ) -> List[str]:
        """Generate acceptance criteria using AI understanding"""
        # This would use a specialized AI prompt to generate acceptance criteria
        # For now, generate basic criteria based on semantic analysis
        
        criteria = []
        
        # Basic completion criteria
        criteria.append(f"Task '{task.name}' is functionally complete")
        
        # Add criteria based on task intent
        task_intent = semantic_analysis.task_intent.lower()
        
        if 'implement' in task_intent or 'build' in task_intent:
            criteria.append("Implementation follows project coding standards")
            criteria.append("Code is properly documented")
        
        if 'api' in task_intent or 'endpoint' in task_intent:
            criteria.append("API endpoints return correct responses")
            criteria.append("Error handling is implemented")
        
        if 'ui' in task_intent or 'interface' in task_intent:
            criteria.append("UI is responsive and accessible")
            criteria.append("User interactions work as expected")
        
        if any(word in task_intent for word in ['test', 'verify']):
            criteria.append("All test cases pass")
            criteria.append("Code coverage meets project standards")
        
        # Add quality criteria based on project standards
        if project_context.quality_requirements.get('testing_required', True):
            criteria.append("Unit tests are written and passing")
        
        if project_context.quality_requirements.get('documentation_required', True):
            criteria.append("Documentation is updated")
        
        # Limit to max criteria
        return criteria[:self.max_acceptance_criteria]
    
    async def _suggest_dependencies(
        self, 
        task: Task, 
        project_context: ProjectContext,
        semantic_analysis: SemanticAnalysis
    ) -> List[str]:
        """Suggest task dependencies using AI understanding"""
        suggestions = []
        
        # Use semantic dependencies from analysis
        for dep in semantic_analysis.semantic_dependencies:
            # Find matching tasks in existing tasks
            for existing_task in project_context.existing_tasks:
                if dep.lower() in existing_task.name.lower():
                    suggestions.append(existing_task.id)
                    break
        
        return suggestions
    
    def _track_changes(
        self, 
        original_task: Task, 
        enhanced_description: str,
        suggested_labels: List[str], 
        estimated_hours: Optional[float],
        acceptance_criteria: List[str]
    ) -> Dict[str, Any]:
        """Track what changes were made during enrichment"""
        changes = {}
        
        # Description changes
        if enhanced_description != original_task.description:
            changes['description'] = {
                'original': original_task.description,
                'enhanced': enhanced_description,
                'length_change': len(enhanced_description) - len(original_task.description or '')
            }
        
        # Label changes
        new_labels = set(suggested_labels) - set(original_task.labels)
        if new_labels:
            changes['labels'] = {
                'added': list(new_labels),
                'total_before': len(original_task.labels),
                'total_after': len(suggested_labels)
            }
        
        # Effort estimation
        if estimated_hours and estimated_hours != original_task.estimated_hours:
            changes['effort_estimate'] = {
                'original': original_task.estimated_hours,
                'ai_estimate': estimated_hours
            }
        
        # Acceptance criteria
        if acceptance_criteria:
            changes['acceptance_criteria'] = {
                'count': len(acceptance_criteria),
                'criteria': acceptance_criteria
            }
        
        return changes
    
    def _create_fallback_result(self, task: Task) -> EnhancementResult:
        """Create minimal enrichment result when AI fails"""
        return EnhancementResult(
            original_task=task,
            enhanced_description=task.description or task.name,
            suggested_labels=task.labels,
            estimated_hours=task.estimated_hours,
            suggested_dependencies=[],
            acceptance_criteria=[],
            risk_factors=['ai_enrichment_failed'],
            confidence=0.1,
            reasoning="AI enrichment failed, using original task data",
            changes_made={},
            enhancement_timestamp=datetime.now()
        )
    
    async def get_enrichment_statistics(self, results: List[EnhancementResult]) -> Dict[str, Any]:
        """Get statistics about enrichment results"""
        if not results:
            return {}
        
        total_tasks = len(results)
        enhanced_descriptions = sum(1 for r in results if 'description' in r.changes_made)
        added_labels = sum(1 for r in results if 'labels' in r.changes_made)
        added_estimates = sum(1 for r in results if 'effort_estimate' in r.changes_made)
        added_criteria = sum(1 for r in results if 'acceptance_criteria' in r.changes_made)
        
        avg_confidence = sum(r.confidence for r in results) / total_tasks
        
        return {
            'total_tasks': total_tasks,
            'enhancement_rates': {
                'descriptions_enhanced': enhanced_descriptions / total_tasks,
                'labels_added': added_labels / total_tasks,
                'estimates_added': added_estimates / total_tasks,
                'criteria_added': added_criteria / total_tasks
            },
            'average_confidence': avg_confidence,
            'high_confidence_count': sum(1 for r in results if r.confidence > 0.8),
            'total_labels_added': sum(
                len(r.changes_made.get('labels', {}).get('added', []))
                for r in results
            ),
            'total_criteria_added': sum(
                r.changes_made.get('acceptance_criteria', {}).get('count', 0)
                for r in results
            )
        }