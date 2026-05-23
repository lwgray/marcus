"""Unit tests for #607 step 5 — enterprise native-prompt tightening.

The pre-step-5 enterprise prompt at
``src/ai/advanced/prd/advanced_parser.py`` asked the LLM for
"15-30+ features", which trained the model to atomize a complex
enterprise project into 15-50 narrow functional requirements (and
therefore 16-51 ``Implement`` tasks on the board). Mechanism #3 from
issue #607.

Step 5 tightens the prompt so an enterprise project is described as
8-12 BROAD feature areas, each with a rich, concrete description that
bundles related concerns. The agent sees the full scope on a coarser
task instead of the scope being shredded across many narrow tasks.

These tests pin the prompt-template contract: a future edit that
re-introduces the "15-30+" language or drops the consolidation
guidance fails these tests.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.ai.advanced.prd.advanced_parser import (
    AdvancedPRDParser,
    ProjectConstraints,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def parser() -> AdvancedPRDParser:
    """Parser with mocked LLM dependencies."""
    with (
        patch("src.ai.advanced.prd.advanced_parser.LLMAbstraction"),
        patch("src.ai.advanced.prd.advanced_parser.HybridDependencyInferer"),
    ):
        p = AdvancedPRDParser()
        p.llm_client = Mock()
        p.llm_client.analyze = AsyncMock(return_value="{}")
        return p


async def _capture_prompt(parser: AdvancedPRDParser, complexity_mode: str) -> str:
    """Run ``_analyze_prd_deeply`` and capture the LLM prompt argument."""
    captured: dict[str, str] = {}

    async def fake_structured_call(
        *,
        llm: Any,
        prompt: str,
        operation: str,
        initial_max_tokens: int = 16384,
    ) -> dict:
        captured["prompt"] = prompt
        # Minimal valid PRD analysis response so the caller proceeds.
        return json.loads(
            '{"functional_requirements": [], "non_functional_requirements": [], '
            '"technical_constraints": [], "business_objectives": [], '
            '"user_personas": [], "success_metrics": [], '
            '"implementation_approach": "agile", "complexity_assessment": {}, '
            '"risk_factors": [], "confidence": 0.9, "domain": "other", '
            '"structuralCategory": "other"}'
        )

    constraints = ProjectConstraints(
        team_size=3,
        available_skills=["Python"],
        technology_constraints=[],
        complexity_mode=complexity_mode,
    )
    with patch(
        "src.utils.structured_llm.safe_structured_call",
        side_effect=fake_structured_call,
    ):
        await parser._analyze_prd_deeply("a todo app", constraints)
    return captured.get("prompt", "")


class TestEnterprisePromptCoarserFeatureCount:
    """#607 step 5: enterprise must ask for FEWER, COARSER features."""

    @pytest.mark.asyncio
    async def test_enterprise_does_not_request_15_to_30_plus_features(
        self, parser: AdvancedPRDParser
    ) -> None:
        """The legacy "15-30+ features" target trained over-decomposition."""
        prompt = await _capture_prompt(parser, "enterprise")
        # The legacy string must be gone from the enterprise guidance.
        assert "15-30+ features" not in prompt, (
            "#607 step 5: prompt still asks for '15-30+ features' at "
            "enterprise — this is mechanism #3 of over-decomposition. "
            "Should target a tighter band with richer descriptions."
        )

    @pytest.mark.asyncio
    async def test_enterprise_targets_coarser_feature_band(
        self, parser: AdvancedPRDParser
    ) -> None:
        """Replacement target band must be visibly in the prompt.

        Implementation must use a band like "8-12" or similar coarser
        count and identify it as the enterprise target. The exact
        wording can vary; what's tested is that the LLM sees an
        explicit numeric target lower than the legacy 15-30+.
        """
        prompt = await _capture_prompt(parser, "enterprise")
        # Some band-like phrasing in the enterprise section anchors
        # the LLM to a smaller count. We accept any range whose UPPER
        # bound is <= 15 (vs the legacy 30+).
        # Searching the enterprise section specifically.
        enterprise_idx = prompt.find("ENTERPRISE MODE")
        assert enterprise_idx >= 0, "ENTERPRISE MODE section missing"
        ent_section = prompt[enterprise_idx : enterprise_idx + 2000]
        # The new band must include an upper bound of 12-15 (not 30+).
        # Allow flexibility in the exact wording; pin only the band.
        import re

        bands = re.findall(
            r"(\d+)\s*[-–]\s*(\d+)\s+(?:features|broad|feature)", ent_section
        )
        assert bands, (
            f"No feature-count band found in enterprise section; "
            f"section excerpt: {ent_section[:300]!r}"
        )
        # At least one band's upper bound must be <= 15.
        upper_bounds = [int(hi) for _lo, hi in bands]
        assert min(upper_bounds) <= 15, (
            f"#607 step 5: enterprise feature-count band's upper bound is "
            f"{upper_bounds} — should be <= 15 to drive coarser features. "
            f"Bands found: {bands}"
        )


class TestEnterprisePromptRichDescriptionsGuidance:
    """The enterprise prompt must direct the LLM to RICHER descriptions,
    not MORE features.
    """

    @pytest.mark.asyncio
    async def test_enterprise_prompt_warns_against_more_narrower_features(
        self, parser: AdvancedPRDParser
    ) -> None:
        """Explicit guidance: coarser tasks + richer descriptions, not
        many narrow tasks.
        """
        prompt = await _capture_prompt(parser, "enterprise")
        # The guidance can be phrased many ways; check for the key
        # concept words.
        enterprise_idx = prompt.find("ENTERPRISE MODE")
        ent_section = prompt[enterprise_idx : enterprise_idx + 3000].lower()
        # Must mention "consolidate" or "bundle" or "coarser" — the
        # consolidation discipline that prevents over-decomposition.
        assert (
            "consolidate" in ent_section
            or "bundle" in ent_section
            or "coarser" in ent_section
            or "broader" in ent_section
        ), (
            "Enterprise section must direct the LLM to CONSOLIDATE / "
            "BUNDLE / use COARSER features instead of splitting widely. "
            f"Section excerpt: {ent_section[:400]!r}"
        )


class TestProtoTypeAndStandardPromptsUnchanged:
    """Step 5 only retargets ENTERPRISE; prototype + standard guidance
    untouched.
    """

    @pytest.mark.asyncio
    async def test_prototype_band_unchanged(self, parser: AdvancedPRDParser) -> None:
        """Prototype still targets 3-5 core features."""
        prompt = await _capture_prompt(parser, "prototype")
        assert "PROTOTYPE MODE" in prompt
        assert "3-5 core features" in prompt or "(3-5 " in prompt

    @pytest.mark.asyncio
    async def test_standard_band_unchanged(self, parser: AdvancedPRDParser) -> None:
        """Standard still targets 8-15 features."""
        prompt = await _capture_prompt(parser, "standard")
        assert "STANDARD MODE" in prompt
        assert "8-15 features" in prompt or "(8-15 " in prompt
