"""
Advanced PRD Parser for Marcus Phase 4

Transform natural language requirements into actionable tasks with
deep understanding, intelligent task breakdown, and risk assessment.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import json

from src.core.models import Task, TaskStatus, Priority
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.intelligence.dependency_inferer import DependencyInferer
from src.ai.types import AnalysisContext

logger = logging.getLogger(__name__)


@dataclass
class PRDAnalysis:
    """Deep analysis of a PRD document"""
    functional_requirements: List[Dict[str, Any]]
    non_functional_requirements: List[Dict[str, Any]]
    technical_constraints: List[str]
    business_objectives: List[str]
    user_personas: List[Dict[str, Any]]
    success_metrics: List[str]
    implementation_approach: str
    complexity_assessment: Dict[str, Any]
    risk_factors: List[Dict[str, Any]]
    confidence: float


@dataclass
class TaskGenerationResult:
    """Result of PRD-to-tasks conversion"""
    tasks: List[Task]
    task_hierarchy: Dict[str, List[str]]  # parent_id -> [child_ids]
    dependencies: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]
    estimated_timeline: Dict[str, Any]
    resource_requirements: Dict[str, Any]
    success_criteria: List[str]
    generation_confidence: float


@dataclass
class ProjectConstraints:
    """Constraints for task generation"""
    deadline: Optional[datetime] = None
    budget_limit: Optional[float] = None
    team_size: int = 3
    available_skills: List[str] = None
    technology_constraints: List[str] = None
    quality_requirements: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.available_skills is None:
            self.available_skills = []
        if self.technology_constraints is None:
            self.technology_constraints = []
        if self.quality_requirements is None:
            self.quality_requirements = {}


class AdvancedPRDParser:
    """
    Advanced PRD parser that converts natural language requirements
    into complete task breakdown with intelligent dependencies and risk assessment
    """
    
    def __init__(self):
        self.llm_client = LLMAbstraction()
        self.dependency_inferer = DependencyInferer()
        
        # PRD parsing configuration
        self.max_tasks_per_epic = 8
        self.min_task_complexity_hours = 1
        self.max_task_complexity_hours = 40
        
        # Standard project phases for task organization
        self.standard_phases = [
            'research_and_planning',
            'design_and_architecture', 
            'setup_and_configuration',
            'core_development',
            'integration_and_testing',
            'deployment_and_launch',
            'monitoring_and_optimization'
        ]
        
        # Risk assessment categories
        self.risk_categories = [
            'technical_complexity',
            'integration_challenges', 
            'performance_requirements',
            'security_concerns',
            'scalability_needs',
            'external_dependencies',
            'timeline_pressure',
            'resource_constraints'
        ]
        
        logger.info("Advanced PRD parser initialized")
    
    async def parse_prd_to_tasks(
        self, 
        prd_content: str, 
        constraints: ProjectConstraints
    ) -> TaskGenerationResult:
        """
        Convert PRD into complete task breakdown with dependencies
        
        Args:
            prd_content: Full PRD document content
            constraints: Project constraints and limitations
            
        Returns:
            Complete task generation result with breakdown and analysis
        """
        logger.info("Starting advanced PRD parsing and task generation")
        
        # Step 1: Deep PRD analysis
        prd_analysis = await self._analyze_prd_deeply(prd_content)
        
        # Step 2: Generate task hierarchy
        task_hierarchy = await self._generate_task_hierarchy(prd_analysis, constraints)
        
        # Step 3: Create detailed tasks
        tasks = await self._create_detailed_tasks(task_hierarchy, prd_analysis, constraints)
        
        # Step 4: AI-powered dependency inference
        dependencies = await self._infer_smart_dependencies(tasks, prd_analysis)
        
        # Step 5: Risk assessment and timeline prediction
        risk_assessment = await self._assess_implementation_risks(tasks, prd_analysis, constraints)
        timeline_prediction = await self._predict_timeline(tasks, dependencies, constraints)
        
        # Step 6: Resource requirement analysis
        resource_requirements = await self._analyze_resource_requirements(tasks, prd_analysis, constraints)
        
        # Step 7: Generate success criteria
        success_criteria = await self._generate_success_criteria(prd_analysis, tasks)
        
        return TaskGenerationResult(
            tasks=tasks,
            task_hierarchy=task_hierarchy,
            dependencies=dependencies,
            risk_assessment=risk_assessment,
            estimated_timeline=timeline_prediction,
            resource_requirements=resource_requirements,
            success_criteria=success_criteria,
            generation_confidence=self._calculate_generation_confidence(prd_analysis, tasks)
        )
    
    async def _analyze_prd_deeply(self, prd_content: str) -> PRDAnalysis:
        """Perform deep analysis of PRD using AI"""
        analysis_prompt = f"""
        Analyze this Product Requirements Document in detail:

        {prd_content}

        Provide a comprehensive JSON analysis with:
        1. Functional requirements (features, capabilities)
        2. Non-functional requirements (performance, security, usability)
        3. Technical constraints and limitations
        4. Business objectives and goals
        5. User personas and target audience
        6. Success metrics and KPIs
        7. Recommended implementation approach
        8. Complexity assessment (technical, timeline, resource)
        9. Risk factors and mitigation strategies

        Focus on extracting actionable, specific requirements that can be converted into development tasks.
        """
        
        try:
            # Use AI to analyze PRD
            context = {'analysis_type': 'comprehensive_prd', 'output_format': 'structured_json'}
            
            # This would use the LLM to parse and analyze
            # For now, simulate with structured parsing
            analysis_data = await self._simulate_prd_analysis(prd_content)
            
            return PRDAnalysis(
                functional_requirements=analysis_data.get('functional_requirements', []),
                non_functional_requirements=analysis_data.get('non_functional_requirements', []),
                technical_constraints=analysis_data.get('technical_constraints', []),
                business_objectives=analysis_data.get('business_objectives', []),
                user_personas=analysis_data.get('user_personas', []),
                success_metrics=analysis_data.get('success_metrics', []),
                implementation_approach=analysis_data.get('implementation_approach', 'agile_iterative'),
                complexity_assessment=analysis_data.get('complexity_assessment', {}),
                risk_factors=analysis_data.get('risk_factors', []),
                confidence=analysis_data.get('confidence', 0.8)
            )
            
        except Exception as e:
            logger.error(f"PRD analysis failed: {e}")
            return self._create_fallback_analysis(prd_content)
    
    async def _generate_task_hierarchy(
        self, 
        analysis: PRDAnalysis, 
        constraints: ProjectConstraints
    ) -> Dict[str, List[str]]:
        """Generate hierarchical task structure"""
        hierarchy = {}
        
        # Create epics from functional requirements
        for req in analysis.functional_requirements:
            epic_id = f"epic_{req.get('id', 'unknown')}"
            hierarchy[epic_id] = []
            
            # Break epic into smaller tasks
            epic_tasks = await self._break_down_epic(req, analysis, constraints)
            hierarchy[epic_id] = [task['id'] for task in epic_tasks]
        
        # Add non-functional requirement tasks
        nfr_epic_id = "epic_non_functional"
        nfr_tasks = await self._create_nfr_tasks(analysis.non_functional_requirements, constraints)
        hierarchy[nfr_epic_id] = [task['id'] for task in nfr_tasks]
        
        # Add infrastructure and setup tasks
        infra_epic_id = "epic_infrastructure"
        infra_tasks = await self._create_infrastructure_tasks(analysis, constraints)
        hierarchy[infra_epic_id] = [task['id'] for task in infra_tasks]
        
        return hierarchy
    
    async def _create_detailed_tasks(
        self,
        task_hierarchy: Dict[str, List[str]],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints
    ) -> List[Task]:
        """Create detailed Task objects with rich metadata"""
        tasks = []
        task_counter = 1
        
        for epic_id, task_ids in list(task_hierarchy.items()):
            for task_id in task_ids:
                # Generate task based on ID and analysis
                task = await self._generate_detailed_task(
                    task_id, epic_id, analysis, constraints, task_counter
                )
                tasks.append(task)
                task_counter += 1
        
        return tasks
    
    async def _generate_detailed_task(
        self,
        task_id: str,
        epic_id: str,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
        sequence: int
    ) -> Task:
        """Generate a detailed task with AI-enhanced metadata"""
        
        # Extract task information from analysis
        task_info = self._extract_task_info(task_id, epic_id, analysis)
        
        # Use AI to enhance task details
        enhanced_details = await self._enhance_task_with_ai(task_info, analysis, constraints)
        
        # Create task with all metadata
        task = Task(
            id=task_id,
            name=enhanced_details.get('name', f"Task {sequence}"),
            description=enhanced_details.get('description', ''),
            status=TaskStatus.TODO,
            priority=self._determine_priority(task_info, analysis),
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=enhanced_details.get('due_date'),
            estimated_hours=enhanced_details.get('estimated_hours'),
            dependencies=[],  # Will be filled by dependency inference
            labels=enhanced_details.get('labels', [])
        )
        
        return task
    
    async def _infer_smart_dependencies(
        self, 
        tasks: List[Task], 
        analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Use AI to infer intelligent dependencies"""
        
        # Use the existing dependency inferer with AI enhancement
        dependency_graph = await self.dependency_inferer.infer_dependencies(tasks)
        
        # Convert to result format
        dependencies = []
        for edge in dependency_graph.edges:
            dependencies.append({
                'dependent_task_id': edge.dependent_task_id,
                'dependency_task_id': edge.dependency_task_id,
                'dependency_type': edge.dependency_type,
                'confidence': edge.confidence,
                'reasoning': edge.reasoning
            })
        
        # Add PRD-specific dependencies
        prd_dependencies = await self._add_prd_specific_dependencies(tasks, analysis)
        dependencies.extend(prd_dependencies)
        
        return dependencies
    
    async def _assess_implementation_risks(
        self,
        tasks: List[Task],
        analysis: PRDAnalysis, 
        constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Assess implementation risks with AI analysis"""
        
        risk_assessment = {
            'overall_risk_level': 'medium',
            'risk_factors': [],
            'mitigation_strategies': [],
            'critical_path_risks': [],
            'resource_risks': [],
            'timeline_risks': []
        }
        
        # Analyze complexity risks
        complexity_risks = await self._analyze_complexity_risks(tasks, analysis)
        risk_assessment['risk_factors'].extend(complexity_risks)
        
        # Analyze constraint risks
        constraint_risks = await self._analyze_constraint_risks(tasks, constraints)
        risk_assessment['timeline_risks'] = constraint_risks
        
        # Generate mitigation strategies
        risk_assessment['mitigation_strategies'] = await self._generate_mitigation_strategies(
            risk_assessment['risk_factors'], tasks, analysis
        )
        
        # Calculate overall risk level
        risk_count = len(risk_assessment['risk_factors'])
        if risk_count < 3:
            risk_assessment['overall_risk_level'] = 'low'
        elif risk_count > 6:
            risk_assessment['overall_risk_level'] = 'high'
        
        return risk_assessment
    
    async def _predict_timeline(
        self,
        tasks: List[Task],
        dependencies: List[Dict[str, Any]],
        constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Predict project timeline with AI-enhanced estimation"""
        
        # Calculate critical path
        total_effort = sum(task.estimated_hours or 8 for task in tasks)
        
        # Adjust for team size and parallel work
        team_productivity = min(constraints.team_size, len(tasks) // 2)  # Diminishing returns
        parallel_factor = 0.7 if team_productivity > 1 else 1.0
        
        # Calculate duration
        working_hours_per_day = 6  # Assume 6 productive hours per day
        estimated_days = (total_effort * parallel_factor) / (team_productivity * working_hours_per_day)
        
        # Add buffer for unknowns and coordination overhead
        buffer_factor = 1.3  # 30% buffer
        estimated_days *= buffer_factor
        
        # Timeline prediction
        start_date = datetime.now()
        estimated_completion = start_date + timedelta(days=estimated_days)
        
        timeline = {
            'estimated_duration_days': int(estimated_days),
            'estimated_completion_date': estimated_completion.isoformat(),
            'total_effort_hours': total_effort,
            'critical_path_tasks': await self._identify_critical_path_tasks(tasks, dependencies),
            'milestone_dates': await self._calculate_milestone_dates(start_date, estimated_days),
            'confidence_interval': {
                'optimistic_days': int(estimated_days * 0.8),
                'pessimistic_days': int(estimated_days * 1.4)
            }
        }
        
        return timeline
    
    async def _analyze_resource_requirements(
        self,
        tasks: List[Task],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Analyze resource requirements"""
        
        # Skill requirements analysis
        skill_requirements = await self._analyze_skill_requirements(tasks, analysis)
        
        # Tool and technology requirements
        tech_requirements = await self._analyze_tech_requirements(analysis, constraints)
        
        # External dependency analysis
        external_deps = await self._analyze_external_dependencies(analysis)
        
        return {
            'required_skills': skill_requirements,
            'technology_stack': tech_requirements,
            'external_dependencies': external_deps,
            'estimated_team_size': self._calculate_optimal_team_size(tasks, constraints),
            'specialized_roles_needed': await self._identify_specialized_roles(tasks, analysis)
        }
    
    async def _generate_success_criteria(
        self, 
        analysis: PRDAnalysis, 
        tasks: List[Task]
    ) -> List[str]:
        """Generate project success criteria"""
        criteria = []
        
        # Add criteria from business objectives
        for objective in analysis.business_objectives:
            criteria.append(f"Business objective met: {objective}")
        
        # Add criteria from success metrics
        criteria.extend(analysis.success_metrics)
        
        # Add technical completion criteria
        criteria.append("All development tasks completed successfully")
        criteria.append("All tests passing with required coverage")
        criteria.append("Application deployed and accessible")
        
        # Add quality criteria
        if analysis.non_functional_requirements:
            criteria.append("Non-functional requirements satisfied")
        
        return criteria
    
    def _calculate_generation_confidence(
        self, 
        analysis: PRDAnalysis, 
        tasks: List[Task]
    ) -> float:
        """Calculate confidence in task generation quality"""
        factors = []
        
        # PRD analysis confidence
        factors.append(analysis.confidence)
        
        # Task detail completeness
        detailed_tasks = sum(1 for task in tasks if task.description and len(task.description) > 20)
        task_detail_score = detailed_tasks / len(tasks) if tasks else 0
        factors.append(task_detail_score)
        
        # Requirement coverage
        req_count = len(analysis.functional_requirements) + len(analysis.non_functional_requirements)
        coverage_score = min(len(tasks) / max(req_count * 3, 1), 1.0)  # Expect 3 tasks per requirement
        factors.append(coverage_score)
        
        return sum(factors) / len(factors) if factors else 0.5
    
    # Helper methods for simulation and fallback
    async def _simulate_prd_analysis(self, prd_content: str) -> Dict[str, Any]:
        """Simulate PRD analysis for development/testing"""
        # Extract key information using simple patterns
        
        # Look for features/requirements
        features = re.findall(r'(?i)(?:feature|requirement|must|should).*?([^\n.]+)', prd_content)
        
        # Simulate analysis result
        return {
            'functional_requirements': [
                {'id': f'req_{i}', 'description': feature.strip(), 'priority': 'high'}
                for i, feature in enumerate(features[:5])
            ],
            'non_functional_requirements': [
                {'id': 'nfr_1', 'description': 'Performance: Response time < 200ms', 'category': 'performance'},
                {'id': 'nfr_2', 'description': 'Security: Data encryption at rest and in transit', 'category': 'security'}
            ],
            'technical_constraints': ['React frontend', 'Python backend', 'PostgreSQL database'],
            'business_objectives': ['Increase user engagement', 'Reduce operational costs'],
            'user_personas': [{'name': 'Primary User', 'role': 'End User', 'goals': ['Easy to use', 'Fast']}],
            'success_metrics': ['User adoption > 80%', 'Performance meets SLA'],
            'implementation_approach': 'agile_iterative',
            'complexity_assessment': {'technical': 'medium', 'timeline': 'medium', 'resource': 'medium'},
            'risk_factors': [
                {'category': 'technical', 'description': 'Integration complexity', 'impact': 'medium'},
                {'category': 'timeline', 'description': 'Aggressive deadline', 'impact': 'high'}
            ],
            'confidence': 0.8
        }
    
    def _create_fallback_analysis(self, prd_content: str) -> PRDAnalysis:
        """Create fallback analysis when AI fails"""
        return PRDAnalysis(
            functional_requirements=[{'id': 'req_1', 'description': 'Basic functionality', 'priority': 'high'}],
            non_functional_requirements=[],
            technical_constraints=['Standard web application'],
            business_objectives=['Deliver working solution'],
            user_personas=[],
            success_metrics=['Application works as intended'],
            implementation_approach='standard',
            complexity_assessment={'overall': 'medium'},
            risk_factors=[{'category': 'analysis', 'description': 'AI analysis failed', 'impact': 'low'}],
            confidence=0.3
        )
    
    # Additional helper methods would be implemented here...
    async def _break_down_epic(self, req: Dict[str, Any], analysis: PRDAnalysis, constraints: ProjectConstraints) -> List[Dict[str, Any]]:
        """Break down epic into smaller tasks"""
        # Simplified implementation
        req_id = req.get('id', 'unknown')
        return [
            {'id': f'task_{req_id}_design', 'name': f"Design {req.get('description', 'feature')}", 'type': 'design'},
            {'id': f'task_{req_id}_implement', 'name': f"Implement {req.get('description', 'feature')}", 'type': 'implementation'},
            {'id': f'task_{req_id}_test', 'name': f"Test {req.get('description', 'feature')}", 'type': 'testing'}
        ]
    
    async def _create_nfr_tasks(self, nfrs: List[Dict[str, Any]], constraints: ProjectConstraints) -> List[Dict[str, Any]]:
        """Create non-functional requirement tasks"""
        return [
            {'id': f'nfr_task_{nfr.get("id", i)}', 'name': f"Implement {nfr.get('description', 'NFR')}", 'type': 'nfr'}
            for i, nfr in enumerate(nfrs)
        ]
    
    async def _create_infrastructure_tasks(self, analysis: PRDAnalysis, constraints: ProjectConstraints) -> List[Dict[str, Any]]:
        """Create infrastructure and setup tasks"""
        return [
            {'id': 'infra_setup', 'name': 'Set up development environment', 'type': 'setup'},
            {'id': 'infra_ci_cd', 'name': 'Configure CI/CD pipeline', 'type': 'infrastructure'},
            {'id': 'infra_deploy', 'name': 'Set up deployment infrastructure', 'type': 'deployment'}
        ]
    
    def _extract_task_info(self, task_id: str, epic_id: str, analysis: PRDAnalysis) -> Dict[str, Any]:
        """Extract task information from analysis"""
        return {
            'id': task_id,
            'epic_id': epic_id,
            'type': 'development',  # Default type
            'complexity': 'medium'
        }
    
    async def _enhance_task_with_ai(self, task_info: Dict[str, Any], analysis: PRDAnalysis, constraints: ProjectConstraints) -> Dict[str, Any]:
        """Enhance task with PRD-aware details following board quality standards"""
        task_id = task_info.get('id', 'unknown')
        epic_id = task_info.get('epic_id', 'unknown')
        
        # Extract meaningful context from PRD analysis
        project_context = self._extract_project_context(analysis, task_id, epic_id)
        
        # Generate context-aware task details
        if 'design' in task_id.lower():
            name, description = self._generate_design_task(project_context, task_id)
            task_type = 'design'
            estimated_hours = 8
        elif 'implement' in task_id.lower():
            name, description = self._generate_implementation_task(project_context, task_id)
            task_type = 'implementation'
            estimated_hours = 16
        elif 'test' in task_id.lower():
            name, description = self._generate_testing_task(project_context, task_id)
            task_type = 'testing'
            estimated_hours = 8
        elif 'setup' in task_id.lower() or 'infra' in task_id.lower():
            name, description = self._generate_infrastructure_task(project_context, task_id)
            task_type = 'setup'
            estimated_hours = 12
        else:
            name, description = self._generate_generic_task(project_context, task_id)
            task_type = 'feature'
            estimated_hours = 12
            
        # Generate appropriate labels based on context and requirements
        labels = self._generate_labels(task_type, project_context, constraints)
        
        return {
            'name': name,
            'description': description,
            'estimated_hours': estimated_hours,
            'labels': labels,
            'due_date': None
        }
    
    def _determine_priority(self, task_info: Dict[str, Any], analysis: PRDAnalysis) -> Priority:
        """Determine task priority"""
        task_type = task_info.get('type', 'development')
        
        if task_type in ['setup', 'infrastructure']:
            return Priority.HIGH
        elif task_type in ['design', 'planning']:
            return Priority.HIGH
        elif task_type in ['testing', 'deployment']:
            return Priority.MEDIUM
        else:
            return Priority.MEDIUM
    
    # Additional helper methods would continue to be implemented...
    async def _add_prd_specific_dependencies(self, tasks: List[Task], analysis: PRDAnalysis) -> List[Dict[str, Any]]:
        """Add PRD-specific dependencies"""
        return []  # Simplified for now
    
    async def _analyze_complexity_risks(self, tasks: List[Task], analysis: PRDAnalysis) -> List[Dict[str, Any]]:
        """Analyze complexity-related risks"""
        return [
            {'type': 'technical_complexity', 'description': 'Complex integration requirements', 'impact': 'medium'}
        ]
    
    async def _analyze_constraint_risks(self, tasks: List[Task], constraints: ProjectConstraints) -> List[Dict[str, Any]]:
        """Analyze constraint-related risks"""
        risks = []
        if constraints.deadline:
            total_effort = sum(task.estimated_hours or 8 for task in tasks)
            days_available = (constraints.deadline - datetime.now()).days
            if total_effort > days_available * constraints.team_size * 6:  # 6 hours per day
                risks.append({'type': 'timeline_pressure', 'description': 'Insufficient time for planned work', 'impact': 'high'})
        return risks
    
    async def _generate_mitigation_strategies(self, risks: List[Dict[str, Any]], tasks: List[Task], analysis: PRDAnalysis) -> List[str]:
        """Generate risk mitigation strategies"""
        return [
            "Regular risk assessment reviews",
            "Maintain project buffer time",
            "Implement incremental delivery approach"
        ]
    
    async def _identify_critical_path_tasks(self, tasks: List[Task], dependencies: List[Dict[str, Any]]) -> List[str]:
        """Identify tasks on the critical path"""
        # Simplified - return setup and deployment tasks as critical
        return [task.id for task in tasks if any(label in ['setup', 'deployment'] for label in task.labels)]
    
    async def _calculate_milestone_dates(self, start_date: datetime, duration_days: float) -> Dict[str, str]:
        """Calculate key milestone dates"""
        milestones = {}
        milestones['design_complete'] = (start_date + timedelta(days=duration_days * 0.25)).isoformat()
        milestones['development_complete'] = (start_date + timedelta(days=duration_days * 0.75)).isoformat()
        milestones['testing_complete'] = (start_date + timedelta(days=duration_days * 0.9)).isoformat()
        return milestones
    
    async def _analyze_skill_requirements(self, tasks: List[Task], analysis: PRDAnalysis) -> List[str]:
        """Analyze required skills"""
        skills = set()
        for constraint in analysis.technical_constraints:
            if 'react' in constraint.lower():
                skills.add('React')
            if 'python' in constraint.lower():
                skills.add('Python')
            if 'postgres' in constraint.lower():
                skills.add('PostgreSQL')
        return list(skills)
    
    async def _analyze_tech_requirements(self, analysis: PRDAnalysis, constraints: ProjectConstraints) -> List[str]:
        """Analyze technology requirements"""
        return analysis.technical_constraints
    
    async def _analyze_external_dependencies(self, analysis: PRDAnalysis) -> List[str]:
        """Analyze external dependencies"""
        return ["Third-party API integrations", "External service providers"]
    
    def _calculate_optimal_team_size(self, tasks: List[Task], constraints: ProjectConstraints) -> int:
        """Calculate optimal team size"""
        task_complexity = len(tasks)
        if task_complexity < 10:
            return min(2, constraints.team_size)
        elif task_complexity < 25:
            return min(4, constraints.team_size)
        else:
            return min(6, constraints.team_size)
    
    async def _identify_specialized_roles(self, tasks: List[Task], analysis: PRDAnalysis) -> List[str]:
        """Identify specialized roles needed"""
        roles = ['Full-stack Developer']
        
        # Check for UI/UX needs
        if any('design' in task.name.lower() for task in tasks):
            roles.append('UI/UX Designer')
        
        # Check for DevOps needs
        if any('deploy' in task.name.lower() or 'infrastructure' in task.name.lower() for task in tasks):
            roles.append('DevOps Engineer')
        
        return roles