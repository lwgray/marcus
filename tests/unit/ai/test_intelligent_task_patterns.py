"""
Unit tests for intelligent task pattern selection.

This module tests the ability to select appropriate task patterns based on:
1. Feature complexity (atomic, simple, coordinated, distributed)
2. Project complexity mode (prototype, standard, enterprise)
3. Presence of design artifacts requirement

As of issue #607 (step 3), test-task pairing has been rolled up: a separate
``Test {feature}`` task is no longer emitted. Instead the behaviors that must
be tested are captured as ``completion_criteria`` on the paired
``Implement {feature}`` task. TDD is enforced via the worker prompt as a
project-wide standard, and the runtime validator (``_validate_runtime``)
remains the enforcement gate that tests exist and pass.

Per the project's CLAUDE.md, all unit tests in tests/unit/ must carry the
``@pytest.mark.unit`` marker — otherwise they are skipped by ``pytest -m unit``
in CI. Markers have been added throughout this file.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser


class TestAtomicFeaturePatterns:
    """Test task pattern selection for atomic features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_atomic_generates_one_task_prototype(self, parser):
        """Test that atomic features generate 1 task in prototype mode."""
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
            "requires_design_artifacts": False,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.unit
    def test_atomic_generates_one_task_standard(self, parser):
        """Test that atomic features generate 1 task in standard mode."""
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.unit
    def test_atomic_generates_one_task_enterprise_no_separate_test(self, parser):
        """Atomic features in enterprise mode get only 1 task.

        Issue #607 step 3 — the paired ``Test {feature}`` task is rolled up
        into the implement task's completion_criteria; it is no longer a
        separate board task.
        """
        # Arrange
        requirement = {
            "id": "green_bg",
            "name": "Green Background",
            "complexity": "atomic",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert — only implementation; no separate test task
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)


class TestSimpleFeaturePatterns:
    """Test task pattern selection for simple features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_simple_generates_one_task_prototype(self, parser):
        """Test that simple features generate 1 task in prototype mode."""
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.unit
    def test_simple_generates_one_task_standard_no_separate_test(self, parser):
        """Simple features in standard mode now get only 1 task.

        Previously the standard pattern emitted ``Implement X`` + ``Test X``;
        after issue #607 step 3 the test behaviors live on the implement task.
        """
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_simple_generates_two_tasks_enterprise_design_plus_implement(self, parser):
        """Simple features in enterprise mode get design + implementation only."""
        # Arrange
        requirement = {
            "id": "score_display",
            "name": "Score Tracking",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert — design + implementation; the test task is rolled up
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)


class TestCoordinatedFeaturePatterns:
    """Test task pattern selection for coordinated features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_coordinated_generates_one_task_prototype(self, parser):
        """Coordinated features in prototype mode get only 1 task (implement)."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_coordinated_generates_two_tasks_standard(self, parser):
        """Coordinated features in standard mode get design + implementation."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_coordinated_generates_two_tasks_enterprise(self, parser):
        """Coordinated features in enterprise mode get design + implementation."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)


class TestDistributedFeaturePatterns:
    """Test task pattern selection for distributed features."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_distributed_generates_one_task_prototype(self, parser):
        """Distributed features in prototype mode get only 1 task."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_distributed_generates_two_tasks_standard(self, parser):
        """Distributed features in standard mode get design + implementation."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_distributed_generates_two_tasks_enterprise(self, parser):
        """Distributed features in enterprise mode get design + implementation."""
        # Arrange
        requirement = {
            "id": "microservices",
            "name": "Microservice Architecture",
            "complexity": "distributed",
            "requires_design_artifacts": True,
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)


class TestTaskIdGeneration:
    """Test that task IDs are generated correctly."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_task_ids_have_correct_format(self, parser):
        """Test that generated task IDs follow naming convention."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert — coordinated/standard now produces design + implement only
        assert tasks[0]["id"] == "task_user_auth_design"
        assert tasks[1]["id"] == "task_user_auth_implement"

    @pytest.mark.unit
    def test_task_names_include_feature_name(self, parser):
        """Test that generated task names include the feature name."""
        # Arrange
        requirement = {
            "id": "user_auth",
            "name": "User Authentication",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="standard")

        # Assert
        for task in tasks:
            assert "User Authentication" in task["name"]


class TestBreakDownEpicIntegration:
    """Test that _break_down_epic uses _select_task_pattern."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.fixture
    def mock_analysis(self):
        """Create mock PRDAnalysis."""
        return Mock(functional_requirements=[])

    @pytest.fixture
    def mock_constraints_standard(self):
        """Create mock constraints with standard mode."""
        constraints = Mock()
        constraints.quality_requirements = {"project_size": "standard"}
        constraints.complexity_mode = "standard"
        return constraints

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_break_down_epic_uses_complexity(
        self, parser, mock_analysis, mock_constraints_standard
    ):
        """Test that _break_down_epic respects complexity field."""
        # Arrange
        requirement = {
            "id": "atomic_feature",
            "name": "Atomic Feature",
            "complexity": "atomic",
            "priority": "high",
        }

        # Act
        tasks = await parser._break_down_epic(
            requirement, mock_analysis, mock_constraints_standard
        )

        # Assert
        assert len(tasks) == 1  # Atomic should only get 1 task in standard mode
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_break_down_epic_defaults_for_no_complexity_field(
        self, parser, mock_analysis, mock_constraints_standard
    ):
        """Backward compat: requirements without complexity still parse.

        After #607 step 3 the coordinated/standard pattern is design +
        implementation only (no separate test task).
        """
        # Arrange
        requirement = {
            "id": "old_feature",
            "name": "Old Feature Without Complexity",
            "priority": "high",
            # No complexity field (for backward compatibility)
        }

        # Act
        tasks = await parser._break_down_epic(
            requirement, mock_analysis, mock_constraints_standard
        )

        # Assert — defaults to coordinated → 2 tasks (design + implement)
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)


class TestComplexityModeEffects:
    """Test how complexity mode affects task generation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_prototype_simplifies_coordinated_features(self, parser):
        """Prototype mode reduces coordinated features to a single implement task."""
        # Arrange
        requirement = {
            "id": "complex_feature",
            "name": "Complex Feature",
            "complexity": "coordinated",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="prototype")

        # Assert — prototype skips design AND no separate test task
        assert len(tasks) == 1
        assert tasks[0]["type"] == "implementation"

    @pytest.mark.unit
    def test_enterprise_adds_design_to_simple_features(self, parser):
        """Enterprise mode adds design to simple features (no separate test task)."""
        # Arrange
        requirement = {
            "id": "simple_feature",
            "name": "Simple Feature",
            "complexity": "simple",
        }

        # Act
        tasks = parser._select_task_pattern(requirement, complexity_mode="enterprise")

        # Assert — design + implement; no testing task
        assert len(tasks) == 2
        assert tasks[0]["type"] == "design"
        assert tasks[1]["type"] == "implementation"
        assert all(t["type"] != "testing" for t in tasks)

    @pytest.mark.unit
    def test_standard_mode_uses_intelligent_patterns(self, parser):
        """Standard mode uses complexity-based patterns without test pairing."""
        # Arrange
        atomic_req = {"id": "atomic", "name": "Atomic", "complexity": "atomic"}
        simple_req = {"id": "simple", "name": "Simple", "complexity": "simple"}
        coordinated_req = {
            "id": "coordinated",
            "name": "Coordinated",
            "complexity": "coordinated",
        }

        # Act
        atomic_tasks = parser._select_task_pattern(
            atomic_req, complexity_mode="standard"
        )
        simple_tasks = parser._select_task_pattern(
            simple_req, complexity_mode="standard"
        )
        coordinated_tasks = parser._select_task_pattern(
            coordinated_req, complexity_mode="standard"
        )

        # Assert
        assert len(atomic_tasks) == 1  # Just implementation
        assert len(simple_tasks) == 1  # Just implementation (no test pair)
        assert len(coordinated_tasks) == 2  # Design + implementation


class TestNoTestTasksAcrossAllModes:
    """Issue #607 step 3: separate ``Test {feature}`` tasks are never emitted.

    The test behaviors that previously formed a separate testing task now live
    on the implement task as ``completion_criteria``. These tests guard the
    invariant: no path through ``_select_task_pattern`` produces a task whose
    ``type`` equals ``"testing"``.
    """

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "complexity_mode",
        ["prototype", "standard", "enterprise"],
    )
    @pytest.mark.parametrize(
        "complexity",
        ["atomic", "simple", "coordinated", "distributed"],
    )
    def test_no_testing_task_for_any_combination(
        self, parser, complexity_mode, complexity
    ):
        """No task pattern emits a ``testing`` task in any mode/complexity."""
        # Arrange
        requirement = {
            "id": f"feature_{complexity}",
            "name": f"Feature {complexity}",
            "complexity": complexity,
        }

        # Act
        tasks = parser._select_task_pattern(
            requirement, complexity_mode=complexity_mode
        )

        # Assert
        testing_tasks = [t for t in tasks if t["type"] == "testing"]
        assert testing_tasks == [], (
            f"Expected no testing tasks in mode={complexity_mode}, "
            f"complexity={complexity}; got {testing_tasks}"
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "complexity_mode",
        ["prototype", "standard", "enterprise"],
    )
    @pytest.mark.parametrize(
        "complexity",
        ["atomic", "simple", "coordinated", "distributed"],
    )
    def test_at_least_one_implementation_task_always_present(
        self, parser, complexity_mode, complexity
    ):
        """Every mode/complexity emits at least one implementation task.

        The implement task is the carrier for the rolled-up test behaviors
        via its ``completion_criteria``.
        """
        # Arrange
        requirement = {
            "id": f"feature_{complexity}",
            "name": f"Feature {complexity}",
            "complexity": complexity,
        }

        # Act
        tasks = parser._select_task_pattern(
            requirement, complexity_mode=complexity_mode
        )

        # Assert
        impl_tasks = [t for t in tasks if t["type"] == "implementation"]
        assert len(impl_tasks) == 1, (
            f"Expected exactly one implementation task in "
            f"mode={complexity_mode}, complexity={complexity}; got {impl_tasks}"
        )


class TestTestCoverageCriteriaGeneration:
    """Issue #607 step 3: the helper that derives test-coverage criteria.

    ``_generate_test_coverage_criteria`` produces the list of criterion
    strings that the implement task's ``completion_criteria`` field is
    populated with. The strings name *behaviors that must be tested*, not
    test framework or structure (those remain agent choices).
    """

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return AdvancedPRDParser()

    @pytest.mark.unit
    def test_returns_non_empty_list_of_strings(self, parser):
        """Helper returns a non-empty list of string criteria."""
        # Act
        criteria = parser._generate_test_coverage_criteria(
            feature_name="User Login",
            base_description="Users can log in with email and password.",
        )

        # Assert
        assert isinstance(criteria, list)
        assert len(criteria) >= 1
        assert all(isinstance(c, str) and c.strip() for c in criteria)

    @pytest.mark.unit
    def test_criteria_mention_feature_name(self, parser):
        """Generated criteria reference the feature so they read sensibly."""
        # Act
        criteria = parser._generate_test_coverage_criteria(
            feature_name="Mark Complete",
            base_description="Toggle a todo item's done flag.",
        )

        # Assert — at least one criterion contains the feature name (any case)
        flat = " ".join(criteria).lower()
        assert "mark complete" in flat

    @pytest.mark.unit
    def test_criteria_name_behaviors_not_implementation_how(self, parser):
        """Criteria describe what to test, not how to test (no framework names)."""
        # Act
        criteria = parser._generate_test_coverage_criteria(
            feature_name="User Login",
            base_description="Users can log in.",
        )

        # Assert — no implementation prescription leaks in
        joined = " ".join(criteria).lower()
        forbidden_hows = ["pytest", "unittest", "jest", "mocha", "rspec"]
        for token in forbidden_hows:
            assert token not in joined, (
                f"Criterion accidentally prescribes framework '{token}': " f"{criteria}"
            )

    @pytest.mark.unit
    def test_criteria_include_happy_path_and_invalid_input(self, parser):
        """Default criteria cover both happy path and invalid input behaviors."""
        # Act
        criteria = parser._generate_test_coverage_criteria(
            feature_name="Create Todo",
            base_description="Create a new todo with a title.",
        )

        # Assert — must hint at both success and error paths
        joined = " ".join(criteria).lower()
        # Heuristic: at least one criterion references valid/normal/happy
        # AND at least one references invalid/error/edge.
        has_happy = any(kw in joined for kw in ["valid", "happy", "normal", "success"])
        has_unhappy = any(kw in joined for kw in ["invalid", "error", "edge", "fail"])
        assert has_happy, f"No happy-path criterion found: {criteria}"
        assert has_unhappy, f"No error/edge criterion found: {criteria}"


class TestImplementTaskCompletionCriteriaIntegration:
    """End-to-end: ``_generate_detailed_task`` populates ``completion_criteria``.

    Issue #607 step 3 — the integration check: a requirement that flows
    through ``_select_task_pattern`` → ``_generate_detailed_task`` ends up
    with an implement task whose ``completion_criteria`` carries the
    test-behavior strings.  Design tasks must NOT receive
    ``completion_criteria`` (they're not implement tasks).
    """

    @pytest.fixture
    def parser(self):
        """Parser with LLM patched out to return a canned description."""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            mock_llm = Mock()
            mock_llm.analyze = AsyncMock(
                return_value="Implement the feature per the requirement."
            )
            mock_llm_class.return_value = mock_llm
            p = AdvancedPRDParser()
            p.llm_client = mock_llm
            return p

    @pytest.fixture
    def analysis(self):
        """Minimal PRDAnalysis-shaped object with one functional requirement.

        Uses ``SimpleNamespace`` rather than ``Mock`` because the parser
        reads ``analysis.__dict__`` directly when stuffing source_context,
        and a real ``__dict__`` is much cleaner than fighting with
        ``Mock``'s auto-attribute behavior.
        """
        from types import SimpleNamespace

        return SimpleNamespace(
            functional_requirements=[
                {
                    "id": "user_login",
                    "name": "User Login",
                    "description": "Users can log in with email and password.",
                }
            ],
            non_functional_requirements=[],
            technical_constraints=[],
            original_description="A simple todo app.",
        )

    @pytest.fixture
    def constraints(self):
        """Minimal ProjectConstraints-shaped object."""
        from types import SimpleNamespace

        return SimpleNamespace(
            team_size=1,
            technical_constraints=[],
            quality_requirements={},
            complexity_mode="standard",
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_implement_task_gets_completion_criteria_populated(
        self, parser, analysis, constraints
    ):
        """The implement task carries test-coverage criteria as a list of strings."""
        # Arrange — pre-populate _task_metadata as _generate_task_hierarchy would.
        parser._task_metadata = {
            "task_user_login_implement": {
                "original_name": "Implement User Login",
                "type": "implementation",
                "epic_id": "epic_user_login",
                "requirement": analysis.functional_requirements[0],
            }
        }

        # Act
        task = await parser._generate_detailed_task(
            task_id="task_user_login_implement",
            epic_id="epic_user_login",
            analysis=analysis,
            constraints=constraints,
            sequence=1,
        )

        # Assert
        assert (
            task.completion_criteria is not None
        ), "implement tasks must carry completion_criteria after #607 step 3"
        assert isinstance(task.completion_criteria, list)
        assert len(task.completion_criteria) >= 1
        # Live shape is list-of-strings, honored by WorkAnalyzer._extract_criteria
        # and by sqlite_kanban JSON serialization.
        assert all(isinstance(c, str) for c in task.completion_criteria)
        # The criteria reference the feature being implemented.
        flat = " ".join(task.completion_criteria).lower()
        assert "user login" in flat

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_design_task_does_not_get_completion_criteria(
        self, parser, analysis, constraints
    ):
        """Design tasks have no completion_criteria — only implement tasks do."""
        # Arrange
        parser._task_metadata = {
            "task_user_login_design": {
                "original_name": "Design User Login",
                "type": "design",
                "epic_id": "epic_user_login",
                "requirement": analysis.functional_requirements[0],
            }
        }

        # Act
        task = await parser._generate_detailed_task(
            task_id="task_user_login_design",
            epic_id="epic_user_login",
            analysis=analysis,
            constraints=constraints,
            sequence=1,
        )

        # Assert
        assert (
            task.completion_criteria is None
        ), "design tasks must NOT receive completion_criteria (only implement)"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_infrastructure_task_does_not_get_completion_criteria(
        self, parser, constraints
    ):
        """Infrastructure tasks must not inherit test-coverage criteria.

        Regression guard for Codex P1 on PR #608: ``_extract_task_type``
        falls back to ``"implement"`` when a task_id contains no
        design/implement/test substring (e.g. ``"infra_setup"``,
        ``"infra_ci_cd"``). Without canonical-type gating, those tasks
        would receive happy-path / invalid-input criteria they have no
        business carrying. The gate must consult ``_task_metadata`` and
        only emit criteria when the canonical type equals
        ``TASK_TYPE_IMPLEMENTATION``.
        """
        # Arrange — infra task_id with no design/implement/test substring,
        # canonical type stamped as "infrastructure" in _task_metadata.
        from types import SimpleNamespace

        infra_analysis = SimpleNamespace(
            functional_requirements=[],
            non_functional_requirements=[],
            technical_constraints=[],
            original_description="Project setup.",
        )
        parser._task_metadata = {
            "infra_setup": {
                "original_name": "Project Setup",
                "type": "infrastructure",
                "epic_id": "epic_infrastructure",
                "description": "Configure project tooling.",
            }
        }

        # Act
        task = await parser._generate_detailed_task(
            task_id="infra_setup",
            epic_id="epic_infrastructure",
            analysis=infra_analysis,
            constraints=constraints,
            sequence=1,
        )

        # Assert
        assert task.completion_criteria is None, (
            "infrastructure tasks must NOT receive test-coverage criteria "
            "even though _extract_task_type defaults 'infra_setup' to "
            "'implement' (Codex P1 on #608)"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_nfr_task_does_not_get_completion_criteria(self, parser, constraints):
        """NFR tasks must not inherit per-feature test-coverage criteria.

        Non-functional requirements (performance, security, accessibility)
        are different in kind from feature implementations and their
        validation criteria are NFR-specific, not happy-path/invalid-input.
        Same Codex P1 regression class as the infrastructure case.
        """
        # Arrange
        from types import SimpleNamespace

        nfr_analysis = SimpleNamespace(
            functional_requirements=[],
            non_functional_requirements=[
                {
                    "id": "performance_requirement",
                    "name": "Performance Requirement",
                    "description": "API responds within 200ms.",
                }
            ],
            technical_constraints=[],
            original_description="A todo app with performance budget.",
        )
        parser._task_metadata = {
            "nfr_performance_requirement": {
                "original_name": "Performance Requirement",
                "type": "nfr",
                "epic_id": "epic_non_functional",
                "description": "API responds within 200ms.",
            }
        }

        # Act
        task = await parser._generate_detailed_task(
            task_id="nfr_performance_requirement",
            epic_id="epic_non_functional",
            analysis=nfr_analysis,
            constraints=constraints,
            sequence=1,
        )

        # Assert
        assert task.completion_criteria is None, (
            "NFR tasks must NOT receive feature-style test-coverage "
            "criteria (Codex P1 on #608)"
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_implement_task_without_metadata_does_not_get_criteria(
        self, parser, analysis, constraints
    ):
        """Defensive: task_id resembles an implement but metadata is missing.

        A task whose ID syntactically contains ``"implement"`` but whose
        canonical type is absent from ``_task_metadata`` should not
        receive criteria — the gate is strict: canonical metadata must
        affirmatively declare ``TASK_TYPE_IMPLEMENTATION``. This guards
        against future code paths that emit implement-looking IDs
        without the metadata stamp.
        """
        # Arrange — no metadata entry; just functional req that matches.
        parser._task_metadata = {}

        # Act
        task = await parser._generate_detailed_task(
            task_id="task_user_login_implement",
            epic_id="epic_user_login",
            analysis=analysis,
            constraints=constraints,
            sequence=1,
        )

        # Assert
        assert task.completion_criteria is None, (
            "implement-looking task_id without TASK_TYPE_IMPLEMENTATION "
            "metadata must not receive criteria — gate is canonical, not "
            "substring-based"
        )
