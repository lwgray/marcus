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
