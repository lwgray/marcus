"""
Unit tests for Integration Verification Task Generator.

Tests the integration verification phase that runs after implementation
completes to verify the project actually builds, starts, and works.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.nlp_task_utils import TaskType

pytestmark = pytest.mark.unit


def create_test_task(
    task_id: str,
    name: str,
    labels: list[str] | None = None,
    priority: Priority = Priority.HIGH,
    status: TaskStatus = TaskStatus.TODO,
    dependencies: list[str] | None = None,
) -> Task:
    """Create a test task with sensible defaults."""
    return Task(
        id=task_id,
        name=name,
        description=f"Description for {name}",
        status=status,
        priority=priority,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=4.0,
        labels=labels or [],
        dependencies=dependencies or [],
    )


@pytest.fixture
def sample_implementation_tasks() -> list[Task]:
    """Create sample implementation tasks for testing.

    Uses realistic AI-generated labels (not hardcoded type:feature).
    The classifier detects implementation from the task name.
    """
    return [
        create_test_task(
            "impl-001",
            "Build weather widget",
            labels=["implement", "frontend"],
        ),
        create_test_task(
            "impl-002",
            "Build clock widget",
            labels=["implement", "frontend"],
        ),
    ]


@pytest.fixture
def sample_testing_tasks() -> list[Task]:
    """Create sample testing tasks for testing."""
    return [
        create_test_task(
            "test-001",
            "Write widget tests",
            labels=["testing"],
        ),
    ]


@pytest.fixture
def sample_design_tasks() -> list[Task]:
    """Create sample design tasks for testing."""
    return [
        create_test_task(
            "design-001",
            "Design dashboard architecture",
            labels=["design"],
        ),
    ]


@pytest.fixture
def all_sample_tasks(
    sample_design_tasks: list[Task],
    sample_implementation_tasks: list[Task],
    sample_testing_tasks: list[Task],
) -> list[Task]:
    """Combine all sample tasks."""
    return sample_design_tasks + sample_implementation_tasks + sample_testing_tasks


class TestIntegrationTaskGenerator:
    """Test suite for IntegrationTaskGenerator."""

    def test_creates_task_with_correct_dependencies(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Test integration task depends on all impl and test tasks."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        # Should depend on design, impl, and test tasks
        assert "design-001" in task.dependencies
        assert "impl-001" in task.dependencies
        assert "impl-002" in task.dependencies
        assert "test-001" in task.dependencies

    def test_no_task_when_no_implementation_tasks(self) -> None:
        """Test returns None when no implementation tasks exist."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        design_only = [
            create_test_task(
                "design-001",
                "Design system",
                labels=["type:design"],
            ),
        ]
        task = IntegrationTaskGenerator.create_integration_task(design_only, "Project")

        assert task is None

    def test_task_labels_correct(self, all_sample_tasks: list[Task]) -> None:
        """Test integration task has correct labels."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        assert "integration" in task.labels
        assert "verification" in task.labels
        assert "type:integration" in task.labels

    def test_task_priority_urgent(self, all_sample_tasks: list[Task]) -> None:
        """Test integration task has URGENT priority."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        assert task.priority == Priority.URGENT

    def test_task_description_includes_verification_steps(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Test task description includes key verification instructions."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        desc = task.description
        # Should mention key verification steps
        assert "build" in desc.lower()
        assert "start" in desc.lower()
        assert "verify" in desc.lower()
        assert "integration_verification.json" in desc
        assert "log_artifact" in desc

    def test_description_includes_config_doc_verification(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Description instructs agent to cross-check documented config values against source.

        Prevents 'specification theater': agents documenting configuration keys
        or env vars from a spec without verifying they are actually wired in
        code. Applies to any project type, not just web apps.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        desc = task.description
        # Must mention configuration / env var checking …
        assert "configuration" in desc.lower() or "env" in desc.lower()
        # … and include at least one concrete search pattern for common stacks
        assert any(
            pattern in desc
            for pattern in ["import.meta.env", "os.environ", "process.env"]
        )
        # … and the concept of phantom / unused values
        assert "phantom" in desc.lower() or "never used" in desc.lower()

    def test_description_includes_interface_doc_verification(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Description instructs agent to verify documented interfaces have implementations.

        General language covers all project types: web services (endpoints),
        CLIs (commands), libraries (functions), data pipelines (stages), etc.
        Dead documentation should be removed or implemented.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        desc = task.description
        # Must mention documentation accuracy in general terms …
        assert "documented" in desc.lower() or "documentation" in desc.lower()
        # … with project-type examples that span beyond just web APIs
        assert "implementation" in desc.lower() or "implement" in desc.lower()
        # … and cover multiple project type examples
        assert (
            "cli" in desc.lower()
            or "library" in desc.lower()
            or "pipeline" in desc.lower()
        )

    def test_task_id_format(self, all_sample_tasks: list[Task]) -> None:
        """Test integration task ID starts with correct prefix."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        assert task.id.startswith("integration_verify_")

    def test_acceptance_criteria_set(self, all_sample_tasks: list[Task]) -> None:
        """Test integration task has meaningful acceptance criteria."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        assert task.acceptance_criteria is not None
        assert len(task.acceptance_criteria) > 0

    def test_task_status_is_todo(self, all_sample_tasks: list[Task]) -> None:
        """Test integration task starts in TODO status."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "Dashboard"
        )

        assert task is not None
        assert task.status == TaskStatus.TODO

    def test_task_name_includes_project_name(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Test integration task name includes the project name."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            all_sample_tasks, "My Dashboard"
        )

        assert task is not None
        assert "My Dashboard" in task.name

    def test_works_with_generic_ai_labels(self) -> None:
        """Test integration task created with generic labels.

        AI-generated tasks often have simple labels like 'implement'
        instead of 'type:feature'. The classifier should still detect
        them as implementation tasks.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        tasks = [
            create_test_task(
                "t1",
                "Design the system",
                labels=["design"],
            ),
            create_test_task(
                "t2",
                "Build the backend API",
                labels=["implement", "backend"],
            ),
            create_test_task(
                "t3",
                "Build the frontend UI",
                labels=["frontend"],
            ),
        ]

        task = IntegrationTaskGenerator.create_integration_task(tasks, "Dashboard")

        assert task is not None, (
            "Integration task should be created even with generic "
            "AI-generated labels (not type:feature)"
        )


class TestEnhanceProjectWithIntegration:
    """Test suite for enhance_project_with_integration function."""

    def test_adds_integration_task_to_task_list(
        self, all_sample_tasks: list[Task]
    ) -> None:
        """Test that integration task is added to task list."""
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            all_sample_tasks, "Build a dashboard app", "Dashboard"
        )

        assert len(result) == len(all_sample_tasks) + 1
        integration_tasks = [t for t in result if "integration" in t.labels]
        assert len(integration_tasks) == 1

    def test_skips_poc_projects(self, all_sample_tasks: list[Task]) -> None:
        """Test that POC projects don't get integration tasks."""
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            all_sample_tasks, "Build a poc dashboard", "Dashboard"
        )

        assert len(result) == len(all_sample_tasks)

    def test_skips_demo_projects(self, all_sample_tasks: list[Task]) -> None:
        """Test that demo projects don't get integration tasks."""
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            all_sample_tasks, "Build a demo app", "Dashboard"
        )

        assert len(result) == len(all_sample_tasks)

    def test_documentation_depends_on_integration(self) -> None:
        """Test doc task includes integration task in dependencies."""
        from src.integrations.documentation_tasks import (
            DocumentationTaskGenerator,
        )
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        # Use type:feature labels so DocumentationTaskGenerator
        # also recognizes them (it still uses hardcoded labels)
        tasks_with_typed_labels = [
            create_test_task(
                "design-001",
                "Design dashboard architecture",
                labels=["type:design"],
            ),
            create_test_task(
                "impl-001",
                "Build weather widget",
                labels=["type:feature", "component:frontend"],
            ),
            create_test_task(
                "test-001",
                "Write widget tests",
                labels=["type:testing"],
            ),
        ]

        # First add integration task
        tasks_with_integration = enhance_project_with_integration(
            tasks_with_typed_labels,
            "Build a dashboard app",
            "Dashboard",
        )

        # Find the integration task
        integration_task = next(
            t for t in tasks_with_integration if "integration" in t.labels
        )

        # Now create documentation task from the updated list
        doc_task = DocumentationTaskGenerator.create_documentation_task(
            tasks_with_integration, "Dashboard"
        )

        assert doc_task is not None
        assert integration_task.id in doc_task.dependencies

    def test_returns_unchanged_when_no_impl_tasks(self) -> None:
        """Test returns original tasks when no impl tasks exist."""
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        design_only = [
            create_test_task(
                "design-001",
                "Design system",
                labels=["type:design"],
            ),
        ]
        result = enhance_project_with_integration(
            design_only, "Build a system", "System"
        )

        assert len(result) == len(design_only)


class TestIntegrationTaskContractFile:
    """
    GH-320 PR 2: Integration task names the contract file when
    contract-first decomposition is active.

    The integration agent must treat the contract as authoritative:
    fix implementations that diverge, never edit the contract to
    match a broken implementation. Without this instruction in the
    task description, the integration agent could silently "fix" a
    mismatch by editing the contract, breaking the invariant that
    made contract-first decomposition work.
    """

    def test_integration_task_includes_contract_preamble_when_set(
        self, sample_implementation_tasks: list[Task]
    ) -> None:
        """contract_file set → task description includes preamble."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            sample_implementation_tasks,
            project_name="Snake Game",
            contract_file="docs/api/types.ts",
        )

        assert task is not None
        assert "CONTRACT-FIRST PROJECT" in task.description
        assert "docs/api/types.ts" in task.description

    def test_integration_task_preamble_forbids_contract_modification(
        self, sample_implementation_tasks: list[Task]
    ) -> None:
        """
        Preamble must instruct the agent NOT to modify the contract.

        This is the load-bearing invariant. If an integration agent
        can silently edit the contract to match a broken
        implementation, contract-first decomposition breaks for
        all future runs.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            sample_implementation_tasks,
            project_name="Snake Game",
            contract_file="docs/api/types.ts",
        )

        assert task is not None
        description_lower = task.description.lower()
        assert "fix the implementation" in description_lower
        assert "do not modify the contract" in description_lower or (
            "do not" in description_lower and "contract" in description_lower
        )

    def test_integration_task_no_preamble_when_contract_file_none(
        self, sample_implementation_tasks: list[Task]
    ) -> None:
        """Feature-based path (contract_file=None) → no preamble."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        task = IntegrationTaskGenerator.create_integration_task(
            sample_implementation_tasks,
            project_name="Dashboard",
            contract_file=None,
        )

        assert task is not None
        assert "CONTRACT-FIRST PROJECT" not in task.description

    def test_enhance_project_with_integration_passes_contract_file(
        self, sample_implementation_tasks: list[Task]
    ) -> None:
        """
        enhance_project_with_integration forwards contract_file to the
        integration task description.
        """
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            sample_implementation_tasks,
            project_description="Build a snake game",
            project_name="Snake Game",
            contract_file="docs/api/snake-types.ts",
        )

        integration_tasks = [t for t in result if "type:integration" in t.labels]
        assert len(integration_tasks) == 1
        assert "docs/api/snake-types.ts" in integration_tasks[0].description
        assert "CONTRACT-FIRST PROJECT" in integration_tasks[0].description

    def test_enhance_project_with_integration_default_no_contract(
        self, sample_implementation_tasks: list[Task]
    ) -> None:
        """
        Backward-compat: callers that don't pass contract_file get the
        unchanged (non-contract-first) integration task.
        """
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            sample_implementation_tasks,
            project_description="Build a dashboard",
            project_name="Dashboard",
        )

        integration_tasks = [t for t in result if "type:integration" in t.labels]
        assert len(integration_tasks) == 1
        assert "CONTRACT-FIRST PROJECT" not in integration_tasks[0].description


class TestPhaseEnumUpdates:
    """Test that INTEGRATION is properly added to phase enums."""

    def test_integration_phase_exists(self) -> None:
        """Test TaskPhase.INTEGRATION exists."""
        from src.core.phase_dependency_enforcer import TaskPhase

        assert hasattr(TaskPhase, "INTEGRATION")

    def test_integration_phase_between_testing_and_documentation(
        self,
    ) -> None:
        """Test INTEGRATION phase is ordered between TESTING and DOCS."""
        from src.core.phase_dependency_enforcer import TaskPhase

        assert TaskPhase.TESTING.value < TaskPhase.INTEGRATION.value
        assert TaskPhase.INTEGRATION.value < TaskPhase.DOCUMENTATION.value

    def test_integration_type_exists(self) -> None:
        """Test TaskType.INTEGRATION exists."""
        assert hasattr(TaskType, "INTEGRATION")
        assert TaskType.INTEGRATION.value == "integration"

    def test_type_to_phase_mapping(self) -> None:
        """Test TaskType.INTEGRATION maps to TaskPhase.INTEGRATION."""
        from src.core.phase_dependency_enforcer import (
            PhaseDependencyEnforcer,
            TaskPhase,
        )

        mapping = PhaseDependencyEnforcer.TYPE_TO_PHASE_MAP
        assert TaskType.INTEGRATION in mapping
        assert mapping[TaskType.INTEGRATION] == TaskPhase.INTEGRATION

    def test_integration_in_phase_order(self) -> None:
        """Test INTEGRATION is in PHASE_ORDER list."""
        from src.core.phase_dependency_enforcer import (
            PhaseDependencyEnforcer,
            TaskPhase,
        )

        assert TaskPhase.INTEGRATION in PhaseDependencyEnforcer.PHASE_ORDER
        # Should be after TESTING and before DOCUMENTATION
        order = PhaseDependencyEnforcer.PHASE_ORDER
        testing_idx = order.index(TaskPhase.TESTING)
        integration_idx = order.index(TaskPhase.INTEGRATION)
        doc_idx = order.index(TaskPhase.DOCUMENTATION)
        assert testing_idx < integration_idx < doc_idx


class TestIntegrationTaskClassification:
    """Test that integration tasks are classified correctly."""

    def test_classify_integration_verification_task(self) -> None:
        """Test task with 'integration verification' is classified."""
        from src.integrations.enhanced_task_classifier import (
            EnhancedTaskClassifier,
        )

        classifier = EnhancedTaskClassifier()
        task = create_test_task(
            "int-001",
            "Integration verification for Dashboard",
            labels=["integration", "verification"],
        )

        result = classifier.classify(task)
        assert result == TaskType.INTEGRATION

    def test_classify_build_verification_task(self) -> None:
        """Test task with 'build verification' is classified."""
        from src.integrations.enhanced_task_classifier import (
            EnhancedTaskClassifier,
        )

        classifier = EnhancedTaskClassifier()
        task = create_test_task(
            "int-002",
            "Build verification and smoke test",
            labels=["integration"],
        )

        result = classifier.classify(task)
        assert result == TaskType.INTEGRATION

    def test_integration_not_confused_with_testing(self) -> None:
        """Test 'Write integration tests' classifies as TESTING."""
        from src.integrations.enhanced_task_classifier import (
            EnhancedTaskClassifier,
        )

        classifier = EnhancedTaskClassifier()
        task = create_test_task(
            "test-002",
            "Write integration tests for API",
            labels=["type:testing"],
        )

        result = classifier.classify(task)
        # Should be TESTING, not INTEGRATION
        assert result == TaskType.TESTING


class TestShouldAddIntegrationTask:
    """Test the should_add_integration_task decision logic."""

    def test_normal_project_gets_integration(self) -> None:
        """Test normal projects get integration verification."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build an e-commerce platform"
        )

    def test_poc_skips_integration(self) -> None:
        """Test POC projects skip integration verification."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Build a poc to test the idea"
        )

    def test_proof_of_concept_skips_integration(self) -> None:
        """Test proof of concept projects skip integration."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Proof of concept for new API"
        )

    def test_demo_skips_integration(self) -> None:
        """Test demo projects skip integration verification."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Create a demo for the team"
        )

    def test_experiment_gets_integration(self) -> None:
        """Test experiment projects DO get integration verification.

        Regression test for GH-320 PR 1. Previously the keyword
        "experiment" was in the skip list, which meant Marcus's own
        multi-agent experiments never exercised integration verification
        and we could not measure whether integration verification was
        catching the bugs contract-first decomposition introduces.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Experiment with new rendering"
        )

    def test_test_project_still_skips_integration(self) -> None:
        """Test projects with 'test' in the description still skip.

        Complements ``test_experiment_gets_integration``: we only
        removed "experiment" from the skip list, not "test". Projects
        literally named "test this thing" are still POC-like and
        should not get the integration phase.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Quick test of the new encoder"
        )

    def test_description_mentioning_test_suite_still_gets_integration(
        self,
    ) -> None:
        """
        Descriptions that mention a 'test suite' as a requirement
        must NOT be classified as POC projects.

        Regression test for the substring-match bug: the original
        implementation used ``"test" in description_lower`` which
        fired on any compound containing "test" — including the
        word "test suite" — and silently suppressed the integration
        verification task for real projects whose descriptions
        happened to mention testing infrastructure.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build a dashboard web app with a comprehensive test suite"
        )

    def test_description_with_unit_tests_still_gets_integration(self) -> None:
        """'Unit tests' is not a POC indicator."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build an auth service with unit tests and integration tests"
        )

    def test_description_with_test_driven_still_gets_integration(self) -> None:
        """'Test-driven development' is not a POC indicator."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Use test-driven development to build a REST API"
        )

    def test_description_with_latest_still_gets_integration(self) -> None:
        """Word boundary: 'latest' must not match 'test'."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build an app using the latest React version"
        )

    def test_description_with_contest_still_gets_integration(self) -> None:
        """Word boundary: 'contest' must not match 'test'."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build a contest voting platform for community events"
        )

    def test_description_with_testing_framework_still_gets_integration(
        self,
    ) -> None:
        """'Testing framework' is infrastructure, not POC intent."""
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert IntegrationTaskGenerator.should_add_integration_task(
            "Build a testing framework for browser automation"
        )

    def test_plural_pocs_skip_integration(self) -> None:
        """
        Regression test for Codex P1 on PR #333: the word-boundary
        regex must match plural ``pocs`` as well as singular ``poc``.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Build POCs to evaluate different approaches"
        )

    def test_plural_demos_skip_integration(self) -> None:
        """
        Regression test for Codex P1 on PR #333: the word-boundary
        regex must match plural ``demos`` as well as singular
        ``demo``.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Create demos for the stakeholder presentation"
        )

    def test_plural_proof_of_concepts_skip_integration(self) -> None:
        """
        Regression test for Codex P1 on PR #333: the word-boundary
        regex must match ``proof of concepts`` as well as the
        singular ``proof of concept``.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        assert not IntegrationTaskGenerator.should_add_integration_task(
            "Proof of concepts for three candidate architectures"
        )


class TestIntegrationTaskFunctionalRequirements:
    """
    Test that functional requirements are attached to the integration
    task as acceptance criteria (GH-320 task #64).

    The integration agent already verifies the merged product — giving
    it the full requirements list means it checks whether user intent
    was realized, even if no individual impl task carries a specific
    verb. This was the gap in Experiment 4 v2 where both agents built
    API plumbing but no UI because no task carried "display" forward
    and the integration agent had no reference back to the user's ask.
    """

    @pytest.fixture
    def sample_tasks(self) -> list[Task]:
        """Two implementation tasks for a dashboard project."""
        return [
            create_test_task(
                "t1",
                "Implement WeatherWidget",
                labels=["contract_first", "implementation"],
            ),
            create_test_task(
                "t2",
                "Implement TimeWidget",
                labels=["contract_first", "implementation"],
            ),
        ]

    def test_requirements_appended_to_acceptance_criteria(
        self, sample_tasks: list[Task]
    ) -> None:
        """
        When functional_requirements are provided, each requirement's
        name must appear in the integration task's acceptance_criteria.
        """
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        requirements = [
            {"id": "f1", "name": "Display current weather temperature"},
            {"id": "f2", "name": "Display current time with timezone"},
        ]

        result = enhance_project_with_integration(
            sample_tasks,
            "Build a dashboard",
            "Dashboard",
            functional_requirements=requirements,
        )

        integration_task = next((t for t in result if "integration" in t.labels), None)
        assert integration_task is not None, "Integration task not created"

        for req in requirements:
            assert any(
                req["name"] in criterion
                for criterion in integration_task.acceptance_criteria
            ), (
                f"Requirement {req['name']!r} not found in "
                f"acceptance_criteria: {integration_task.acceptance_criteria}"
            )

    def test_no_requirements_preserves_default_criteria(
        self, sample_tasks: list[Task]
    ) -> None:
        """
        When no functional_requirements are provided (feature-based
        path), the integration task keeps its default acceptance
        criteria unchanged.
        """
        from src.integrations.integration_verification import (
            enhance_project_with_integration,
        )

        result = enhance_project_with_integration(
            sample_tasks,
            "Build a dashboard",
            "Dashboard",
        )

        integration_task = next((t for t in result if "integration" in t.labels), None)
        assert integration_task is not None
        # Default criteria include "Tests run with full terminal output"
        assert any("Tests run" in c for c in integration_task.acceptance_criteria)
        # No requirement-specific criteria
        assert not any("Display" in c for c in integration_task.acceptance_criteria)


class TestStartCommandBuildPipelineRequirement:
    """
    Integration verification prompt must require the agent's declared
    start_command to exercise the build pipeline, not merely the test
    suite.

    Regression for dashboard-v73: agent_unicorn_1 declared
    ``start_command='cd worktrees/agent_unicorn_1 && npm test'`` for
    the integration verification task. The smoke gate ran vitest in
    the worktree and it passed in <1s — but vitest never invokes the
    build pipeline. Had the React app been missing public/index.html
    (the v71 failure shape), npm test would still pass while
    npm run build would fail. The prompt now teaches the agent that
    a passing test suite does not prove the deliverable can be built
    and started, and requires start_command to exercise the build
    pipeline (chain build + test if both apply).

    Tool-agnostic by design: the prompt names the *contract* (must
    exercise the build pipeline) without naming any specific tool.
    Marcus stays platform-agnostic; the agent picks the right
    command for their stack.
    """

    def test_prompt_requires_start_command_to_exercise_build_pipeline(self) -> None:
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        prompt = IntegrationTaskGenerator._generate_integration_description(
            project_name="dashboard-v74"
        )

        # The contract must appear verbatim — this is the v73-class fix
        assert "exercise the build pipeline" in prompt

    def test_prompt_explains_why_test_suite_is_not_enough(self) -> None:
        """
        The prompt must explain WHY a passing test suite isn't
        sufficient evidence the deliverable works. Without the
        explanation the agent will rationalize that "tests pass =
        product works" and re-fall into v73.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        prompt = IntegrationTaskGenerator._generate_integration_description(
            project_name="dashboard-v74"
        )

        # Must address the "tests pass therefore product works" fallacy
        assert "test suite does not prove" in prompt

    def test_prompt_is_tool_agnostic(self) -> None:
        """
        The contract sentence must not pin any specific stack. Tool
        names (npm, vite, tsc, pip, cargo, go, mvn, etc.) may appear
        in worked examples elsewhere in the prompt, but the contract
        sentence itself must describe the requirement abstractly.
        Marcus is a coordination layer for ALL agent work, not just
        software dev — stack-specific contract language regresses
        toward the "software bias" failure mode that pre-#347 had.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        prompt = IntegrationTaskGenerator._generate_integration_description(
            project_name="dashboard-v74"
        )

        # Find the "must exercise the build pipeline" sentence and
        # verify the SENTENCE itself contains no stack-specific tokens.
        # Locate the contract sentence
        idx = prompt.find("must exercise the build pipeline")
        assert idx >= 0
        # Take a window of ~400 chars around the contract sentence
        # to sanity-check the surrounding language
        window = prompt[idx : idx + 400].lower()
        # The contract sentence should be tool-agnostic — none of
        # these stack names should appear in the window
        forbidden_in_contract = [
            " npm ",
            " vite ",
            " tsc ",
            " pip ",
            " cargo ",
            " maven ",
            " gradle ",
            " webpack ",
        ]
        for tok in forbidden_in_contract:
            assert tok not in window, (
                f"Build-pipeline contract sentence must be "
                f"tool-agnostic; found {tok!r} in:\n\n{window}"
            )

    def test_prompt_forbids_shell_chains_in_start_command(self) -> None:
        """
        The prompt must explicitly tell agents that start_command is
        a single subprocess invocation, not a shell script.

        Codex P1 on PR #351: Marcus's product_smoke runner uses
        asyncio.create_subprocess_exec(*shlex.split(...)), which does
        NOT interpret shell operators. && / || / | / cd / $(...) are
        passed as literal arguments and produce confusing failures
        (or worse, vacuous passes — on macOS /usr/bin/cd is a real
        no-op binary that returns exit 0 for any args, so
        `cd ... && X` silently false-passes the smoke gate). Until
        the runner is fixed (#125), the prompt must steer agents
        away from shell chains and toward a single binary invocation.
        """
        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        prompt = IntegrationTaskGenerator._generate_integration_description(
            project_name="dashboard-v74"
        )

        prompt_lower = prompt.lower()
        # Must explicitly state that start_command is a single command
        assert "single command" in prompt_lower or "single subprocess" in prompt_lower
        # Must call out shell operators by name so the agent
        # recognizes the trap
        assert "&&" in prompt
        # Must offer the wrapper-script escape hatch for cases that
        # genuinely need to combine steps
        assert "wrapper" in prompt_lower

    def test_prompt_examples_contain_no_shell_chains(self) -> None:
        """
        All ``start_command`` example strings in the prompt must be
        single-command invocations. Pre-existing examples used shell
        chains (``test -d docs && test -f README.md``) which would
        not work under Marcus's exec-based runner. The fix is to
        replace them with single binary invocations and steer
        chained needs toward wrapper scripts.

        Detection strategy: find every quoted ``start_command="..."``
        substring in the prompt and assert none contain ``&&``.
        """
        import re

        from src.integrations.integration_verification import (
            IntegrationTaskGenerator,
        )

        prompt = IntegrationTaskGenerator._generate_integration_description(
            project_name="dashboard-v74"
        )

        # Find every start_command="..." example string
        examples = re.findall(r'start_command="([^"]*)"', prompt)
        assert examples, "Prompt should still have start_command examples"
        for example in examples:
            assert "&&" not in example, (
                f"start_command example contains a shell chain that "
                f"will not work under Marcus's exec-based runner: "
                f"{example!r}. Replace with a single command or a "
                f"wrapper script."
            )
            assert "||" not in example
            # `cd` as the first token is the v73 vacuous-pass trap
            # on macOS where /usr/bin/cd exists as a no-op stub
            tokens = example.split()
            if tokens:
                assert tokens[0] != "cd", (
                    f"start_command example begins with 'cd' which is "
                    f"a vacuous-pass trap on macOS (/usr/bin/cd returns "
                    f"exit 0 for any args). Use the worktree's actual "
                    f"build command instead."
                )
