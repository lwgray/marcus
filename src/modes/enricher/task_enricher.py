"""
Task Enricher for Marcus Phase 2

Enriches existing tasks with metadata and structure to organize chaotic boards.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from src.core.models import Task, Priority
from src.detection.board_analyzer import BoardAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentPlan:
    """Plan for enriching a task"""
    missing_description: bool
    missing_labels: bool
    missing_estimates: bool
    missing_dependencies: bool
    missing_acceptance_criteria: bool
    suggested_improvements: List[str]
    confidence_score: float


@dataclass
class BoardContext:
    """Context about the board for enrichment"""
    project_type: str
    detected_phases: List[str]
    detected_components: List[str]
    common_labels: List[str]
    workflow_pattern: str


@dataclass
class EnrichedTask:
    """Task with enrichments applied"""
    original_task: Task
    enriched_description: str
    suggested_labels: List[str]
    estimated_hours: int
    suggested_dependencies: List[str]
    acceptance_criteria: List[str]
    confidence_score: float
    enrichment_reasoning: str


class TaskEnricher:
    """Enriches existing tasks with metadata and structure"""
    
    def __init__(self):
        # Common task patterns and their typical estimates
        self.task_patterns = {
            'setup': {
                'patterns': [r'setup', r'init', r'configure', r'install'],
                'base_hours': 3,
                'labels': ['setup', 'configuration'],
                'typical_dependencies': []
            },
            'design': {
                'patterns': [r'design', r'architect', r'plan', r'wireframe', r'mockup'],
                'base_hours': 6,
                'labels': ['design', 'planning'],
                'typical_dependencies': ['setup']
            },
            'backend': {
                'patterns': [r'api', r'server', r'backend', r'endpoint', r'service', r'model'],
                'base_hours': 8,
                'labels': ['backend', 'api'],
                'typical_dependencies': ['design']
            },
            'frontend': {
                'patterns': [r'ui', r'frontend', r'component', r'page', r'interface'],
                'base_hours': 6,
                'labels': ['frontend', 'ui'],
                'typical_dependencies': ['backend']
            },
            'testing': {
                'patterns': [r'test', r'qa', r'quality', r'verify'],
                'base_hours': 4,
                'labels': ['testing', 'qa'],
                'typical_dependencies': ['frontend', 'backend']
            },
            'deployment': {
                'patterns': [r'deploy', r'release', r'launch', r'production'],
                'base_hours': 4,
                'labels': ['deployment', 'release'],
                'typical_dependencies': ['testing']
            },
            'documentation': {
                'patterns': [r'document', r'docs', r'readme', r'guide'],
                'base_hours': 2,
                'labels': ['documentation'],
                'typical_dependencies': []
            },
            'bugfix': {
                'patterns': [r'fix', r'bug', r'issue', r'error'],
                'base_hours': 3,
                'labels': ['bugfix', 'maintenance'],
                'typical_dependencies': []
            }
        }
        
        # Technology-specific labels
        self.tech_labels = {
            'react': ['frontend', 'react', 'javascript'],
            'vue': ['frontend', 'vue', 'javascript'],
            'angular': ['frontend', 'angular', 'typescript'],
            'node': ['backend', 'nodejs', 'javascript'],
            'python': ['backend', 'python'],
            'django': ['backend', 'python', 'django'],
            'flask': ['backend', 'python', 'flask'],
            'fastapi': ['backend', 'python', 'fastapi'],
            'express': ['backend', 'nodejs', 'express'],
            'postgresql': ['database', 'postgresql'],
            'mysql': ['database', 'mysql'],
            'mongodb': ['database', 'mongodb'],
            'redis': ['database', 'redis', 'cache'],
            'docker': ['infrastructure', 'docker'],
            'kubernetes': ['infrastructure', 'kubernetes'],
            'aws': ['infrastructure', 'aws', 'cloud'],
            'azure': ['infrastructure', 'azure', 'cloud'],
            'gcp': ['infrastructure', 'gcp', 'cloud']
        }
        
        # Common acceptance criteria patterns
        self.acceptance_criteria_templates = {
            'setup': [
                "Environment is properly configured",
                "All dependencies are installed",
                "Configuration files are in place"
            ],
            'design': [
                "Design meets requirements",
                "Stakeholders approve the design",
                "Design is technically feasible"
            ],
            'backend': [
                "API endpoints are functional",
                "Data validation is implemented",
                "Error handling is in place",
                "Tests pass"
            ],
            'frontend': [
                "UI matches design specifications",
                "Component is responsive",
                "User interactions work correctly",
                "Accessibility standards are met"
            ],
            'testing': [
                "All test cases pass",
                "Code coverage meets standards",
                "No critical bugs found"
            ],
            'deployment': [
                "Application deploys successfully",
                "Production environment is stable",
                "Rollback plan is available"
            ]
        }
    
    async def analyze_task(self, task: Task, board_context: BoardContext) -> EnrichmentPlan:
        """
        Analyze what's missing from a task
        
        Args:
            task: Task to analyze
            board_context: Context about the board
            
        Returns:
            Plan for enriching the task
        """
        missing_description = not task.description or len(task.description) < 20
        missing_labels = len(task.labels) < 2
        missing_estimates = not task.estimated_hours or task.estimated_hours == 0
        missing_dependencies = len(task.dependencies) == 0
        missing_acceptance_criteria = 'acceptance criteria' not in (task.description or '').lower()
        
        # Generate suggestions
        suggestions = []
        
        if missing_description:
            suggestions.append("Add detailed description explaining what needs to be done")
        
        if missing_labels:
            suggestions.append("Add labels to categorize the task (phase, component, technology)")
        
        if missing_estimates:
            suggestions.append("Add time estimate based on task complexity")
        
        if missing_dependencies:
            suggestions.append("Identify dependencies on other tasks")
        
        if missing_acceptance_criteria:
            suggestions.append("Define clear acceptance criteria for completion")
        
        # Calculate confidence score
        missing_count = sum([
            missing_description, missing_labels, missing_estimates,
            missing_dependencies, missing_acceptance_criteria
        ])
        confidence_score = max(0.2, 1.0 - (missing_count * 0.15))
        
        return EnrichmentPlan(
            missing_description=missing_description,
            missing_labels=missing_labels,
            missing_estimates=missing_estimates,
            missing_dependencies=missing_dependencies,
            missing_acceptance_criteria=missing_acceptance_criteria,
            suggested_improvements=suggestions,
            confidence_score=confidence_score
        )
    
    async def generate_enrichments(
        self, 
        task: Task, 
        board_context: BoardContext
    ) -> Dict[str, Any]:
        """
        Generate missing information for a task
        
        Args:
            task: Task to enrich
            board_context: Context about the board
            
        Returns:
            Dictionary with enrichment suggestions
        """
        enrichments = {}
        
        # Classify task type
        task_type = self._classify_task_type(task)
        
        # Generate description if missing
        if not task.description or len(task.description) < 20:
            enrichments['description'] = self._generate_description(task, task_type, board_context)
        
        # Generate labels
        enrichments['labels'] = self._generate_labels(task, task_type, board_context)
        
        # Estimate hours
        enrichments['estimated_hours'] = self._estimate_hours(task, task_type)
        
        # Suggest dependencies
        enrichments['dependencies'] = await self._suggest_dependencies(task, task_type, board_context)
        
        # Generate acceptance criteria
        enrichments['acceptance_criteria'] = self._generate_acceptance_criteria(task, task_type)
        
        # Calculate confidence
        enrichments['confidence'] = self._calculate_enrichment_confidence(task, task_type)
        
        # Generate reasoning
        enrichments['reasoning'] = self._generate_enrichment_reasoning(task, task_type, enrichments)
        
        return enrichments
    
    async def enrich_task_batch(
        self, 
        tasks: List[Task], 
        board_context: BoardContext
    ) -> List[EnrichedTask]:
        """
        Enrich multiple tasks efficiently
        
        Args:
            tasks: List of tasks to enrich
            board_context: Context about the board
            
        Returns:
            List of enriched tasks
        """
        enriched_tasks = []
        
        # First pass: classify all tasks to understand relationships
        task_classifications = {}
        for task in tasks:
            task_classifications[task.id] = self._classify_task_type(task)
        
        # Second pass: enrich each task
        for task in tasks:
            enrichments = await self.generate_enrichments(task, board_context)
            
            enriched_task = EnrichedTask(
                original_task=task,
                enriched_description=enrichments.get('description', task.description),
                suggested_labels=enrichments.get('labels', task.labels),
                estimated_hours=enrichments.get('estimated_hours', task.estimated_hours),
                suggested_dependencies=enrichments.get('dependencies', []),
                acceptance_criteria=enrichments.get('acceptance_criteria', []),
                confidence_score=enrichments.get('confidence', 0.5),
                enrichment_reasoning=enrichments.get('reasoning', '')
            )
            
            enriched_tasks.append(enriched_task)
        
        return enriched_tasks
    
    def _classify_task_type(self, task: Task) -> str:
        """Classify task type based on name and description"""
        task_text = f"{task.name} {task.description or ''}".lower()
        
        # Check each pattern
        for task_type, config in self.task_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, task_text):
                    return task_type
        
        return 'general'
    
    def _generate_description(self, task: Task, task_type: str, board_context: BoardContext) -> str:
        """Generate detailed description for a task"""
        base_description = task.description or ""
        
        # Enhance based on task type
        if task_type == 'setup':
            enhanced = f"{base_description}\n\nThis setup task involves:\n"
            enhanced += "- Configuring the development environment\n"
            enhanced += "- Installing necessary dependencies\n"
            enhanced += "- Setting up project structure\n"
            
        elif task_type == 'design':
            enhanced = f"{base_description}\n\nThis design task includes:\n"
            enhanced += "- Creating architectural diagrams\n"
            enhanced += "- Defining component interfaces\n"
            enhanced += "- Documenting design decisions\n"
            
        elif task_type == 'backend':
            enhanced = f"{base_description}\n\nBackend implementation should include:\n"
            enhanced += "- API endpoint implementation\n"
            enhanced += "- Data validation and error handling\n"
            enhanced += "- Database integration\n"
            enhanced += "- Unit tests\n"
            
        elif task_type == 'frontend':
            enhanced = f"{base_description}\n\nFrontend implementation should include:\n"
            enhanced += "- User interface components\n"
            enhanced += "- State management\n"
            enhanced += "- API integration\n"
            enhanced += "- Responsive design\n"
            
        elif task_type == 'testing':
            enhanced = f"{base_description}\n\nTesting should cover:\n"
            enhanced += "- Unit tests for core functionality\n"
            enhanced += "- Integration tests\n"
            enhanced += "- User acceptance testing\n"
            enhanced += "- Performance testing if applicable\n"
            
        elif task_type == 'deployment':
            enhanced = f"{base_description}\n\nDeployment process includes:\n"
            enhanced += "- Production environment setup\n"
            enhanced += "- CI/CD pipeline configuration\n"
            enhanced += "- Monitoring and logging setup\n"
            enhanced += "- Rollback procedures\n"
            
        else:
            enhanced = f"{base_description}\n\nThis task requires careful implementation with proper testing and documentation."
        
        return enhanced.strip()
    
    def _generate_labels(self, task: Task, task_type: str, board_context: BoardContext) -> List[str]:
        """Generate appropriate labels for a task"""
        labels = set(task.labels)  # Start with existing labels
        
        # Add task type label
        if task_type != 'general':
            labels.add(f"type:{task_type}")
        
        # Add phase label
        phase_labels = {
            'setup': 'phase:setup',
            'design': 'phase:design',
            'backend': 'phase:development',
            'frontend': 'phase:development',
            'testing': 'phase:testing',
            'deployment': 'phase:deployment'
        }
        
        if task_type in phase_labels:
            labels.add(phase_labels[task_type])
        
        # Add component labels based on detected components
        task_text = f"{task.name} {task.description or ''}".lower()
        for component in board_context.detected_components:
            if component in task_text:
                labels.add(f"component:{component}")
        
        # Add technology labels
        for tech, tech_labels in self.tech_labels.items():
            if tech in task_text:
                labels.update(tech_labels)
        
        # Add priority label
        if task.priority:
            labels.add(f"priority:{task.priority.value}")
        
        return sorted(list(labels))
    
    def _estimate_hours(self, task: Task, task_type: str) -> int:
        """Estimate hours for a task"""
        if task.estimated_hours and task.estimated_hours > 0:
            return task.estimated_hours
        
        # Get base estimate from pattern
        base_hours = self.task_patterns.get(task_type, {}).get('base_hours', 4)
        
        # Adjust based on task complexity indicators
        task_text = f"{task.name} {task.description or ''}".lower()
        
        complexity_multiplier = 1.0
        
        # Increase for complex keywords
        complex_keywords = ['complex', 'advanced', 'integration', 'multiple', 'comprehensive']
        for keyword in complex_keywords:
            if keyword in task_text:
                complexity_multiplier += 0.3
        
        # Decrease for simple keywords
        simple_keywords = ['simple', 'basic', 'quick', 'small']
        for keyword in simple_keywords:
            if keyword in task_text:
                complexity_multiplier -= 0.2
        
        # Ensure reasonable bounds
        complexity_multiplier = max(0.5, min(complexity_multiplier, 2.5))
        
        estimated_hours = int(base_hours * complexity_multiplier)
        return max(1, estimated_hours)
    
    async def _suggest_dependencies(
        self, 
        task: Task, 
        task_type: str, 
        board_context: BoardContext
    ) -> List[str]:
        """Suggest dependencies for a task"""
        suggestions = []
        
        # Get typical dependencies for task type
        typical_deps = self.task_patterns.get(task_type, {}).get('typical_dependencies', [])
        
        # Add logical dependencies based on common patterns
        task_text = f"{task.name} {task.description or ''}".lower()
        
        # Frontend depends on backend
        if task_type == 'frontend' or 'frontend' in task_text or 'ui' in task_text:
            if 'api' in task_text or 'backend' in board_context.detected_components:
                suggestions.append("Backend API implementation")
        
        # Testing depends on implementation
        if task_type == 'testing':
            if 'frontend' in board_context.detected_components:
                suggestions.append("Frontend implementation")
            if 'backend' in board_context.detected_components:
                suggestions.append("Backend implementation")
        
        # Deployment depends on testing
        if task_type == 'deployment':
            suggestions.append("Testing completion")
            suggestions.append("Code review approval")
        
        # Integration tasks depend on components
        if 'integrat' in task_text:
            suggestions.append("Component implementations")
        
        return suggestions
    
    def _generate_acceptance_criteria(self, task: Task, task_type: str) -> List[str]:
        """Generate acceptance criteria for a task"""
        # Get template criteria for task type
        template_criteria = self.acceptance_criteria_templates.get(task_type, [])
        
        # Customize based on task name
        customized_criteria = []
        task_name_lower = task.name.lower()
        
        for criterion in template_criteria:
            # Replace generic terms with task-specific terms
            customized = criterion
            if 'component' in task_name_lower:
                customized = customized.replace('Application', 'Component')
            if 'api' in task_name_lower:
                customized = customized.replace('Application', 'API')
            
            customized_criteria.append(customized)
        
        # Add task-specific criteria
        if 'user' in task_name_lower:
            customized_criteria.append("User requirements are satisfied")
        
        if 'performance' in task_name_lower:
            customized_criteria.append("Performance benchmarks are met")
        
        if 'security' in task_name_lower:
            customized_criteria.append("Security requirements are implemented")
        
        # Ensure we have at least basic criteria
        if not customized_criteria:
            customized_criteria = [
                "Implementation meets requirements",
                "Code is properly tested",
                "Documentation is updated"
            ]
        
        return customized_criteria
    
    def _calculate_enrichment_confidence(self, task: Task, task_type: str) -> float:
        """Calculate confidence in enrichment suggestions"""
        confidence = 0.7  # Base confidence
        
        # Increase confidence for well-known task types
        if task_type in self.task_patterns:
            confidence += 0.15
        
        # Increase confidence if task has some existing metadata
        if task.description and len(task.description) > 10:
            confidence += 0.1
        
        if task.labels:
            confidence += 0.1
        
        # Decrease confidence for very generic task names
        if len(task.name.split()) <= 2:
            confidence -= 0.1
        
        return max(0.3, min(confidence, 0.95))
    
    def _generate_enrichment_reasoning(
        self, 
        task: Task, 
        task_type: str, 
        enrichments: Dict[str, Any]
    ) -> str:
        """Generate reasoning for enrichment suggestions"""
        reasoning_parts = []
        
        if task_type != 'general':
            reasoning_parts.append(f"Classified as {task_type} task based on name and description")
        
        if enrichments.get('estimated_hours'):
            reasoning_parts.append(f"Estimated {enrichments['estimated_hours']} hours based on typical {task_type} complexity")
        
        if enrichments.get('labels'):
            new_labels = set(enrichments['labels']) - set(task.labels)
            if new_labels:
                reasoning_parts.append(f"Added labels: {', '.join(sorted(new_labels))}")
        
        if enrichments.get('dependencies'):
            reasoning_parts.append("Suggested dependencies based on common development workflows")
        
        if not reasoning_parts:
            reasoning_parts.append("Applied general task enrichment guidelines")
        
        return "; ".join(reasoning_parts)