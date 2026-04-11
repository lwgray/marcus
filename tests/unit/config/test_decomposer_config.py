"""
Unit tests for decomposer strategy selection (GH-320 PR 2).

Tests the precedence order of ``resolve_decomposer``:
1. Explicit options["decomposer"]
2. MARCUS_DECOMPOSER env var
3. Default: feature_based

And the loud-warning behavior for unknown strategy values.
"""

import pytest

from src.config.decomposer_config import (
    DECOMPOSER_CONTRACT_FIRST,
    DECOMPOSER_FEATURE_BASED,
    ENV_VAR,
    is_contract_first,
    resolve_decomposer,
)

pytestmark = pytest.mark.unit


class TestResolveDecomposer:
    """Test suite for resolve_decomposer precedence and validation."""

    def test_default_is_feature_based(self, monkeypatch):
        """No env var, no options → feature_based."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert resolve_decomposer() == DECOMPOSER_FEATURE_BASED
        assert resolve_decomposer(None) == DECOMPOSER_FEATURE_BASED
        assert resolve_decomposer({}) == DECOMPOSER_FEATURE_BASED

    def test_options_dict_contract_first_wins(self, monkeypatch):
        """options["decomposer"]=contract_first is selected."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        result = resolve_decomposer({"decomposer": DECOMPOSER_CONTRACT_FIRST})
        assert result == DECOMPOSER_CONTRACT_FIRST

    def test_env_var_contract_first_wins_when_options_silent(self, monkeypatch):
        """MARCUS_DECOMPOSER env var is consulted when options has no key."""
        monkeypatch.setenv(ENV_VAR, DECOMPOSER_CONTRACT_FIRST)
        assert resolve_decomposer(None) == DECOMPOSER_CONTRACT_FIRST
        assert resolve_decomposer({}) == DECOMPOSER_CONTRACT_FIRST

    def test_options_dict_overrides_env_var(self, monkeypatch):
        """options["decomposer"] takes precedence over MARCUS_DECOMPOSER."""
        monkeypatch.setenv(ENV_VAR, DECOMPOSER_CONTRACT_FIRST)
        result = resolve_decomposer({"decomposer": DECOMPOSER_FEATURE_BASED})
        assert result == DECOMPOSER_FEATURE_BASED

    def test_unknown_strategy_in_options_falls_back(self, monkeypatch, caplog):
        """Unknown options value → fall back to feature_based with warning."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        import logging

        with caplog.at_level(logging.WARNING, logger="src.config.decomposer_config"):
            result = resolve_decomposer({"decomposer": "quantum_cluster"})
        assert result == DECOMPOSER_FEATURE_BASED
        assert any("quantum_cluster" in rec.message for rec in caplog.records)
        assert any("falling back" in rec.message for rec in caplog.records)

    def test_unknown_strategy_in_env_var_falls_back(self, monkeypatch, caplog):
        """Unknown env value → fall back to feature_based with warning."""
        monkeypatch.setenv(ENV_VAR, "banana_strategy")
        import logging

        with caplog.at_level(logging.WARNING, logger="src.config.decomposer_config"):
            result = resolve_decomposer(None)
        assert result == DECOMPOSER_FEATURE_BASED
        assert any("banana_strategy" in rec.message for rec in caplog.records)

    def test_feature_based_explicit_in_options(self, monkeypatch):
        """Explicit feature_based in options returns feature_based."""
        monkeypatch.setenv(ENV_VAR, DECOMPOSER_CONTRACT_FIRST)
        result = resolve_decomposer({"decomposer": DECOMPOSER_FEATURE_BASED})
        assert result == DECOMPOSER_FEATURE_BASED


class TestIsContractFirst:
    """Test suite for the is_contract_first convenience wrapper."""

    def test_default_false(self, monkeypatch):
        """No env var, no options → False."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert is_contract_first() is False
        assert is_contract_first(None) is False

    def test_true_when_contract_first_selected(self, monkeypatch):
        """options contract_first → True."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert is_contract_first({"decomposer": DECOMPOSER_CONTRACT_FIRST}) is True

    def test_false_when_feature_based_selected(self, monkeypatch):
        """options feature_based → False."""
        monkeypatch.delenv(ENV_VAR, raising=False)
        assert is_contract_first({"decomposer": DECOMPOSER_FEATURE_BASED}) is False

    def test_true_when_env_var_contract_first(self, monkeypatch):
        """Env var contract_first → True."""
        monkeypatch.setenv(ENV_VAR, DECOMPOSER_CONTRACT_FIRST)
        assert is_contract_first(None) is True
