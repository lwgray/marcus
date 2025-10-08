"""
Unit tests for password hashing and verification.

Tests bcrypt password hashing, verification, and strength evaluation.
"""

import pytest
from app.security.password import (
    hash_password,
    verify_password,
    get_password_strength,
)


class TestPasswordHashing:
    """Test suite for password hashing functionality."""

    def test_hash_password_creates_valid_hash(self) -> None:
        """Test that hash_password creates a valid bcrypt hash."""
        # Arrange
        password = "TestPassword123!"  # pragma: allowlist secret

        # Act
        hashed = hash_password(password)

        # Assert
        assert isinstance(hashed, str)
        assert len(hashed) == 60  # Bcrypt hashes are always 60 chars
        assert hashed.startswith("$2b$")  # Bcrypt format identifier

    def test_hash_password_generates_unique_salts(self) -> None:
        """Test that each hash uses a unique salt."""
        # Arrange
        password = "SamePassword"  # pragma: allowlist secret

        # Act
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Assert
        assert hash1 != hash2  # Different salts = different hashes

    def test_hash_password_with_custom_rounds(self) -> None:
        """Test hashing with custom work factor."""
        # Arrange
        password = "TestPassword"  # pragma: allowlist secret

        # Act
        hash_10 = hash_password(password, rounds=10)
        hash_14 = hash_password(password, rounds=14)

        # Assert
        assert "$2b$10$" in hash_10
        assert "$2b$14$" in hash_14

    def test_verify_password_correct_password(self) -> None:
        """Test verifying correct password."""
        # Arrange
        password = "CorrectPassword"  # pragma: allowlist secret
        hashed = hash_password(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    def test_verify_password_incorrect_password(self) -> None:
        """Test verifying incorrect password."""
        # Arrange
        correct_password = "CorrectPassword"  # pragma: allowlist secret
        wrong_password = "WrongPassword"  # pragma: allowlist secret
        hashed = hash_password(correct_password)

        # Act
        result = verify_password(wrong_password, hashed)

        # Assert
        assert result is False

    def test_verify_password_invalid_hash(self) -> None:
        """Test verifying password with invalid hash format."""
        # Arrange
        password = "TestPassword"  # pragma: allowlist secret
        invalid_hash = "not-a-valid-hash"  # pragma: allowlist secret

        # Act
        result = verify_password(password, invalid_hash)

        # Assert
        assert result is False  # Should not raise exception

    def test_verify_password_case_sensitive(self) -> None:
        """Test that password verification is case-sensitive."""
        # Arrange
        password = "Password123"  # pragma: allowlist secret
        hashed = hash_password(password)

        # Act
        result_lower = verify_password("password123", hashed)
        result_upper = verify_password("PASSWORD123", hashed)

        # Assert
        assert result_lower is False
        assert result_upper is False


class TestPasswordStrength:
    """Test suite for password strength evaluation."""

    def test_password_strength_very_weak(self) -> None:
        """Test very weak password (< 8 characters)."""
        # Act
        result = get_password_strength("short")  # pragma: allowlist secret

        # Assert
        assert result["score"] == 0
        assert result["length"] == 5
        assert "Very weak" in result["recommendation"]

    def test_password_strength_weak(self) -> None:
        """Test weak password (8+ chars, single type)."""
        # Act
        result = get_password_strength("lowercase")  # pragma: allowlist secret

        # Assert
        assert result["score"] in [1, 2]
        assert result["has_lower"] is True
        assert result["has_upper"] is False
        assert result["has_digit"] is False
        assert result["has_special"] is False

    def test_password_strength_moderate(self) -> None:
        """Test moderate password (8+ chars, multiple types)."""
        # Act
        result = get_password_strength("Password1")  # pragma: allowlist secret

        # Assert
        assert result["score"] >= 2
        assert result["has_lower"] is True
        assert result["has_upper"] is True
        assert result["has_digit"] is True

    def test_password_strength_good(self) -> None:
        """Test good password (12+ chars, four types)."""
        # Act
        result = get_password_strength("GoodPass123!")  # pragma: allowlist secret

        # Assert
        assert result["score"] >= 4
        assert result["has_lower"] is True
        assert result["has_upper"] is True
        assert result["has_digit"] is True
        assert result["has_special"] is True

    def test_password_strength_strong(self) -> None:
        """Test strong password (16+ chars, all types)."""
        # Act
        result = get_password_strength("VeryStrongPassword123!")  # pragma: allowlist secret

        # Assert
        assert result["score"] == 5
        assert result["has_lower"] is True
        assert result["has_upper"] is True
        assert result["has_digit"] is True
        assert result["has_special"] is True
        assert result["recommendation"] == "Strong"

    def test_password_strength_no_uppercase(self) -> None:
        """Test password without uppercase letters."""
        # Act
        result = get_password_strength("lowercase123!")  # pragma: allowlist secret

        # Assert
        assert result["has_upper"] is False
        assert result["has_lower"] is True
        assert result["has_digit"] is True
        assert result["has_special"] is True

    def test_password_strength_only_special_chars(self) -> None:
        """Test password with only special characters."""
        # Act
        result = get_password_strength("!@#$%^&*()")  # pragma: allowlist secret

        # Assert
        assert result["has_special"] is True
        assert result["has_lower"] is False
        assert result["has_upper"] is False
        assert result["has_digit"] is False
