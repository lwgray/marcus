"""Template Library for Marcus Creator Mode.

Provides project templates to prevent illogical task assignments like
"Deploy to production" before any code exists.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from src.core.models import Priority


class ProjectSize(Enum):
    """Project size categories."""

    MVP = "mvp"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


@dataclass
class TaskTemplate:
    """Template for a single task."""

    name: str
    description: str
    phase: str
    estimated_hours: int
    priority: Priority = Priority.MEDIUM
    labels: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)  # Task names this depends on
    optional: bool = False
    conditions: Dict[str, Any] = field(default_factory=dict)  # When to include


@dataclass
class PhaseTemplate:
    """Template for a project phase."""

    name: str
    description: str
    order: int
    tasks: List[TaskTemplate]

    def get_required_tasks(self) -> List[TaskTemplate]:
        """Get only required tasks."""
        return [t for t in self.tasks if not t.optional]


@dataclass
class ProjectTemplate:
    """Base class for project templates."""

    name: str
    description: str
    category: str
    phases: List[PhaseTemplate]
    default_size: ProjectSize = ProjectSize.MEDIUM

    def get_all_tasks(self, size: Optional[ProjectSize] = None) -> List[TaskTemplate]:
        """Get all tasks adjusted for project size."""
        tasks = []
        target_size = size if size is not None else self.default_size

        for phase in self.phases:
            for task in phase.tasks:
                # Skip optional tasks for MVP
                if target_size == ProjectSize.MVP and task.optional:
                    continue

                # Adjust estimates based on size
                adjusted_task = self._adjust_task_for_size(task, target_size)
                tasks.append(adjusted_task)

        return tasks

    def _adjust_task_for_size(
        self, task: TaskTemplate, size: ProjectSize
    ) -> TaskTemplate:
        """Adjust task estimates based on project size."""
        size_multipliers = {
            ProjectSize.MVP: 0.5,
            ProjectSize.SMALL: 0.7,
            ProjectSize.MEDIUM: 1.0,
            ProjectSize.LARGE: 1.5,
            ProjectSize.ENTERPRISE: 2.0,
        }

        multiplier = size_multipliers.get(size, 1.0)

        # Create adjusted task
        adjusted = TaskTemplate(
            name=task.name,
            description=task.description,
            phase=task.phase,
            estimated_hours=int(task.estimated_hours * multiplier),
            priority=task.priority,
            labels=task.labels.copy(),
            dependencies=task.dependencies.copy(),
            optional=task.optional,
            conditions=task.conditions.copy(),
        )

        # Add size label
        adjusted.labels.append(f"size:{size.value}")

        return adjusted


class WebAppTemplate(ProjectTemplate):
    """Template for full-stack web applications."""

    def __init__(self) -> None:
        phases = [
            PhaseTemplate(
                name="Setup",
                description="Project initialization and setup",
                order=1,
                tasks=[
                    TaskTemplate(
                        name="Initialize repository",
                        description="Create Git repository and initial commit",
                        phase="setup",
                        estimated_hours=1,
                        priority=Priority.HIGH,
                        labels=["setup", "git"],
                    ),
                    TaskTemplate(
                        name="Set up development environment",
                        description="Configure development tools, linters, and IDE",
                        phase="setup",
                        estimated_hours=2,
                        priority=Priority.HIGH,
                        labels=["setup", "dev-env"],
                        dependencies=["Initialize repository"],
                    ),
                    TaskTemplate(
                        name="Configure build tools",
                        description="Set up webpack/vite, TypeScript, and build pipeline",
                        phase="setup",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["setup", "build"],
                        dependencies=["Set up development environment"],
                    ),
                    TaskTemplate(
                        name="Set up CI/CD pipeline",
                        description="Configure GitHub Actions or similar for automated testing",
                        phase="setup",
                        estimated_hours=4,
                        priority=Priority.MEDIUM,
                        labels=["setup", "ci-cd"],
                        dependencies=["Configure build tools"],
                        optional=True,
                    ),
                ],
            ),
            PhaseTemplate(
                name="Design",
                description="Architecture and database design",
                order=2,
                tasks=[
                    TaskTemplate(
                        name="Design system architecture",
                        description="Create high-level architecture diagram and tech stack decisions",
                        phase="design",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["design", "architecture"],
                        dependencies=["Set up development environment"],
                    ),
                    TaskTemplate(
                        name="Design database schema",
                        description="Create database schema with tables, relationships, and indexes",
                        phase="design",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["design", "database"],
                        dependencies=["Design system architecture"],
                    ),
                    TaskTemplate(
                        name="Design API structure",
                        description="Define RESTful API endpoints and data contracts",
                        phase="design",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["design", "api"],
                        dependencies=["Design database schema"],
                    ),
                    TaskTemplate(
                        name="Create UI mockups",
                        description="Design user interface mockups and user flow",
                        phase="design",
                        estimated_hours=8,
                        priority=Priority.MEDIUM,
                        labels=["design", "ui"],
                        optional=True,
                    ),
                ],
            ),
            PhaseTemplate(
                name="Backend Development",
                description="Server-side implementation",
                order=3,
                tasks=[
                    TaskTemplate(
                        name="Set up backend framework",
                        description="Initialize Express/FastAPI/Django with basic configuration",
                        phase="backend",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["backend", "setup"],
                        dependencies=["Design API structure"],
                    ),
                    TaskTemplate(
                        name="Implement database models",
                        description="Create ORM models based on schema design",
                        phase="backend",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["backend", "database"],
                        dependencies=[
                            "Set up backend framework",
                            "Design database schema",
                        ],
                    ),
                    TaskTemplate(
                        name="Implement authentication",
                        description="Add user registration, login, and JWT token handling",
                        phase="backend",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["backend", "auth"],
                        dependencies=["Implement database models"],
                    ),
                    TaskTemplate(
                        name="Create CRUD API endpoints",
                        description="Implement Create, Read, Update, Delete operations for main entities",
                        phase="backend",
                        estimated_hours=12,
                        priority=Priority.HIGH,
                        labels=["backend", "api"],
                        dependencies=[
                            "Implement database models",
                            "Implement authentication",
                        ],
                    ),
                    TaskTemplate(
                        name="Add API validation",
                        description="Implement request validation and error handling",
                        phase="backend",
                        estimated_hours=4,
                        priority=Priority.MEDIUM,
                        labels=["backend", "validation"],
                        dependencies=["Create CRUD API endpoints"],
                    ),
                    TaskTemplate(
                        name="Implement business logic",
                        description="Add domain-specific business rules and workflows",
                        phase="backend",
                        estimated_hours=16,
                        priority=Priority.HIGH,
                        labels=["backend", "business-logic"],
                        dependencies=["Create CRUD API endpoints"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Frontend Development",
                description="Client-side implementation",
                order=4,
                tasks=[
                    TaskTemplate(
                        name="Set up frontend framework",
                        description="Initialize React/Vue/Angular with routing",
                        phase="frontend",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["frontend", "setup"],
                        dependencies=["Configure build tools"],
                    ),
                    TaskTemplate(
                        name="Create component library",
                        description="Build reusable UI components (buttons, forms, etc)",
                        phase="frontend",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["frontend", "components"],
                        dependencies=["Set up frontend framework"],
                    ),
                    TaskTemplate(
                        name="Implement authentication UI",
                        description="Create login, register, and auth flow pages",
                        phase="frontend",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["frontend", "auth"],
                        dependencies=[
                            "Create component library",
                            "Implement authentication",
                        ],
                    ),
                    TaskTemplate(
                        name="Build main application views",
                        description="Implement core application pages and navigation",
                        phase="frontend",
                        estimated_hours=16,
                        priority=Priority.HIGH,
                        labels=["frontend", "views"],
                        dependencies=[
                            "Create component library",
                            "Create CRUD API endpoints",
                        ],
                    ),
                    TaskTemplate(
                        name="Add state management",
                        description="Implement Redux/Vuex/MobX for application state",
                        phase="frontend",
                        estimated_hours=6,
                        priority=Priority.MEDIUM,
                        labels=["frontend", "state"],
                        dependencies=["Build main application views"],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Implement responsive design",
                        description="Ensure UI works on mobile and tablet devices",
                        phase="frontend",
                        estimated_hours=8,
                        priority=Priority.MEDIUM,
                        labels=["frontend", "responsive"],
                        dependencies=["Build main application views"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Testing",
                description="Quality assurance and testing",
                order=5,
                tasks=[
                    TaskTemplate(
                        name="Write unit tests for backend",
                        description="Test models, services, and API endpoints",
                        phase="testing",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["testing", "backend"],
                        dependencies=["Implement business logic"],
                    ),
                    TaskTemplate(
                        name="Write unit tests for frontend",
                        description="Test components and utilities",
                        phase="testing",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["testing", "frontend"],
                        dependencies=["Build main application views"],
                    ),
                    TaskTemplate(
                        name="Create integration tests",
                        description="Test API integration and data flow",
                        phase="testing",
                        estimated_hours=6,
                        priority=Priority.MEDIUM,
                        labels=["testing", "integration"],
                        dependencies=[
                            "Write unit tests for backend",
                            "Write unit tests for frontend",
                        ],
                    ),
                    TaskTemplate(
                        name="Perform manual testing",
                        description="Manual QA of all features and edge cases",
                        phase="testing",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["testing", "qa"],
                        dependencies=["Build main application views"],
                    ),
                    TaskTemplate(
                        name="Fix identified bugs",
                        description="Address issues found during testing",
                        phase="testing",
                        estimated_hours=12,
                        priority=Priority.HIGH,
                        labels=["testing", "bugfix"],
                        dependencies=["Perform manual testing"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Deployment",
                description="Production deployment and launch",
                order=6,
                tasks=[
                    TaskTemplate(
                        name="Set up production infrastructure",
                        description="Configure servers, databases, and CDN",
                        phase="deployment",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["deployment", "infrastructure"],
                        dependencies=["Fix identified bugs"],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Configure environment variables",
                        description="Set up production configs and secrets",
                        phase="deployment",
                        estimated_hours=2,
                        priority=Priority.HIGH,
                        labels=["deployment", "config"],
                        dependencies=["Set up production infrastructure"],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Set up monitoring and logging",
                        description="Configure error tracking and performance monitoring",
                        phase="deployment",
                        estimated_hours=4,
                        priority=Priority.MEDIUM,
                        labels=["deployment", "monitoring"],
                        dependencies=["Set up production infrastructure"],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Deploy to production",
                        description="Deploy application to production environment",
                        phase="deployment",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["deployment", "release"],
                        dependencies=[
                            "Configure environment variables",
                            "Set up monitoring and logging",
                        ],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Perform production smoke tests",
                        description="Verify all features work in production",
                        phase="deployment",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["deployment", "testing"],
                        dependencies=["Deploy to production"],
                        optional=True,
                    ),
                ],
            ),
        ]

        super().__init__(
            name="Full-Stack Web Application",
            description="Complete web application with frontend, backend, and database",
            category="web",
            phases=phases,
        )


class APIServiceTemplate(ProjectTemplate):
    """Template for API-only services."""

    def __init__(self) -> None:
        phases = [
            PhaseTemplate(
                name="Setup",
                description="Service initialization",
                order=1,
                tasks=[
                    TaskTemplate(
                        name="Initialize repository",
                        description="Create Git repository with .gitignore and README",
                        phase="setup",
                        estimated_hours=1,
                        priority=Priority.HIGH,
                        labels=["setup", "git"],
                    ),
                    TaskTemplate(
                        name="Set up API framework",
                        description="Initialize FastAPI/Express with basic structure",
                        phase="setup",
                        estimated_hours=2,
                        priority=Priority.HIGH,
                        labels=["setup", "api"],
                        dependencies=["Initialize repository"],
                    ),
                    TaskTemplate(
                        name="Configure development environment",
                        description="Set up Docker, environment variables, and hot reload",
                        phase="setup",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["setup", "dev-env"],
                        dependencies=["Set up API framework"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Design",
                description="API design and planning",
                order=2,
                tasks=[
                    TaskTemplate(
                        name="Design API schema",
                        description="Create OpenAPI/Swagger specification",
                        phase="design",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["design", "api"],
                        dependencies=["Set up API framework"],
                    ),
                    TaskTemplate(
                        name="Design data models",
                        description="Define data structures and validation rules",
                        phase="design",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["design", "models"],
                        dependencies=["Design API schema"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Implementation",
                description="Core API implementation",
                order=3,
                tasks=[
                    TaskTemplate(
                        name="Implement data models",
                        description="Create Pydantic/TypeScript models with validation",
                        phase="implementation",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["backend", "models"],
                        dependencies=["Design data models"],
                    ),
                    TaskTemplate(
                        name="Create API endpoints",
                        description="Implement all API routes with proper HTTP methods",
                        phase="implementation",
                        estimated_hours=12,
                        priority=Priority.HIGH,
                        labels=["backend", "api"],
                        dependencies=["Implement data models"],
                    ),
                    TaskTemplate(
                        name="Add authentication",
                        description="Implement API key or OAuth authentication",
                        phase="implementation",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["backend", "auth"],
                        dependencies=["Create API endpoints"],
                    ),
                    TaskTemplate(
                        name="Implement rate limiting",
                        description="Add rate limiting to prevent abuse",
                        phase="implementation",
                        estimated_hours=3,
                        priority=Priority.MEDIUM,
                        labels=["backend", "security"],
                        dependencies=["Create API endpoints"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Testing & Documentation",
                description="Testing and documentation",
                order=4,
                tasks=[
                    TaskTemplate(
                        name="Write API tests",
                        description="Create comprehensive test suite for all endpoints",
                        phase="testing",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["testing", "api"],
                        dependencies=["Add authentication"],
                    ),
                    TaskTemplate(
                        name="Generate API documentation",
                        description="Auto-generate and customize API docs",
                        phase="testing",
                        estimated_hours=3,
                        priority=Priority.MEDIUM,
                        labels=["documentation", "api"],
                        dependencies=["Create API endpoints"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Deployment",
                description="API deployment",
                order=5,
                tasks=[
                    TaskTemplate(
                        name="Containerize application",
                        description="Create production Docker image",
                        phase="deployment",
                        estimated_hours=3,
                        priority=Priority.HIGH,
                        labels=["deployment", "docker"],
                        dependencies=["Write API tests"],
                    ),
                    TaskTemplate(
                        name="Deploy to cloud",
                        description="Deploy to AWS/GCP/Azure with auto-scaling",
                        phase="deployment",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["deployment", "cloud"],
                        dependencies=["Containerize application"],
                    ),
                ],
            ),
        ]

        super().__init__(
            name="API Service",
            description="RESTful API service without frontend",
            category="api",
            phases=phases,
        )


class MobileAppTemplate(ProjectTemplate):
    """Template for mobile applications."""

    def __init__(self) -> None:
        phases = [
            PhaseTemplate(
                name="Setup",
                description="Mobile app initialization",
                order=1,
                tasks=[
                    TaskTemplate(
                        name="Initialize mobile project",
                        description="Set up React Native/Flutter/Native project",
                        phase="setup",
                        estimated_hours=2,
                        priority=Priority.HIGH,
                        labels=["setup", "mobile"],
                    ),
                    TaskTemplate(
                        name="Configure development environment",
                        description="Set up emulators, devices, and debugging tools",
                        phase="setup",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["setup", "dev-env"],
                        dependencies=["Initialize mobile project"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Core Features",
                description="Essential mobile features",
                order=2,
                tasks=[
                    TaskTemplate(
                        name="Implement navigation",
                        description="Set up app navigation and routing",
                        phase="features",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["mobile", "navigation"],
                        dependencies=["Configure development environment"],
                    ),
                    TaskTemplate(
                        name="Create UI screens",
                        description="Build main application screens",
                        phase="features",
                        estimated_hours=16,
                        priority=Priority.HIGH,
                        labels=["mobile", "ui"],
                        dependencies=["Implement navigation"],
                    ),
                    TaskTemplate(
                        name="Add offline support",
                        description="Implement local storage and sync",
                        phase="features",
                        estimated_hours=8,
                        priority=Priority.MEDIUM,
                        labels=["mobile", "offline"],
                        dependencies=["Create UI screens"],
                        optional=True,
                    ),
                    TaskTemplate(
                        name="Implement push notifications",
                        description="Add push notification support",
                        phase="features",
                        estimated_hours=6,
                        priority=Priority.MEDIUM,
                        labels=["mobile", "notifications"],
                        dependencies=["Create UI screens"],
                        optional=True,
                    ),
                ],
            ),
            PhaseTemplate(
                name="Platform Integration",
                description="Native platform features",
                order=3,
                tasks=[
                    TaskTemplate(
                        name="Integrate device features",
                        description="Camera, GPS, contacts as needed",
                        phase="platform",
                        estimated_hours=8,
                        priority=Priority.MEDIUM,
                        labels=["mobile", "native"],
                        dependencies=["Create UI screens"],
                    ),
                    TaskTemplate(
                        name="Handle platform differences",
                        description="iOS and Android specific adjustments",
                        phase="platform",
                        estimated_hours=6,
                        priority=Priority.HIGH,
                        labels=["mobile", "platform"],
                        dependencies=["Create UI screens"],
                    ),
                ],
            ),
            PhaseTemplate(
                name="Testing & Release",
                description="Mobile app testing and store release",
                order=4,
                tasks=[
                    TaskTemplate(
                        name="Test on real devices",
                        description="Test on various devices and OS versions",
                        phase="release",
                        estimated_hours=8,
                        priority=Priority.HIGH,
                        labels=["mobile", "testing"],
                        dependencies=["Handle platform differences"],
                    ),
                    TaskTemplate(
                        name="Prepare store listings",
                        description="Create app store descriptions and screenshots",
                        phase="release",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["mobile", "store"],
                        dependencies=["Test on real devices"],
                    ),
                    TaskTemplate(
                        name="Submit to app stores",
                        description="Submit to Apple App Store and Google Play",
                        phase="release",
                        estimated_hours=4,
                        priority=Priority.HIGH,
                        labels=["mobile", "deployment"],
                        dependencies=["Prepare store listings"],
                    ),
                ],
            ),
        ]

        super().__init__(
            name="Mobile Application",
            description="Native or cross-platform mobile app",
            category="mobile",
            phases=phases,
        )
