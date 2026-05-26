"""
Unit tests for scaffold anchoring (issue #659).

When Marcus generates a project scaffold pre-fork, each implementation
task receives a placeholder file at a canonical path (e.g.,
``src/core/gameEngine.js`` for the "Implement Game Core Engine" task).
Without an explicit anchor in the agent's task instructions, agents
sometimes invent sibling paths (the ``src/game/gameEngine.js`` orphan
observed in ``snake-baton-1``), leaving the scaffold as dead code on
disk and creating import ambiguity downstream.

These tests verify two behaviors:

1. ``_generate_project_scaffold`` returns a ``{task_name → path}``
   mapping for every placeholder the LLM bound to an implementation
   task. Config files (manifests, entry points, .gitignore) are
   absent from the mapping because they have no owning task.

2. ``build_tiered_instructions`` surfaces the persisted
   ``scaffold_path`` from ``task.source_context`` in the
   IMPLEMENTATION FILE section of the agent's task instructions.
"""

import json
from typing import Any, Optional
from unittest.mock import AsyncMock, patch

import pytest

from src.core.models import (
    Priority,
    Task,
    TaskStatus,
)
from src.integrations.nlp_tools import (
    _backfill_task_names,
    _generate_project_scaffold,
    _tokenize_for_anchor_match,
)
from src.marcus_mcp.tools.task import build_tiered_instructions

pytestmark = pytest.mark.unit


def _make_task(name: str, source_context: Optional[dict[str, Any]] = None) -> Task:
    """Construct a minimal Task instance for the tests below."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return Task(
        id=f"task_{name.lower().replace(' ', '_')}",
        name=name,
        description="",
        status=TaskStatus.TODO,
        priority=Priority.MEDIUM,
        assigned_to=None,
        created_at=now,
        updated_at=now,
        due_date=None,
        estimated_hours=2.0,
        labels=["implementation"],
        source_context=source_context or {},
        responsibility="implements " + name,
    )


class TestScaffoldReturnsAnchorMapping:
    """``_generate_project_scaffold`` returns ``task_name → scaffold_path``."""

    @pytest.mark.asyncio
    async def test_returns_mapping_for_each_bound_placeholder(self, tmp_path) -> None:
        """Each placeholder with a valid ``task_name`` lands in the mapping.

        Mirrors the snake-baton-1 shape: two implementation tasks, one
        placeholder per task. The LLM is mocked to emit the canonical
        JSON the prompt asks for.
        """
        tasks = [
            _make_task("Implement Game Core Engine"),
            _make_task("Implement Game Presentation and Feedback System"),
        ]
        design_content = {
            "Design Game Core Engine": {
                "artifacts": [
                    {
                        "artifact_type": "architecture",
                        "content": "# arch doc",
                    }
                ]
            }
        }
        llm_response = json.dumps(
            [
                {"path": "package.json", "content": "{}"},
                {
                    "path": "src/core/gameEngine.js",
                    "content": "// game engine placeholder",
                    "task_name": "Implement Game Core Engine",
                },
                {
                    "path": "src/presentation/renderer.js",
                    "content": "// renderer placeholder",
                    "task_name": "Implement Game Presentation and Feedback System",
                },
            ]
        )

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction.analyze",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            success, task_to_path = await _generate_project_scaffold(
                tasks=tasks,
                project_description="Snake game in vanilla JS",
                project_name="snake",
                project_root=str(tmp_path),
                design_content=design_content,
            )

        assert success is True
        assert task_to_path == {
            "Implement Game Core Engine": "src/core/gameEngine.js",
            "Implement Game Presentation and Feedback System": (
                "src/presentation/renderer.js"
            ),
        }

    @pytest.mark.asyncio
    async def test_config_files_excluded_from_mapping(self, tmp_path) -> None:
        """Files without a ``task_name`` (configs / entry points) skip the mapping.

        ``package.json``, ``vite.config.js``, ``index.html``, and the
        entry-point ``main.js`` are shared infrastructure — no single
        task owns them, so they MUST NOT appear in the anchor mapping.
        """
        tasks = [_make_task("Implement Game Core Engine")]
        design_content = {
            "Design Game Core Engine": {
                "artifacts": [{"artifact_type": "architecture", "content": "doc"}]
            }
        }
        llm_response = json.dumps(
            [
                {"path": "package.json", "content": "{}"},
                {"path": "vite.config.js", "content": "export default {}"},
                {"path": "index.html", "content": "<!doctype html>"},
                {"path": "src/main.js", "content": "// entry"},
                {
                    "path": "src/core/gameEngine.js",
                    "content": "// engine",
                    "task_name": "Implement Game Core Engine",
                },
            ]
        )

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction.analyze",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            _, task_to_path = await _generate_project_scaffold(
                tasks=tasks,
                project_description="snake",
                project_name="snake",
                project_root=str(tmp_path),
                design_content=design_content,
            )

        # Only the explicitly-bound placeholder appears.
        assert task_to_path == {"Implement Game Core Engine": "src/core/gameEngine.js"}

    @pytest.mark.asyncio
    async def test_unknown_task_name_is_ignored(self, tmp_path) -> None:
        """A ``task_name`` not matching any impl task is silently dropped.

        Defensive against LLM hallucination — if the model emits a
        ``task_name`` that doesn't correspond to a real task, we'd
        rather write the scaffold file and skip the anchor than write
        a phantom anchor that misleads downstream code.
        """
        tasks = [_make_task("Implement Game Core Engine")]
        design_content = {
            "Design X": {
                "artifacts": [{"artifact_type": "architecture", "content": "doc"}]
            }
        }
        llm_response = json.dumps(
            [
                {
                    "path": "src/foo.js",
                    "content": "// foo",
                    "task_name": "Implement Some Task That Does Not Exist",
                },
            ]
        )

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction.analyze",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            _, task_to_path = await _generate_project_scaffold(
                tasks=tasks,
                project_description="x",
                project_name="x",
                project_root=str(tmp_path),
                design_content=design_content,
            )

        assert task_to_path == {}

    @pytest.mark.asyncio
    async def test_duplicate_task_name_keeps_first(self, tmp_path) -> None:
        """When the LLM binds two files to the same task, only the first wins.

        Multiple placeholders per task is a prompt-drift symptom we
        log but don't fail on. The mapping is task → ONE path; the
        first one the writer sees stays.
        """
        tasks = [_make_task("Implement Game Core Engine")]
        design_content = {
            "Design X": {
                "artifacts": [{"artifact_type": "architecture", "content": "doc"}]
            }
        }
        llm_response = json.dumps(
            [
                {
                    "path": "src/core/gameEngine.js",
                    "content": "// first",
                    "task_name": "Implement Game Core Engine",
                },
                {
                    "path": "src/engine/index.js",
                    "content": "// second",
                    "task_name": "Implement Game Core Engine",
                },
            ]
        )

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction.analyze",
            new_callable=AsyncMock,
            return_value=llm_response,
        ):
            _, task_to_path = await _generate_project_scaffold(
                tasks=tasks,
                project_description="x",
                project_name="x",
                project_root=str(tmp_path),
                design_content=design_content,
            )

        # First write wins; both files still land on disk, but only
        # the first is anchored.
        assert task_to_path == {"Implement Game Core Engine": "src/core/gameEngine.js"}


class TestTokenizeForAnchorMatch:
    """``_tokenize_for_anchor_match`` normalizes naming variants to one form.

    The backfill heuristic compares file basenames to task names by
    token-set intersection, so the tokenizer must produce the same
    bag of words for ``GameCoreEngine``, ``game_core_engine``,
    ``game-core-engine``, and ``Game Core Engine``.
    """

    def test_pascalcase_splits_at_case_transitions(self) -> None:
        """``GameCoreEngine`` → {game, core, engine}."""
        assert _tokenize_for_anchor_match("GameCoreEngine") == {
            "game",
            "core",
            "engine",
        }

    def test_snake_case_splits_on_underscore(self) -> None:
        """``game_core_engine`` → {game, core, engine}."""
        assert _tokenize_for_anchor_match("game_core_engine") == {
            "game",
            "core",
            "engine",
        }

    def test_kebab_case_splits_on_dash(self) -> None:
        """``game-core-engine`` → {game, core, engine}."""
        assert _tokenize_for_anchor_match("game-core-engine") == {
            "game",
            "core",
            "engine",
        }

    def test_space_separated_with_filler_words_dropped(self) -> None:
        """Implementation task names drop the ``implement`` filler."""
        assert _tokenize_for_anchor_match("Implement Game Core Engine") == {
            "game",
            "core",
            "engine",
        }

    def test_single_letter_tokens_dropped(self) -> None:
        """One-character tokens are too noisy to discriminate."""
        # "a b c GameEngine" → only the multi-char content tokens survive.
        assert _tokenize_for_anchor_match("a b c GameEngine") == {
            "game",
            "engine",
        }

    def test_empty_input_returns_empty_set(self) -> None:
        """Defensive: empty / None input doesn't crash."""
        assert _tokenize_for_anchor_match("") == set()


class TestBackfillTaskNames:
    """``_backfill_task_names`` recovers anchors when the LLM omits ``task_name``.

    Real failure observed on test76 (snake-scaffold-2): the LLM
    produced 2 placeholder files without ``task_name`` fields, the
    anchor mapping ended up empty, and agents went back to inventing
    sibling paths. The backfill matches by lexical token overlap so
    Marcus doesn't depend on LLM compliance for the anchor to land.
    """

    def _config_sets(self) -> "tuple[set[str], set[str]]":
        config_extensions = {".json", ".toml", ".yaml"}
        config_names = {".gitignore", ".env.example", "vite.config.js"}
        return config_extensions, config_names

    def test_pascalcase_basename_matches_task_name(self) -> None:
        """``src/core/GameCoreEngine.js`` → "Implement Game Core Engine"."""
        files = [
            {
                "path": "src/core/GameCoreEngine.js",
                "content": "// engine placeholder",
            },
        ]
        impl_task_names = {
            "Implement Game Core Engine",
            "Implement Game Presentation Layer",
        }
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        assert files[0]["task_name"] == "Implement Game Core Engine"

    def test_existing_valid_task_name_not_overwritten(self) -> None:
        """LLM-supplied ``task_name`` always wins over inference."""
        files = [
            {
                "path": "src/core/GameCoreEngine.js",
                "content": "// engine",
                "task_name": "Implement Game Presentation Layer",
            },
        ]
        impl_task_names = {
            "Implement Game Core Engine",
            "Implement Game Presentation Layer",
        }
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        # Wrong but explicit — leave alone (caller may log).
        assert files[0]["task_name"] == "Implement Game Presentation Layer"

    def test_config_files_skipped(self) -> None:
        """Manifests, entry points, .gitignore never get a task_name."""
        files = [
            {"path": "package.json", "content": "{}"},
            {"path": "vite.config.js", "content": "..."},
            {"path": "src/main.js", "content": "// entry"},
            {"path": ".gitignore", "content": "node_modules"},
        ]
        impl_task_names = {"Implement Game Core Engine"}
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        for f in files:
            assert "task_name" not in f

    def test_ambiguous_match_leaves_unbound(self) -> None:
        """When two tasks tie closely, don't guess — leave unbound.

        Wrong anchors are worse than no anchors. The agent gets a
        fallback experience either way, but a wrong anchor sends
        them confidently to the wrong file.
        """
        files = [
            {"path": "src/engine.js", "content": "// engine"},
        ]
        # Both tasks share exactly one token ("engine") with
        # "src/engine.js" → identical Jaccard scores → ambiguous.
        impl_task_names = {
            "Implement Audio Engine",
            "Implement Physics Engine",
        }
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        assert "task_name" not in files[0]

    def test_no_task_matches_leaves_unbound(self) -> None:
        """Files unrelated to any impl task stay unbound."""
        files = [
            {"path": "src/utils/totally_unrelated.js", "content": "// ..."},
        ]
        impl_task_names = {"Implement Game Core Engine"}
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        assert "task_name" not in files[0]

    def test_one_task_can_only_be_bound_once(self) -> None:
        """Two files matching the same task: only the first wins.

        Prevents an LLM that emits redundant placeholders from
        double-binding the same task — which would clobber the
        first anchor in the writer's ``task_to_path`` map.
        """
        files = [
            {"path": "src/core/GameCoreEngine.js", "content": "// 1"},
            {"path": "src/engine/GameCoreEngine.js", "content": "// 2"},
        ]
        impl_task_names = {
            "Implement Game Core Engine",
            "Implement Game Presentation Layer",
        }
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)
        # Exactly one gets bound to the engine task.
        anchored = [
            f for f in files if f.get("task_name") == "Implement Game Core Engine"
        ]
        assert len(anchored) == 1

    def test_test76_real_world_scenario(self) -> None:
        """Reproduce the exact test76 LLM output and verify recovery.

        On snake-scaffold-2 the LLM emitted:
          src/core/GameCoreEngine.js
          src/presentation/GamePresentationLayer.js
          src/main.js
          package.json
        with NO task_name on any file. Impl tasks:
          Implement Game Core Engine
          Implement Game Presentation Layer
          Integrate Game Loop and Input Handling

        The backfill should anchor the first two correctly and
        leave the third unbound (no matching placeholder file).
        """
        files = [
            {"path": "package.json", "content": "{}"},
            {"path": "src/main.js", "content": "// entry"},
            {"path": "src/core/GameCoreEngine.js", "content": "// engine"},
            {
                "path": "src/presentation/GamePresentationLayer.js",
                "content": "// presentation",
            },
        ]
        impl_task_names = {
            "Implement Game Core Engine",
            "Implement Game Presentation Layer",
            "Integrate Game Loop and Input Handling",
        }
        cext, cnames = self._config_sets()
        _backfill_task_names(files, impl_task_names, cext, cnames)

        # Each placeholder is now anchored to its owning impl task.
        engine = next(f for f in files if "core" in f["path"])
        presentation = next(f for f in files if "presentation" in f["path"])
        assert engine["task_name"] == "Implement Game Core Engine"
        assert presentation["task_name"] == "Implement Game Presentation Layer"
        # Integrate task has no placeholder — that's a separate
        # problem (loud warning will surface it), but it's not the
        # backfill's job to invent files.


class TestAgentInstructionsSurfaceScaffoldPath:
    """``build_tiered_instructions`` surfaces ``scaffold_path`` to the agent."""

    def test_implementation_file_section_appears_when_path_set(self) -> None:
        """A task with ``source_context.scaffold_path`` gets an anchor section.

        The instructions must explicitly name the path so the agent
        fills the scaffold rather than picking a sibling path.
        """
        task = _make_task(
            "Implement Game Core Engine",
            source_context={
                "scaffold_path": "src/core/gameEngine.js",
                "contract_file": "docs/architecture/engine.md",
            },
        )

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        assert "IMPLEMENTATION FILE: src/core/gameEngine.js" in instructions
        assert "do NOT create a sibling file" in instructions

    def test_no_anchor_section_when_path_missing(self) -> None:
        """Without ``scaffold_path``, no IMPLEMENTATION FILE section appears.

        Legacy tasks created before #659 won't have the field;
        instructions must still render cleanly without it.
        """
        task = _make_task(
            "Implement Game Core Engine",
            source_context={"contract_file": "docs/architecture/engine.md"},
        )

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        assert "IMPLEMENTATION FILE:" not in instructions

    def test_empty_scaffold_path_treated_as_missing(self) -> None:
        """``scaffold_path = ""`` should not render an empty anchor section."""
        task = _make_task(
            "Implement Game Core Engine",
            source_context={
                "scaffold_path": "",
                "contract_file": "docs/architecture/engine.md",
            },
        )

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        assert "IMPLEMENTATION FILE:" not in instructions

    def test_falls_back_to_description_marker_for_non_sqlite(self) -> None:
        """Non-SQLite providers carry the anchor via a description marker.

        Planka, GitHub, and Linear don't have a ``source_context``
        column. The anchor survives in the task description as a
        ``<!-- MARCUS_SCAFFOLD_PATH: ... -->`` marker, mirroring the
        ``MARCUS_CONTRACT_FIRST`` pattern. ``_resolve_scaffold_path``
        parses the marker as the fallback path source.
        """
        task = _make_task(
            "Implement Game Core Engine",
            source_context={
                "contract_file": "docs/architecture/engine.md",
                # No scaffold_path here — simulates a Planka-backed
                # task that never persisted the JSON column.
            },
        )
        # Description carries the marker, the way the
        # cross-provider write path leaves it.
        task.description = (
            "Build the engine.\n\n"
            "<!-- MARCUS_SCAFFOLD_PATH: src/core/gameEngine.js -->"
        )

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        assert "IMPLEMENTATION FILE: src/core/gameEngine.js" in instructions

    def test_source_context_wins_over_description_marker(self) -> None:
        """When both are present, ``source_context`` is the source of truth.

        SQLite carries the path in its JSON column; the description
        marker is the cross-provider fallback. If both somehow
        disagree (e.g., the description marker is stale and the JSON
        column was updated), the JSON column is authoritative for
        the IMPLEMENTATION FILE section.

        Note: the description (including its marker) appears verbatim
        in Layer 0's mandatory workflow listing. That's expected —
        the marker IS a description-borne signal in non-SQLite
        providers. What matters is which path the structured anchor
        section names.
        """
        task = _make_task(
            "Implement Game Core Engine",
            source_context={"scaffold_path": "src/core/gameEngine.js"},
        )
        task.description = "<!-- MARCUS_SCAFFOLD_PATH: src/old/stale_path.js -->"

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        # The structured anchor section names the source_context path.
        assert "IMPLEMENTATION FILE: src/core/gameEngine.js" in instructions
        # The structured section does NOT name the stale marker path.
        assert "IMPLEMENTATION FILE: src/old/stale_path.js" not in instructions

    def test_malformed_marker_does_not_render_section(self) -> None:
        """A marker without a closing ``-->`` is silently ignored."""
        task = _make_task(
            "Implement Game Core Engine",
            source_context={},
        )
        task.description = "<!-- MARCUS_SCAFFOLD_PATH: src/core/gameEngine.js"

        instructions = build_tiered_instructions(
            base_instructions="Build the engine.",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
            state=None,
        )

        assert "IMPLEMENTATION FILE:" not in instructions
