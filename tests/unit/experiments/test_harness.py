"""
Unit tests for the per-CLI harness registry.

``dev-tools/experiments/runners/harness.py`` defines the :class:`Harness`
Protocol and one implementation per agent CLI (``ClaudeHarness``,
``CodexHarness``).  These tests pin the contract directly — the
``test_spawn_agents.py`` suite continues to cover the integration with
``AgentSpawner``.
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# dev-tools uses a hyphen → not importable as a package → load via importlib.
_HARNESS_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "dev-tools"
    / "experiments"
    / "runners"
    / "harness.py"
)
_spec = importlib.util.spec_from_file_location("harness", _HARNESS_PATH)
assert _spec is not None and _spec.loader is not None
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    """``HARNESSES`` + ``get_harness`` resolve names to implementations."""

    def test_registry_lists_both_claude_and_codex(self) -> None:
        """Today's two supported harnesses are present."""
        assert set(harness.HARNESSES) == {"claude", "codex"}

    def test_get_harness_returns_singleton(self) -> None:
        """Repeated lookups for the same name return the same object."""
        assert harness.get_harness("claude") is harness.get_harness("claude")
        assert harness.get_harness("codex") is harness.get_harness("codex")

    def test_get_harness_raises_with_choices_listed(self) -> None:
        """Unknown harness name → ValueError naming every supported choice."""
        with pytest.raises(ValueError, match="claude, codex") as exc:
            harness.get_harness("gemini")
        # User who typed the wrong name sees the supported list — both
        # current names appear in the message.
        assert "gemini" in str(exc.value)
        assert "claude" in str(exc.value)
        assert "codex" in str(exc.value)


# ---------------------------------------------------------------------------
# Per-harness metadata (the cheap-to-read attributes)
# ---------------------------------------------------------------------------


class TestClaudeHarnessMetadata:
    """``ClaudeHarness`` carries claude-specific flags + provider tag."""

    def test_identity(self) -> None:
        """Name + binary are both ``"claude"``; provider is anthropic."""
        impl = harness.get_harness("claude")
        assert impl.name == "claude"
        assert impl.binary == "claude"
        assert impl.provider == "anthropic"

    def test_needs_trust_dialog_poll_true(self) -> None:
        """Claude's first-run prompt requires the spawner to poll for it."""
        assert harness.get_harness("claude").needs_trust_dialog_poll is True

    def test_needs_pretrust_directory_true(self) -> None:
        """Claude reads ~/.claude.json; pretrust seeds it."""
        assert harness.get_harness("claude").needs_pretrust_directory is True

    def test_workflow_files_include_both_conventions(self) -> None:
        """Both CLAUDE.md and AGENTS.md are written — harmless for claude,
        load-bearing for codex (and we always copy both)."""
        impl = harness.get_harness("claude")
        assert "CLAUDE.md" in impl.workflow_files
        assert "AGENTS.md" in impl.workflow_files


class TestCodexHarnessMetadata:
    """``CodexHarness`` carries codex-specific flags + provider tag."""

    def test_identity(self) -> None:
        """Name + binary are both ``"codex"``; provider is openai."""
        impl = harness.get_harness("codex")
        assert impl.name == "codex"
        assert impl.binary == "codex"
        assert impl.provider == "openai"

    def test_needs_trust_dialog_poll_false(self) -> None:
        """Codex under ``--yolo`` has no interactive trust dialog."""
        assert harness.get_harness("codex").needs_trust_dialog_poll is False

    def test_needs_pretrust_directory_false(self) -> None:
        """Codex bypasses its own per-directory trust dialog under ``--yolo``."""
        assert harness.get_harness("codex").needs_pretrust_directory is False

    def test_workflow_files_include_both_conventions(self) -> None:
        """AGENTS.md is the codex-specific convention; CLAUDE.md harmless."""
        impl = harness.get_harness("codex")
        assert "AGENTS.md" in impl.workflow_files
        assert "CLAUDE.md" in impl.workflow_files


# ---------------------------------------------------------------------------
# Rendered shell — must match the strings the old if/elif produced
# ---------------------------------------------------------------------------


class TestClaudeRenderedShell:
    """Strings the ClaudeHarness emits, asserted exactly."""

    def test_agent_command_print_mode(self, tmp_path: Path) -> None:
        """Project-creator pane uses ``--print``."""
        impl = harness.get_harness("claude")
        cmd = impl.build_agent_command(
            tmp_path / "work",
            tmp_path / "prompt.txt",
            model_flag="--model X ",
            print_mode=True,
        )
        assert "claude --add-dir" in cmd
        assert "--dangerously-skip-permissions" in cmd
        assert "--print" in cmd
        assert "--model X" in cmd

    def test_agent_command_non_print_mode_strips_print_flag(
        self, tmp_path: Path
    ) -> None:
        """Worker panes do not get ``--print``."""
        impl = harness.get_harness("claude")
        cmd = impl.build_agent_command(
            tmp_path / "work",
            tmp_path / "prompt.txt",
            model_flag="",
            print_mode=False,
        )
        assert "--print" not in cmd

    def test_wrap_worker_invocation_is_identity(self) -> None:
        """Claude TUI stays alive — wrapper returns the inner command verbatim."""
        impl = harness.get_harness("claude")
        inner = "claude --add-dir /x < /p"
        assert impl.wrap_worker_invocation(inner) == inner

    def test_mcp_register_snippet_uses_http_transport(self) -> None:
        """``claude mcp add ... -t http`` + idempotent ``|| true``."""
        snippet = harness.get_harness("claude").build_mcp_register_snippet()
        assert "claude mcp add marcus -t http" in snippet
        assert "|| true" in snippet
        assert "codex" not in snippet

    def test_install_hint_is_single_line(self) -> None:
        """Claude install hint is a single instruction."""
        lines = harness.get_harness("claude").install_hint("http://localhost:4298/mcp")
        assert len(lines) == 1
        assert "Claude Code CLI" in lines[0]


class TestCodexRenderedShell:
    """Strings the CodexHarness emits, asserted exactly."""

    def test_agent_command_contains_required_flags(self, tmp_path: Path) -> None:
        """Every documented codex flag must land in the rendered command."""
        impl = harness.get_harness("codex")
        cmd = impl.build_agent_command(
            tmp_path / "work",
            tmp_path / "prompt.txt",
            model_flag="--model gpt-5.3-codex ",
            print_mode=False,
        )
        assert "codex exec --dangerously-bypass-approvals-and-sandbox" in cmd
        assert "--skip-git-repo-check" in cmd
        assert "--disable guardian_approval" in cmd
        assert "--enable goals" in cmd
        assert "--model gpt-5.3-codex" in cmd
        # ``-C`` and ``--add-dir`` both point at the working directory.
        assert f"-C {tmp_path / 'work'}" in cmd
        assert f"--add-dir {tmp_path / 'work'}" in cmd

    def test_agent_command_ignores_print_mode(self, tmp_path: Path) -> None:
        """``print_mode`` is silently dropped — codex is always non-interactive."""
        impl = harness.get_harness("codex")
        with_print = impl.build_agent_command(
            tmp_path / "w",
            tmp_path / "p",
            model_flag="",
            print_mode=True,
        )
        without_print = impl.build_agent_command(
            tmp_path / "w",
            tmp_path / "p",
            model_flag="",
            print_mode=False,
        )
        assert with_print == without_print
        assert "--print" not in with_print

    def test_wrap_worker_invocation_renders_bounded_loop(self) -> None:
        """Wrapper is a bash for-loop bounded by MAX_RELAUNCHES."""
        wrapped = harness.get_harness("codex").wrap_worker_invocation(
            "codex exec --foo < prompt"
        )
        assert "MAX_RELAUNCHES=50" in wrapped
        assert "for relaunch in $(seq 1 $MAX_RELAUNCHES)" in wrapped
        assert "codex exec --foo < prompt" in wrapped
        assert "hit MAX_RELAUNCHES" in wrapped

    def test_wrap_worker_invocation_breaks_on_clean_exit(self) -> None:
        """Codex wrapper breaks the loop on rc=0 — Codex review P1 on #554."""
        wrapped = harness.get_harness("codex").wrap_worker_invocation("codex exec")
        assert "rc=$?" in wrapped
        assert "[ $rc -eq 0 ]" in wrapped
        assert "break" in wrapped

    def test_mcp_register_snippet_uses_url_flag(self) -> None:
        """``codex mcp add ... --url`` + idempotent ``|| true``."""
        snippet = harness.get_harness("codex").build_mcp_register_snippet()
        assert "codex mcp add marcus --url" in snippet
        assert "|| true" in snippet
        assert "claude" not in snippet

    def test_install_hint_includes_npm_and_mcp_steps(self) -> None:
        """Codex install hint covers both install + MCP registration."""
        lines = harness.get_harness("codex").install_hint("http://localhost:4298/mcp")
        assert len(lines) == 2
        assert "npm install -g @openai/codex" in lines[0]
        assert "codex mcp add marcus" in lines[1]
        # The user's specific MCP URL is interpolated, not a placeholder.
        assert "http://localhost:4298/mcp" in lines[1]


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """Both implementations satisfy the runtime-checkable :class:`Harness`
    Protocol."""

    def test_claude_implements_harness_protocol(self) -> None:
        """isinstance check passes — ClaudeHarness has every method/attr."""
        assert isinstance(harness.get_harness("claude"), harness.Harness)

    def test_codex_implements_harness_protocol(self) -> None:
        """isinstance check passes — CodexHarness has every method/attr."""
        assert isinstance(harness.get_harness("codex"), harness.Harness)
