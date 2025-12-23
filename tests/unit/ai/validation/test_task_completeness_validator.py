"""Unit tests for TaskCompletenessValidator."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ai.validation.task_completeness_validator import TaskCompletenessValidator
from src.core.error_framework import BusinessLogicError, ErrorContext
from src.core.models import Task


class TestTaskCompletenessValidator:
    """Test suite for TaskCompletenessValidator."""

    @pytest.fixture
    def mock_ai_client(self) -> AsyncMock:
        """Create mock AI client."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def mock_prd_parser(self) -> AsyncMock:
        """Create mock PRD parser."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def validator(
        self, mock_ai_client: AsyncMock, mock_prd_parser: AsyncMock
    ) -> TaskCompletenessValidator:
        """Create validator instance with mocked dependencies."""
        return TaskCompletenessValidator(mock_ai_client, mock_prd_parser)

    @pytest.fixture
    def sample_tasks(self) -> list[Task]:
        """Create sample task list."""
        from datetime import datetime, timezone

        from src.core.models import Priority, TaskStatus

        now = datetime.now(timezone.utc)
        return [
            Task(
                id="1",
                name="Create MCP tools",
                description="Implement MCP tools for deck operations",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="2",
                name="Build API client",
                description="Create client to wrap Deck of Cards API",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=3.0,
            ),
        ]

    @pytest.fixture
    def error_context(self) -> ErrorContext:
        """Create error context for testing."""
        return ErrorContext(
            operation="test_validation",
            correlation_id="test-123",
        )

    @pytest.mark.asyncio
    async def test_extract_intents_success(
        self, validator: TaskCompletenessValidator, mock_ai_client: AsyncMock
    ) -> None:
        """Test successful intent extraction from description."""
        # Arrange
        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {"intents": ["MCP server", "Deck of Cards API wrapper", "card tools"]}
            ),
        ) as mock_call:
            # Act
            result = await validator.extract_intents(
                "Build an MCP server that wraps the Deck of Cards API",
                "deck-mcp",
            )

            # Assert - returns simple list of intents
            assert isinstance(result, list)
            assert len(result) == 3
            assert "MCP server" in result
            assert "Deck of Cards API wrapper" in result
            assert "card tools" in result
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_coverage_complete(
        self,
        validator: TaskCompletenessValidator,
        mock_ai_client: AsyncMock,
        sample_tasks: list[Task],
    ) -> None:
        """Test validation passes when all intents are covered."""
        # Arrange
        intents = ["MCP tools", "API client"]
        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {
                    "complete": True,
                    "missing": [],
                }
            ),
        ):
            # Act
            result = await validator.validate_coverage(intents, sample_tasks)

            # Assert
            assert result["complete"] is True
            assert result["missing"] == []

    @pytest.mark.asyncio
    async def test_validate_coverage_incomplete(
        self,
        validator: TaskCompletenessValidator,
        mock_ai_client: AsyncMock,
        sample_tasks: list[Task],
    ) -> None:
        """Test validation fails when intents are missing."""
        # Arrange
        intents = ["MCP tools", "API client", "MCP server"]
        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {
                    "complete": False,
                    "missing": ["MCP server"],
                }
            ),
        ):
            # Act
            result = await validator.validate_coverage(intents, sample_tasks)

            # Assert
            assert result["complete"] is False
            assert "MCP server" in result["missing"]

    @pytest.mark.asyncio
    async def test_validate_with_retry_passes_first_attempt(
        self,
        validator: TaskCompletenessValidator,
        mock_ai_client: AsyncMock,
        sample_tasks: list[Task],
        error_context: ErrorContext,
    ) -> None:
        """Test validation succeeds on first attempt."""
        # Arrange
        call_count = [0]

        async def mock_call_ai(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                # extract_intents call (flat format for backwards compat)
                return json.dumps({"intents": ["MCP tools", "API client"]})
            else:
                # validate_coverage call
                return json.dumps(
                    {
                        "complete": True,
                        "missing": [],
                        "missing_component_intents": [],
                        "missing_integration_intents": [],
                    }
                )

        with patch.object(validator, "_call_ai", side_effect=mock_call_ai):
            # Act
            result = await validator.validate_with_retry(
                description="Build MCP tools and API client",
                project_name="test-project",
                tasks=sample_tasks,
                constraints=MagicMock(),
                context=error_context,
            )

            # Assert
            assert result.is_complete is True
            assert result.total_attempts == 1
            assert result.passed_on_attempt == 1
            assert len(result.final_tasks) == 2

    @pytest.mark.asyncio
    async def test_validate_with_retry_passes_second_attempt(
        self,
        validator: TaskCompletenessValidator,
        mock_ai_client: AsyncMock,
        mock_prd_parser: AsyncMock,
        sample_tasks: list[Task],
        error_context: ErrorContext,
    ) -> None:
        """Test validation succeeds after retry with emphasis."""
        # Arrange
        from datetime import datetime, timezone

        from src.core.models import Priority, TaskStatus

        now = datetime.now(timezone.utc)

        # Create tasks for retry (now includes server task)
        retry_tasks = sample_tasks + [
            Task(
                id="3",
                name="Create MCP server",
                description="Setup MCP server entry point",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=5.0,
            )
        ]

        # Mock PRD parser to return new tasks on retry
        mock_prd_result = MagicMock()
        mock_prd_result.tasks = retry_tasks
        mock_prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_prd_result)

        call_count = [0]

        async def mock_call_ai(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                # extract_intents call (flat format for backwards compat)
                return json.dumps(
                    {"intents": ["MCP server", "MCP tools", "API client"]}
                )
            elif call_count[0] == 2:
                # First validate_coverage call (incomplete)
                return json.dumps(
                    {
                        "complete": False,
                        "missing": ["MCP server"],
                        "missing_component_intents": [],
                        "missing_integration_intents": ["MCP server"],
                    }
                )
            else:
                # Second validate_coverage call (complete)
                return json.dumps(
                    {
                        "complete": True,
                        "missing": [],
                        "missing_component_intents": [],
                        "missing_integration_intents": [],
                    }
                )

        with patch.object(validator, "_call_ai", side_effect=mock_call_ai):
            # Act
            result = await validator.validate_with_retry(
                description="Build MCP server with tools",
                project_name="test-project",
                tasks=sample_tasks,
                constraints=MagicMock(),
                context=error_context,
            )

            # Assert
            assert result.is_complete is True
            assert result.total_attempts == 2
            assert result.passed_on_attempt == 2
            assert len(result.final_tasks) == 3
            # Verify composition-aware emphasis was added to retry
            assert mock_prd_parser.parse_prd_to_tasks.called
            retry_call_description = mock_prd_parser.parse_prd_to_tasks.call_args[0][0]
            assert (
                "CRITICAL" in retry_call_description
                or "IMPORTANT" in retry_call_description
            )
            assert "MCP server" in retry_call_description

    @pytest.mark.asyncio
    async def test_validate_with_retry_fails_after_max_attempts(
        self,
        validator: TaskCompletenessValidator,
        mock_ai_client: AsyncMock,
        mock_prd_parser: AsyncMock,
        sample_tasks: list[Task],
        error_context: ErrorContext,
    ) -> None:
        """Test validation raises error after exhausting max attempts."""
        # Arrange
        mock_prd_result = MagicMock()
        mock_prd_result.tasks = sample_tasks
        mock_prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_prd_result)

        call_count = [0]

        async def mock_call_ai(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                # extract_intents call (flat format for backwards compat)
                return json.dumps({"intents": ["MCP server", "MCP tools"]})
            else:
                # All validate_coverage calls fail
                return json.dumps(
                    {
                        "complete": False,
                        "missing": ["MCP server"],
                        "missing_component_intents": [],
                        "missing_integration_intents": ["MCP server"],
                    }
                )

        with patch.object(validator, "_call_ai", side_effect=mock_call_ai):
            # Act & Assert
            with pytest.raises(BusinessLogicError) as exc_info:
                await validator.validate_with_retry(
                    description="Build MCP server",
                    project_name="test-project",
                    tasks=sample_tasks,
                    constraints=MagicMock(),
                    context=error_context,
                )

            # Verify error message
            assert "validation failed after 3 attempts" in str(exc_info.value)
            assert "MCP server" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_composition_emphasis_generation(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test composition-aware emphasis text generation."""
        # Arrange
        missing_components = ["User authentication"]
        missing_integration = ["MCP server", "documentation"]

        # Act
        emphasis = validator._create_composition_emphasis(
            missing_components=missing_components,
            missing_integration=missing_integration,
        )

        # Assert
        assert "IMPORTANT" in emphasis  # For components
        assert "CRITICAL" in emphasis  # For integration
        assert "User authentication" in emphasis
        assert "MCP server" in emphasis
        assert "documentation" in emphasis


class TestCompositionAwareness:
    """Test suite for composition-aware validation features."""

    def test_structured_intents_len(self) -> None:
        """Test StructuredIntents supports len() for backwards compatibility."""
        # Arrange
        intents = StructuredIntents(
            component_intents=["Feature A", "Feature B"],
            integration_intents=["Server setup"],
            all_intents=["Feature A", "Feature B", "Server setup"],
        )

        # Act & Assert
        assert len(intents) == 3

    def test_structured_intents_iteration(self) -> None:
        """Test StructuredIntents supports iteration for backwards compat."""
        # Arrange
        intents = StructuredIntents(
            component_intents=["Feature A", "Feature B"],
            integration_intents=["Server setup"],
            all_intents=["Feature A", "Feature B", "Server setup"],
        )

        # Act
        items = list(intents)

        # Assert
        assert items == ["Feature A", "Feature B", "Server setup"]

    def test_structured_intents_iteration_with_any(self) -> None:
        """Test StructuredIntents works with any() like original list."""
        # Arrange
        intents = StructuredIntents(
            component_intents=["Deck creation", "Card drawing"],
            integration_intents=["MCP server infrastructure"],
            all_intents=["Deck creation", "Card drawing", "MCP server infrastructure"],
        )

        # Act & Assert - Mimics test_task_validation_e2e.py usage
        server_related = any(
            "server" in intent.lower() or "mcp" in intent.lower() for intent in intents
        )
        assert server_related is True

    @pytest.fixture
    def mock_ai_client(self) -> AsyncMock:
        """Create mock AI client."""
        return AsyncMock()

    @pytest.fixture
    def mock_prd_parser(self) -> AsyncMock:
        """Create mock PRD parser."""
        return AsyncMock()

    @pytest.fixture
    def validator(
        self, mock_ai_client: AsyncMock, mock_prd_parser: AsyncMock
    ) -> TaskCompletenessValidator:
        """Create validator instance with mocked dependencies."""
        return TaskCompletenessValidator(mock_ai_client, mock_prd_parser)

    @pytest.fixture
    def sample_component_tasks(self) -> list[Task]:
        """Create sample tasks covering only components (not integration)."""
        from datetime import datetime, timezone

        from src.core.models import Priority, TaskStatus

        now = datetime.now(timezone.utc)
        return [
            Task(
                id="1",
                name="Implement Create Deck Tool",
                description="Implement MCP tool for creating decks",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=2.0,
            ),
            Task(
                id="2",
                name="Implement Draw Cards Tool",
                description="Implement MCP tool for drawing cards",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=2.0,
            ),
            Task(
                id="3",
                name="Implement Get Status Tool",
                description="Implement MCP tool for getting deck status",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=1.5,
            ),
        ]

    @pytest.fixture
    def error_context(self) -> ErrorContext:
        """Create error context for testing."""
        return ErrorContext(
            operation="test_composition_validation",
            correlation_id="test-comp-123",
        )

    def test_structured_intents_creation(self) -> None:
        """Test StructuredIntents dataclass properly combines intents."""
        # Arrange & Act
        intents = StructuredIntents(
            component_intents=["Deck operations", "Card management"],
            integration_intents=["MCP server setup", "Tool registration"],
            all_intents=[
                "Deck operations",
                "Card management",
                "MCP server setup",
                "Tool registration",
            ],
        )

        # Assert
        assert len(intents.component_intents) == 2
        assert len(intents.integration_intents) == 2
        assert len(intents.all_intents) == 4
        assert "Deck operations" in intents.component_intents
        assert "MCP server setup" in intents.integration_intents

    @pytest.mark.asyncio
    async def test_extract_structured_intents_with_both_tiers(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test extraction returns structured intents with both tiers."""
        # Arrange
        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {
                    "component_intents": [
                        "Deck creation",
                        "Card drawing",
                        "Status checking",
                    ],
                    "integration_intents": [
                        "MCP server infrastructure",
                        "Tool registration",
                        "Server entry point",
                    ],
                }
            ),
        ):
            # Act
            intents = await validator.extract_intents(
                "Build an MCP server for BlackJack deck operations",
                "blackjack-mcp",
            )

            # Assert
            assert isinstance(intents, StructuredIntents)
            assert len(intents.component_intents) == 3
            assert len(intents.integration_intents) == 3
            assert "Deck creation" in intents.component_intents
            assert "MCP server infrastructure" in intents.integration_intents
            assert len(intents.all_intents) == 6

    @pytest.mark.asyncio
    async def test_extract_intents_fallback_on_malformed_response(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test fallback when AI returns malformed JSON."""
        # Arrange
        description = "Build an MCP server"

        with patch.object(
            validator,
            "_call_ai",
            return_value="not valid json",
        ):
            # Act
            intents = await validator.extract_intents(description, "test-project")

            # Assert
            assert isinstance(intents, StructuredIntents)
            assert len(intents.component_intents) == 1
            assert intents.component_intents[0] == description[:100]
            assert len(intents.integration_intents) == 0
            assert len(intents.all_intents) == 1

    @pytest.mark.asyncio
    async def test_validate_coverage_detects_missing_integration(
        self,
        validator: TaskCompletenessValidator,
        sample_component_tasks: list[Task],
    ) -> None:
        """Test validation detects missing integration tasks."""
        # Arrange
        structured_intents = StructuredIntents(
            component_intents=["Deck operations", "Card management"],
            integration_intents=["MCP server setup", "Tool registration"],
            all_intents=[
                "Deck operations",
                "Card management",
                "MCP server setup",
                "Tool registration",
            ],
        )

        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {
                    "complete": False,
                    "missing": ["MCP server setup", "Tool registration"],
                    "missing_component_intents": [],
                    "missing_integration_intents": [
                        "MCP server setup",
                        "Tool registration",
                    ],
                }
            ),
        ):
            # Act
            result = await validator.validate_coverage(
                structured_intents, sample_component_tasks
            )

            # Assert
            assert result["complete"] is False
            assert len(result["missing"]) == 2
            assert "MCP server setup" in result["missing"]
            assert len(result["missing_component_intents"]) == 0
            assert len(result["missing_integration_intents"]) == 2

    @pytest.mark.asyncio
    async def test_validate_coverage_passes_with_both_tiers(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test validation passes when both component and integration tasks present."""
        # Arrange
        from datetime import datetime, timezone

        from src.core.models import Priority, TaskStatus

        now = datetime.now(timezone.utc)

        # Tasks covering both components and integration
        complete_tasks = [
            Task(
                id="1",
                name="Implement Deck Tools",
                description="MCP tools for deck operations",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=3.0,
            ),
            Task(
                id="2",
                name="Create MCP Server",
                description="Setup MCP server infrastructure and tool registration",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=4.0,
            ),
        ]

        structured_intents = StructuredIntents(
            component_intents=["Deck operations"],
            integration_intents=["MCP server setup"],
            all_intents=["Deck operations", "MCP server setup"],
        )

        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps(
                {
                    "complete": True,
                    "missing": [],
                    "missing_component_intents": [],
                    "missing_integration_intents": [],
                }
            ),
        ):
            # Act
            result = await validator.validate_coverage(
                structured_intents, complete_tasks
            )

            # Assert
            assert result["complete"] is True
            assert len(result["missing"]) == 0
            assert len(result["missing_component_intents"]) == 0
            assert len(result["missing_integration_intents"]) == 0

    @pytest.mark.asyncio
    async def test_composition_emphasis_distinguishes_tiers(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test emphasis text distinguishes between component and integration gaps."""
        # Arrange
        missing_components = ["User authentication"]
        missing_integration = ["API server setup", "Deployment configuration"]

        # Act
        emphasis = validator._create_composition_emphasis(
            missing_components, missing_integration
        )

        # Assert
        assert "IMPORTANT" in emphasis or "COMPONENTS" in emphasis
        assert "CRITICAL" in emphasis or "INTEGRATION" in emphasis
        assert "User authentication" in emphasis
        assert "API server setup" in emphasis
        assert "Deployment configuration" in emphasis
        # Should mention the importance of integration
        assert (
            "wire" in emphasis.lower()
            or "assembly" in emphasis.lower()
            or "infrastructure" in emphasis.lower()
        )

    @pytest.mark.asyncio
    async def test_retry_with_missing_integration_adds_specific_emphasis(
        self,
        validator: TaskCompletenessValidator,
        mock_prd_parser: AsyncMock,
        sample_component_tasks: list[Task],
        error_context: ErrorContext,
    ) -> None:
        """Test retry with missing integration generates tier-specific emphasis."""
        # Arrange
        from datetime import datetime, timezone

        from src.core.models import Priority, TaskStatus

        now = datetime.now(timezone.utc)

        # After retry, tasks should include integration
        retry_tasks = sample_component_tasks + [
            Task(
                id="4",
                name="Create MCP Server Entry Point",
                description="Setup server.py with MCP protocol and tool registration",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=now,
                updated_at=now,
                due_date=None,
                estimated_hours=3.0,
            )
        ]

        mock_prd_result = MagicMock()
        mock_prd_result.tasks = retry_tasks
        mock_prd_parser.parse_prd_to_tasks = AsyncMock(return_value=mock_prd_result)

        call_count = [0]

        async def mock_call_ai(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                # extract_intents call
                return json.dumps(
                    {
                        "component_intents": ["Deck operations"],
                        "integration_intents": ["MCP server infrastructure"],
                    }
                )
            elif call_count[0] == 2:
                # First validate_coverage call (missing integration)
                return json.dumps(
                    {
                        "complete": False,
                        "missing": ["MCP server infrastructure"],
                        "missing_component_intents": [],
                        "missing_integration_intents": ["MCP server infrastructure"],
                    }
                )
            else:
                # Second validate_coverage call (complete)
                return json.dumps(
                    {
                        "complete": True,
                        "missing": [],
                        "missing_component_intents": [],
                        "missing_integration_intents": [],
                    }
                )

        with patch.object(validator, "_call_ai", side_effect=mock_call_ai):
            # Act
            result = await validator.validate_with_retry(
                description="Build an MCP server for deck operations",
                project_name="blackjack-mcp",
                tasks=sample_component_tasks,
                constraints=MagicMock(),
                context=error_context,
            )

            # Assert
            assert result.is_complete is True
            assert result.total_attempts == 2
            assert result.passed_on_attempt == 2

            # Verify emphasis was tier-specific
            retry_description = mock_prd_parser.parse_prd_to_tasks.call_args[0][0]
            assert "CRITICAL" in retry_description or "INTEGRATION" in retry_description
            assert "MCP server infrastructure" in retry_description

    @pytest.mark.asyncio
    async def test_backwards_compatibility_with_flat_intents(
        self, validator: TaskCompletenessValidator
    ) -> None:
        """Test system handles AI returning flat intent list gracefully."""
        # Arrange - AI returns old flat format
        with patch.object(
            validator,
            "_call_ai",
            return_value=json.dumps({"intents": ["Feature A", "Feature B"]}),
        ):
            # Act
            intents = await validator.extract_intents(
                "Build features A and B", "test-project"
            )

            # Assert - Should work with backwards compatibility
            assert isinstance(intents, StructuredIntents)
            # Old format should be treated as components
            assert len(intents.component_intents) >= 1
            assert len(intents.all_intents) >= 1
