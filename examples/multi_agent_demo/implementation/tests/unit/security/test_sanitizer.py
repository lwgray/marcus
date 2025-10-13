"""
Unit tests for input sanitization.

Tests HTML sanitization, text cleaning, and input validation.
"""

import pytest
from app.security.sanitizer import (
    escape_sql_like,
    sanitize_email,
    sanitize_filename,
    sanitize_html,
    sanitize_text,
    sanitize_url,
)


class TestSanitizeHTML:
    """Test suite for HTML sanitization."""

    def test_sanitize_html_removes_script_tags(self) -> None:
        """Test that <script> tags are removed/escaped."""
        # Arrange
        dangerous_html = (
            "<p>Hello</p><script>alert('xss')</script>"  # pragma: allowlist secret
        )

        # Act
        safe_html = sanitize_html(dangerous_html)

        # Assert
        assert "<script>" not in safe_html
        assert "<p>Hello</p>" in safe_html

    def test_sanitize_html_preserves_allowed_tags(self) -> None:
        """Test that allowed tags are preserved."""
        # Arrange
        html = "<p>Hello <strong>World</strong></p>"

        # Act
        result = sanitize_html(html)

        # Assert
        assert result == html

    def test_sanitize_html_removes_dangerous_attributes(self) -> None:
        """Test that dangerous attributes like onclick are removed."""
        # Arrange
        html = (
            '<a href="#" onclick="alert(\'xss\')">Link</a>'  # pragma: allowlist secret
        )

        # Act
        result = sanitize_html(html)

        # Assert
        assert "onclick" not in result  # pragma: allowlist secret
        assert '<a href="#">Link</a>' == result

    def test_sanitize_html_strip_mode(self) -> None:
        """Test strip mode removes disallowed tags entirely."""
        # Arrange
        html = "<p>Keep</p><script>Remove</script>"  # pragma: allowlist secret

        # Act
        result = sanitize_html(html, strip=True)

        # Assert
        assert "script" not in result.lower()  # pragma: allowlist secret
        assert "<p>Keep</p>" in result


class TestSanitizeText:
    """Test suite for plain text sanitization."""

    def test_sanitize_text_removes_html(self) -> None:
        """Test that HTML tags are removed from text."""
        # Arrange
        text = "Hello <b>World</b>"

        # Act
        result = sanitize_text(text)

        # Assert
        assert result == "Hello World"
        assert "<b>" not in result

    def test_sanitize_text_removes_extra_whitespace(self) -> None:
        """Test that extra whitespace is normalized."""
        # Arrange
        text = "Hello    World  \n\n  Test"

        # Act
        result = sanitize_text(text)

        # Assert
        assert result == "Hello World Test"

    def test_sanitize_text_truncates_to_max_length(self) -> None:
        """Test that text is truncated to max_length."""
        # Arrange
        long_text = "This is a very long text that should be truncated"

        # Act
        result = sanitize_text(long_text, max_length=20)

        # Assert
        assert len(result) <= 20
        assert result.endswith("...")


class TestSanitizeFilename:
    """Test suite for filename sanitization."""

    def test_sanitize_filename_removes_path_separators(self) -> None:
        """Test that path separators are removed."""
        # Arrange
        filename = "../../etc/passwd"  # pragma: allowlist secret

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert "/" not in result
        assert "\\\\" not in result

    def test_sanitize_filename_removes_dangerous_characters(self) -> None:
        """Test that dangerous characters are removed."""
        # Arrange
        filename = "file<>name.txt"

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_filename_preserves_extension(self) -> None:
        """Test that file extension is preserved."""
        # Arrange
        filename = "document.pdf"

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert result.endswith(".pdf")

    def test_sanitize_filename_truncates_long_filename_with_extension(self) -> None:
        """Test that very long filenames are truncated while preserving extension."""
        # Arrange
        long_name = "a" * 300  # 300 characters
        filename = f"{long_name}.txt"

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert len(result) <= 255
        assert result.endswith(".txt")

    def test_sanitize_filename_truncates_long_filename_without_extension(self) -> None:
        """Test that very long filenames without extension are truncated."""
        # Arrange
        filename = "a" * 300  # 300 characters, no extension

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert len(result) <= 255

    def test_sanitize_filename_handles_empty_after_sanitization(self) -> None:
        """Test that completely invalid filename gets default name."""
        # Arrange
        filename = "....   "  # Only dots and spaces

        # Act
        result = sanitize_filename(filename)

        # Assert
        assert result == "file"


class TestSanitizeEmail:
    """Test suite for email sanitization."""

    def test_sanitize_email_lowercases_email(self) -> None:
        """Test that email is converted to lowercase."""
        # Arrange
        email = "User@Example.COM"

        # Act
        result = sanitize_email(email)

        # Assert
        assert result == "user@example.com"

    def test_sanitize_email_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        # Arrange
        email = "  user@example.com  "

        # Act
        result = sanitize_email(email)

        # Assert
        assert result == "user@example.com"

    def test_sanitize_email_invalid_format(self) -> None:
        """Test that invalid email raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid email"):
            sanitize_email("not-an-email")


class TestSanitizeURL:
    """Test suite for URL sanitization."""

    def test_sanitize_url_allows_https(self) -> None:
        """Test that HTTPS URLs are allowed."""
        # Arrange
        url = "https://example.com/path"

        # Act
        result = sanitize_url(url)

        # Assert
        assert result == url

    def test_sanitize_url_blocks_javascript(self) -> None:
        """Test that javascript: URLs are blocked."""
        # Act & Assert
        with pytest.raises(ValueError, match="not allowed"):
            sanitize_url("javascript:alert('xss')")  # pragma: allowlist secret

    def test_sanitize_url_requires_domain(self) -> None:
        """Test that URL must include domain."""
        # Act & Assert
        with pytest.raises(ValueError, match="must include a domain"):
            sanitize_url("http://")

    def test_sanitize_url_malformed_url(self) -> None:
        """Test that malformed URLs raise ValueError."""
        # Act & Assert
        # Test with various malformed URLs that might cause urlparse to fail
        with pytest.raises(
            ValueError, match="Invalid URL format|not allowed|must include a domain"
        ):
            sanitize_url("ht!tp://invalid url with spaces")


class TestEscapeSQLLike:
    """Test suite for SQL LIKE escaping."""

    def test_escape_sql_like_escapes_percent(self) -> None:
        """Test that % wildcard is escaped."""
        # Arrange
        value = "50% discount"

        # Act
        result = escape_sql_like(value)

        # Assert
        assert "\\%" in result

    def test_escape_sql_like_escapes_underscore(self) -> None:
        """Test that _ wildcard is escaped."""
        # Arrange
        value = "test_value"

        # Act
        result = escape_sql_like(value)

        # Assert
        assert "\\_" in result
