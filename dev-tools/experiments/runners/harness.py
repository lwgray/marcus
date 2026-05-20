"""
Per-CLI harness definitions for the Marcus experiment runner.

A *harness* is the agent CLI a spawned tmux pane runs — currently
``claude`` (Anthropic's Claude Code) or ``codex`` (OpenAI's Codex
CLI).  Both speak the same Marcus MCP protocol, but the surface
around them — the exact shell command, the worker-keepalive
wrapper, the trust-dialog handling, the workflow-file convention,
and the install hint shown on a missing binary — differs.

Before this module landed, ``AgentSpawner`` had six ``if/elif`` sites
spread across one ~2000-line file, one per harness-specific quirk.
Adding a third harness (e.g. ``gemini``) meant editing every site.
This module collects every harness-specific behavior into a single
:class:`Harness` Protocol with one implementation per CLI, plus a
:data:`HARNESSES` registry the spawner looks up by name.

The contract is "byte-identical rendered shell scripts": the strings
returned here must be exactly what the previous ``if/elif`` blocks
returned, so the existing ``TestCodexScriptsRender`` and sibling
tests stay green without modification.

Classes
-------
Harness
    Structural protocol every harness implementation must satisfy.
ClaudeHarness
    Default harness — Anthropic Claude Code CLI.
CodexHarness
    OpenAI Codex CLI harness with ``--enable goals`` + a bounded
    bash relaunch loop.

Functions
---------
get_harness(name)
    Resolve a harness by name, raising :class:`ValueError` for
    unknown names with a list of supported choices.

Data
----
HARNESSES
    Mapping of harness name -> :class:`Harness` instance.
"""

from pathlib import Path
from typing import Dict, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class Harness(Protocol):
    """Structural protocol every per-CLI harness implementation satisfies.

    Attributes
    ----------
    name : str
        Stable identifier the runner stores on ``config.harness`` and
        the user picks on the command line (``--harness <name>``).
    binary : str
        Executable name looked up on PATH during the spawner
        pre-flight.
    provider : str
        Cost-tracking provider label (``"anthropic"`` / ``"openai"``).
        Reserved for the cost ingester work tracked in issue #582 —
        ``src/cost_tracking/worker_ingester.py`` writes
        ``provider="anthropic"`` today; once #582 lands the codex
        ingester will read this field rather than hardcoding a
        provider string per code path.
    needs_trust_dialog_poll : bool
        ``True`` when the harness raises an interactive trust dialog
        on first launch in a directory; the spawner then polls each
        pane for the prompt and confirms it.  Claude only.
    needs_pretrust_directory : bool
        ``True`` when the harness reads a per-directory trust file
        (e.g. ``~/.claude.json``) that the spawner must seed before
        launch.  Claude only.
    workflow_files : Tuple[str, ...]
        Workflow filenames the spawner copies into the implementation
        directory so the agent picks up Marcus-specific guidance.
        For codex, both ``CLAUDE.md`` and ``AGENTS.md`` are written —
        the latter is the codex-specific convention
        (https://developers.openai.com/codex/guides/agents-md).
    """

    name: str
    binary: str
    provider: str
    needs_trust_dialog_poll: bool
    needs_pretrust_directory: bool
    workflow_files: Tuple[str, ...]

    def build_agent_command(
        self,
        workdir: Path,
        prompt_file: Path,
        *,
        model_flag: str,
        print_mode: bool = False,
    ) -> str:
        """Return the per-pane shell command line that launches the agent."""
        ...

    def wrap_worker_invocation(self, inner_cmd: str) -> str:
        """Return the worker shell block: bare invocation or wrapped loop.

        ``inner_cmd`` is the pre-rendered single-shot command produced
        by :meth:`build_agent_command`.  Implementations decide whether
        to return it unchanged (claude TUI stays alive) or wrap it
        (codex relaunch loop).

        .. note::
            Resist adding knobs through ``inner_cmd`` — if a future
            harness needs different wrapping behavior, expose the
            distinction as a *structured* parameter or a new method.
            Threading semantics through the inner command string
            re-couples the strategy classes to each other.
        """
        ...

    def build_mcp_register_snippet(self) -> str:
        """Return the snippet that registers Marcus MCP from inside a pane."""
        ...

    def install_hint(self, marcus_mcp_url: str) -> List[str]:
        """Return printable lines suggesting how to install the missing CLI."""
        ...


class ClaudeHarness:
    """Harness for Anthropic's Claude Code CLI (the original Marcus harness).

    Claude is a long-lived TUI process: a single launch stays alive
    across many model turns inside the pane.  No keepalive wrapper is
    needed.  Claude raises an interactive trust dialog the first time
    it touches a directory, so the spawner polls for it and writes
    ``~/.claude.json`` ahead of time (pretrust).
    """

    name: str = "claude"
    binary: str = "claude"
    provider: str = "anthropic"
    needs_trust_dialog_poll: bool = True
    needs_pretrust_directory: bool = True
    workflow_files: Tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")

    def build_agent_command(
        self,
        workdir: Path,
        prompt_file: Path,
        *,
        model_flag: str,
        print_mode: bool = False,
    ) -> str:
        """Render the ``claude`` invocation for one pane.

        Parameters
        ----------
        workdir : Path
            Directory passed via ``--add-dir`` as the agent's writable
            workspace.
        prompt_file : Path
            File piped to claude on stdin.
        model_flag : str
            Pre-formatted ``"--model X "`` string (empty when no model
            override is set).  Pre-formatted by the caller so the
            harness does not need to know about model-resolution rules.
        print_mode : bool, optional
            When ``True``, append ``--print`` so claude exits with
            stdout flushed.  Used by the project-creator pane.

        Returns
        -------
        str
            Single shell command with backslash-newline continuations,
            matching the byte layout the prior ``if/elif`` produced.
        """
        print_flag = "--print " if print_mode else ""
        return (
            f"claude --add-dir {workdir} \\\n"
            f"  {model_flag}--dangerously-skip-permissions "
            f"{print_flag}< {prompt_file}"
        )

    def wrap_worker_invocation(self, inner_cmd: str) -> str:
        """Claude TUI stays alive across model turns — no wrapper needed."""
        return inner_cmd

    def build_mcp_register_snippet(self) -> str:
        """``claude mcp add`` writes to ``~/.claude.json``.

        ``|| true`` swallows the "already exists" error so re-spawned
        panes do not abort on the registration step.
        """
        return 'claude mcp add marcus -t http "$MARCUS_MCP_URL" ' "2>/dev/null || true"

    def install_hint(self, marcus_mcp_url: str) -> List[str]:
        """Single-line install hint shown when ``claude`` is missing."""
        return ["  Install Claude Code CLI then retry."]


class CodexHarness:
    """Harness for OpenAI's Codex CLI.

    ``codex exec`` is fire-and-exit by default: each invocation runs
    until the model judges the goal complete or the token budget is
    reached.  ``--enable goals`` extends that significantly (the
    agent treats the prompt as a never-ending goal and keeps polling
    Marcus across empty ``request_next_task`` cycles), but the
    invocation can still exit on edge cases — the model handing in
    ``update_goal(complete)``, a token-budget cap, an unrecoverable
    error.  A bounded bash relaunch loop wraps the invocation as a
    safety net: ``MAX_RELAUNCHES`` caps runaway token spend if
    something is genuinely wedged, and a clean ``rc=0`` exit breaks
    the loop early so a deliberately-completed run does not keep
    burning tokens (especially relevant under ``--epictetus``).
    """

    name: str = "codex"
    binary: str = "codex"
    provider: str = "openai"
    needs_trust_dialog_poll: bool = False
    needs_pretrust_directory: bool = False
    workflow_files: Tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")

    def build_agent_command(
        self,
        workdir: Path,
        prompt_file: Path,
        *,
        model_flag: str,
        print_mode: bool = False,
    ) -> str:
        """Render the ``codex exec`` invocation for one pane.

        Flags
        -----
        ``--dangerously-bypass-approvals-and-sandbox``
            Documented "YOLO mode" — approval=never,
            sandbox=danger-full-access.  Required for unattended
            tmux panes where no human can confirm approvals.
        ``--skip-git-repo-check``
            Monitor pane and similar start before any commits exist;
            this stops codex from refusing to launch on an "empty"
            repository.
        ``--disable guardian_approval``
            Turns off codex's "files changed under me without my
            doing it" safety check.  Required because Marcus workers
            run ``git merge main --no-edit`` between tasks (see
            agent_prompt.md) which guardian otherwise treats as
            anomalous and halts the agent on.
        ``--enable goals``
            Turns on codex's autonomous agentic loop.  The agent
            treats the prompt as a never-ending goal and keeps
            polling instead of wrapping up after two empty cycles.

        ``print_mode`` is ignored — ``codex exec`` is inherently
        non-interactive.

        Parameters
        ----------
        workdir : Path
            Working root passed to ``-C`` and ``--add-dir``.
        prompt_file : Path
            File piped to codex on stdin.
        model_flag : str
            Pre-formatted ``"--model X "`` string.
        print_mode : bool, optional
            Ignored.  Codex is always non-interactive.

        Returns
        -------
        str
            Single shell command with backslash-newline continuations.
        """
        del print_mode  # codex is always non-interactive
        return (
            f"codex exec --dangerously-bypass-approvals-and-sandbox "
            f"--skip-git-repo-check --disable guardian_approval "
            f"--enable goals "
            f"-C {workdir} --add-dir {workdir} \\\n"
            f"  {model_flag}< {prompt_file}"
        )

    def wrap_worker_invocation(self, inner_cmd: str) -> str:
        """Wrap ``codex exec`` in a bounded bash relaunch loop.

        Breaks the loop on ``rc=0`` (clean exit) so a worker that
        finishes naturally stays quiescent — important under
        ``--epictetus``, where the monitor leaves the tmux session
        up for post-run interrogation.  Non-zero exits (crashes,
        token-budget hits, signals) still trigger a relaunch with a
        3-second sleep.  ``MAX_RELAUNCHES`` caps runaway spend if
        something is genuinely wedged.
        """
        return (
            "MAX_RELAUNCHES=50\n"
            "for relaunch in $(seq 1 $MAX_RELAUNCHES); do\n"
            f'  echo "[worker] codex launch $relaunch/$MAX_RELAUNCHES"\n'
            f"  {inner_cmd}\n"
            "  rc=$?\n"
            "  if [ $rc -eq 0 ]; then\n"
            '    echo "[worker] codex exec finished cleanly (rc=0);'
            ' not relaunching"\n'
            "    break\n"
            "  fi\n"
            '  echo "[worker] codex exec exited rc=$rc;'
            ' relaunching in 3s..."\n'
            "  sleep 3\n"
            "done\n"
            'echo "[worker] hit MAX_RELAUNCHES=$MAX_RELAUNCHES — giving up"'
        )

    def build_mcp_register_snippet(self) -> str:
        """``codex mcp add`` writes to ``~/.codex/config.toml``.

        ``|| true`` swallows the "already exists" error so re-spawned
        panes do not abort on the registration step.
        """
        return 'codex mcp add marcus --url "$MARCUS_MCP_URL" ' "2>/dev/null || true"

    def install_hint(self, marcus_mcp_url: str) -> List[str]:
        """Two-line install hint shown when ``codex`` is missing."""
        return [
            "  Install via: npm install -g @openai/codex",
            (
                "  Then register Marcus MCP: codex mcp add marcus "
                f'--url "{marcus_mcp_url}"'
            ),
        ]


HARNESSES: Dict[str, Harness] = {
    ClaudeHarness.name: ClaudeHarness(),
    CodexHarness.name: CodexHarness(),
}


def get_harness(name: str) -> Harness:
    """Look up a harness implementation by name.

    Parameters
    ----------
    name : str
        Harness identifier — must be a key in :data:`HARNESSES`.

    Returns
    -------
    Harness
        The matching implementation singleton.

    Raises
    ------
    ValueError
        When ``name`` is not a registered harness.  The error message
        lists every supported name so the user sees the right value
        immediately.
    """
    try:
        return HARNESSES[name]
    except KeyError as exc:
        choices = ", ".join(sorted(HARNESSES))
        raise ValueError(f"Unknown harness {name!r}; supported: {choices}") from exc
