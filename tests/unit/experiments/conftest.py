"""
Shared fixtures for experiment-runner tests.

The runner scripts live under ``dev-tools/experiments/runners/``.
That directory has the hyphenated parent ``dev-tools`` which is not
a valid Python package name, so test files cannot ``from
dev_tools.experiments.runners import ...``.  Pre-PR-#585 each test
file individually loaded ``spawn_agents.py`` and ``harness.py`` via
``importlib.util.spec_from_file_location`` to work around this.  That
dance also forced ``spawn_agents.py`` to carry a ``try/except
ImportError`` import block for the same reason — every cross-module
refactor under ``runners/`` paid the tax.

This conftest fixes the root cause once: insert
``dev-tools/experiments/`` onto ``sys.path`` for the entire
experiments test subtree.  Tests can then write ``from
runners.spawn_agents import AgentSpawner`` and ``from runners.harness
import HARNESSES`` exactly the way production code does.

The insert is idempotent — repeated test runs do not stack entries.
"""

import sys
from pathlib import Path

_RUNNERS_PARENT = (
    Path(__file__).parent.parent.parent.parent / "dev-tools" / "experiments"
)
_runners_parent_str = str(_RUNNERS_PARENT)
if _runners_parent_str not in sys.path:
    sys.path.insert(0, _runners_parent_str)
