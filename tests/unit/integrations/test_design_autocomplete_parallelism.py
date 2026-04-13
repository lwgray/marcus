"""
Unit tests for parallel design autocomplete (GH-304).

Verifies that ``_generate_design_content()`` parallelizes LLM calls both
across design tasks (Level 1) and within each task (Level 2), wraps each
call with retry, caps concurrency via ``asyncio.Semaphore``, and
fail-fasts when any call exhausts retries.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.core.models import Priority, TaskStatus
from src.integrations.nlp_tools import (
    _build_sibling_domains_block,
    _generate_contracts_by_domain,
    _generate_design_content,
)


def _make_design_task(name: str, description: str = "Do the design") -> Mock:
    """Build a minimal design Task stand-in that passes ``_is_design_task``.

    Parameters
    ----------
    name : str
        Task name. Must start with ``"Design "`` for ``_is_design_task``
        to return True.
    description : str
        Task description used in LLM prompt templating.

    Returns
    -------
    Mock
        A ``Mock`` object with ``name``, ``description``, ``labels``,
        ``status``, and ``assigned_to`` attributes wired so that
        ``_is_design_task(task)`` is True and the function-under-test
        can mutate the status/labels on success.
    """
    task = Mock()
    task.name = name
    task.description = description
    task.labels = ["design"]
    task.status = TaskStatus.TODO
    task.assigned_to = None
    task.priority = Priority.HIGH
    return task


# Valid architecture/API/data-model response bodies (> 20 chars to pass the
# empty/short filter in _generate_single_artifact).
_VALID_ARTIFACT_RESPONSE = (
    "## Architecture\n\nComponent A talks to Component B via REST.\n"
)

# Valid decisions response — JSON with the three required keys.
_VALID_DECISIONS_RESPONSE = (
    '[{"what": "Use REST", "why": "Simpler", "impact": "Lower latency"}]'
)


def _mock_llm_response(prompt: str, context: Any) -> str:
    """Return a valid response string for artifact or decisions prompts.

    Dispatches on prompt content so the same mock can serve both artifact
    calls and the decisions call with semantically valid payloads.
    """
    if "decision" in prompt.lower() and "json" in prompt.lower():
        return _VALID_DECISIONS_RESPONSE
    return _VALID_ARTIFACT_RESPONSE


@pytest.mark.unit
class TestDesignAutocompleteParallelism:
    """Test suite for ``_generate_design_content()`` GH-304 parallelism."""

    @pytest.mark.asyncio
    async def test_llm_calls_run_in_parallel_across_tasks_and_specs(
        self, tmp_path: Any
    ) -> None:
        """Wall-clock time must be far below sequential baseline.

        With 3 design tasks × 5 LLM calls each = 15 total calls, and each
        mocked call taking 100ms, a sequential implementation would take
        ~1500ms. A correctly parallelized implementation (Level 1 across
        tasks + Level 2 within each task, with Semaphore(10)) should
        complete in ~100–300ms wall-clock.
        """
        call_times: List[float] = []

        async def slow_analyze(prompt: str, context: Any) -> str:
            call_times.append(time.monotonic())
            await asyncio.sleep(0.1)
            return _mock_llm_response(prompt, context)

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=slow_analyze)

        tasks = [
            _make_design_task("Design Authentication"),
            _make_design_task("Design Payments"),
            _make_design_task("Design Notifications"),
        ]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            start = time.monotonic()
            result = await _generate_design_content(
                tasks=tasks,
                project_description="Build a widget.",
                project_name="TestProject",
                project_root=str(tmp_path),
            )
            wall_clock = time.monotonic() - start

        # All 3 design tasks were processed with 5 calls each = 15 calls
        assert mock_llm.analyze.call_count == 15

        # Parallel: all 15 calls should have STARTED within a narrow
        # window (well under the sequential baseline of 1.5s)
        assert wall_clock < 0.5, (
            f"Wall-clock {wall_clock:.3f}s suggests sequential execution — "
            f"expected < 0.5s for parallel (baseline sequential = 1.5s)"
        )

        # All 3 tasks should appear in the returned design_content and
        # have been mutated to DONE
        assert set(result.keys()) == {
            "Design Authentication",
            "Design Payments",
            "Design Notifications",
        }
        for task in tasks:
            assert task.status == TaskStatus.DONE
            assert task.assigned_to == "Marcus"
            assert "auto_completed" in task.labels

    @pytest.mark.asyncio
    async def test_each_task_produces_four_artifacts_and_decisions(
        self, tmp_path: Any
    ) -> None:
        """Each design task should produce 4 artifacts + the decisions list.

        Verifies the inner Level-2 gather includes all 4 artifact specs
        and the decisions call, and that the results are assembled
        correctly.
        """
        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=_mock_llm_response)

        tasks = [_make_design_task("Design Auth")]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_design_content(
                tasks=tasks,
                project_description="A project.",
                project_name="P",
                project_root=str(tmp_path),
            )

        # 5 LLM calls per task (4 artifact specs + 1 decisions)
        assert mock_llm.analyze.call_count == 5

        entry = result["Design Auth"]
        # 4 artifact specs defined in _DESIGN_ARTIFACT_SPECS
        assert len(entry["artifacts"]) == 4
        assert len(entry["decisions"]) == 1
        # Each artifact file should be written under tmp_path
        for artifact in entry["artifacts"]:
            file_path = tmp_path / artifact["relative_path"]
            assert file_path.exists(), f"Missing artifact file: {file_path}"

    @pytest.mark.asyncio
    async def test_empty_response_skips_artifact_without_aborting_task(
        self, tmp_path: Any
    ) -> None:
        """Short LLM responses are skipped without failing the whole task.

        If the LLM returns an empty or <20-char response for one artifact
        spec, that spec is dropped, but the other 3 artifacts and the
        decisions call should still succeed and the task should still
        complete (since at least one artifact was produced).
        """
        call_count = {"n": 0}

        async def mixed_analyze(prompt: str, context: Any) -> str:
            call_count["n"] += 1
            # First artifact call returns garbage, the rest return valid
            if call_count["n"] == 1:
                return "nope"
            return _mock_llm_response(prompt, context)

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=mixed_analyze)

        tasks = [_make_design_task("Design X")]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_design_content(
                tasks=tasks,
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        entry = result["Design X"]
        # 3 of 4 artifacts should have survived
        assert len(entry["artifacts"]) == 3
        # Task should still be marked DONE (at least one artifact produced)
        assert tasks[0].status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_malformed_decisions_list_does_not_abort_design_phase(
        self, tmp_path: Any
    ) -> None:
        """Non-dict elements in the LLM decisions list must not crash.

        Regression test for PR #319 Codex P1 review: an LLM that returns
        a decisions JSON list with mixed types (e.g. a trailing string,
        number, or null) used to raise ``TypeError`` from
        ``"what" in d`` for non-iterable elements. Under the GH-304
        fail-fast ``asyncio.gather`` flow, that exception would abort
        the entire design phase for what is really a recoverable
        formatting issue. The parser must filter to ``isinstance(dict)``
        before checking for required keys.
        """
        # Decisions response: 1 valid dict, 1 string, 1 int, 1 dict
        # missing required keys, 1 None. Only the first should survive.
        malformed_decisions = (
            "["
            '{"what": "Use REST", "why": "Simpler", "impact": "OK"},'
            '"a stray string",'
            "42,"
            '{"what": "Missing keys"},'
            "null"
            "]"
        )

        async def malformed_analyze(prompt: str, context: Any) -> str:
            if "decision" in prompt.lower() and "json" in prompt.lower():
                return malformed_decisions
            return _VALID_ARTIFACT_RESPONSE

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=malformed_analyze)

        tasks = [_make_design_task("Design Mixed")]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            # This used to raise TypeError before the isinstance guard.
            result = await _generate_design_content(
                tasks=tasks,
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        # The design phase must complete normally
        entry = result["Design Mixed"]
        assert len(entry["artifacts"]) == 4
        # Only the one well-formed dict should pass the filter
        assert len(entry["decisions"]) == 1
        assert entry["decisions"][0]["what"] == "Use REST"
        # And the task should still be marked DONE
        assert tasks[0].status == TaskStatus.DONE

    @pytest.mark.asyncio
    async def test_llm_failure_exhausts_retries_then_propagates(
        self, tmp_path: Any
    ) -> None:
        """If any LLM call fails after 3 retries, the whole function raises.

        Verifies fail-fast semantics (GH-304 Option B): the Kaia-reviewed
        retry config (``max_attempts=3``) means a persistently-failing
        LLM call gets exactly 3 attempts before its exception propagates
        out, aborts the surrounding ``gather``, and raises out of
        ``_generate_design_content``. No task state mutations happen.
        """
        fail_count = {"n": 0}

        async def always_fail(prompt: str, context: Any) -> str:
            fail_count["n"] += 1
            raise RuntimeError("LLM provider exploded")

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=always_fail)

        tasks = [_make_design_task("Design Broken")]

        # Skip backoff sleeps so the test doesn't spend seconds sleeping.
        # Patches asyncio.sleep *inside the resilience module only* so the
        # @with_retry decorator's exponential-backoff waits are no-ops;
        # the test's own asyncio.sleep calls (if any) are unaffected.
        async def _no_sleep(_delay: float) -> None:
            return None

        with (
            patch(
                "src.ai.providers.llm_abstraction.LLMAbstraction",
                return_value=mock_llm,
            ),
            patch("src.core.resilience.asyncio.sleep", new=_no_sleep),
        ):
            with pytest.raises(RuntimeError, match="LLM provider exploded"):
                await _generate_design_content(
                    tasks=tasks,
                    project_description="P",
                    project_name="P",
                    project_root=str(tmp_path),
                )

        # At least 3 attempts must have fired for the failing call.
        # (The other 4 parallel calls for this task may also have fired
        # before gather cancelled them — we don't assert an exact count.)
        assert fail_count["n"] >= 3

        # Task must NOT have been marked DONE on failure
        assert tasks[0].status == TaskStatus.TODO
        assert tasks[0].assigned_to is None
        assert "auto_completed" not in tasks[0].labels

    @pytest.mark.asyncio
    async def test_no_design_tasks_returns_empty_dict(self, tmp_path: Any) -> None:
        """Early-return path when no design tasks exist in the input."""
        # Implementation task, not a design task
        task = Mock()
        task.name = "Implement Feature"
        task.description = "..."
        task.labels = ["backend"]
        task.status = TaskStatus.TODO

        with patch("src.ai.providers.llm_abstraction.LLMAbstraction") as mock_llm_cls:
            result = await _generate_design_content(
                tasks=[task],
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        assert result == {}
        # Should not even instantiate the LLM client
        mock_llm_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_concurrency_cap_limits_in_flight_calls(self, tmp_path: Any) -> None:
        """Semaphore(10) should cap the max observed in-flight LLM calls.

        With 3 tasks × 5 calls = 15 potential parallel calls, the
        Semaphore(10) guard should limit concurrent in-flight calls to
        at most 10 at any instant. We observe this by tracking
        enter/exit of the mocked ``analyze`` coroutine.
        """
        concurrency = {"current": 0, "max": 0}
        lock = asyncio.Lock()

        async def tracked_analyze(prompt: str, context: Any) -> str:
            async with lock:
                concurrency["current"] += 1
                concurrency["max"] = max(concurrency["max"], concurrency["current"])
            try:
                await asyncio.sleep(0.05)
                return _mock_llm_response(prompt, context)
            finally:
                async with lock:
                    concurrency["current"] -= 1

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=tracked_analyze)

        tasks = [
            _make_design_task("Design One"),
            _make_design_task("Design Two"),
            _make_design_task("Design Three"),
        ]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            await _generate_design_content(
                tasks=tasks,
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        # Semaphore is set to 10; 15 potential calls — max observed should
        # be ≤ 10 (with some slack for scheduler timing, we assert ≤ 10)
        assert concurrency["max"] <= 10, (
            f"Observed {concurrency['max']} concurrent LLM calls — "
            f"Semaphore(10) should cap this"
        )
        # All 15 calls should have completed
        assert mock_llm.analyze.call_count == 15

    @pytest.mark.asyncio
    async def test_duplicate_design_task_names_both_get_llm_calls_and_done(
        self, tmp_path: Any
    ) -> None:
        """Two design tasks with the same name must both run and both DONE.

        Regression test for the Codex P2 review on PR #322. The first
        version of the #320 PR 1 refactor built a
        ``{domain_name: task}`` dict, which silently dropped duplicate
        tasks — only one LLM call would fire and only one task would
        be marked DONE.

        Under normal operation the PRD parser's
        ``_create_bundled_design_tasks`` emits one design task per
        unique domain, so collisions are not reachable from that
        code path. But nothing enforces that invariant downstream,
        and the pre-#320 code was correct under the weaker
        assumption. Per-task iteration must be preserved so future
        code paths that produce duplicates (or bugs that accidentally
        do) don't silently drop work.
        """
        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=_mock_llm_response)

        # Two tasks with the EXACT same name but different descriptions
        tasks = [
            _make_design_task("Design Auth", description="JWT-based auth"),
            _make_design_task("Design Auth", description="OAuth-based auth"),
        ]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_design_content(
                tasks=tasks,
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        # 2 tasks × 5 calls each = 10 total LLM calls — both tasks
        # must get their own LLM calls, not share a single set.
        assert mock_llm.analyze.call_count == 10

        # BOTH tasks must be marked DONE — not just one
        assert tasks[0].status == TaskStatus.DONE
        assert tasks[1].status == TaskStatus.DONE
        assert tasks[0].assigned_to == "Marcus"
        assert tasks[1].assigned_to == "Marcus"
        assert "auto_completed" in tasks[0].labels
        assert "auto_completed" in tasks[1].labels

        # design_content is keyed by task.name; with two identical
        # names, there's only one entry (write-order semantics,
        # preserved from pre-#320 code). The important invariant is
        # that both tasks' WORK was done, not that both appear as
        # distinct keys in the returned dict.
        assert "Design Auth" in result


@pytest.mark.unit
class TestGenerateContractsByDomain:
    """Tests for the domain-keyed contract generation entry point (GH-320 PR 1).

    ``_generate_contracts_by_domain`` is the task-free sibling of
    ``_generate_design_content``. It takes a ``{domain_name:
    domain_description}`` dict and returns results keyed by domain
    name, without touching any Task objects. This is the entry point
    the contract-first decomposition path in PR 2 will call from the
    planner before any tasks exist.

    These tests verify the new function's behavior directly; the
    existing ``TestDesignAutocompleteParallelism`` class exercises
    the same code paths indirectly via ``_generate_design_content``.
    """

    @pytest.mark.asyncio
    async def test_generates_contracts_keyed_by_domain(self, tmp_path: Any) -> None:
        """Happy path: domains dict in, domain-keyed results out.

        Verifies that each domain in the input produces a
        ``{"artifacts": [...], "decisions": [...]}`` entry in the
        output, keyed by the domain name (not mangled or re-keyed),
        and that artifact files are written to disk under the
        project root.
        """
        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=_mock_llm_response)

        domains = {
            "Authentication": "Design the auth domain with JWT-based login.",
            "Payments": "Design the payment domain with Stripe integration.",
        }

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_contracts_by_domain(
                domains=domains,
                project_description="A SaaS platform.",
                project_name="TestProject",
                project_root=str(tmp_path),
            )

        # Both domains should appear in the result, keyed by name
        assert set(result.keys()) == {"Authentication", "Payments"}

        # 2 domains × 5 LLM calls each (4 artifacts + 1 decisions) = 10
        assert mock_llm.analyze.call_count == 10

        # Each domain should have 4 artifacts and 1 parsed decision
        for domain_name in ("Authentication", "Payments"):
            entry = result[domain_name]
            assert entry is not None
            assert len(entry["artifacts"]) == 4
            assert len(entry["decisions"]) == 1
            # All artifact files should exist on disk
            for artifact in entry["artifacts"]:
                file_path = tmp_path / artifact["relative_path"]
                assert (
                    file_path.exists()
                ), f"Missing artifact file for {domain_name}: {file_path}"

    @pytest.mark.asyncio
    async def test_empty_domains_returns_empty_dict(self, tmp_path: Any) -> None:
        """Early-return path: empty domains dict produces empty result.

        Should not instantiate the LLM client or make any LLM calls.
        """
        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
        ) as mock_llm_cls:
            result = await _generate_contracts_by_domain(
                domains={},
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        assert result == {}
        mock_llm_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_domain_with_empty_response_returns_none_for_that_domain(
        self, tmp_path: Any
    ) -> None:
        """A domain where every artifact produced an empty response is None.

        The domain key is still present in the result dict, but the
        value is ``None`` (not a partial entry). This lets the caller
        distinguish "domain processed but no artifacts" from "domain
        not processed at all."
        """

        async def empty_analyze(prompt: str, context: Any) -> str:
            return "nope"  # shorter than 20 chars, gets filtered

        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=empty_analyze)

        domains = {"Auth": "Design the auth domain."}

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_contracts_by_domain(
                domains=domains,
                project_description="P",
                project_name="P",
                project_root=str(tmp_path),
            )

        assert "Auth" in result
        assert result["Auth"] is None

    @pytest.mark.asyncio
    async def test_generate_design_content_still_produces_same_output_shape(
        self, tmp_path: Any
    ) -> None:
        """Regression: ``_generate_design_content`` behavior unchanged.

        The task-based entry point is now a thin adapter over
        ``_generate_contracts_by_domain``, but callers should see
        the same output shape: mapping of task name ->
        ``{"artifacts": [...], "decisions": [...]}`` and design
        tasks mutated in-place to ``status=DONE``,
        ``assigned_to="Marcus"``, and the ``auto_completed`` label.

        This test is a belt-and-suspenders regression guard. The
        broader ``TestDesignAutocompleteParallelism`` class already
        covers these properties individually; this one asserts the
        full shape end-to-end after the refactor.
        """
        mock_llm = Mock()
        mock_llm.analyze = AsyncMock(side_effect=_mock_llm_response)

        tasks = [
            _make_design_task("Design Authentication"),
            _make_design_task("Design Payments"),
        ]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=mock_llm,
        ):
            result = await _generate_design_content(
                tasks=tasks,
                project_description="A SaaS platform.",
                project_name="TestProject",
                project_root=str(tmp_path),
            )

        # Output is keyed by TASK name (with "Design " prefix), not
        # domain name. That's the whole point of the adapter layer —
        # the caller's contract hasn't changed.
        assert set(result.keys()) == {
            "Design Authentication",
            "Design Payments",
        }
        for task in tasks:
            assert task.status == TaskStatus.DONE
            assert task.assigned_to == "Marcus"
            assert "auto_completed" in task.labels

        # Both tasks should have 4 artifacts + 1 decision, and the
        # filenames should use the domain slug (without the "design-"
        # prefix).
        for task_name in ("Design Authentication", "Design Payments"):
            entry = result[task_name]
            assert len(entry["artifacts"]) == 4
            assert len(entry["decisions"]) == 1
            # Verify the filename reflects the domain, not the full
            # task name
            for artifact in entry["artifacts"]:
                assert "authentication" in artifact["relative_path"] or (
                    "payments" in artifact["relative_path"]
                )
                assert "design-" not in artifact["filename"]


@pytest.mark.unit
class TestSiblingDomainsBlock:
    """
    Tests for ``_build_sibling_domains_block`` — the GH-320 Option A
    scope clamp. Verifies the sibling block gives the contract
    generator prompt concrete referents for "don't leak other
    domains' fields" so the LLM stops producing cross-file type
    contradictions.
    """

    def test_empty_domains_returns_empty_string(self) -> None:
        """Single-domain project has no siblings → empty block."""
        assert _build_sibling_domains_block("Auth", {"Auth": "…"}) == ""

    def test_empty_map_returns_empty_string(self) -> None:
        """No domains at all → empty block (defensive)."""
        assert _build_sibling_domains_block("Auth", {}) == ""

    def test_current_domain_excluded_from_block(self) -> None:
        """The caller's own domain must not appear in the sibling list."""
        block = _build_sibling_domains_block(
            "Auth",
            {"Auth": "Auth description", "Billing": "Billing description"},
        )
        assert "**Auth**:" not in block
        assert "**Billing**:" in block

    def test_multiple_siblings_listed(self) -> None:
        """All non-current domains must appear as bullets."""
        block = _build_sibling_domains_block(
            "Dashboard",
            {
                "Dashboard": "…",
                "Weather": "Weather widget",
                "Time": "Time widget",
            },
        )
        assert "**Weather**:" in block
        assert "**Time**:" in block
        assert "**Dashboard**:" not in block

    def test_description_truncated_to_100_chars(self) -> None:
        """Long descriptions are truncated with an ellipsis."""
        long_desc = "x" * 500
        block = _build_sibling_domains_block("A", {"A": "...", "B": long_desc})
        # Find the B bullet line
        b_line = next(line for line in block.split("\n") if line.startswith("- **B**:"))
        # Line form: "- **B**: xxxx..." — stripped desc ≤100, then
        # ellipsis on top. Verify total length stays bounded.
        desc_part = b_line.split(":", 1)[1].strip()
        assert len(desc_part) <= 100
        assert desc_part.endswith("...")

    def test_description_whitespace_collapsed(self) -> None:
        """Multi-line descriptions collapse to a single scannable line."""
        block = _build_sibling_domains_block(
            "A",
            {
                "A": "...",
                "B": "First line\n\nSecond line\n\tThird line",
            },
        )
        b_line = next(line for line in block.split("\n") if line.startswith("- **B**:"))
        assert "\n" not in b_line
        assert "First line Second line Third line" in b_line

    def test_block_contains_scope_instruction(self) -> None:
        """
        The block must name the behavior the LLM should adopt, not
        just list the siblings — the list alone is inert without the
        directive to stop-and-reference instead of redefine.
        """
        block = _build_sibling_domains_block("A", {"A": "...", "B": "B desc"})
        # The directive lives in the closing block of the helper —
        # it names the Invariant 5 failure mode explicitly so future
        # maintainers see the loop between prompt and smoke test.
        assert "BEFORE WRITING ANY FIELD" in block
        assert "Invariant 5" in block

    def test_none_passthrough_safe(self) -> None:
        """
        ``_generate_single_artifact`` passes ``all_domains=None`` when
        the caller has no domain map. The helper is guarded at the
        call site, but verify the helper tolerates the case anyway
        (defensive: empty map and None must both yield empty block).
        """
        # The helper signature takes a non-None Dict, but empty dict
        # is the None-equivalent as far as behavior goes. This
        # double-checks that no sibling block is emitted and callers
        # don't need to special-case the render.
        assert _build_sibling_domains_block("A", {}) == ""


@pytest.mark.unit
class TestSiblingBlockPromptIntegration:
    """
    Integration-style tests that verify the sibling block reaches
    the actual LLM prompt via ``_generate_single_artifact`` and
    ``_generate_single_decisions``. Uses a captured-prompt mock so
    the test can inspect what the LLM actually sees.
    """

    @pytest.mark.asyncio
    async def test_artifact_prompt_carries_sibling_block_feature_based(
        self, tmp_path: Any
    ) -> None:
        """
        Feature-based path: when multiple design tasks exist, each
        task's artifact prompts must include a Sibling Domains
        block naming the OTHER tasks' domains.
        """
        captured_prompts: List[str] = []

        async def capture_analyze(prompt: str, context: Any) -> str:
            captured_prompts.append(prompt)
            return _mock_llm_response(prompt, context)

        fake_llm = Mock()
        fake_llm.analyze = AsyncMock(side_effect=capture_analyze)

        tasks = [
            _make_design_task("Design Weather", "weather widget description"),
            _make_design_task("Design Time", "time widget description"),
        ]

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=fake_llm,
        ):
            await _generate_design_content(
                tasks=tasks,
                project_description="two widget dashboard",
                project_name="test",
                project_root=str(tmp_path),
            )

        # Weather prompts should name Time as a sibling, and Time
        # prompts should name Weather. The "**X** domain" marker
        # appears in the "Generate the ... document for the **X**
        # domain" line in both _ARTIFACT_PROMPT and
        # _INTERFACE_CONTRACTS_PROMPT.
        weather_prompts = [p for p in captured_prompts if "**Weather** domain" in p]
        time_prompts = [p for p in captured_prompts if "**Time** domain" in p]
        assert weather_prompts, "no prompts addressed to Weather domain"
        assert time_prompts, "no prompts addressed to Time domain"
        for p in weather_prompts:
            assert "Sibling Domains" in p
            assert "**Time**:" in p  # Time listed as sibling
            # Self-reference appears in "for the **Weather** domain",
            # not in the sibling bullet list. Make sure no sibling
            # bullet lists Weather.
            assert "- **Weather**:" not in p
        for p in time_prompts:
            assert "Sibling Domains" in p
            assert "**Weather**:" in p
            assert "- **Time**:" not in p

    @pytest.mark.asyncio
    async def test_contracts_by_domain_passes_siblings(self, tmp_path: Any) -> None:
        """
        The contract-first path (``_generate_contracts_by_domain``)
        must thread the full ``domains`` dict into every per-domain
        prompt so each domain sees its siblings.
        """
        captured_prompts: List[str] = []

        async def capture_analyze(prompt: str, context: Any) -> str:
            captured_prompts.append(prompt)
            return _mock_llm_response(prompt, context)

        fake_llm = Mock()
        fake_llm.analyze = AsyncMock(side_effect=capture_analyze)

        domains = {
            "Auth": "Auth description",
            "Billing": "Billing description",
            "Dashboard": "Dashboard description",
        }

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=fake_llm,
        ):
            await _generate_contracts_by_domain(
                domains=domains,
                project_description="a multi-domain app",
                project_name="test",
                project_root=str(tmp_path),
            )

        # Each domain's prompts must list the other two as siblings
        # and exclude itself from the sibling bullet list.
        for current, siblings in [
            ("Auth", ["Billing", "Dashboard"]),
            ("Billing", ["Auth", "Dashboard"]),
            ("Dashboard", ["Auth", "Billing"]),
        ]:
            matching = [p for p in captured_prompts if f"**{current}** domain" in p]
            assert matching, f"no prompts for domain {current}"
            for prompt in matching:
                assert "Sibling Domains" in prompt
                assert f"- **{current}**:" not in prompt  # self excluded
                for sib in siblings:
                    assert (
                        f"- **{sib}**:" in prompt
                    ), f"sibling {sib} missing from {current} prompt"

    @pytest.mark.asyncio
    async def test_single_domain_has_no_sibling_block(self, tmp_path: Any) -> None:
        """
        Single-domain project: the sibling block renders empty and
        the prompt has no Sibling Domains heading.
        """
        captured_prompts: List[str] = []

        async def capture_analyze(prompt: str, context: Any) -> str:
            captured_prompts.append(prompt)
            return _mock_llm_response(prompt, context)

        fake_llm = Mock()
        fake_llm.analyze = AsyncMock(side_effect=capture_analyze)

        with patch(
            "src.ai.providers.llm_abstraction.LLMAbstraction",
            return_value=fake_llm,
        ):
            await _generate_contracts_by_domain(
                domains={"Solo": "the only domain"},
                project_description="single-domain app",
                project_name="test",
                project_root=str(tmp_path),
            )

        for prompt in captured_prompts:
            assert "Sibling Domains" not in prompt
