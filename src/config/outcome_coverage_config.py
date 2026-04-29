"""Feature flag for user-outcome coverage (issue #449).

Reads the ``MARCUS_OUTCOME_COVERAGE`` environment variable.  When the
flag is off (the default for v0.4.x), the entire intent-fidelity
pipeline (extraction, coverage check, gap-fill, score logging) is a
no-op — PRD analysis runs as it always has, no extra LLM calls fire,
and ``PRDAnalysis.user_outcomes`` stays empty.

The flag is opt-in for v0.4.x while the integration soaks; the plan
is to flip the default to ON once batch experiment runs confirm it
behaves correctly across project types and the LLM-cost / latency
budget impact is measured.
"""

from __future__ import annotations

import os

# Public constant.  Importable for tests that need to monkey-patch
# the env var or assert the canonical name.
ENV_VAR_NAME: str = "MARCUS_OUTCOME_COVERAGE"

_TRUTHY = frozenset({"1", "true", "yes", "on", "enabled"})


def is_outcome_coverage_enabled() -> bool:
    """Return ``True`` when the outcome-coverage pipeline is active.

    The pipeline is OFF by default for v0.4.x — opt-in via
    ``MARCUS_OUTCOME_COVERAGE`` during the integration soak.  Default
    will flip to ON in a later release once batch experiments
    validate behavior across project types.

    Set ``MARCUS_OUTCOME_COVERAGE`` to one of ``"1" | "true" | "yes"
    | "on" | "enabled"`` (case-insensitive) to enable.

    Returns
    -------
    bool
        ``True`` only when ``MARCUS_OUTCOME_COVERAGE`` is set to a
        recognized truthy value; ``False`` otherwise (including when
        the var is unset, empty, or set to an unknown value).
    """
    raw = os.environ.get(ENV_VAR_NAME, "").strip().lower()
    return raw in _TRUTHY
