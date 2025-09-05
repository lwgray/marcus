"""
Unit tests for Intelligent Task Enricher initialization.

This module tests the initialization and configuration of the IntelligentTaskEnricher
class, ensuring proper setup of default settings and standard labels.

Notes
-----
All external AI provider calls are mocked to ensure fast, reliable tests that
don't depend on external services or consume API quotas.
"""

from unittest.mock import patch

import pytest

from src.ai.enrichment.intelligent_enricher import IntelligentTaskEnricher


class TestIntelligentTaskEnricherInitialization:
    """Test suite for IntelligentTaskEnricher initialization"""

    def test_initialization_default_settings(self):
        """Test enricher initializes with default settings"""
        with patch("src.ai.enrichment.intelligent_enricher.LLMAbstraction") as mock_llm:
            enricher = IntelligentTaskEnricher()

            # Verify LLM client is initialized
            mock_llm.assert_called_once()
            assert enricher.llm_client is not None

            # Verify default settings
            assert enricher.enhancement_confidence_threshold == 0.7
            assert enricher.max_description_length == 500
            assert enricher.max_acceptance_criteria == 5

            # Verify standard labels structure
            assert "component" in enricher.standard_labels
            assert "type" in enricher.standard_labels
            assert "priority" in enricher.standard_labels
            assert "complexity" in enricher.standard_labels
            assert "phase" in enricher.standard_labels

            # Verify label categories
            assert "frontend" in enricher.standard_labels["component"]
            assert "backend" in enricher.standard_labels["component"]
            assert "feature" in enricher.standard_labels["type"]
            assert "bugfix" in enricher.standard_labels["type"]

    def test_standard_labels_completeness(self):
        """Test all standard label categories are properly defined"""
        with patch("src.ai.enrichment.intelligent_enricher.LLMAbstraction"):
            enricher = IntelligentTaskEnricher()

            # Component labels
            expected_components = [
                "frontend",
                "backend",
                "database",
                "api",
                "ui",
                "infrastructure",
            ]
            assert all(
                comp in enricher.standard_labels["component"]
                for comp in expected_components
            )

            # Type labels
            expected_types = [
                "feature",
                "bugfix",
                "enhancement",
                "refactor",
                "test",
                "documentation",
            ]
            assert all(
                type_label in enricher.standard_labels["type"]
                for type_label in expected_types
            )

            # Priority labels
            expected_priorities = ["urgent", "high", "medium", "low"]
            assert all(
                priority in enricher.standard_labels["priority"]
                for priority in expected_priorities
            )

            # Complexity labels
            expected_complexity = ["simple", "moderate", "complex"]
            assert all(
                complexity in enricher.standard_labels["complexity"]
                for complexity in expected_complexity
            )

            # Phase labels
            expected_phases = [
                "design",
                "implementation",
                "testing",
                "deployment",
                "maintenance",
            ]
            assert all(
                phase in enricher.standard_labels["phase"] for phase in expected_phases
            )
