"""Feature flag for setup-time gotcha enumeration (issue #680).

Reads the ``MARCUS_GOTCHA_ENUMERATION`` environment variable.

A "gotcha" is a known failure mode for a user outcome — a behavior that
a naive implementation gets wrong even though it satisfies the literal
task description. For a snake game, "pressing the opposite direction
should be ignored, not cause instant death" and "food must never spawn
on a cell occupied by the snake" are gotchas: the task says "handle
direction" and "spawn food", but the obvious implementation ships a
broken game.

When the flag is on (the default), the decomposition pipeline makes one
LLM call per outcome batch that enumerates these failure modes and
writes them into the ``acceptance_criteria`` of every task that covers
the outcome. Because ``request_next_task`` now delivers
``acceptance_criteria`` to the agent (issue #664) and the self-verify
skeptic reads the same field, the enumerated gotcha reaches both the
builder and the verifier — closing the "decomposition shatters the
gestalt" gap that a single agent would not have.

When the flag is off, the enumeration step is a no-op: no extra LLM
call fires and acceptance_criteria are left exactly as the outcome /
signal enrichment produced them.
"""

from __future__ import annotations

import os

# Public constant. Importable for tests that monkey-patch the env var
# or assert the canonical name.
ENV_VAR_NAME: str = "MARCUS_GOTCHA_ENUMERATION"

_FALSY = frozenset({"0", "false", "no", "off", "disabled"})


def is_gotcha_enumeration_enabled() -> bool:
    """Return ``True`` when setup-time gotcha enumeration is active.

    The step is ON by default. Set ``MARCUS_GOTCHA_ENUMERATION`` to one
    of ``"0" | "false" | "no" | "off" | "disabled"`` (case-insensitive)
    to disable — the pre-#680 behavior (no gotcha criteria) is the
    always-available fallback.

    Returns
    -------
    bool
        ``False`` only when ``MARCUS_GOTCHA_ENUMERATION`` is set to a
        recognized falsy value; ``True`` otherwise (including when the
        var is unset, empty, or set to an unknown value).
    """
    raw = os.environ.get(ENV_VAR_NAME, "").strip().lower()
    return raw not in _FALSY
