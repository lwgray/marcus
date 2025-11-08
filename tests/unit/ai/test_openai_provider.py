"""
Unit tests for OpenAI Provider.

This module tests the OpenAI GPT provider integration, ensuring robust
handling of API calls, response parsing, and error scenarios without
making actual API requests.

Notes
-----
All external API calls are mocked to ensure fast, reliable tests that
don't depend on external services or consume API quotas.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.ai.providers.base_provider import (
    EffortEstimate,
    SemanticAnalysis,
    SemanticDependency,
)
from src.ai.providers.openai_provider import OpenAIProvider
from src.core.models import Priority, Task, TaskStatus


class TestOpenAIProviderInitialization:
    """Test suite for OpenAI provider initialization"""

    def test_initialization_with_api_key(self):
        """Test provider initializes successfully with API key"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            provider = OpenAIProvider()

            assert provider.api_key == "test-api-key"
            assert provider.base_url == "https://api.openai.com/v1"
            assert provider.model == "gpt-3.5-turbo"  # Default model
            assert provider.max_tokens == 2048
            assert provider.timeout == 30.0
            assert provider.client is not None

    def test_initialization_with_custom_model(self):
        """Test provider uses custom model from environment"""
        with patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-api-key", "OPENAI_MODEL": "gpt-4"}
        ):
            provider = OpenAIProvider()

            assert provider.model == "gpt-4"

    def test_initialization_without_api_key(self):
        """Test provider raises error without API key"""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(
                ValueError, match="OPENAI_API_KEY environment variable not set"
            ):
                OpenAIProvider()

    def test_http_client_configuration(self):
        """Test HTTP client is configured correctly"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            provider = OpenAIProvider()

            headers = provider.client.headers
            assert headers["Authorization"] == "Bearer test-api-key"
            assert headers["Content-Type"] == "application/json"
            assert provider.client is not None


class TestOpenAIProviderTaskAnalysis:
    """Test suite for task analysis functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="task-123",
            name="Implement user authentication",
            description="Add login and signup functionality",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=8.0,
        )

    @pytest.fixture
    def sample_context(self):
        """Create sample context for testing"""
        return {
            "project_type": "web_application",
            "tech_stack": ["python", "fastapi", "postgresql"],
        }

    async def test_analyze_task_success(self, provider, sample_task, sample_context):
        """Test successful task analysis"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "task_intent": "implement authentication system",
                                "semantic_dependencies": [
                                    "database setup",
                                    "user model",
                                ],
                                "risk_factors": ["security concerns", "complexity"],
                                "suggestions": ["use proven library", "implement 2FA"],
                                "confidence": 0.8,
                                "reasoning": "Authentication is critical for user management",
                                "risk_assessment": {
                                    "technical_complexity": "medium",
                                    "user_impact": "high",
                                    "rollback_difficulty": "medium",
                                },
                            }
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        # Mock the HTTP client
        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.analyze_task(sample_task, sample_context)

        assert isinstance(result, SemanticAnalysis)
        assert result.task_intent == "implement authentication system"
        assert "database setup" in result.semantic_dependencies
        assert "security concerns" in result.risk_factors
        assert "use proven library" in result.suggestions
        assert result.confidence == 0.8
        assert result.reasoning == "Authentication is critical for user management"
        assert result.risk_assessment["technical_complexity"] == "medium"

    async def test_analyze_task_api_timeout(
        self, provider, sample_task, sample_context
    ):
        """Test task analysis with API timeout"""
        provider.client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        result = await provider.analyze_task(sample_task, sample_context)

        assert isinstance(result, SemanticAnalysis)
        assert result.task_intent == "unknown"
        assert "ai_analysis_failed" in result.risk_factors
        assert result.confidence == 0.1
        assert "OpenAI analysis failed" in result.reasoning

    async def test_analyze_task_api_error(self, provider, sample_task, sample_context):
        """Test task analysis with API error"""
        mock_response = Mock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError(
            "Rate limited", request=Mock(), response=mock_response
        )

        provider.client.post = AsyncMock(side_effect=error)

        result = await provider.analyze_task(sample_task, sample_context)

        assert isinstance(result, SemanticAnalysis)
        assert result.task_intent == "unknown"
        assert "ai_analysis_failed" in result.risk_factors
        assert result.confidence == 0.1

    async def test_analyze_task_invalid_json_response(
        self, provider, sample_task, sample_context
    ):
        """Test task analysis with invalid JSON response"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "invalid json content"}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.analyze_task(sample_task, sample_context)

        assert isinstance(result, SemanticAnalysis)
        assert result.task_intent == "parse_error"
        assert "response_parsing_failed" in result.risk_factors
        assert result.confidence == 0.1

    def test_build_task_analysis_prompt(self, provider, sample_task, sample_context):
        """Test task analysis prompt building"""
        prompt = provider._build_task_analysis_prompt(sample_task, sample_context)

        assert sample_task.name in prompt
        assert sample_task.description in prompt
        assert sample_task.priority.value in prompt
        assert sample_context["project_type"] in prompt
        assert "python" in prompt
        assert "fastapi" in prompt
        assert "task_intent" in prompt
        assert "semantic_dependencies" in prompt


class TestOpenAIProviderDependencyInference:
    """Test suite for dependency inference functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for dependency testing"""
        return [
            Task(
                id="task-1",
                name="Database setup",
                description="Set up PostgreSQL database",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=4.0,
            ),
            Task(
                id="task-2",
                name="User model",
                description="Create user data model",
                status=TaskStatus.TODO,
                priority=Priority.MEDIUM,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=3.0,
            ),
            Task(
                id="task-3",
                name="Authentication API",
                description="Implement authentication endpoints",
                status=TaskStatus.TODO,
                priority=Priority.HIGH,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=6.0,
            ),
        ]

    async def test_infer_dependencies_success(self, provider, sample_tasks):
        """Test successful dependency inference"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                {
                                    "dependent_task_id": "task-2",
                                    "dependency_task_id": "task-1",
                                    "confidence": 0.9,
                                    "reasoning": "User model needs database",
                                    "dependency_type": "technical",
                                },
                                {
                                    "dependent_task_id": "task-3",
                                    "dependency_task_id": "task-2",
                                    "confidence": 0.8,
                                    "reasoning": "Auth API needs user model",
                                    "dependency_type": "logical",
                                },
                            ]
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.infer_dependencies(sample_tasks)

        assert len(result) == 2
        assert all(isinstance(dep, SemanticDependency) for dep in result)
        assert result[0].dependent_task_id == "task-2"
        assert result[0].dependency_task_id == "task-1"
        assert result[0].confidence == 0.9
        assert result[0].dependency_type == "technical"

    async def test_infer_dependencies_single_task(self, provider):
        """Test dependency inference with single task returns empty"""
        single_task = [
            Task(
                id="task-1",
                name="Single task",
                description="Only task",
                status=TaskStatus.TODO,
                priority=Priority.LOW,
                assigned_to=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                due_date=None,
                estimated_hours=2.0,
            )
        ]

        result = await provider.infer_dependencies(single_task)

        assert result == []

    async def test_infer_dependencies_api_error(self, provider, sample_tasks):
        """Test dependency inference with API error"""
        provider.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        result = await provider.infer_dependencies(sample_tasks)

        assert result == []

    async def test_infer_dependencies_invalid_task_ids(self, provider, sample_tasks):
        """Test dependency inference filters invalid task IDs"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                {
                                    "dependent_task_id": "invalid-task",
                                    "dependency_task_id": "task-1",
                                    "confidence": 0.9,
                                    "reasoning": "Invalid dependency",
                                    "dependency_type": "technical",
                                },
                                {
                                    "dependent_task_id": "task-2",
                                    "dependency_task_id": "task-1",
                                    "confidence": 0.8,
                                    "reasoning": "Valid dependency",
                                    "dependency_type": "logical",
                                },
                            ]
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.infer_dependencies(sample_tasks)

        # Should only include the valid dependency
        assert len(result) == 1
        assert result[0].dependent_task_id == "task-2"


class TestOpenAIProviderDescriptionEnhancement:
    """Test suite for description enhancement functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="task-123",
            name="Add search feature",
            description="Basic search",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
        )

    async def test_generate_enhanced_description_success(self, provider, sample_task):
        """Test successful description enhancement"""
        enhanced_description = """
        Implement comprehensive search functionality:
        - Full-text search across all content
        - Advanced filtering options
        - Search result ranking and pagination
        - Performance optimization for large datasets
        """

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": enhanced_description}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.generate_enhanced_description(sample_task, {})

        assert result == enhanced_description.strip()

    async def test_generate_enhanced_description_api_error(self, provider, sample_task):
        """Test description enhancement with API error returns original"""
        provider.client.post = AsyncMock(side_effect=Exception("API Error"))

        result = await provider.generate_enhanced_description(sample_task, {})

        assert result == sample_task.description

    async def test_generate_enhanced_description_no_description_fallback(
        self, provider
    ):
        """Test enhancement falls back to task name when no description"""
        task_without_description = Task(
            id="task-123",
            name="Task name",
            description="",
            status=TaskStatus.TODO,
            priority=Priority.MEDIUM,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=5.0,
        )

        provider.client.post = AsyncMock(side_effect=Exception("API Error"))

        result = await provider.generate_enhanced_description(
            task_without_description, {}
        )

        assert result == task_without_description.name

    def test_build_enhancement_prompt(self, provider, sample_task):
        """Test enhancement prompt building"""
        context = {"project_type": "web_app"}

        prompt = provider._build_enhancement_prompt(sample_task, context)

        assert sample_task.name in prompt
        assert sample_task.description in prompt
        assert context["project_type"] in prompt
        assert "Enhanced Description:" in prompt


class TestOpenAIProviderEffortEstimation:
    """Test suite for effort estimation functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="task-123",
            name="Database migration",
            description="Migrate data to new schema",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=0.0,
        )

    async def test_estimate_effort_success(self, provider, sample_task):
        """Test successful effort estimation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "estimated_hours": 12.5,
                                "confidence": 0.7,
                                "factors": ["data complexity", "testing requirements"],
                                "similar_tasks": [
                                    "schema updates",
                                    "data transformations",
                                ],
                                "risk_multiplier": 1.3,
                            }
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.estimate_effort(sample_task, {})

        assert isinstance(result, EffortEstimate)
        assert result.estimated_hours == 12.5
        assert result.confidence == 0.7
        assert "data complexity" in result.factors
        assert "schema updates" in result.similar_tasks
        assert result.risk_multiplier == 1.3

    async def test_estimate_effort_api_error(self, provider, sample_task):
        """Test effort estimation with API error returns fallback"""
        provider.client.post = AsyncMock(side_effect=Exception("API Error"))

        result = await provider.estimate_effort(sample_task, {})

        assert isinstance(result, EffortEstimate)
        assert result.estimated_hours == 8.0
        assert result.confidence == 0.1
        assert "ai_estimation_failed" in result.factors
        assert result.risk_multiplier == 1.5

    async def test_estimate_effort_parse_error(self, provider, sample_task):
        """Test effort estimation with parsing error"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "invalid json"}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.estimate_effort(sample_task, {})

        assert isinstance(result, EffortEstimate)
        assert result.estimated_hours == 8.0
        assert result.confidence == 0.1
        assert "parsing_failed" in result.factors


class TestOpenAIProviderBlockerAnalysis:
    """Test suite for blocker analysis functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    @pytest.fixture
    def sample_task(self):
        """Create sample task for testing"""
        return Task(
            id="task-123",
            name="Deploy application",
            description="Deploy to production",
            status=TaskStatus.BLOCKED,
            priority=Priority.URGENT,
            assigned_to=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=None,
            estimated_hours=4.0,
        )

    async def test_analyze_blocker_success(self, provider, sample_task):
        """Test successful blocker analysis"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            [
                                "Check server configuration",
                                "Verify database connectivity",
                                "Review deployment logs",
                                "Contact system administrator",
                            ]
                        )
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.analyze_blocker(
            sample_task, "Database connection failed", {"severity": "high"}
        )

        assert len(result) == 4
        assert "Check server configuration" in result
        assert "Verify database connectivity" in result

    async def test_analyze_blocker_api_error(self, provider, sample_task):
        """Test blocker analysis with API error returns fallback"""
        provider.client.post = AsyncMock(side_effect=Exception("API Error"))

        result = await provider.analyze_blocker(
            sample_task, "Unknown error", {"severity": "medium"}
        )

        assert len(result) == 3
        assert "Check task requirements and prerequisites" in result
        assert "Review relevant documentation" in result
        assert "Seek assistance from team members" in result

    async def test_analyze_blocker_non_json_response(self, provider, sample_task):
        """Test blocker analysis with non-JSON response parsing"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": """
                    - Check configuration files
                    - Restart the service
                    - Monitor system logs
                    # Additional notes
                    - Contact support if needed
                    """
                    }
                }
            ]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.analyze_blocker(
            sample_task, "Service not responding", {}
        )

        assert len(result) <= 5  # Limited to 5 suggestions
        assert any("Check configuration files" in suggestion for suggestion in result)
        assert any("Restart the service" in suggestion for suggestion in result)

    def test_build_blocker_analysis_prompt(self, provider, sample_task):
        """Test blocker analysis prompt building"""
        context = {"severity": "critical"}
        blocker = "Database timeout"

        prompt = provider._build_blocker_analysis_prompt(sample_task, blocker, context)

        assert sample_task.name in prompt
        assert blocker in prompt
        assert context["severity"] in prompt
        assert "JSON array" in prompt


class TestOpenAIProviderAPICall:
    """Test suite for OpenAI API call functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    async def test_call_openai_success(self, provider):
        """Test successful OpenAI API call"""
        messages = [{"role": "user", "content": "test message"}]

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider._call_openai(messages)

        assert result == "test response"

        # Verify the API call was made correctly
        provider.client.post.assert_called_once_with(
            f"{provider.base_url}/chat/completions",
            json={
                "model": provider.model,
                "messages": messages,
                "max_tokens": provider.max_tokens,
                "temperature": 0.1,
            },
        )

    async def test_call_openai_timeout(self, provider):
        """Test OpenAI API call timeout"""
        messages = [{"role": "user", "content": "test message"}]

        provider.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with pytest.raises(Exception, match="OpenAI API request timed out"):
            await provider._call_openai(messages)

    async def test_call_openai_http_error(self, provider):
        """Test OpenAI API HTTP error"""
        messages = [{"role": "user", "content": "test message"}]

        mock_response = Mock()
        mock_response.status_code = 401
        error = httpx.HTTPStatusError(
            "Unauthorized", request=Mock(), response=mock_response
        )

        provider.client.post = AsyncMock(side_effect=error)

        with pytest.raises(Exception, match="OpenAI API error: 401"):
            await provider._call_openai(messages)

    async def test_call_openai_generic_error(self, provider):
        """Test OpenAI API generic error"""
        messages = [{"role": "user", "content": "test message"}]

        provider.client.post = AsyncMock(side_effect=Exception("Generic error"))

        with pytest.raises(Exception, match="OpenAI API call failed: Generic error"):
            await provider._call_openai(messages)


class TestOpenAIProviderResponseParsing:
    """Test suite for response parsing functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    def test_parse_task_analysis_response_success(self, provider):
        """Test successful task analysis response parsing"""
        response = json.dumps(
            {
                "task_intent": "implement feature",
                "semantic_dependencies": ["dep1", "dep2"],
                "risk_factors": ["risk1"],
                "suggestions": ["suggestion1"],
                "confidence": 0.85,
                "reasoning": "detailed analysis",
                "risk_assessment": {"complexity": "medium"},
            }
        )

        result = provider._parse_task_analysis_response(response)

        assert isinstance(result, SemanticAnalysis)
        assert result.task_intent == "implement feature"
        assert result.semantic_dependencies == ["dep1", "dep2"]
        assert result.confidence == 0.85
        assert result.risk_assessment == {"complexity": "medium"}

    def test_parse_task_analysis_response_missing_fields(self, provider):
        """Test task analysis parsing with missing fields uses defaults"""
        response = json.dumps({"task_intent": "partial response"})

        result = provider._parse_task_analysis_response(response)

        assert result.task_intent == "partial response"
        assert result.semantic_dependencies == []
        assert result.confidence == 0.5  # Default

    def test_parse_task_analysis_response_invalid_json(self, provider):
        """Test task analysis parsing with invalid JSON"""
        response = "invalid json content"

        result = provider._parse_task_analysis_response(response)

        assert result.task_intent == "parse_error"
        assert "response_parsing_failed" in result.risk_factors
        assert result.confidence == 0.1

    def test_parse_dependency_response_success(self, provider):
        """Test successful dependency response parsing"""
        tasks = [Mock(id="task-1"), Mock(id="task-2"), Mock(id="task-3")]

        response = json.dumps(
            [
                {
                    "dependent_task_id": "task-2",
                    "dependency_task_id": "task-1",
                    "confidence": 0.9,
                    "reasoning": "logical dependency",
                    "dependency_type": "technical",
                }
            ]
        )

        result = provider._parse_dependency_response(response, tasks)

        assert len(result) == 1
        assert result[0].dependent_task_id == "task-2"
        assert result[0].confidence == 0.9
        assert result[0].dependency_type == "technical"

    def test_parse_dependency_response_invalid_json(self, provider):
        """Test dependency parsing with invalid JSON returns empty list"""
        tasks = [Mock(id="task-1")]
        response = "invalid json"

        result = provider._parse_dependency_response(response, tasks)

        assert result == []

    def test_parse_estimation_response_success(self, provider):
        """Test successful estimation response parsing"""
        response = json.dumps(
            {
                "estimated_hours": 15.5,
                "confidence": 0.75,
                "factors": ["complexity", "testing"],
                "similar_tasks": ["task_a", "task_b"],
                "risk_multiplier": 1.2,
            }
        )

        result = provider._parse_estimation_response(response)

        assert isinstance(result, EffortEstimate)
        assert result.estimated_hours == 15.5
        assert result.confidence == 0.75
        assert result.factors == ["complexity", "testing"]
        assert result.risk_multiplier == 1.2

    def test_parse_estimation_response_invalid_json(self, provider):
        """Test estimation parsing with invalid JSON returns fallback"""
        response = "invalid json"

        result = provider._parse_estimation_response(response)

        assert result.estimated_hours == 8.0
        assert result.confidence == 0.1
        assert "parsing_failed" in result.factors

    def test_parse_blocker_response_json_array(self, provider):
        """Test blocker response parsing with JSON array"""
        response = json.dumps(["Solution 1", "Solution 2", "Solution 3"])

        result = provider._parse_blocker_response(response)

        assert result == ["Solution 1", "Solution 2", "Solution 3"]

    def test_parse_blocker_response_json_string(self, provider):
        """Test blocker response parsing with JSON string"""
        response = json.dumps("Single solution")

        result = provider._parse_blocker_response(response)

        assert result == ["Single solution"]

    def test_parse_blocker_response_text_format(self, provider):
        """Test blocker response parsing with text format"""
        response = """
        - Check logs
        - Restart service
        # Comment line
        - Contact support
        """

        result = provider._parse_blocker_response(response)

        assert len(result) >= 3
        assert "Check logs" in result
        assert "Restart service" in result
        assert "Contact support" in result
        # Note: Comment lines might be included depending on parsing logic

    def test_parse_blocker_response_empty_fallback(self, provider):
        """Test blocker response parsing empty fallback"""
        response = ""

        result = provider._parse_blocker_response(response)

        assert result == ["Review task requirements"]


class TestOpenAIProviderComplete:
    """Test suite for complete method functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    async def test_complete_success(self, provider):
        """Test successful completion generation"""
        prompt = "Analyze this PRD and provide structured output"
        expected_response = "Here is the structured analysis of the PRD..."

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": expected_response}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete(prompt, max_tokens=2000)

        assert result == expected_response

        # Verify API call was made correctly
        provider.client.post.assert_called_once_with(
            f"{provider.base_url}/chat/completions",
            json={
                "model": provider.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.1,
            },
        )

    async def test_complete_custom_max_tokens(self, provider):
        """Test completion with custom max tokens"""
        prompt = "Short response please"
        expected_response = "Brief answer"
        custom_max_tokens = 500

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": expected_response}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        result = await provider.complete(prompt, max_tokens=custom_max_tokens)

        assert result == expected_response
        assert provider.max_tokens == custom_max_tokens

        # Verify max_tokens was updated
        provider.client.post.assert_called_once()
        call_args = provider.client.post.call_args[1]["json"]
        assert call_args["max_tokens"] == custom_max_tokens

    async def test_complete_api_error(self, provider):
        """Test completion with API error propagates exception"""
        prompt = "Test prompt"

        provider.client.post = AsyncMock(
            side_effect=httpx.TimeoutException("Request timed out")
        )

        with pytest.raises(Exception) as exc_info:
            await provider.complete(prompt)

        assert "OpenAI API request timed out" in str(exc_info.value)

    async def test_complete_http_error(self, provider):
        """Test completion with HTTP error"""
        prompt = "Test prompt"

        mock_response = Mock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError(
            "Rate limited", request=Mock(), response=mock_response
        )

        provider.client.post = AsyncMock(side_effect=error)

        with pytest.raises(Exception) as exc_info:
            await provider.complete(prompt)

        assert "OpenAI API error: 429" in str(exc_info.value)

    async def test_complete_preserves_max_tokens_state(self, provider):
        """Test that complete method preserves max_tokens state correctly"""
        original_max_tokens = provider.max_tokens
        prompt = "Test prompt"
        custom_max_tokens = 1000

        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()

        provider.client.post = AsyncMock(return_value=mock_response)

        # Call with custom max_tokens
        await provider.complete(prompt, max_tokens=custom_max_tokens)

        # Verify max_tokens was updated
        assert provider.max_tokens == custom_max_tokens

    async def test_complete_uses_call_openai_internally(self, provider):
        """Test that complete method uses _call_openai internally"""
        prompt = "Test prompt"
        expected_response = "Test response"

        # Mock _call_openai instead of client.post to test internal call
        provider._call_openai = AsyncMock(return_value=expected_response)

        result = await provider.complete(prompt)

        assert result == expected_response
        provider._call_openai.assert_called_once()

        # Verify the messages format passed to _call_openai
        call_args = provider._call_openai.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["role"] == "user"
        assert call_args[0]["content"] == prompt


class TestOpenAIProviderCleanup:
    """Test suite for provider cleanup functionality"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    async def test_close_client(self, provider):
        """Test HTTP client cleanup"""
        provider.client.aclose = AsyncMock()

        await provider.close()

        provider.client.aclose.assert_called_once()


@pytest.mark.unit
class TestOpenAIProviderIntegration:
    """Integration tests for OpenAI provider components"""

    @pytest.fixture
    def provider(self):
        """Create provider instance with mocked environment"""
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-api-key"}):
            return OpenAIProvider()

    def test_prompt_building_consistency(self, provider):
        """Test all prompt builders return non-empty strings"""
        task = Mock(
            id="test-id",
            name="Test Task",
            description="Test Description",
            priority=Mock(value="high"),
        )

        context = {"project_type": "test", "tech_stack": ["python"]}

        # Test all prompt builders
        task_prompt = provider._build_task_analysis_prompt(task, context)
        enhance_prompt = provider._build_enhancement_prompt(task, context)
        estimate_prompt = provider._build_estimation_prompt(task, context)
        blocker_prompt = provider._build_blocker_analysis_prompt(
            task, "blocker", context
        )

        assert len(task_prompt) > 0
        assert len(enhance_prompt) > 0
        assert len(estimate_prompt) > 0
        assert len(blocker_prompt) > 0

        # Verify task information appears in prompts
        assert "Test Task" in task_prompt
        assert "Test Task" in enhance_prompt
        assert "Test Task" in estimate_prompt
        assert "Test Task" in blocker_prompt

    def test_error_handling_consistency(self, provider):
        """Test error handling returns expected fallback structures"""
        # Test all parsing methods with invalid data
        invalid_json = "invalid json"

        analysis_result = provider._parse_task_analysis_response(invalid_json)
        dependency_result = provider._parse_dependency_response(invalid_json, [])
        estimation_result = provider._parse_estimation_response(invalid_json)
        blocker_result = provider._parse_blocker_response("")

        # Verify fallback structures are correct types
        assert isinstance(analysis_result, SemanticAnalysis)
        assert isinstance(dependency_result, list)
        assert isinstance(estimation_result, EffortEstimate)
        assert isinstance(blocker_result, list)

        # Verify fallback confidence levels are low
        assert analysis_result.confidence == 0.1
        assert estimation_result.confidence == 0.1
