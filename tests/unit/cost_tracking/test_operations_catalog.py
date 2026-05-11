"""
Unit tests for ``src.cost_tracking.operations`` catalog.

Verifies:

- Catalog entries have the required shape.
- Every operation referenced by call sites in production code resolves
  to a real catalog entry, so the dashboard tooltip never falls through
  to the synthesized "Unregistered operation" label.
- ``get_operation`` gracefully synthesizes a fallback entry for unknown
  keys.
"""

from __future__ import annotations

from src.cost_tracking.operations import OPERATIONS, all_operations, get_operation


class TestCatalogShape:
    """Each catalog entry must have label, description, category."""

    def test_every_entry_has_required_fields(self) -> None:
        """All entries expose label/description/category as non-empty strings."""
        for key, entry in OPERATIONS.items():
            assert entry["label"], f"missing label for {key}"
            assert entry["description"], f"missing description for {key}"
            assert entry["category"], f"missing category for {key}"
            assert isinstance(entry["label"], str)
            assert isinstance(entry["description"], str)
            assert isinstance(entry["category"], str)

    def test_categories_are_from_known_set(self) -> None:
        """Categories must come from the documented set so the UI can group."""
        valid = {"decomposition", "runtime", "monitoring", "other"}
        for key, entry in OPERATIONS.items():
            assert (
                entry["category"] in valid
            ), f"{key} has unknown category {entry['category']}"


class TestGetOperation:
    """``get_operation`` looks up keys with a graceful fallback."""

    def test_returns_catalog_entry_when_known(self) -> None:
        """Known keys return the catalog entry verbatim."""
        entry = get_operation("decompose_prd")
        assert entry["category"] == "decomposition"
        assert "PRD" in entry["label"] or "prd" in entry["label"].lower()

    def test_synthesizes_fallback_for_unknown_key(self) -> None:
        """Unknown keys yield a synthesized entry in the 'other' category."""
        entry = get_operation("totally_made_up_op")
        assert entry["category"] == "other"
        assert "totally_made_up_op" in entry["description"]
        # Synthesized label should be a human-readable form of the key
        assert "Totally Made Up Op" in entry["label"]


class TestAllOperations:
    """``all_operations`` returns a defensive copy."""

    def test_returns_copy_not_reference(self) -> None:
        """Mutating the returned dict must not affect the canonical catalog."""
        copy = all_operations()
        copy["bogus_key_for_test"] = {  # type: ignore[typeddict-item]
            "label": "x",
            "description": "y",
            "category": "other",
        }
        assert "bogus_key_for_test" not in OPERATIONS


class TestCallSitesAreRegistered:
    """Spot-check that the operation keys used in production resolve.

    Misspellings or removed entries silently fall through to the
    generic 'analyze' bucket, which defeats the point of per-call
    drill-down. This test enforces the producer/consumer contract.
    """

    def test_known_call_site_keys_are_registered(self) -> None:
        """Every operation key used by ``llm_client.analyze(operation=...)``
        must be in the catalog.
        """
        expected = {
            "decompose_prd",
            "extract_outcomes",
            "outcome_coverage_check",
            "outcome_gap_fill",
            "filter_outcomes",
            "extract_spec_features",
            "discover_domains",
            "synthesize_foundation_tasks",
            "generate_design_artifact",
            "generate_design_decisions",
            "generate_project_scaffold",
            "generate_task_detail",
            "generate_contracts",
            "decompose_task",
            "validate_task_completeness",
            "validate_work",
            "analyze_blocker",
            "infer_dependencies",
            "enrich_task",
            "analyze_task_semantics",
            "estimate_effort",
            "analyze_project_health",
            "analyze",
        }
        missing = expected - set(OPERATIONS.keys())
        assert not missing, f"call-site keys missing from catalog: {missing}"
