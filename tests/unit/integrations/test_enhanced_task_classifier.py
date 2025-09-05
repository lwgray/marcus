"""
Unit tests for Enhanced Task Classifier.

Tests the robust task type identification system with expanded keywords,
pattern matching, and confidence scoring.
"""

from datetime import datetime

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.enhanced_task_classifier import (
    ClassificationResult,
    EnhancedTaskClassifier,
)
from src.integrations.nlp_task_utils import TaskType


class TestEnhancedTaskClassifier:
    """Test suite for EnhancedTaskClassifier"""

    @pytest.fixture
    def classifier(self):
        """Create an EnhancedTaskClassifier instance."""
        return EnhancedTaskClassifier()

    @pytest.fixture
    def base_task_data(self):
        """Base task data for creating test tasks."""
        return {
            "status": TaskStatus.TODO,
            "priority": Priority.MEDIUM,
            "assigned_to": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "due_date": None,
            "estimated_hours": 4.0,
            "dependencies": [],
            "labels": [],
        }

    def create_task(
        self,
        id: str,
        name: str,
        description: str = "",
        labels=None,
        base_task_data=None,
        **kwargs,
    ):
        """Helper to create a task with base data."""
        if base_task_data is None:
            base_data = {
                "status": TaskStatus.TODO,
                "priority": Priority.MEDIUM,
                "assigned_to": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "due_date": None,
                "estimated_hours": 4.0,
                "dependencies": [],
            }
        else:
            base_data = base_task_data.copy()

        # Update any kwargs into base_data
        base_data.update(kwargs)

        return Task(
            id=id, name=name, description=description, labels=labels or [], **base_data
        )

    # Design task tests
    @pytest.mark.parametrize(
        "name,description,expected_confidence",
        [
            (
                "Design authentication system",
                "Create flow diagrams and architecture",
                0.9,
            ),
            ("Plan database schema", "Define tables and relationships", 0.85),
            ("Create UI/UX mockups", "Design user interface wireframes", 0.9),
            ("Define API contracts", "Specify REST endpoint specifications", 0.85),
            ("Architect microservices structure", "Plan service boundaries", 0.9),
            ("Design workflow process", "Map out business process flow", 0.85),
            ("Outline system framework", "Create high-level architecture", 0.8),
            ("Model data structures", "Define domain models and entities", 0.85),
        ],
    )
    def test_design_task_identification(
        self, classifier, name, description, expected_confidence
    ):
        """Test identification of design tasks with various patterns."""
        task = self.create_task("1", name, description)
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.DESIGN
        assert result.confidence >= expected_confidence
        assert len(result.matched_keywords) > 0
        assert (
            "design" in result.reasoning.lower() or "plan" in result.reasoning.lower()
        )

    # Implementation task tests
    @pytest.mark.parametrize(
        "name,description,expected_confidence",
        [
            (
                "Implement user authentication",
                "Build login and registration endpoints",
                0.9,
            ),
            (
                "Create payment processing module",
                "Develop payment gateway integration",
                0.85,
            ),
            ("Build REST API endpoints", "Code CRUD operations for resources", 0.9),
            (
                "Add feature for user profiles",
                "Implement profile management functionality",
                0.85,
            ),
            ("Integrate third-party service", "Add support for external API", 0.85),
            ("Develop backend logic", "Write business logic for orders", 0.85),
            (
                "Setup database connections",
                "Configure and establish DB connections",
                0.65,
            ),
            (
                "Code algorithm for recommendations",
                "Implement recommendation engine",
                0.9,
            ),
        ],
    )
    def test_implementation_task_identification(
        self, classifier, name, description, expected_confidence
    ):
        """Test identification of implementation tasks."""
        task = self.create_task("1", name, description)
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.IMPLEMENTATION
        assert result.confidence >= expected_confidence
        assert len(result.matched_keywords) > 0

    # Testing task tests
    @pytest.mark.parametrize(
        "name,description,expected_confidence",
        [
            ("Write unit tests for auth service", "Test login and registration", 0.95),
            ("Test payment processing", "Verify payment gateway integration", 0.9),
            ("Create integration tests", "Test API endpoints end-to-end", 0.75),
            ("Add test coverage for user module", "Improve test coverage to 80%", 0.9),
            ("Verify API functionality", "Ensure endpoints work correctly", 0.85),
            ("Write e2e test scenarios", "Create end-to-end test suite", 0.95),
            ("Validate business logic", "Check order processing rules", 0.85),
            ("Test performance under load", "Run stress tests on API", 0.9),
        ],
    )
    def test_testing_task_identification(
        self, classifier, name, description, expected_confidence
    ):
        """Test identification of testing tasks."""
        task = self.create_task("1", name, description)
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.TESTING
        assert result.confidence >= expected_confidence
        assert len(result.matched_keywords) > 0

    # Documentation task tests
    @pytest.mark.parametrize(
        "name,description,expected_confidence",
        [
            ("Document API endpoints", "Write documentation for REST API", 0.95),
            ("Create user guide", "Write end-user documentation", 0.9),
            ("Update README", "Add installation and usage instructions", 0.9),
            ("Write developer documentation", "Document code architecture", 0.95),
            ("Add code comments", "Annotate complex functions", 0.65),
            ("Create tutorial for new feature", "Write step-by-step guide", 0.9),
            ("Document deployment process", "Write deployment instructions", 0.65),
            ("Maintain API reference", "Update API documentation", 0.9),
        ],
    )
    def test_documentation_task_identification(
        self, classifier, name, description, expected_confidence
    ):
        """Test identification of documentation tasks."""
        task = self.create_task("1", name, description)
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.DOCUMENTATION
        assert result.confidence >= expected_confidence
        assert len(result.matched_keywords) > 0

    # Pattern matching tests
    def test_pattern_matching_design(self, classifier):
        """Test pattern matching for design tasks."""
        task = self.create_task(
            "1", "Create the system architecture", "Define overall application design"
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.DESIGN
        assert len(result.matched_patterns) > 0
        assert result.confidence > 0.85

    def test_pattern_matching_implementation(self, classifier):
        """Test pattern matching for implementation tasks."""
        task = self.create_task(
            "1", "Add support for OAuth authentication", "Integrate OAuth2 provider"
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.IMPLEMENTATION
        assert len(result.matched_patterns) > 0

    def test_pattern_matching_testing(self, classifier):
        """Test pattern matching for testing tasks."""
        task = self.create_task(
            "1", "Write unit tests for user service", "Create comprehensive test suite"
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.TESTING
        assert len(result.matched_patterns) > 0
        assert "write.*tests" in result.matched_patterns[0].lower()

    # Edge cases and ambiguous tasks
    def test_ambiguous_task_design_wins(self, classifier):
        """Test task with multiple type indicators - design should win."""
        task = self.create_task(
            "1",
            "Design and implement user interface",
            "Create UI mockups and build components",
        )
        result = classifier.classify_with_confidence(task)

        # Design should win due to priority ordering
        assert result.task_type == TaskType.DESIGN
        assert result.confidence < 0.8  # Lower confidence due to ambiguity

    def test_task_with_labels(self, classifier):
        """Test that labels are considered in classification."""
        task = self.create_task(
            "1", "Create new feature", "Add functionality", labels=["testing", "qa"]
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.TESTING
        assert "testing" in result.matched_keywords

    def test_minimal_task_name_only(self, classifier):
        """Test classification with only task name."""
        task = self.create_task("1", "Test authentication")
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.TESTING
        assert result.confidence > 0.7

    def test_other_task_type(self, classifier):
        """Test task that doesn't match any type."""
        task = self.create_task("1", "Team meeting", "Discuss project status")
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.OTHER
        assert result.confidence == 0.0
        assert len(result.matched_keywords) == 0

    # Confidence scoring tests
    def test_high_confidence_with_multiple_indicators(self, classifier):
        """Test high confidence when multiple indicators present."""
        task = self.create_task(
            "1",
            "Design system architecture",
            "Plan and architect the application structure and create diagrams",
            labels=["design", "architecture"],
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.DESIGN
        assert result.confidence > 0.9
        assert len(result.matched_keywords) >= 3

    def test_low_confidence_with_conflicting_indicators(self, classifier):
        """Test low confidence with conflicting indicators."""
        task = self.create_task(
            "1", "Review implementation", "Check the code and test it"
        )
        result = classifier.classify_with_confidence(task)

        # Should classify as something but with lower confidence
        assert result.confidence < 0.7

    # Infrastructure and deployment tests
    def test_infrastructure_task_identification(self, classifier):
        """Test identification of infrastructure tasks."""
        task = self.create_task(
            "1", "Setup CI/CD pipeline", "Configure automated deployment"
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.INFRASTRUCTURE
        assert result.confidence > 0.8

    def test_deployment_task_identification(self, classifier):
        """Test identification of deployment tasks."""
        task = self.create_task(
            "1", "Deploy to production", "Release version 2.0 to live environment"
        )
        result = classifier.classify_with_confidence(task)

        assert result.task_type == TaskType.DEPLOYMENT
        assert result.confidence > 0.85

    # Suggestion tests
    def test_suggestions_for_unclear_task(self, classifier):
        """Test that suggestions are provided for unclear tasks."""
        task = self.create_task("1", "Team meeting", "Discuss project status")
        suggestions = classifier.get_suggestions(task)

        assert "improve_clarity" in suggestions
        assert len(suggestions["improve_clarity"]) > 0

    def test_no_suggestions_for_clear_task(self, classifier):
        """Test no suggestions for well-defined tasks."""
        task = self.create_task(
            "1", "Design authentication system", "Create detailed architecture for auth"
        )
        suggestions = classifier.get_suggestions(task)

        assert len(suggestions) == 0

    # Batch classification test
    def test_classify_multiple_tasks(self, classifier):
        """Test classifying multiple tasks maintains accuracy."""
        tasks = [
            self.create_task("1", "Design API structure"),
            self.create_task("2", "Implement user service"),
            self.create_task("3", "Write unit tests"),
            self.create_task("4", "Document API endpoints"),
            self.create_task("5", "Deploy to staging"),
            self.create_task("6", "Setup monitoring"),
        ]

        expected_types = [
            TaskType.DESIGN,
            TaskType.IMPLEMENTATION,
            TaskType.TESTING,
            TaskType.DOCUMENTATION,
            TaskType.DEPLOYMENT,
            TaskType.INFRASTRUCTURE,
        ]

        for task, expected_type in zip(tasks, expected_types):
            result = classifier.classify(task)
            assert result == expected_type

    # Real-world task examples
    @pytest.mark.parametrize(
        "name,expected_type",
        [
            ("Fix bug in login flow", TaskType.IMPLEMENTATION),
            ("Research authentication methods", TaskType.DESIGN),
            ("Performance test the API", TaskType.TESTING),
            ("Create onboarding tutorial", TaskType.DOCUMENTATION),
            ("Rollback production deployment", TaskType.DEPLOYMENT),
            ("Configure load balancer", TaskType.INFRASTRUCTURE),
            ("Refactor payment module", TaskType.IMPLEMENTATION),
            ("Define data model for orders", TaskType.DESIGN),
            ("Ensure GDPR compliance", TaskType.TESTING),
            ("Update changelog for v2.0", TaskType.DOCUMENTATION),
        ],
    )
    def test_real_world_examples(self, classifier, name, expected_type):
        """Test classification of real-world task examples."""
        task = self.create_task("1", name)
        result = classifier.classify(task)
        assert result == expected_type
