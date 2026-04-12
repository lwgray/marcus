"""
Unit tests for contract-first decomposition gate (GH-320 PR after #334).

Cross-contract type consistency (Invariant 5): when two generated
contract artifacts define the same field name with different types,
the contracts disagree and agents would build incompatible code.
This was the root cause of the WidgetPosition divergence in
Experiment 4 v2 (Python ``positionX (number)`` vs TypeScript
``positionX (string)``).

This is the only hard gate in ``_try_contract_first_decomposition``.
Requirement coverage (the "agents built plumbing but no UI" failure
mode) will be handled additively in task #64 by threading functional
requirements through the contract generation prompt and synthesizing
gap tasks for anything still uncovered — not by falling back to
feature-based (which would throw away contract-first's coordination
win).
"""

import pytest

from src.integrations.contract_validation import (
    check_contract_cross_file_consistency,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_artifact(
    filename: str,
    content: str,
    artifact_type: str = "specification",
) -> dict:
    """Build a minimal Phase A artifact dict."""
    return {
        "filename": filename,
        "content": content,
        "artifact_type": artifact_type,
        "relative_path": f"docs/specifications/{filename}",
        "description": "test artifact",
    }


# --------------------------------------------------------------------------
# Cross-contract type consistency (Invariant 5)
# --------------------------------------------------------------------------


class TestCheckContractCrossFileConsistency:
    """
    Test the cross-contract type consistency check.

    The contract artifacts dict shape comes from
    ``_generate_contracts_by_domain``: ``{domain_name -> {"artifacts":
    [artifact_dict, ...], "decisions": [...]}}``. Each artifact dict
    has ``filename``, ``content``, ``artifact_type``, etc.
    """

    def test_passes_with_no_contradictions(self):
        """
        Two contracts that define different field names → no
        contradictions, check passes.
        """
        contract_artifacts = {
            "Weather Information System": {
                "artifacts": [
                    _make_artifact(
                        "weather-information-system-interface-contracts.md",
                        "## Weather Data\n"
                        "- temperature (number) — current temperature\n"
                        "- conditions (string) — weather conditions\n",
                    ),
                ],
                "decisions": [],
            },
            "Time Display System": {
                "artifacts": [
                    _make_artifact(
                        "time-display-system-interface-contracts.md",
                        "## Time Data\n"
                        "- timezone (string) — IANA timezone\n"
                        "- updateInterval (number) — seconds\n",
                    ),
                ],
                "decisions": [],
            },
        }

        result = check_contract_cross_file_consistency(contract_artifacts)
        assert result["pass"] is True
        assert result["contradictions"] == []
        assert result["files_scanned"] == 2

    def test_passes_when_same_field_has_same_type_across_files(self):
        """
        Two contracts both reference ``id (string)`` — that's not a
        contradiction, that's coherent. Skip identifiers like ``id``
        explicitly because they always alias.
        """
        contract_artifacts = {
            "Domain A": {
                "artifacts": [
                    _make_artifact(
                        "domain-a-interface-contracts.md",
                        "- timestamp (number) — unix epoch\n",
                    ),
                ],
                "decisions": [],
            },
            "Domain B": {
                "artifacts": [
                    _make_artifact(
                        "domain-b-interface-contracts.md",
                        "- timestamp (number) — unix epoch\n",
                    ),
                ],
                "decisions": [],
            },
        }

        result = check_contract_cross_file_consistency(contract_artifacts)
        assert result["pass"] is True

    def test_fails_on_widget_position_field_collision(self):
        """
        Regression test for Experiment 4 v2 WidgetPosition bug.

        Python contract used physical grid coords (number); TypeScript
        used CSS Grid coords with composite types. Both refer to
        ``position_x`` (or normalized to the same canonical field
        name) but disagree on type. This is the exact case the gate
        must catch before agents build incompatible implementations.
        """
        contract_artifacts = {
            "Python Layout": {
                "artifacts": [
                    _make_artifact(
                        "python-layout-interface-contracts.md",
                        "## WidgetPosition\n"
                        "- positionX (number) — horizontal grid coordinate\n"
                        "- positionY (number) — vertical grid coordinate\n",
                    ),
                ],
                "decisions": [],
            },
            "TS Layout": {
                "artifacts": [
                    _make_artifact(
                        "ts-layout-interface-contracts.md",
                        "## WidgetPosition\n"
                        "- positionX (string) — CSS grid-column property\n"
                        "- positionY (string) — CSS grid-row property\n",
                    ),
                ],
                "decisions": [],
            },
        }

        result = check_contract_cross_file_consistency(contract_artifacts)
        assert result["pass"] is False, (
            f"Expected fail on WidgetPosition collision, got " f"{result}"
        )
        contradictions = result["contradictions"]
        assert len(contradictions) >= 1
        # The contradiction must name the field and report types
        # from BOTH files so the operator can see what disagreed.
        positionx_contradiction = next(
            (c for c in contradictions if c["field"] == "positionx"),
            None,
        )
        assert positionx_contradiction is not None, (
            f"Missing contradiction for positionx; got "
            f"{[c['field'] for c in contradictions]}"
        )
        assert len(positionx_contradiction["types_by_file"]) == 2

    def test_fewer_than_two_contract_files_always_passes(self):
        """
        With 0 or 1 contract files there's nothing to cross-check,
        so the gate must not block.
        """
        # Zero contracts
        result = check_contract_cross_file_consistency({})
        assert result["pass"] is True
        assert result["files_scanned"] == 0

        # One contract
        single = {
            "Solo": {
                "artifacts": [
                    _make_artifact(
                        "solo-interface-contracts.md",
                        "- field (number)\n",
                    ),
                ],
                "decisions": [],
            },
        }
        result = check_contract_cross_file_consistency(single)
        assert result["pass"] is True
        assert result["files_scanned"] == 1

    def test_skips_non_interface_contracts_artifacts(self):
        """
        ``_generate_contracts_by_domain`` produces multiple artifact
        types per domain (architecture, api_contracts, data_models,
        interface_contracts). Only ``interface_contracts`` carries
        the type definitions we cross-check; the others are prose.
        """
        contract_artifacts = {
            "Domain A": {
                "artifacts": [
                    _make_artifact(
                        "domain-a-architecture.md",
                        "- timestamp (number) — design note\n",
                        artifact_type="architecture",
                    ),
                    _make_artifact(
                        "domain-a-interface-contracts.md",
                        "- timestamp (number)\n",
                    ),
                ],
                "decisions": [],
            },
            "Domain B": {
                "artifacts": [
                    _make_artifact(
                        "domain-b-architecture.md",
                        "- timestamp (string) — different prose, different type\n",
                        artifact_type="architecture",
                    ),
                    _make_artifact(
                        "domain-b-interface-contracts.md",
                        "- timestamp (number)\n",
                    ),
                ],
                "decisions": [],
            },
        }

        # The (number) vs (string) collision is in architecture
        # artifacts, NOT interface_contracts. The gate ignores
        # architecture prose so this should pass.
        result = check_contract_cross_file_consistency(contract_artifacts)
        assert result["pass"] is True, (
            f"Architecture artifacts should not be cross-checked. " f"Got: {result}"
        )

    def test_handles_none_payload_gracefully(self):
        """
        ``_generate_contracts_by_domain`` returns ``None`` for
        domains where contract generation produced no usable
        output. The gate must skip those domains, not crash.
        """
        contract_artifacts = {
            "Empty Domain": None,
            "Real Domain": {
                "artifacts": [
                    _make_artifact(
                        "real-interface-contracts.md",
                        "- field (string)\n",
                    ),
                ],
                "decisions": [],
            },
        }

        result = check_contract_cross_file_consistency(contract_artifacts)
        assert result["pass"] is True
        # Only one file actually scanned
        assert result["files_scanned"] == 1
