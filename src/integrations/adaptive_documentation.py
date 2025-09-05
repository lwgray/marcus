"""
Adaptive Documentation Generator for Marcus

Provides context-aware documentation task generation that adapts to different
project sources and work types. Supports evolution from project creation to
pre-defined tasks and GitHub issue fixing.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from src.core.models import Priority, Task, TaskStatus
from src.integrations.documentation_tasks import DocumentationTaskGenerator

logger = logging.getLogger(__name__)


class DocumentationType(Enum):
    """Types of documentation that can be generated."""

    PROJECT_SUCCESS = "project_success"
    BUG_FIX_REPORT = "bug_fix_report"
    FEATURE_UPDATE = "feature_update"
    MODIFICATION_SUMMARY = "modification_summary"
    API_CHANGES = "api_changes"
    MIGRATION_GUIDE = "migration_guide"


@dataclass
class DocumentationContext:
    """Context for documentation generation decisions."""

    source_type: str  # "nlp_project", "predefined_tasks", "github_issue"
    work_type: str  # "new_system", "modification", "bug_fix", "feature_add"
    project_name: str
    existing_tasks: List[Task]
    completed_work: List[Task]
    feature_labels: Set[str]  # Feature labels to apply to doc tasks
    metadata: Dict[str, Any]


class AdaptiveDocumentationGenerator:
    """
    Generates documentation tasks adapted to the context of work performed.

    This generator supports multiple documentation strategies:
    - Project-level documentation for new systems
    - Feature-specific documentation for additions
    - Fix reports for bug corrections
    - Update summaries for modifications
    """

    def __init__(self) -> None:
        """Initialize the adaptive documentation generator."""
        self.legacy_generator = DocumentationTaskGenerator()

    def create_documentation_tasks(self, context: DocumentationContext) -> List[Task]:
        """
        Create appropriate documentation tasks based on context.

        Args:
            context: Documentation context including source type and work performed

        Returns:
            List of documentation tasks appropriate for the context
        """
        doc_tasks = []

        # Analyze what type of documentation is needed
        doc_types = self._determine_documentation_types(context)

        for doc_type in doc_types:
            task = self._create_documentation_task(doc_type, context)
            if task:
                doc_tasks.append(task)

        logger.info(
            f"Generated {len(doc_tasks)} documentation tasks for "
            f"{context.source_type}/{context.work_type}"
        )

        return doc_tasks

    def _determine_documentation_types(
        self, context: DocumentationContext
    ) -> List[DocumentationType]:
        """Determine which types of documentation are needed."""
        doc_types = []

        # For new projects from natural language
        if context.source_type == "nlp_project" and context.work_type == "new_system":
            doc_types.append(DocumentationType.PROJECT_SUCCESS)

        # For bug fixes (future: GitHub issues)
        elif context.source_type == "github_issue" and context.work_type == "bug_fix":
            doc_types.append(DocumentationType.BUG_FIX_REPORT)

        # For feature additions
        elif context.work_type == "feature_add":
            doc_types.append(DocumentationType.FEATURE_UPDATE)
            # Also add to project docs if significant
            if self._is_significant_feature(context):
                doc_types.append(DocumentationType.PROJECT_SUCCESS)

        # For modifications to existing code
        elif context.work_type == "modification":
            doc_types.append(DocumentationType.MODIFICATION_SUMMARY)
            # Add API docs if API changed
            if self._has_api_changes(context):
                doc_types.append(DocumentationType.API_CHANGES)

        # Default fallback
        elif not doc_types:
            # Determine based on work analysis
            if self._created_new_system(context):
                doc_types.append(DocumentationType.PROJECT_SUCCESS)
            else:
                doc_types.append(DocumentationType.MODIFICATION_SUMMARY)

        return doc_types

    def _create_documentation_task(
        self, doc_type: DocumentationType, context: DocumentationContext
    ) -> Optional[Task]:
        """Create a specific documentation task."""

        # Get template for documentation type
        template = self._get_documentation_template(doc_type)

        # Find dependencies
        dependencies = self._find_documentation_dependencies(context, doc_type)

        # Build task
        task_id = f"doc_{doc_type.value}_{uuid.uuid4().hex[:8]}"

        # Prepare labels - include feature labels for proper phase enforcement
        labels = ["documentation", doc_type.value]
        if context.feature_labels:
            labels.extend(context.feature_labels)

        task = Task(
            id=task_id,
            name=template["name"].format(project_name=context.project_name),
            description=self._generate_description(doc_type, context),
            status=TaskStatus.TODO,
            priority=self._determine_priority(doc_type, context),
            labels=labels,
            dependencies=dependencies,
            estimated_hours=template.get("estimated_hours", 4.0),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            assigned_to=None,
            due_date=None,
        )

        return task

    def _get_documentation_template(
        self, doc_type: DocumentationType
    ) -> Dict[str, Any]:
        """Get template for documentation type."""
        templates = {
            DocumentationType.PROJECT_SUCCESS: {
                "name": "Create {project_name} PROJECT_SUCCESS documentation",
                "estimated_hours": 4.0,
                "priority": Priority.HIGH,
            },
            DocumentationType.BUG_FIX_REPORT: {
                "name": "Document fix for {project_name}",
                "estimated_hours": 2.0,
                "priority": Priority.MEDIUM,
            },
            DocumentationType.FEATURE_UPDATE: {
                "name": "Document {project_name} feature implementation",
                "estimated_hours": 3.0,
                "priority": Priority.MEDIUM,
            },
            DocumentationType.MODIFICATION_SUMMARY: {
                "name": "Create modification summary for {project_name}",
                "estimated_hours": 2.0,
                "priority": Priority.LOW,
            },
            DocumentationType.API_CHANGES: {
                "name": "Update API documentation for {project_name}",
                "estimated_hours": 3.0,
                "priority": Priority.HIGH,
            },
            DocumentationType.MIGRATION_GUIDE: {
                "name": "Create migration guide for {project_name}",
                "estimated_hours": 3.0,
                "priority": Priority.HIGH,
            },
        }

        return templates.get(doc_type, templates[DocumentationType.PROJECT_SUCCESS])

    def _generate_description(
        self, doc_type: DocumentationType, context: DocumentationContext
    ) -> str:
        """Generate appropriate description for documentation type."""

        if doc_type == DocumentationType.PROJECT_SUCCESS:
            # Use legacy generator for PROJECT_SUCCESS
            return DocumentationTaskGenerator._generate_documentation_description(
                has_tests=any("test" in t.name.lower() for t in context.completed_work),
                has_deployment=any(
                    "deploy" in t.name.lower() for t in context.completed_work
                ),
            )

        elif doc_type == DocumentationType.BUG_FIX_REPORT:
            return """Create comprehensive bug fix documentation:

1. **Bug Description**:
   - What was the issue?
   - How did it manifest?
   - What was the impact?

2. **Root Cause Analysis**:
   - Why did the bug occur?
   - What was the underlying problem?

3. **Fix Implementation**:
   - How was it fixed?
   - What changes were made?
   - Code snippets of key changes

4. **Testing**:
   - Test cases added
   - How to verify the fix
   - Regression test coverage

5. **Prevention**:
   - How to prevent similar issues
   - Lessons learned
"""

        elif doc_type == DocumentationType.FEATURE_UPDATE:
            return """Document the new feature implementation:

1. **Feature Overview**:
   - What does the feature do?
   - Why was it added?
   - User benefits

2. **Technical Implementation**:
   - Architecture decisions
   - Key components
   - Integration points

3. **Usage Guide**:
   - How to use the feature
   - Configuration options
   - Examples

4. **API Reference** (if applicable):
   - New endpoints/methods
   - Parameters and responses
   - Error handling
"""

        else:
            return "Document the changes made to the system."

    def _find_documentation_dependencies(
        self, context: DocumentationContext, doc_type: DocumentationType
    ) -> List[str]:
        """Find appropriate dependencies for documentation task."""
        dependencies = []

        # For PROJECT_SUCCESS, depend on all major implementation and test tasks
        if doc_type == DocumentationType.PROJECT_SUCCESS:
            for task in context.existing_tasks:
                if any(
                    label in task.labels
                    for label in [
                        "type:feature",
                        "type:testing",
                        "type:deployment",
                        "component:backend",
                        "component:frontend",
                        "component:api",
                    ]
                ) and task.priority in [Priority.HIGH, Priority.URGENT]:
                    dependencies.append(task.id)

        # For bug fixes, depend on fix implementation and testing
        elif doc_type == DocumentationType.BUG_FIX_REPORT:
            for task in context.existing_tasks:
                if "fix" in task.name.lower() or "test" in task.name.lower():
                    dependencies.append(task.id)

        # For feature updates, depend on feature implementation
        else:
            # Depend on completed work items
            for task in context.completed_work:
                dependencies.append(task.id)

        return dependencies

    def _determine_priority(
        self, doc_type: DocumentationType, context: DocumentationContext
    ) -> Priority:
        """Determine priority for documentation task."""
        template = self._get_documentation_template(doc_type)
        priority = template.get("priority", Priority.MEDIUM)
        # Ensure we return a Priority enum value
        if isinstance(priority, Priority):
            return priority
        return Priority.MEDIUM

    def _is_significant_feature(self, context: DocumentationContext) -> bool:
        """Check if a feature is significant enough for project docs update."""
        # Features with more than 3 tasks are considered significant
        feature_task_count = len(
            [
                t
                for t in context.existing_tasks
                if context.feature_labels & set(t.labels or [])
            ]
        )
        return feature_task_count > 3

    def _has_api_changes(self, context: DocumentationContext) -> bool:
        """Check if work includes API changes."""
        api_keywords = ["api", "endpoint", "route", "rest", "graphql"]
        for task in context.completed_work:
            if any(keyword in task.name.lower() for keyword in api_keywords):
                return True
        return False

    def _created_new_system(self, context: DocumentationContext) -> bool:
        """Check if work created a new system."""
        # If more than 10 tasks and includes setup/infrastructure
        if len(context.existing_tasks) < 10:
            return False

        has_setup = any(
            "setup" in t.name.lower() or "infrastructure" in t.name.lower()
            for t in context.existing_tasks
        )
        has_implementation = any(
            "implement" in t.name.lower() or "build" in t.name.lower()
            for t in context.existing_tasks
        )

        return has_setup and has_implementation

    def should_add_documentation(self, context: DocumentationContext) -> bool:
        """
        Determine if documentation tasks should be added.

        Similar to legacy should_add_documentation_task but context-aware.
        """
        # Skip for tiny projects
        if len(context.existing_tasks) < 3:
            return False

        # Skip for prototypes/experiments (unless from GitHub issue)
        if context.source_type != "github_issue":
            skip_keywords = [
                "prototype",
                "poc",
                "proof of concept",
                "demo",
                "experiment",
                "test",
            ]
            project_lower = context.project_name.lower()
            if any(keyword in project_lower for keyword in skip_keywords):
                return False

        return True


def create_documentation_context(
    tasks: List[Task],
    project_name: str,
    source_type: str = "nlp_project",
    metadata: Optional[Dict[str, Any]] = None,
) -> DocumentationContext:
    """
    Helper to create DocumentationContext from existing data.

    Args:
        tasks: All project tasks
        project_name: Name of the project
        source_type: Source of tasks (nlp_project, github_issue, etc)
        metadata: Additional context metadata

    Returns:
        DocumentationContext configured for the project
    """
    # Analyze work type
    work_type = "new_system"  # Default

    # Extract feature labels from tasks
    feature_labels = set()
    for task in tasks:
        if task.labels:
            # Look for feature-specific labels
            for label in task.labels:
                if (
                    label.startswith("feature:")
                    or label.startswith("component:")
                    or label in ["backend", "frontend", "api", "database"]
                ):
                    feature_labels.add(label)

    # Completed work (for now, empty - will be populated during execution)
    completed_work = [t for t in tasks if t.status == TaskStatus.DONE]

    return DocumentationContext(
        source_type=source_type,
        work_type=work_type,
        project_name=project_name,
        existing_tasks=tasks,
        completed_work=completed_work,
        feature_labels=feature_labels,
        metadata=metadata or {},
    )
