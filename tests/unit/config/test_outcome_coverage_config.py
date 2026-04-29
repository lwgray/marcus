"""Unit tests for the MARCUS_OUTCOME_COVERAGE feature flag (issue #449)."""

from typing import Any

import pytest

from src.config.outcome_coverage_config import (
    ENV_VAR_NAME,
    is_outcome_coverage_enabled,
)

pytestmark = pytest.mark.unit


class TestOutcomeCoverageFlag:
    """The flag defaults to OFF and accepts canonical truthy values."""

    def test_default_off_when_env_unset(self, monkeypatch: Any) -> None:
        monkeypatch.delenv(ENV_VAR_NAME, raising=False)
        assert is_outcome_coverage_enabled() is False

    def test_default_off_when_env_empty(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "")
        assert is_outcome_coverage_enabled() is False

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "enabled"])
    def test_truthy_values_enable_flag(self, monkeypatch: Any, value: str) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, value)
        assert is_outcome_coverage_enabled() is True

    @pytest.mark.parametrize("value", ["TRUE", "Yes", "ON", "Enabled"])
    def test_truthy_values_are_case_insensitive(
        self, monkeypatch: Any, value: str
    ) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, value)
        assert is_outcome_coverage_enabled() is True

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "random"])
    def test_falsy_or_unknown_values_keep_flag_off(
        self, monkeypatch: Any, value: str
    ) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, value)
        assert is_outcome_coverage_enabled() is False

    def test_whitespace_around_value_is_stripped(self, monkeypatch: Any) -> None:
        monkeypatch.setenv(ENV_VAR_NAME, "  true  ")
        assert is_outcome_coverage_enabled() is True

    def test_constant_name_matches_documented(self) -> None:
        """Locks in the public env var name so docs and code stay in sync."""
        assert ENV_VAR_NAME == "MARCUS_OUTCOME_COVERAGE"
