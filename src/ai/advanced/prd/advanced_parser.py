"""
Advanced PRD Parser for Marcus Phase 4

Transform natural language requirements into actionable tasks with
deep understanding, intelligent task breakdown, and risk assessment.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.types import AnalysisContext
from src.config.hybrid_inference_config import HybridInferenceConfig
from src.core.models import Priority, Task, TaskStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer

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
    available_skills: Optional[List[str]] = None
    technology_constraints: Optional[List[str]] = None
    quality_requirements: Optional[Dict[str, Any]] = None
    deployment_target: str = "local"  # local, dev, prod, remote

    def __post_init__(self) -> None:
        if self.available_skills is None:
            self.available_skills = []
        if self.technology_constraints is None:
            self.technology_constraints = []
        if self.quality_requirements is None:
            self.quality_requirements = {}
        # Validate deployment target
        if self.deployment_target not in ["local", "dev", "prod", "remote"]:
            self.deployment_target = "local"


class AdvancedPRDParser:
    """
    Advanced PRD parser that converts natural language requirements
    into complete task breakdown with intelligent dependencies and risk assessment
    """

    def __init__(self, hybrid_config: Optional[HybridInferenceConfig] = None):
        self.llm_client = LLMAbstraction()

        # Set up hybrid dependency inference with configurable thresholds
        ai_engine = (
            AIAnalysisEngine()
            if hybrid_config and hybrid_config.enable_ai_inference
            else None
        )
        self.dependency_inferer = HybridDependencyInferer(ai_engine, hybrid_config)

        # PRD parsing configuration
        self.max_tasks_per_epic = 8
        self.min_task_complexity_hours = 1
        self.max_task_complexity_hours = 40

        # Standard project phases for task organization
        self.standard_phases = [
            "research_and_planning",
            "design_and_architecture",
            "setup_and_configuration",
            "core_development",
            "integration_and_testing",
            "deployment_and_launch",
            "monitoring_and_optimization",
        ]

        # Risk assessment categories
        self.risk_categories = [
            "technical_complexity",
            "integration_challenges",
            "performance_requirements",
            "security_concerns",
            "scalability_needs",
            "external_dependencies",
            "timeline_pressure",
            "resource_constraints",
        ]

        logger.info("Advanced PRD parser initialized")

    async def parse_prd_to_tasks(
        self, prd_content: str, constraints: ProjectConstraints
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
        logger.info(
            f"PRD analysis found {len(prd_analysis.functional_requirements)} functional requirements"
        )
        task_hierarchy = await self._generate_task_hierarchy(prd_analysis, constraints)

        # Step 3: Create detailed tasks
        logger.info(
            f"Creating detailed tasks from hierarchy with {len(task_hierarchy)} epics"
        )
        tasks = await self._create_detailed_tasks(
            task_hierarchy, prd_analysis, constraints
        )
        logger.info(f"Created {len(tasks)} detailed tasks")

        # Step 4: AI-powered dependency inference
        dependencies = await self._infer_smart_dependencies(tasks, prd_analysis)

        # Step 5: Risk assessment and timeline prediction
        risk_assessment = await self._assess_implementation_risks(
            tasks, prd_analysis, constraints
        )
        timeline_prediction = await self._predict_timeline(
            tasks, dependencies, constraints
        )

        # Step 6: Resource requirement analysis
        resource_requirements = await self._analyze_resource_requirements(
            tasks, prd_analysis, constraints
        )

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
            generation_confidence=self._calculate_generation_confidence(
                prd_analysis, tasks
            ),
        )

    async def _analyze_prd_deeply(self, prd_content: str) -> PRDAnalysis:
        """Perform deep analysis of PRD using AI"""
        analysis_prompt = f"""
        Analyze this Product Requirements Document in detail:

        {prd_content}

        Provide a comprehensive analysis in the following EXACT JSON format:
        {{
            "functionalRequirements": [
                {{
                    "id": "unique_feature_id",
                    "name": "Feature Name",
                    "description": "Detailed description of the feature",
                    "priority": "high|medium|low"
                }}
            ],
            "nonFunctionalRequirements": [
                {{
                    "id": "nfr_id",
                    "name": "Requirement Name",
                    "description": "Detailed description",
                    "category": "performance|security|usability|scalability"
                }}
            ],
            "technicalConstraints": ["constraint1", "constraint2"],
            "businessObjectives": ["objective1", "objective2"],
            "userPersonas": [
                {{
                    "name": "Persona Name",
                    "description": "Persona description",
                    "needs": ["need1", "need2"]
                }}
            ],
            "successMetrics": ["metric1", "metric2"],
            "implementationApproach": "agile|waterfall|iterative",
            "complexityAssessment": {{
                "technical": "low|medium|high",
                "timeline": "days|weeks|months",
                "resources": "small|medium|large"
            }},
            "riskFactors": [
                {{
                    "risk": "Risk description",
                    "impact": "low|medium|high",
                    "mitigation": "Mitigation strategy"
                }}
            ],
            "confidence": 0.85
        }}

        IMPORTANT:
        - For functionalRequirements, use "id", "name", "description", and "priority" fields
        - For nonFunctionalRequirements, use "id", "name", "description", and "category" fields
        - Generate meaningful IDs based on the feature name (e.g., "crud_operations", "user_auth")
        - Focus on extracting actionable, specific requirements that can be converted into development tasks
        """

        try:
            # Use AI to analyze PRD
            # Create a simple context object that has max_tokens
            class SimpleContext:
                def __init__(self, max_tokens: int) -> None:
                    self.max_tokens = max_tokens

            context = SimpleContext(max_tokens=2000)

            logger.info("Attempting to use LLM for PRD analysis...")

            # Track AI analysis start
            ai_start_time = datetime.now()
            flow_id = getattr(self, "_current_flow_id", None)
            if flow_id and hasattr(self, "_pipeline_visualizer"):
                self._pipeline_visualizer.add_event(
                    flow_id=flow_id,
                    stage=PipelineStage.AI_ANALYSIS,
                    event_type="ai_analysis_started",
                    data={
                        "prd_length": len(prd_content),
                        "model": getattr(
                            self.llm_client, "current_provider", "unknown"
                        ),
                    },
                    status="in_progress",
                )

            # Use the actual LLM to analyze the PRD
            analysis_result = await self.llm_client.analyze(
                prompt=analysis_prompt, context=context
            )

            logger.info(
                f"LLM response received: {len(analysis_result) if analysis_result else 0} chars"
            )

            # Parse the AI response using our JSON parser utility
            from src.utils.json_parser import parse_ai_json_response

            try:
                analysis_data = parse_ai_json_response(analysis_result)
                logger.info("Successfully parsed AI response as JSON")
            except (json.JSONDecodeError, ValueError) as e:
                from src.core.error_framework import AIProviderError, ErrorContext

                logger.error(f"Failed to parse AI response as JSON: {e}")
                logger.error(f"Response was: {analysis_result[:200]}...")

                raise AIProviderError(
                    "LLM",
                    "json_parsing",
                    context=ErrorContext(
                        operation="analyze_prd_deeply",
                        integration_name="advanced_prd_parser",
                        custom_context={
                            "prd_length": len(prd_content),
                            "response_length": (
                                len(analysis_result) if analysis_result else 0
                            ),
                            "parsing_error": str(e),
                            "response_preview": (
                                analysis_result[:200] if analysis_result else "None"
                            ),
                            "details": f"AI returned malformed JSON response. This indicates an issue with the AI provider configuration or the response format. Please check your AI provider settings and try again with a clearer project description.",
                        },
                    ),
                )

            # Handle both snake_case and camelCase keys from AI response
            def get_key(data: Dict[str, Any], snake_key: str, camel_key: Optional[str] = None) -> Any:
                """Get value from dict using either snake_case or camelCase key"""
                if camel_key is None:
                    # Convert snake_case to camelCase
                    parts = snake_key.split("_")
                    camel_key = parts[0] + "".join(
                        word.capitalize() for word in parts[1:]
                    )

                # Prefer camelCase (our template format)
                if camel_key in data:
                    return data[camel_key]
                elif snake_key in data:
                    logger.debug(
                        f"AI used snake_case '{snake_key}' instead of expected camelCase '{camel_key}'"
                    )
                    return data[snake_key]
                else:
                    return []  # Return empty list as default

            return PRDAnalysis(
                functional_requirements=get_key(
                    analysis_data, "functional_requirements", "functionalRequirements"
                ),
                non_functional_requirements=get_key(
                    analysis_data,
                    "non_functional_requirements",
                    "nonFunctionalRequirements",
                ),
                technical_constraints=get_key(
                    analysis_data, "technical_constraints", "technicalConstraints"
                ),
                business_objectives=get_key(
                    analysis_data, "business_objectives", "businessObjectives"
                ),
                user_personas=get_key(analysis_data, "user_personas", "userPersonas"),
                success_metrics=get_key(
                    analysis_data, "success_metrics", "successMetrics"
                ),
                # Note: template uses 'implementationApproach', but old responses might use 'recommendedImplementation'
                implementation_approach=(
                    analysis_data.get("implementationApproach")
                    or analysis_data.get("implementation_approach")
                    or analysis_data.get("recommendedImplementation")
                    or "agile_iterative"
                ),
                complexity_assessment=get_key(
                    analysis_data, "complexity_assessment", "complexityAssessment"
                )
                or {},
                risk_factors=get_key(analysis_data, "risk_factors", "riskFactors"),
                confidence=analysis_data.get("confidence", 0.8),
            )

        except Exception as e:
            from src.core.error_framework import AIProviderError, ErrorContext
            from src.core.error_monitoring import record_error_for_monitoring

            # Create comprehensive AI provider error with actionable context
            ai_error = AIProviderError(
                "LLM",
                "prd_analysis",
                context=ErrorContext(
                    operation="analyze_prd_deeply",
                    integration_name="advanced_prd_parser",
                    custom_context={
                        "prd_length": len(prd_content),
                        "prd_preview": (
                            prd_content[:200] + "..."
                            if len(prd_content) > 200
                            else prd_content
                        ),
                        "error_type": type(e).__name__,
                        "original_error": str(e),
                        "troubleshooting_steps": [
                            "Check AI provider API credentials and configuration",
                            "Verify network connectivity to AI provider",
                            "Try simplifying the project description",
                            "Check AI provider service status",
                            "Ensure project description is in English and well-structured",
                        ],
                        "details": f"AI analysis of project requirements failed. This prevents automatic task generation from your project description. "
                        f"The AI provider ({self.llm_client.__class__.__name__}) encountered an error: {str(e)}. "
                        f"Please check your AI configuration and try again. If the problem persists, contact support with this error context.",
                    },
                ),
            )

            # Record for monitoring and raise the error
            record_error_for_monitoring(ai_error)
            logger.error(f"PRD analysis failed: {ai_error}")

            # Raise the error instead of falling back to simulation
            raise ai_error

    async def _generate_task_hierarchy(
        self, analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> Dict[str, List[str]]:
        """Generate hierarchical task structure"""
        hierarchy: Dict[str, List[str]] = {}

        # Store task metadata for later use
        self._task_metadata = {}

        # Filter requirements based on project size
        project_size = (constraints.quality_requirements or {}).get("project_size", "medium")
        functional_requirements = self._filter_requirements_by_size(
            analysis.functional_requirements, project_size, constraints.team_size
        )

        # Create epics from functional requirements
        for i, req in enumerate(functional_requirements):
            # Prefer standardized 'id' field from template
            req_id = req.get("id")

            if not req_id:
                # Fallback: generate ID from name/feature/description
                feature_name = (
                    req.get("name")
                    or req.get("feature")
                    or req.get("description")
                    or f"requirement_{i}"
                )

                # Generate clean feature ID
                feature_id = feature_name.lower()
                # Remove common words and clean up
                for word in ["for", "the", "a", "an", "and", "or", "with", "using"]:
                    feature_id = feature_id.replace(f" {word} ", " ")
                # Convert to ID format
                feature_id = (
                    feature_id.strip()
                    .replace(" ", "_")
                    .replace("-", "_")
                    .replace(":", "")
                )
                # Remove any non-alphanumeric characters except underscore
                feature_id = "".join(
                    c if c.isalnum() or c == "_" else "" for c in feature_id
                )

                # If we still don't have a good ID, use the index
                if not feature_id or feature_id == "feature":
                    feature_id = f"req_{i}"

                req_id = feature_id
                logger.debug(
                    f"Generated fallback ID '{req_id}' for requirement without 'id' field"
                )

            epic_id = f"epic_{req_id}"
            hierarchy[epic_id] = []

            # Break epic into smaller tasks
            epic_tasks = await self._break_down_epic(req, analysis, constraints)
            logger.debug(f"Epic {epic_id} broken down into {len(epic_tasks)} tasks")

            # Store task metadata for later use
            for task in epic_tasks:
                self._task_metadata[task["id"]] = {
                    "original_name": task["name"],
                    "type": task["type"],
                    "epic_id": epic_id,
                    "requirement": req,
                }

            hierarchy[epic_id] = [task["id"] for task in epic_tasks]

        # Add non-functional requirement tasks (skip for prototype projects)
        if project_size not in ["prototype", "mvp"]:
            nfr_epic_id = "epic_non_functional"
            # Filter NFRs based on project size
            filtered_nfrs = self._filter_nfrs_by_size(
                analysis.non_functional_requirements, project_size
            )
            nfr_tasks = await self._create_nfr_tasks(filtered_nfrs, constraints)

            # Store NFR task metadata
            for task in nfr_tasks:
                self._task_metadata[task["id"]] = {
                    "original_name": task["name"],
                    "type": task["type"],
                    "epic_id": nfr_epic_id,
                    "description": task.get("description", ""),
                    "nfr_data": task.get("nfr_data", {}),
                }

            hierarchy[nfr_epic_id] = [task["id"] for task in nfr_tasks]

        # Add infrastructure and setup tasks (minimal for prototype projects)
        if project_size not in [
            "prototype",
            "mvp",
        ]:  # Prototype projects skip infrastructure
            infra_epic_id = "epic_infrastructure"
            infra_tasks = await self._create_infrastructure_tasks(
                analysis, constraints, project_size
            )

            # Store infrastructure task metadata
            for task in infra_tasks:
                self._task_metadata[task["id"]] = {
                    "original_name": task["name"],
                    "type": task["type"],
                    "epic_id": infra_epic_id,
                }

            hierarchy[infra_epic_id] = [task["id"] for task in infra_tasks]

        return hierarchy

    async def _create_detailed_tasks(
        self,
        task_hierarchy: Dict[str, List[str]],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Task]:
        """Create detailed Task objects with rich metadata"""
        tasks = []
        task_counter = 1

        for epic_id, task_ids in list(task_hierarchy.items()):
            # Skip deployment-related epics based on deployment_target
            if self._should_skip_epic(epic_id, constraints.deployment_target):
                logger.info(
                    f"Skipping {epic_id} for deployment_target={constraints.deployment_target}"
                )
                continue

            for task_id in task_ids:
                # Skip deployment-related tasks based on deployment_target
                if self._should_skip_task(
                    task_id, epic_id, constraints.deployment_target
                ):
                    logger.info(
                        f"Skipping task {task_id} for deployment_target={constraints.deployment_target}"
                    )
                    continue

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
        sequence: int,
    ) -> Task:
        """Generate a detailed task with AI-enhanced metadata"""

        # Extract task information from analysis
        task_info = self._extract_task_info(task_id, epic_id, analysis)

        # Use AI to enhance task details
        enhanced_details = await self._enhance_task_with_ai(
            task_info, analysis, constraints
        )

        # Create task with all metadata
        task = Task(
            id=task_id,
            name=enhanced_details.get("name", f"Task {sequence}"),
            description=enhanced_details.get("description", ""),
            status=TaskStatus.TODO,
            priority=self._determine_priority(task_info, analysis),
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=enhanced_details.get("due_date"),
            estimated_hours=enhanced_details.get("estimated_hours", 1.0),
            dependencies=[],  # Will be filled by dependency inference
            labels=enhanced_details.get("labels", []),
            # New generalization fields
            source_type="nlp_project",
            source_context={
                "prd_analysis": analysis.__dict__ if hasattr(analysis, "__dict__") else {},
                "task_info": task_info,
                "constraints": constraints.__dict__ if hasattr(constraints, "__dict__") else {},
            },
        )

        # Note: acceptance_criteria and subtasks would need to be added to Task model
        # For now, we store them in labels or use a different approach
        if enhanced_details.get("acceptance_criteria"):
            # task.acceptance_criteria = enhanced_details["acceptance_criteria"]  # type: ignore
            pass

        if enhanced_details.get("subtasks"):
            # task.subtasks = enhanced_details["subtasks"]  # type: ignore
            pass

        return task

    async def _infer_smart_dependencies(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Use AI to infer intelligent dependencies"""

        # Use the existing dependency inferer with AI enhancement
        dependency_graph = await self.dependency_inferer.infer_dependencies(tasks)

        # Convert to result format
        dependencies = []
        for edge in dependency_graph.edges:
            dependencies.append(
                {
                    "dependent_task_id": edge.dependent_task_id,
                    "dependency_task_id": edge.dependency_task_id,
                    "dependency_type": edge.dependency_type,
                    "confidence": edge.confidence,
                    "reasoning": edge.reasoning,
                }
            )

        # Add PRD-specific dependencies
        prd_dependencies = await self._add_prd_specific_dependencies(tasks, analysis)
        dependencies.extend(prd_dependencies)

        return dependencies

    async def _assess_implementation_risks(
        self, tasks: List[Task], analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Assess implementation risks with AI analysis"""

        risk_assessment = {
            "overall_risk_level": "medium",
            "risk_factors": [],
            "mitigation_strategies": [],
            "critical_path_risks": [],
            "resource_risks": [],
            "timeline_risks": [],
        }

        # Analyze complexity risks
        complexity_risks = await self._analyze_complexity_risks(tasks, analysis)
        if isinstance(risk_assessment["risk_factors"], list):
            risk_assessment["risk_factors"].extend(complexity_risks)
        else:
            risk_assessment["risk_factors"] = list(complexity_risks)

        # Analyze constraint risks
        constraint_risks = await self._analyze_constraint_risks(tasks, constraints)
        risk_assessment["timeline_risks"] = constraint_risks

        # Generate mitigation strategies
        risk_assessment["mitigation_strategies"] = (
            await self._generate_mitigation_strategies(
                risk_assessment["risk_factors"], tasks, analysis
            )
        )

        # Calculate overall risk level
        risk_count = len(risk_assessment["risk_factors"])
        if risk_count < 3:
            risk_assessment["overall_risk_level"] = "low"
        elif risk_count > 6:
            risk_assessment["overall_risk_level"] = "high"

        return risk_assessment

    async def _predict_timeline(
        self,
        tasks: List[Task],
        dependencies: List[Dict[str, Any]],
        constraints: ProjectConstraints,
    ) -> Dict[str, Any]:
        """Predict project timeline with AI-enhanced estimation"""

        # Calculate critical path
        total_effort = sum(task.estimated_hours or 8 for task in tasks)

        # Adjust for team size and parallel work
        team_productivity = min(
            constraints.team_size, len(tasks) // 2
        )  # Diminishing returns
        parallel_factor = 0.7 if team_productivity > 1 else 1.0

        # Calculate duration
        working_hours_per_day = 6  # Assume 6 productive hours per day
        estimated_days = (total_effort * parallel_factor) / (
            team_productivity * working_hours_per_day
        )

        # Add buffer for unknowns and coordination overhead
        buffer_factor = 1.3  # 30% buffer
        estimated_days *= buffer_factor

        # Timeline prediction
        start_date = datetime.now()
        estimated_completion = start_date + timedelta(days=estimated_days)

        timeline = {
            "estimated_duration_days": int(estimated_days),
            "estimated_completion_date": estimated_completion.isoformat(),
            "total_effort_hours": total_effort,
            "critical_path_tasks": await self._identify_critical_path_tasks(
                tasks, dependencies
            ),
            "milestone_dates": await self._calculate_milestone_dates(
                start_date, estimated_days
            ),
            "confidence_interval": {
                "optimistic_days": int(estimated_days * 0.8),
                "pessimistic_days": int(estimated_days * 1.4),
            },
        }

        return timeline

    async def _analyze_resource_requirements(
        self, tasks: List[Task], analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Analyze resource requirements"""

        # Skill requirements analysis
        skill_requirements = await self._analyze_skill_requirements(tasks, analysis)

        # Tool and technology requirements
        tech_requirements = await self._analyze_tech_requirements(analysis, constraints)

        # External dependency analysis
        external_deps = await self._analyze_external_dependencies(analysis)

        return {
            "required_skills": skill_requirements,
            "technology_stack": tech_requirements,
            "external_dependencies": external_deps,
            "estimated_team_size": self._calculate_optimal_team_size(
                tasks, constraints
            ),
            "specialized_roles_needed": await self._identify_specialized_roles(
                tasks, analysis
            ),
        }

    async def _generate_success_criteria(
        self, analysis: PRDAnalysis, tasks: List[Task]
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
        self, analysis: PRDAnalysis, tasks: List[Task]
    ) -> float:
        """Calculate confidence in task generation quality"""
        factors = []

        # PRD analysis confidence
        factors.append(analysis.confidence)

        # Task detail completeness
        detailed_tasks = sum(
            1 for task in tasks if task.description and len(task.description) > 20
        )
        task_detail_score = detailed_tasks / len(tasks) if tasks else 0
        factors.append(task_detail_score)

        # Requirement coverage
        req_count = len(analysis.functional_requirements) + len(
            analysis.non_functional_requirements
        )
        coverage_score = min(
            len(tasks) / max(req_count * 3, 1), 1.0
        )  # Expect 3 tasks per requirement
        factors.append(coverage_score)

        return sum(factors) / len(factors) if factors else 0.5

    # Removed fallback simulation methods - now uses proper Marcus Error Framework
    # When AI analysis fails, the system will raise appropriate errors with actionable feedback

    # Additional helper methods would be implemented here...
    async def _break_down_epic(
        self,
        req: Dict[str, Any],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """Break down epic into smaller tasks"""
        # First try to use standardized fields (from our template)
        req_id = req.get("id")
        feature_name = req.get("name")

        # Fallback to other possible field names if template wasn't followed
        if not feature_name:
            feature_name = req.get("feature") or req.get("description") or "feature"
            logger.warning(
                f"AI deviated from template format. Expected 'name' field but got: {list(req.keys())}"
            )

        if not req_id:
            # Generate ID from feature name as fallback
            feature_id = feature_name.lower()
            # Remove common words and clean up
            for word in ["for", "the", "a", "an", "and", "or", "with", "using"]:
                feature_id = feature_id.replace(f" {word} ", " ")
            # Convert to ID format
            feature_id = (
                feature_id.strip().replace(" ", "_").replace("-", "_").replace(":", "")
            )
            # Remove any non-alphanumeric characters except underscore
            feature_id = "".join(
                c if c.isalnum() or c == "_" else "" for c in feature_id
            )

            # If we still don't have a good ID, use the index from functional requirements
            if not feature_id or feature_id == "feature":
                req_index = (
                    analysis.functional_requirements.index(req)
                    if req in analysis.functional_requirements
                    else 0
                )
                feature_id = f"req_{req_index}"

            req_id = feature_id
            logger.warning(
                f"AI deviated from template format. Expected 'id' field, generated: {req_id}"
            )

        return [
            {
                "id": f"task_{req_id}_design",
                "name": f"Design {feature_name}",
                "type": "design",
            },
            {
                "id": f"task_{req_id}_implement",
                "name": f"Implement {feature_name}",
                "type": "implementation",
            },
            {
                "id": f"task_{req_id}_test",
                "name": f"Test {feature_name}",
                "type": "testing",
            },
        ]

    async def _create_nfr_tasks(
        self, nfrs: List[Dict[str, Any]], constraints: ProjectConstraints
    ) -> List[Dict[str, Any]]:
        """Create non-functional requirement tasks"""
        tasks = []
        for i, nfr in enumerate(nfrs):
            # Prefer standardized fields from template
            nfr_id = nfr.get("id")
            nfr_name = nfr.get("name")

            # Fallback to other fields if template wasn't followed
            if not nfr_name:
                nfr_name = (
                    nfr.get("requirement") or nfr.get("description") or f"NFR {i+1}"
                )
                if nfr.get("requirement") or nfr.get("description"):
                    logger.warning(
                        f"NFR deviated from template format. Expected 'name' field but got: {list(nfr.keys())}"
                    )

            if not nfr_id:
                # Generate clean ID as fallback
                req_id = nfr_name.lower().replace(" ", "_").replace("-", "_")
                req_id = "".join(c if c.isalnum() or c == "_" else "" for c in req_id)
                nfr_id = req_id or str(i)
                logger.warning(
                    f"NFR deviated from template format. Expected 'id' field, generated: {nfr_id}"
                )

            # Get the description from the NFR data
            nfr_description = nfr.get("description", "")
            
            tasks.append(
                {
                    "id": f"nfr_task_{nfr_id}",
                    "name": f"Implement {nfr_name}",
                    "type": "nfr",
                    "description": nfr_description,  # Store the NFR description
                    "nfr_data": nfr,  # Store full NFR data for later use
                }
            )
        return tasks

    async def _create_infrastructure_tasks(
        self,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
        project_size: str = "medium",
    ) -> List[Dict[str, Any]]:
        """Create infrastructure and setup tasks"""
        tasks = []

        # Always include basic setup for all project sizes
        tasks.append(
            {
                "id": "infra_setup",
                "name": "Set up development environment",
                "type": "setup",
            }
        )

        # Add CI/CD for standard+ projects
        if project_size in ["standard", "medium", "large", "enterprise"]:
            tasks.append(
                {
                    "id": "infra_ci_cd",
                    "name": "Configure CI/CD pipeline",
                    "type": "infrastructure",
                }
            )

        # Add deployment infrastructure only for enterprise projects
        if project_size in ["enterprise", "large"]:
            tasks.append(
                {
                    "id": "infra_deploy",
                    "name": "Set up deployment infrastructure",
                    "type": "deployment",
                }
            )

        return tasks

    def _extract_task_info(
        self, task_id: str, epic_id: str, analysis: PRDAnalysis
    ) -> Dict[str, Any]:
        """Extract task information from analysis"""
        return {
            "id": task_id,
            "epic_id": epic_id,
            "type": "development",  # Default type
            "complexity": "medium",
        }

    async def _enhance_task_with_ai(
        self,
        task_info: Dict[str, Any],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> Dict[str, Any]:
        """Enhance task with PRD-aware details following board quality standards"""
        task_id = task_info.get("id", "unknown")
        epic_id = task_info.get("epic_id", "unknown")

        # Get original task metadata
        task_metadata = self._task_metadata.get(task_id, {})
        original_name = task_metadata.get("original_name", "")

        # Extract meaningful context from PRD analysis
        project_context = self._extract_project_context(analysis, task_id, epic_id)

        # Generate context-aware task details
        if "design" in task_id.lower():
            name, description = self._generate_design_task(
                project_context, task_id, original_name
            )
            task_type = "design"
            estimated_hours = 8
        elif "implement" in task_id.lower():
            name, description = self._generate_implementation_task(
                project_context, task_id, original_name
            )
            task_type = "implementation"
            estimated_hours = 16
        elif "test" in task_id.lower():
            name, description = self._generate_testing_task(
                project_context, task_id, original_name
            )
            task_type = "testing"
            estimated_hours = 8
        elif "setup" in task_id.lower() or "infra" in task_id.lower():
            name, description = self._generate_infrastructure_task(
                project_context, task_id, original_name
            )
            task_type = "setup"
            estimated_hours = 12
        else:
            name, description = self._generate_generic_task(
                project_context, task_id, original_name
            )
            task_type = "feature"
            estimated_hours = 12

        # Generate appropriate labels based on context and requirements
        labels = self._generate_labels(task_type, project_context, constraints)

        # Generate acceptance criteria based on task type
        acceptance_criteria = self._generate_acceptance_criteria(
            task_type, project_context, name
        )

        # Generate subtasks to break down the work
        subtasks = self._generate_subtasks(task_type, project_context, name)

        return {
            "name": name,
            "description": description,
            "estimated_hours": estimated_hours,
            "labels": labels,
            "due_date": None,
            "acceptance_criteria": acceptance_criteria,
            "subtasks": subtasks,
        }

    def _determine_priority(
        self, task_info: Dict[str, Any], analysis: PRDAnalysis
    ) -> Priority:
        """Determine task priority"""
        task_type = task_info.get("type", "development")

        if task_type in ["setup", "infrastructure"]:
            return Priority.HIGH
        elif task_type in ["design", "planning"]:
            return Priority.HIGH
        elif task_type in ["testing", "deployment"]:
            return Priority.MEDIUM
        else:
            return Priority.MEDIUM

    # Additional helper methods would continue to be implemented...
    async def _add_prd_specific_dependencies(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Add PRD-specific dependencies"""
        return []  # Simplified for now

    async def _analyze_complexity_risks(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Analyze complexity-related risks"""
        return [
            {
                "type": "technical_complexity",
                "description": "Complex integration requirements",
                "impact": "medium",
            }
        ]

    async def _analyze_constraint_risks(
        self, tasks: List[Task], constraints: ProjectConstraints
    ) -> List[Dict[str, Any]]:
        """Analyze constraint-related risks"""
        risks = []
        if constraints.deadline:
            total_effort = sum(task.estimated_hours or 8 for task in tasks)
            days_available = (constraints.deadline - datetime.now()).days
            if (
                total_effort > days_available * constraints.team_size * 6
            ):  # 6 hours per day
                risks.append(
                    {
                        "type": "timeline_pressure",
                        "description": "Insufficient time for planned work",
                        "impact": "high",
                    }
                )
        return risks

    async def _generate_mitigation_strategies(
        self, risks: List[Dict[str, Any]], tasks: List[Task], analysis: PRDAnalysis
    ) -> List[str]:
        """Generate risk mitigation strategies"""
        return [
            "Regular risk assessment reviews",
            "Maintain project buffer time",
            "Implement incremental delivery approach",
        ]

    async def _identify_critical_path_tasks(
        self, tasks: List[Task], dependencies: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify tasks on the critical path"""
        # Simplified - return setup and deployment tasks as critical
        return [
            task.id
            for task in tasks
            if any(label in ["setup", "deployment"] for label in task.labels)
        ]

    async def _calculate_milestone_dates(
        self, start_date: datetime, duration_days: float
    ) -> Dict[str, str]:
        """Calculate key milestone dates"""
        milestones = {}
        milestones["design_complete"] = (
            start_date + timedelta(days=duration_days * 0.25)
        ).isoformat()
        milestones["development_complete"] = (
            start_date + timedelta(days=duration_days * 0.75)
        ).isoformat()
        milestones["testing_complete"] = (
            start_date + timedelta(days=duration_days * 0.9)
        ).isoformat()
        return milestones

    async def _analyze_skill_requirements(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[str]:
        """Analyze required skills"""
        skills = set()
        for constraint in analysis.technical_constraints:
            if "react" in constraint.lower():
                skills.add("React")
            if "python" in constraint.lower():
                skills.add("Python")
            if "postgres" in constraint.lower():
                skills.add("PostgreSQL")
        return list(skills)

    async def _analyze_tech_requirements(
        self, analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> List[str]:
        """Analyze technology requirements"""
        return analysis.technical_constraints

    async def _analyze_external_dependencies(self, analysis: PRDAnalysis) -> List[str]:
        """Analyze external dependencies"""
        return ["Third-party API integrations", "External service providers"]

    def _calculate_optimal_team_size(
        self, tasks: List[Task], constraints: ProjectConstraints
    ) -> int:
        """Calculate optimal team size"""
        task_complexity = len(tasks)
        if task_complexity < 10:
            return min(2, constraints.team_size)
        elif task_complexity < 25:
            return min(4, constraints.team_size)
        else:
            return min(6, constraints.team_size)

    async def _identify_specialized_roles(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[str]:
        """Identify specialized roles needed"""
        roles = ["Full-stack Developer"]

        # Check for UI/UX needs
        if any("design" in task.name.lower() for task in tasks):
            roles.append("UI/UX Designer")

        # Check for DevOps needs
        if any(
            "deploy" in task.name.lower() or "infrastructure" in task.name.lower()
            for task in tasks
        ):
            roles.append("DevOps Engineer")

        return roles

    def _extract_project_context(
        self, analysis: PRDAnalysis, task_id: str, epic_id: str
    ) -> Dict[str, Any]:
        """Extract meaningful project context from PRD analysis"""
        context = {
            "business_objectives": (
                analysis.business_objectives[:3]
                if analysis.business_objectives
                else ["deliver working solution"]
            ),
            "technical_constraints": (
                analysis.technical_constraints[:3]
                if analysis.technical_constraints
                else ["standard web application"]
            ),
            "functional_requirements": (
                analysis.functional_requirements[:5]
                if analysis.functional_requirements
                else []
            ),
            "project_type": "web application",  # Default
            "domain": "general",
        }

        # First, check if this task is for a specific functional requirement
        task_specific_domain = None
        task_specific_type = None

        # Extract the feature from task_id (e.g., task_crud_operations_design -> crud_operations)
        if "task_" in task_id:
            parts = task_id.split("_")
            if len(parts) >= 3:
                feature_parts = parts[1:-1]  # Remove 'task' prefix and action suffix
                feature_id = "_".join(feature_parts)

                # Find the matching functional requirement
                for req in analysis.functional_requirements:
                    req_feature = req.get("feature", "").lower().replace(" ", "_")
                    if req_feature == feature_id:
                        # Determine domain based on this specific requirement
                        req_text = f"{req.get('feature', '')} {req.get('description', '')}".lower()

                        if any(
                            word in req_text
                            for word in ["crud", "create", "read", "update", "delete"]
                        ):
                            task_specific_domain = "crud_operations"
                            task_specific_type = "REST API"
                        elif any(
                            word in req_text
                            for word in ["auth", "login", "jwt", "token"]
                        ):
                            task_specific_domain = "user_management"
                            task_specific_type = "authentication system"
                        elif any(
                            word in req_text
                            for word in ["validation", "validate", "verify"]
                        ):
                            task_specific_domain = "validation"
                            task_specific_type = "input validation system"
                        elif any(
                            word in req_text
                            for word in ["property", "properties", "schema", "model"]
                        ):
                            task_specific_domain = "data_modeling"
                            task_specific_type = "data model"
                        break

        # Use task-specific domain if found, otherwise fall back to general analysis
        if task_specific_domain:
            context["domain"] = task_specific_domain
            context["project_type"] = task_specific_type
        else:
            # Determine general project type from overall requirements
            all_text = " ".join(
                [
                    " ".join(analysis.business_objectives),
                    " ".join(analysis.technical_constraints),
                    " ".join(
                        [
                            req.get("description", "")
                            for req in analysis.functional_requirements
                        ]
                    ),
                ]
            ).lower()

            # Use more specific matching to avoid false positives
            if any(word in all_text for word in ["api", "rest", "endpoint", "crud"]):
                context["domain"] = "backend_services"
                context["project_type"] = "REST API"
            elif any(
                word in all_text for word in ["ui", "interface", "frontend", "react"]
            ):
                context["domain"] = "frontend"
                context["project_type"] = "frontend application"
            elif any(word in all_text for word in ["data", "analytics", "report"]):
                context["domain"] = "data_analytics"
                context["project_type"] = "data analytics platform"
            elif any(
                word in all_text for word in ["ecommerce", "shop", "cart", "product"]
            ):
                context["domain"] = "ecommerce"
                context["project_type"] = "e-commerce platform"

        # Extract specific requirements that match this task/epic
        relevant_requirements = []
        for req in analysis.functional_requirements:
            req_text = req.get("description", "").lower()
            if (
                task_id.lower() in req_text
                or epic_id.lower() in req_text
                or any(keyword in req_text for keyword in task_id.lower().split("_"))
            ):
                relevant_requirements.append(req)

        context["relevant_requirements"] = relevant_requirements[
            :2
        ]  # Top 2 most relevant

        return context

    def _generate_design_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate design task name and description using PRD context"""
        domain = context["domain"]
        project_type = context["project_type"]
        objectives = context["business_objectives"]

        # Extract feature name from original name (e.g., "Design CRUD Operations" -> "CRUD Operations")
        feature_name = original_name.replace("Design ", "") if original_name else ""

        if domain == "crud_operations":
            # Use original feature name if available, otherwise use generic
            name = original_name if original_name else "Design CRUD API Architecture"
            description = f"Create architectural design and documentation for CRUD operations in {project_type}. Define API endpoints, document request/response formats, plan error handling strategies, and design pagination approach. Deliverables: API specification document, data flow diagrams, and architectural decisions. Goal: {objectives[0] if objectives else 'efficient data management'}."
        elif domain == "data_modeling":
            name = original_name if original_name else "Design Data Model and Schema"
            description = f"Design data architecture and create documentation for {project_type}. Research data requirements, create entity relationship diagrams, document field specifications and constraints. Plan migration strategy and define validation rules. Deliverables: ER diagrams, schema documentation, and data dictionary. Focus on: {objectives[0] if objectives else 'scalable data architecture'}."
        elif domain == "validation":
            name = original_name if original_name else "Design Input Validation System"
            description = f"Design validation strategy and create documentation for {project_type}. Research validation requirements, define validation rules and patterns, plan error handling approach. Document security considerations and sanitization procedures. Deliverables: validation specification document, error message catalog, and security guidelines. Goal: {objectives[0] if objectives else 'data integrity and security'}."
        elif domain == "user_management":
            name = original_name if original_name else "Design User Authentication Flow"
            description = f"Design authentication architecture and create documentation for {project_type}. Research security requirements, create user flow diagrams, document authentication patterns and session management approach. Plan security protocols and define user account lifecycle. Deliverables: authentication flow diagrams, security documentation, and API specifications. Goal: {objectives[0] if objectives else 'secure user access'}."
        elif domain == "frontend":
            name = (
                original_name if original_name else "Design User Interface Architecture"
            )
            description = f"Create detailed UI/UX design for {project_type}. Include component hierarchy, design system, responsive layouts, and user interaction patterns. Focus on achieving: {objectives[0] if objectives else 'excellent user experience'}. Define accessibility standards and usability requirements."
        elif domain == "backend_services":
            name = original_name if original_name else "Design API Architecture"
            description = f"Design API architecture for {project_type}. Research requirements, document API specifications, define endpoint patterns and data contracts. Create architectural diagrams and technical documentation. Deliverables: API documentation, architectural decisions, and interface specifications. Focus on: {objectives[0] if objectives else 'scalable API design'}."
        elif domain == "ecommerce":
            name = (
                original_name if original_name else "Design E-commerce User Experience"
            )
            description = f"Design comprehensive e-commerce user experience for {project_type}. Include product catalog, shopping cart, checkout flow, user accounts, and order management. Optimize for: {objectives[0] if objectives else 'seamless shopping experience'}."
        else:
            # For any other domain, use original name or create one from feature
            name = (
                original_name
                if original_name
                else f"Design {feature_name if feature_name else project_type.title()} Architecture"
            )
            description = f"Research and design architecture for {project_type}. Create documentation defining approach, patterns, and specifications. Plan component structure and integration points. Deliverables: design documentation, architectural diagrams, and technical specifications. Goal: {objectives[0] if objectives else 'effective solution delivery'}."

        # Add specific requirements if available
        if context["relevant_requirements"]:
            req = context["relevant_requirements"][0]
            description += (
                f" Specific requirement: {req.get('description', '')[:100]}..."
            )

        return name, description

    def _generate_implementation_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate implementation task name and description using PRD context"""
        domain = context["domain"]
        project_type = context["project_type"]
        tech_constraints = context["technical_constraints"]

        if domain == "user_management":
            name = (
                original_name
                if original_name
                else "Implement User Authentication Service"
            )
            description = f"Build secure user authentication service for {project_type}. Implement user registration, login, JWT token management, password hashing with bcrypt, and session handling. Technology stack: {', '.join(tech_constraints)}. Include rate limiting, email verification, and comprehensive error handling."
        elif domain == "frontend":
            name = original_name if original_name else "Build User Interface Components"
            description = f"Develop responsive UI components for {project_type}. Create reusable component library, implement state management, handle user interactions, and ensure accessibility compliance. Using: {', '.join(tech_constraints)}. Include loading states, error boundaries, and responsive design."
        elif domain == "backend_services":
            name = original_name if original_name else "Develop Backend API Services"
            objectives = context.get("business_objectives", [])
            description = f"Implement backend API services for {project_type} following the design specifications. Build endpoints, business logic, data validation, and error handling. Include appropriate tests and logging. Technology: {', '.join(tech_constraints)}. Goal: {objectives[0] if objectives else 'working implementation'}."
        elif domain == "ecommerce":
            name = original_name if original_name else "Build E-commerce Core Features"
            description = f"Implement core e-commerce functionality for {project_type}. Build product catalog, shopping cart, checkout process, payment integration, and order management. Stack: {', '.join(tech_constraints)}. Include inventory management and order tracking."
        elif domain == "crud_operations":
            name = original_name if original_name else "Implement CRUD API Endpoints"
            description = f"Build complete CRUD (Create, Read, Update, Delete) functionality for {project_type}. Implement RESTful endpoints with proper HTTP methods, request/response handling, data validation, and error responses. Technology: {', '.join(tech_constraints)}. Include pagination, filtering, and sorting capabilities."
        elif domain == "data_modeling":
            name = (
                original_name
                if original_name
                else "Implement Data Models and Database Layer"
            )
            description = f"Create data models and database integration for {project_type}. Define schemas, implement ORM/ODM models, set up migrations, add indexes for performance, and implement data validation. Stack: {', '.join(tech_constraints)}. Include relationships, constraints, and data integrity rules."
        elif domain == "validation":
            name = (
                original_name
                if original_name
                else "Implement Input Validation and Sanitization"
            )
            description = f"Build comprehensive validation layer for {project_type}. Implement input validation rules, data sanitization, type checking, business rule validation, and error message formatting. Technology: {', '.join(tech_constraints)}. Include XSS prevention, SQL injection protection, and data format validation."
        else:
            # Extract feature name from original name
            feature_name = (
                original_name.replace("Implement ", "") if original_name else ""
            )
            name = (
                original_name
                if original_name
                else f"Implement {feature_name if feature_name else project_type.title()} Core Features"
            )
            description = f"Build core functionality for {project_type}. Implement business logic, data processing, user interfaces, and system integrations. Using: {', '.join(tech_constraints)}. Include proper error handling, logging, and performance optimization."

        # Add specific requirements if available
        if context["relevant_requirements"]:
            req = context["relevant_requirements"][0]
            description += (
                f" Addresses requirement: {req.get('description', '')[:100]}..."
            )

        return name, description

    def _generate_testing_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate testing task name and description using PRD context"""
        domain = context["domain"]
        project_type = context["project_type"]

        if domain == "user_management":
            name = (
                original_name
                if original_name
                else "Test Authentication Security Features"
            )
            description = f"Create comprehensive test suite for user authentication in {project_type}. Include unit tests for login/registration, integration tests for JWT flows, security testing for password policies, and end-to-end user journey tests. Achieve >80% code coverage."
        elif domain == "frontend":
            name = original_name if original_name else "Test User Interface Components"
            description = f"Develop UI testing suite for {project_type}. Include component unit tests, user interaction tests, accessibility testing, responsive design validation, and cross-browser compatibility tests. Test all user flows and error states."
        elif domain == "backend_services":
            name = (
                original_name
                if original_name
                else "Test API Functionality and Performance"
            )
            description = f"Create API testing suite for {project_type}. Include endpoint unit tests, integration tests, load testing, security testing, and error handling validation. Test data validation, authentication, and business logic. Achieve >80% coverage."
        elif domain == "ecommerce":
            name = (
                original_name if original_name else "Test E-commerce Transaction Flows"
            )
            description = f"Develop comprehensive testing for {project_type}. Test shopping cart functionality, checkout process, payment integration, order management, and inventory updates. Include security testing for payment processing and fraud prevention."
        elif domain == "crud_operations":
            name = (
                original_name
                if original_name
                else "Test CRUD Operations and API Endpoints"
            )
            description = f"Create comprehensive test suite for CRUD operations in {project_type}. Test all HTTP methods (GET, POST, PUT, DELETE), validate request/response formats, test error handling, pagination, filtering, and edge cases. Include load testing for concurrent operations. Achieve >80% coverage."
        elif domain == "data_modeling":
            name = (
                original_name
                if original_name
                else "Test Data Models and Database Operations"
            )
            description = f"Develop database testing suite for {project_type}. Test model validations, database constraints, migrations, relationships, data integrity, and transaction handling. Include performance testing for queries and indexes. Validate data consistency and error scenarios."
        elif domain == "validation":
            name = (
                original_name if original_name else "Test Input Validation and Security"
            )
            description = f"Create validation testing suite for {project_type}. Test all validation rules, boundary conditions, invalid inputs, injection attempts, XSS prevention, and error message accuracy. Include fuzz testing and security vulnerability scanning. Ensure comprehensive input sanitization coverage."
        else:
            # Extract feature name from original name
            feature_name = original_name.replace("Test ", "") if original_name else ""
            name = (
                original_name
                if original_name
                else f"Test {feature_name if feature_name else project_type.title()} Functionality"
            )
            description = f"Create comprehensive test suite for {project_type}. Include unit tests, integration tests, and end-to-end testing. Validate business logic, user workflows, and system reliability. Achieve >80% code coverage."

        return name, description

    def _generate_infrastructure_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate infrastructure task name and description using PRD context"""
        project_type = context["project_type"]
        tech_constraints = context["technical_constraints"]

        if "setup" in task_id.lower():
            name = original_name if original_name else "Setup Development Environment"
            description = f"Configure complete development environment for {project_type}. Set up local development stack, database, environment variables, development tools, and project dependencies. Technology: {', '.join(tech_constraints)}. Include Docker containers, hot reloading, and debugging tools."
        elif "ci" in task_id.lower() or "cd" in task_id.lower():
            name = original_name if original_name else "Configure CI/CD Pipeline"
            description = f"Set up continuous integration and deployment for {project_type}. Configure automated testing, code quality checks, building, and deployment to staging/production. Using: {', '.join(tech_constraints)}. Include security scanning and performance monitoring."
        elif "deploy" in task_id.lower():
            name = original_name if original_name else "Setup Production Deployment"
            description = f"Configure production infrastructure for {project_type}. Set up hosting, load balancing, monitoring, logging, backup systems, and security measures. Technology: {', '.join(tech_constraints)}. Include scaling strategy and disaster recovery."
        else:
            name = original_name if original_name else "Configure System Infrastructure"
            description = f"Set up core infrastructure for {project_type}. Configure servers, databases, caching, monitoring, and security systems. Stack: {', '.join(tech_constraints)}. Include performance optimization and maintenance procedures."

        return name, description

    def _generate_generic_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate generic task name and description using PRD context"""
        project_type = context["project_type"]
        objectives = context["business_objectives"]

        # Try to infer from task_id what this might be about
        if "nfr" in task_id.lower():
            # Use original_name if available to preserve unique NFR names
            if original_name and original_name != "":
                name = original_name
            else:
                # Extract NFR type from task_id if possible (e.g., nfr_task_performance)
                nfr_type = task_id.replace("nfr_task_", "").replace("_", " ").title()
                if nfr_type and nfr_type != task_id:
                    name = f"Implement {nfr_type} Requirements"
                else:
                    name = "Implement Non-Functional Requirements"
            # Use the stored NFR description if available
            task_metadata = self._task_metadata.get(task_id, {})
            stored_description = task_metadata.get("description", "")
            if stored_description:
                description = stored_description
            else:
                # Fallback to generic description
                description = f"Address performance, security, and scalability requirements for {project_type}. Implement caching, optimize database queries, add security headers, and ensure system reliability. Target: {objectives[0] if objectives else 'system performance'}."
        elif any(keyword in task_id.lower() for keyword in ["req_0", "req_1", "req_2"]):
            req_index = next(
                (
                    i
                    for i, keyword in enumerate(["req_0", "req_1", "req_2"])
                    if keyword in task_id.lower()
                ),
                0,
            )
            if req_index < len(context["functional_requirements"]):
                req = context["functional_requirements"][req_index]
                req_desc = req.get("description", "feature requirement")
                name = f"Implement {req_desc[:30]}..."
                description = f"Complete implementation of: {req_desc}. For {project_type} to achieve: {objectives[0] if objectives else 'project goals'}."
            else:
                name = f"Implement Core {project_type.title()} Feature"
                description = f"Build essential functionality for {project_type}. Implement core business logic, user interactions, and system integrations to achieve: {objectives[0] if objectives else 'project success'}."
        else:
            name = f"Develop {project_type.title()} Component"
            description = f"Build and integrate component for {project_type}. Implement required functionality, ensure proper testing, and maintain code quality standards. Supports: {objectives[0] if objectives else 'project objectives'}."

        return name, description

    def _generate_labels(
        self, task_type: str, context: Dict[str, Any], constraints: ProjectConstraints
    ) -> List[str]:
        """Generate appropriate labels following Board Quality Standards taxonomy"""
        labels = []

        # Component labels
        domain = context["domain"]
        if domain == "user_management":
            labels.append("component:authentication")
        elif domain == "frontend":
            labels.append("component:frontend")
        elif domain == "backend_services":
            labels.append("component:backend")
        elif domain == "ecommerce":
            labels.append("component:ecommerce")
        else:
            # For REST API projects, use API label
            project_type = context.get("project_type", "").lower()
            if "api" in project_type or "rest" in project_type:
                labels.append("component:api")
            else:
                labels.append("component:backend")  # Default

        # Type labels
        if task_type == "design":
            labels.append("type:design")
        elif task_type == "implementation":
            labels.append("type:feature")
        elif task_type == "testing":
            labels.append("type:testing")
        elif task_type == "setup":
            labels.append("type:setup")
        else:
            labels.append("type:feature")

        # Priority labels (default to medium)
        labels.append("priority:medium")

        # Skill labels based on constraints
        if constraints.available_skills:
            for skill in constraints.available_skills[:1]:  # Take first skill
                if skill.lower() in ["react", "vue", "angular"]:
                    labels.append("skill:frontend")
                    break
                elif skill.lower() in ["node.js", "nodejs", "python", "java"]:
                    labels.append("skill:backend")
                    break
                elif skill.lower() in ["docker", "kubernetes", "aws"]:
                    labels.append("skill:devops")
                    break
                else:
                    labels.append(f"skill:{skill.lower()}")
                    break
        else:
            labels.append("skill:fullstack")

        # Complexity labels
        if task_type in ["design", "setup"]:
            labels.append("complexity:moderate")
        elif task_type == "testing":
            labels.append("complexity:simple")
        else:
            labels.append("complexity:moderate")

        return labels

    def _generate_acceptance_criteria(
        self, task_type: str, context: Dict[str, Any], task_name: str
    ) -> List[str]:
        """Generate acceptance criteria based on task type and context"""
        criteria = []

        if task_type == "design":
            criteria = [
                "Design documentation is complete with all components specified",
                "User flows and wireframes are created and reviewed",
                "Technical architecture is documented and approved",
                "Design system components are defined",
                "Accessibility requirements are documented",
            ]
        elif task_type == "implementation":
            criteria = [
                "All functionality is implemented as per specifications",
                "Code passes all unit tests with >80% coverage",
                "Code follows project coding standards and conventions",
                "API endpoints are documented and tested",
                "Error handling and validation are implemented",
                "Performance meets defined benchmarks",
            ]
        elif task_type == "testing":
            criteria = [
                "All test cases are written and documented",
                "Unit tests achieve >80% code coverage",
                "Integration tests cover all API endpoints",
                "End-to-end tests validate user workflows",
                "Performance tests meet SLA requirements",
                "Test results are documented and reviewed",
            ]
        elif task_type == "setup":
            criteria = [
                "Development environment runs successfully",
                "All dependencies are installed and documented",
                "Configuration files are properly set up",
                "Database migrations run without errors",
                "README includes setup instructions",
                "Team members can successfully run the project",
            ]
        elif task_type == "deployment":
            criteria = [
                "Application deploys successfully to target environment",
                "All environment variables are configured",
                "Health checks pass in production",
                "Monitoring and logging are operational",
                "Rollback procedure is documented and tested",
                "Performance meets production requirements",
            ]
        else:
            # Generic criteria for feature tasks
            criteria = [
                f"{task_name} is fully implemented and functional",
                "Feature works as specified in requirements",
                "Code is tested and passes all tests",
                "Documentation is updated",
                "Code review is completed and approved",
            ]

        # Add context-specific criteria
        if context.get("domain") == "user_management":
            criteria.append(
                "Security requirements are met (authentication, authorization)"
            )
            criteria.append("User data privacy is properly handled")
        elif context.get("domain") == "ecommerce":
            criteria.append("Payment processing is secure and PCI compliant")
            criteria.append("Order workflow is thoroughly tested")

        return criteria[:5]  # Return top 5 most relevant criteria

    def _generate_subtasks(
        self, task_type: str, context: Dict[str, Any], task_name: str
    ) -> List[str]:
        """Generate subtasks to break down the work"""
        subtasks = []

        if task_type == "design":
            subtasks = [
                "Research existing solutions and best practices",
                "Create initial wireframes and mockups",
                "Design component hierarchy and data flow",
                "Document API contracts and interfaces",
                "Create design system tokens and components",
                "Review design with stakeholders",
            ]
        elif task_type == "implementation":
            # Parse the task name to understand what we're implementing
            if "authentication" in task_name.lower():
                subtasks = [
                    "Set up authentication middleware",
                    "Implement user registration endpoint",
                    "Create login/logout functionality",
                    "Add password reset flow",
                    "Implement JWT token management",
                    "Add session management",
                    "Create user profile endpoints",
                ]
            elif "database" in task_name.lower():
                subtasks = [
                    "Design database schema",
                    "Create migration scripts",
                    "Set up database connections",
                    "Implement data models",
                    "Add database indexes",
                    "Create seed data scripts",
                ]
            elif "api" in task_name.lower():
                subtasks = [
                    "Define API endpoints and routes",
                    "Implement request validation",
                    "Create response serializers",
                    "Add error handling middleware",
                    "Implement rate limiting",
                    "Add API documentation",
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
                    "Add integration tests",
                ]
        elif task_type == "testing":
            subtasks = [
                "Write unit test specifications",
                "Implement unit tests for models",
                "Create integration test suite",
                "Add API endpoint tests",
                "Write end-to-end test scenarios",
                "Set up test data fixtures",
                "Configure test automation",
            ]
        elif task_type == "setup":
            subtasks = [
                "Initialize project repository",
                "Set up development dependencies",
                "Configure build tools",
                "Create environment configuration",
                "Set up database connections",
                "Configure linting and formatting",
                "Create development scripts",
            ]
        elif task_type == "deployment":
            subtasks = [
                "Create deployment configuration",
                "Set up CI/CD pipeline",
                "Configure environment variables",
                "Set up monitoring and alerts",
                "Create deployment scripts",
                "Configure load balancing",
                "Set up backup procedures",
            ]
        else:
            # Generic feature subtasks
            subtasks = [
                f"Plan {task_name} implementation",
                "Implement core functionality",
                "Add data persistence layer",
                "Create user interface components",
                "Write tests",
                "Update documentation",
            ]

        # Customize based on context
        if context.get("tech_stack"):
            tech = context["tech_stack"]
            if "React" in tech and task_type == "implementation":
                subtasks.extend(
                    [
                        "Create React components",
                        "Set up component state management",
                        "Add component styling",
                    ]
                )
            elif "Django" in tech and task_type == "implementation":
                subtasks.extend(
                    [
                        "Create Django models",
                        "Add Django views and serializers",
                        "Configure Django admin",
                    ]
                )

        return subtasks[:7]  # Return top 7 most relevant subtasks

    def _should_skip_epic(self, epic_id: str, deployment_target: str) -> bool:
        """Determine if an epic should be skipped based on deployment target"""

        # Skip deployment and production epics for local development
        if deployment_target == "local":
            skip_keywords = [
                "deployment",
                "production",
                "deploy",
                "release",
                "hosting",
                "infrastructure",
            ]
            return any(keyword in epic_id.lower() for keyword in skip_keywords)

        # Skip advanced deployment features for dev environment
        elif deployment_target == "dev":
            skip_keywords = [
                "production",
                "scaling",
                "monitoring",
                "optimization",
                "disaster_recovery",
            ]
            return any(keyword in epic_id.lower() for keyword in skip_keywords)

        # Include everything for prod and remote
        return False

    def _should_skip_task(
        self, task_id: str, epic_id: str, deployment_target: str
    ) -> bool:
        """Determine if a task should be skipped based on deployment target"""
        task_lower = task_id.lower()

        # Skip deployment tasks for local development
        if deployment_target == "local":
            skip_keywords = [
                "deploy",
                "production",
                "hosting",
                "server",
                "cloud",
                "aws",
                "azure",
                "gcp",
                "kubernetes",
                "docker",
                "container",
                "load_balancer",
                "cdn",
                "ssl",
                "domain",
                "dns",
            ]
            return any(keyword in task_lower for keyword in skip_keywords)

        # Skip production-specific tasks for dev environment
        elif deployment_target == "dev":
            skip_keywords = [
                "production",
                "prod_",
                "scaling",
                "auto_scale",
                "load_balancer",
                "disaster_recovery",
                "backup",
                "monitoring",
                "alerting",
                "performance_optimization",
                "cdn",
                "multi_region",
            ]
            return any(keyword in task_lower for keyword in skip_keywords)

        # Include everything for prod and remote
        return False

    def _filter_requirements_by_size(
        self, requirements: List[Dict[str, Any]], project_size: str, team_size: int
    ) -> List[Dict[str, Any]]:
        """Filter functional requirements based on project size and team capacity"""
        # Map to new 3-option system (with legacy support)
        if project_size in ["prototype", "mvp"]:
            # Prototype: only keep the most essential 1-2 requirements
            return requirements[:2]
        elif project_size in ["standard", "small", "medium"]:
            # Standard: limit based on team size (typically 3-5 features)
            max_reqs = min(len(requirements), max(3, team_size))
            return requirements[:max_reqs]
        else:
            # Enterprise/Large: include all requirements
            return requirements

    def _filter_nfrs_by_size(self, nfrs: List[Dict[str, Any]], project_size: str) -> List[Dict[str, Any]]:
        """Filter non-functional requirements based on project size"""
        if project_size in ["prototype", "mvp", "small"]:
            # Prototype: Skip NFRs entirely or just basic auth
            essential_nfrs = []
            for nfr in nfrs:
                nfr_type = nfr.get("type", "").lower()
                if "auth" in nfr_type:
                    essential_nfrs.append(nfr)
            return essential_nfrs[:1]  # Maximum 1 NFR for prototypes
        elif project_size in ["standard", "medium"]:
            # Standard: Keep 2-3 most important NFRs (security, performance)
            return nfrs[:2]
        else:
            # Enterprise: include all NFRs
            return nfrs
