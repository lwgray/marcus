"""Minimal stub for causal analyzer (original removed in cleanup).

The full causal analysis engine was removed in commit e1bad09 as part of
the visualization system cleanup. This stub provides minimal compatibility
for the stall_dashboard.py module.

Original functionality (979 lines, now replaced by this stub):
- Root cause detection for project stalls
- Causal chain building and analysis
- Intervention point identification
- Human decision analysis
- System failure analysis
- Actionable fix generation
- Prevention strategy recommendations

This stub returns empty analysis to allow the diagnostic tools to function
without the full causal analysis system.
"""

from typing import Any


def analyze_why(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Minimal stub for causal analysis.

    Original causal analyzer was removed in visualization cleanup.
    This stub allows stall_dashboard.py to work without full analysis.

    Parameters
    ----------
    snapshot : dict[str, Any]
        Stall snapshot data containing project state, tasks, dependencies,
        and conversation history

    Returns
    -------
    dict[str, Any]
        Minimal analysis dict with empty/basic values. Keys match the
        original analyzer output format for compatibility.

    Examples
    --------
    >>> snapshot = {"project_name": "Test", "stall_reason": "Unknown"}
    >>> analysis = analyze_why(snapshot)
    >>> analysis["narrative"]
    'Causal analysis not available (simplified diagnostics)'
    """
    return {
        "root_causes": [],
        "causal_chains": [],
        "intervention_points": [],
        "human_decisions": [],
        "narrative": "Causal analysis not available (simplified diagnostics)",
        "system_failures": [],
        "actionable_fixes": [],
        "prevention_strategies": [],
    }
