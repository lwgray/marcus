"""Unit tests for PRD project classification (Marcus #546 Phase 0).

The PRD-analysis LLM call is asked to bucket each project into a
``domain`` and a ``structural_category``.  These two labels feed Phase
0 cost persistence and the ``project_created`` telemetry event.  The
privacy guarantee is that only a fixed taxonomy bucket ever leaves the
machine — never the free-text answer the LLM produced.  These tests
pin that guarantee on the ``_bucket_label`` normalizer and verify the
labels survive the ``PRDAnalysis`` -> ``TaskGenerationResult`` hand-off.
"""

from __future__ import annotations

import pytest

from src.ai.advanced.prd.advanced_parser import (
    DOMAIN_BUCKETS,
    STRUCTURAL_CATEGORY_BUCKETS,
    TECH_STACK_BUCKETS,
    PRDAnalysis,
    TaskGenerationResult,
    _bucket_label,
    _normalize_tech_stack,
)

pytestmark = pytest.mark.unit


class TestBucketLabel:
    """``_bucket_label`` collapses any LLM answer to a known bucket."""

    def test_exact_match_passes_through(self) -> None:
        assert _bucket_label("fintech", DOMAIN_BUCKETS) == "fintech"
        assert (
            _bucket_label("data pipeline", STRUCTURAL_CATEGORY_BUCKETS)
            == "data pipeline"
        )

    def test_case_insensitive_match_normalizes_to_canonical(self) -> None:
        """Casing drift is normalized to the canonical taxonomy spelling."""
        assert _bucket_label("FinTech", DOMAIN_BUCKETS) == "fintech"
        assert _bucket_label("  ML/AI  ", STRUCTURAL_CATEGORY_BUCKETS) == "ML/AI"

    def test_off_taxonomy_label_collapses_to_other(self) -> None:
        """An LLM hallucination outside the taxonomy becomes 'other'.

        This is the privacy guard: a free-text answer like a project
        name can never leak — it is forced into 'other'.
        """
        assert _bucket_label("crypto-mining-rig", DOMAIN_BUCKETS) == "other"
        assert (
            _bucket_label("a snake game for my nephew", STRUCTURAL_CATEGORY_BUCKETS)
            == "other"
        )

    def test_missing_or_blank_label_collapses_to_unknown(self) -> None:
        assert _bucket_label(None, DOMAIN_BUCKETS) == "unknown"
        assert _bucket_label("", DOMAIN_BUCKETS) == "unknown"
        assert _bucket_label("   ", STRUCTURAL_CATEGORY_BUCKETS) == "unknown"

    def test_non_string_input_does_not_raise(self) -> None:
        """Non-string LLM junk is coerced, never raises."""
        assert _bucket_label(42, DOMAIN_BUCKETS) == "other"
        assert _bucket_label(["nested"], DOMAIN_BUCKETS) == "other"

    def test_every_bucket_is_its_own_label(self) -> None:
        """Each taxonomy member round-trips to itself."""
        for bucket in DOMAIN_BUCKETS:
            assert _bucket_label(bucket, DOMAIN_BUCKETS) == bucket
        for bucket in STRUCTURAL_CATEGORY_BUCKETS:
            assert _bucket_label(bucket, STRUCTURAL_CATEGORY_BUCKETS) == bucket


class TestTaxonomyContract:
    """The taxonomies must match what docs/telemetry.md discloses."""

    def test_domain_buckets_match_disclosure(self) -> None:
        assert DOMAIN_BUCKETS == frozenset(
            {
                "fintech",
                "healthtech",
                "edtech",
                "ecommerce",
                "social",
                "productivity",
                "devtools",
                "gaming",
                "media",
                "iot",
                "data_analytics",
                "ml_ai",
                "enterprise",
                "consumer",
                "other",
            }
        )

    def test_structural_category_buckets_match_disclosure(self) -> None:
        assert STRUCTURAL_CATEGORY_BUCKETS == frozenset(
            {
                "web app",
                "data pipeline",
                "CLI tool",
                "game",
                "API service",
                "ML/AI",
                "library",
                "automation",
                "other",
            }
        )


class TestNormalizeTechStack:
    """``_normalize_tech_stack`` buckets detected tech to a fixed taxonomy."""

    def test_exact_taxonomy_labels_pass_through(self) -> None:
        out = _normalize_tech_stack(["python", "react", "postgres"])
        assert out == ["python", "react", "postgres"]

    def test_aliases_normalize_to_canonical(self) -> None:
        """Common aliases map to their canonical bucket."""
        assert _normalize_tech_stack(["js"]) == ["javascript"]
        assert _normalize_tech_stack(["postgresql"]) == ["postgres"]
        assert _normalize_tech_stack(["k8s"]) == ["kubernetes"]
        assert _normalize_tech_stack(["nodejs"]) == ["node"]

    def test_separator_and_case_variants_collapse(self) -> None:
        """'React Native', 'react-native', 'react_native' all → react_native."""
        for variant in ("React Native", "react-native", "react_native"):
            assert _normalize_tech_stack([variant]) == ["react_native"]

    def test_off_taxonomy_label_becomes_other(self) -> None:
        """An unrecognized / hallucinated label collapses to 'other'.

        Privacy guard: a free-text label that could echo project
        detail can never ship — it is forced to 'other'.
        """
        out = _normalize_tech_stack(["my-secret-internal-framework"])
        assert out == ["other"]

    def test_duplicate_buckets_deduped(self) -> None:
        """Multiple raw labels mapping to the same bucket yield one entry."""
        out = _normalize_tech_stack(["js", "javascript", "JS"])
        assert out == ["javascript"]

    def test_missing_or_junk_input(self) -> None:
        """None / empty / non-string entries never raise; non-strings drop."""
        assert _normalize_tech_stack(None) == []
        assert _normalize_tech_stack([]) == []
        # Non-string items are skipped, not coerced — result is empty.
        assert _normalize_tech_stack([42, None, {"x": 1}]) == []
        # A real string mixed with junk: the string still buckets.
        assert _normalize_tech_stack([42, "python", None]) == ["python"]

    def test_every_bucket_round_trips(self) -> None:
        """Each taxonomy member normalizes to itself."""
        for bucket in TECH_STACK_BUCKETS:
            assert _normalize_tech_stack([bucket]) == [bucket]


class TestClassificationDefaults:
    """``PRDAnalysis`` / ``TaskGenerationResult`` default to 'unknown'."""

    def test_prd_analysis_defaults_to_unknown(self) -> None:
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
        assert analysis.domain == "unknown"
        assert analysis.structural_category == "unknown"

    def test_task_generation_result_defaults_to_unknown(self) -> None:
        result = TaskGenerationResult(
            tasks=[],
            task_hierarchy={},
            dependencies=[],
            risk_assessment={},
            estimated_timeline={},
            resource_requirements={},
            success_criteria=[],
            generation_confidence=0.8,
        )
        assert result.domain == "unknown"
        assert result.structural_category == "unknown"
