"""
Unit tests for ``_extract_declared_files`` (#206 MVP, Phase 2).

This helper is called inside ``decompose_by_contract`` after the
LLM-produced task list is parsed. For each contract task it produces
the list of file paths the task intends to write to. The list is
persisted into ``task.source_context["declared_files"]`` and later
consulted by ``request_next_task`` (Phase 3) to skip tasks whose
files are currently held by another in-progress task.

MVP scope (per design doc open question #1): **conservative** —
the only declared write target is the task's own ``contract_file``.
Contract artifacts (foundation files) and other inferred
implementation files are NOT declared, because:

- Contract artifacts are READ by every implementation task; the
  registry only locks writes (reads are free).
- Inferred impl files would risk over-blocking (false-positive
  conflicts) before we have empirical data on contention rates.
- Bright-line: ``contract_file`` is already part of the contract
  responsibility (a WHAT, not a HOW), so declaring it adds no new
  constraint on the agent's implementation choices.

If a task has no ``contract_file`` (e.g., legacy feature-based
tasks, foundation pre-fork tasks), the helper returns an empty list
and the task is unaffected by the lock filter.
"""

import pytest

from src.ai.advanced.prd.advanced_parser import _extract_declared_files

pytestmark = pytest.mark.unit


class TestExtractDeclaredFiles:
    """``_extract_declared_files`` is the contract-first declarer."""

    def test_returns_contract_file_when_present(self) -> None:
        """A contract task with a contract_file declares that file."""
        files = _extract_declared_files(
            responsibility="implements GameEngine interface",
            contract_file="src/types/engine.ts",
            contract_artifacts={},
        )
        assert files == ["src/types/engine.ts"]

    def test_returns_empty_list_when_contract_file_missing(self) -> None:
        """A task without a contract_file declares nothing (MVP conservative).

        These tasks pass through ``request_next_task`` unfiltered —
        the registry returns False for ``any_held([])``.
        """
        files = _extract_declared_files(
            responsibility="vague description with no file",
            contract_file="",
            contract_artifacts={},
        )
        assert files == []

    def test_returns_empty_list_when_responsibility_missing(self) -> None:
        """Defensive: no responsibility AND no contract_file -> empty."""
        files = _extract_declared_files(
            responsibility="",
            contract_file="",
            contract_artifacts={},
        )
        assert files == []

    def test_does_not_include_contract_artifacts(self) -> None:
        """Contract artifacts are READ files — never in declared_files.

        The registry only locks writes; agents read freely from the
        foundation contract artifacts. Including them would block
        every implementation task on every other one because they
        all read the same foundation files.
        """
        files = _extract_declared_files(
            responsibility="implements GameEngine",
            contract_file="src/types/engine.ts",
            contract_artifacts={
                "domain_contract": {
                    "file_path": "src/types/engine.ts",
                    "schema_file": "src/types/schema.ts",
                },
                "api_contract": {
                    "file_path": "src/types/api.ts",
                },
            },
        )
        # Only the task's own contract_file is declared.
        assert files == ["src/types/engine.ts"]

    def test_handles_none_contract_file(self) -> None:
        """Defensive: contract_file=None (not empty string) -> empty list.

        Callers in the parser coerce to ``str(raw or "")`` so this
        normally cannot happen, but the helper should be robust.
        """
        files = _extract_declared_files(
            responsibility="anything",
            contract_file=None,
            contract_artifacts={},
        )
        assert files == []

    def test_handles_none_contract_artifacts(self) -> None:
        """``contract_artifacts=None`` must not raise."""
        files = _extract_declared_files(
            responsibility="implements GameEngine",
            contract_file="src/types/engine.ts",
            contract_artifacts=None,
        )
        assert files == ["src/types/engine.ts"]

    def test_strips_whitespace_in_contract_file(self) -> None:
        """A whitespace-only contract_file is treated as missing."""
        files = _extract_declared_files(
            responsibility="anything",
            contract_file="   ",
            contract_artifacts={},
        )
        assert files == []

    def test_normalizes_contract_file_value(self) -> None:
        """A contract_file with surrounding whitespace is normalized."""
        files = _extract_declared_files(
            responsibility="anything",
            contract_file="  src/types/engine.ts  ",
            contract_artifacts={},
        )
        assert files == ["src/types/engine.ts"]
