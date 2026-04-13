"""
Unit tests for Task.responsibility surfacing in agent prompts (GH-320 PR 2).

Tests that when a task carries ``Task.responsibility`` (set by
contract-first decomposition), ``build_tiered_instructions`` adds a
high-signal contract ownership layer that names the contract file and
instructs the agent to read it before writing code.

This layer is what makes contract-first decomposition work in practice:
agents can't produce code that adheres to a contract they haven't read.
"""

from datetime import datetime, timezone

import pytest

from src.core.models import Priority, Task, TaskStatus
from src.marcus_mcp.tools.task import build_tiered_instructions

pytestmark = pytest.mark.unit


def _make_task(
    name: str = "Implement GameEngine",
    responsibility: str = "implements GameEngine interface from types.ts",
    contract_file: str = "docs/api/types.ts",
) -> Task:
    """Build a contract-first Task for testing prompt surfacing."""
    return Task(
        id="contract_task_1",
        name=name,
        description="Build the game loop and state transitions",
        status=TaskStatus.TODO,
        priority=Priority.HIGH,
        assigned_to=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        due_date=None,
        estimated_hours=0.15,
        labels=["contract_first", "implementation"],
        source_type="contract_first",
        source_context={
            "contract_file": contract_file,
            "complexity_mode": "standard",
        },
        responsibility=responsibility,
    )


class TestContractResponsibilityLayer:
    """Test suite for the contract responsibility layer in tiered instructions."""

    def test_contract_responsibility_layer_fires_when_set(self):
        """
        Task.responsibility set → CONTRACT RESPONSIBILITY layer in output.

        The layer must surface the contract interface the agent owns
        so the LLM generating instructions emphasizes read-the-contract
        behavior.
        """
        task = _make_task()

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" in instructions
        assert "implements GameEngine interface from types.ts" in instructions

    def test_contract_file_named_in_instructions(self):
        """The contract file path must appear so agents know what to Read()."""
        task = _make_task(contract_file="docs/api/snake-types.ts")

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "docs/api/snake-types.ts" in instructions
        # The instruction must tell the agent to Read() the contract
        # before writing code.
        assert "Read" in instructions
        assert (
            "before writing" in instructions.lower() or "read" in instructions.lower()
        )

    def test_no_contract_layer_when_responsibility_unset(self):
        """Legacy tasks (no responsibility) → no contract layer."""
        legacy_task = Task(
            id="legacy_1",
            name="Implement Feature",
            description="Build a feature",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["backend"],
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=legacy_task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" not in instructions

    def test_contract_layer_instructs_no_silent_modification(self):
        """
        Agent must be told NOT to silently modify the contract.

        If an implementation diverges from the contract, the agent
        should report a blocker, not edit the contract to match the
        implementation. This is the invariant that makes
        contract-first decomposition work.
        """
        task = _make_task()

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # The exact wording is less important than the semantic signal.
        # Must mention that modification is off-limits.
        lower = instructions.lower()
        assert "do not" in lower or "don't" in lower or "must not" in lower
        assert "modify the contract" in lower or "silently" in lower

    def test_contract_layer_fires_before_subtask_layer(self):
        """
        Contract responsibility layer fires BEFORE subtask context.

        Ordering matters: contract ownership is structural. An agent
        should understand which contract interface it owns before
        considering whether this is a subtask of a larger task.
        """
        task = _make_task()
        task._is_subtask = True  # type: ignore[attr-defined]
        task._parent_task_name = "Parent Task"  # type: ignore[attr-defined]

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        contract_idx = instructions.find("CONTRACT RESPONSIBILITY")
        subtask_idx = instructions.find("SUBTASK CONTEXT")

        assert contract_idx != -1
        assert subtask_idx != -1
        assert contract_idx < subtask_idx, (
            "Contract responsibility must appear before subtask context "
            f"in the instructions. Contract at {contract_idx}, "
            f"subtask at {subtask_idx}."
        )

    def test_missing_contract_file_in_source_context_still_shows_responsibility(self):
        """
        Responsibility set but contract_file missing → still surfaces responsibility.

        Degenerate but recoverable: the agent knows what interface to
        implement even if the exact file path isn't specified. The
        layer falls back to a generic "check docs/" instruction.
        """
        task = _make_task()
        task.source_context = {}  # strip contract_file

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" in instructions
        assert "implements GameEngine interface from types.ts" in instructions
        # Generic fallback guidance
        assert "docs" in instructions.lower()


class TestContractMetadataPersistenceFallback:
    """
    Tests for the persistence fallback added in response to Codex P1
    review on PR #327.

    Kanban providers don't all round-trip Task.responsibility or
    Task.source_context. SQLite persists source_context but not
    responsibility as a top-level column. Planka persists neither.
    Without a fallback path, the CONTRACT RESPONSIBILITY layer would
    silently never fire for tasks reloaded from the board, even
    though they were born contract-first.

    The fix: ``decompose_by_contract`` embeds a MARCUS_CONTRACT_FIRST
    marker in the task description (which every provider round-trips
    as the core field), and ``_parse_contract_metadata`` reads from
    multiple sources in priority order.
    """

    def _make_task_without_responsibility(
        self,
        description: str,
        source_context=None,
    ) -> Task:
        """Simulate a task reloaded from a kanban provider that
        stripped Task.responsibility."""
        task = Task(
            id="reloaded_task",
            name="Implement GameEngine",
            description=description,
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.15,
            labels=["contract_first"],
            source_type=("contract_first" if source_context is not None else None),
            source_context=source_context,
            # NOTE: responsibility NOT set — simulates the provider
            # stripping it during persistence
        )
        return task

    def test_sqlite_reload_source_context_path(self):
        """
        SQLite reload: source_context round-trips but responsibility
        doesn't. Layer should fire via priority-2 source_context path.
        """
        task = self._make_task_without_responsibility(
            description="Build the game loop.",
            source_context={
                "contract_file": "docs/api/types.ts",
                "responsibility": "implements GameEngine interface",
                "complexity_mode": "standard",
            },
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" in instructions
        assert "implements GameEngine interface" in instructions
        assert "docs/api/types.ts" in instructions

    def test_planka_reload_description_marker_path(self):
        """
        Planka reload: nothing but description round-trips. Layer
        should fire via priority-3 description marker path.
        """
        description_with_marker = (
            "Build the game loop and state transitions.\n\n"
            "<!-- MARCUS_CONTRACT_FIRST\n"
            "responsibility: implements GameEngine interface from types.ts\n"
            "contract_file: docs/api/types.ts\n"
            "-->"
        )
        task = self._make_task_without_responsibility(
            description=description_with_marker,
            source_context=None,  # Planka doesn't persist source_context
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" in instructions
        assert "implements GameEngine interface from types.ts" in instructions
        assert "docs/api/types.ts" in instructions

    def test_no_marker_and_no_source_context_no_layer(self):
        """
        Non-contract-first legacy task with no marker → no layer.
        """
        task = self._make_task_without_responsibility(
            description="Build a generic feature.",
            source_context=None,
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" not in instructions

    def test_malformed_marker_ignored(self):
        """
        Malformed marker (missing closing `-->`) → no layer fires.
        Defensive: don't half-surface garbage to agents.
        """
        description_with_broken_marker = (
            "Build the game loop.\n\n"
            "<!-- MARCUS_CONTRACT_FIRST\n"
            "responsibility: implements GameEngine\n"
            "contract_file: docs/api/types.ts\n"
            # No closing --> on purpose
        )
        task = self._make_task_without_responsibility(
            description=description_with_broken_marker,
            source_context=None,
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" not in instructions

    def test_priority_order_direct_responsibility_wins(self):
        """
        Priority order: Task.responsibility > source_context >
        description marker. Direct field wins when present.
        """
        task = Task(
            id="priority_test",
            name="Test",
            description=(
                "Base description.\n\n"
                "<!-- MARCUS_CONTRACT_FIRST\n"
                "responsibility: from_marker\n"
                "contract_file: marker/path.ts\n"
                "-->"
            ),
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.15,
            labels=[],
            source_context={
                "responsibility": "from_source_context",
                "contract_file": "sc/path.ts",
            },
            responsibility="from_direct_field",
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        # Direct field wins
        assert "from_direct_field" in instructions
        # The contract_file associated with the winning layer is
        # source_context's (because that's where contract_file lives
        # when task.responsibility is set) — NOT the marker's.
        assert "sc/path.ts" in instructions
        assert "from_source_context" not in instructions
        assert "from_marker" not in instructions


class TestPhase1ProductIntentFraming:
    """
    Tests for the Phase 1 framing layer (GH-320 Option A + Phase 1).

    When ``source_context["product_intent"]`` is set by the contract
    decomposer, the instructions layer surfaces a "WHY THIS EXISTS"
    section above the contract-file details and adds an autonomy
    directive reframing the contract as a coordination boundary
    rather than a prescriptive spec. This is the fix for the
    dashboard-v70 regression where contract-first agents treated
    the contract as a full build spec and "forgot what a dashboard
    was."
    """

    def _make_task_with_intent(
        self,
        product_intent: str = "the user sees current weather on the dashboard",
        responsibility: str = "Weather data domain",
        contract_file: str = "docs/api/weather.md",
    ) -> Task:
        return Task(
            id="phase1_task",
            name="Implement Weather",
            description="Build the weather data feature",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.2,
            labels=["contract_first", "implementation"],
            source_type="contract_first",
            source_context={
                "contract_file": contract_file,
                "product_intent": product_intent,
                "complexity_mode": "standard",
            },
            responsibility=responsibility,
        )

    def test_product_intent_surfaces_when_set(self) -> None:
        """
        Product intent set → WHY THIS EXISTS section appears in the
        contract responsibility layer.
        """
        task = self._make_task_with_intent()
        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "WHY THIS EXISTS" in instructions
        assert "the user sees current weather on the dashboard" in instructions

    def test_autonomy_directive_accompanies_intent(self) -> None:
        """
        When intent is present, the autonomy directive reframes
        the contract as a coordination boundary. This is what
        releases the agent from prescriptive-spec framing.
        """
        task = self._make_task_with_intent()
        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        lower = instructions.lower()
        assert "coordination boundary" in lower
        assert "not a build spec" in lower
        assert "use judgment" in lower

    def test_product_intent_precedes_contract_file_section(self) -> None:
        """
        Ordering: WHY THIS EXISTS (intent) must appear BEFORE the
        "Contract file:" line so the agent reads the user-facing
        reason before the interface details.
        """
        task = self._make_task_with_intent()
        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        intent_idx = instructions.find("WHY THIS EXISTS")
        contract_file_idx = instructions.find("Contract file:")

        assert intent_idx != -1
        assert contract_file_idx != -1
        assert intent_idx < contract_file_idx, (
            "product intent must appear before contract file. "
            f"intent at {intent_idx}, contract file at {contract_file_idx}"
        )

    def test_no_intent_no_framing_section(self) -> None:
        """
        Legacy tasks without product_intent → no WHY THIS EXISTS
        section. The contract responsibility layer still fires
        but looks like the pre-Phase-1 instructions.
        """
        task = Task(
            id="legacy_contract_task",
            name="Implement Legacy",
            description="Build it",
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.15,
            labels=["contract_first"],
            source_type="contract_first",
            source_context={
                "contract_file": "docs/api/legacy.md",
                "complexity_mode": "standard",
                # No product_intent field at all
            },
            responsibility="Legacy interface",
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "CONTRACT RESPONSIBILITY" in instructions  # layer still fires
        assert "WHY THIS EXISTS" not in instructions  # but no framing
        assert "Legacy interface" in instructions

    def test_empty_intent_treated_as_no_intent(self) -> None:
        """
        Empty-string product_intent must be treated the same as
        missing — don't surface a blank WHY THIS EXISTS heading.
        """
        task = self._make_task_with_intent(product_intent="")
        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "WHY THIS EXISTS" not in instructions

    def test_product_intent_survives_description_marker_fallback(self) -> None:
        """
        Phase 1 marker path: when the task reloaded from Planka has
        only the HTML comment marker to work from, product_intent
        embedded in the marker must be parsed and surfaced.
        """
        description_with_intent_marker = (
            "Build the weather widget.\n\n"
            "<!-- MARCUS_CONTRACT_FIRST\n"
            "responsibility: implements WeatherProvider\n"
            "contract_file: docs/api/weather.md\n"
            "product_intent: users check weather before heading out\n"
            "-->"
        )
        task = Task(
            id="planka_reload_phase1",
            name="Implement Weather",
            description=description_with_intent_marker,
            status=TaskStatus.TODO,
            priority=Priority.HIGH,
            assigned_to=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            due_date=None,
            estimated_hours=0.15,
            labels=["contract_first"],
            source_type=None,  # Planka-like: nothing round-trips
            source_context=None,
        )

        instructions = build_tiered_instructions(
            base_instructions="Do the task",
            task=task,
            context_data=None,
            dependency_awareness=None,
            predictions=None,
        )

        assert "WHY THIS EXISTS" in instructions
        assert "users check weather before heading out" in instructions
