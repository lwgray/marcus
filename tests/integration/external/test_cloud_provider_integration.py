"""
Integration tests for CloudLLMProvider against Fireworks AI.

Skipped unless FIREWORKS_API_KEY is set in the environment.

Run with:
    FIREWORKS_API_KEY=fw_... pytest tests/integration/external/test_cloud_provider_integration.py -v

The model defaults to the Fireworks-hosted Qwen model but can be overridden:
    FIREWORKS_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct ...
"""

import os
from datetime import datetime, timezone

import pytest

FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY", "")
FIREWORKS_URL = "https://api.fireworks.ai/inference/v1"
# Override with FIREWORKS_MODEL env var to point at any accessible model.
# The default is a private deployment — set FIREWORKS_MODEL to a public
# Fireworks model ID if using a different API key.
FIREWORKS_MODEL = os.getenv(
    "FIREWORKS_MODEL",
    "accounts/fireworks/models/qwen2p5-coder-7b-instruct",
)

pytestmark = pytest.mark.skipif(
    not FIREWORKS_API_KEY,
    reason="FIREWORKS_API_KEY not set — skipping Fireworks integration tests",
)


@pytest.fixture
def provider():
    """Build a real CloudLLMProvider pointed at Fireworks."""
    from unittest.mock import Mock, patch

    from src.ai.providers.cloud_provider import CloudLLMProvider

    mock_cfg = Mock()
    mock_cfg.ai.max_tokens = 512
    mock_cfg.ai.temperature = 0.1

    with patch("src.config.marcus_config.get_config", return_value=mock_cfg):
        return CloudLLMProvider(
            model=FIREWORKS_MODEL,
            api_key=FIREWORKS_API_KEY,
            url=FIREWORKS_URL,
        )


def _make_task():
    from src.core.models import Priority, Task, TaskStatus

    return Task(
        id="fw-int-1",
        name="Implement user authentication endpoint",
        description="Add JWT-based login endpoint to the FastAPI app",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=4.0,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fireworks_complete_returns_string(provider) -> None:
    """Real call to Fireworks: complete() must return a non-empty string."""
    result = await provider.complete("Say hello in one word.")
    assert isinstance(result, str)
    assert result.strip(), "Expected non-empty response from Fireworks"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fireworks_analyze_task_returns_real_analysis(provider) -> None:
    """Real call to Fireworks: analyze_task must return a genuine response.

    We detect silent fallback by checking task_intent is not the sentinel
    value 'unknown' that LocalLLMProvider uses when the API call fails.
    """
    from src.ai.providers.base_provider import SemanticAnalysis

    result = await provider.analyze_task(_make_task(), {"project_type": "api"})

    assert isinstance(result, SemanticAnalysis)
    assert result.task_intent not in (
        "unknown",
        "parse_error",
    ), (
        f"Got fallback sentinel intent '{result.task_intent}' — "
        "the API call likely failed silently"
    )
    assert 0.0 <= result.confidence <= 1.0
    # A real response should have higher confidence than the 0.1 fallback
    assert result.confidence > 0.1, (
        f"Confidence {result.confidence} matches the silent-fallback value "
        "(0.1) — the API call may have failed"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fireworks_estimate_effort_returns_real_estimate(
    provider,
) -> None:
    """Real call to Fireworks: estimate_effort must return real model output.

    Silent fallback returns exactly estimated_hours=8.0 and confidence=0.3;
    we check that we got something different.
    """
    from src.ai.providers.base_provider import EffortEstimate

    result = await provider.estimate_effort(
        _make_task(), {"tech_stack": ["python", "fastapi"]}
    )

    assert isinstance(result, EffortEstimate)
    assert result.estimated_hours > 0.0
    assert 0.0 <= result.confidence <= 1.0
    # Fallback sentinel is confidence=0.3 with factors=["parse_error"]
    assert (
        "parse_error" not in result.factors
    ), "Got parse-error fallback — the API call likely failed silently"
