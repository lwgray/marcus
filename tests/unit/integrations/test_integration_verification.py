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
