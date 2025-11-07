"""
Unit tests for AdvancedPRDParser error handling

Tests error scenarios in PRD analysis with all external dependencies mocked.
Verifies proper Marcus Error Framework integration and fallback removal.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser, ProjectConstraints
from src.core.error_framework import AIProviderError


class TestAdvancedPRDParserErrorHandling:
    """Test suite for AdvancedPRDParser error handling"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing AI provider failures"""
        mock_client = Mock()
        mock_client.analyze = AsyncMock()
        return mock_client

    @pytest.fixture
    def mock_dependency_inferer(self):
        """Mock dependency inferer"""
        mock_inferer = Mock()
        mock_inferer.infer_dependencies = AsyncMock()
        return mock_inferer

    @pytest.fixture
    def parser(self, mock_llm_client, mock_dependency_inferer):
        """Create AdvancedPRDParser with mocked dependencies"""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_client
            with patch(
                "src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"
            ) as mock_dep_class:
                mock_dep_class.return_value = mock_dependency_inferer
                parser = AdvancedPRDParser()
                parser.llm_client = mock_llm_client  # Ensure our mock is used
                return parser

    @pytest.fixture
    def sample_prd_content(self):
        """Sample PRD content for testing"""
        return "Create a todo application with user authentication and task management features."

    @pytest.fixture
    def sample_constraints(self):
        """Sample project constraints"""
        return ProjectConstraints(
            team_size=3,
            available_skills=["Python", "React"],
            technology_constraints=["REST API", "PostgreSQL"],
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_provider_connection_failure_raises_proper_error(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test AI provider connection failure raises AIProviderError with proper context"""
        # Arrange
        connection_error = ConnectionError("Unable to connect to AI provider")
        mock_llm_client.analyze.side_effect = connection_error

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        assert error.service_name == "LLM"
        assert error.operation == "prd_analysis"
        assert "AI provider error" in str(error)
        assert "prd_analysis failed for LLM" in str(error)

        # Verify error context contains troubleshooting information
        context = error.context.custom_context
        assert context is not None
        assert context["prd_length"] == len(sample_prd_content)
        assert context["prd_preview"] in str(error.context.custom_context)
        assert context["original_error"] == "Unable to connect to AI provider"
        assert "troubleshooting_steps" in context
        troubleshooting_steps = context["troubleshooting_steps"]
        assert any("API credentials" in step for step in troubleshooting_steps)
        assert any("network connectivity" in step for step in troubleshooting_steps)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ai_timeout_failure_raises_proper_error(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test AI provider timeout raises AIProviderError with timeout context"""
        # Arrange
        timeout_error = TimeoutError("AI provider request timed out")
        mock_llm_client.analyze.side_effect = timeout_error

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        assert error.service_name == "LLM"
        assert error.operation == "prd_analysis"
        assert "AI provider error" in str(error)
        assert "prd_analysis failed for LLM" in str(error)

        # Verify context includes timeout-specific troubleshooting
        context = error.context.custom_context
        assert context is not None
        assert context["original_error"] == "AI provider request timed out"
        assert "troubleshooting_steps" in context
        troubleshooting_steps = context["troubleshooting_steps"]
        assert any("network" in step.lower() for step in troubleshooting_steps)
        assert any("service status" in step.lower() for step in troubleshooting_steps)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_json_parsing_failure_raises_proper_error(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test malformed JSON response raises AIProviderError with parsing context"""
        # Arrange
        malformed_json = "This is not valid JSON { incomplete: true"
        mock_llm_client.analyze.return_value = malformed_json

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        assert error.service_name == "LLM"
        assert (
            error.operation == "prd_analysis"
        )  # JSON errors are caught and re-raised as prd_analysis errors

        # Verify parsing error context - JSON errors are caught and re-raised as general AI errors
        context = error.context.custom_context
        assert context is not None
        assert context["prd_length"] == len(sample_prd_content)
        assert "original_error" in context  # Contains the JSON parsing error details
        assert "troubleshooting_steps" in context

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_ai_response_raises_proper_error(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test empty AI response raises AIProviderError"""
        # Arrange
        mock_llm_client.analyze.return_value = ""

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        assert error.service_name == "LLM"
        assert (
            error.operation == "prd_analysis"
        )  # JSON errors are caught and re-raised as prd_analysis errors

        context = error.context.custom_context
        assert context is not None
        assert (
            "original_error" in context
        )  # JSON parsing error details are in original_error

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_none_ai_response_raises_proper_error(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test None AI response raises AIProviderError"""
        # Arrange
        mock_llm_client.analyze.return_value = None

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        assert error.service_name == "LLM"
        assert (
            error.operation == "prd_analysis"
        )  # JSON errors are caught and re-raised as prd_analysis errors

        context = error.context.custom_context
        assert context is not None
        assert (
            "original_error" in context
        )  # JSON parsing error details are in original_error

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_successful_ai_analysis_works_normally(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test successful AI analysis continues to work normally"""
        # Arrange
        valid_response = {
            "functional_requirements": [
                {
                    "id": "req_1",
                    "name": "User Authentication",
                    "description": "User authentication",
                    "priority": "high",
                },
                {
                    "id": "req_2",
                    "name": "Task Management",
                    "description": "Task management",
                    "priority": "high",
                },
            ],
            "non_functional_requirements": [
                {
                    "id": "nfr_1",
                    "description": "Performance optimization",
                    "category": "performance",
                }
            ],
            "technical_constraints": ["REST API", "PostgreSQL"],
            "business_objectives": ["Improve productivity", "User engagement"],
            "user_personas": [{"name": "End User", "role": "Task Manager"}],
            "success_metrics": ["Task completion rate", "User satisfaction"],
            "implementation_approach": "agile_iterative",
            "complexity_assessment": {"technical": "medium", "timeline": "medium"},
            "risk_factors": [
                {"category": "technical", "description": "Integration complexity"}
            ],
            "confidence": 0.85,
        }
        mock_llm_client.analyze.return_value = json.dumps(valid_response)

        # Act
        result = await parser._analyze_prd_deeply(
            sample_prd_content, sample_constraints
        )

        # Assert
        assert len(result.functional_requirements) == 2
        assert result.functional_requirements[0]["id"] == "req_1"
        assert result.functional_requirements[0]["description"] == "User authentication"
        assert len(result.non_functional_requirements) == 1
        assert result.confidence == 0.85
        assert result.implementation_approach == "agile_iterative"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_monitoring_integration(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test that errors are properly recorded for monitoring"""
        # Arrange
        api_error = ValueError("API key invalid")
        mock_llm_client.analyze.side_effect = api_error

        # Mock the error monitoring
        with patch(
            "src.core.error_monitoring.record_error_for_monitoring"
        ) as mock_record:
            # Act & Assert
            with pytest.raises(AIProviderError):
                await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

            # Verify error was recorded for monitoring
            mock_record.assert_called_once()
            recorded_error = mock_record.call_args[0][0]
            assert isinstance(recorded_error, AIProviderError)
            assert recorded_error.service_name == "LLM"
            assert recorded_error.operation == "prd_analysis"

    @pytest.mark.unit
    def test_no_fallback_methods_exist(self, parser):
        """Test that fallback simulation methods have been removed"""
        # Verify fallback methods no longer exist
        assert not hasattr(parser, "_simulate_prd_analysis")
        assert not hasattr(parser, "_simulate_prd_analysis_enhanced")
        assert not hasattr(parser, "_create_fallback_analysis")
        assert not hasattr(parser, "_detect_tech_stack")
        assert not hasattr(parser, "_extract_business_objectives")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_context_includes_actionable_troubleshooting(
        self, parser, mock_llm_client, sample_prd_content, sample_constraints
    ):
        """Test error context includes comprehensive troubleshooting steps"""
        # Arrange
        auth_error = PermissionError("Invalid API credentials")
        mock_llm_client.analyze.side_effect = auth_error

        # Act & Assert
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(sample_prd_content, sample_constraints)

        error = exc_info.value
        context = error.context.custom_context
        assert context is not None

        # Verify all expected troubleshooting steps are present
        expected_steps = [
            "Check AI provider API credentials and configuration",
            "Verify network connectivity to AI provider",
            "Try simplifying the project description",
            "Check AI provider service status",
            "Ensure project description is in English and well-structured",
        ]

        troubleshooting_steps = context["troubleshooting_steps"]
        for expected_step in expected_steps:
            assert expected_step in troubleshooting_steps

        # Verify error details are comprehensive
        assert "AI analysis of project requirements failed" in context["details"]
        assert "prevents automatic task generation" in context["details"]
        assert "check your AI configuration" in context["details"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prd_content_length_tracked_in_errors(
        self, parser, mock_llm_client, sample_constraints
    ):
        """Test that PRD content length is tracked in error context for debugging"""
        # Arrange
        short_prd = "Build app"
        long_prd = (
            "A" * 1000 + " detailed project requirements with many specifications"
        )

        mock_llm_client.analyze.side_effect = RuntimeError("Test error")

        # Test short PRD
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(short_prd, sample_constraints)
        assert exc_info.value.context.custom_context["prd_length"] == len(short_prd)

        # Test long PRD
        with pytest.raises(AIProviderError) as exc_info:
            await parser._analyze_prd_deeply(long_prd, sample_constraints)
        assert exc_info.value.context.custom_context["prd_length"] == len(long_prd)

        # Verify preview is truncated for long content
        preview = exc_info.value.context.custom_context["prd_preview"]
        assert len(preview) <= 203  # 200 chars + "..."
        assert preview.endswith("...")


class TestAdvancedPRDParserTaskGeneration:
    """Test suite for PRD parser task generation improvements"""

    @pytest.fixture
    def parser(self):
        """Create parser instance with mocked dependencies"""
        with patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"):
            with patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"):
                return AdvancedPRDParser()

    @pytest.fixture
    def mock_constraints(self):
        """Create mock project constraints"""
        return ProjectConstraints(
            team_size=2, technology_constraints=["Node.js", "Express", "PostgreSQL"]
        )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_prd_handles_camelcase_and_snakecase_keys(self, parser):
        """Test that PRD analysis handles both camelCase and snake_case keys"""
        # Test data with camelCase (as AI returns)
        camelcase_data = {
            "functionalRequirements": [
                {"feature": "CRUD", "description": "CRUD operations"}
            ],
            "nonFunctionalRequirements": [
                {"requirement": "Performance", "description": "Fast"}
            ],
            "technicalConstraints": ["Node.js"],
            "businessObjectives": ["Build API"],
            "userPersonas": [],
            "successMetrics": ["Working"],
            "recommendedImplementation": "agile",
            "complexityAssessment": {"level": "low"},
            "riskFactors": [],
        }

        with patch("src.utils.json_parser.parse_ai_json_response") as mock_parse:
            mock_parse.return_value = camelcase_data

            with patch.object(parser.llm_client, "analyze", new_callable=AsyncMock):
                result = await parser._analyze_prd_deeply(
                    "Test PRD", ProjectConstraints()
                )

                assert len(result.functional_requirements) == 1
                assert result.functional_requirements[0]["feature"] == "CRUD"
                assert len(result.non_functional_requirements) == 1
                assert result.implementation_approach == "agile"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_task_hierarchy_creates_unique_epic_ids(
        self, parser, mock_constraints
    ):
        """Test that each functional requirement gets a unique epic ID"""
        from src.ai.advanced.prd.advanced_parser import PRDAnalysis

        prd_analysis = PRDAnalysis(
            functional_requirements=[
                {"feature": "CRUD Operations", "description": "CRUD"},
                {"feature": "User Auth", "description": "Auth"},
                {"feature": "Validation", "description": "Validate"},
            ],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
        )

        hierarchy = await parser._generate_task_hierarchy(
            prd_analysis, mock_constraints
        )

        # Should have unique epic IDs
        assert "epic_crud_operations" in hierarchy
        assert "epic_user_auth" in hierarchy
        assert "epic_validation" in hierarchy
        assert len(hierarchy) == 5  # 3 functional + 1 NFR + 1 infra

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_break_down_epic_uses_feature_name_for_unique_ids(
        self, parser, mock_constraints
    ):
        """Test that task IDs are based on feature names"""
        from src.ai.advanced.prd.advanced_parser import PRDAnalysis

        req1 = {"feature": "CRUD Operations", "description": "CRUD"}
        req2 = {"feature": "User Auth", "description": "Auth"}

        analysis = PRDAnalysis(
            functional_requirements=[],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.8,
        )

        tasks1 = await parser._break_down_epic(req1, analysis, mock_constraints)
        tasks2 = await parser._break_down_epic(req2, analysis, mock_constraints)

        # Check task IDs are unique and based on feature
        assert tasks1[0]["id"] == "task_crud_operations_design"
        assert tasks1[1]["id"] == "task_crud_operations_implement"
        assert tasks1[2]["id"] == "task_crud_operations_test"

        assert tasks2[0]["id"] == "task_user_auth_design"
        assert tasks2[1]["id"] == "task_user_auth_implement"
        assert tasks2[2]["id"] == "task_user_auth_test"

        # Check task names include feature name
        assert tasks1[0]["name"] == "Design CRUD Operations"
        assert tasks2[0]["name"] == "Design User Auth"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_nfr_tasks_uses_requirement_name_for_ids(
        self, parser, mock_constraints
    ):
        """Test NFR tasks use requirement names for unique IDs"""
        nfrs = [
            {"requirement": "Performance", "description": "Fast"},
            {"requirement": "Security", "description": "Secure"},
        ]

        tasks = await parser._create_nfr_tasks(nfrs, mock_constraints)

        assert len(tasks) == 2
        assert tasks[0]["id"] == "nfr_task_performance"
        assert tasks[0]["name"] == "Implement Performance"
        assert tasks[1]["id"] == "nfr_task_security"
        assert tasks[1]["name"] == "Implement Security"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_task_generation_creates_all_tasks(
        self, parser, mock_constraints
    ):
        """Test that all functional requirements generate tasks"""
        from src.ai.advanced.prd.advanced_parser import PRDAnalysis

        prd_analysis = PRDAnalysis(
            functional_requirements=[
                {
                    "feature": "CRUD Operations",
                    "description": "Create, Read, Update, Delete",
                },
                {
                    "feature": "Todo Properties",
                    "description": "Title, status, timestamps",
                },
                {"feature": "User Auth", "description": "JWT authentication"},
                {"feature": "Validation", "description": "Input validation"},
            ],
            non_functional_requirements=[
                {"requirement": "Performance", "description": "100 req/s"},
                {"requirement": "Security", "description": "JWT tokens"},
            ],
            technical_constraints=["Node.js", "Express"],
            business_objectives=["Build TODO API"],
            user_personas=[],
            success_metrics=["All CRUD working"],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.9,
        )

        # Generate hierarchy
        hierarchy = await parser._generate_task_hierarchy(
            prd_analysis, mock_constraints
        )

        # Should have all functional epics
        assert (
            len(hierarchy) == 5
        )  # 3 functional + 1 NFR + 1 infra (validation is filtered)
        assert "epic_crud_operations" in hierarchy
        assert "epic_todo_properties" in hierarchy
        assert "epic_user_auth" in hierarchy

        # Each functional epic should have 3 tasks
        assert len(hierarchy["epic_crud_operations"]) == 3
        assert len(hierarchy["epic_todo_properties"]) == 3
        assert len(hierarchy["epic_user_auth"]) == 3

        # NFR epic should have tasks for each NFR
        assert len(hierarchy["epic_non_functional"]) == 2  # Performance + Security

        # Infrastructure epic should have 2 tasks (setup + CI/CD)
        assert len(hierarchy["epic_infrastructure"]) == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_task_descriptions_are_task_type_specific(
        self, parser, mock_constraints
    ):
        """
        Test that Design/Implement/Test tasks get different descriptions.

        Verifies the fix for the issue where all three task types were
        getting the same implementation-focused description.
        """
        from src.ai.advanced.prd.advanced_parser import PRDAnalysis

        prd_analysis = PRDAnalysis(
            functional_requirements=[
                {
                    "id": "user_authentication",
                    "name": "User Authentication",
                    "description": "Implement JWT-based authentication for user registration, login, and token-based authorization",
                    "priority": "high",
                }
            ],
            non_functional_requirements=[],
            technical_constraints=[],
            business_objectives=[],
            user_personas=[],
            success_metrics=[],
            implementation_approach="agile",
            complexity_assessment={},
            risk_factors=[],
            confidence=0.9,
        )

        # Mock the LLM to return task-type-specific descriptions
        async def mock_analyze(prompt, context):
            # Return different descriptions based on task type in prompt
            if "**DESIGN**" in prompt:
                return "Design the authentication architecture, API endpoints, and user flow diagrams."
            elif "**TEST**" in prompt:
                return "Write comprehensive tests for authentication flows including registration, login, and token validation."
            elif "**IMPLEMENT**" in prompt:
                return "Implement JWT-based authentication with user registration and login endpoints."
            return "Generic description"

        parser.llm_client.analyze = AsyncMock(side_effect=mock_analyze)

        # Generate all three task types
        design_task = await parser._generate_detailed_task(
            task_id="task_user_authentication_design",
            epic_id="epic_user_auth",
            analysis=prd_analysis,
            constraints=mock_constraints,
            sequence=1,
        )

        implement_task = await parser._generate_detailed_task(
            task_id="task_user_authentication_implement",
            epic_id="epic_user_auth",
            analysis=prd_analysis,
            constraints=mock_constraints,
            sequence=2,
        )

        test_task = await parser._generate_detailed_task(
            task_id="task_user_authentication_test",
            epic_id="epic_user_auth",
            analysis=prd_analysis,
            constraints=mock_constraints,
            sequence=3,
        )

        # Verify task names are correct (existing behavior)
        assert design_task.name == "Design User Authentication"
        assert implement_task.name == "Implement User Authentication"
        assert test_task.name == "Test User Authentication"

        # Verify descriptions are task-type-specific (NEW: this was the bug)
        assert (
            "design" in design_task.description.lower()
            or "architecture" in design_task.description.lower()
        )
        assert (
            "implement" in implement_task.description.lower()
            or "build" in implement_task.description.lower()
        )
        assert (
            "test" in test_task.description.lower()
            or "validation" in test_task.description.lower()
        )

        # Verify they're NOT all the same description
        assert design_task.description != implement_task.description
        assert design_task.description != test_task.description
        assert implement_task.description != test_task.description


class TestConstraintRiskAnalysis:
    """Test suite for constraint risk analysis with deadline handling"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        mock_client = Mock()
        mock_client.analyze = AsyncMock()
        return mock_client

    @pytest.fixture
    def parser(self, mock_llm_client):
        """Create AdvancedPRDParser with mocked dependencies"""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_client
            parser = AdvancedPRDParser()
            parser.llm_client = mock_llm_client
            return parser

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_constraint_risks_with_sufficient_time(self, parser):
        """Test that no timeline pressure risk with sufficient time"""
        from datetime import timedelta, timezone

        from src.core.models import Priority, Task, TaskStatus

        # Arrange - Create deadline with sufficient time (7 days, 2 people = 84 hours capacity)
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        constraints = ProjectConstraints(deadline=deadline, team_size=2)

        now_utc = datetime.now(timezone.utc)
        tasks = [
            Task(
                id="task1",
                name="Test Task",
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=40,  # 40 hours of work - well within capacity
                assigned_to=None,
                created_at=now_utc,
                updated_at=now_utc,
                due_date=None,
            )
        ]

        # Act
        risks = await parser._analyze_constraint_risks(tasks, constraints)

        # Assert - Should not detect timeline pressure
        assert isinstance(risks, list)
        assert not any(risk["type"] == "timeline_pressure" for risk in risks)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_constraint_risks_with_aware_deadline(self, parser):
        """Test that aware deadline works correctly"""
        from datetime import timedelta, timezone

        from src.core.models import Priority, Task, TaskStatus

        # Arrange - Create aware deadline (with UTC timezone)
        aware_deadline = datetime.now(timezone.utc) + timedelta(days=7)
        constraints = ProjectConstraints(deadline=aware_deadline, team_size=2)

        now_utc = datetime.now(timezone.utc)
        tasks = [
            Task(
                id="task1",
                name="Test Task",
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=40,
                assigned_to=None,
                created_at=now_utc,
                updated_at=now_utc,
                due_date=None,
            )
        ]

        # Act
        risks = await parser._analyze_constraint_risks(tasks, constraints)

        # Assert
        assert isinstance(risks, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_constraint_risks_detects_timeline_pressure(self, parser):
        """Test that timeline pressure is detected with insufficient time"""
        from datetime import timedelta, timezone

        from src.core.models import Priority, Task, TaskStatus

        # Arrange - Create tight deadline (1 day) with too much work (100 hours)
        tight_deadline = datetime.now(timezone.utc) + timedelta(days=1)
        constraints = ProjectConstraints(deadline=tight_deadline, team_size=2)

        now_utc = datetime.now(timezone.utc)
        tasks = [
            Task(
                id="task1",
                name="Test Task",
                description="Test",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                estimated_hours=100,  # Too much work for 1 day with 2 people
                assigned_to=None,
                created_at=now_utc,
                updated_at=now_utc,
                due_date=None,
            )
        ]

        # Act
        risks = await parser._analyze_constraint_risks(tasks, constraints)

        # Assert - Should detect timeline pressure
        assert len(risks) > 0
        assert any(risk["type"] == "timeline_pressure" for risk in risks)


class TestTaskDescriptionConstraints:
    """Test suite for task description constraint handling (GH-143 fix)"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for testing"""
        mock_client = Mock()
        mock_client.analyze = AsyncMock()
        return mock_client

    @pytest.fixture
    def parser(self, mock_llm_client):
        """Create AdvancedPRDParser with mocked LLM"""
        with patch(
            "src.ai.advanced.prd.advanced_parser.LLMAbstraction"
        ) as mock_llm_class:
            mock_llm_class.return_value = mock_llm_client
            with patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"):
                parser = AdvancedPRDParser()
                parser.llm_client = mock_llm_client
                return parser

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_design_task_includes_technical_constraints_in_prompt(
        self, parser, mock_llm_client
    ):
        """Test design task generation includes tech constraints in LLM prompt (GH-143)"""
        # Arrange
        mock_llm_client.analyze.return_value = "Design auth with FastAPI endpoints"

        # Act
        description = await parser._generate_task_description_for_type(
            base_description="User authentication system",
            task_type="design",
            feature_name="Authentication",
            constraints=["FastAPI", "PostgreSQL", "React"],
            original_description="Build a blog platform",
        )

        # Assert
        assert mock_llm_client.analyze.called
        call_args = mock_llm_client.analyze.call_args[0]
        prompt = call_args[0]

        # Verify tech constraints are in the prompt for design tasks
        assert "TECHNICAL CONSTRAINTS" in prompt
        assert "FastAPI" in prompt
        assert "PostgreSQL" in prompt
        assert "React" in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_implement_task_excludes_technical_constraints_from_prompt(
        self, parser, mock_llm_client
    ):
        """Test implementation task does NOT include tech constraints in prompt (GH-143)"""
        # Arrange
        mock_llm_client.analyze.return_value = "Implement auth service with endpoints"

        # Act
        description = await parser._generate_task_description_for_type(
            base_description="User authentication system",
            task_type="implement",
            feature_name="Authentication",
            constraints=["FastAPI", "PostgreSQL", "React"],
            original_description="Build a blog platform",
        )

        # Assert
        assert mock_llm_client.analyze.called
        call_args = mock_llm_client.analyze.call_args[0]
        prompt = call_args[0]

        # Verify tech constraints are NOT in the prompt for implementation tasks
        assert "TECHNICAL CONSTRAINTS" not in prompt
        assert "FastAPI" not in prompt
        assert "PostgreSQL" not in prompt
        assert "React" not in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_task_excludes_technical_constraints_from_prompt(
        self, parser, mock_llm_client
    ):
        """Test test task does NOT include tech constraints in prompt"""
        # Arrange
        mock_llm_client.analyze.return_value = "Write comprehensive auth tests"

        # Act
        description = await parser._generate_task_description_for_type(
            base_description="User authentication system",
            task_type="test",
            feature_name="Authentication",
            constraints=["FastAPI", "PostgreSQL"],
            original_description="Build a blog platform",
        )

        # Assert
        assert mock_llm_client.analyze.called
        call_args = mock_llm_client.analyze.call_args[0]
        prompt = call_args[0]

        # Verify tech constraints are NOT in the prompt for test tasks
        assert "TECHNICAL CONSTRAINTS" not in prompt

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_implement_task_prompt_instructs_no_tech_specification(
        self, parser, mock_llm_client
    ):
        """Test implementation prompt explicitly says not to specify technologies"""
        # Arrange
        mock_llm_client.analyze.return_value = "Build backend API"

        # Act
        await parser._generate_task_description_for_type(
            base_description="Backend API",
            task_type="implement",
            feature_name="API",
            constraints=["Node.js"],
        )

        # Assert
        call_args = mock_llm_client.analyze.call_args[0]
        prompt = call_args[0]

        # Verify prompt instructs not to specify technologies
        assert "DO NOT specify technologies" in prompt
        assert "discover the tech stack from design documentation" in prompt
