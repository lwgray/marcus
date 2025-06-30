"""
Board Organizer for Marcus Phase 2 Enricher Mode

Organizes chaotic boards into logical structures with multiple strategies.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import re

from src.core.models import Task, TaskStatus, Priority

logger = logging.getLogger(__name__)


@dataclass
class OrganizationStrategy:
    """Strategy for organizing a board"""
    name: str
    description: str
    confidence: float
    structure: Dict[str, Any]
    reasoning: str


@dataclass
class PhasedStructure:
    """Board organized by development phases"""
    phases: Dict[str, List[Task]]
    phase_order: List[str]
    cross_phase_dependencies: List[Tuple[str, str]]


@dataclass
class ComponentStructure:
    """Board organized by system components"""
    components: Dict[str, List[Task]]
    integration_tasks: List[Task]
    shared_tasks: List[Task]


@dataclass
class LabelingPlan:
    """Plan for consistent labeling"""
    label_hierarchy: Dict[str, List[str]]
    task_label_assignments: Dict[str, List[str]]
    cleanup_suggestions: List[str]


class BoardOrganizer:
    """Organizes boards into logical structures"""
    
    def __init__(self):
        # Development phase definitions
        self.development_phases = {
            'planning': {
                'keywords': ['plan', 'design', 'architect', 'wireframe', 'mockup', 'spec'],
                'order': 1,
                'description': 'Planning and design phase'
            },
            'setup': {
                'keywords': ['setup', 'init', 'configure', 'install', 'scaffold'],
                'order': 2,
                'description': 'Project setup and configuration'
            },
            'development': {
                'keywords': ['implement', 'build', 'create', 'develop', 'code', 'write'],
                'order': 3,
                'description': 'Core development phase'
            },
            'testing': {
                'keywords': ['test', 'qa', 'quality', 'verify', 'validate'],
                'order': 4,
                'description': 'Testing and quality assurance'
            },
            'deployment': {
                'keywords': ['deploy', 'release', 'launch', 'ship', 'production'],
                'order': 5,
                'description': 'Deployment and release'
            },
            'maintenance': {
                'keywords': ['maintain', 'fix', 'bug', 'patch', 'update', 'support'],
                'order': 6,
                'description': 'Maintenance and support'
            }
        }
        
        # Component type definitions
        self.component_types = {
            'frontend': {
                'keywords': ['frontend', 'ui', 'interface', 'client', 'react', 'vue', 'angular'],
                'description': 'User interface and frontend'
            },
            'backend': {
                'keywords': ['backend', 'api', 'server', 'service', 'endpoint'],
                'description': 'Backend services and APIs'
            },
            'database': {
                'keywords': ['database', 'db', 'sql', 'mongo', 'data', 'model'],
                'description': 'Data storage and management'
            },
            'infrastructure': {
                'keywords': ['infra', 'devops', 'ci', 'cd', 'docker', 'k8s', 'deploy'],
                'description': 'Infrastructure and DevOps'
            },
            'mobile': {
                'keywords': ['mobile', 'ios', 'android', 'app', 'native'],
                'description': 'Mobile applications'
            },
            'testing': {
                'keywords': ['test', 'qa', 'spec', 'e2e', 'unit', 'integration'],
                'description': 'Testing and quality assurance'
            },
            'documentation': {
                'keywords': ['doc', 'readme', 'guide', 'manual', 'help'],
                'description': 'Documentation and guides'
            }
        }
        
        # Priority hierarchy
        self.priority_hierarchy = {
            Priority.URGENT: 4,
            Priority.HIGH: 3,
            Priority.MEDIUM: 2,
            Priority.LOW: 1
        }
    
    async def analyze_organization_options(self, tasks: List[Task]) -> List[OrganizationStrategy]:
        """
        Suggest organization strategies for the board
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List of possible organization strategies with confidence scores
        """
        strategies = []
        
        # Analyze phase-based organization
        phase_strategy = await self._analyze_phase_organization(tasks)
        if phase_strategy:
            strategies.append(phase_strategy)
        
        # Analyze component-based organization
        component_strategy = await self._analyze_component_organization(tasks)
        if component_strategy:
            strategies.append(component_strategy)
        
        # Analyze feature-based organization
        feature_strategy = await self._analyze_feature_organization(tasks)
        if feature_strategy:
            strategies.append(feature_strategy)
        
        # Analyze priority-based organization
        priority_strategy = await self._analyze_priority_organization(tasks)
        if priority_strategy:
            strategies.append(priority_strategy)
        
        # Sort by confidence
        strategies.sort(key=lambda s: s.confidence, reverse=True)
        
        return strategies
    
    async def _analyze_phase_organization(self, tasks: List[Task]) -> Optional[OrganizationStrategy]:
        """Analyze viability of phase-based organization"""
        phase_distribution = defaultdict(int)
        phase_tasks = defaultdict(list)
        
        for task in tasks:
            task_text = f"{task.name} {task.description or ''}".lower()
            task_phase = None
            
            # Classify task by phase
            for phase_name, phase_config in list(self.development_phases.items()):
                for keyword in phase_config['keywords']:
                    if keyword in task_text:
                        task_phase = phase_name
                        break
                if task_phase:
                    break
            
            if not task_phase:
                task_phase = 'development'  # Default phase
            
            phase_distribution[task_phase] += 1
            phase_tasks[task_phase].append(task)
        
        # Calculate confidence
        total_tasks = len(tasks)
        if total_tasks == 0:
            return None
        
        # Good phase distribution should have tasks in multiple phases
        unique_phases = len(phase_distribution)
        confidence = min(0.9, unique_phases / 4)  # Max confidence if 4+ phases
        
        # Bonus if we have logical progression
        if 'planning' in phase_distribution and 'development' in phase_distribution:
            confidence += 0.1
        if 'testing' in phase_distribution and 'deployment' in phase_distribution:
            confidence += 0.1
        
        confidence = min(0.95, confidence)
        
        return OrganizationStrategy(
            name="phase_based",
            description="Organize tasks by development phases (planning → development → testing → deployment)",
            confidence=confidence,
            structure={
                "phases": dict(phase_distribution),
                "phase_tasks": {k: [t.id for t in v] for k, v in list(phase_tasks.items())}
            },
            reasoning=f"Found {unique_phases} distinct phases across {total_tasks} tasks"
        )
    
    async def _analyze_component_organization(self, tasks: List[Task]) -> Optional[OrganizationStrategy]:
        """Analyze viability of component-based organization"""
        component_distribution = defaultdict(int)
        component_tasks = defaultdict(list)
        
        for task in tasks:
            task_text = f"{task.name} {task.description or ''} {' '.join(task.labels)}".lower()
            task_components = []
            
            # Classify task by components
            for component_name, component_config in list(self.component_types.items()):
                for keyword in component_config['keywords']:
                    if keyword in task_text:
                        task_components.append(component_name)
            
            # If no specific component, try to infer
            if not task_components:
                if any(word in task_text for word in ['user', 'interface', 'page']):
                    task_components.append('frontend')
                elif any(word in task_text for word in ['data', 'store', 'save']):
                    task_components.append('database')
                else:
                    task_components.append('general')
            
            # Assign to primary component
            primary_component = task_components[0]
            component_distribution[primary_component] += 1
            component_tasks[primary_component].append(task)
        
        # Calculate confidence
        total_tasks = len(tasks)
        if total_tasks == 0:
            return None
        
        unique_components = len(component_distribution)
        confidence = min(0.9, unique_components / 3)  # Max confidence if 3+ components
        
        # Bonus for having frontend/backend split
        if 'frontend' in component_distribution and 'backend' in component_distribution:
            confidence += 0.15
        
        # Bonus for having database tasks
        if 'database' in component_distribution:
            confidence += 0.1
        
        confidence = min(0.95, confidence)
        
        return OrganizationStrategy(
            name="component_based",
            description="Organize tasks by system components (frontend, backend, database, etc.)",
            confidence=confidence,
            structure={
                "components": dict(component_distribution),
                "component_tasks": {k: [t.id for t in v] for k, v in list(component_tasks.items())}
            },
            reasoning=f"Found {unique_components} distinct components across {total_tasks} tasks"
        )
    
    async def _analyze_feature_organization(self, tasks: List[Task]) -> Optional[OrganizationStrategy]:
        """Analyze viability of feature-based organization"""
        # Extract potential features from task names
        feature_keywords = set()
        
        for task in tasks:
            # Extract noun phrases that might be features
            words = re.findall(r'\b[a-zA-Z]+\b', task.name.lower())
            
            # Look for feature-like patterns
            for i, word in enumerate(words):
                # Skip common verbs and articles
                if word in ['implement', 'create', 'build', 'add', 'fix', 'test', 'the', 'a', 'an']:
                    continue
                
                # Look for multi-word features
                if i < len(words) - 1:
                    potential_feature = f"{word} {words[i+1]}"
                    if len(potential_feature) > 6:  # Reasonable feature name length
                        feature_keywords.add(potential_feature)
                
                # Single word features
                if len(word) > 4:
                    feature_keywords.add(word)
        
        # Group tasks by features
        feature_distribution = defaultdict(int)
        feature_tasks = defaultdict(list)
        
        for task in tasks:
            task_text = task.name.lower()
            task_features = []
            
            for feature in feature_keywords:
                if feature in task_text:
                    task_features.append(feature)
            
            if not task_features:
                task_features.append('general')
            
            # Assign to primary feature
            primary_feature = task_features[0]
            feature_distribution[primary_feature] += 1
            feature_tasks[primary_feature].append(task)
        
        # Calculate confidence based on feature clustering
        total_tasks = len(tasks)
        if total_tasks == 0:
            return None
        
        # Good feature organization should have multiple tasks per feature
        avg_tasks_per_feature = total_tasks / len(feature_distribution)
        confidence = min(0.8, avg_tasks_per_feature / 3)  # Max confidence if 3+ tasks per feature
        
        # Reduce confidence if too many single-task features
        single_task_features = sum(1 for count in list(feature_distribution.values()) if count == 1)
        if single_task_features > len(feature_distribution) * 0.7:
            confidence *= 0.5
        
        return OrganizationStrategy(
            name="feature_based",
            description="Organize tasks by features or functional areas",
            confidence=confidence,
            structure={
                "features": dict(feature_distribution),
                "feature_tasks": {k: [t.id for t in v] for k, v in list(feature_tasks.items())}
            },
            reasoning=f"Identified {len(feature_distribution)} potential features with avg {avg_tasks_per_feature:.1f} tasks each"
        )
    
    async def _analyze_priority_organization(self, tasks: List[Task]) -> Optional[OrganizationStrategy]:
        """Analyze viability of priority-based organization"""
        priority_distribution = defaultdict(int)
        priority_tasks = defaultdict(list)
        
        for task in tasks:
            priority = task.priority or Priority.MEDIUM
            priority_distribution[priority.value] += 1
            priority_tasks[priority.value].append(task)
        
        # Calculate confidence
        total_tasks = len(tasks)
        if total_tasks == 0:
            return None
        
        # Good priority organization should have varied priorities
        unique_priorities = len(priority_distribution)
        confidence = min(0.7, unique_priorities / 3)  # Max confidence if 3+ priorities
        
        # Bonus if priorities are well distributed
        max_priority_count = max(priority_distribution.values())
        if max_priority_count < total_tasks * 0.8:  # No single priority dominates
            confidence += 0.2
        
        return OrganizationStrategy(
            name="priority_based",
            description="Organize tasks by priority levels (urgent → high → medium → low)",
            confidence=confidence,
            structure={
                "priorities": dict(priority_distribution),
                "priority_tasks": {k: [t.id for t in v] for k, v in list(priority_tasks.items())}
            },
            reasoning=f"Found {unique_priorities} priority levels across {total_tasks} tasks"
        )
    
    async def organize_by_phase(self, tasks: List[Task]) -> PhasedStructure:
        """
        Organize tasks into development phases
        
        Args:
            tasks: Tasks to organize
            
        Returns:
            Phased structure with tasks organized by development phases
        """
        phases = {}
        phase_order = []
        
        # Initialize phases
        for phase_name, phase_config in list(self.development_phases.items()):
            phases[phase_name] = []
            phase_order.append(phase_name)
        
        # Sort phase order by configured order
        phase_order.sort(key=lambda p: self.development_phases[p]['order'])
        
        # Classify tasks
        for task in tasks:
            task_text = f"{task.name} {task.description or ''}".lower()
            task_phase = None
            
            # Find best matching phase
            max_matches = 0
            for phase_name, phase_config in list(self.development_phases.items()):
                matches = sum(1 for keyword in phase_config['keywords'] if keyword in task_text)
                if matches > max_matches:
                    max_matches = matches
                    task_phase = phase_name
            
            # Default to development if no clear match
            if not task_phase:
                task_phase = 'development'
            
            phases[task_phase].append(task)
        
        # Identify cross-phase dependencies
        cross_phase_deps = []
        for task in tasks:
            task_phase = None
            # Find which phase this task is in
            for phase_name, phase_tasks in list(phases.items()):
                if task in phase_tasks:
                    task_phase = phase_name
                    break
            
            if task_phase and task.dependencies:
                for dep_id in task.dependencies:
                    # Find dependency phase
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if dep_task:
                        dep_phase = None
                        for phase_name, phase_tasks in list(phases.items()):
                            if dep_task in phase_tasks:
                                dep_phase = phase_name
                                break
                        
                        if dep_phase and dep_phase != task_phase:
                            cross_phase_deps.append((dep_phase, task_phase))
        
        return PhasedStructure(
            phases=phases,
            phase_order=phase_order,
            cross_phase_dependencies=cross_phase_deps
        )
    
    async def organize_by_component(self, tasks: List[Task]) -> ComponentStructure:
        """
        Organize tasks by system components
        
        Args:
            tasks: Tasks to organize
            
        Returns:
            Component structure with tasks organized by components
        """
        components = {}
        integration_tasks = []
        shared_tasks = []
        
        # Initialize components
        for component_name in self.component_types.keys():
            components[component_name] = []
        
        # Classify tasks
        for task in tasks:
            task_text = f"{task.name} {task.description or ''} {' '.join(task.labels)}".lower()
            matching_components = []
            
            # Find matching components
            for component_name, component_config in list(self.component_types.items()):
                for keyword in component_config['keywords']:
                    if keyword in task_text:
                        matching_components.append(component_name)
                        break
            
            # Categorize based on matches
            if len(matching_components) == 0:
                # No specific component - likely shared
                shared_tasks.append(task)
            elif len(matching_components) == 1:
                # Single component
                components[matching_components[0]].append(task)
            else:
                # Multiple components - likely integration
                integration_tasks.append(task)
        
        return ComponentStructure(
            components=components,
            integration_tasks=integration_tasks,
            shared_tasks=shared_tasks
        )
    
    async def create_labels_and_groups(self, strategy: OrganizationStrategy) -> LabelingPlan:
        """
        Create consistent labeling plan
        
        Args:
            strategy: Organization strategy to implement
            
        Returns:
            Labeling plan with hierarchy and assignments
        """
        label_hierarchy = {}
        task_label_assignments = {}
        cleanup_suggestions = []
        
        if strategy.name == "phase_based":
            # Create phase hierarchy
            label_hierarchy["phase"] = list(self.development_phases.keys())
            
            # Assign phase labels
            phase_tasks = strategy.structure.get("phase_tasks", {})
            for phase, task_ids in list(phase_tasks.items()):
                for task_id in task_ids:
                    if task_id not in task_label_assignments:
                        task_label_assignments[task_id] = []
                    task_label_assignments[task_id].append(f"phase:{phase}")
            
        elif strategy.name == "component_based":
            # Create component hierarchy
            label_hierarchy["component"] = list(self.component_types.keys())
            
            # Assign component labels
            component_tasks = strategy.structure.get("component_tasks", {})
            for component, task_ids in list(component_tasks.items()):
                for task_id in task_ids:
                    if task_id not in task_label_assignments:
                        task_label_assignments[task_id] = []
                    task_label_assignments[task_id].append(f"component:{component}")
        
        elif strategy.name == "priority_based":
            # Create priority hierarchy
            label_hierarchy["priority"] = ["urgent", "high", "medium", "low"]
            
            # Assign priority labels
            priority_tasks = strategy.structure.get("priority_tasks", {})
            for priority, task_ids in list(priority_tasks.items()):
                for task_id in task_ids:
                    if task_id not in task_label_assignments:
                        task_label_assignments[task_id] = []
                    task_label_assignments[task_id].append(f"priority:{priority}")
        
        # Add cleanup suggestions
        cleanup_suggestions.extend([
            "Remove duplicate labels",
            "Standardize label naming convention",
            "Add missing category labels",
            "Consolidate similar labels"
        ])
        
        return LabelingPlan(
            label_hierarchy=label_hierarchy,
            task_label_assignments=task_label_assignments,
            cleanup_suggestions=cleanup_suggestions
        )