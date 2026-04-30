"""Feature flag for user-outcome coverage (issue #449).

Reads the ``MARCUS_OUTCOME_COVERAGE`` environment variable.  When the
flag is on (the default for v0.3.6.post1+), the intent-fidelity
pipeline runs: extracts user outcomes from the spec, runs a coverage
check against the freshly-decomposed task graph, synthesizes gap-fill
tasks for uncovered outcomes, and emits a ``PLANNING_INTENT_FIDELITY``
event with ``intent_fidelity_score``.

When the flag is off, the entire pipeline is a no-op — PRD analysis
runs as it always has, no extra LLM calls fire, and
``PRDAnalysis.user_outcomes`` stays empty.

The flag was opt-in in 0.3.6 while the integration soaked; flipped on
by default in 0.3.6.post1 after positive signal from snake_game-v38
(coverage produced more implementation tasks) and the broader
multi-domain decomposer audit.  Cost / latency measurement remains
tracked in #409 for the data-driven decision to make the pipeline
non-optional.
"""

from __future__ import annotations

import os

# Public constant.  Importable for tests that need to monkey-patch
# the env var or assert the canonical name.
ENV_VAR_NAME: str = "MARCUS_OUTCOME_COVERAGE"

_FALSY = frozenset({"0", "false", "no", "off", "disabled"})


def is_outcome_coverage_enabled() -> bool:
    """Return ``True`` when the outcome-coverage pipeline is active.

    The pipeline is ON by default as of 0.3.6.post1.  Set
    ``MARCUS_OUTCOME_COVERAGE`` to one of ``"0" | "false" | "no" |
    "off" | "disabled"`` (case-insensitive) to disable — the legacy
    pre-#449 decomposer behavior is the always-available fallback for
    debugging.

    Returns
    -------
    bool
        ``False`` only when ``MARCUS_OUTCOME_COVERAGE`` is set to a
        recognized falsy value; ``True`` otherwise (including when
        the var is unset, empty, or set to an unknown value).
    """
    raw = os.environ.get(ENV_VAR_NAME, "").strip().lower()
    return raw not in _FALSY
