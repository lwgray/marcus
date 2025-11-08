"""
Intelligent Task Generator for Marcus Phase 2.

AI-powered task generation from PRD requirements.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

try:
    from typing import NotRequired  # Python 3.11+
except ImportError:
    from typing_extensions import NotRequired

from src.core.models import Priority, Task, TaskStatus
from src.intelligence.prd_parser import Feature, ParsedPRD, TechStack

logger = logging.getLogger(__name__)


class TaskTemplate(TypedDict):
    """Type definition for task template."""

    name: str
    description: NotRequired[str]
    hours: int
    dependencies: List[str]


class FeatureTaskTemplate(TypedDict):
    """Type definition for feature task template."""

    name: str
    description: NotRequired[str]
    phase: str
    base_hours: int
    dependencies: List[str]


class TechStackTaskTemplate(TypedDict):
    """Type definition for tech stack task template."""

    name: str
    description: NotRequired[str]
    phase: str
    base_hours: int
    dependencies: List[str]


@dataclass
class ProjectStructure:
    """Generated project structure from PRD."""

    phases: List[str]
    tasks: List[Task]
    dependencies: Dict[str, List[str]]
    estimated_duration: int  # in days
    recommended_team_size: int


@dataclass
class ProjectContext:
    """Context for task generation."""

    tech_stack: TechStack
    team_size: int
    timeline_weeks: int
    complexity_level: str  # low, medium, high


@dataclass
class TaskDescription:
    """Detailed task description."""

    name: str
    description: str
    acceptance_criteria: List[str]
    technical_requirements: List[str]
    phase: str
    estimated_hours: int
    complexity: str
    dependencies: List[str]


class IntelligentTaskGenerator:
    """AI-powered task generation from requirements."""

    def __init__(self) -> None:
        # Task templates for different types of features
        self.feature_task_templates = {
            "user_authentication": [
                {
                    "name": "Design user authentication system",
                    "phase": "design",
                    "base_hours": 4,
                    "dependencies": [],
                },
                {
                    "name": "Implement user registration",
                    "phase": "backend",
                    "base_hours": 8,
                    "dependencies": ["Design user authentication system"],
                },
                {
                    "name": "Implement user login",
                    "phase": "backend",
                    "base_hours": 6,
                    "dependencies": ["Implement user registration"],
                },
                {
                    "name": "Build login/register UI",
                    "phase": "frontend",
                    "base_hours": 8,
                    "dependencies": ["Implement user login"],
                },
                {
                    "name": "Test authentication flow",
                    "phase": "testing",
                    "base_hours": 4,
                    "dependencies": ["Build login/register UI"],
                },
            ],
            "data_management": [
                {
                    "name": "Design data models",
                    "phase": "design",
                    "base_hours": 6,
                    "dependencies": [],
                },
                {
                    "name": "Create database schema",
                    "phase": "backend",
                    "base_hours": 8,
                    "dependencies": ["Design data models"],
                },
                {
                    "name": "Implement CRUD operations",
                    "phase": "backend",
                    "base_hours": 12,
                    "dependencies": ["Create database schema"],
                },
                {
                    "name": "Build data entry forms",
                    "phase": "frontend",
                    "base_hours": 10,
                    "dependencies": ["Implement CRUD operations"],
                },
                {
                    "name": "Test data operations",
                    "phase": "testing",
                    "base_hours": 6,
                    "dependencies": ["Build data entry forms"],
                },
            ],
            "api_integration": [
                {
                    "name": "Design API endpoints",
                    "phase": "design",
                    "base_hours": 4,
                    "dependencies": [],
                },
                {
                    "name": "Implement API endpoints",
                    "phase": "backend",
                    "base_hours": 16,
                    "dependencies": ["Design API endpoints"],
                },
                {
                    "name": "Add API documentation",
                    "phase": "backend",
                    "base_hours": 4,
                    "dependencies": ["Implement API endpoints"],
                },
                {
                    "name": "Integrate frontend with API",
                    "phase": "frontend",
                    "base_hours": 12,
                    "dependencies": ["Add API documentation"],
                },
                {
                    "name": "Test API integration",
                    "phase": "testing",
                    "base_hours": 8,
                    "dependencies": ["Integrate frontend with API"],
                },
            ],
        }

        # Complexity multipliers
        self.complexity_multipliers = {"low": 0.7, "medium": 1.0, "high": 1.5}

        # Tech stack specific tasks
        self.tech_stack_tasks = {
            "react": [
                {
                    "name": "Set up React project structure",
                    "phase": "setup",
                    "base_hours": 3,
                    "dependencies": [],
                },
                {
                    "name": "Configure React routing",
                    "phase": "setup",
                    "base_hours": 2,
                    "dependencies": ["Set up React project structure"],
                },
            ],
            "node": [
                {
                    "name": "Set up Node.js server",
                    "phase": "setup",
                    "base_hours": 3,
                    "dependencies": [],
                },
                {
                    "name": "Configure Express middleware",
                    "phase": "setup",
                    "base_hours": 2,
                    "dependencies": ["Set up Node.js server"],
                },
            ],
            "postgresql": [
                {
                    "name": "Set up PostgreSQL database",
                    "phase": "setup",
                    "base_hours": 2,
                    "dependencies": [],
                },
                {
                    "name": "Configure database migrations",
                    "phase": "setup",
                    "base_hours": 3,
                    "dependencies": ["Set up PostgreSQL database"],
                },
            ],
        }

    async def generate_tasks_from_prd(self, prd: ParsedPRD) -> ProjectStructure:
        """
        Generate complete project structure from parsed PRD.

        Parameters
        ----------
        prd : ParsedPRD
            Parsed PRD with features and requirements

        Returns
        -------
        ProjectStructure
            Complete project structure with tasks and dependencies
        """
        logger.info(f"Generating tasks for project: {prd.title}")

        # Analyze project context
        context = self._analyze_project_context(prd)

        # Generate tasks for each phase
        all_tasks = []

        # 1. Setup tasks
        setup_tasks = await self._generate_setup_tasks(prd.tech_stack, context)
        all_tasks.extend(setup_tasks)

        # 2. Design tasks
        design_tasks = await self._generate_design_tasks(prd.features, context)
        all_tasks.extend(design_tasks)

        # 3. Feature implementation tasks
        feature_tasks = await self._generate_feature_tasks(prd.features, context)
        all_tasks.extend(feature_tasks)

        # 4. Integration tasks
        integration_tasks = await self._generate_integration_tasks(
            prd.features, context
        )
        all_tasks.extend(integration_tasks)

        # 5. Testing tasks
        testing_tasks = await self._generate_testing_tasks(prd.features, context)
        all_tasks.extend(testing_tasks)

        # 6. Deployment tasks
        deployment_tasks = await self._generate_deployment_tasks(
            prd.tech_stack, context
        )
        all_tasks.extend(deployment_tasks)

        # Extract dependencies
        dependencies = self._extract_dependencies(all_tasks)

        # Calculate project metrics
        estimated_duration = self._calculate_project_duration(
            all_tasks, context.team_size
        )
        recommended_team_size = self._recommend_team_size(
            all_tasks, context.timeline_weeks
        )

        return ProjectStructure(
            phases=[
                "setup",
                "design",
                "backend",
                "frontend",
                "integration",
                "testing",
                "deployment",
            ],
            tasks=all_tasks,
            dependencies=dependencies,
            estimated_duration=estimated_duration,
            recommended_team_size=recommended_team_size,
        )

    async def _generate_setup_tasks(
        self, tech_stack: TechStack, context: ProjectContext
    ) -> List[Task]:
        """Generate setup and configuration tasks."""
        tasks = []

        # Basic setup tasks
        basic_setup = [
            {
                "name": "Initialize project repository",
                "description": (
                    "Create Git repository with proper .gitignore and README"
                ),
                "hours": 1,
                "dependencies": [],
            },
            {
                "name": "Set up development environment",
                "description": (
                    "Configure development tools, linters, and IDE settings"
                ),
                "hours": 3,
                "dependencies": ["Initialize project repository"],
            },
        ]

        for task_data in basic_setup:
            task = self._create_task_from_template(task_data, "setup", context)
            tasks.append(task)

        # Tech stack specific setup
        all_tech = (
            tech_stack.frontend
            + tech_stack.backend
            + tech_stack.database
            + tech_stack.infrastructure
        )

        for tech in all_tech:
            tech_lower = tech.lower()
            if tech_lower in self.tech_stack_tasks:
                for task_template in self.tech_stack_tasks[tech_lower]:
                    task = self._create_task_from_template(
                        task_template, "setup", context
                    )
                    tasks.append(task)

        return tasks

    async def _generate_design_tasks(
        self, features: List[Feature], context: ProjectContext
    ) -> List[Task]:
        """Generate design and architecture tasks."""
        tasks = []

        # Basic design tasks
        design_tasks = [
            {
                "name": "Create system architecture diagram",
                "description": (
                    "Design high-level system architecture and "
                    "component relationships"
                ),
                "hours": 6,
                "dependencies": ["Set up development environment"],
            },
            {
                "name": "Design database schema",
                "description": (
                    "Create comprehensive database schema with relationships "
                    "and constraints"
                ),
                "hours": 8,
                "dependencies": ["Create system architecture diagram"],
            },
            {
                "name": "Define API contracts",
                "description": (
                    "Specify API endpoints, request/response formats, "
                    "and error handling"
                ),
                "hours": 6,
                "dependencies": ["Design database schema"],
            },
        ]

        # Add UI design tasks if frontend is involved
        if context.tech_stack.frontend:
            design_tasks.extend(
                [
                    {
                        "name": "Create UI wireframes",
                        "description": (
                            "Design user interface wireframes and " "user flow diagrams"
                        ),
                        "hours": 8,
                        "dependencies": ["Define API contracts"],
                    },
                    {
                        "name": "Design component library",
                        "description": (
                            "Define reusable UI components and design system"
                        ),
                        "hours": 6,
                        "dependencies": ["Create UI wireframes"],
                    },
                ]
            )

        for task_data in design_tasks:
            task = self._create_task_from_template(task_data, "design", context)
            tasks.append(task)

        return tasks

    async def _generate_feature_tasks(
        self, features: List[Feature], context: ProjectContext
    ) -> List[Task]:
        """Generate tasks for implementing features."""
        tasks = []

        for feature in features:
            feature_tasks = await self._generate_tasks_for_feature(feature, context)
            tasks.extend(feature_tasks)

        return tasks

    async def _generate_tasks_for_feature(
        self, feature: Feature, context: ProjectContext
    ) -> List[Task]:
        """Generate tasks for a specific feature."""
        tasks = []

        # Categorize feature type
        feature_type = self._categorize_feature(feature)

        # Get task template for feature type
        task_templates = self.feature_task_templates.get(feature_type, [])

        if not task_templates:
            # Generate generic tasks for unknown feature types
            task_templates = self._generate_generic_feature_tasks(feature)

        # Create tasks from templates
        for template in task_templates:
            # Customize template for this specific feature
            customized_template = self._customize_template_for_feature(
                template, feature, context
            )
            # Ensure phase is a string
            phase_str = str(template.get("phase", "backend"))
            task = self._create_task_from_template(
                customized_template, phase_str, context
            )
            tasks.append(task)

        return tasks

    async def _generate_integration_tasks(
        self, features: List[Feature], context: ProjectContext
    ) -> List[Task]:
        """Generate integration tasks."""
        tasks = []

        integration_tasks = [
            {
                "name": "Integrate frontend and backend",
                "description": (
                    "Connect frontend components to backend APIs and " "test data flow"
                ),
                "hours": 12,
                "dependencies": ["Implement CRUD operations", "Build data entry forms"],
            },
            {
                "name": "Implement error handling",
                "description": "Add comprehensive error handling and user feedback",
                "hours": 8,
                "dependencies": ["Integrate frontend and backend"],
            },
        ]

        # Add external service integrations
        if context.tech_stack.external_services:
            for service in context.tech_stack.external_services:
                integration_tasks.append(
                    {
                        "name": f"Integrate {service}",
                        "description": (
                            f"Implement {service} integration with "
                            f"proper error handling"
                        ),
                        "hours": 6,
                        "dependencies": ["Implement error handling"],
                    }
                )

        for task_data in integration_tasks:
            task = self._create_task_from_template(task_data, "integration", context)
            tasks.append(task)

        return tasks

    async def _generate_testing_tasks(
        self, features: List[Feature], context: ProjectContext
    ) -> List[Task]:
        """Generate testing tasks."""
        tasks = []

        testing_tasks = [
            {
                "name": "Write unit tests",
                "description": "Create comprehensive unit tests for core functionality",
                "hours": 16,
                "dependencies": ["Implement error handling"],
            },
            {
                "name": "Write integration tests",
                "description": "Test component integration and API endpoints",
                "hours": 12,
                "dependencies": ["Write unit tests"],
            },
            {
                "name": "Perform manual testing",
                "description": "Manual testing of all features and user workflows",
                "hours": 10,
                "dependencies": ["Write integration tests"],
            },
            {
                "name": "Fix identified bugs",
                "description": "Address issues found during testing phases",
                "hours": 8,
                "dependencies": ["Perform manual testing"],
            },
        ]

        for task_data in testing_tasks:
            task = self._create_task_from_template(task_data, "testing", context)
            tasks.append(task)

        return tasks

    async def _generate_deployment_tasks(
        self, tech_stack: TechStack, context: ProjectContext
    ) -> List[Task]:
        """Generate deployment tasks."""
        tasks = []

        deployment_tasks = [
            {
                "name": "Set up production environment",
                "description": (
                    "Configure production servers, databases, and infrastructure"
                ),
                "hours": 8,
                "dependencies": ["Fix identified bugs"],
            },
            {
                "name": "Configure CI/CD pipeline",
                "description": "Set up automated testing and deployment pipeline",
                "hours": 6,
                "dependencies": ["Set up production environment"],
            },
            {
                "name": "Deploy to staging",
                "description": (
                    "Deploy application to staging environment for final testing"
                ),
                "hours": 4,
                "dependencies": ["Configure CI/CD pipeline"],
            },
            {
                "name": "Deploy to production",
                "description": "Deploy application to production environment",
                "hours": 4,
                "dependencies": ["Deploy to staging"],
            },
            {
                "name": "Monitor production deployment",
                "description": (
                    "Monitor application performance and fix any deployment issues"
                ),
                "hours": 6,
                "dependencies": ["Deploy to production"],
            },
        ]

        for task_data in deployment_tasks:
            task = self._create_task_from_template(task_data, "deployment", context)
            tasks.append(task)

        return tasks

    def _analyze_project_context(self, prd: ParsedPRD) -> ProjectContext:
        """Analyze PRD to determine project context."""
        # Determine team size
        team_size = prd.constraints.team_size or self._estimate_team_size(prd)

        # Determine timeline
        timeline_weeks = self._parse_timeline(prd.constraints.timeline) or 12

        # Determine complexity
        complexity = self._assess_project_complexity(prd)

        return ProjectContext(
            tech_stack=prd.tech_stack,
            team_size=team_size,
            timeline_weeks=timeline_weeks,
            complexity_level=complexity,
        )

    def _categorize_feature(self, feature: Feature) -> str:
        """Categorize feature to determine task template."""
        feature_text = f"{feature.name} {feature.description}".lower()

        if any(word in feature_text for word in ["auth", "login", "register", "user"]):
            return "user_authentication"
        elif any(
            word in feature_text for word in ["data", "crud", "model", "database"]
        ):
            return "data_management"
        elif any(word in feature_text for word in ["api", "endpoint", "service"]):
            return "api_integration"
        else:
            return "generic"

    def _generate_generic_feature_tasks(self, feature: Feature) -> List[Dict[str, Any]]:
        """Generate generic tasks for unknown feature types."""
        feature.name.replace(" ", "_").lower()

        return [
            {
                "name": f"Design {feature.name}",
                "phase": "design",
                "base_hours": 4,
                "dependencies": ["Define API contracts"],
            },
            {
                "name": f"Implement {feature.name} backend",
                "phase": "backend",
                "base_hours": 8,
                "dependencies": [f"Design {feature.name}"],
            },
            {
                "name": f"Implement {feature.name} frontend",
                "phase": "frontend",
                "base_hours": 8,
                "dependencies": [f"Implement {feature.name} backend"],
            },
            {
                "name": f"Test {feature.name}",
                "phase": "testing",
                "base_hours": 4,
                "dependencies": [f"Implement {feature.name} frontend"],
            },
        ]

    def _customize_template_for_feature(
        self, template: Dict[str, Any], feature: Feature, context: ProjectContext
    ) -> Dict[str, Any]:
        """Customize task template for specific feature."""
        customized = template.copy()

        # Replace generic names with feature-specific names
        if "name" in customized and isinstance(customized["name"], str):
            name = customized["name"]
            name = name.replace("user authentication", feature.name.lower())
            name = name.replace("data management", feature.name.lower())
            customized["name"] = name

        # Adjust hours based on feature complexity
        complexity_multiplier = self.complexity_multipliers.get(
            feature.estimated_complexity, 1.0
        )

        # Convert to consistent format with hours field
        base_hours = customized.get("base_hours", 4)
        if isinstance(base_hours, (int, float)):
            calculated_hours = int(base_hours * complexity_multiplier)
        else:
            calculated_hours = 4

        # Update the template with calculated hours
        customized["hours"] = calculated_hours
        if "base_hours" in customized:
            del customized["base_hours"]

        return customized

    def _create_task_from_template(
        self, template: Dict[str, Any], phase: str, context: ProjectContext
    ) -> Task:
        """Create Task object from template."""
        # Generate unique ID
        task_id = str(uuid.uuid4())

        # Determine priority based on phase
        phase_priorities = {
            "setup": Priority.HIGH,
            "design": Priority.HIGH,
            "backend": Priority.HIGH,
            "frontend": Priority.MEDIUM,
            "integration": Priority.MEDIUM,
            "testing": Priority.HIGH,
            "deployment": Priority.HIGH,
        }

        priority = phase_priorities.get(phase, Priority.MEDIUM)

        # Create labels
        labels = [f"phase:{phase}", f"complexity:{context.complexity_level}"]

        # Add tech stack labels
        if context.tech_stack.frontend:
            labels.extend([f"tech:{tech}" for tech in context.tech_stack.frontend[:2]])
        if context.tech_stack.backend:
            labels.extend([f"tech:{tech}" for tech in context.tech_stack.backend[:2]])

        # Determine estimated hours based on template type
        hours_value = template.get("hours") or template.get("base_hours") or 4
        estimated_hours = (
            float(hours_value) if isinstance(hours_value, (int, float, str)) else 4.0
        )

        # Extract name and description safely
        name = str(template.get("name", "Unnamed Task"))
        description = str(template.get("description", ""))

        # Create task
        task = Task(
            id=task_id,
            name=name,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=estimated_hours,
            dependencies=[],  # Will be resolved later
            labels=labels,
        )

        # Add metadata to source_context for task tracking
        task.source_context = {
            "phase": phase,
            "generated": True,
            "dependencies_names": template.get("dependencies", []),
        }

        return task

    def _extract_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """Extract dependencies between tasks."""
        dependencies = {}
        task_name_to_id = {task.name: task.id for task in tasks}

        for task in tasks:
            # Safely extract dependency names from source_context or metadata
            # (for backward compatibility)
            dep_names = []

            # Try source_context first (preferred)
            try:
                if hasattr(task, "source_context") and task.source_context:
                    dep_names = task.source_context.get("dependencies_names", [])
            except (AttributeError, TypeError):
                pass

            # Try metadata for backward compatibility with tests
            if not dep_names:
                try:
                    if hasattr(task, "metadata") and getattr(task, "metadata", None):
                        metadata = getattr(task, "metadata")
                        if isinstance(metadata, dict):
                            dep_names = metadata.get("dependencies_names", [])
                            # Ensure we got a list from metadata
                            if not isinstance(dep_names, list):
                                dep_names = []
                except (AttributeError, TypeError):
                    dep_names = []

            task_deps = []

            for dep_name in dep_names:
                if dep_name in task_name_to_id:
                    task_deps.append(task_name_to_id[dep_name])
                    if hasattr(task, "dependencies") and hasattr(
                        task.dependencies, "append"
                    ):
                        task.dependencies.append(task_name_to_id[dep_name])

            dependencies[task.id] = task_deps

        return dependencies

    def _estimate_team_size(self, prd: ParsedPRD) -> int:
        """Estimate recommended team size based on PRD."""
        feature_count = len(prd.features)
        tech_complexity = len(
            prd.tech_stack.frontend + prd.tech_stack.backend + prd.tech_stack.database
        )

        if feature_count <= 5 and tech_complexity <= 3:
            return 2
        elif feature_count <= 10 and tech_complexity <= 6:
            return 3
        elif feature_count <= 15:
            return 4
        else:
            return 5

    def _parse_timeline(self, timeline_str: Optional[str]) -> Optional[int]:
        """Parse timeline string to weeks."""
        if not timeline_str:
            return None

        timeline_lower = timeline_str.lower()

        import re

        # Look for weeks
        weeks_match = re.search(r"(\d+)\s*weeks?", timeline_lower)
        if weeks_match:
            return int(weeks_match.group(1))

        # Look for months
        months_match = re.search(r"(\d+)\s*months?", timeline_lower)
        if months_match:
            return int(months_match.group(1)) * 4

        # Look for days
        days_match = re.search(r"(\d+)\s*days?", timeline_lower)
        if days_match:
            return max(1, int(days_match.group(1)) // 7)

        return None

    def _assess_project_complexity(self, prd: ParsedPRD) -> str:
        """Assess overall project complexity."""
        complexity_score = 0

        # Feature complexity
        for feature in prd.features:
            if feature.estimated_complexity == "high":
                complexity_score += 3
            elif feature.estimated_complexity == "medium":
                complexity_score += 2
            else:
                complexity_score += 1

        # Tech stack complexity
        total_tech = len(
            prd.tech_stack.frontend
            + prd.tech_stack.backend
            + prd.tech_stack.database
            + prd.tech_stack.infrastructure
        )
        complexity_score += min(total_tech, 10)

        # External services add complexity
        complexity_score += len(prd.tech_stack.external_services) * 2

        # Normalize score
        if complexity_score <= 10:
            return "low"
        elif complexity_score <= 25:
            return "medium"
        else:
            return "high"

    def _calculate_project_duration(self, tasks: List[Task], team_size: int) -> int:
        """Calculate estimated project duration in days."""
        total_hours = sum(task.estimated_hours for task in tasks)

        # Assume 6 productive hours per person per day
        productive_hours_per_day = team_size * 6

        # Add 20% buffer for coordination and unexpected issues
        duration_days = int((total_hours / productive_hours_per_day) * 1.2)

        return max(duration_days, 1)

    def _recommend_team_size(self, tasks: List[Task], timeline_weeks: int) -> int:
        """Recommend team size based on tasks and timeline."""
        total_hours = sum(task.estimated_hours for task in tasks)
        available_hours = timeline_weeks * 5 * 6  # 5 days/week * 6 hours/day

        # Calculate minimum team size needed
        min_team_size = max(1, int(total_hours / available_hours) + 1)

        return min(min_team_size, 8)  # Cap at 8 people
