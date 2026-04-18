"""
Decomposer strategy selection (GH-320 PR 2).

Resolves which task decomposition strategy to use at project creation
time. Two strategies are supported:

- **feature_based** (default): the legacy path. Tasks are shaped by
  functional requirements from the PRD.
  :func:`src.ai.advanced.prd.advanced_parser.AdvancedPRDParser.parse_prd_to_tasks`.
- **contract_first**: tasks are shaped by contract interfaces generated
  before decomposition. Each task owns one side of a contract.
  :func:`src.ai.advanced.prd.advanced_parser.AdvancedPRDParser.decompose_by_contract`.

Selection precedence (highest to lowest):

1. Explicit ``options["decomposer"]`` passed to ``create_project``
2. ``MARCUS_DECOMPOSER`` environment variable
3. Default: ``contract_first``

Rationale
---------
Options-dict precedence lets callers (experiment runners, tests, CI)
override the environment at call time without touching process state.
Environment variable precedence lets operators flip the strategy for a
running Marcus server without restarting. ``contract_first`` is the
default as of v0.3.4: it generates domain contracts synchronously
inside ``create_project``, so the board is complete before any agent
starts — no Phase A race. Use ``MARCUS_DECOMPOSER=feature_based`` or
pass ``options["decomposer"] = "feature_based"`` to revert to the
legacy path for loosely-coupled projects.

See Also
--------
src.ai.advanced.prd.advanced_parser.AdvancedPRDParser.decompose_by_contract :
    The contract-first decomposer implementation.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Literal, Optional

logger = logging.getLogger(__name__)

# Literal type for the decomposer strategy. Downstream callers that
# need exhaustiveness checking (match statements, type guards) can
# import this and get compile-time verification that they're handling
# every valid strategy.
DecomposerStrategy = Literal["feature_based", "contract_first"]

DECOMPOSER_FEATURE_BASED: DecomposerStrategy = "feature_based"
DECOMPOSER_CONTRACT_FIRST: DecomposerStrategy = "contract_first"

VALID_DECOMPOSERS: set[DecomposerStrategy] = {
    DECOMPOSER_FEATURE_BASED,
    DECOMPOSER_CONTRACT_FIRST,
}

ENV_VAR = "MARCUS_DECOMPOSER"


def resolve_decomposer(
    options: Optional[Dict[str, Any]] = None,
) -> DecomposerStrategy:
    """
    Resolve the active decomposer strategy from options and environment.

    Parameters
    ----------
    options : Optional[Dict[str, Any]]
        Options dict passed to ``create_project``. If it contains a
        ``"decomposer"`` key with a valid strategy name, that wins.

    Returns
    -------
    DecomposerStrategy
        Either ``"feature_based"`` or ``"contract_first"``. The
        ``DecomposerStrategy`` literal type lets callers use
        exhaustive match/if-else without defensive fallthroughs.

    Notes
    -----
    Unknown strategy values (from either source) trigger a loud
    warning and fall back to ``"feature_based"``. Silent fallbacks
    would hide configuration errors — the user asked for
    ``contract_first`` and got feature_based without knowing. Loud
    warning surfaces the problem at project creation time.

    Examples
    --------
    >>> resolve_decomposer({"decomposer": "contract_first"})
    'contract_first'
    >>> resolve_decomposer(None)  # MARCUS_DECOMPOSER unset
    'contract_first'
    >>> # With MARCUS_DECOMPOSER=contract_first in env
    >>> resolve_decomposer(None)
    'contract_first'
    """
    if options is not None:
        explicit = options.get("decomposer")
        if explicit is not None:
            if explicit in VALID_DECOMPOSERS:
                logger.info(f"[decomposer] Using '{explicit}' from options dict")
                # cast via local variable so mypy narrows the type
                validated: DecomposerStrategy = explicit
                return validated
            logger.warning(
                f"[decomposer] Unknown strategy '{explicit}' in options; "
                f"falling back to '{DECOMPOSER_FEATURE_BASED}'. "
                f"Valid strategies: {sorted(VALID_DECOMPOSERS)}"
            )
            return DECOMPOSER_FEATURE_BASED

    env_value = os.environ.get(ENV_VAR)
    if env_value is not None:
        if env_value in VALID_DECOMPOSERS:
            logger.info(f"[decomposer] Using '{env_value}' from {ENV_VAR}")
            validated_env: DecomposerStrategy = env_value  # type: ignore[assignment]
            return validated_env
        logger.warning(
            f"[decomposer] Unknown strategy '{env_value}' in {ENV_VAR}; "
            f"falling back to '{DECOMPOSER_FEATURE_BASED}'. "
            f"Valid strategies: {sorted(VALID_DECOMPOSERS)}"
        )
        return DECOMPOSER_FEATURE_BASED

    return DECOMPOSER_CONTRACT_FIRST


def is_contract_first(options: Optional[Dict[str, Any]] = None) -> bool:
    """
    Return True if the contract-first decomposer is active.

    Convenience wrapper around :func:`resolve_decomposer`.

    Parameters
    ----------
    options : Optional[Dict[str, Any]]
        Options dict passed to ``create_project``.

    Returns
    -------
    bool
        ``True`` if ``contract_first`` is selected; ``False`` for
        ``feature_based`` (the default).
    """
    return resolve_decomposer(options) == DECOMPOSER_CONTRACT_FIRST
