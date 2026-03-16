"""
Integration tests for end-to-end task completeness validation.

These tests use real AI providers to verify the validation system works
with actual LLM responses.
"""

import pytest

from src.ai.advanced.prd.advanced_parser import AdvancedPRDParser
from src.ai.providers.llm_abstraction import LLMAbstraction
from src.ai.validation.task_completeness_validator import (
    TaskCompletenessValidator,
)
from src.core.error_framework import ErrorContext


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_validation_e2e() -> None:
    """
    Test validation catches missing MCP server setup.

    This is the real-world scenario that motivated this feature:
    Task decomposition created tools but missed the server.py file.
    """
    # Arrange
    description = (
        "Build an MCP server that wraps the Deck of Cards API. "
        "Create MCP tools for: create_deck, draw_cards, get_deck_status, shuffle_deck"
    )
    project_name = "deck-mcp-test"

    # Initialize real components
    ai_client = LLMAbstraction()
    prd_parser = AdvancedPRDParser()  # Would need proper initialization

    validator = TaskCompletenessValidator(
        ai_client=ai_client,
        prd_parser=prd_parser,
    )

    # Act - Extract intents
    intents = await validator.extract_intents(description, project_name)

    # Assert - Should identify MCP server as core intent
    assert len(intents) > 0
    # At least one intent should mention "server" or "MCP"
    server_related = any(
        "server" in intent.lower() or "mcp" in intent.lower() for intent in intents
    )
    assert server_related, f"Expected MCP server intent, got: {intents}"


# TODO: Add full end-to-end test once we have proper test fixtures
# This would require mocking the PRD parser or using a test Kanban instance
"""
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_validation_workflow():
    '''Test complete validation workflow with retry.'''
    # This requires significant setup:
    # - Mock or test PRD parser
    # - Sample task list that's incomplete
    # - Verify retry adds missing tasks
    pass
"""
