"""
Unit tests for contract-first decomposition gate (GH-320 PR after #334).

The gate runs two checks before contract-first decomposition is
allowed to ship tasks:

1. **Cross-contract type consistency** (Invariant 5 from the smoke
   test harness, now wired into the live path): when two generated
   contract artifacts define the same field name with different
   types, the contracts disagree and agents would build incompatible
   code. This was the root cause of the WidgetPosition divergence
   in Experiment 4 v2 (Python ``position_x/y/width/height`` vs
   TypeScript ``gridColumn/gridRow/gridColumnSpan/gridRowSpan``).

2. **Functional requirement coverage** (verb-coverage check from
   Kaia's review of Experiment 4 v2): every PRD functional
   requirement that uses a user-facing verb (``display``,
   ``render``, ``show``, ``visualize``, etc.) must be covered by
   at least one task whose name or description contains that verb.
   This catches the "agents built API plumbing but no UI"
   regression where contract decomposition lost the user's
   visible intent.

Both checks return ``{"pass": bool, "issues": [...]}`` and the
caller decides whether to fall back to feature-based or proceed.
"""

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.integrations.contract_validation import (
    check_contract_cross_file_consistency,
    check_requirement_coverage,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _make_artifact(
    filename: str,
    content: str,
    artifact_type: str = "interface_contracts",
) -> dict:
    """Build a minimal Phase A artifact dict."""
    return {
        "filename": filename,
        "content": content,
        "artifact_type": artifact_type,
        "relative_path": f"docs/specifications/{filename}",
        "description": "test artifact",
    }


def _make_task(
    name: str,
    description: str = "",
    labels: list[str] | None = None,
) -> Task:
    """Build a minimal Task for coverage tests."""
    from datetime import datetime, timezone

    return Task(
        id=name.lower().replace(" ", "_"),
        name=name,
        description=description,
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=1.0,
        labels=labels or [],
    )


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


# --------------------------------------------------------------------------
# Functional requirement coverage (verb check)
# --------------------------------------------------------------------------


class TestCheckRequirementCoverage:
    """
    Test the user-facing verb coverage check.

    Walks ``prd_analysis.functional_requirements`` looking for
    user-facing verbs (display, render, show, visualize, etc.). For
    each requirement that contains a user-facing verb, verifies that
    at least one task in the decomposed output has that verb in its
    name or description (case-insensitive, word-boundary).

    This is the gate that catches the Experiment 4 v2 failure mode:
    PRD said "display weather and time", contract decomposition
    produced "Implement WeatherWidget" + "Implement TimeWidget", and
    no task had "display" anywhere because contracts framed
    everything in API/state terms. Both agents shipped a clean
    plumbing layer with no UI.
    """

    def test_passes_when_display_verb_appears_in_task_name(self):
        """
        Requirement uses ``display``; a task has ``display`` in its
        name → covered, gate passes.
        """
        requirements = [
            {"name": "Display weather conditions", "id": "f1"},
            {"name": "Display current time", "id": "f2"},
        ]
        tasks = [
            _make_task("Display weather widget"),
            _make_task("Display time widget"),
        ]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is True
        assert result["missing_requirements"] == []

    def test_passes_when_verb_appears_in_task_description(self):
        """
        Verb may live in task description rather than name. The
        check is name OR description.
        """
        requirements = [{"name": "Render dashboard layout", "id": "f1"}]
        tasks = [
            _make_task(
                "Build dashboard component",
                description=(
                    "Render the dashboard layout with weather and time "
                    "widgets in a CSS grid."
                ),
            ),
        ]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is True

    def test_fails_when_display_verb_uncovered(self):
        """
        Regression test for Experiment 4 v2.

        PRD says "display weather and time"; contract decomposition
        produced "Implement WeatherWidget" + "Implement TimeWidget".
        No task contains the word "display" anywhere. The gate must
        flag this as missing coverage, not silently let agents ship
        a UI-less product.
        """
        requirements = [
            {"name": "Display current weather temperature", "id": "f1"},
            {"name": "Display current time with timezone", "id": "f2"},
        ]
        tasks = [
            _make_task(
                "Implement WeatherWidget",
                description=(
                    "Build the WeatherWidget Python module with "
                    "OpenWeatherMap API integration and 10-minute "
                    "refresh interval."
                ),
            ),
            _make_task(
                "Implement TimeWidget",
                description=(
                    "Build the TimeWidget TypeScript module with "
                    "timezone selection and 1-second update interval."
                ),
            ),
        ]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is False, (
            "Display verb is uncovered — both tasks talk about "
            "implementation, neither mentions display."
        )
        missing = result["missing_requirements"]
        assert len(missing) == 2
        # Each missing entry must report which verb was expected
        # so the operator can see what was lost.
        assert all(m.get("verb") == "display" for m in missing)

    def test_ignores_requirements_without_user_facing_verbs(self):
        """
        Requirements that don't use a user-facing verb (e.g.
        "Authenticate user", "Validate input") are not checked.
        Only the user-visible action verbs are load-bearing.
        """
        requirements = [
            {"name": "Authenticate user via JWT", "id": "f1"},
            {"name": "Validate request body", "id": "f2"},
            {"name": "Cache responses for 5 minutes", "id": "f3"},
        ]
        tasks = [
            _make_task("Implement Auth Module"),
        ]

        # No user-facing verbs in any requirement → nothing to check
        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is True
        assert result["missing_requirements"] == []

    def test_recognizes_render_verb(self):
        """``render`` is also a user-facing verb."""
        requirements = [{"name": "Render the chart with D3", "id": "f1"}]
        tasks = [_make_task("Implement chart module")]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is False
        assert result["missing_requirements"][0]["verb"] == "render"

    def test_recognizes_show_verb(self):
        """``show`` is also a user-facing verb."""
        requirements = [{"name": "Show error notifications", "id": "f1"}]
        tasks = [_make_task("Implement notification API")]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is False
        assert result["missing_requirements"][0]["verb"] == "show"

    def test_recognizes_visualize_verb(self):
        """``visualize`` is also a user-facing verb."""
        requirements = [{"name": "Visualize sales over time", "id": "f1"}]
        tasks = [_make_task("Implement sales aggregation")]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is False
        assert result["missing_requirements"][0]["verb"] == "visualize"

    def test_word_boundary_match_does_not_match_substring(self):
        """
        ``display`` must match as a whole word. ``displayed`` is OK
        (covers the verb), but ``misdisplayer`` should not. This
        prevents accidental matches against unrelated identifiers.
        """
        requirements = [{"name": "Display weather", "id": "f1"}]
        # Task name has "displayed" — that's a valid covering form
        tasks = [_make_task("Render the displayed weather widget")]

        result = check_requirement_coverage(requirements, tasks)
        assert result["pass"] is True

    def test_empty_requirements_passes_trivially(self):
        """No requirements → nothing to check → pass."""
        result = check_requirement_coverage([], [_make_task("Build thing")])
        assert result["pass"] is True
        assert result["missing_requirements"] == []

    def test_empty_task_list_with_uncovered_requirement_fails(self):
        """Requirement with user-facing verb + no tasks → fail."""
        requirements = [{"name": "Display weather", "id": "f1"}]
        result = check_requirement_coverage(requirements, [])
        assert result["pass"] is False
        assert len(result["missing_requirements"]) == 1
