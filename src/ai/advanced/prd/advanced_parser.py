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
        logger.info(f"PRD analysis found {len(prd_analysis.functional_requirements)} functional requirements")
        task_hierarchy = await self._generate_task_hierarchy(prd_analysis, constraints)
        
        # Step 3: Create detailed tasks
        logger.info(f"Creating detailed tasks from hierarchy with {len(task_hierarchy)} epics")
        tasks = await self._create_detailed_tasks(task_hierarchy, prd_analysis, constraints)
        logger.info(f"Created {len(tasks)} detailed tasks")
        
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
            # Create a simple context object that has max_tokens
            class SimpleContext:
                def __init__(self, max_tokens):
                    self.max_tokens = max_tokens
            
            context = SimpleContext(max_tokens=2000)
            
            logger.info("Attempting to use LLM for PRD analysis...")
            
            # Use the actual LLM to analyze the PRD
            analysis_result = await self.llm_client.analyze(
                prompt=analysis_prompt,
                context=context
            )
            
            logger.info(f"LLM response received: {len(analysis_result) if analysis_result else 0} chars")
            
            # Parse the AI response
            import json
            try:
                analysis_data = json.loads(analysis_result)
                logger.info("Successfully parsed AI response as JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse AI response as JSON: {e}")
                logger.warning(f"Response was: {analysis_result[:200]}...")
                logger.warning("Falling back to simulation")
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
            from src.core.error_framework import AIProviderError, ErrorContext
            from src.core.error_monitoring import record_error_for_monitoring
            
            # Create AI provider error with context
            ai_error = AIProviderError(
                provider_name="LLM",
                operation="prd_analysis",
                context=ErrorContext(
                    operation="analyze_prd_deeply",
                    integration_name="advanced_prd_parser",
                    custom_context={
                        "prd_length": len(prd_content),
                        "details": f"LLM analysis failed: {str(e)}. Falling back to simulation."
                    }
                )
            )
            
            # Record for monitoring but continue with fallback
            record_error_for_monitoring(ai_error)
            logger.error(f"PRD analysis failed: {ai_error}")
            logger.info("Attempting simulation fallback...")
            
            try:
                # Try enhanced simulation with better pattern matching
                analysis_data = await self._simulate_prd_analysis_enhanced(prd_content)
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
                    confidence=analysis_data.get('confidence', 0.6)  # Lower confidence for simulation
                )
            except Exception as sim_error:
                from src.core.error_framework import BusinessLogicError
                
                logger.error(f"Simulation also failed: {sim_error}")
                
                # If both AI and simulation fail, raise a proper error
                raise BusinessLogicError(
                    f"Both AI analysis and simulation fallback failed for PRD. "
                    f"Original error: {str(e)}. Simulation error: {str(sim_error)}. "
                    f"The PRD content may be malformed or too complex to parse. "
                    f"PRD preview: '{prd_content[:200]}...'",
                    context=ErrorContext(
                        operation="analyze_prd_deeply",
                        integration_name="advanced_prd_parser",
                        custom_context={
                            "prd_length": len(prd_content),
                            "original_error": str(e),
                            "simulation_error": str(sim_error),
                            "operation_type": "prd_analysis_fallback"
                        }
                    )
                ) from e
    
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
            logger.debug(f"Epic {epic_id} broken down into {len(epic_tasks)} tasks")
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
        
        # Add acceptance criteria as a dynamic attribute
        if enhanced_details.get('acceptance_criteria'):
            task.acceptance_criteria = enhanced_details['acceptance_criteria']
        
        # Add subtasks as a dynamic attribute
        if enhanced_details.get('subtasks'):
            task.subtasks = enhanced_details['subtasks']
        
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
        """Analyze PRD content to extract project-specific requirements"""
        prd_lower = prd_content.lower()
        logger.info(f"Running PRD simulation for content: {prd_content[:100]}...")
        
        # Extract features based on common keywords and patterns
        functional_requirements = []
        
        # Look for specific feature mentions
        if 'todo' in prd_lower or 'task' in prd_lower:
            functional_requirements.extend([
                {'id': 'req_1', 'description': 'Add new tasks/todos functionality', 'priority': 'high'},
                {'id': 'req_2', 'description': 'Delete existing tasks', 'priority': 'high'},
                {'id': 'req_3', 'description': 'Mark tasks as complete/incomplete', 'priority': 'high'},
                {'id': 'req_4', 'description': 'Display list of all tasks', 'priority': 'high'}
            ])
        elif 'friday night funkin' in prd_lower or 'fnf' in prd_lower or 'rhythm game' in prd_lower:
            functional_requirements.extend([
                {'id': 'req_1', 'description': 'Create rhythm-based gameplay with arrow keys', 'priority': 'high'},
                {'id': 'req_2', 'description': 'Implement music synchronization engine', 'priority': 'high'},
                {'id': 'req_3', 'description': 'Build character animation system', 'priority': 'high'},
                {'id': 'req_4', 'description': 'Create note scrolling system', 'priority': 'high'},
                {'id': 'req_5', 'description': 'Implement scoring and health system', 'priority': 'high'}
            ])
        elif 'api' in prd_lower or 'endpoint' in prd_lower:
            functional_requirements.extend([
                {'id': 'req_1', 'description': 'Design RESTful API endpoints', 'priority': 'high'},
                {'id': 'req_2', 'description': 'Implement API authentication', 'priority': 'high'},
                {'id': 'req_3', 'description': 'Create API documentation', 'priority': 'medium'}
            ])
        elif 'database' in prd_lower or 'storage' in prd_lower:
            functional_requirements.extend([
                {'id': 'req_1', 'description': 'Design database schema', 'priority': 'high'},
                {'id': 'req_2', 'description': 'Implement data models', 'priority': 'high'},
                {'id': 'req_3', 'description': 'Create data access layer', 'priority': 'high'}
            ])
        elif 'e-commerce' in prd_lower or 'ecommerce' in prd_lower or ('analytics' in prd_lower and 'dashboard' in prd_lower):
            functional_requirements.extend([
                {'id': 'req_1', 'description': 'Create analytics data pipeline', 'priority': 'high'},
                {'id': 'req_2', 'description': 'Build dashboard visualization components', 'priority': 'high'},
                {'id': 'req_3', 'description': 'Implement real-time metrics tracking', 'priority': 'high'},
                {'id': 'req_4', 'description': 'Design KPI reporting system', 'priority': 'high'},
                {'id': 'req_5', 'description': 'Create data export functionality', 'priority': 'medium'}
            ])
        else:
            # Generic fallback based on content
            features = re.findall(r'(?i)(?:create|build|implement|add|develop)\s+([^,.\n]+)', prd_content)
            for i, feature in enumerate(features[:5]):
                functional_requirements.append({
                    'id': f'req_{i+1}', 
                    'description': feature.strip(), 
                    'priority': 'high'
                })
        
        # Extract non-functional requirements based on keywords
        non_functional_requirements = []
        if 'performance' in prd_lower or 'fast' in prd_lower or 'speed' in prd_lower:
            non_functional_requirements.append({
                'id': 'nfr_1', 
                'description': 'Optimize for performance and responsiveness', 
                'category': 'performance'
            })
        if 'secure' in prd_lower or 'security' in prd_lower:
            non_functional_requirements.append({
                'id': 'nfr_2', 
                'description': 'Implement security best practices', 
                'category': 'security'
            })
        if 'mobile' in prd_lower or 'responsive' in prd_lower:
            non_functional_requirements.append({
                'id': 'nfr_3', 
                'description': 'Ensure mobile responsiveness', 
                'category': 'usability'
            })
        
        # Determine tech stack based on content
        technical_constraints = []
        if 'react' in prd_lower:
            technical_constraints.append('React frontend')
        elif 'vue' in prd_lower:
            technical_constraints.append('Vue.js frontend')
        elif 'angular' in prd_lower:
            technical_constraints.append('Angular frontend')
        elif 'html' in prd_lower or 'canvas' in prd_lower:
            technical_constraints.append('HTML5/Canvas')
        else:
            technical_constraints.append('Modern web technologies')
            
        if 'python' in prd_lower:
            technical_constraints.append('Python backend')
        elif 'node' in prd_lower or 'javascript' in prd_lower:
            technical_constraints.append('Node.js backend')
        elif 'game' in prd_lower:
            technical_constraints.append('JavaScript/Web Audio API')
            
        # Analyze complexity
        word_count = len(prd_content.split())
        complexity = 'high' if word_count > 200 or 'complex' in prd_lower else 'medium'
        
        # Ensure we have at least some requirements
        if not functional_requirements:
            logger.warning("No specific requirements found, using generic requirements")
            functional_requirements = [
                {'id': 'req_1', 'description': 'Implement core functionality', 'priority': 'high'}
            ]
        
        result = {
            'functional_requirements': functional_requirements,
            'non_functional_requirements': non_functional_requirements,
            'technical_constraints': technical_constraints,
            'business_objectives': ['Deliver working solution', 'Meet user requirements'],
            'user_personas': [{'name': 'End User', 'role': 'Primary User', 'goals': ['Easy to use']}],
            'success_metrics': ['All features implemented', 'Tests passing'],
            'implementation_approach': 'agile_iterative',
            'complexity_assessment': {'technical': complexity, 'timeline': 'medium', 'resource': 'medium'},
            'risk_factors': [
                {'category': 'technical', 'description': 'Implementation complexity', 'impact': complexity}
            ],
            'confidence': 0.7
        }
        
        logger.info(f"Simulation result: {len(result['functional_requirements'])} functional reqs, "
                   f"{len(result['non_functional_requirements'])} non-functional reqs")
        
        return result
    
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
    
    async def _simulate_prd_analysis_enhanced(self, prd_content: str) -> Dict[str, Any]:
        """Enhanced PRD simulation with better pattern matching"""
        prd_lower = prd_content.lower()
        logger.info(f"Running enhanced PRD simulation for content: {prd_content[:100]}...")
        
        # Enhanced pattern matching
        functional_requirements = []
        
        # More comprehensive keyword matching
        project_type_patterns = {
            'web_app': ['web app', 'webapp', 'website', 'web application', 'frontend', 'backend'],
            'mobile_app': ['mobile app', 'ios app', 'android app', 'mobile application'],
            'api': ['api', 'rest api', 'graphql', 'endpoint', 'microservice'],
            'dashboard': ['dashboard', 'analytics', 'reporting', 'metrics', 'charts'],
            'ecommerce': ['e-commerce', 'ecommerce', 'shop', 'store', 'marketplace', 'payment'],
            'todo_app': ['todo', 'task', 'tasks', 'to-do', 'checklist'],
            'game': ['game', 'gaming', 'rhythm game', 'fnf', 'friday night funkin'],
            'cms': ['cms', 'content management', 'blog', 'articles', 'publishing'],
            'social': ['social', 'chat', 'messaging', 'forum', 'community'],
            'auth': ['authentication', 'login', 'signup', 'user management', 'auth']
        }
        
        detected_types = []
        for project_type, keywords in project_type_patterns.items():
            if any(keyword in prd_lower for keyword in keywords):
                detected_types.append(project_type)
        
        # Generate requirements based on detected project types
        for project_type in detected_types:
            if project_type == 'web_app':
                functional_requirements.extend([
                    {'id': 'req_ui', 'description': 'Create responsive user interface', 'priority': 'high'},
                    {'id': 'req_nav', 'description': 'Implement navigation system', 'priority': 'high'},
                    {'id': 'req_layout', 'description': 'Design page layouts and components', 'priority': 'medium'}
                ])
            elif project_type == 'api':
                functional_requirements.extend([
                    {'id': 'req_endpoints', 'description': 'Design API endpoints', 'priority': 'high'},
                    {'id': 'req_auth', 'description': 'Implement API authentication', 'priority': 'high'},
                    {'id': 'req_docs', 'description': 'Create API documentation', 'priority': 'medium'}
                ])
            elif project_type == 'todo_app':
                functional_requirements.extend([
                    {'id': 'req_crud', 'description': 'Implement task CRUD operations', 'priority': 'high'},
                    {'id': 'req_status', 'description': 'Add task status management', 'priority': 'high'},
                    {'id': 'req_filter', 'description': 'Create task filtering and search', 'priority': 'medium'}
                ])
            elif project_type == 'dashboard':
                functional_requirements.extend([
                    {'id': 'req_viz', 'description': 'Create data visualizations', 'priority': 'high'},
                    {'id': 'req_realtime', 'description': 'Implement real-time data updates', 'priority': 'high'},
                    {'id': 'req_export', 'description': 'Add data export functionality', 'priority': 'medium'}
                ])
        
        # Fallback: Use enhanced regex patterns if no specific type detected
        if not functional_requirements:
            # Multiple patterns for better extraction
            patterns = [
                r'(?i)(?:create|build|implement|add|develop|design)\s+(?:a\s+|an\s+)?([^,.\n!?]+)',
                r'(?i)(?:need|want|should|must)\s+(?:to\s+)?(?:have\s+|be\s+able\s+to\s+)?([^,.\n!?]+)',
                r'(?i)(?:user|admin|customer)\s+(?:can|should|must)\s+([^,.\n!?]+)',
                r'(?i)(?:system|app|application)\s+(?:will|should|must)\s+([^,.\n!?]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, prd_content)
                for i, match in enumerate(matches[:3]):  # Limit to 3 per pattern
                    if match.strip() and len(match.strip()) > 5:  # Avoid short meaningless matches
                        functional_requirements.append({
                            'id': f'req_extracted_{len(functional_requirements)+1}',
                            'description': match.strip().capitalize(),
                            'priority': 'high'
                        })
        
        # Ensure we have at least one requirement
        if not functional_requirements:
            functional_requirements.append({
                'id': 'req_generic',
                'description': 'Implement core application functionality',
                'priority': 'high'
            })
        
        # Enhanced non-functional requirements detection
        non_functional_requirements = []
        nfr_keywords = {
            'performance': ['performance', 'fast', 'speed', 'optimize', 'efficient', 'latency'],
            'security': ['secure', 'security', 'auth', 'encryption', 'safety', 'protection'],
            'usability': ['user-friendly', 'intuitive', 'easy', 'accessible', 'ux', 'ui'],
            'scalability': ['scalable', 'scale', 'growth', 'load', 'traffic', 'concurrent'],
            'reliability': ['reliable', 'stable', 'robust', 'availability', 'uptime']
        }
        
        for category, keywords in nfr_keywords.items():
            if any(keyword in prd_lower for keyword in keywords):
                non_functional_requirements.append({
                    'id': f'nfr_{category}',
                    'description': f'Ensure {category} requirements are met',
                    'category': category
                })
        
        return {
            'functional_requirements': functional_requirements,
            'non_functional_requirements': non_functional_requirements,
            'technical_constraints': self._detect_tech_stack(prd_content),
            'business_objectives': self._extract_business_objectives(prd_content),
            'user_personas': [],
            'success_metrics': [],
            'implementation_approach': 'agile_iterative',
            'complexity_assessment': {'overall': 'medium'},
            'risk_factors': [],
            'confidence': 0.7  # Higher confidence than basic simulation
        }
    
    def _detect_tech_stack(self, prd_content: str) -> List[str]:
        """Detect technology stack mentions"""
        prd_lower = prd_content.lower()
        tech_stack = []
        
        tech_keywords = {
            'React': ['react', 'react.js', 'reactjs'],
            'Vue.js': ['vue', 'vue.js', 'vuejs'],
            'Angular': ['angular'],
            'Node.js': ['node', 'node.js', 'nodejs'],
            'Python': ['python', 'django', 'flask', 'fastapi'],
            'JavaScript': ['javascript', 'js'],
            'TypeScript': ['typescript', 'ts'],
            'Database': ['database', 'db', 'sql', 'postgres', 'mysql', 'mongodb']
        }
        
        for tech, keywords in tech_keywords.items():
            if any(keyword in prd_lower for keyword in keywords):
                tech_stack.append(tech)
        
        return tech_stack
    
    def _extract_business_objectives(self, prd_content: str) -> List[str]:
        """Extract business objectives from content"""
        objectives = []
        prd_lower = prd_content.lower()
        
        if 'revenue' in prd_lower or 'profit' in prd_lower:
            objectives.append('Increase revenue')
        if 'user' in prd_lower and ('engagement' in prd_lower or 'retention' in prd_lower):
            objectives.append('Improve user engagement')
        if 'efficiency' in prd_lower or 'productivity' in prd_lower:
            objectives.append('Improve operational efficiency')
        
        return objectives

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
        
        # Generate acceptance criteria based on task type
        acceptance_criteria = self._generate_acceptance_criteria(task_type, project_context, name)
        
        # Generate subtasks to break down the work
        subtasks = self._generate_subtasks(task_type, project_context, name)
        
        return {
            'name': name,
            'description': description,
            'estimated_hours': estimated_hours,
            'labels': labels,
            'due_date': None,
            'acceptance_criteria': acceptance_criteria,
            'subtasks': subtasks
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
    
    def _extract_project_context(self, analysis: PRDAnalysis, task_id: str, epic_id: str) -> Dict[str, Any]:
        """Extract meaningful project context from PRD analysis"""
        context = {
            'business_objectives': analysis.business_objectives[:3] if analysis.business_objectives else ['deliver working solution'],
            'technical_constraints': analysis.technical_constraints[:3] if analysis.technical_constraints else ['standard web application'],
            'functional_requirements': analysis.functional_requirements[:5] if analysis.functional_requirements else [],
            'project_type': 'web application',  # Default
            'domain': 'general'
        }
        
        # Determine project type and domain from requirements and constraints
        all_text = ' '.join([
            ' '.join(analysis.business_objectives),
            ' '.join(analysis.technical_constraints),
            ' '.join([req.get('description', '') for req in analysis.functional_requirements])
        ]).lower()
        
        if any(word in all_text for word in ['auth', 'login', 'user', 'account']):
            context['domain'] = 'user_management'
            context['project_type'] = 'user authentication system'
        elif any(word in all_text for word in ['api', 'service', 'endpoint']):
            context['domain'] = 'backend_services'
            context['project_type'] = 'backend service'
        elif any(word in all_text for word in ['ui', 'interface', 'frontend', 'react']):
            context['domain'] = 'frontend'
            context['project_type'] = 'frontend application'
        elif any(word in all_text for word in ['data', 'analytics', 'report']):
            context['domain'] = 'data_analytics'
            context['project_type'] = 'data analytics platform'
        elif any(word in all_text for word in ['ecommerce', 'shop', 'cart', 'product']):
            context['domain'] = 'ecommerce'
            context['project_type'] = 'e-commerce platform'
        
        # Extract specific requirements that match this task/epic
        relevant_requirements = []
        for req in analysis.functional_requirements:
            req_text = req.get('description', '').lower()
            if (task_id.lower() in req_text or 
                epic_id.lower() in req_text or
                any(keyword in req_text for keyword in task_id.lower().split('_'))):
                relevant_requirements.append(req)
        
        context['relevant_requirements'] = relevant_requirements[:2]  # Top 2 most relevant
        
        return context
    
    def _generate_design_task(self, context: Dict[str, Any], task_id: str) -> Tuple[str, str]:
        """Generate design task name and description using PRD context"""
        domain = context['domain']
        project_type = context['project_type']
        objectives = context['business_objectives']
        
        if domain == 'user_management':
            name = "Design User Authentication Flow"
            description = f"Design comprehensive user authentication and account management system for {project_type}. Define user registration, login, password reset flows, session management, and security protocols. Include wireframes, user flows, and technical specifications. Business goal: {objectives[0] if objectives else 'secure user access'}."
        elif domain == 'frontend':
            name = "Design User Interface Architecture"
            description = f"Create detailed UI/UX design for {project_type}. Include component hierarchy, design system, responsive layouts, and user interaction patterns. Focus on achieving: {objectives[0] if objectives else 'excellent user experience'}. Define accessibility standards and usability requirements."
        elif domain == 'backend_services':
            name = "Design API Architecture"
            description = f"Design RESTful API architecture for {project_type}. Define endpoint specifications, data models, request/response schemas, authentication mechanisms, and error handling. Ensure scalability for: {objectives[0] if objectives else 'reliable service delivery'}."
        elif domain == 'ecommerce':
            name = "Design E-commerce User Experience"
            description = f"Design comprehensive e-commerce user experience for {project_type}. Include product catalog, shopping cart, checkout flow, user accounts, and order management. Optimize for: {objectives[0] if objectives else 'seamless shopping experience'}."
        else:
            name = f"Design {project_type.title()} Architecture"
            description = f"Create architectural design for {project_type}. Define system components, data flow, user interactions, and technical specifications. Support business objective: {objectives[0] if objectives else 'effective solution delivery'}."
        
        # Add specific requirements if available
        if context['relevant_requirements']:
            req = context['relevant_requirements'][0]
            description += f" Specific requirement: {req.get('description', '')[:100]}..."
        
        return name, description
    
    def _generate_implementation_task(self, context: Dict[str, Any], task_id: str) -> Tuple[str, str]:
        """Generate implementation task name and description using PRD context"""
        domain = context['domain']
        project_type = context['project_type']
        tech_constraints = context['technical_constraints']
        
        if domain == 'user_management':
            name = "Implement User Authentication Service"
            description = f"Build secure user authentication service for {project_type}. Implement user registration, login, JWT token management, password hashing with bcrypt, and session handling. Technology stack: {', '.join(tech_constraints)}. Include rate limiting, email verification, and comprehensive error handling."
        elif domain == 'frontend':
            name = "Build User Interface Components"
            description = f"Develop responsive UI components for {project_type}. Create reusable component library, implement state management, handle user interactions, and ensure accessibility compliance. Using: {', '.join(tech_constraints)}. Include loading states, error boundaries, and responsive design."
        elif domain == 'backend_services':
            name = "Develop Backend API Services"
            description = f"Implement backend API services for {project_type}. Build RESTful endpoints, implement business logic, add data validation, error handling, and logging. Technology: {', '.join(tech_constraints)}. Include API documentation, performance optimization, and security measures."
        elif domain == 'ecommerce':
            name = "Build E-commerce Core Features"
            description = f"Implement core e-commerce functionality for {project_type}. Build product catalog, shopping cart, checkout process, payment integration, and order management. Stack: {', '.join(tech_constraints)}. Include inventory management and order tracking."
        else:
            name = f"Implement {project_type.title()} Core Features"
            description = f"Build core functionality for {project_type}. Implement business logic, data processing, user interfaces, and system integrations. Using: {', '.join(tech_constraints)}. Include proper error handling, logging, and performance optimization."
        
        # Add specific requirements if available
        if context['relevant_requirements']:
            req = context['relevant_requirements'][0]
            description += f" Addresses requirement: {req.get('description', '')[:100]}..."
        
        return name, description
    
    def _generate_testing_task(self, context: Dict[str, Any], task_id: str) -> Tuple[str, str]:
        """Generate testing task name and description using PRD context"""
        domain = context['domain']
        project_type = context['project_type']
        
        if domain == 'user_management':
            name = "Test Authentication Security Features"
            description = f"Create comprehensive test suite for user authentication in {project_type}. Include unit tests for login/registration, integration tests for JWT flows, security testing for password policies, and end-to-end user journey tests. Achieve >80% code coverage."
        elif domain == 'frontend':
            name = "Test User Interface Components"
            description = f"Develop UI testing suite for {project_type}. Include component unit tests, user interaction tests, accessibility testing, responsive design validation, and cross-browser compatibility tests. Test all user flows and error states."
        elif domain == 'backend_services':
            name = "Test API Functionality and Performance"
            description = f"Create API testing suite for {project_type}. Include endpoint unit tests, integration tests, load testing, security testing, and error handling validation. Test data validation, authentication, and business logic. Achieve >80% coverage."
        elif domain == 'ecommerce':
            name = "Test E-commerce Transaction Flows"
            description = f"Develop comprehensive testing for {project_type}. Test shopping cart functionality, checkout process, payment integration, order management, and inventory updates. Include security testing for payment processing and fraud prevention."
        else:
            name = f"Test {project_type.title()} Functionality"
            description = f"Create comprehensive test suite for {project_type}. Include unit tests, integration tests, and end-to-end testing. Validate business logic, user workflows, and system reliability. Achieve >80% code coverage."
        
        return name, description
    
    def _generate_infrastructure_task(self, context: Dict[str, Any], task_id: str) -> Tuple[str, str]:
        """Generate infrastructure task name and description using PRD context"""
        project_type = context['project_type']
        tech_constraints = context['technical_constraints']
        
        if 'setup' in task_id.lower():
            name = "Setup Development Environment"
            description = f"Configure complete development environment for {project_type}. Set up local development stack, database, environment variables, development tools, and project dependencies. Technology: {', '.join(tech_constraints)}. Include Docker containers, hot reloading, and debugging tools."
        elif 'ci' in task_id.lower() or 'cd' in task_id.lower():
            name = "Configure CI/CD Pipeline"
            description = f"Set up continuous integration and deployment for {project_type}. Configure automated testing, code quality checks, building, and deployment to staging/production. Using: {', '.join(tech_constraints)}. Include security scanning and performance monitoring."
        elif 'deploy' in task_id.lower():
            name = "Setup Production Deployment"
            description = f"Configure production infrastructure for {project_type}. Set up hosting, load balancing, monitoring, logging, backup systems, and security measures. Technology: {', '.join(tech_constraints)}. Include scaling strategy and disaster recovery."
        else:
            name = "Configure System Infrastructure"
            description = f"Set up core infrastructure for {project_type}. Configure servers, databases, caching, monitoring, and security systems. Stack: {', '.join(tech_constraints)}. Include performance optimization and maintenance procedures."
        
        return name, description
    
    def _generate_generic_task(self, context: Dict[str, Any], task_id: str) -> Tuple[str, str]:
        """Generate generic task name and description using PRD context"""
        project_type = context['project_type']
        objectives = context['business_objectives']
        
        # Try to infer from task_id what this might be about
        if 'nfr' in task_id.lower():
            name = f"Implement Non-Functional Requirements"
            description = f"Address performance, security, and scalability requirements for {project_type}. Implement caching, optimize database queries, add security headers, and ensure system reliability. Target: {objectives[0] if objectives else 'system performance'}."
        elif any(keyword in task_id.lower() for keyword in ['req_0', 'req_1', 'req_2']):
            req_index = next((i for i, keyword in enumerate(['req_0', 'req_1', 'req_2']) if keyword in task_id.lower()), 0)
            if req_index < len(context['functional_requirements']):
                req = context['functional_requirements'][req_index]
                req_desc = req.get('description', 'feature requirement')
                name = f"Implement {req_desc[:30]}..."
                description = f"Complete implementation of: {req_desc}. For {project_type} to achieve: {objectives[0] if objectives else 'project goals'}."
            else:
                name = f"Implement Core {project_type.title()} Feature"
                description = f"Build essential functionality for {project_type}. Implement core business logic, user interactions, and system integrations to achieve: {objectives[0] if objectives else 'project success'}."
        else:
            name = f"Develop {project_type.title()} Component"
            description = f"Build and integrate component for {project_type}. Implement required functionality, ensure proper testing, and maintain code quality standards. Supports: {objectives[0] if objectives else 'project objectives'}."
        
        return name, description
    
    def _generate_labels(self, task_type: str, context: Dict[str, Any], constraints: ProjectConstraints) -> List[str]:
        """Generate appropriate labels following Board Quality Standards taxonomy"""
        labels = []
        
        # Component labels
        domain = context['domain']
        if domain == 'user_management':
            labels.append('component:authentication')
        elif domain == 'frontend':
            labels.append('component:frontend')
        elif domain == 'backend_services':
            labels.append('component:backend')
        elif domain == 'ecommerce':
            labels.append('component:ecommerce')
        else:
            labels.append('component:backend')  # Default
        
        # Type labels
        if task_type == 'design':
            labels.append('type:design')
        elif task_type == 'implementation':
            labels.append('type:feature')
        elif task_type == 'testing':
            labels.append('type:testing')
        elif task_type == 'setup':
            labels.append('type:setup')
        else:
            labels.append('type:feature')
        
        # Priority labels (default to medium)
        labels.append('priority:medium')
        
        # Skill labels based on constraints
        if constraints.available_skills:
            for skill in constraints.available_skills[:1]:  # Take first skill
                if skill.lower() in ['react', 'vue', 'angular']:
                    labels.append('skill:frontend')
                    break
                elif skill.lower() in ['node.js', 'nodejs', 'python', 'java']:
                    labels.append('skill:backend')
                    break
                elif skill.lower() in ['docker', 'kubernetes', 'aws']:
                    labels.append('skill:devops')
                    break
                else:
                    labels.append(f'skill:{skill.lower()}')
                    break
        else:
            labels.append('skill:fullstack')
        
        # Complexity labels
        if task_type in ['design', 'setup']:
            labels.append('complexity:moderate')
        elif task_type == 'testing':
            labels.append('complexity:simple')
        else:
            labels.append('complexity:moderate')
        
        return labels
    
    def _generate_acceptance_criteria(self, task_type: str, context: Dict[str, Any], task_name: str) -> List[str]:
        """Generate acceptance criteria based on task type and context"""
        criteria = []
        
        if task_type == 'design':
            criteria = [
                "Design documentation is complete with all components specified",
                "User flows and wireframes are created and reviewed",
                "Technical architecture is documented and approved",
                "Design system components are defined",
                "Accessibility requirements are documented"
            ]
        elif task_type == 'implementation':
            criteria = [
                "All functionality is implemented as per specifications",
                "Code passes all unit tests with >80% coverage",
                "Code follows project coding standards and conventions",
                "API endpoints are documented and tested",
                "Error handling and validation are implemented",
                "Performance meets defined benchmarks"
            ]
        elif task_type == 'testing':
            criteria = [
                "All test cases are written and documented",
                "Unit tests achieve >80% code coverage",
                "Integration tests cover all API endpoints",
                "End-to-end tests validate user workflows",
                "Performance tests meet SLA requirements",
                "Test results are documented and reviewed"
            ]
        elif task_type == 'setup':
            criteria = [
                "Development environment runs successfully",
                "All dependencies are installed and documented",
                "Configuration files are properly set up",
                "Database migrations run without errors",
                "README includes setup instructions",
                "Team members can successfully run the project"
            ]
        elif task_type == 'deployment':
            criteria = [
                "Application deploys successfully to target environment",
                "All environment variables are configured",
                "Health checks pass in production",
                "Monitoring and logging are operational",
                "Rollback procedure is documented and tested",
                "Performance meets production requirements"
            ]
        else:
            # Generic criteria for feature tasks
            criteria = [
                f"{task_name} is fully implemented and functional",
                "Feature works as specified in requirements",
                "Code is tested and passes all tests",
                "Documentation is updated",
                "Code review is completed and approved"
            ]
        
        # Add context-specific criteria
        if context.get('domain') == 'user_management':
            criteria.append("Security requirements are met (authentication, authorization)")
            criteria.append("User data privacy is properly handled")
        elif context.get('domain') == 'ecommerce':
            criteria.append("Payment processing is secure and PCI compliant")
            criteria.append("Order workflow is thoroughly tested")
        
        return criteria[:5]  # Return top 5 most relevant criteria
    
    def _generate_subtasks(self, task_type: str, context: Dict[str, Any], task_name: str) -> List[str]:
        """Generate subtasks to break down the work"""
        subtasks = []
        
        if task_type == 'design':
            subtasks = [
                "Research existing solutions and best practices",
                "Create initial wireframes and mockups",
                "Design component hierarchy and data flow",
                "Document API contracts and interfaces",
                "Create design system tokens and components",
                "Review design with stakeholders"
            ]
        elif task_type == 'implementation':
            # Parse the task name to understand what we're implementing
            if 'authentication' in task_name.lower():
                subtasks = [
                    "Set up authentication middleware",
                    "Implement user registration endpoint",
                    "Create login/logout functionality",
                    "Add password reset flow",
                    "Implement JWT token management",
                    "Add session management",
                    "Create user profile endpoints"
                ]
            elif 'database' in task_name.lower():
                subtasks = [
                    "Design database schema",
                    "Create migration scripts",
                    "Set up database connections",
                    "Implement data models",
                    "Add database indexes",
                    "Create seed data scripts"
                ]
            elif 'api' in task_name.lower():
                subtasks = [
                    "Define API endpoints and routes",
                    "Implement request validation",
                    "Create response serializers",
                    "Add error handling middleware",
                    "Implement rate limiting",
                    "Add API documentation"
                ]
            else:
                # Generic implementation subtasks
                subtasks = [
                    "Create data models and schemas",
                    "Implement business logic layer",
                    "Create API endpoints",
                    "Add input validation",
                    "Implement error handling",
                    "Write unit tests",
                    "Add integration tests"
                ]
        elif task_type == 'testing':
            subtasks = [
                "Write unit test specifications",
                "Implement unit tests for models",
                "Create integration test suite",
                "Add API endpoint tests",
                "Write end-to-end test scenarios",
                "Set up test data fixtures",
                "Configure test automation"
            ]
        elif task_type == 'setup':
            subtasks = [
                "Initialize project repository",
                "Set up development dependencies",
                "Configure build tools",
                "Create environment configuration",
                "Set up database connections",
                "Configure linting and formatting",
                "Create development scripts"
            ]
        elif task_type == 'deployment':
            subtasks = [
                "Create deployment configuration",
                "Set up CI/CD pipeline",
                "Configure environment variables",
                "Set up monitoring and alerts",
                "Create deployment scripts",
                "Configure load balancing",
                "Set up backup procedures"
            ]
        else:
            # Generic feature subtasks
            subtasks = [
                f"Plan {task_name} implementation",
                "Implement core functionality",
                "Add data persistence layer",
                "Create user interface components",
                "Write tests",
                "Update documentation"
            ]
        
        # Customize based on context
        if context.get('tech_stack'):
            tech = context['tech_stack']
            if 'React' in tech and task_type == 'implementation':
                subtasks.extend([
                    "Create React components",
                    "Set up component state management",
                    "Add component styling"
                ])
            elif 'Django' in tech and task_type == 'implementation':
                subtasks.extend([
                    "Create Django models",
                    "Add Django views and serializers",
                    "Configure Django admin"
                ])
        
        return subtasks[:7]  # Return top 7 most relevant subtasks