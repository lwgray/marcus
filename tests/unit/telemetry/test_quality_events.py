"""Unit tests for the Stage 5A quality event helpers (Marcus #9).

Three events:

- ``fire_agent_registered``         — agent join
- ``fire_planning_intent_fidelity`` — planning quality score
- ``fire_project_cost_summary``     — aggregate cost roll-up

All pin no-PII regression nets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.delenv("MARCUS_TELEMETRY", raising=False)
    monkeypatch.delenv("MARCUS_POSTHOG_API_KEY", raising=False)
    return tmp_path


@pytest.fixture
def mock_client(monkeypatch: pytest.MonkeyPatch) -> Any:
    client = MagicMock()
    monkeypatch.setattr(
        "src.telemetry.events.get_telemetry_client", lambda: client
    )
    return client


class TestFireAgentRegistered:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_agent_registered

        fire_agent_registered(
            role="Backend Developer",
            skills=["python", "fastapi"],
            agent_model="claude-sonnet-4-6",
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "agent_registered"
        assert args[1] == {
            "role": "Backend Developer",
            "skills": ["python", "fastapi"],
            "agent_model": "claude-sonnet-4-6",
        }

    def test_agent_model_defaults_to_unknown(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_agent_registered

        fire_agent_registered(role="x", skills=[])
        props = mock_client.capture.call_args[0][1]
        assert props["agent_model"] == "unknown"

    def test_no_agent_name_in_payload(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """Agent display name (which may identify a human) is NOT shipped.

        The disclosure ships ``role`` and ``skills`` (user-controlled
        labels per the disclosure note), NOT ``name`` or ``agent_id``.
        Signature is the regression net.
        """
        import inspect

        from src.telemetry.events import fire_agent_registered

        sig = inspect.signature(fire_agent_registered)
        # Only role / skills / agent_model are accepted.
        assert set(sig.parameters.keys()) == {"role", "skills", "agent_model"}

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_agent_registered

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_agent_registered(role="x", skills=[])  # Must not raise.


class TestFirePlanningIntentFidelity:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_planning_intent_fidelity

        fire_planning_intent_fidelity(
            decomposer="contract_first",
            intent_fidelity_score=0.87,
            coverage_before_fill=0.71,
            coverage_after_fill=0.94,
            gap_filled_outcomes=3,
        )
        args, _ = mock_client.capture.call_args
        assert args[0] == "planning_intent_fidelity"
        assert args[1] == {
            "decomposer": "contract_first",
            "intent_fidelity_score": 0.87,
            "coverage_before_fill": 0.71,
            "coverage_after_fill": 0.94,
            "gap_filled_outcomes": 3,
        }

    def test_project_name_not_accepted_by_signature(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """The internal PLANNING_INTENT_FIDELITY event carries
        ``project_name`` for Cato.  The PostHog forwarder MUST NOT.
        Signature pin so a future refactor can't silently start
        accepting (and shipping) the name.
        """
        import inspect

        from src.telemetry.events import fire_planning_intent_fidelity

        sig = inspect.signature(fire_planning_intent_fidelity)
        assert "project_name" not in sig.parameters

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_planning_intent_fidelity

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_planning_intent_fidelity(
            decomposer="x",
            intent_fidelity_score=0.5,
            coverage_before_fill=0.5,
            coverage_after_fill=0.5,
            gap_filled_outcomes=0,
        )  # Must not raise.


class TestFireProjectCostSummary:
    def test_event_name_and_keys(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_project_cost_summary

        summary = {
            "input_tokens": 142000,
            "output_tokens": 18500,
            "cache_read_tokens": 89000,
            "cache_creation_tokens": 4200,
            "cost_usd_cents": 47,
            "task_count": 14,
        }
        fire_project_cost_summary(summary)
        args, _ = mock_client.capture.call_args
        assert args[0] == "project_cost_summary"
        # All token + cost fields preserved.
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_read_tokens",
            "cache_creation_tokens",
            "cost_usd_cents",
        ):
            assert args[1][key] == summary[key]

    def test_cost_per_task_derived(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_project_cost_summary

        # 47 cents / 14 tasks ≈ 3.4 cents/task
        fire_project_cost_summary(
            {"cost_usd_cents": 47, "task_count": 14, "input_tokens": 0}
        )
        props = mock_client.capture.call_args[0][1]
        assert abs(props["cost_per_task_cents"] - 47 / 14) < 0.1

    def test_zero_tasks_does_not_divide(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        from src.telemetry.events import fire_project_cost_summary

        fire_project_cost_summary(
            {"cost_usd_cents": 0, "task_count": 0, "input_tokens": 0}
        )
        props = mock_client.capture.call_args[0][1]
        assert props["cost_per_task_cents"] == 0

    def test_no_project_id_no_project_name(
        self, isolated_home: Path, mock_client: Any
    ) -> None:
        """project_id and project_name from the source summary must NOT ship.

        The cost_aggregator.project_summary() return value carries
        identifying fields for local use; this event ships only the
        numeric metrics.
        """
        from src.telemetry.events import fire_project_cost_summary

        polluted_summary = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
            "cache_creation_tokens": 0,
            "cost_usd_cents": 5,
            "task_count": 3,
            "project_id": "SECRET-customer-xyz-uuid",
            "project_name": "ProjectX",
        }
        fire_project_cost_summary(polluted_summary)
        props = mock_client.capture.call_args[0][1]
        assert "project_id" not in props
        assert "project_name" not in props
        flat = " ".join(str(v) for v in props.values())
        assert "SECRET" not in flat
        assert "customer" not in flat

    def test_swallows_exceptions(
        self, isolated_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.telemetry.events import fire_project_cost_summary

        broken = MagicMock()
        broken.capture.side_effect = RuntimeError("simulated")
        monkeypatch.setattr(
            "src.telemetry.events.get_telemetry_client", lambda: broken
        )
        fire_project_cost_summary({})  # Must not raise.
