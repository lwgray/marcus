"""
Advanced PRD Parser for Marcus Phase 4.

Transform natural language requirements into actionable tasks with
deep understanding, intelligent task breakdown, and risk assessment.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.ai.providers.llm_abstraction import LLMAbstraction
from src.config.hybrid_inference_config import HybridInferenceConfig
from src.core.models import Priority, Task, TaskStatus
from src.integrations.ai_analysis_engine import AIAnalysisEngine
from src.intelligence.dependency_inferer_hybrid import HybridDependencyInferer
from src.visualization.shared_pipeline_events import PipelineStage

logger = logging.getLogger(__name__)


@dataclass
class PRDAnalysis:
    """Deep analysis of a PRD document."""

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
    original_description: str = ""  # NEW: Preserve original user description


@dataclass
class TaskGenerationResult:
    """Result of PRD-to-tasks conversion."""

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
    """Constraints for task generation."""

    deadline: Optional[datetime] = None
    budget_limit: Optional[float] = None
    team_size: int = 3
    available_skills: Optional[List[str]] = None
    technology_constraints: Optional[List[str]] = None
    quality_requirements: Optional[Dict[str, Any]] = None
    deployment_target: str = "local"  # local, dev, prod, remote
    complexity_mode: str = "standard"  # prototype, standard, enterprise

    def __post_init__(self) -> None:
        """Initialize post-creation."""
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
    Advanced PRD parser that converts natural language requirements.

    Converts requirements into complete task breakdown with intelligent
    dependencies and risk assessment.
    """

    def __init__(
        self,
        hybrid_config: Optional[HybridInferenceConfig] = None,
        memory: Optional[Any] = None,
    ):
        self.llm_client = LLMAbstraction()
        self.memory = memory  # Store memory system for learning durations

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

        # Task pattern constants
        self.TASK_TYPE_DESIGN = "design"
        self.TASK_TYPE_IMPLEMENTATION = "implementation"
        self.TASK_TYPE_TESTING = "testing"

        # Complexity mode constants
        self.VALID_COMPLEXITY_MODES = ["prototype", "standard", "enterprise"]
        self.VALID_COMPLEXITIES = ["atomic", "simple", "coordinated", "distributed"]

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

    def _get_learned_task_duration(
        self, task_type: str, default_minutes: float = 6.0
    ) -> float:
        """
        Get median task duration from historical data.

        Uses memory system to query learned median completion times.
        Falls back to default if no historical data available.

        Parameters
        ----------
        task_type : str
            Task type: "design", "implement", "test", etc.
        default_minutes : float
            Default duration in minutes if no learned data available

        Returns
        -------
        float
            Estimated duration in minutes
        """
        try:
            if self.memory:
                # Query memory system for median duration
                median_hours = self.memory.get_median_duration_by_type(task_type)
                if median_hours is not None:
                    # Convert hours to minutes
                    learned_minutes: float = float(median_hours) * 60
                    logger.info(
                        f"Using learned duration for {task_type}: "
                        f"{learned_minutes:.1f} minutes "
                        f"(from {median_hours:.3f} hours)"
                    )
                    return learned_minutes
                else:
                    logger.debug(
                        f"No learned duration for {task_type}, "
                        f"using default: {default_minutes} minutes"
                    )
        except Exception as e:
            logger.warning(
                f"Failed to get learned duration for {task_type}: {e}. "
                f"Using default: {default_minutes} minutes"
            )

        # Fallback to default
        return default_minutes

    async def parse_prd_to_tasks(
        self, prd_content: str, constraints: ProjectConstraints
    ) -> TaskGenerationResult:
        """
        Convert PRD into complete task breakdown with dependencies.

        Args
        ----
            prd_content: Full PRD document content
            constraints: Project constraints and limitations

        Returns
        -------
            Complete task generation result with breakdown and analysis
        """
        logger.info("Starting advanced PRD parsing and task generation")

        # Step 1: Deep PRD analysis
        prd_analysis = await self._analyze_prd_deeply(prd_content)

        # Step 2: Generate task hierarchy
        req_count = len(prd_analysis.functional_requirements)
        logger.info(f"PRD analysis found {req_count} functional requirements")
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
        """Perform deep analysis of PRD using AI."""
        # nosec B608: This is an AI prompt template, not SQL
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
                    "priority": "high|medium|low",
                    "complexity": "atomic|simple|coordinated|distributed",
                    "requires_design_artifacts": true|false,
                    "affected_components": ["component1", "component2"]
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

        CRITICAL RULES:
        - RESPECT EXPLICIT EXCLUSIONS: If the description says
          "Do not include X" or "Do not add Y", you MUST NOT create
          requirements for those items
        - ONLY include features and requirements explicitly mentioned
          or clearly implied
        - Do NOT add "best practices" features that were explicitly
          excluded
        - For functionalRequirements, use "id", "name", "description",
          "priority", "complexity", "requires_design_artifacts", and
          "affected_components" fields
        - For nonFunctionalRequirements, use "id", "name", "description",
          and "category" fields
        - Generate meaningful IDs based on the feature name
          (e.g., "crud_operations", "user_auth")
        - Focus on extracting actionable, specific requirements that can
          be converted into development tasks

        UNIQUENESS AND DEDUPLICATION:
        - ENSURE UNIQUENESS: Each functional requirement must represent a
          DISTINCT feature
          * Check that no two requirements describe the same functionality
          * Consolidate overlapping features (e.g., "User Auth" +
            "Login System" → "User Authentication")
          * IDs must be unique - never reuse an ID or create similar IDs
            for related features
          * If a feature appears in multiple contexts (e.g., auth for
            profiles and auth for messaging), create ONE requirement with
            both contexts listed in affected_components

        - AVOID OVER-DECOMPOSITION: Keep requirements at consistent
          granularity level
          * Don't split "User Authentication" into separate requirements
            for Login, Registration, Password Reset
          * These should be ONE requirement that will be broken into
            parallelizable subtasks during implementation
          * Parallelization happens at the subtask level, not the
            requirement level
          * Implementation details belong in the description, not as
            separate requirements

        - CROSS-CHECK FEATURE GROUPS: Before finalizing, verify no
          duplicate features exist across groups
          * Example: If both "User Profiles" and "Messaging" groups
            mention authentication, create a single "User Authentication"
            requirement with affected_components: ["user-profiles",
            "messaging"]
          * Same applies for other cross-cutting concerns like logging,
            validation, error handling

        COMPLEXITY CLASSIFICATION:
        - "atomic": Single file changes (e.g., set background color, update text)
        - "simple": One component feature (e.g., score display, button handler)
        - "coordinated": Multi-component feature requiring coordination
          (e.g., user auth with API + UI + DB, full CRUD operations)
        - "distributed": Multi-service architecture
          (e.g., microservices, separate auth/user/order services)

        DESIGN ARTIFACTS NEEDED:
        - Set "requires_design_artifacts" to true if the feature needs
          interface contracts, API specs, or data schemas for coordination
        - Set to false for atomic or simple features that don't need
          design documentation

        AFFECTED COMPONENTS:
        - List all components touched by this feature
        - Examples: ["frontend"], ["api", "database"], ["auth-service", "user-service"]
        - Use specific names like "api", "database", "frontend", "auth-service"

        TECHNICAL CONSTRAINTS:
        - Extract ALL technology constraints from the description
        - Include explicit constraints: "use X", "vanilla JS", "PostgreSQL"
        - Include exclusions: "no frameworks", "don't use React", "avoid ORM"
        - Convert to lowercase with hyphens: "vanilla-js", "no-react", "postgresql"

        EXCLUSION EXAMPLES:
        - If description says "Do not include API Security", return
          empty nonFunctionalRequirements array or omit security NFRs
        - If description says "Do not include API Response Time", do
          not add performance monitoring
        - If description says "just a simple X", do not add enterprise
          features
        """
        try:
            # Use AI to analyze PRD
            # Create a simple context object that has max_tokens
            class SimpleContext:
                def __init__(self, max_tokens: int) -> None:
                    self.max_tokens = max_tokens

            # Increase max_tokens to handle complex PRDs with many requirements
            # 2000 tokens is too small - causes JSON truncation for 15+ features
            # Task Management (18 features) and Restaurant Booking (17 features)
            # need ~4000 tokens for complete JSON response
            # Note: Claude Haiku max_tokens limit is 4096
            context = SimpleContext(max_tokens=4096)

            logger.info("Attempting to use LLM for PRD analysis...")

            # Track AI analysis start
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

            result_len = len(analysis_result) if analysis_result else 0
            logger.info(f"LLM response received: {result_len} chars")

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
                            "details": (
                                "AI returned malformed JSON response. "
                                "This indicates an issue with the AI "
                                "provider configuration or the response "
                                "format. Please check your AI provider "
                                "settings and try again with a clearer "
                                "project description."
                            ),
                        },
                    ),
                )

            # Handle both snake_case and camelCase keys from AI response
            def get_key(
                data: Dict[str, Any], snake_key: str, camel_key: Optional[str] = None
            ) -> Any:
                """Get value from dict using either snake_case or camelCase key."""
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
                        f"AI used snake_case '{snake_key}' instead of "
                        f"expected camelCase '{camel_key}'"
                    )
                    return data[snake_key]
                else:
                    return []  # Return empty list as default

            # Extract functional requirements and deduplicate
            functional_reqs = get_key(
                analysis_data, "functional_requirements", "functionalRequirements"
            )
            # Apply deduplication to prevent duplicate tasks
            functional_reqs = self._deduplicate_functional_requirements(functional_reqs)

            return PRDAnalysis(
                functional_requirements=functional_reqs,
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
                # Note: template uses 'implementationApproach',
                # but old responses might use 'recommendedImplementation'
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
                original_description=prd_content,  # NEW: Preserve original description
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
                            ("Check AI provider API credentials and " "configuration"),
                            "Verify network connectivity to AI provider",
                            "Try simplifying the project description",
                            "Check AI provider service status",
                            (
                                "Ensure project description is in English "
                                "and well-structured"
                            ),
                        ],
                        "details": (
                            f"AI analysis of project requirements failed. "
                            f"This prevents automatic task generation from "
                            f"your project description. "
                            f"The AI provider "
                            f"({self.llm_client.__class__.__name__}) "
                            f"encountered an error: {str(e)}. "
                            f"Please check your AI configuration and try "
                            f"again. If the problem persists, contact "
                            f"support with this error context."
                        ),
                    },
                ),
            )

            # Record for monitoring and raise the error
            record_error_for_monitoring(ai_error)
            logger.error(f"PRD analysis failed: {ai_error}")

            # Raise the error instead of falling back to simulation
            raise ai_error

    async def _discover_domains(
        self, functional_requirements: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Use AI to discover natural domain groupings from functional requirements.

        Parameters
        ----------
        functional_requirements : List[Dict[str, Any]]
            List of functional requirements with id, name, description, etc.

        Returns
        -------
        Dict[str, List[str]]
            Mapping of domain_name -> [feature_ids]
            Example: {"User Management": ["user_reg", "user_login"],
                     "Todo Management": ["todo_create", "todo_list"]}
        """
        if not functional_requirements:
            return {}

        # Build feature list for AI prompt
        feature_list = []
        for idx, req in enumerate(functional_requirements, 1):
            feature_id = req.get("id", f"feature_{idx}")
            feature_name = req.get("name", "Unknown Feature")
            description = req.get("description", "")
            affected_components = req.get("affected_components", [])
            complexity = req.get("complexity", "simple")

            feature_list.append(
                f"{idx}. {feature_name} (ID: {feature_id})\n"
                f"   Description: {description}\n"
                f"   Components: {', '.join(affected_components)}\n"
                f"   Complexity: {complexity}"
            )

        features_text = "\n\n".join(feature_list)

        # Determine target number of domains based on project size
        num_features = len(functional_requirements)
        if num_features <= 5:
            target_domains = "2-3"
        elif num_features <= 15:
            target_domains = "3-5"
        elif num_features <= 30:
            target_domains = "4-7"
        else:
            target_domains = "6-10"

        prompt = f"""Analyze these features and group them into logical domains.

Each domain should represent a cohesive area of functionality that requires
coordination and shared design artifacts (API contracts, data models, etc.).

Consider:
- Shared data models (features touching same entities)
- Integration points (features that communicate)
- Common components (UI, backend services, databases)
- Semantic similarity (related business functionality)

Features:
{features_text}

Return JSON with {target_domains} domains (adaptive to project size):
{{
  "domains": [
    {{
      "name": "Descriptive Domain Name",
      "feature_ids": ["feature_id1", "feature_id2"],
      "rationale": "Why these features belong together (1 sentence)"
    }}
  ]
}}

IMPORTANT:
- Use the exact feature IDs from above
- Every feature MUST be assigned to exactly one domain
- Domain names should be descriptive (e.g., "User Management System",
  "Product Catalog", "Payment Processing")
- Group by COORDINATION NEEDS, not just technical similarity

Provide ONLY valid JSON, no preamble."""

        try:
            # Create context for AI call
            class SimpleContext:
                def __init__(self, max_tokens: int) -> None:
                    self.max_tokens = max_tokens

            context = SimpleContext(max_tokens=500)

            # Use LLM to discover domains
            result = await self.llm_client.analyze(prompt, context)
            response_text = str(result) if result else "{}"

            # Parse JSON response
            import json

            domain_data = json.loads(response_text)
            domains_list = domain_data.get("domains", [])

            # Convert to simple dict mapping
            domains = {}
            for domain in domains_list:
                domain_name = domain.get("name", "Unknown Domain")
                feature_ids = domain.get("feature_ids", [])
                rationale = domain.get("rationale", "")

                domains[domain_name] = feature_ids
                logger.info(
                    f"Discovered domain '{domain_name}' with {len(feature_ids)} "
                    f"features: {rationale}"
                )

            # Validate: Ensure all features are assigned
            assigned_features = set()
            for feature_ids in domains.values():
                assigned_features.update(feature_ids)

            all_feature_ids = {
                req.get("id", f"feature_{i+1}")
                for i, req in enumerate(functional_requirements)
            }
            unassigned = all_feature_ids - assigned_features

            if unassigned:
                logger.warning(
                    f"AI did not assign {len(unassigned)} features to domains: "
                    f"{unassigned}. Creating 'Other' domain."
                )
                domains["Other"] = list(unassigned)

            # Additional validation: Check for semantically similar feature names
            # This helps detect potential duplicates that passed through deduplication
            feature_names = [
                (req.get("id"), req.get("name")) for req in functional_requirements
            ]

            normalized_names: Dict[str, Tuple[str, str]] = {}
            for fid, fname in feature_names:
                if not fname or not fid:
                    continue
                # Type narrowing: fid and fname are guaranteed to be str here
                fid_str: str = fid
                fname_str: str = fname
                normalized = fname_str.lower().strip()
                # Normalize variations
                normalized = normalized.replace("authentication", "auth")
                normalized = normalized.replace("authorization", "auth")
                normalized = normalized.replace(" system", "")
                normalized = normalized.replace(" feature", "")
                normalized = normalized.replace(" component", "")
                normalized = normalized.replace(" service", "")
                normalized = normalized.replace("management", "mgmt")

                if normalized in normalized_names:
                    logger.warning(
                        f"Potential duplicate features detected: "
                        f"'{fname_str}' (ID: {fid_str}) and "
                        f"'{normalized_names[normalized][1]}' "
                        f"(ID: {normalized_names[normalized][0]}) "
                        f"have similar normalized names: '{normalized}'. "
                        f"Consider consolidating these features."
                    )
                else:
                    normalized_names[normalized] = (fid_str, fname_str)

            return domains

        except Exception as e:
            logger.warning(
                f"Domain discovery failed: {e}. Falling back to single domain."
            )
            # Fallback: Create single domain with all features
            all_ids = [
                req.get("id", f"feature_{i+1}")
                for i, req in enumerate(functional_requirements)
            ]
            return {"Project Domain": all_ids}

    async def _create_bundled_design_tasks(
        self,
        domains: Dict[str, List[str]],
        functional_requirements: List[Dict[str, Any]],
        complexity_mode: str,
    ) -> List[Dict[str, Any]]:
        """
        Create bundled design tasks, one per domain.

        Parameters
        ----------
        domains : Dict[str, List[str]]
            Mapping of domain_name -> [feature_ids]
        functional_requirements : List[Dict[str, Any]]
            All functional requirements
        complexity_mode : str
            Project complexity mode: "prototype", "standard", or "enterprise"

        Returns
        -------
        List[Dict[str, Any]]
            List of bundled design tasks
        """
        bundled_design_tasks = []

        # Create a lookup map for requirements
        req_map = {req.get("id"): req for req in functional_requirements}

        for domain_name, feature_ids in domains.items():
            # Get all requirements for this domain (filter out None values)
            domain_reqs = [req_map[fid] for fid in feature_ids if fid in req_map]

            if not domain_reqs:
                continue

            # Build detailed description including all features in this domain
            feature_descriptions = []
            for idx, req in enumerate(domain_reqs, 1):
                feature_name = req.get("name", "Unknown Feature")
                description = req.get("description", "")

                feature_descriptions.append(
                    f"{idx}. {feature_name.upper()}\n" f"   {description}"
                )

            features_text = "\n\n".join(feature_descriptions)

            # Create task description
            task_description = f"""Design the architecture for the {domain_name} \
which encompasses the following features:

{features_text}

Your design should define:
- Component boundaries (what components exist and their responsibilities)
- Data flows (how data moves between components)
- Integration points (how components communicate)
- Shared data models (schemas, entities, etc.)

Agents implementing these features will use get_task_context() to see your design
artifacts and log_artifact() to document their specific implementation choices
(exact API paths, field names, technologies, etc.)."""

            # Create bundled design task
            task_id = f"design_{domain_name.lower().replace(' ', '_')}"

            bundled_design_tasks.append(
                {
                    "id": task_id,
                    "name": f"Design {domain_name}",
                    "description": task_description,
                    "type": self.TASK_TYPE_DESIGN,
                    "domain_name": domain_name,
                    "feature_ids": feature_ids,  # Track which features this covers
                    "priority": "high",  # Design tasks should run first
                    "estimated_hours": self._get_learned_task_duration(
                        "design", default_minutes=6.0 * len(domain_reqs)
                    )
                    / 60.0,  # Scale with number of features
                    "labels": ["design", "architecture", domain_name.lower()],
                }
            )

            logger.info(
                f"Created bundled design task '{task_id}' for domain "
                f"'{domain_name}' covering {len(feature_ids)} features"
            )

        return bundled_design_tasks

    async def _generate_task_hierarchy(
        self, analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> Dict[str, List[str]]:
        """Generate hierarchical task structure."""
        hierarchy: Dict[str, List[str]] = {}

        # Store task metadata for later use
        self._task_metadata = {}

        # Filter requirements based on project size
        project_size = (constraints.quality_requirements or {}).get(
            "project_size", "medium"
        )
        functional_requirements = self._filter_requirements_by_size(
            analysis.functional_requirements, project_size, constraints.team_size
        )

        # Get complexity mode from constraints (passed from create_project)
        complexity_mode = constraints.complexity_mode

        # STEP 1: Discover domains from functional requirements
        domains = await self._discover_domains(functional_requirements)
        logger.info(f"Discovered {len(domains)} domains: {list(domains.keys())}")

        # STEP 2: Create bundled design tasks (one per domain)
        bundled_design_tasks = await self._create_bundled_design_tasks(
            domains, functional_requirements, complexity_mode
        )

        # Store bundled design tasks (they don't belong to any epic)
        if bundled_design_tasks:
            design_epic_id = "epic_design_architecture"
            hierarchy[design_epic_id] = []

            for task in bundled_design_tasks:
                self._task_metadata[task["id"]] = {
                    "original_name": task["name"],
                    "type": task["type"],
                    "epic_id": design_epic_id,
                    "domain_name": task["domain_name"],
                    "feature_ids": task["feature_ids"],
                }
                hierarchy[design_epic_id].append(task["id"])

        # Store domain mapping for later dependency resolution
        self._domain_mapping = domains  # feature_id -> domain_name lookup
        self._bundled_designs = {
            task["domain_name"]: task["id"] for task in bundled_design_tasks
        }

        # Validate functional requirements for duplicates before creating epics
        req_ids = [req.get("id") for req in functional_requirements]
        logger.info(
            f"Creating epics from {len(functional_requirements)} functional "
            f"requirements: {req_ids}"
        )

        # Check for duplicate IDs (should not happen after deduplication, but verify)
        if len(req_ids) != len(set(req_ids)):
            from collections import Counter

            id_counts = Counter(req_ids)
            duplicates = [req_id for req_id, count in id_counts.items() if count > 1]
            logger.error(
                f"DUPLICATE REQUIREMENT IDs DETECTED: {duplicates} - "
                f"This will create duplicate tasks! Check deduplication logic."
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
                    f"Generated fallback ID '{req_id}' for requirement "
                    f"without 'id' field"
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
        """
        Create detailed Task objects with rich metadata.

        Uses parallel AI calls for performance - all task descriptions are
        generated concurrently instead of sequentially.
        """
        import asyncio

        # Collect all task generation jobs for parallel execution
        task_generation_jobs = []
        task_sequence = 1

        for epic_id, task_ids in list(task_hierarchy.items()):
            # Skip deployment-related epics based on deployment_target
            deploy_target = constraints.deployment_target
            if self._should_skip_epic(epic_id, deploy_target):
                logger.info(f"Skipping {epic_id} for deployment_target={deploy_target}")
                continue

            for task_id in task_ids:
                # Skip deployment-related tasks based on deployment_target
                if self._should_skip_task(
                    task_id, epic_id, constraints.deployment_target
                ):
                    logger.info(
                        f"Skipping task {task_id} for "
                        f"deployment_target={constraints.deployment_target}"
                    )
                    continue

                # Add task generation to parallel jobs instead of awaiting
                task_generation_jobs.append(
                    self._generate_detailed_task(
                        task_id, epic_id, analysis, constraints, task_sequence
                    )
                )
                task_sequence += 1

        # Execute all task generations in parallel with error handling
        logger.info(
            f"Generating {len(task_generation_jobs)} task descriptions in parallel..."
        )
        task_results = await asyncio.gather(
            *task_generation_jobs, return_exceptions=True
        )

        # Filter out exceptions and collect valid tasks
        tasks = []
        failed_count = 0
        for idx, result in enumerate(task_results):
            if isinstance(result, Task):
                tasks.append(result)
            elif isinstance(result, Exception):
                failed_count += 1
                logger.error(
                    f"Task generation failed for task {idx + 1}: {result}",
                    exc_info=result,
                )
                # Continue with other tasks

        if failed_count > 0:
            logger.warning(
                f"Task generation completed with {failed_count} failures. "
                f"Successfully generated {len(tasks)}/{len(task_results)} tasks."
            )
        else:
            logger.info(f"Successfully generated all {len(tasks)} tasks in parallel")

        return tasks

    async def _generate_detailed_task(
        self,
        task_id: str,
        epic_id: str,
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
        sequence: int,
    ) -> Task:
        """
        Generate a detailed task using AI descriptions directly.

        This creates tasks with clean, AI-generated descriptions instead of
        template boilerplate, while preserving Design/Implement/Test methodology
        through task names and labels.
        """
        # Extract task type from task_id
        task_type = self._extract_task_type(task_id)

        # Find matching requirement from AI analysis
        relevant_req = self._find_matching_requirement(task_id, analysis)

        if relevant_req:
            # Get base information from requirement
            base_description = relevant_req.get("description", "")
            feature_name = relevant_req.get("name", "")

            # Create task name with phase prefix
            task_name = f"{task_type.title()} {feature_name}"

            # Generate task-type-specific description using LLM with constraints
            description = await self._generate_task_description_for_type(
                base_description=base_description,
                task_type=task_type,
                feature_name=feature_name,
                constraints=analysis.technical_constraints,
                original_description=analysis.original_description,
            )

            # Get estimated hours based on task type
            # CRITICAL: Use learned median from historical data
            # Falls back to reality-based estimates (4-8 minutes)
            if task_type == "design":
                estimated_minutes = self._get_learned_task_duration(
                    "design", default_minutes=6.0
                )
            elif task_type == "implement":
                estimated_minutes = self._get_learned_task_duration(
                    "implement", default_minutes=8.0
                )
            elif task_type == "test":
                estimated_minutes = self._get_learned_task_duration(
                    "test", default_minutes=6.0
                )
            else:
                estimated_minutes = self._get_learned_task_duration(
                    task_type, default_minutes=7.0
                )

            # Convert to hours for backward compatibility with existing system
            estimated_hours = estimated_minutes / 60

        else:
            # Fallback: use old template approach if no AI requirement matches
            logger.warning(f"No matching AI requirement for {task_id}, using fallback")
            task_info = self._extract_task_info(task_id, epic_id, analysis)
            enhanced_details = await self._enhance_task_with_ai(
                task_info, analysis, constraints
            )
            task_name = enhanced_details.get("name", f"Task {sequence}")
            description = enhanced_details.get("description", "")
            estimated_hours = enhanced_details.get("estimated_hours", 12.0)
            feature_name = task_name  # Use task name for labels in fallback

        # Generate labels (methodology preserved here)
        labels = self._generate_task_labels(task_type, feature_name, analysis)

        # Create task with clean AI description
        task = Task(
            id=task_id,
            name=task_name,
            description=description,  # ✅ Clean AI content, no template noise
            status=TaskStatus.TODO,
            priority=self._determine_priority({"type": task_type}, analysis),
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=estimated_hours,
            dependencies=[],  # Will be filled by dependency inference
            labels=labels,
            # Store context for reference
            source_type="nlp_project",
            source_context={
                "prd_analysis": (
                    analysis.__dict__ if hasattr(analysis, "__dict__") else {}
                ),
                "requirement": relevant_req,
                "task_type": task_type,
                "constraints": (
                    constraints.__dict__ if hasattr(constraints, "__dict__") else {}
                ),
            },
        )

        return task

    def _extract_task_type(self, task_id: str) -> str:
        """
        Extract task type (design/implement/test) from task_id.

        Parameters
        ----------
        task_id : str
            Task ID in format like "epic_1_design_1" or "epic_1_implement_1"

        Returns
        -------
        str
            Task type: "design", "implement", or "test"
        """
        task_id_lower = task_id.lower()

        if "design" in task_id_lower:
            return "design"
        elif "implement" in task_id_lower:
            return "implement"
        elif "test" in task_id_lower:
            return "test"
        else:
            # Default to implement for unknown types
            logger.warning(
                f"Could not extract task type from {task_id}, defaulting to 'implement'"
            )
            return "implement"

    def _find_matching_requirement(
        self, task_id: str, analysis: PRDAnalysis
    ) -> Optional[Dict[str, Any]]:
        """
        Find the AI requirement that matches this task_id.

        Parameters
        ----------
        task_id : str
            Task ID like "task_todo_list_management_design" or
            "nfr_task_performance_requirement"
        analysis : PRDAnalysis
            Complete PRD analysis with requirements

        Returns
        -------
        Optional[Dict[str, Any]]
            Matching requirement dict or None if not found
        """
        # Get all requirements from analysis (functional + non-functional)
        functional_reqs = getattr(analysis, "functional_requirements", [])
        non_functional_reqs = getattr(analysis, "non_functional_requirements", [])

        all_requirements = []
        if functional_reqs:
            all_requirements.extend(
                functional_reqs
                if isinstance(functional_reqs, list)
                else [functional_reqs]
            )
        if non_functional_reqs:
            all_requirements.extend(
                non_functional_reqs
                if isinstance(non_functional_reqs, list)
                else [non_functional_reqs]
            )

        if not all_requirements:
            logger.warning("No requirements found in analysis")
            return None

        # Extract requirement ID from task_id
        # task_todo_list_management_design -> todo_list_management
        # nfr_task_performance_requirement -> performance_requirement
        # task_user_auth_implement -> user_auth

        if task_id.startswith("nfr_task_"):
            # Non-functional requirement - strip "nfr_task_" AND phase suffix
            # Example: nfr_task_scalability_implement -> scalability
            parts = task_id.replace("nfr_task_", "").rsplit("_", 1)
            req_id = parts[0] if parts else task_id.replace("nfr_task_", "")
        elif task_id.startswith("task_"):
            # Functional requirement - extract between "task_" and last "_phase"
            parts = task_id.replace("task_", "").rsplit("_", 1)
            req_id = parts[0] if parts else task_id
        else:
            logger.warning(f"Unknown task_id format: {task_id}")
            return None

        logger.debug(f"Extracted req_id '{req_id}' from task_id '{task_id}'")

        # Find matching requirement by ID
        for req in all_requirements:
            # Convert to dict if it's a Pydantic model
            req_dict: Dict[str, Any]
            if hasattr(req, "dict"):
                req_dict = req.dict()
            elif hasattr(req, "__dict__"):
                req_dict = req.__dict__
            elif isinstance(req, dict):
                req_dict = req
            else:
                continue

            # Check if this requirement matches
            if req_dict.get("id") == req_id:
                logger.debug(
                    f"Matched requirement: task_id='{task_id}' -> "
                    f"req_id='{req_id}' -> '{req_dict.get('name')}'"
                )
                return req_dict

        logger.warning(f"No requirement found with id={req_id} for task_id={task_id}")
        return None

    def _deduplicate_functional_requirements(
        self, requirements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate functional requirements based on ID and semantic similarity.

        This prevents the AI from creating duplicate tasks when it generates
        similar requirements with different names (e.g., "User Auth" and
        "Authentication System" for the same feature).

        Parameters
        ----------
        requirements : List[Dict[str, Any]]
            Raw functional requirements from AI analysis

        Returns
        -------
        List[Dict[str, Any]]
            Deduplicated requirements

        Notes
        -----
        Deduplication strategy:
        1. Check for exact duplicate IDs
        2. Normalize feature names to detect semantic duplicates:
           - Remove common suffixes: " system", " feature", " component", " module"
           - Normalize variations: "authentication" → "auth", "authorization" → "auth"
        3. Keep first occurrence, log and skip duplicates
        """
        seen_ids = set()
        seen_names_normalized = set()
        deduplicated = []

        for req in requirements:
            req_id = req.get("id", "").lower().strip()
            req_name = req.get("name", "").lower().strip()

            # Normalize name for similarity checking
            normalized_name = req_name
            # Remove common suffix variations
            for suffix in [" system", " feature", " component", " module", " service"]:
                normalized_name = normalized_name.replace(suffix, "")
            # Normalize common variations
            normalized_name = normalized_name.replace("authentication", "auth")
            normalized_name = normalized_name.replace("authorization", "auth")
            normalized_name = normalized_name.replace("management", "mgmt")

            # Check for duplicate ID
            if req_id in seen_ids:
                logger.warning(
                    f"Duplicate requirement ID detected: '{req_id}' - "
                    f"'{req.get('name')}' - SKIPPING (AI violated uniqueness "
                    f"constraint)"
                )
                continue

            # Check for semantic duplicate (similar name)
            if normalized_name in seen_names_normalized:
                logger.warning(
                    f"Duplicate requirement detected (similar name): "
                    f"'{req.get('name')}' (normalized: '{normalized_name}') - "
                    f"SKIPPING (consolidate with existing requirement)"
                )
                continue

            # Add to results
            seen_ids.add(req_id)
            seen_names_normalized.add(normalized_name)
            deduplicated.append(req)

        if len(deduplicated) < len(requirements):
            logger.info(
                f"Deduplication removed {len(requirements) - len(deduplicated)} "
                f"duplicate functional requirements"
            )

        return deduplicated

    def _format_constraints_for_prompt(self, constraints: List[str]) -> str:
        """
        Format technical constraints for inclusion in AI prompts.

        Converts constraint tags like "vanilla-js" into readable descriptions
        that help the AI understand what to include/exclude.

        Parameters
        ----------
        constraints : List[str]
            List of constraint tags (e.g., ["vanilla-js", "no-frameworks"])

        Returns
        -------
        str
            Human-readable constraint description for AI prompts
        """
        if not constraints:
            return ""

        # Separate positive and negative constraints
        positive = []
        negative = []

        for constraint in constraints:
            if constraint.startswith("no-"):
                # Convert "no-X" to "do not use X"
                tech = constraint[3:].replace("-", " ")
                negative.append(tech)
            else:
                # Convert "vanilla-js" to "vanilla JavaScript"
                tech = constraint.replace("-", " ")
                positive.append(tech)

        parts = []
        if positive:
            parts.append(f"Use: {', '.join(positive)}")
        if negative:
            parts.append(f"Do not use: {', '.join(negative)}")

        return ". ".join(parts) if parts else ""

    def _check_constraint_violations(
        self, description: str, constraints: List[str]
    ) -> List[str]:
        """
        Check if a task description violates any technical constraints.

        Parameters
        ----------
        description : str
            The generated task description
        constraints : List[str]
            List of constraint tags to check against

        Returns
        -------
        List[str]
            List of detected violations (empty if no violations)
        """
        violations = []
        description_lower = description.lower()

        # Check for specific "no-X" constraints
        # This catches things like "no-react", "no-orm", "no-typescript", etc.
        for constraint in constraints:
            if constraint.startswith("no-"):
                tech = constraint[3:]  # Remove "no-" prefix
                # Normalize both the tech name and description for comparison
                tech_normalized = tech.replace("-", " ").lower()

                # Check if the technology appears in the description
                if tech_normalized in description_lower:
                    violations.append(f"Mentions '{tech}' but constraint prohibits it")

        # Special handling for "no-frameworks" - look for the word "framework"
        if "no-frameworks" in constraints or "vanilla-js" in constraints:
            if "framework" in description_lower:
                violations.append(
                    "Mentions 'framework' but constraints prohibit frameworks"
                )

        return violations

    async def _generate_task_description_for_type(
        self,
        base_description: str,
        task_type: str,
        feature_name: str,
        constraints: Optional[List[str]] = None,
        original_description: Optional[str] = None,
    ) -> str:
        """
        Use LLM to generate task-type-specific descriptions with constraint awareness.

        This ensures Design/Implement/Test tasks get appropriate descriptions
        that are then passed to subtasks during decomposition. Technical constraints
        are incorporated to ensure generated descriptions respect project requirements.

        Parameters
        ----------
        base_description : str
            Original requirement description
        task_type : str
            Task type: "design", "implement", or "test"
        feature_name : str
            Name of the feature being worked on
        constraints : Optional[List[str]], default=None
            Technical constraints to respect (e.g., "vanilla-js", "no-frameworks")
        original_description : Optional[str], default=None
            Original user description for context

        Returns
        -------
        str
            Task-type-specific description that respects constraints
        """
        # Format constraints for the prompt
        constraint_text = ""
        if constraints:
            formatted_constraints = self._format_constraints_for_prompt(constraints)
            if formatted_constraints:
                constraint_text = (
                    f"\n\nTECHNICAL CONSTRAINTS (MUST FOLLOW):\n{formatted_constraints}"
                )

        # Include original description context if available
        original_context = ""
        if original_description:
            original_context = f"\nOriginal Request: {original_description}"

        prompt = f"""Given this feature requirement:

Feature: {feature_name}
Requirement: {base_description}{original_context}{constraint_text}

Generate a clear, specific description for a **{task_type.upper()}** task.

Guidelines:
- For DESIGN tasks: Create specifications for coordination (NOT implementation
  prescription). Define: component boundaries, what needs to communicate,
  data flow patterns, integration points. DO NOT specify: exact API paths,
  exact field names, exact function signatures, exact technologies. Agents
  discover these through get_task_context() and document via log_artifact().
  Example: "Frontend auth component communicates with backend auth service"
  NOT "LoginForm calls POST /api/v1/auth/login with {{email, password}}".
- For IMPLEMENT tasks: Focus on coding, building features, integrating
  components, writing the actual code. Agents use get_task_context() to
  see design artifacts from dependencies.
- For TEST tasks: Focus on writing tests, creating test scenarios,
  validation, test coverage, quality assurance.

IMPORTANT: Your description MUST respect the technical constraints listed above.

Provide ONLY the description (3-4 sentences), no preamble or
explanation."""

        try:
            # Create a simple context object
            class SimpleContext:
                def __init__(self, max_tokens: int) -> None:
                    self.max_tokens = max_tokens

            context = SimpleContext(max_tokens=200)

            # Use LLM to generate task-specific description
            result = await self.llm_client.analyze(prompt, context)
            description: str = str(result) if result else ""
            description = description.strip()

            # Validate that generated description doesn't violate constraints
            if constraints:
                violations = self._check_constraint_violations(description, constraints)
                if violations:
                    logger.warning(
                        f"Generated description has constraint violations: "
                        f"{violations}. Description: {description}"
                    )
                    # Note: We log but don't fail
                    # AI can be retried or manually corrected

            return description

        except Exception as e:
            logger.warning(
                f"Failed to generate task-specific description: {e}. "
                f"Falling back to base description."
            )
            # Fallback: use base description with simple prefix
            if task_type == "design":
                return f"Design {base_description.lower()}"
            elif task_type == "test":
                return f"Test {base_description.lower()}"
            else:
                return base_description

    def _generate_task_labels(
        self, task_type: str, feature_name: str, analysis: PRDAnalysis
    ) -> List[str]:
        """
        Generate labels for a task to preserve D/I/T methodology.

        Parameters
        ----------
        task_type : str
            "design", "implement", or "test"
        feature_name : str
            Name of the feature being worked on
        analysis : PRDAnalysis
            Complete PRD analysis

        Returns
        -------
        List[str]
            List of labels for the task
        """
        labels = []

        # Add task type label (preserves methodology)
        labels.append(task_type)

        # Add technology/domain labels from analysis
        tech_stack = getattr(analysis, "technical_requirements", {})
        if isinstance(tech_stack, dict):
            # Add backend/frontend labels
            if tech_stack.get("backend"):
                labels.append("backend")
            if tech_stack.get("frontend"):
                labels.append("frontend")
            if tech_stack.get("database"):
                labels.append("database")

        # Add priority-based labels
        project_type = getattr(analysis, "project_type", "")
        if project_type:
            labels.append(project_type.lower())

        # Add feature-based labels (extract key terms)
        feature_lower = feature_name.lower()
        if "api" in feature_lower or "endpoint" in feature_lower:
            labels.append("api")
        if "auth" in feature_lower or "login" in feature_lower:
            labels.append("authentication")
        if "user" in feature_lower:
            labels.append("user-management")
        if "database" in feature_lower or "model" in feature_lower:
            labels.append("data")

        # Remove duplicates while preserving order
        seen = set()
        unique_labels = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique_labels.append(label)

        return unique_labels

    async def _infer_smart_dependencies(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Use AI to infer intelligent dependencies."""
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

        # BUGFIX: Filter out generic design→implement dependencies when using
        # bundled domain designs. The pattern-based inference adds ALL design
        # tasks as dependencies for implement/test tasks. We'll replace these
        # with domain-specific dependencies in the next step.
        if hasattr(self, "_bundled_designs") and self._bundled_designs:
            filtered_dependencies = []

            for dep in dependencies:
                dep_task = next(
                    (t for t in tasks if t.id == dep["dependency_task_id"]), None
                )
                dependent_task = next(
                    (t for t in tasks if t.id == dep["dependent_task_id"]), None
                )

                # Skip generic design dependencies when:
                # 1. Dependency is ANY design task (check by name prefix)
                # 2. Dependent is an implement/test task
                # 3. This is from pattern-based inference (not domain-specific)
                is_design_task = dep_task and dep_task.name.lower().startswith(
                    "design "
                )
                is_implement_or_test_task = dependent_task and (
                    dependent_task.name.lower().startswith("implement ")
                    or dependent_task.name.lower().startswith("test ")
                )

                if (
                    is_design_task
                    and is_implement_or_test_task
                    and dep["dependency_type"] == "blocks"
                ):
                    # Type narrowing: we know both are not None from the
                    # conditions above
                    assert dependent_task is not None
                    assert dep_task is not None
                    logger.debug(
                        f"Filtering generic design dependency: "
                        f"{dependent_task.name} -x-> {dep_task.name} "
                        f"(will use domain-specific dependency instead)"
                    )
                    continue

                filtered_dependencies.append(dep)

            dependencies = filtered_dependencies
            logger.info(
                f"Filtered {len(dependencies) - len(filtered_dependencies)} "
                f"generic design dependencies (using bundled domain designs)"
            )

        # Add PRD-specific dependencies (domain-aware)
        prd_dependencies = await self._add_prd_specific_dependencies(tasks, analysis)
        dependencies.extend(prd_dependencies)

        return dependencies

    async def _assess_implementation_risks(
        self, tasks: List[Task], analysis: PRDAnalysis, constraints: ProjectConstraints
    ) -> Dict[str, Any]:
        """Assess implementation risks with AI analysis."""
        risk_assessment: Dict[str, Any] = {
            "overall_risk_level": "medium",
            "risk_factors": [],
            "mitigation_strategies": [],
            "critical_path_risks": [],
            "resource_risks": [],
            "timeline_risks": [],
        }

        # Analyze complexity risks
        complexity_risks = await self._analyze_complexity_risks(tasks, analysis)
        risk_factors_list: List[Dict[str, Any]] = risk_assessment["risk_factors"]
        risk_factors_list.extend(complexity_risks)

        # Analyze constraint risks
        constraint_risks = await self._analyze_constraint_risks(tasks, constraints)
        timeline_risks_list: List[Dict[str, Any]] = risk_assessment["timeline_risks"]
        timeline_risks_list.extend(constraint_risks)

        # Generate mitigation strategies
        mitigation = await self._generate_mitigation_strategies(
            risk_factors_list, tasks, analysis
        )
        risk_assessment["mitigation_strategies"] = mitigation

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
        """Predict project timeline with AI-enhanced estimation."""
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
        start_date = datetime.now(timezone.utc)
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
        """Analyze resource requirements."""
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
        """Generate project success criteria."""
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
        """Calculate confidence in task generation quality."""
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
        # Expect 3 tasks per requirement
        coverage_score = min(len(tasks) / max(req_count * 3, 1), 1.0)
        factors.append(coverage_score)

        return sum(factors) / len(factors) if factors else 0.5

    # Removed fallback simulation methods - now uses proper Marcus
    # Error Framework. When AI analysis fails, the system will raise
    # appropriate errors with actionable feedback

    # Additional helper methods would be implemented here...
    def _select_task_pattern(
        self, requirement: Dict[str, Any], complexity_mode: str = "standard"
    ) -> List[Dict[str, str]]:
        """
        Select task pattern based on feature complexity and project mode.

        Implements intelligent task pattern selection to avoid over-engineering
        simple features while maintaining proper structure for complex ones.

        Parameters
        ----------
        requirement : Dict[str, Any]
            The requirement dictionary containing:
            - id: Feature identifier
            - name: Feature name
            - complexity: One of "atomic", "simple", "coordinated", "distributed"
            - requires_design_artifacts: Boolean (optional)
        complexity_mode : str, optional
            Project complexity mode: "prototype", "standard", or "enterprise"
            Default is "standard"

        Returns
        -------
        List[Dict[str, str]]
            List of task dictionaries, each containing:
            - id: Task identifier
            - name: Task name
            - type: Task type ("design", "implementation", or "testing")

        Notes
        -----
        Task patterns by complexity and mode:

        Prototype Mode (speed-focused):
        - atomic: 1 task (Implementation only)
        - simple: 1 task (Implementation only)
        - coordinated: 2 tasks (Implementation + Testing)
        - distributed: 2 tasks (Implementation + Testing)

        Standard Mode (balanced):
        - atomic: 1 task (Implementation only)
        - simple: 2 tasks (Implementation + Testing)
        - coordinated: 3 tasks (Design + Implementation + Testing)
        - distributed: 3 tasks (Design + Implementation + Testing)

        Enterprise Mode (full traceability):
        - atomic: 2 tasks (Implementation + Testing)
        - simple: 3 tasks (Design + Implementation + Testing)
        - coordinated: 3 tasks (Design + Implementation + Testing)
        - distributed: 3 tasks (Design + Implementation + Testing)
        """
        # Validate complexity_mode
        if complexity_mode not in self.VALID_COMPLEXITY_MODES:
            logger.warning(
                f"Invalid complexity_mode '{complexity_mode}', "
                f"defaulting to 'standard'. "
                f"Valid modes: {self.VALID_COMPLEXITY_MODES}"
            )
            complexity_mode = "standard"

        req_id = requirement.get("id", "feature")
        feature_name = requirement.get("name", "Feature")
        complexity = requirement.get("complexity", "coordinated")  # Backward compatible

        # Validate complexity
        if complexity not in self.VALID_COMPLEXITIES:
            logger.warning(
                f"Invalid complexity '{complexity}', defaulting to 'coordinated'. "
                f"Valid complexities: {self.VALID_COMPLEXITIES}"
            )
            complexity = "coordinated"

        tasks = []

        # Determine task pattern based on complexity and mode
        if complexity_mode == "prototype":
            # Prototype: Speed over structure
            # Design ONLY for coordinated/distributed (produces artifacts)
            # Atomic/simple: just implement (nothing to coordinate)
            if complexity in ["coordinated", "distributed"]:
                tasks.append(
                    {
                        "id": f"task_{req_id}_design",
                        "name": f"Design {feature_name}",
                        "type": self.TASK_TYPE_DESIGN,
                    }
                )
            tasks.append(
                {
                    "id": f"task_{req_id}_implement",
                    "name": f"Implement {feature_name}",
                    "type": self.TASK_TYPE_IMPLEMENTATION,
                }
            )
            # Add testing for coordinated/distributed features
            if complexity in ["coordinated", "distributed"]:
                tasks.append(
                    {
                        "id": f"task_{req_id}_test",
                        "name": f"Test {feature_name}",
                        "type": self.TASK_TYPE_TESTING,
                    }
                )

        elif complexity_mode == "enterprise":
            # Enterprise: Full traceability with design tasks for all features
            tasks.append(
                {
                    "id": f"task_{req_id}_design",
                    "name": f"Design {feature_name}",
                    "type": self.TASK_TYPE_DESIGN,
                }
            )
            tasks.append(
                {
                    "id": f"task_{req_id}_implement",
                    "name": f"Implement {feature_name}",
                    "type": self.TASK_TYPE_IMPLEMENTATION,
                }
            )
            tasks.append(
                {
                    "id": f"task_{req_id}_test",
                    "name": f"Test {feature_name}",
                    "type": self.TASK_TYPE_TESTING,
                }
            )

        else:  # standard mode (default)
            # Design ONLY for coordinated/distributed (produces coordination artifacts)
            # Atomic/simple: just implement (nothing to coordinate)
            if complexity in ["coordinated", "distributed"]:
                tasks.append(
                    {
                        "id": f"task_{req_id}_design",
                        "name": f"Design {feature_name}",
                        "type": self.TASK_TYPE_DESIGN,
                    }
                )
            tasks.append(
                {
                    "id": f"task_{req_id}_implement",
                    "name": f"Implement {feature_name}",
                    "type": self.TASK_TYPE_IMPLEMENTATION,
                }
            )
            # Add testing for simple/coordinated/distributed (not atomic)
            if complexity != "atomic":
                tasks.append(
                    {
                        "id": f"task_{req_id}_test",
                        "name": f"Test {feature_name}",
                        "type": self.TASK_TYPE_TESTING,
                    }
                )

        return tasks

    async def _break_down_epic(
        self,
        req: Dict[str, Any],
        analysis: PRDAnalysis,
        constraints: ProjectConstraints,
    ) -> List[Dict[str, Any]]:
        """
        Break down epic into smaller tasks using intelligent task pattern selection.

        This method now uses _select_task_pattern() to determine the appropriate
        number and type of tasks based on feature complexity and project mode.

        Parameters
        ----------
        req : Dict[str, Any]
            The requirement dictionary containing complexity metadata
        analysis : PRDAnalysis
            The full PRD analysis context
        constraints : ProjectConstraints
            Project constraints including quality requirements

        Returns
        -------
        List[Dict[str, Any]]
            List of task dictionaries for this epic
        """
        # Ensure requirement has valid ID and name (fallback generation)
        req_id = req.get("id")
        feature_name = req.get("name")

        # Fallback to other possible field names if template wasn't followed
        if not feature_name:
            feature_name = req.get("feature") or req.get("description") or "feature"
            logger.warning(
                f"AI deviated from template format. Expected 'name' "
                f"field but got: {list(req.keys())}"
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

            # If we still don't have a good ID, use the index from
            # functional requirements
            if not feature_id or feature_id == "feature":
                req_index = (
                    analysis.functional_requirements.index(req)
                    if req in analysis.functional_requirements
                    else 0
                )
                feature_id = f"req_{req_index}"

            req_id = feature_id
            logger.warning(
                f"AI deviated from template format. Expected 'id' "
                f"field, generated: {req_id}"
            )

        # Inject the normalized ID and name back into requirement
        # to ensure _select_task_pattern gets consistent values
        req["id"] = req_id
        req["name"] = feature_name

        # Get complexity mode from constraints (passed from create_project)
        complexity_mode = constraints.complexity_mode

        # Use intelligent task pattern selection
        tasks = self._select_task_pattern(req, complexity_mode)

        return tasks

    async def _create_nfr_tasks(
        self, nfrs: List[Dict[str, Any]], constraints: ProjectConstraints
    ) -> List[Dict[str, Any]]:
        """Create non-functional requirement tasks."""
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
                        f"NFR deviated from template format. Expected "
                        f"'name' field but got: {list(nfr.keys())}"
                    )

            if not nfr_id:
                # Generate clean ID as fallback
                req_id = nfr_name.lower().replace(" ", "_").replace("-", "_")
                req_id = "".join(c if c.isalnum() or c == "_" else "" for c in req_id)
                nfr_id = req_id or str(i)
                logger.warning(
                    f"NFR deviated from template format. Expected 'id' "
                    f"field, generated: {nfr_id}"
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
        """Create infrastructure and setup tasks."""
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
        """Extract task information from analysis."""
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
        """Enhance task with PRD-aware details following board quality standards."""
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
            estimated_hours = 6 / 60  # 6 minutes in hours
        elif "implement" in task_id.lower():
            name, description = self._generate_implementation_task(
                project_context, task_id, original_name
            )
            task_type = "implementation"
            estimated_hours = 8 / 60  # 8 minutes in hours
        elif "test" in task_id.lower():
            name, description = self._generate_testing_task(
                project_context, task_id, original_name
            )
            task_type = "testing"
            estimated_hours = 6 / 60  # 6 minutes in hours
        elif "setup" in task_id.lower() or "infra" in task_id.lower():
            name, description = self._generate_infrastructure_task(
                project_context, task_id, original_name
            )
            task_type = "setup"
            estimated_hours = 10 / 60  # 10 minutes in hours
        else:
            name, description = self._generate_generic_task(
                project_context, task_id, original_name
            )
            task_type = "feature"
            estimated_hours = 7 / 60  # 7 minutes in hours

        # Generate appropriate labels based on context and requirements
        labels = self._generate_labels(task_type, project_context, constraints)

        # Add feature label based on epic_id to group related tasks
        # This ensures tasks from the same feature share a common label
        # for phase enforcement
        if epic_id and epic_id.startswith("epic_"):
            feature_name = epic_id.replace("epic_", "").replace("_", "-")
            labels.append(f"feature:{feature_name}")

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
        """Determine task priority."""
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
        """
        Add PRD-specific dependencies, including bundled design dependencies.

        Creates dependencies from implement/test tasks to their domain's bundled
        design task to ensure coordination.
        """
        dependencies = []

        # Check if we have bundled designs and domain mapping
        if not hasattr(self, "_bundled_designs") or not hasattr(
            self, "_domain_mapping"
        ):
            return []

        # Create a reverse mapping: feature_id -> domain_name
        feature_to_domain = {}
        for domain_name, feature_ids in self._domain_mapping.items():
            for feature_id in feature_ids:
                feature_to_domain[feature_id] = domain_name

        # For each task, check if it needs to depend on a bundled design
        for task in tasks:
            task_id_lower = task.id.lower()

            # Only implement and test tasks depend on design
            if "implement" not in task_id_lower and "test" not in task_id_lower:
                continue

            # Extract feature_id from task_id
            # (e.g., "task_user_login_implement" -> "user_login")
            # Task IDs are in format: "task_{feature_id}_{type}"
            parts = task.id.split("_")
            if len(parts) >= 3 and parts[0] == "task":
                # Find the feature_id (everything between "task_" and the type suffix)
                type_suffixes = ["design", "implement", "test"]
                # Remove "task_" prefix
                remainder = "_".join(parts[1:])
                # Remove type suffix
                feature_id = remainder
                for suffix in type_suffixes:
                    if remainder.endswith(f"_{suffix}"):
                        feature_id = remainder[: -len(f"_{suffix}")]
                        break

                # Find which domain this feature belongs to
                feature_domain: Optional[str] = feature_to_domain.get(feature_id)

                if feature_domain:
                    # Get the bundled design task ID for this domain
                    design_task_id = self._bundled_designs.get(feature_domain)

                    if design_task_id:
                        # Add dependency: implement/test task depends on bundled design
                        dependencies.append(
                            {
                                "dependent_task_id": task.id,
                                "dependency_task_id": design_task_id,
                                "dependency_type": "architectural",
                                # High confidence - explicit bundled design dep
                                "confidence": 1.0,
                                "reasoning": (
                                    f"Implement/test tasks must wait for "
                                    f"{feature_domain} design to define "
                                    f"architecture and interfaces"
                                ),
                            }
                        )
                        logger.debug(
                            f"Added bundled design dependency: "
                            f"{task.id} -> {design_task_id}"
                        )

        logger.info(f"Added {len(dependencies)} bundled design dependencies to tasks")
        return dependencies

    async def _analyze_complexity_risks(
        self, tasks: List[Task], analysis: PRDAnalysis
    ) -> List[Dict[str, Any]]:
        """Analyze complexity-related risks."""
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
        """Analyze constraint-related risks."""
        risks = []
        if constraints.deadline:
            total_effort = sum(task.estimated_hours or 8 for task in tasks)
            days_available = (constraints.deadline - datetime.now(timezone.utc)).days
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
        """Generate risk mitigation strategies."""
        return [
            "Regular risk assessment reviews",
            "Maintain project buffer time",
            "Implement incremental delivery approach",
        ]

    async def _identify_critical_path_tasks(
        self, tasks: List[Task], dependencies: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify tasks on the critical path."""
        # Simplified - return setup and deployment tasks as critical
        return [
            task.id
            for task in tasks
            if any(label in ["setup", "deployment"] for label in task.labels)
        ]

    async def _calculate_milestone_dates(
        self, start_date: datetime, duration_days: float
    ) -> Dict[str, str]:
        """Calculate key milestone dates."""
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
        """Analyze required skills."""
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
        """Analyze technology requirements."""
        return analysis.technical_constraints

    async def _analyze_external_dependencies(self, analysis: PRDAnalysis) -> List[str]:
        """Analyze external dependencies."""
        return ["Third-party API integrations", "External service providers"]

    def _calculate_optimal_team_size(
        self, tasks: List[Task], constraints: ProjectConstraints
    ) -> int:
        """Calculate optimal team size."""
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
        """Identify specialized roles needed."""
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
        """Extract meaningful project context from PRD analysis."""
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

        # Extract the feature from task_id
        # (e.g., task_crud_operations_design -> crud_operations)
        if "task_" in task_id:
            parts = task_id.split("_")
            if len(parts) >= 3:
                feature_parts = parts[1:-1]  # Remove 'task' prefix and action suffix
                feature_id = "_".join(feature_parts)

                # Find the matching functional requirement
                for req in analysis.functional_requirements:
                    req_feature = req.get("feature", "").lower().replace(" ", "_")
                    if req_feature == feature_id:
                        # Determine domain based on requirement
                        feature_val = req.get("feature", "")
                        desc_val = req.get("description", "")
                        req_text = f"{feature_val} {desc_val}".lower()

                        crud_keywords = ["crud", "create", "read", "update", "delete"]
                        if any(word in req_text for word in crud_keywords):
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
        """Generate design task name and description using PRD context."""
        domain = context["domain"]
        project_type = context["project_type"]
        objectives = context["business_objectives"]

        # Extract feature name from original name
        # (e.g., "Design CRUD Operations" -> "CRUD Operations")
        feature_name = original_name.replace("Design ", "") if original_name else ""

        if domain == "crud_operations":
            # Use original feature name if available, otherwise use generic
            name = original_name if original_name else "Design CRUD API Architecture"
            description = (
                f"Create architectural design and documentation for CRUD "
                f"operations in {project_type}. Define API endpoints, "
                f"document request/response formats, plan error handling "
                f"strategies, and design pagination approach. Deliverables: "
                f"API specification document, data flow diagrams, and "
                f"architectural decisions. Goal: "
                f"{objectives[0] if objectives else 'efficient data management'}."
            )
        elif domain == "data_modeling":
            name = original_name if original_name else "Design Data Model and Schema"
            description = (
                f"Design data architecture and create documentation for "
                f"{project_type}. Research data requirements, create entity "
                f"relationship diagrams, document field specifications and "
                f"constraints. Plan migration strategy and define validation "
                f"rules. Deliverables: ER diagrams, schema documentation, and "
                f"data dictionary. Focus on: "
                f"{objectives[0] if objectives else 'scalable data architecture'}."
            )
        elif domain == "validation":
            name = original_name if original_name else "Design Input Validation System"
            description = (
                f"Design validation strategy and create documentation for "
                f"{project_type}. Research validation requirements, define "
                f"validation rules and patterns, plan error handling approach. "
                f"Document security considerations and sanitization procedures. "
                f"Deliverables: validation specification document, error "
                f"message catalog, and security guidelines. Goal: "
                f"{objectives[0] if objectives else 'data integrity and security'}."
            )
        elif domain == "user_management":
            name = original_name if original_name else "Design User Authentication Flow"
            description = (
                f"Design authentication architecture and create documentation "
                f"for {project_type}. Research security requirements, create "
                f"user flow diagrams, document authentication patterns and "
                f"session management approach. Plan security protocols and "
                f"define user account lifecycle. Deliverables: authentication "
                f"flow diagrams, security documentation, and API specifications. "
                f"Goal: {objectives[0] if objectives else 'secure user access'}."
            )
        elif domain == "frontend":
            name = (
                original_name if original_name else "Design User Interface Architecture"
            )
            description = (
                f"Create detailed UI/UX design for {project_type}. Include "
                f"component hierarchy, design system, responsive layouts, and "
                f"user interaction patterns. Focus on achieving: "
                f"{objectives[0] if objectives else 'excellent user experience'}. "
                f"Define accessibility standards and usability requirements."
            )
        elif domain == "backend_services":
            name = original_name if original_name else "Design API Architecture"
            description = (
                f"Design API architecture for {project_type}. Research "
                f"requirements, document API specifications, define endpoint "
                f"patterns and data contracts. Create architectural diagrams "
                f"and technical documentation. Deliverables: API documentation, "
                f"architectural decisions, and interface specifications. "
                f"Focus on: {objectives[0] if objectives else 'scalable API design'}."
            )
        elif domain == "ecommerce":
            name = (
                original_name if original_name else "Design E-commerce User Experience"
            )
            description = (
                f"Design comprehensive e-commerce user experience for "
                f"{project_type}. Include product catalog, shopping cart, "
                f"checkout flow, user accounts, and order management. "
                f"Optimize for: "
                f"{objectives[0] if objectives else 'seamless shopping experience'}."
            )
        else:
            # For any other domain, use original name or create one from
            # feature
            name = (
                original_name
                if original_name
                else (
                    f"Design {feature_name if feature_name else project_type.title()} "
                    f"Architecture"
                )
            )
            description = (
                f"Research and design architecture for {project_type}. Create "
                f"documentation defining approach, patterns, and specifications. "
                f"Plan component structure and integration points. Deliverables: "
                f"design documentation, architectural diagrams, and technical "
                f"specifications. Goal: "
                f"{objectives[0] if objectives else 'effective solution delivery'}."
            )

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
        """Generate implementation task name and description using PRD context."""
        domain = context["domain"]
        project_type = context["project_type"]
        tech_constraints = context["technical_constraints"]

        if domain == "user_management":
            name = (
                original_name
                if original_name
                else "Implement User Authentication Service"
            )
            description = (
                f"Build secure user authentication service for {project_type}. "
                f"Implement user registration, login, JWT token management, "
                f"password hashing with bcrypt, and session handling. "
                f"Technology stack: {', '.join(tech_constraints)}. Include "
                f"rate limiting, email verification, and comprehensive error "
                f"handling."
            )
        elif domain == "frontend":
            name = original_name if original_name else "Build User Interface Components"
            description = (
                f"Develop responsive UI components for {project_type}. Create "
                f"reusable component library, implement state management, handle "
                f"user interactions, and ensure accessibility compliance. Using: "
                f"{', '.join(tech_constraints)}. Include loading states, error "
                f"boundaries, and responsive design."
            )
        elif domain == "backend_services":
            name = original_name if original_name else "Develop Backend API Services"
            objectives = context.get("business_objectives", [])
            description = (
                f"Implement backend API services for {project_type} following "
                f"the design specifications. Build endpoints, business logic, "
                f"data validation, and error handling. Include appropriate tests "
                f"and logging. Technology: {', '.join(tech_constraints)}. Goal: "
                f"{objectives[0] if objectives else 'working implementation'}."
            )
        elif domain == "ecommerce":
            name = original_name if original_name else "Build E-commerce Core Features"
            description = (
                f"Implement core e-commerce functionality for {project_type}. "
                f"Build product catalog, shopping cart, checkout process, "
                f"payment integration, and order management. Stack: "
                f"{', '.join(tech_constraints)}. Include inventory management "
                f"and order tracking."
            )
        elif domain == "crud_operations":
            name = original_name if original_name else "Implement CRUD API Endpoints"
            description = (
                f"Build complete CRUD (Create, Read, Update, Delete) "
                f"functionality for {project_type}. Implement RESTful endpoints "
                f"with proper HTTP methods, request/response handling, data "
                f"validation, and error responses. Technology: "
                f"{', '.join(tech_constraints)}. Include pagination, filtering, "
                f"and sorting capabilities."
            )
        elif domain == "data_modeling":
            name = (
                original_name
                if original_name
                else "Implement Data Models and Database Layer"
            )
            description = (
                f"Create data models and database integration for "
                f"{project_type}. Define schemas, implement ORM/ODM models, "
                f"set up migrations, add indexes for performance, and implement "
                f"data validation. Stack: {', '.join(tech_constraints)}. Include "
                f"relationships, constraints, and data integrity rules."
            )
        elif domain == "validation":
            name = (
                original_name
                if original_name
                else "Implement Input Validation and Sanitization"
            )
            description = (
                f"Build comprehensive validation layer for {project_type}. "
                f"Implement input validation rules, data sanitization, type "
                f"checking, business rule validation, and error message "
                f"formatting. Technology: {', '.join(tech_constraints)}. Include "
                f"XSS prevention, SQL injection protection, and data format "
                f"validation."
            )
        else:
            # Extract feature name from original name
            feature_name = (
                original_name.replace("Implement ", "") if original_name else ""
            )
            name = (
                original_name
                if original_name
                else (
                    f"Implement "
                    f"{feature_name if feature_name else project_type.title()} "
                    f"Core Features"
                )
            )
            description = (
                f"Build core functionality for {project_type}. Implement "
                f"business logic, data processing, user interfaces, and system "
                f"integrations. Using: {', '.join(tech_constraints)}. Include "
                f"proper error handling, logging, and performance optimization."
            )

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
        """Generate testing task name and description using PRD context."""
        domain = context["domain"]
        project_type = context["project_type"]

        if domain == "user_management":
            name = (
                original_name
                if original_name
                else "Test Authentication Security Features"
            )
            description = (
                f"Create comprehensive test suite for user authentication in "
                f"{project_type}. Include unit tests for login/registration, "
                f"integration tests for JWT flows, security testing for password "
                f"policies, and end-to-end user journey tests. Achieve >80% code "
                f"coverage."
            )
        elif domain == "frontend":
            name = original_name if original_name else "Test User Interface Components"
            description = (
                f"Develop UI testing suite for {project_type}. Include component "
                f"unit tests, user interaction tests, accessibility testing, "
                f"responsive design validation, and cross-browser compatibility "
                f"tests. Test all user flows and error states."
            )
        elif domain == "backend_services":
            name = (
                original_name
                if original_name
                else "Test API Functionality and Performance"
            )
            description = (
                f"Create API testing suite for {project_type}. Include endpoint "
                f"unit tests, integration tests, load testing, security testing, "
                f"and error handling validation. Test data validation, "
                f"authentication, and business logic. Achieve >80% coverage."
            )
        elif domain == "ecommerce":
            name = (
                original_name if original_name else "Test E-commerce Transaction Flows"
            )
            description = (
                f"Develop comprehensive testing for {project_type}. Test "
                f"shopping cart functionality, checkout process, payment "
                f"integration, order management, and inventory updates. Include "
                f"security testing for payment processing and fraud prevention."
            )
        elif domain == "crud_operations":
            name = (
                original_name
                if original_name
                else "Test CRUD Operations and API Endpoints"
            )
            description = (
                f"Create comprehensive test suite for CRUD operations in "
                f"{project_type}. Test all HTTP methods (GET, POST, PUT, DELETE), "
                f"validate request/response formats, test error handling, "
                f"pagination, filtering, and edge cases. Include load testing for "
                f"concurrent operations. Achieve >80% coverage."
            )
        elif domain == "data_modeling":
            name = (
                original_name
                if original_name
                else "Test Data Models and Database Operations"
            )
            description = (
                f"Develop database testing suite for {project_type}. Test model "
                f"validations, database constraints, migrations, relationships, "
                f"data integrity, and transaction handling. Include performance "
                f"testing for queries and indexes. Validate data consistency and "
                f"error scenarios."
            )
        elif domain == "validation":
            name = (
                original_name if original_name else "Test Input Validation and Security"
            )
            description = (
                f"Create validation testing suite for {project_type}. Test all "
                f"validation rules, boundary conditions, invalid inputs, injection "
                f"attempts, XSS prevention, and error message accuracy. Include "
                f"fuzz testing and security vulnerability scanning. Ensure "
                f"comprehensive input sanitization coverage."
            )
        else:
            # Extract feature name from original name
            feature_name = original_name.replace("Test ", "") if original_name else ""
            name = (
                original_name
                if original_name
                else (
                    f"Test {feature_name if feature_name else project_type.title()} "
                    f"Functionality"
                )
            )
            description = (
                f"Create comprehensive test suite for {project_type}. Include "
                f"unit tests, integration tests, and end-to-end testing. Validate "
                f"business logic, user workflows, and system reliability. Achieve "
                f">80% code coverage."
            )

        return name, description

    def _generate_infrastructure_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate infrastructure task name and description using PRD context."""
        project_type = context["project_type"]
        tech_constraints = context["technical_constraints"]

        if "setup" in task_id.lower():
            name = original_name if original_name else "Setup Development Environment"
            description = (
                f"Configure complete development environment for {project_type}. "
                f"Set up local development stack, database, environment variables, "
                f"development tools, and project dependencies. Technology: "
                f"{', '.join(tech_constraints)}. Include Docker containers, hot "
                f"reloading, and debugging tools."
            )
        elif "ci" in task_id.lower() or "cd" in task_id.lower():
            name = original_name if original_name else "Configure CI/CD Pipeline"
            description = (
                f"Set up continuous integration and deployment for {project_type}. "
                f"Configure automated testing, code quality checks, building, and "
                f"deployment to staging/production. Using: "
                f"{', '.join(tech_constraints)}. Include security scanning and "
                f"performance monitoring."
            )
        elif "deploy" in task_id.lower():
            name = original_name if original_name else "Setup Production Deployment"
            description = (
                f"Configure production infrastructure for {project_type}. Set up "
                f"hosting, load balancing, monitoring, logging, backup systems, "
                f"and security measures. Technology: {', '.join(tech_constraints)}. "
                f"Include scaling strategy and disaster recovery."
            )
        else:
            name = original_name if original_name else "Configure System Infrastructure"
            description = (
                f"Set up core infrastructure for {project_type}. Configure "
                f"servers, databases, caching, monitoring, and security systems. "
                f"Stack: {', '.join(tech_constraints)}. Include performance "
                f"optimization and maintenance procedures."
            )

        return name, description

    def _generate_generic_task(
        self, context: Dict[str, Any], task_id: str, original_name: str = ""
    ) -> Tuple[str, str]:
        """Generate generic task name and description using PRD context."""
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
                description = (
                    f"Address performance, security, and scalability "
                    f"requirements for {project_type}. Implement caching, "
                    f"optimize database queries, add security headers, and ensure "
                    f"system reliability. Target: "
                    f"{objectives[0] if objectives else 'system performance'}."
                )
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
                description = (
                    f"Complete implementation of: {req_desc}. For {project_type} "
                    f"to achieve: "
                    f"{objectives[0] if objectives else 'project goals'}."
                )
            else:
                name = f"Implement Core {project_type.title()} Feature"
                description = (
                    f"Build essential functionality for {project_type}. "
                    f"Implement core business logic, user interactions, and "
                    f"system integrations to achieve: "
                    f"{objectives[0] if objectives else 'project success'}."
                )
        else:
            name = f"Develop {project_type.title()} Component"
            description = (
                f"Build and integrate component for {project_type}. Implement "
                f"required functionality, ensure proper testing, and maintain "
                f"code quality standards. Supports: "
                f"{objectives[0] if objectives else 'project objectives'}."
            )

        return name, description

    def _generate_labels(
        self, task_type: str, context: Dict[str, Any], constraints: ProjectConstraints
    ) -> List[str]:
        """Generate appropriate labels following Board Quality Standards taxonomy."""
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
        """Generate acceptance criteria based on task type and context."""
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
        """Generate subtasks to break down the work."""
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
        """Determine if an epic should be skipped based on deployment target."""
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
        """Determine if a task should be skipped based on deployment target."""
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
        """Filter functional requirements based on project size and team capacity."""
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

    def _filter_nfrs_by_size(
        self, nfrs: List[Dict[str, Any]], project_size: str
    ) -> List[Dict[str, Any]]:
        """Filter non-functional requirements based on project size."""
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
