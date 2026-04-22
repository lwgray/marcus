"""
Spec Coverage Check for Marcus Task Decomposition.

After task decomposition, verifies that all features mentioned in the
project specification have at least one corresponding task. Synthesizes
gap tasks for uncovered features so agents are aware of missing scope.

Background
----------
Dashboard-v88 post-mortem: Marcus's LLM decomposer silently dropped
the "5-day forecast" feature from the project spec. No task was generated,
no agent knew it was in scope, and the feature shipped entirely missing.
UD1 wrote .forecast-card CSS as a hint, but with no task, no agent built
the component. Epictetus rated Completeness 2.0/5 (D).

Design
------
1. extract_spec_features  — LLM call to pull feature phrases from spec.
2. find_uncovered_features — keyword match against task names/descriptions.
3. check_spec_coverage    — orchestrates 1+2 and returns gap Task objects.

Gap tasks are labeled ``spec_gap`` so Cato and agents can distinguish them
from normal decomposed tasks. They are inserted into safe_tasks before
board creation so all agents see them.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, List

from src.core.models import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


async def _llm_extract_features(description: str) -> str:
    """
    Call LLM to extract feature phrases from a project description.

    Parameters
    ----------
    description : str
        Raw project specification text.

    Returns
    -------
    str
        Raw LLM response (expected to be a JSON array of feature strings).
    """
    from src.ai.providers.llm_abstraction import LLMAbstraction

    llm = LLMAbstraction()

    class _Ctx:
        max_tokens = 512

    prompt = (
        "You are a project manager analyzing a software specification.\n\n"
        "Extract ALL distinct user-facing features from this spec. "
        "Return ONLY a JSON array of short feature phrases "
        "(2-5 words each). Be exhaustive — do not skip features.\n\n"
        "Project spec:\n"
        f"{description}\n\n"
        'Return ONLY valid JSON like: ["feature one", "feature two", ...]'
    )

    response = await llm.analyze(prompt, _Ctx())
    return str(response)


async def extract_spec_features(description: str) -> List[str]:
    """
    Extract feature phrases from a project description via LLM.

    Parameters
    ----------
    description : str
        Project specification text.

    Returns
    -------
    List[str]
        Feature phrases (e.g. ["5-day forecast", "animated clock"]).
        Returns empty list on any failure — non-fatal.
    """
    try:
        raw = await _llm_extract_features(description)
        # Find the JSON array in the response
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start == -1 or end == 0:
            logger.warning("[spec_coverage] LLM response missing JSON array")
            return []
        parsed: Any = json.loads(raw[start:end])
        if not isinstance(parsed, list):
            return []
        return [str(f) for f in parsed if f]
    except Exception as exc:
        logger.warning(f"[spec_coverage] extract_spec_features failed: {exc}")
        return []


def find_uncovered_features(
    features: List[str],
    tasks: List[Task],
) -> List[str]:
    """
    Identify features that have no matching task.

    Coverage is determined by case-insensitive substring matching of each
    feature word against task names and descriptions. A feature is covered
    if ANY significant word (length > 3) in the feature phrase appears in
    ANY task's name or description.

    Parameters
    ----------
    features : List[str]
        Feature phrases extracted from the spec.
    tasks : List[Task]
        Decomposed task objects to check coverage against.

    Returns
    -------
    List[str]
        Feature phrases with zero task coverage.
    """
    if not features:
        return []

    # Build search corpus: all task names and descriptions lowercased
    corpus = " ".join(f"{t.name} {t.description}".lower() for t in tasks)

    uncovered: List[str] = []
    for feature in features:
        feature_lower = feature.lower()
        # Significant words: length > 3, not common stopwords
        stopwords = {
            "with",
            "from",
            "that",
            "this",
            "have",
            "will",
            "been",
            "their",
            "there",
            "when",
            "where",
            "which",
            "using",
            "based",
        }
        words = [w for w in feature_lower.split() if len(w) > 3 and w not in stopwords]
        if not words:
            continue

        # Feature is covered if ANY significant word appears in corpus
        covered = any(word in corpus for word in words)
        if not covered:
            uncovered.append(feature)

    return uncovered


async def check_spec_coverage(
    description: str,
    tasks: List[Task],
    project_name: str,
) -> List[Task]:
    """
    Verify all spec features have tasks; return gap tasks for any missing.

    This is the main entry point. Called after task decomposition and
    safety checks, before tasks are committed to the kanban board.
    Non-fatal: any internal error returns [] so the pipeline never stalls.

    Parameters
    ----------
    description : str
        Original project description / specification.
    tasks : List[Task]
        Current task list after decomposition and safety checks.
    project_name : str
        Project name (for gap task naming).

    Returns
    -------
    List[Task]
        Gap Task objects to append to the task list, one per uncovered
        feature. Empty list when all features are covered or on any error.

    Notes
    -----
    Gap tasks carry the ``spec_gap`` label so Cato's display role
    classifier can distinguish them from normal decomposed tasks.
    """
    try:
        features = await extract_spec_features(description)
        if not features:
            logger.info(
                "[spec_coverage] No features extracted — skipping coverage check"
            )
            return []

        uncovered = find_uncovered_features(features, tasks)
        if not uncovered:
            logger.info(
                f"[spec_coverage] All {len(features)} spec features have coverage"
            )
            return []

        logger.warning(
            f"[spec_coverage] {len(uncovered)} spec feature(s) have no task: "
            f"{uncovered}"
        )

        gap_tasks: List[Task] = []
        now = datetime.now(timezone.utc)
        for feature in uncovered:
            task_name = f"Implement {feature.title()}"
            gap_tasks.append(
                Task(
                    id=f"gap_{uuid.uuid4().hex[:12]}",
                    name=task_name,
                    description=(
                        f"Spec coverage check found this feature missing from "
                        f"the task list: '{feature}'. "
                        f"Implement this feature as described in the project spec."
                    ),
                    status=TaskStatus.TODO,
                    priority=Priority.HIGH,
                    labels=["spec_gap"],
                    dependencies=[],
                    estimated_hours=3.0,
                    assigned_to=None,
                    created_at=now,
                    updated_at=now,
                    due_date=None,
                )
            )
            logger.info(f"[spec_coverage] Synthesized gap task: '{task_name}'")

        return gap_tasks

    except Exception as exc:
        logger.warning(f"[spec_coverage] check_spec_coverage failed (non-fatal): {exc}")
        return []
