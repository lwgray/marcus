#!/usr/bin/env python3
"""
Smoke test for GH-304 design autocomplete parallelism.

Runs ``_generate_design_content()`` end-to-end against the *real* LLM
provider configured in ``config_marcus.json``, not a mock. Reports
wall-clock time, artifact counts per task, and a pass/fail verdict so
the author can paste the output into the PR description as evidence.

This is NOT a pytest test. It costs real money (one full run is ~$0.50
to ~$3.00 depending on model and project size) and should be run once
before merging #304. Do not wire it into CI.

Usage
-----
Run from the repo root::

    python scripts/smoke_test_design_autocomplete.py

    # Or with a different complexity:
    python scripts/smoke_test_design_autocomplete.py --complexity prototype
    python scripts/smoke_test_design_autocomplete.py --complexity enterprise

Exit codes
----------
0
    Smoke test passed (wall-clock under budget, all design tasks
    produced artifacts).
1
    Smoke test failed — see stderr for details.

Notes
-----
The script instantiates a temporary project workspace under
``/tmp/marcus-smoke-304-<timestamp>/`` and leaves it in place on success
for manual inspection of generated artifacts.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

# Ensure the repo root is on sys.path when running as a script
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from src.core.models import Priority, TaskStatus  # noqa: E402
from src.integrations.nlp_tools import _generate_design_content  # noqa: E402

# Budgets used for the pass/fail verdict. These reflect the GH-304 goal
# of keeping project creation under the 10-minute timeout.
_WALL_CLOCK_BUDGETS_SECONDS = {
    "prototype": 180.0,  # 1-2 design tasks
    "standard": 300.0,  # 3 design tasks
    "enterprise": 540.0,  # up to 10 design tasks, buffer under 600s timeout
}


class _SmokeTask:
    """Minimal Task-like object that passes ``_is_design_task``.

    We don't use the full ``src.core.models.Task`` dataclass because it
    has strict field validation; this smoke test only needs enough
    surface area for ``_generate_design_content`` to mutate state on
    success.
    """

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.labels: List[str] = ["design"]
        self.status: TaskStatus = TaskStatus.TODO
        self.assigned_to: Any = None
        self.priority: Priority = Priority.HIGH


def _build_design_tasks(complexity: str) -> List[_SmokeTask]:
    """Build a synthetic list of design tasks for the given complexity.

    Parameters
    ----------
    complexity : str
        One of ``"prototype"``, ``"standard"``, ``"enterprise"``.

    Returns
    -------
    List[_SmokeTask]
        A list of design tasks that mirrors what Marcus's PRD parser
        would emit for a project of this complexity.
    """
    base = [
        _SmokeTask(
            "Design Authentication",
            "User signup, login, and session management with JWTs.",
        ),
        _SmokeTask(
            "Design Data Layer",
            "PostgreSQL schemas for users, accounts, and audit logs.",
        ),
    ]
    extras_standard = [
        _SmokeTask(
            "Design API Gateway",
            "REST API with rate limiting and request validation.",
        ),
    ]
    extras_enterprise = [
        _SmokeTask(
            "Design Notification System",
            "Email + SMS delivery with retry queue and dead-letter handling.",
        ),
        _SmokeTask(
            "Design Search",
            "Full-text search over user documents via OpenSearch.",
        ),
        _SmokeTask(
            "Design Analytics Pipeline",
            "Event ingestion, aggregation, and dashboard backend.",
        ),
        _SmokeTask(
            "Design Billing",
            "Stripe integration, subscription management, invoice generation.",
        ),
        _SmokeTask(
            "Design Admin Console",
            "Internal tools for support, user management, and audit review.",
        ),
        _SmokeTask(
            "Design DevOps",
            "CI/CD pipeline, Terraform infrastructure, observability stack.",
        ),
        _SmokeTask(
            "Design Security",
            "RBAC, secrets management, vulnerability scanning.",
        ),
    ]

    if complexity == "prototype":
        return base[:1]
    if complexity == "standard":
        return base + extras_standard
    if complexity == "enterprise":
        return base + extras_standard + extras_enterprise
    raise ValueError(f"Unknown complexity: {complexity}")


async def _run_smoke(complexity: str, workdir: Path) -> int:
    """Run the parallel design autocomplete and report the result.

    Parameters
    ----------
    complexity : str
        Project complexity name (``prototype``/``standard``/``enterprise``).
    workdir : Path
        Project workspace where artifact files will be written.

    Returns
    -------
    int
        Process exit code: 0 on success, 1 on failure.
    """
    tasks = _build_design_tasks(complexity)
    budget = _WALL_CLOCK_BUDGETS_SECONDS[complexity]

    print(f"GH-304 smoke test — complexity={complexity}")
    print(f"  design tasks: {len(tasks)}")
    print(f"  wall-clock budget: {budget:.0f}s")
    print(f"  workdir: {workdir}")
    print()

    start = time.monotonic()
    try:
        design_content = await _generate_design_content(
            tasks=tasks,
            project_description=(
                "A multi-tenant SaaS platform with real-time collaboration, "
                "audit logging, and enterprise SSO."
            ),
            project_name="SmokeTest-304",
            project_root=str(workdir),
        )
    except Exception as exc:
        wall_clock = time.monotonic() - start
        print(f"FAIL — _generate_design_content raised after {wall_clock:.1f}s")
        print(f"  exception: {type(exc).__name__}: {exc}")
        return 1

    wall_clock = time.monotonic() - start
    print(f"Completed in {wall_clock:.1f}s wall-clock " f"(budget {budget:.0f}s)")
    print()

    # Per-task artifact summary
    print("Per-task summary:")
    missing: List[str] = []
    for task in tasks:
        entry = design_content.get(task.name)
        if entry is None:
            missing.append(task.name)
            print(f"  [MISS] {task.name}: no artifacts, status={task.status.value}")
            continue
        n_art = len(entry["artifacts"])
        n_dec = len(entry["decisions"])
        print(
            f"  [ OK ] {task.name}: {n_art} artifact(s), "
            f"{n_dec} decision(s), status={task.status.value}"
        )
    print()

    # Verdict
    verdict_ok = True
    if wall_clock > budget:
        print(f"FAIL — wall-clock {wall_clock:.1f}s exceeds budget {budget:.0f}s")
        verdict_ok = False
    if missing:
        print(f"FAIL — {len(missing)} design task(s) produced no artifacts:")
        for name in missing:
            print(f"    - {name}")
        verdict_ok = False

    if verdict_ok:
        print("PASS — all design tasks produced artifacts within budget")
        print(f"  artifacts preserved under {workdir} for inspection")
        return 0
    return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "GH-304 smoke test: run _generate_design_content() against "
            "a real LLM and report wall-clock + artifact counts."
        )
    )
    parser.add_argument(
        "--complexity",
        choices=["prototype", "standard", "enterprise"],
        default="standard",
        help="Which project complexity to simulate (default: standard).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable INFO-level logging from marcus modules.",
    )
    return parser.parse_args()


def main() -> int:
    """Parse CLI args, validate credentials, and run the smoke test.

    Returns
    -------
    int
        Process exit code: 0 on pass, 1 on fail, 130 on Ctrl-C.
    """
    args = _parse_args()

    if args.verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )
    else:
        logging.basicConfig(level=logging.WARNING)

    if (
        not os.environ.get("ANTHROPIC_API_KEY")
        and not Path("config_marcus.json").exists()
    ):
        print(
            "ERROR: no ANTHROPIC_API_KEY in environment and no "
            "config_marcus.json found. Set one or the other before "
            "running this smoke test.",
            file=sys.stderr,
        )
        return 1

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    workdir = Path(tempfile.gettempdir()) / f"marcus-smoke-304-{timestamp}"
    workdir.mkdir(parents=True, exist_ok=True)

    try:
        return asyncio.run(_run_smoke(args.complexity, workdir))
    except KeyboardInterrupt:
        print("\naborted by user", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
