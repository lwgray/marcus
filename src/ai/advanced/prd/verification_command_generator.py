"""
Setup-time generation of verification commands per :class:`UserOutcome`.

Background
----------
Issue #636: Marcus's integration verifier ships unplayable apps when the
agent authors its own verification commands. The agent has retry pressure
to keep weakening the command until exit=0; the command that finally
passes may not actually test the user-facing behavior. Project test58
(purple-dot-snake-game) shipped without keyboard input because the
agent's verification for ``outcome_control_snake`` was a trivial check
that didn't simulate a keypress.

Invariant #2 v2 (CLAUDE.md MULTIAGENCY_PROCLAMATION) moved verification
ownership from the agent to Marcus's setup-time pipeline. The agent
still owns implementation (HOW to build the feature); Marcus owns the
contract (WHAT to build AND HOW to verify it was built correctly).
This is the contract-net protocol pattern from 1980s MAS literature.

This module is the setup-time piece: given the project's
:class:`UserOutcome` records (extracted from the spec), it generates a
:class:`ContractVerification` per outcome — a shell command Marcus runs
to demonstrate the outcome's ``success_signal`` against the deliverable.

The smoke gate at completion time (issue #636 Phase B, separate PR) will
prefer these contract-authored commands over agent-supplied ones.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.ai.advanced.prd.outcome_extractor import UserOutcome

logger = logging.getLogger(__name__)


@dataclass
class ContractVerification:
    """A setup-time-authored verification command for one user outcome.

    Marcus generates one per in-scope :class:`UserOutcome` during Phase A
    and stamps the list onto the integration task's
    ``source_context["contract_verifications"]``. At completion time the
    smoke gate runs each command as a subprocess.

    Attributes
    ----------
    signal_id : str
        The ``UserOutcome.id`` this verification observes. Required so
        the smoke gate's coverage check can match verifications to
        in-scope outcomes (issue #523 Slice B).
    command : str
        Shell command Marcus runs as a subprocess in the project's
        composed ``implementation/`` directory. Exit 0 iff the outcome
        was demonstrated; non-zero rejects completion.
    description : str
        Short human label used in smoke-gate log lines and the blocker
        message when the verification fails. Helps operators
        understand which outcome the verifier was observing.
    readiness_probe : Optional[str]
        Optional probe command for long-running server-mode commands.
        When provided, Marcus runs ``command`` in the background and
        polls ``readiness_probe`` (exit 0 = ready) for up to 15s
        before killing the background process. Absent => ``command``
        is one-shot; must exit 0 within 60s.
    """

    signal_id: str
    command: str
    description: str
    readiness_probe: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage on ``source_context``.

        Returns
        -------
        Dict[str, Any]
            JSON-safe dict matching the existing schema used by the
            agent-authored verifications in ``report_task_progress``.
            Compatibility with that schema is intentional: the smoke
            gate can treat contract-authored and agent-authored entries
            interchangeably at the run-as-subprocess layer (issue #636
            Phase B will add the precedence logic above this layer).
        """
        d: Dict[str, Any] = {
            "signal_id": self.signal_id,
            "command": self.command,
            "description": self.description,
        }
        if self.readiness_probe is not None:
            d["readiness_probe"] = self.readiness_probe
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ContractVerification":
        """Reconstruct from a dict produced by :meth:`to_dict`.

        Raises
        ------
        ValueError
            When required fields are missing or non-string. Matches
            the strict-validation style of :class:`UserOutcome` —
            malformed records never enter the pipeline.
        """
        for required in ("signal_id", "command", "description"):
            value = d.get(required)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"ContractVerification: field {required!r} must be a "
                    f"non-empty string, got {value!r}"
                )

        readiness = d.get("readiness_probe")
        if readiness is not None and not isinstance(readiness, str):
            raise ValueError(
                f"ContractVerification: 'readiness_probe' must be a string "
                f"or None, got {readiness!r}"
            )

        return cls(
            signal_id=d["signal_id"],
            command=d["command"],
            description=d["description"],
            readiness_probe=readiness,
        )


_GENERATION_PROMPT_TEMPLATE = """\
You are generating a SHELL COMMAND that Marcus will run as a subprocess
to verify that a user-visible outcome was achieved by a built software
project.

Outcome ID: {outcome_id}
User Action: {action}
Success Signal: {success_signal}

Project description (for tech-stack context):
{project_description}

The command must satisfy ALL of these requirements:

1. Exit 0 if and only if the Success Signal was demonstrated by the
   running deliverable. Non-zero exit means the outcome was not
   demonstrated and the build is incomplete.

2. Actually EXERCISE the user-facing behavior described by the Success
   Signal. Do NOT just check that files exist or modules can be
   imported — those checks pass even when the user-facing behavior is
   broken (the test58 failure mode).

3. Use ONLY tools the project's tech stack already provides. Infer the
   stack from the project description. If the outcome cannot be
   verified using tools the stack already includes, return null for
   the command field — Marcus will surface the gap rather than ship a
   broken verification.

4. Be runnable as a subprocess from the project's root directory. Use
   relative paths or paths starting from the project root.

5. Be idempotent: re-running must not leave state behind (no /tmp
   pollution, no zombie processes, no orphaned databases).

6. For long-running processes (web server, dev server), provide a
   ``readiness_probe`` — a second shell command Marcus polls until it
   exits 0, before declaring the process ready. Marcus always kills
   the background process when the probe is done.

Return strict JSON of the form:

{{
  "command": "<shell command>" or null,
  "readiness_probe": "<optional probe command>" or null,
  "description": "<short human label for log lines>"
}}

Respond with ONLY the JSON object — no preamble, no markdown fences.
"""


async def generate_verification_command(
    outcome: UserOutcome,
    project_description: str,
    llm_client: Any,
    max_tokens: int = 800,
) -> Optional[ContractVerification]:
    """Generate one :class:`ContractVerification` for a single outcome.

    Calls the LLM once to translate the outcome's ``success_signal``
    into a runnable shell command. Returns ``None`` when the LLM
    indicates the outcome cannot be verified with the project's
    available tooling — caller decides whether to flag the gap, drop
    the outcome, or raise.

    Parameters
    ----------
    outcome : UserOutcome
        The outcome to generate a verification for. Both in-scope and
        out-of-scope outcomes are accepted; callers decide whether to
        skip out-of-scope ones before calling.
    project_description : str
        The original project specification, used as tech-stack context
        in the prompt. The LLM infers from this what tools are
        available.
    llm_client : Any
        Any client exposing ``async analyze(prompt, context)`` and
        returning a string. Mocked in unit tests.
    max_tokens : int, optional
        Token budget for the LLM call. Default 800 — verification
        commands are short.

    Returns
    -------
    Optional[ContractVerification]
        A populated :class:`ContractVerification`, or ``None`` when
        the LLM reports the outcome cannot be verified with the
        available tech stack.

    Raises
    ------
    ValueError
        When the LLM returns malformed JSON, missing required fields,
        or non-string values in required fields. Strict-fail mirrors
        :func:`extract_user_outcomes` so malformed records don't
        silently corrupt the contract.
    """
    prompt = _GENERATION_PROMPT_TEMPLATE.format(
        outcome_id=outcome.id,
        action=outcome.action,
        success_signal=outcome.success_signal,
        project_description=project_description,
    )

    from src.utils.structured_llm import safe_structured_call

    try:
        payload = await safe_structured_call(
            llm=llm_client,
            prompt=prompt,
            operation="generate_verification_command",
            initial_max_tokens=max_tokens,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"Verification-command generator: LLM returned malformed JSON "
            f"for outcome {outcome.id!r}: {exc}"
        ) from exc

    command = payload.get("command")
    if command is None:
        # LLM explicitly declined — tech stack can't verify this
        # outcome. Caller surfaces the gap (don't silently drop).
        logger.info(
            "Verification-command generator: LLM returned null command for "
            "outcome %r — tech stack cannot verify this outcome. "
            "Returning None.",
            outcome.id,
        )
        return None

    if not isinstance(command, str) or not command.strip():
        raise ValueError(
            f"Verification-command generator: 'command' must be a "
            f"non-empty string or null for outcome {outcome.id!r}, got "
            f"{command!r}"
        )

    description = payload.get("description") or outcome.success_signal
    if not isinstance(description, str):
        raise ValueError(
            f"Verification-command generator: 'description' must be a "
            f"string for outcome {outcome.id!r}, got {description!r}"
        )

    readiness_probe = payload.get("readiness_probe")
    if readiness_probe is not None and not isinstance(readiness_probe, str):
        raise ValueError(
            f"Verification-command generator: 'readiness_probe' must be "
            f"a string or null for outcome {outcome.id!r}, got "
            f"{readiness_probe!r}"
        )

    return ContractVerification(
        signal_id=outcome.id,
        command=command.strip(),
        description=description.strip(),
        readiness_probe=readiness_probe.strip() if readiness_probe else None,
    )


async def generate_verification_commands(
    outcomes: List[UserOutcome],
    project_description: str,
    llm_client: Any,
) -> List[ContractVerification]:
    """Generate verifications for many outcomes concurrently.

    Fans out N LLM calls via ``asyncio.gather`` so total Phase A
    latency is dominated by the slowest single call, not the sum
    (Kaia review M4 on PR spec).

    Two categories of per-outcome failure are isolated rather than
    poisoning the whole batch (Kaia P2-2 on PR #642):

    1. The LLM declined the outcome (``generate_verification_command``
       returned ``None``) — drop the outcome silently. The tech stack
       cannot verify it; Phase B will surface the gap when it tries
       to enforce coverage.
    2. The per-outcome call raised an exception — log a WARNING with
       the outcome id and the exception, then drop that outcome. The
       remaining N-1 results still ship. Without ``return_exceptions=True``
       a single bad LLM response would lose ALL N verifications.

    Parameters
    ----------
    outcomes : List[UserOutcome]
        Outcomes to generate verifications for. Caller is responsible
        for filtering to in-scope outcomes before passing.
    project_description : str
        Tech-stack context — passed through to every per-outcome call.
    llm_client : Any
        Any client exposing ``async analyze(prompt, context)``.

    Returns
    -------
    List[ContractVerification]
        Successfully-generated verifications, in the input outcome
        order. May be shorter than ``len(outcomes)`` when some
        outcomes are unverifiable on the current stack OR when their
        per-outcome generator call raised.
    """
    if not outcomes:
        return []

    coroutines = [
        generate_verification_command(o, project_description, llm_client)
        for o in outcomes
    ]
    results = await asyncio.gather(*coroutines, return_exceptions=True)

    verifications: List[ContractVerification] = []
    for outcome, result in zip(outcomes, results):
        if isinstance(result, ContractVerification):
            verifications.append(result)
        elif isinstance(result, BaseException):
            # Per-outcome failure — log and drop. Keeps the rest of
            # the batch alive (P2-2 fix). Failing the whole batch on
            # any single bad LLM response converts an 11% per-project
            # partial-failure rate into a 11% complete-loss rate
            # (assuming ~2% per-call failure, 6 outcomes).
            logger.warning(
                "Verification-command generator failed for outcome %r: %s",
                outcome.id,
                result,
            )
        # else: result is None — LLM declined; gap surfaced by Phase B
    return verifications
